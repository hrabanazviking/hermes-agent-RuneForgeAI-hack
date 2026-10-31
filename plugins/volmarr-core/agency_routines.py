"""Proposal-only agency routine (Emergent Agency Phase 7, roadmap §14).

Before the entity receives meaningful action authority, it runs for an
extended evaluation period in proposal-only mode. This module is that
mode:

- **Disabled by default.** ``agency_routine_enabled`` defaults to
  false; nothing here runs, installs, or contributes to the packet
  unless an operator explicitly enables it.
- **Installed only explicitly, paused by default.** The Hermes cron
  job (``Volmarr Agency Review``, every 360 minutes — the agency
  timescale of roadmap §19, less frequent than the heartbeat) is
  created only by the explicit ``hermes volmarr agency install``
  operator action, through the existing :class:`RoutineManager`
  surface, and is created paused. No bridge hook installs anything.
- **One cycle per invocation, bounded.** One ``run_once`` call
  collects at most ``agency_routine_max_proposals`` proposals, makes
  zero model calls (``agency_routine_max_model_calls`` is a hard cap
  this deterministic implementation never spends), and stops
  collecting when its runtime budget
  (``agency_routine_max_runtime_seconds``) is exhausted.
- **Local-first and non-destructive.** Candidates are read from the
  local stores only (drives, curiosity frontier, goals, self-model).
  The routine writes exactly one thing: its own bounded proposals
  log. It never executes an action, never calls the agency
  orchestrator's executors, never records an autonomy result, never
  satisfies a drive, never records a curiosity attempt, and never
  creates or updates a goal.

Proposal kinds (roadmap §14): ``intrinsic_goal`` (from drive intent
proposals), ``research_question`` (from the curiosity frontier),
``maintenance_task`` (from blocked goals), ``project_improvement``
(from active goals), and ``self_improvement_experiment`` (from
low-confidence limitation/uncertainty self-model claims).

Repetition is measured, not assumed: every proposal carries a
deterministic fingerprint (kind + normalised summary); a proposal
whose fingerprint already appears in the log is suppressed and
counted, so the §14 evaluation questions (useful? repetitive? stable
direction or churn?) have real numbers in :meth:`evaluation`.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home, mkdir_under_hermes_home

from .context_packet import ContextItem
from .curiosity import CuriosityStore
from .drives import DriveStore
from .goals import GoalStore
from .identity import IdentityError, IdentityStore, _as_bool
from .routines import RoutineManager
from .self_model import SelfModelStore

AGENCY_ROUTINE_NAME = "Volmarr Agency Review"
AGENCY_ROUTINE_SCHEDULE = "every 360m"
AGENCY_ROUTINE_SCRIPT_NAME = "volmarr_agency_review.py"
PROPOSALS_VERSION = 1
DEFAULT_LOG_PATH = Path("entity") / "agency_proposals.jsonl"
DEFAULT_LOG_LIMIT = 200
MAX_LOG_BYTES = 4 * 1024 * 1024
DEFAULT_MAX_PROPOSALS = 5
DEFAULT_MAX_MODEL_CALLS = 0
DEFAULT_MAX_RUNTIME_SECONDS = 60

PROPOSAL_KINDS = frozenset({
    "intrinsic_goal", "research_question", "maintenance_task",
    "project_improvement", "self_improvement_experiment",
})

_LOG_FIELDS = {
    "proposals_version", "run_id", "owner_entity_id", "trigger", "status",
    "started_at", "ended_at", "proposals", "duplicates_suppressed",
    "candidates_considered", "model_calls_used", "truncated",
}
_PROPOSAL_FIELDS = {"proposal_id", "kind", "summary", "source_ref", "score", "fingerprint"}

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


class AgencyRoutineError(RuntimeError):
    """The agency routine cannot be safely run or its log read."""


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def proposal_fingerprint(kind: str, summary: str) -> str:
    return hashlib.sha256(f"{kind}\n{_normalize(summary)}".encode("utf-8")).hexdigest()


def _script_content() -> str:
    return '''"""Generated entrypoint for the Volmarr Agency Review routine."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def _hermes_executable() -> str | None:
    discovered = shutil.which("hermes")
    if discovered:
        return discovered
    suffix = ".exe" if sys.platform == "win32" else ""
    sibling = Path(sys.executable).with_name(f"hermes{suffix}")
    return str(sibling) if sibling.is_file() else None


def main() -> int:
    executable = _hermes_executable()
    if executable is None:
        print("Hermes executable was not found for the agency routine.", file=sys.stderr)
        return 1
    try:
        completed = subprocess.run(
            [executable, "volmarr", "agency", "run", "--json"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"Agency routine failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    if completed.returncode:
        detail = (completed.stderr or completed.stdout or "routine failed").strip()[:2000]
        print(detail, file=sys.stderr)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
'''


class AgencyRoutineManager(RoutineManager):
    """The Agency Review cron definition (explicit install, paused)."""

    def __init__(self, ctx) -> None:
        super().__init__(
            ctx,
            name=AGENCY_ROUTINE_NAME,
            schedule=AGENCY_ROUTINE_SCHEDULE,
            script_name=AGENCY_ROUTINE_SCRIPT_NAME,
            script_content=_script_content(),
        )


@dataclass(frozen=True)
class AgencyRoutineReport:
    run_id: str
    owner_entity_id: str
    status: str
    started_at: str
    ended_at: str
    proposals: tuple[dict[str, Any], ...]
    duplicates_suppressed: int
    candidates_considered: int
    model_calls_used: int
    truncated: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class AgencyRoutineService:
    """Collect one bounded batch of proposals; execute nothing."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)
        self._drives = DriveStore(ctx)
        self._curiosity = CuriosityStore(ctx)
        self._goals = GoalStore(ctx)
        self._self_model = SelfModelStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("agency_routine_enabled", False), False
        )

    def _max_proposals(self) -> int:
        try:
            value = int(self._ctx.get_config(
                "agency_routine_max_proposals", DEFAULT_MAX_PROPOSALS))
        except (TypeError, ValueError):
            value = DEFAULT_MAX_PROPOSALS
        return min(20, max(1, value))

    def _max_model_calls(self) -> int:
        try:
            value = int(self._ctx.get_config(
                "agency_routine_max_model_calls", DEFAULT_MAX_MODEL_CALLS))
        except (TypeError, ValueError):
            value = DEFAULT_MAX_MODEL_CALLS
        return min(5, max(0, value))

    def _max_runtime_seconds(self) -> float:
        try:
            value = float(self._ctx.get_config(
                "agency_routine_max_runtime_seconds", DEFAULT_MAX_RUNTIME_SECONDS))
        except (TypeError, ValueError):
            value = float(DEFAULT_MAX_RUNTIME_SECONDS)
        return min(300.0, max(5.0, value))

    def _log_limit(self) -> int:
        try:
            value = int(self._ctx.get_config(
                "agency_routine_log_limit", DEFAULT_LOG_LIMIT))
        except (TypeError, ValueError):
            value = DEFAULT_LOG_LIMIT
        return min(500, max(10, value))

    def log_path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(
            "agency_routine_log_path", str(DEFAULT_LOG_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_LOG_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_LOG_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise AgencyRoutineError(
                "agency routine log path resolves outside the active profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    # -- the proposal-only run -------------------------------------------
    def run_once(self, trigger: str = "scheduled", *,
                 now: datetime | None = None) -> AgencyRoutineReport:
        if not isinstance(trigger, str) or not re.fullmatch(
                r"[a-z0-9][a-z0-9_-]*", trigger):
            raise AgencyRoutineError("agency routine trigger is invalid")
        if not self.enabled():
            raise AgencyRoutineError("agency routine is disabled")
        # Model-call bound: this deterministic routine spends none, so
        # a configured cap can never be exceeded; the field is reported
        # honestly in every run record.
        if self._max_model_calls() < 0:  # pragma: no cover - clamped above
            raise AgencyRoutineError("agency routine model-call cap is invalid")
        started = now or _now_dt()
        clock_start = time.monotonic()
        run_id = str(uuid.uuid4())
        owner = self._identity.ensure().entity_id

        seen = {
            proposal["fingerprint"]
            for record in self.log()
            for proposal in record["proposals"]
        }
        candidates = self._candidates(owner, started)
        proposals: list[dict[str, Any]] = []
        duplicates = 0
        truncated = False
        for candidate in candidates:
            if len(proposals) >= self._max_proposals():
                truncated = True
                break
            if time.monotonic() - clock_start > self._max_runtime_seconds():
                truncated = True
                break
            fingerprint = proposal_fingerprint(candidate["kind"], candidate["summary"])
            if fingerprint in seen:
                duplicates += 1
                continue
            seen.add(fingerprint)
            proposals.append({
                "proposal_id": str(uuid.uuid4()),
                "kind": candidate["kind"],
                "summary": candidate["summary"][:1000],
                "source_ref": candidate["source_ref"],
                "score": round(float(candidate["score"]), 6),
                "fingerprint": fingerprint,
            })
        ended = _now_dt() if now is None else started
        record = {
            "proposals_version": PROPOSALS_VERSION,
            "run_id": run_id, "owner_entity_id": owner, "trigger": trigger,
            "status": "completed", "started_at": _fmt(started),
            "ended_at": _fmt(ended), "proposals": proposals,
            "duplicates_suppressed": duplicates,
            "candidates_considered": len(candidates),
            "model_calls_used": 0, "truncated": truncated,
        }
        self._append_log(record)
        return AgencyRoutineReport(
            run_id=run_id, owner_entity_id=owner, status="completed",
            started_at=_fmt(started), ended_at=_fmt(ended),
            proposals=tuple(proposals), duplicates_suppressed=duplicates,
            candidates_considered=len(candidates), model_calls_used=0,
            truncated=truncated,
        )

    def _candidates(self, owner: str, moment: datetime) -> list[dict[str, Any]]:
        raw: list[dict[str, Any]] = []
        self._drives.ensure()
        for proposal in self._drives.proposals(now=moment):
            raw.append({
                "kind": "intrinsic_goal", "source_ref": proposal["drive"],
                "score": float(proposal["expected_value"]),
                "summary": proposal["proposal"],
            })
        self._curiosity.ensure()
        for entry in self._curiosity.frontier(now=moment):
            raw.append({
                "kind": "research_question", "source_ref": entry["question_id"],
                "score": float(entry["score"]),
                "summary": f"Investigate locally: {entry['question']}",
            })
        self._goals.ensure()
        goals = self._goals.get().get("goals", {})
        goal_rows = [g for g in goals.values() if g.get("status") in ("active", "blocked")]
        goal_rows.sort(key=lambda g: (0 if g["status"] == "blocked" else 1,
                                      int(g.get("priority", 5)), g["goal_id"]))
        for goal in goal_rows:
            blocked = goal["status"] == "blocked"
            raw.append({
                "kind": "maintenance_task" if blocked else "project_improvement",
                "source_ref": goal["goal_id"],
                "score": 0.9 if blocked else 0.8,
                "summary": f"Advance goal: {goal['title']} — {goal['next_action']}",
            })
        self._self_model.ensure()
        claims = [
            claim for claim in self._self_model.claims()
            if claim.domain in ("limitation", "uncertainty")
        ]
        claims.sort(key=lambda c: (c.confidence, c.domain, c.key))
        for claim in claims:
            raw.append({
                "kind": "self_improvement_experiment",
                "source_ref": claim.claim_id,
                "score": round(1.0 - float(claim.confidence), 6),
                "summary": (
                    f"Test the {claim.domain} claim '{claim.key}': {claim.statement}"
                ),
            })
        raw.sort(key=lambda c: (-c["score"], c["kind"], c["source_ref"]))
        return raw

    # -- evaluation (roadmap §14 questions, as counts) ---------------------
    def evaluation(self) -> dict[str, Any]:
        records = self.log()
        per_kind: dict[str, int] = {kind: 0 for kind in sorted(PROPOSAL_KINDS)}
        total = 0
        for record in records:
            for proposal in record["proposals"]:
                per_kind[proposal["kind"]] += 1
                total += 1
        suppressed = sum(r["duplicates_suppressed"] for r in records)
        considered = sum(r["candidates_considered"] for r in records)
        return {
            "runs": len(records),
            "proposals_total": total,
            "proposals_per_kind": per_kind,
            "duplicates_suppressed": suppressed,
            "candidates_considered": considered,
            "repetition_rate": (
                round(suppressed / considered, 6) if considered else 0.0
            ),
            "last_run_at": records[-1]["ended_at"] if records else "",
            "model_calls_used_total": sum(r["model_calls_used"] for r in records),
        }

    # -- the bounded log -----------------------------------------------------
    def _append_log(self, record: dict[str, Any]) -> None:
        path = self.log_path()
        if path.is_symlink():
            raise AgencyRoutineError("agency routine log must not be a symbolic link")
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
                    raise AgencyRoutineError("agency routine log exceeds its size limit")
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                lines = path.read_text(encoding="utf-8").splitlines()
                limit = self._log_limit()
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

    def log(self, *, limit: int = 500) -> list[dict[str, Any]]:
        """Strictly parsed log records, oldest first."""
        owner = self._identity.read().entity_id
        path = self.log_path()
        if path.is_symlink():
            raise AgencyRoutineError("agency routine log must not be a symbolic link")
        if not path.is_file():
            return []
        if path.stat().st_size > MAX_LOG_BYTES:
            raise AgencyRoutineError("agency routine log exceeds its size limit")
        records: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except ValueError as exc:
                raise AgencyRoutineError("agency routine log is malformed") from exc
            if not isinstance(payload, dict) or set(payload) != _LOG_FIELDS:
                raise AgencyRoutineError("agency routine log record fields are invalid")
            if payload.get("proposals_version") != PROPOSALS_VERSION:
                raise AgencyRoutineError("agency routine log version is unsupported")
            if payload.get("owner_entity_id") != owner:
                raise AgencyRoutineError(
                    "agency routine log owner does not match entity identity")
            proposals = payload.get("proposals")
            if not isinstance(proposals, list) or len(proposals) > 20:
                raise AgencyRoutineError("agency routine log proposals are invalid")
            for proposal in proposals:
                if not isinstance(proposal, dict) or set(proposal) != _PROPOSAL_FIELDS:
                    raise AgencyRoutineError("agency routine proposal fields are invalid")
                if proposal["kind"] not in PROPOSAL_KINDS:
                    raise AgencyRoutineError("agency routine proposal kind is invalid")
                if proposal["fingerprint"] != proposal_fingerprint(
                        proposal["kind"], proposal["summary"]):
                    raise AgencyRoutineError("agency routine proposal fingerprint is invalid")
            records.append(payload)
        return records[-max(1, min(500, limit)):]


class AgencyRoutineBridge:
    """Offer the last proposal batch's counts to the packet.

    The bridge never runs the routine and never installs it: runs are
    invoked explicitly (operator / the paused-by-default cron job),
    never from a session hook.
    """

    def __init__(self, ctx) -> None:
        self._service = AgencyRoutineService(ctx)

    def hooks(self):
        return ()

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not self._service.enabled():
            return []
        try:
            records = self._service.log(limit=1)
        except (IdentityError, AgencyRoutineError, OSError):
            return []
        if not records or not records[-1]["proposals"]:
            return []
        last = records[-1]
        kinds: dict[str, int] = {}
        for proposal in last["proposals"]:
            kinds[proposal["kind"]] = kinds.get(proposal["kind"], 0) + 1
        detail = ", ".join(f"{count} {kind}" for kind, count in sorted(kinds.items()))
        return [ContextItem(
            section="current_state",
            content=(
                f"Agency review: {len(last['proposals'])} proposal(s) awaiting review "
                f"({detail}); {last['duplicates_suppressed']} duplicate(s) suppressed; "
                "nothing was executed"
            ),
            source="agency_routine",
            record_id=last["run_id"],
            priority=0.5,
            updated_at=_parse(last["ended_at"]).timestamp(),
        )]


__all__ = [
    "AGENCY_ROUTINE_NAME", "AGENCY_ROUTINE_SCHEDULE", "AGENCY_ROUTINE_SCRIPT_NAME",
    "PROPOSALS_VERSION", "DEFAULT_LOG_PATH", "PROPOSAL_KINDS",
    "AgencyRoutineError", "AgencyRoutineManager", "AgencyRoutineReport",
    "AgencyRoutineService", "AgencyRoutineBridge", "proposal_fingerprint",
]
