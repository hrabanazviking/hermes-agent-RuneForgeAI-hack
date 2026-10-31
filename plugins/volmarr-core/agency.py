"""Agency orchestrator (Emergent Agency Phase 6, roadmap §13).

Connects the five agency domains into ONE bounded cycle:

1. identity and continuity health, 2. autonomy policy / circuit
breaker, 3. compact self-model, 4. deterministic drive decay,
5. open curiosity frontier, 6. active / blocked goals, 7. candidate
intentions, 8. deduplication and deterministic scoring, 9. selection
of at most N candidates, 10. a bounded plan (the selected proposals,
in order), 11. a policy decision for every selected action,
12. execution of allowed actions *only through a registered local
executor*, 13. verification, 14. the agency journal, 15. structured
metacognition when the cycle did something significant, 16. evidence
fed back to drives / curiosity, 17. a content-free cycle report
(the telemetry shape — counts and statuses, never content),
18. end of cycle.

One invocation performs one cycle and exits: this module contains no
loop, no scheduler, and no turn-path caller. Hermes cron decides when
another cycle occurs (the proposal-only routine is Phase 7).

Execution honesty: the only built-in executor is ``world_get``, a
read-only local inspection (self-model claims + goal ledger readable
and consistent on re-read). An allowed action with no registered
executor is recorded ``skipped`` with verification
``not_executed_no_executor`` — allowed is never reported as executed.
Additional executors are injected by the caller (tests, later
phases); none may be registered implicitly.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from hermes_constants import get_hermes_home, mkdir_under_hermes_home

from .agency_contracts import (
    ActionProposal,
    ActionResult,
    AgencyCycleReport,
    Provenance,
    ReflectionRecord,
)
from .autonomy import AutonomyStore
from .context_packet import ContextItem
from .curiosity import CuriosityError, CuriosityStore
from .drives import DriveError, DriveStore
from .goals import GoalStore
from .heartbeat import HeartbeatError, HeartbeatStore
from .identity import IdentityError, IdentityStore, _as_bool
from .metacognition import MetacognitionError, MetacognitionStore
from .self_model import SelfModelStore

AGENCY_JOURNAL_VERSION = 1
DEFAULT_JOURNAL_PATH = Path("entity") / "agency_journal.jsonl"
DEFAULT_JOURNAL_LIMIT = 200
MAX_JOURNAL_BYTES = 4 * 1024 * 1024
DEFAULT_MAX_CANDIDATES = 3
EXECUTOR_ACTIONS = frozenset({"world_get"})

_JOURNAL_FIELDS = {
    "journal_version", "cycle_id", "owner_entity_id", "trigger", "status",
    "started_at", "ended_at", "continuity_health", "selected_goal_id",
    "selected_intent_id", "actions_proposed", "actions_allowed",
    "actions_confirmation", "actions_denied", "actions_executed",
    "actions_failed", "actions_skipped", "verification", "reflection_id",
}

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


class AgencyError(RuntimeError):
    """An agency cycle cannot be safely run or journaled."""


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


# An executor takes (proposal, candidate) and returns (status, summary)
# with status in {"succeeded", "failed"}; anything else is a failure.
Executor = Callable[[ActionProposal, dict[str, Any]], tuple[str, str]]


class AgencyOrchestrator:
    """Run one bounded agency cycle over the existing agency stores."""

    def __init__(self, ctx, executors: dict[str, Executor] | None = None) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)
        self._autonomy = AutonomyStore(ctx)
        self._drives = DriveStore(ctx)
        self._curiosity = CuriosityStore(ctx)
        self._goals = GoalStore(ctx)
        self._self_model = SelfModelStore(ctx)
        self._metacognition = MetacognitionStore(ctx)
        self._heartbeat = HeartbeatStore(ctx)
        self._executors: dict[str, Executor] = {"world_get": self._execute_world_get}
        for action, executor in (executors or {}).items():
            if not callable(executor):
                raise AgencyError("agency executor must be callable")
            self._executors[action] = executor

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("agency_enabled", True), True
        )

    def _max_candidates(self) -> int:
        try:
            value = int(self._ctx.get_config("agency_max_candidates", DEFAULT_MAX_CANDIDATES))
        except (TypeError, ValueError):
            value = DEFAULT_MAX_CANDIDATES
        return min(10, max(1, value))

    def _journal_limit(self) -> int:
        try:
            value = int(self._ctx.get_config("agency_journal_limit", DEFAULT_JOURNAL_LIMIT))
        except (TypeError, ValueError):
            value = DEFAULT_JOURNAL_LIMIT
        return min(500, max(10, value))

    def journal_path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config("agency_journal_path", str(DEFAULT_JOURNAL_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_JOURNAL_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_JOURNAL_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise AgencyError("agency journal path resolves outside the active profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    # -- the cycle ---------------------------------------------------------
    def run_cycle(self, trigger: str = "scheduled", *, now: datetime | None = None) -> AgencyCycleReport:
        if not isinstance(trigger, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", trigger):
            raise AgencyError("agency cycle trigger is invalid")
        if not self.enabled():
            raise AgencyError("agency orchestrator is disabled")
        started = now or _now_dt()
        cycle_id = str(uuid.uuid4())
        owner = self._identity.ensure().entity_id
        source = Provenance(source_type="cognition_telemetry", source_id="agency_cycle")

        continuity_health = self._continuity_health(started)
        self._autonomy.ensure()
        state = self._autonomy.state()

        counts = dict(proposed=0, allow=0, confirmation=0, deny=0,
                      executed=0, failed=0, skipped=0)
        selected_goal_id = ""
        selected_intent_id = ""
        reflection_id = ""
        verification = "not_run"

        if state["paused"] or state["circuit_breaker_tripped"]:
            status = "paused"
            ended = _now_dt() if now is None else started
            self._append_journal(self._journal_record(
                cycle_id, owner, trigger, status, started, ended, continuity_health,
                selected_goal_id, selected_intent_id, counts, verification, reflection_id,
            ))
            return self._report(cycle_id, owner, status, started, ended, source, counts)

        # Steps 3-6: read the domains (decay is the deterministic
        # drive update; every other read is side-effect free).
        self._self_model.ensure()
        claims_count = len(self._self_model.claims())
        self._drives.ensure()
        self._drives.decay(now=started)
        self._curiosity.ensure()
        self._goals.ensure()

        candidates = self._candidates(owner, started, claims_count)
        selected = candidates[: self._max_candidates()]
        counts["proposed"] = len(selected)

        executed_refs: list[tuple[dict[str, Any], ActionProposal]] = []
        for candidate in selected:
            proposal = candidate["proposal"]
            if not selected_intent_id:
                selected_intent_id = proposal.proposal_id
            if candidate["kind"] == "goal" and not selected_goal_id:
                selected_goal_id = candidate["ref"]
            decision = self._autonomy.evaluate(proposal, now=started)
            self._autonomy.record_decision(decision)
            counts[{"allow": "allow", "require_confirmation": "confirmation",
                    "deny": "deny"}[decision.decision]] += 1
            if decision.decision != "allow":
                continue
            result, verified = self._execute(candidate, proposal, owner)
            self._autonomy.record_result(result, estimated_cost=candidate["estimated_cost"])
            if result.status == "succeeded":
                counts["executed"] += 1
                executed_refs.append((candidate, proposal))
            elif result.status == "failed":
                counts["failed"] += 1
            else:
                counts["skipped"] += 1

        if counts["failed"]:
            verification = "failed"
        elif counts["executed"] and counts["skipped"]:
            verification = "partial"
        elif counts["executed"]:
            verification = "passed"
        elif counts["allow"]:
            verification = "not_executed_no_executor"
        status = "failed" if counts["failed"] else "completed"

        # Step 16: evidence back to drives / curiosity for what ran.
        for candidate, _proposal in executed_refs:
            self._feed_back(candidate, cycle_id, started)

        # Step 15: structured metacognition for significant action.
        if counts["executed"]:
            reflection_id = self._reflect(
                owner, cycle_id, selected_intent_id, counts, started
            )

        ended = _now_dt() if now is None else started
        self._append_journal(self._journal_record(
            cycle_id, owner, trigger, status, started, ended, continuity_health,
            selected_goal_id, selected_intent_id, counts, verification, reflection_id,
        ))
        return self._report(cycle_id, owner, status, started, ended, source, counts)

    # -- steps 1-10 helpers --------------------------------------------------
    def _continuity_health(self, moment: datetime) -> str:
        try:
            self._heartbeat.ensure()
            data = self._heartbeat.read()
        except (IdentityError, HeartbeatError, OSError):
            return "unknown"
        last = data.get("last_heartbeat_at", "")
        if not last:
            return "never"
        age = (moment - _parse(last)).total_seconds()
        return "fresh" if age <= self._heartbeat.stale_after_seconds() else "stale"

    def _candidates(self, owner: str, moment: datetime, claims_count: int) -> list[dict[str, Any]]:
        raw: list[dict[str, Any]] = []
        expires = _fmt(moment + timedelta(hours=1))
        for proposal in self._drives.proposals(now=moment):
            raw.append({
                "kind": "drive", "ref": proposal["drive"], "score": float(proposal["expected_value"]),
                "action": "world_get", "risk_class": 0, "estimated_cost": "low",
                "summary": proposal["proposal"],
                "source": Provenance(source_type="drive", source_id=proposal["drive"]),
            })
        for entry in self._curiosity.frontier(now=moment):
            raw.append({
                "kind": "curiosity", "ref": entry["question_id"], "score": float(entry["score"]),
                "action": "world_get", "risk_class": 0, "estimated_cost": "low",
                "summary": f"Investigate locally: {entry['question']}",
                "source": Provenance(source_type="curiosity", source_id=entry["question_id"]),
            })
        goals = self._goals.get().get("goals", {})
        goal_rows = [g for g in goals.values() if g.get("status") in ("active", "blocked")]
        goal_rows.sort(key=lambda g: (0 if g["status"] == "blocked" else 1,
                                      int(g.get("priority", 5)), g["goal_id"]))
        for goal in goal_rows:
            raw.append({
                "kind": "goal", "ref": goal["goal_id"],
                "score": 0.9 if goal["status"] == "blocked" else 0.8,
                "action": "goal_update", "risk_class": 2, "estimated_cost": "low",
                "summary": f"Advance goal: {goal['title']} — {goal['next_action']}",
                "source": Provenance(source_type="goal", source_id=goal["goal_id"]),
            })
        seen: set[tuple[str, str]] = set()
        deduped: list[dict[str, Any]] = []
        for candidate in sorted(raw, key=lambda c: (-c["score"], c["action"], c["ref"])):
            key = (candidate["action"], _normalize(candidate["summary"]))
            if key in seen:
                continue
            seen.add(key)
            candidate["proposal"] = ActionProposal(
                proposal_id=str(uuid.uuid4()), owner_entity_id=owner,
                action=candidate["action"], summary=candidate["summary"][:1000],
                risk_class=candidate["risk_class"], estimated_cost=candidate["estimated_cost"],
                source=candidate["source"], created_at=_fmt(moment),
                drive_ref=candidate["ref"] if candidate["kind"] == "drive" else "",
                expires_at=expires,
            )
            deduped.append(candidate)
        return deduped

    # -- steps 12-13: execution + verification -------------------------------
    def _execute(self, candidate: dict[str, Any], proposal: ActionProposal,
                 owner: str) -> tuple[ActionResult, bool]:
        executor = self._executors.get(proposal.action)
        if executor is None:
            return ActionResult(
                result_id=str(uuid.uuid4()), proposal_id=proposal.proposal_id,
                owner_entity_id=owner, status="skipped",
                summary="No executor is registered for this action; allowed but not executed.",
                source=Provenance(source_type="tool_result", source_id="agency_cycle"),
                completed_at=_fmt(_now_dt()),
            ), False
        try:
            status, summary = executor(proposal, candidate)
            if status not in ("succeeded", "failed"):
                status, summary = "failed", "Executor returned an invalid status."
        except Exception as exc:  # an executor failure is a cycle fact, not a crash
            status, summary = "failed", f"Executor raised {type(exc).__name__}."
        return ActionResult(
            result_id=str(uuid.uuid4()), proposal_id=proposal.proposal_id,
            owner_entity_id=owner, status=status, summary=str(summary)[:1000],
            source=Provenance(source_type="tool_result", source_id="agency_cycle"),
            completed_at=_fmt(_now_dt()),
        ), status == "succeeded"

    def _execute_world_get(self, proposal: ActionProposal,
                           candidate: dict[str, Any]) -> tuple[str, str]:
        """Read-only local inspection, verified by a consistent re-read."""
        claims_before = len(self._self_model.claims())
        goals_before = self._goals.get().get("goals", {})
        claims_after = len(self._self_model.claims())
        goals_after = self._goals.get().get("goals", {})
        if claims_before != claims_after or set(goals_before) != set(goals_after):
            return "failed", "Local inspection re-read was inconsistent."
        return "succeeded", (
            f"Local inspection verified: {claims_after} self-model claims and "
            f"{len(goals_after)} goals readable."
        )

    # -- step 16: feedback -----------------------------------------------------
    def _feed_back(self, candidate: dict[str, Any], cycle_id: str, moment: datetime) -> None:
        try:
            if candidate["kind"] == "drive":
                self._drives.record_signal(
                    candidate["ref"], "satisfy",
                    source=Provenance(source_type="tool_result", source_id=cycle_id),
                    now=moment,
                )
            elif candidate["kind"] == "curiosity":
                self._curiosity.record_attempt(candidate["ref"], now=moment)
        except (DriveError, CuriosityError, IdentityError, OSError):
            return

    # -- step 15: metacognition -------------------------------------------------
    def _reflect(self, owner: str, cycle_id: str, intent_id: str,
                 counts: dict[str, int], moment: datetime) -> str:
        record = ReflectionRecord(
            reflection_id=str(uuid.uuid4()), owner_entity_id=owner,
            trigger="significant_autonomous_action",
            subject_ref=intent_id or cycle_id,
            observed_outcome="success",
            source=Provenance(source_type="tool_result", source_id=cycle_id),
            created_at=_fmt(moment),
            lessons=(f"Agency cycle executed {counts['executed']} local action(s) "
                     f"under the autonomy gate and verified the results.",),
        )
        try:
            self._metacognition.ensure()
            self._metacognition.record_reflection(record)
        except (MetacognitionError, IdentityError, OSError):
            return ""
        return record.reflection_id

    # -- step 14: journal ---------------------------------------------------------
    @staticmethod
    def _journal_record(cycle_id, owner, trigger, status, started, ended,
                        continuity_health, goal_id, intent_id, counts,
                        verification, reflection_id) -> dict[str, Any]:
        return {
            "journal_version": AGENCY_JOURNAL_VERSION,
            "cycle_id": cycle_id, "owner_entity_id": owner, "trigger": trigger,
            "status": status, "started_at": _fmt(started), "ended_at": _fmt(ended),
            "continuity_health": continuity_health, "selected_goal_id": goal_id,
            "selected_intent_id": intent_id,
            "actions_proposed": counts["proposed"], "actions_allowed": counts["allow"],
            "actions_confirmation": counts["confirmation"],
            "actions_denied": counts["deny"], "actions_executed": counts["executed"],
            "actions_failed": counts["failed"], "actions_skipped": counts["skipped"],
            "verification": verification, "reflection_id": reflection_id,
        }

    def _append_journal(self, record: dict[str, Any]) -> None:
        path = self.journal_path()
        if path.is_symlink():
            raise AgencyError("agency journal must not be a symbolic link")
        lock_path = path.with_suffix(path.suffix + ".lock")
        mkdir_under_hermes_home(lock_path.parent)
        with lock_path.open("a+b") as lock:
            lock.seek(0, os.SEEK_END)
            if lock.tell() == 0:
                lock.write(b"\0")
                lock.flush()
            lock.seek(0)
            if fcntl is not None:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            elif msvcrt is not None:
                msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            try:
                if path.exists() and path.stat().st_size > MAX_JOURNAL_BYTES:
                    raise AgencyError("agency journal exceeds its size limit")
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                lines = path.read_text(encoding="utf-8").splitlines()
                limit = self._journal_limit()
                if len(lines) > limit:
                    tmp = path.with_suffix(path.suffix + ".tmp")
                    tmp.write_text("\n".join(lines[-limit:]) + "\n", encoding="utf-8")
                    os.replace(tmp, path)
            finally:
                lock.seek(0)
                if fcntl is not None:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                elif msvcrt is not None:
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)

    def journal(self, *, limit: int = 20) -> list[dict[str, Any]]:
        """Strictly parsed recent journal records, oldest first."""
        owner = self._identity.read().entity_id
        path = self.journal_path()
        if path.is_symlink():
            raise AgencyError("agency journal must not be a symbolic link")
        if not path.is_file():
            return []
        if path.stat().st_size > MAX_JOURNAL_BYTES:
            raise AgencyError("agency journal exceeds its size limit")
        records: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except ValueError as exc:
                raise AgencyError("agency journal is malformed") from exc
            if not isinstance(payload, dict) or set(payload) != _JOURNAL_FIELDS:
                raise AgencyError("agency journal record fields are invalid")
            if payload.get("journal_version") != AGENCY_JOURNAL_VERSION:
                raise AgencyError("agency journal version is unsupported")
            if payload.get("owner_entity_id") != owner:
                raise AgencyError("agency journal owner does not match entity identity")
            records.append(payload)
        return records[-max(1, min(500, limit)):]

    @staticmethod
    def _report(cycle_id, owner, status, started, ended, source, counts) -> AgencyCycleReport:
        return AgencyCycleReport(
            cycle_id=cycle_id, owner_entity_id=owner, status=status,
            started_at=_fmt(started), finished_at=_fmt(ended), source=source,
            proposals_considered=counts["proposed"], decisions_allow=counts["allow"],
            decisions_confirmation=counts["confirmation"], decisions_deny=counts["deny"],
            actions_executed=counts["executed"], actions_failed=counts["failed"],
        )


class AgencyBridge:
    """Offer the last cycle's content-free status to the packet.

    The bridge never runs a cycle: cycles are invoked explicitly
    (operator / cron routine), never from a session hook.
    """

    def __init__(self, ctx) -> None:
        self._orchestrator = AgencyOrchestrator(ctx)

    def hooks(self):
        return ()

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not self._orchestrator.enabled():
            return []
        try:
            records = self._orchestrator.journal(limit=1)
        except (IdentityError, AgencyError, OSError):
            return []
        if not records:
            return []
        last = records[-1]
        if last["status"] == "completed" and not last["actions_executed"]:
            return []
        return [ContextItem(
            section="current_state",
            content=(
                f"Agency: last cycle {last['status']} — {last['actions_executed']} executed, "
                f"{last['actions_failed']} failed, verification {last['verification']}"
            ),
            source="agency",
            record_id=last["cycle_id"],
            priority=0.5,
            updated_at=_parse(last["ended_at"]).timestamp(),
        )]


__all__ = [
    "AGENCY_JOURNAL_VERSION", "DEFAULT_JOURNAL_PATH", "EXECUTOR_ACTIONS",
    "AgencyError", "AgencyOrchestrator", "AgencyBridge",
]
