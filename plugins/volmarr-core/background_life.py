"""Background-life reconciliation (Self-Aware Agency roadmap §15).

§15 says: do not create another scheduler — use Hermes cron. The
plugin already owns three of the surfaces §15 names, banked in
earlier slices, and this module is a reconciliation over them,
not a second scheduler or routine set:

- frequent continuity — the existing ~10-minute no-agent routine
  (:mod:`.routines`, ``every 10m``) already pulses the heartbeat
  and aggregates goal counts deterministically, with no LLM;
- daily consolidation — the existing daily routine
  (:mod:`.consolidation`, ``every 1440m``) already records a
  non-destructive checkpoint (relationships / goals / heartbeat);
- the agency / curiosity / reflection work already exists as
  gated services (Slices 93, 94, 97, 100), but NOT as §15
  routines.

What §15 adds, and what stands here:

- the four §15 routines named in roadmap order
  (:data:`ROUTINES`): frequent continuity (``every 10m``, backed),
  reflection (``every 120m``, paused by default, backed: false —
  no routine exists yet), curiosity (``every 240m``, paused by
  default, backed: false), and daily consolidation
  (``every 1440m``, backed). Reflection and curiosity report
  ``backed: false`` honestly: their definitions, gates, and
  cadences are registered here, but no Hermes-cron job backs
  them yet and this module installs nothing;
- the §15 gates as pure functions (:func:`routine_gate`):
  frequent continuity and daily consolidation are deterministic
  and always allowed; reflection is allowed only when a
  reflection trigger is pending; curiosity is allowed only when
  a high-value open question exists (top score at or above the
  usefulness floor) and then selects at most one question, whose
  default action is a research proposal — never automatic
  external research;
- the frequent-continuity extension coverage, stated honestly
  (:data:`FREQUENT_COVERAGE`): heartbeat and aggregate goals are
  covered by the existing routine; health is partial (the
  heartbeat probe only); stale-blocked-goal detection is partial
  (blocked goals are counted, staleness is not aged); high-
  priority discrepancy detection is deferred (discrepancies live
  in the layered self-model, which the no-agent routine does
  not call);
- the daily-consolidation digest extension §15 names
  (:data:`DAILY_DIGEST_FIELDS`): the seven digest/count fields
  the daily checkpoint should record beyond its current summary
  (self-model, awareness, and drive-state digests; curiosity,
  reflection, autonomy-action, and intrinsic-goal counts), plus
  the rule that the daily routine never rewrites personality
  canon (:data:`DAILY_CANON_RULE`);
- explicit run receipts in this module's own bounded log
  (``entity/background_life.jsonl``): routine id, slug-gated
  outcome, and a counts-only detail dict (slug keys, non-negative
  int values — no field can carry free text). Recording a
  receipt runs nothing and installs nothing; Hermes cron
  remains the only scheduler.

Disabled by default.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home, mkdir_under_hermes_home

from .consolidation import SLEEP_JOB_NAME, SLEEP_SCHEDULE, SLEEP_SCRIPT_NAME
from .context_packet import ContextItem
from .identity import IdentityError, IdentityStore, _as_bool
from .routines import FREQUENT_JOB_NAME, FREQUENT_SCHEDULE, FREQUENT_SCRIPT_NAME

RECEIPT_VERSION = 1
DEFAULT_LOG_PATH = Path("entity") / "background_life.jsonl"
DEFAULT_LOG_LIMIT = 200
MAX_LOG_BYTES = 4 * 1024 * 1024
DEFAULT_MIN_SCORE = 0.10

REFLECTION_SCHEDULE = "every 120m"
REFLECTION_JOB_NAME = "Volmarr Reflection Routine"
REFLECTION_SCRIPT_NAME = "volmarr_reflection_routine.py"
CURIOSITY_SCHEDULE = "every 240m"
CURIOSITY_JOB_NAME = "Volmarr Curiosity Routine"
CURIOSITY_SCRIPT_NAME = "volmarr_curiosity_routine.py"

OUTCOMES = frozenset({"completed", "blocked"})
_SLUG = re.compile(r"[a-z0-9][a-z0-9_-]*")


@dataclass(frozen=True)
class RoutineDefinition:
    routine_id: str
    label: str
    schedule: str
    cron_job_name: str
    cron_script_name: str
    backing: str
    purposes: tuple[str, ...]
    paused_by_default: bool
    llm_required: bool
    max_items: int

    @property
    def backed(self) -> bool:
        return bool(self.backing)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["purposes"] = list(self.purposes)
        data["backed"] = self.backed
        return data


# The four §15 routines, in roadmap order.
ROUTINES: tuple[RoutineDefinition, ...] = (
    RoutineDefinition(
        routine_id="frequent_continuity",
        label="Frequent continuity",
        schedule=FREQUENT_SCHEDULE,
        cron_job_name=FREQUENT_JOB_NAME,
        cron_script_name=FREQUENT_SCRIPT_NAME,
        backing="frequent_continuity_routine",
        purposes=("heartbeat", "health", "aggregate goals",
                  "stale-blocked-goal detection",
                  "high-priority deterministic discrepancy detection"),
        paused_by_default=True,
        llm_required=False,
        max_items=0,
    ),
    RoutineDefinition(
        routine_id="reflection",
        label="Reflection routine",
        schedule=REFLECTION_SCHEDULE,
        cron_job_name=REFLECTION_JOB_NAME,
        cron_script_name=REFLECTION_SCRIPT_NAME,
        backing="",
        purposes=("run only when a reflection trigger is pending",
                  "prefer local reflex cognition"),
        paused_by_default=True,
        llm_required=False,
        max_items=1,
    ),
    RoutineDefinition(
        routine_id="curiosity",
        label="Curiosity routine",
        schedule=CURIOSITY_SCHEDULE,
        cron_job_name=CURIOSITY_JOB_NAME,
        cron_script_name=CURIOSITY_SCRIPT_NAME,
        backing="",
        purposes=("select at most one high-value open question",
                  "default to a research proposal, not external research"),
        paused_by_default=True,
        llm_required=False,
        max_items=1,
    ),
    RoutineDefinition(
        routine_id="daily_consolidation",
        label="Daily consolidation",
        schedule=SLEEP_SCHEDULE,
        cron_job_name=SLEEP_JOB_NAME,
        cron_script_name=SLEEP_SCRIPT_NAME,
        backing="daily_consolidation_routine",
        purposes=("record the §15 daily digests and counts",
                  "never rewrite personality canon automatically"),
        paused_by_default=True,
        llm_required=False,
        max_items=0,
    ),
)
ROUTINE_BY_ID = {item.routine_id: item for item in ROUTINES}

# How the existing frequent routine covers §15's extension list.
FREQUENT_COVERAGE = {
    "heartbeat": "covered",
    "health": "partial",
    "aggregate_goals": "covered",
    "stale_blocked_goal_detection": "partial",
    "discrepancy_detection": "deferred",
}

# The seven digest/count fields §15 adds to the daily checkpoint.
DAILY_DIGEST_FIELDS = (
    "self_model_digest",
    "awareness_digest",
    "drive_state_digest",
    "curiosity_counts",
    "reflection_counts",
    "autonomy_action_counts",
    "intrinsic_goal_counts",
)
DAILY_CANON_RULE = "never_rewrite_personality_canon"

_RECEIPT_FIELDS = {
    "receipt_version", "kind", "record_id", "routine",
    "owner_entity_id", "recorded_at", "outcome", "reason_code",
    "counts",
}

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


class BackgroundLifeError(RuntimeError):
    """A background-life receipt cannot be safely built or read."""


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


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


def _epoch(value: str) -> float:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, OverflowError, OSError):
        return 0.0


def _canonical_uuid(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


def routine_definitions() -> list[dict[str, Any]]:
    """The four §15 routines, in roadmap order."""
    return [item.as_dict() for item in ROUTINES]


def frequent_coverage() -> list[dict[str, str]]:
    return [
        {"item": key, "coverage": value}
        for key, value in FREQUENT_COVERAGE.items()
    ]


def daily_digest_fields() -> list[str]:
    return list(DAILY_DIGEST_FIELDS)


def routine_gate(routine_id: str, *,
                 reflection_trigger_pending: bool = False,
                 curiosity_top_score: float | None = None,
                 min_score: float = DEFAULT_MIN_SCORE) -> dict[str, Any]:
    """The pure §15 gate for one routine.

    Deterministic routines are always allowed. Reflection runs
    only when a trigger is pending. Curiosity runs only when a
    high-value question exists, selects at most one, and its
    default action is a research proposal.
    """
    if routine_id not in ROUTINE_BY_ID:
        raise BackgroundLifeError("routine is not a §15 routine")
    if isinstance(min_score, bool) or not isinstance(min_score, (int, float)) \
            or not 0.0 <= float(min_score) <= 1.0:
        raise BackgroundLifeError("curiosity minimum score is invalid")
    if routine_id in ("frequent_continuity", "daily_consolidation"):
        return {"routine": routine_id, "allowed": True,
                "reason_code": "deterministic_routine",
                "selected": 0, "default_action": "run"}
    if routine_id == "reflection":
        allowed = bool(reflection_trigger_pending)
        return {"routine": routine_id, "allowed": allowed,
                "reason_code": "trigger_pending" if allowed
                else "no_trigger_pending",
                "selected": 1 if allowed else 0, "default_action": "reflect"}
    # curiosity
    if curiosity_top_score is None:
        return {"routine": routine_id, "allowed": False,
                "reason_code": "no_open_question",
                "selected": 0, "default_action": "research_proposal"}
    if isinstance(curiosity_top_score, bool) \
            or not isinstance(curiosity_top_score, (int, float)) \
            or not 0.0 <= float(curiosity_top_score) <= 1.0:
        raise BackgroundLifeError("curiosity top score is invalid")
    allowed = float(curiosity_top_score) >= float(min_score)
    return {"routine": routine_id, "allowed": allowed,
            "reason_code": "high_value_question" if allowed
            else "below_usefulness_floor",
            "selected": 1 if allowed else 0,
            "default_action": "research_proposal"}


def _validate_counts(counts: Any) -> dict[str, int]:
    if counts is None:
        return {}
    if not isinstance(counts, dict):
        raise BackgroundLifeError("receipt counts are invalid")
    out: dict[str, int] = {}
    for key, value in counts.items():
        if not isinstance(key, str) or not _SLUG.fullmatch(key):
            raise BackgroundLifeError("receipt counts key is invalid")
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise BackgroundLifeError("receipt counts value is invalid")
        out[key] = value
    return out


class BackgroundLifeService:
    """The §15 background-life registry and explicit receipt log."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("background_life_enabled", False), False
        )

    def _limit(self) -> int:
        try:
            value = int(self._ctx.get_config(
                "background_life_log_limit", DEFAULT_LOG_LIMIT))
        except (TypeError, ValueError):
            value = DEFAULT_LOG_LIMIT
        return min(500, max(10, value))

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(
            "background_life_log_path", str(DEFAULT_LOG_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_LOG_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_LOG_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise BackgroundLifeError(
                "background life log path resolves outside the profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    def cron_specs(self) -> list[dict[str, Any]]:
        """Hermes-cron descriptors for the §15 routines.

        These describe the cron jobs each routine maps to; this
        module installs nothing and Hermes cron remains the only
        scheduler. Unbacked routines report ``backed: false``.
        """
        return [
            {"routine": item.routine_id, "name": item.cron_job_name,
             "schedule": item.schedule, "script": item.cron_script_name,
             "backing": item.backing, "backed": item.backed,
             "paused_by_default": item.paused_by_default}
            for item in ROUTINES
        ]

    def build_receipt(self, routine_id: str, *, outcome: str,
                      reason_code: str = "",
                      counts: dict[str, Any] | None = None,
                      recorded_at: str | None = None) -> dict[str, Any]:
        """Build a §15 run receipt. Pure; records and runs nothing."""
        if routine_id not in ROUTINE_BY_ID:
            raise BackgroundLifeError("routine is not a §15 routine")
        if outcome not in OUTCOMES:
            raise BackgroundLifeError("receipt outcome is invalid")
        if reason_code and not _SLUG.fullmatch(reason_code):
            raise BackgroundLifeError("receipt reason_code is invalid")
        stamp = recorded_at or _fmt(_now_dt())
        if not _timestamp_ok(stamp):
            raise BackgroundLifeError("receipt recorded_at is invalid")
        receipt = {
            "receipt_version": RECEIPT_VERSION,
            "kind": "background_life_receipt",
            "record_id": str(uuid.uuid4()),
            "routine": routine_id,
            "owner_entity_id": self._identity.read().entity_id,
            "recorded_at": stamp,
            "outcome": outcome,
            "reason_code": reason_code,
            "counts": _validate_counts(counts),
        }
        self._validate(receipt, receipt["owner_entity_id"])
        return receipt

    def record_receipt(self, receipt: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled():
            raise BackgroundLifeError("background life is disabled")
        owner = self._identity.read().entity_id
        self._validate(receipt, owner)
        self._append(receipt)
        return receipt

    def receipts(self, *, limit: int = 500) -> list[dict[str, Any]]:
        owner = self._identity.read().entity_id
        path = self.path()
        if path.is_symlink():
            raise BackgroundLifeError(
                "background life log must not be a symbolic link")
        if not path.is_file():
            return []
        if path.stat().st_size > MAX_LOG_BYTES:
            raise BackgroundLifeError(
                "background life log exceeds its size limit")
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except ValueError as exc:
                raise BackgroundLifeError(
                    "background life log is malformed") from exc
            self._validate(payload, owner)
            out.append(payload)
        return out[-max(1, min(500, limit)):]

    def _validate(self, payload: Any, owner: str) -> None:
        if not isinstance(payload, dict):
            raise BackgroundLifeError("background life receipt is invalid")
        if set(payload) != _RECEIPT_FIELDS:
            raise BackgroundLifeError("background life receipt fields are invalid")
        if payload.get("receipt_version") != RECEIPT_VERSION:
            raise BackgroundLifeError("background life receipt version is unsupported")
        if payload.get("kind") != "background_life_receipt":
            raise BackgroundLifeError("background life receipt kind is invalid")
        if payload.get("owner_entity_id") != owner:
            raise BackgroundLifeError(
                "background life receipt owner does not match entity identity")
        if not _canonical_uuid(payload.get("record_id")):
            raise BackgroundLifeError("background life receipt id is invalid")
        if payload.get("routine") not in ROUTINE_BY_ID:
            raise BackgroundLifeError("background life receipt routine is invalid")
        if payload.get("outcome") not in OUTCOMES:
            raise BackgroundLifeError("background life receipt outcome is invalid")
        reason = payload.get("reason_code")
        if not isinstance(reason, str) or (reason and not _SLUG.fullmatch(reason)):
            raise BackgroundLifeError("background life receipt reason_code is invalid")
        if not _timestamp_ok(payload.get("recorded_at")):
            raise BackgroundLifeError("background life receipt recorded_at is invalid")
        _validate_counts(payload.get("counts"))

    def _append(self, record: dict[str, Any]) -> None:
        path = self.path()
        if path.is_symlink():
            raise BackgroundLifeError(
                "background life log must not be a symbolic link")
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
                    raise BackgroundLifeError(
                        "background life log exceeds its size limit")
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


class BackgroundLifeBridge:
    """Surface the latest §15 receipt, content-bearing only.

    No session hook — receipts are recorded only by explicit
    calls, and nothing here installs or runs a routine.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._service = BackgroundLifeService(ctx)

    def hooks(self):
        return ()

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not _as_bool(
            self._ctx.get_config("background_life_enabled", False), False
        ):
            return []
        try:
            receipts = self._service.receipts(limit=1)
        except (IdentityError, BackgroundLifeError, OSError):
            return []
        if not receipts:
            return []
        latest = receipts[-1]
        if latest["outcome"] != "blocked" and not latest["counts"]:
            return []
        label = ROUTINE_BY_ID[latest["routine"]].label
        return [ContextItem(
            section="current_state",
            content=(
                f"Background life (§15): {label} last run "
                f"{latest['outcome']}"
                + (f" ({latest['reason_code']})" if latest["reason_code"] else "")
                + "; routines run through Hermes cron, not a new scheduler."
            ),
            source="background_life",
            record_id=latest["record_id"],
            priority=0.4,
            updated_at=_epoch(latest["recorded_at"]),
        )]


__all__ = [
    "RECEIPT_VERSION",
    "DEFAULT_LOG_PATH",
    "ROUTINES",
    "ROUTINE_BY_ID",
    "FREQUENT_COVERAGE",
    "DAILY_DIGEST_FIELDS",
    "DAILY_CANON_RULE",
    "BackgroundLifeError",
    "BackgroundLifeService",
    "BackgroundLifeBridge",
    "routine_definitions",
    "frequent_coverage",
    "daily_digest_fields",
    "routine_gate",
]
