"""Limited local autonomy (Emergent Agency Phase 8, roadmap §15).

Once proposal quality is proven (Phase 7), a narrow set of Class 0
and Class 1 local actions may run through the Phase 5 autonomy gate
and the Phase 6 orchestrator's executor surface. The roadmap's core
rule for this phase:

    The AI can choose when to think and what to inspect —
    not change anything it wants.

The registry below is the whole of that authority. Every action is
local to the active profile: read-only inspections of the entity's
own stores, bounded private records inside the profile, the
self-model's own merge layer, and the non-destructive consolidation
checkpoint. Nothing here touches the network, another profile, a
credential, the autonomy policy, canonical identity, or any file
outside the profile's entity stores.

``run_local_tests`` is registered (Class 1) so the gate can classify
it, but it has NO built-in executor: running the pytest suite from
inside an agency cycle would be recursive and unbounded, so it stays
caller-injected (operator/test harness) and an allowed proposal for
it is recorded ``skipped`` — never as executed. The full test suite
remains an operator action via ``scripts/run_tests.sh``.

``prepare_suggested_patch`` prepares a suggestion record only; it
applies nothing, ever.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from hermes_constants import get_hermes_home, mkdir_under_hermes_home

from .agency_contracts import ActionProposal, ActionResult, Provenance
from .autonomy import AutonomyStore
from .consolidation import ConsolidationError, ConsolidationService
from .context_packet import ContextItem
from .curiosity import CuriosityStore
from .goals import GoalStore
from .heartbeat import HeartbeatError, HeartbeatStore
from .identity import IdentityError, IdentityStore, _as_bool
from .metacognition import MetacognitionStore
from .self_model import SelfModelError, SelfModelStore

LOCAL_AUTONOMY_LOG_VERSION = 1
DEFAULT_LOG_PATH = Path("entity") / "local_actions.jsonl"
DEFAULT_LOG_LIMIT = 200
MAX_LOG_BYTES = 4 * 1024 * 1024

# The §15 registry: action -> risk class (0 or 1 only, by design).
LOCAL_AUTONOMY_ACTIONS: dict[str, int] = {
    "inspect_project_state": 0,
    "check_health": 0,
    "inspect_memory_integrity": 0,
    "local_readonly_research": 0,
    "run_local_tests": 1,
    "generate_private_report": 1,
    "organize_curiosity_queue": 1,
    "update_self_model_evidence": 1,
    "run_consolidation": 1,
    "prepare_suggested_patch": 1,
}

# Actions with a built-in executor. ``run_local_tests`` is absent on
# purpose (see the module docstring).
BUILTIN_EXECUTOR_ACTIONS = frozenset(
    action for action in LOCAL_AUTONOMY_ACTIONS if action != "run_local_tests"
)

_LOG_FIELDS = {
    "log_version", "record_id", "owner_entity_id", "kind", "action",
    "summary", "detail", "created_at",
}
_LOG_KINDS = frozenset({"report", "suggested_patch"})

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


class LocalAutonomyError(RuntimeError):
    """A local-autonomy action cannot be safely run or logged."""


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) > 2}


Executor = Callable[[ActionProposal, dict[str, Any]], tuple[str, str]]


class LocalActionLog:
    """Bounded profile-local log for reports and suggested patches."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def _limit(self) -> int:
        try:
            value = int(self._ctx.get_config("local_autonomy_log_limit", DEFAULT_LOG_LIMIT))
        except (TypeError, ValueError):
            value = DEFAULT_LOG_LIMIT
        return min(500, max(10, value))

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(
            "local_autonomy_log_path", str(DEFAULT_LOG_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_LOG_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_LOG_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise LocalAutonomyError("local action log path resolves outside the active profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    def append(self, *, kind: str, action: str, summary: str,
               detail: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
        if kind not in _LOG_KINDS:
            raise LocalAutonomyError("local action log kind is invalid")
        owner = self._identity.read().entity_id
        clean_detail: dict[str, Any] = {}
        for key, value in detail.items():
            if not isinstance(key, str) or not re.fullmatch(r"[a-z0-9_]+", key):
                raise LocalAutonomyError("local action log detail key is invalid")
            if isinstance(value, bool) or not isinstance(value, (int, str)):
                raise LocalAutonomyError("local action log detail value is invalid")
            clean_detail[key] = value if isinstance(value, int) else value[:200]
        record = {
            "log_version": LOCAL_AUTONOMY_LOG_VERSION,
            "record_id": str(uuid.uuid4()),
            "owner_entity_id": owner,
            "kind": kind,
            "action": action,
            "summary": summary[:500],
            "detail": clean_detail,
            "created_at": _fmt(now or _now_dt()),
        }
        path = self.path()
        if path.is_symlink():
            raise LocalAutonomyError("local action log must not be a symbolic link")
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
                if path.exists() and path.stat().st_size > MAX_LOG_BYTES:
                    raise LocalAutonomyError("local action log exceeds its size limit")
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                lines = path.read_text(encoding="utf-8").splitlines()
                limit = self._limit()
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
        return record

    def records(self, *, limit: int = 20) -> list[dict[str, Any]]:
        owner = self._identity.read().entity_id
        path = self.path()
        if path.is_symlink():
            raise LocalAutonomyError("local action log must not be a symbolic link")
        if not path.is_file():
            return []
        if path.stat().st_size > MAX_LOG_BYTES:
            raise LocalAutonomyError("local action log exceeds its size limit")
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except ValueError as exc:
                raise LocalAutonomyError("local action log is malformed") from exc
            if not isinstance(payload, dict) or set(payload) != _LOG_FIELDS:
                raise LocalAutonomyError("local action log record fields are invalid")
            if payload.get("log_version") != LOCAL_AUTONOMY_LOG_VERSION:
                raise LocalAutonomyError("local action log version is unsupported")
            if payload.get("owner_entity_id") != owner:
                raise LocalAutonomyError("local action log owner does not match entity identity")
            if payload.get("kind") not in _LOG_KINDS:
                raise LocalAutonomyError("local action log kind is invalid")
            out.append(payload)
        return out[-max(1, min(500, limit)):]


class LocalAutonomyExecutors:
    """Built-in executors for the §15 local actions.

    Each executor takes ``(proposal, candidate)`` and returns
    ``(status, summary)`` with status ``succeeded``/``failed`` — the
    agency orchestrator's executor shape. Candidate keys:
    ``evidence`` ({domain, key, outcome}) for
    ``update_self_model_evidence`` and ``question`` for
    ``local_readonly_research``; other actions need none.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._self_model = SelfModelStore(ctx)
        self._goals = GoalStore(ctx)
        self._curiosity = CuriosityStore(ctx)
        self._metacognition = MetacognitionStore(ctx)
        self._heartbeat = HeartbeatStore(ctx)
        self._log = LocalActionLog(ctx)

    def executors(self) -> dict[str, Executor]:
        return {
            "inspect_project_state": self._inspect_project_state,
            "check_health": self._check_health,
            "inspect_memory_integrity": self._inspect_memory_integrity,
            "local_readonly_research": self._local_readonly_research,
            "generate_private_report": self._generate_private_report,
            "organize_curiosity_queue": self._organize_curiosity_queue,
            "update_self_model_evidence": self._update_self_model_evidence,
            "run_consolidation": self._run_consolidation,
            "prepare_suggested_patch": self._prepare_suggested_patch,
        }

    # -- Class 0: read-only inspections --------------------------------
    def _inspect_project_state(self, proposal, candidate):
        goals_before = self._goals.get().get("goals", {})
        claims_before = len(self._self_model.claims())
        goals_after = self._goals.get().get("goals", {})
        claims_after = len(self._self_model.claims())
        if set(goals_before) != set(goals_after) or claims_before != claims_after:
            return "failed", "Project-state inspection re-read was inconsistent."
        active = sum(1 for g in goals_after.values() if g.get("status") == "active")
        blocked = sum(1 for g in goals_after.values() if g.get("status") == "blocked")
        return "succeeded", (
            f"Project state inspected: {len(goals_after)} goals "
            f"({active} active, {blocked} blocked), {claims_after} self-model claims."
        )

    def _check_health(self, proposal, candidate):
        try:
            data = self._heartbeat.read()
            heartbeat = f"sequence {data.get('heartbeat_sequence', 0)}"
        except (IdentityError, HeartbeatError, OSError):
            heartbeat = "unavailable"
        claims = len(self._self_model.claims())
        return "succeeded", f"Health checked locally: heartbeat {heartbeat}; {claims} claims readable."

    def _inspect_memory_integrity(self, proposal, candidate):
        claims = self._self_model.claims()
        goals = self._goals.get().get("goals", {})
        questions = self._curiosity.questions()
        summary = self._metacognition.summary()
        if not isinstance(summary, dict):
            return "failed", "Metacognition summary did not parse during integrity inspection."
        return "succeeded", (
            f"Memory integrity verified: {len(claims)} claims, {len(goals)} goals, "
            f"{len(questions)} curiosity questions, metacognition summary readable."
        )

    def _local_readonly_research(self, proposal, candidate):
        question = str(candidate.get("question") or proposal.summary or "")
        wanted = _tokens(question)
        claim_hits = sum(
            1 for claim in self._self_model.claims()
            if wanted & _tokens(f"{claim.domain} {claim.key} {claim.statement}")
        )
        goal_hits = sum(
            1 for goal in self._goals.get().get("goals", {}).values()
            if wanted & _tokens(f"{goal.get('title', '')} {goal.get('description', '')}")
        )
        question_hits = sum(
            1 for item in self._curiosity.questions()
            if wanted & _tokens(item.question)
        )
        return "succeeded", (
            f"Local read-only research: {claim_hits} self-model, {goal_hits} goal, "
            f"{question_hits} curiosity matches in local stores; nothing external consulted."
        )

    # -- Class 1: bounded profile-local effects --------------------------
    def _generate_private_report(self, proposal, candidate):
        goals = self._goals.get().get("goals", {})
        detail = {
            "goals_total": len(goals),
            "goals_active": sum(1 for g in goals.values() if g.get("status") == "active"),
            "goals_blocked": sum(1 for g in goals.values() if g.get("status") == "blocked"),
            "claims_total": len(self._self_model.claims()),
            "curiosity_total": len(self._curiosity.questions()),
        }
        self._log.append(kind="report", action=proposal.action,
                         summary="Private local-autonomy report (counts only).", detail=detail)
        return "succeeded", (
            f"Private report generated in the profile-local log: {detail['goals_total']} goals, "
            f"{detail['claims_total']} claims, {detail['curiosity_total']} curiosity questions."
        )

    def _organize_curiosity_queue(self, proposal, candidate):
        frontier = self._curiosity.frontier()
        total = len(self._curiosity.questions())
        top = frontier[0]["question_id"] if frontier else "none"
        return "succeeded", (
            f"Curiosity queue organised deterministically: {len(frontier)} frontier "
            f"question(s) of {total} total; top {top}."
        )

    def _update_self_model_evidence(self, proposal, candidate):
        evidence = candidate.get("evidence")
        if not isinstance(evidence, dict):
            return "failed", "No evidence candidate was supplied; self-model unchanged."
        domain = evidence.get("domain")
        key = evidence.get("key")
        outcome = evidence.get("outcome")
        if not all(isinstance(v, str) and v for v in (domain, key, outcome)):
            return "failed", "Evidence candidate is incomplete; self-model unchanged."
        try:
            claim = self._self_model.apply_evidence(
                domain, key, outcome=outcome, source=proposal.source)
        except SelfModelError as exc:
            if "not found" in str(exc):
                return "succeeded", (
                    "Self-model merge layer skipped the evidence: claim not found; "
                    "no claim was created."
                )
            return "failed", f"Self-model merge layer refused the evidence: {exc}"
        return "succeeded", (
            f"Self-model evidence applied by the merge layer: {domain}/{key} "
            f"confidence now {claim.confidence:.2f}."
        )

    def _run_consolidation(self, proposal, candidate):
        try:
            report = ConsolidationService(self._ctx).run("manual")
        except (ConsolidationError, IdentityError, OSError) as exc:
            return "failed", f"Consolidation did not complete: {type(exc).__name__}."
        if not report.healthy:
            return "failed", "Consolidation reported an unhealthy result."
        return "succeeded", (
            f"Consolidation checkpoint recorded: sequence {report.sequence} "
            f"({report.status})."
        )

    def _prepare_suggested_patch(self, proposal, candidate):
        summary = str(candidate.get("patch_summary") or proposal.summary or "")[:500]
        if not summary:
            return "failed", "No patch suggestion was supplied; nothing prepared."
        self._log.append(kind="suggested_patch", action=proposal.action,
                         summary=summary, detail={"applied": "false"})
        return "succeeded", "Suggested patch prepared as a proposal record only; nothing was applied."


class LocalAutonomyService:
    """Run ONE §15 action through the Phase 5 gate, explicitly.

    No hook, loop, or scheduler lives here: an operator, a routine,
    or the agency orchestrator invokes ``run_action`` and it exits.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)
        self._autonomy = AutonomyStore(ctx)
        self._executors = LocalAutonomyExecutors(ctx).executors()

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("local_autonomy_enabled", True), True
        )

    def run_action(self, action: str, summary: str = "", *,
                   candidate: dict[str, Any] | None = None,
                   now: datetime | None = None) -> dict[str, Any]:
        if action not in LOCAL_AUTONOMY_ACTIONS:
            raise LocalAutonomyError("local autonomy action is not in the Phase 8 registry")
        if not self.enabled():
            raise LocalAutonomyError("local autonomy is disabled")
        moment = now or _now_dt()
        self._autonomy.ensure()
        owner = self._identity.read().entity_id
        proposal = ActionProposal(
            proposal_id=str(uuid.uuid4()), owner_entity_id=owner,
            action=action,
            summary=(summary or f"Local autonomy action: {action}")[:1000],
            risk_class=LOCAL_AUTONOMY_ACTIONS[action], estimated_cost="low",
            source=Provenance(source_type="cognition_telemetry", source_id="local_autonomy"),
            created_at=_fmt(moment),
            expires_at=_fmt(moment + timedelta(hours=1)),
        )
        decision = self._autonomy.evaluate(proposal, now=moment)
        self._autonomy.record_decision(decision)
        outcome: dict[str, Any] = {
            "action": action, "decision": decision.decision,
            "reason_code": decision.reason_code, "status": "not_executed",
            "summary": "",
        }
        if decision.decision != "allow":
            return outcome
        cand = dict(candidate or {})
        cand.setdefault("question", proposal.summary)
        executor = self._executors.get(action)
        if executor is None:
            result = ActionResult(
                result_id=str(uuid.uuid4()), proposal_id=proposal.proposal_id,
                owner_entity_id=owner, status="skipped",
                summary="No built-in executor is registered for this action; allowed but not executed.",
                source=Provenance(source_type="tool_result", source_id="local_autonomy"),
                completed_at=_fmt(_now_dt()),
            )
        else:
            try:
                status, text = executor(proposal, cand)
                if status not in ("succeeded", "failed"):
                    status, text = "failed", "Executor returned an invalid status."
            except Exception as exc:  # an executor failure is a fact, not a crash
                status, text = "failed", f"Executor raised {type(exc).__name__}."
            result = ActionResult(
                result_id=str(uuid.uuid4()), proposal_id=proposal.proposal_id,
                owner_entity_id=owner, status=status, summary=str(text)[:1000],
                source=Provenance(source_type="tool_result", source_id="local_autonomy"),
                completed_at=_fmt(_now_dt()),
            )
        self._autonomy.record_result(result, estimated_cost="low")
        outcome["status"] = result.status
        outcome["summary"] = result.summary
        return outcome


class LocalAutonomyBridge:
    """Surface the last private report / patch suggestion, if any.

    Content-bearing only: a profile that has never generated a
    report or prepared a suggestion contributes nothing.
    """

    def __init__(self, ctx) -> None:
        self._service_ctx = ctx
        self._log = LocalActionLog(ctx)
        self._identity = IdentityStore(ctx)

    def hooks(self):
        return ()

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not _as_bool(self._service_ctx.get_config("local_autonomy_enabled", True), True):
            return []
        try:
            records = self._log.records(limit=1)
        except (IdentityError, LocalAutonomyError, OSError):
            return []
        if not records:
            return []
        last = records[-1]
        label = "Private report" if last["kind"] == "report" else "Suggested patch (not applied)"
        return [ContextItem(
            section="current_state",
            content=f"Local autonomy: {label} — {last['summary']}",
            source="local_autonomy",
            record_id=last["record_id"],
            priority=0.5,
            updated_at=_parse(last["created_at"]).timestamp(),
        )]


__all__ = [
    "LOCAL_AUTONOMY_ACTIONS", "BUILTIN_EXECUTOR_ACTIONS",
    "LOCAL_AUTONOMY_LOG_VERSION", "DEFAULT_LOG_PATH",
    "LocalAutonomyError", "LocalActionLog", "LocalAutonomyExecutors",
    "LocalAutonomyService", "LocalAutonomyBridge",
]
