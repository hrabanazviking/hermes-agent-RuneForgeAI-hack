"""Intrinsic-motivation lifecycle reconciliation (Self-Aware §8).

Emergent Agency Phase 2 (Slice 91) already built the bounded drive
store and Phase 9 (Slice 99) already built durable intrinsic goals
with schema-v2 origin provenance. What neither slice implements is
this roadmap's own §8 layer, which is therefore built here as a
reconciliation, not a second motivation engine:

- §8.2 drive coverage: the twelve suggested drives are mapped
  deterministically onto the drives the existing store actually
  carries — direct, by alias (``creative_expression`` is the store's
  ``creation``, ``resource_stewardship`` its ``stewardship``,
  ``world_understanding`` its ``exploration``), or honestly missing
  (``goal_completion``, ``truthfulness``, ``system_health``,
  ``self_improvement`` have no backing drive yet);
- §8.4 goal provenance: every evaluation carries the full motivation
  block (drive, deterministic tension score, bounded rationale
  summary) beside the goal-ledger origin fields. The ledger's flat
  ``origin`` supports only ``user`` / ``intrinsic`` / ``maintenance``;
  the §8.4 ``relationship`` and ``curiosity`` origin types cannot be
  stored there yet — recorded as an honest gap, not papered over;
- §8.5 intrinsic goal lifecycle: one explicit, deterministic
  evaluation walks a drive intent proposal through drive pressure →
  deduplication → value/identity check → resource check →
  autonomy-policy check and reports ``planned_candidate``,
  ``awaiting_approval``, ``already_exists``, or ``rejected`` with a
  per-stage record.

Evaluation creates no goal, executes nothing, and writes nothing:
only the explicit ``record_evaluation`` appends the evaluation to
this module's own bounded log. Promotion itself remains the
Phase 9 service's explicit call. Disabled by default.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home, mkdir_under_hermes_home

from .autonomy import AutonomyError, AutonomyStore
from .context_packet import ContextItem
from .drives import (
    FORBIDDEN_DRIVES,
    PROPOSAL_TENSION_THRESHOLD,
    STARTER_DRIVES,
    DriveError,
    DriveStore,
    tension_of,
)
from .goals import GoalError, GoalStore
from .identity import IdentityError, IdentityStore, _as_bool
from .intrinsic_goals import (
    NEAR_DUPLICATE_THRESHOLD,
    IntrinsicGoalError,
    IntrinsicGoalService,
    goal_fingerprint,
    title_similarity,
)

LIFECYCLE_VERSION = 1
DEFAULT_LOG_PATH = Path("entity") / "motivation_lifecycle.jsonl"
DEFAULT_LOG_LIMIT = 200
MAX_LOG_BYTES = 4 * 1024 * 1024
MAX_TITLE_CHARS = 200

SECTION8_DRIVES = (
    "continuity", "competence", "curiosity", "coherence",
    "relationship_care", "goal_completion", "truthfulness",
    "system_health", "creative_expression", "self_improvement",
    "world_understanding", "resource_stewardship",
)
DRIVE_ALIASES = {
    "creative_expression": "creation",
    "resource_stewardship": "stewardship",
    "world_understanding": "exploration",
}
_KNOWN_DRIVES = (
    frozenset(SECTION8_DRIVES)
    | frozenset(drive_id for drive_id, _ in STARTER_DRIVES)
    | frozenset(DRIVE_ALIASES.values())
)

STAGES = (
    "drive_pressure", "deduplication", "value_identity_check",
    "resource_check", "autonomy_policy_check",
)
_STAGE_STATUSES = frozenset(
    {"pass", "fail", "awaiting", "duplicate", "unavailable"})
OUTCOMES = frozenset(
    {"planned_candidate", "awaiting_approval", "already_exists", "rejected"})
_LIVE_STATUSES = frozenset({"planned", "active", "blocked"})

_FIELDS = {
    "lifecycle_version", "evaluation_id", "owner_entity_id",
    "evaluated_at", "drive", "title", "motivation", "stages",
    "outcome", "existing_goal_id",
}

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


class MotivationLifecycleError(RuntimeError):
    """A motivation lifecycle evaluation cannot be safely run or read."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _fmt(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _timestamp_ok(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _epoch(value: str) -> float:
    try:
        return _parse(value).timestamp()
    except (ValueError, OverflowError, OSError):
        return 0.0


def _unit(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and 0.0 <= float(value) <= 1.0
    )


def _canonical_uuid(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


class MotivationLifecycleService:
    """§8.2 coverage plus the §8.5 lifecycle evaluation (read-only)."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)
        self._drives = DriveStore(ctx)
        self._goals = GoalStore(ctx)
        self._intrinsic = IntrinsicGoalService(ctx)
        self._autonomy = AutonomyStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("motivation_lifecycle_enabled", False), False
        )

    def _limit(self) -> int:
        try:
            value = int(self._ctx.get_config(
                "motivation_lifecycle_log_limit", DEFAULT_LOG_LIMIT))
        except (TypeError, ValueError):
            value = DEFAULT_LOG_LIMIT
        return min(500, max(10, value))

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(
            "motivation_lifecycle_log_path", str(DEFAULT_LOG_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_LOG_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_LOG_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise MotivationLifecycleError(
                "motivation lifecycle log path resolves outside the profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    # -- §8.2 coverage ---------------------------------------------------
    def coverage(self) -> list[dict[str, Any]]:
        """Map each §8.2 drive onto the existing store, deterministically."""
        try:
            states = {s.drive_id: s for s in self._drives.drives()}
        except (IdentityError, DriveError, OSError):
            states = {}
        rows: list[dict[str, Any]] = []
        for drive_id in SECTION8_DRIVES:
            if drive_id in states:
                backing, status = drive_id, "direct"
            elif DRIVE_ALIASES.get(drive_id) in states:
                backing, status = DRIVE_ALIASES[drive_id], "alias"
            else:
                backing, status = "", "missing"
            state = states.get(backing) if backing else None
            rows.append({
                "section8_drive": drive_id,
                "status": status,
                "backing_drive": backing,
                "activation": state.activation if state else None,
                "tension": tension_of(state) if state else None,
            })
        return rows

    # -- §8.5 lifecycle evaluation -----------------------------------------
    def evaluate(self, proposal: dict[str, Any], *,
                 now: datetime | None = None) -> dict[str, Any]:
        """Walk one intent proposal through the five §8.5 stages.

        Pure and deterministic for identical stored state and clock:
        reads the drive, goal, and autonomy stores and writes nothing.
        The outcome is a *candidate* verdict — creating the goal
        remains the Phase 9 promotion call, and execution/reflection
        remain later lifecycle stages outside this evaluation.
        """
        if not isinstance(proposal, dict):
            raise MotivationLifecycleError("proposal must be a mapping")
        title = proposal.get("title") or proposal.get("proposal") or ""
        if not isinstance(title, str) or not title.strip() \
                or len(title.strip()) > MAX_TITLE_CHARS:
            raise MotivationLifecycleError("proposal title is missing or oversized")
        title = title.strip()
        description = proposal.get("description", "")
        if not isinstance(description, str) or len(description) > 4000:
            raise MotivationLifecycleError("proposal description is invalid")
        drive = proposal.get("drive") or proposal.get("origin_ref") or ""
        if not isinstance(drive, str) or not drive.strip() or len(drive) > 200:
            raise MotivationLifecycleError("proposal drive is missing or invalid")
        drive = drive.strip()
        moment = now or datetime.now(timezone.utc)
        owner = self._identity.read().entity_id
        stages: list[dict[str, str]] = []

        # Stage 1 — drive pressure.
        score = 0.0
        try:
            states = {s.drive_id: s for s in self._drives.drives()}
        except (IdentityError, DriveError, OSError):
            states = None
        if states is None:
            stages.append({"stage": "drive_pressure", "status": "unavailable",
                           "reason": "drive_store_unreadable"})
        else:
            backing = drive if drive in states else DRIVE_ALIASES.get(drive, "")
            state = states.get(backing) if backing else None
            if state is None:
                stages.append({"stage": "drive_pressure", "status": "fail",
                               "reason": "drive_not_in_store"})
            elif not state.enabled:
                stages.append({"stage": "drive_pressure", "status": "fail",
                               "reason": "drive_disabled"})
            else:
                score = tension_of(state)
                if state.cooldown_until and _parse(state.cooldown_until) > moment:
                    stages.append({"stage": "drive_pressure", "status": "fail",
                                   "reason": "drive_in_cooldown"})
                elif score < PROPOSAL_TENSION_THRESHOLD:
                    stages.append({"stage": "drive_pressure", "status": "fail",
                                   "reason": "tension_below_threshold"})
                else:
                    stages.append({"stage": "drive_pressure", "status": "pass",
                                   "reason": "tension_sufficient"})

        # Stage 2 — deduplication (exact, rejected-cooldown, near-duplicate).
        existing_goal_id = ""
        try:
            data = self._goals.get()
            fingerprint = goal_fingerprint(title, description)
            duplicate = None
            for goal in data["goals"].values():
                if goal.get("origin") != "intrinsic" \
                        or goal["status"] == "archived":
                    continue
                if goal_fingerprint(
                        goal["title"], goal.get("description", "")) == fingerprint:
                    duplicate = goal
                    break
            if duplicate is not None:
                existing_goal_id = duplicate["goal_id"]
                stages.append({"stage": "deduplication", "status": "duplicate",
                               "reason": "exact_duplicate_of_live_intrinsic_goal"})
            else:
                rejected = self._goals.rejected_fingerprints()
                entry = rejected.get(fingerprint)
                if entry is not None and _parse(entry["cooldown_until"]) > moment:
                    stages.append({"stage": "deduplication", "status": "fail",
                                   "reason": "rejected_fingerprint_in_cooldown"})
                elif any(
                    other_fp != fingerprint
                    and _parse(other["cooldown_until"]) > moment
                    and title_similarity(title, other["title"])
                    >= NEAR_DUPLICATE_THRESHOLD
                    for other_fp, other in rejected.items()
                ):
                    stages.append({"stage": "deduplication", "status": "fail",
                                   "reason": "near_duplicate_of_rejected_goal"})
                else:
                    stages.append({"stage": "deduplication", "status": "pass",
                                   "reason": "no_duplicate"})
        except (IdentityError, GoalError, OSError):
            stages.append({"stage": "deduplication", "status": "unavailable",
                           "reason": "goal_ledger_unreadable"})

        # Stage 3 — value/identity check.
        if drive in FORBIDDEN_DRIVES:
            stages.append({"stage": "value_identity_check", "status": "fail",
                           "reason": "forbidden_drive"})
        elif drive not in _KNOWN_DRIVES:
            stages.append({"stage": "value_identity_check", "status": "fail",
                           "reason": "unknown_drive"})
        else:
            stages.append({"stage": "value_identity_check", "status": "pass",
                           "reason": "drive_within_bounds"})

        # Stage 4 — resource check (the Phase 9 intrinsic quota).
        try:
            data = self._goals.get()
            live = sum(
                1 for goal in data["goals"].values()
                if goal.get("origin") == "intrinsic"
                and goal["status"] in _LIVE_STATUSES
            )
            if not self._intrinsic.enabled():
                stages.append({"stage": "resource_check", "status": "awaiting",
                               "reason": "intrinsic_goals_disabled"})
            elif live >= self._intrinsic._quota():
                stages.append({"stage": "resource_check", "status": "fail",
                               "reason": "intrinsic_goal_quota_full"})
            else:
                stages.append({"stage": "resource_check", "status": "pass",
                               "reason": "quota_available"})
        except (IdentityError, GoalError, IntrinsicGoalError, OSError):
            stages.append({"stage": "resource_check", "status": "unavailable",
                           "reason": "goal_ledger_unreadable"})

        # Stage 5 — autonomy-policy check (human-authoritative policy).
        try:
            policy = self._autonomy.policy()
            state = self._autonomy.state()
            if state["paused"] or state["circuit_breaker_tripped"]:
                stages.append({"stage": "autonomy_policy_check",
                               "status": "awaiting",
                               "reason": "autonomy_paused_or_breaker_tripped"})
            elif str(policy["mode"]) in ("propose", "local", "bounded"):
                stages.append({"stage": "autonomy_policy_check",
                               "status": "pass",
                               "reason": "policy_mode_permits_planning"})
            else:
                stages.append({"stage": "autonomy_policy_check",
                               "status": "awaiting",
                               "reason": "policy_mode_requires_approval"})
        except (IdentityError, AutonomyError, GoalError, OSError, KeyError):
            stages.append({"stage": "autonomy_policy_check",
                           "status": "unavailable",
                           "reason": "autonomy_policy_unreadable"})

        statuses = [row["status"] for row in stages]
        if "duplicate" in statuses:
            outcome = "already_exists"
        elif "fail" in statuses:
            outcome = "rejected"
        elif "awaiting" in statuses or "unavailable" in statuses:
            outcome = "awaiting_approval"
        else:
            outcome = "planned_candidate"
        return {
            "lifecycle_version": LIFECYCLE_VERSION,
            "evaluation_id": str(uuid.uuid4()),
            "owner_entity_id": owner,
            "evaluated_at": _fmt(moment),
            "drive": drive,
            "title": title,
            "motivation": {
                "drive": drive,
                "score": score,
                "rationale_summary": (
                    f"Drive {drive} tension {score:.2f} in the motivation "
                    "store; lifecycle evaluated deterministically."
                ),
            },
            "stages": stages,
            "outcome": outcome,
            "existing_goal_id": existing_goal_id,
        }

    # -- bounded evaluation log --------------------------------------------
    def record_evaluation(self, proposal: dict[str, Any], *,
                          now: datetime | None = None) -> dict[str, Any]:
        """Evaluate one proposal and append the evaluation to the log.

        The only write this module ever performs, and only to its own
        log: no goal is created and no source store is touched.
        """
        if not self.enabled():
            raise MotivationLifecycleError("motivation lifecycle is disabled")
        evaluation = self.evaluate(proposal, now=now)
        self._append(evaluation)
        return evaluation

    def records(self, *, limit: int = 500) -> list[dict[str, Any]]:
        owner = self._identity.read().entity_id
        path = self.path()
        if path.is_symlink():
            raise MotivationLifecycleError(
                "motivation lifecycle log must not be a symbolic link")
        if not path.is_file():
            return []
        if path.stat().st_size > MAX_LOG_BYTES:
            raise MotivationLifecycleError(
                "motivation lifecycle log exceeds its size limit")
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except ValueError as exc:
                raise MotivationLifecycleError(
                    "motivation lifecycle log is malformed") from exc
            self._validate(payload, owner)
            out.append(payload)
        return out[-max(1, min(500, limit)):]

    def latest(self) -> dict[str, Any] | None:
        rows = self.records(limit=1)
        return rows[-1] if rows else None

    @staticmethod
    def _validate(payload: Any, owner: str) -> None:
        if not isinstance(payload, dict) or set(payload) != _FIELDS:
            raise MotivationLifecycleError("lifecycle record fields are invalid")
        if payload.get("lifecycle_version") != LIFECYCLE_VERSION:
            raise MotivationLifecycleError("lifecycle version is unsupported")
        if not _canonical_uuid(payload.get("evaluation_id")):
            raise MotivationLifecycleError("lifecycle evaluation id is invalid")
        if payload.get("owner_entity_id") != owner:
            raise MotivationLifecycleError(
                "lifecycle owner does not match entity identity")
        if not _timestamp_ok(payload.get("evaluated_at")):
            raise MotivationLifecycleError("lifecycle evaluated_at is invalid")
        drive = payload.get("drive")
        if not isinstance(drive, str) or not drive or len(drive) > 200:
            raise MotivationLifecycleError("lifecycle drive is invalid")
        title = payload.get("title")
        if not isinstance(title, str) or not title.strip() \
                or len(title) > MAX_TITLE_CHARS:
            raise MotivationLifecycleError("lifecycle title is invalid")
        motivation = payload.get("motivation")
        if not isinstance(motivation, dict) \
                or set(motivation) != {"drive", "score", "rationale_summary"} \
                or motivation.get("drive") != drive \
                or not _unit(motivation.get("score")) \
                or not isinstance(motivation.get("rationale_summary"), str) \
                or len(motivation["rationale_summary"]) > 500:
            raise MotivationLifecycleError("lifecycle motivation block is invalid")
        stages = payload.get("stages")
        if not isinstance(stages, list) or len(stages) != len(STAGES):
            raise MotivationLifecycleError("lifecycle stages are invalid")
        for row, expected in zip(stages, STAGES):
            if not isinstance(row, dict) \
                    or set(row) != {"stage", "status", "reason"} \
                    or row.get("stage") != expected \
                    or row.get("status") not in _STAGE_STATUSES \
                    or not isinstance(row.get("reason"), str) \
                    or not row["reason"] or len(row["reason"]) > 200:
                raise MotivationLifecycleError("lifecycle stage record is invalid")
        if payload.get("outcome") not in OUTCOMES:
            raise MotivationLifecycleError("lifecycle outcome is invalid")
        existing = payload.get("existing_goal_id")
        if existing != "" and not _canonical_uuid(existing):
            raise MotivationLifecycleError("lifecycle existing goal id is invalid")

    def _append(self, record: dict[str, Any]) -> None:
        path = self.path()
        if path.is_symlink():
            raise MotivationLifecycleError(
                "motivation lifecycle log must not be a symbolic link")
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
                    raise MotivationLifecycleError(
                        "motivation lifecycle log exceeds its size limit")
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(
                        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
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


class MotivationLifecycleBridge:
    """Surface the latest lifecycle evaluation, when one is actionable.

    Content-bearing only: a ``planned_candidate`` or
    ``awaiting_approval`` evaluation contributes one packet item.
    No session hook — evaluations happen only by explicit calls.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._service = MotivationLifecycleService(ctx)

    def hooks(self):
        return ()

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not _as_bool(
            self._ctx.get_config("motivation_lifecycle_enabled", False), False
        ):
            return []
        try:
            latest = self._service.latest()
        except (IdentityError, MotivationLifecycleError, OSError):
            return []
        if latest is None or latest["outcome"] not in (
                "planned_candidate", "awaiting_approval"):
            return []
        return [ContextItem(
            section="current_state",
            content=(
                f"Intrinsic goal lifecycle: {latest['title']} "
                f"(drive {latest['drive']}, outcome {latest['outcome']})"
            ),
            source="motivation_lifecycle",
            record_id=latest["evaluation_id"],
            priority=0.4,
            updated_at=_epoch(latest["evaluated_at"]),
        )]


__all__ = [
    "LIFECYCLE_VERSION",
    "DEFAULT_LOG_PATH",
    "SECTION8_DRIVES",
    "DRIVE_ALIASES",
    "STAGES",
    "OUTCOMES",
    "MotivationLifecycleError",
    "MotivationLifecycleService",
    "MotivationLifecycleBridge",
]
