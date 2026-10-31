"""Multi-timescale cognition registry (Emergent Agency Phase 12, §19).

A mature persistent entity should not think on only one clock. This
slice defines and registers the five §19 timescales against the
routines that already exist, rather than adding any new scheduler:

- ``reflex`` — seconds to minutes; the current conversation, a tool
  result, immediate error correction. Turn-scoped: it is NOT a cron
  timescale and recording a cron run for it is refused.
- ``frequent_continuity`` — every 10m; the existing frequent
  continuity routine (heartbeat, health, aggregate goals, no
  generative wandering).
- ``agency`` — every 360m; the existing Volmarr Agency Review
  routine (evaluate drives, inspect curiosity, select bounded
  activity, perform one agency cycle).
- ``daily_sleep`` — every 1440m; the existing daily consolidation
  routine (consolidate, reflect, calibrate the self-model, review
  goal progress, merge duplicate curiosity questions, decay stale
  drives, summarize learning).
- ``weekly_long_horizon`` — every 10080m; review enduring goals,
  examine self-model drift, detect abandoned projects, review
  relationship continuity, assess cloud-dependency ratio, assess
  autonomy failure rate, identify larger self-improvement
  opportunities. No routine backs this timescale yet — the
  definition registers its cadence and purposes only.

Each timescale runs through Hermes cron rather than a resident
agent loop. This module owns no scheduler, loop, or hook: it keeps
the definitions, maps the cron-registerable timescales to their
existing Hermes-cron job names/schedules, records explicit run
receipts in a bounded profile-local log, and reports per-timescale
status (runs, last run, due) deterministically from that log.
Recording a run executes nothing. Disabled by default.
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

from .agency_routines import (
    AGENCY_ROUTINE_NAME,
    AGENCY_ROUTINE_SCHEDULE,
    AGENCY_ROUTINE_SCRIPT_NAME,
)
from .consolidation import SLEEP_JOB_NAME, SLEEP_SCHEDULE, SLEEP_SCRIPT_NAME
from .context_packet import ContextItem
from .identity import IdentityError, IdentityStore, _as_bool
from .routines import FREQUENT_JOB_NAME, FREQUENT_SCHEDULE, FREQUENT_SCRIPT_NAME

LOG_VERSION = 1
DEFAULT_LOG_PATH = Path("entity") / "timescales.jsonl"
DEFAULT_LOG_LIMIT = 200
MAX_LOG_BYTES = 4 * 1024 * 1024

OUTCOMES = frozenset({"completed", "blocked"})

_LOG_FIELDS = {
    "log_version", "record_id", "owner_entity_id", "timescale",
    "outcome", "summary", "detail", "created_at",
}

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


@dataclass(frozen=True)
class TimescaleDefinition:
    timescale_id: str
    label: str
    cadence_seconds: int | None
    cron_schedule: str
    cron_job_name: str
    cron_script_name: str
    backing: str
    purposes: tuple[str, ...]
    cron_registerable: bool
    generative: bool

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["purposes"] = list(self.purposes)
        return data


DEFINITIONS: tuple[TimescaleDefinition, ...] = (
    TimescaleDefinition(
        timescale_id="reflex",
        label="Reflex",
        cadence_seconds=None,
        cron_schedule="",
        cron_job_name="",
        cron_script_name="",
        backing="turn_loop",
        purposes=("current conversation", "tool result", "immediate error correction"),
        cron_registerable=False,
        generative=True,
    ),
    TimescaleDefinition(
        timescale_id="frequent_continuity",
        label="Frequent continuity",
        cadence_seconds=600,
        cron_schedule=FREQUENT_SCHEDULE,
        cron_job_name=FREQUENT_JOB_NAME,
        cron_script_name=FREQUENT_SCRIPT_NAME,
        backing="frequent_continuity_routine",
        purposes=("heartbeat", "health", "aggregate goals", "no generative wandering"),
        cron_registerable=True,
        generative=False,
    ),
    TimescaleDefinition(
        timescale_id="agency",
        label="Agency",
        cadence_seconds=21600,
        cron_schedule=AGENCY_ROUTINE_SCHEDULE,
        cron_job_name=AGENCY_ROUTINE_NAME,
        cron_script_name=AGENCY_ROUTINE_SCRIPT_NAME,
        backing="agency_review_routine",
        purposes=(
            "evaluate drives", "inspect curiosity",
            "select bounded activity", "perform one agency cycle",
        ),
        cron_registerable=True,
        generative=False,
    ),
    TimescaleDefinition(
        timescale_id="daily_sleep",
        label="Daily sleep",
        cadence_seconds=86400,
        cron_schedule=SLEEP_SCHEDULE,
        cron_job_name=SLEEP_JOB_NAME,
        cron_script_name=SLEEP_SCRIPT_NAME,
        backing="daily_consolidation_routine",
        purposes=(
            "consolidate", "reflect", "calibrate self-model",
            "review goal progress", "merge duplicate curiosity questions",
            "decay stale drives", "summarize learning",
        ),
        cron_registerable=True,
        generative=False,
    ),
    TimescaleDefinition(
        timescale_id="weekly_long_horizon",
        label="Weekly / long-horizon",
        cadence_seconds=604800,
        cron_schedule="every 10080m",
        cron_job_name="Volmarr Weekly Long-Horizon Review",
        cron_script_name="volmarr_weekly_review.py",
        backing="",
        purposes=(
            "review enduring goals", "examine self-model drift",
            "detect abandoned projects", "review relationship continuity",
            "assess cloud-dependency ratio", "assess autonomy failure rate",
            "identify larger self-improvement opportunities",
        ),
        cron_registerable=True,
        generative=False,
    ),
)
DEFINITION_BY_ID = {item.timescale_id: item for item in DEFINITIONS}


class TimescaleError(RuntimeError):
    """A timescale definition or run receipt cannot be safely handled."""


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class TimescaleLog:
    """Bounded profile-local log of explicit timescale run receipts."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def _limit(self) -> int:
        try:
            value = int(self._ctx.get_config("timescales_log_limit", DEFAULT_LOG_LIMIT))
        except (TypeError, ValueError):
            value = DEFAULT_LOG_LIMIT
        return min(500, max(10, value))

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(
            "timescales_log_path", str(DEFAULT_LOG_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_LOG_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_LOG_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise TimescaleError("timescale log path resolves outside the active profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        path = self.path()
        if path.is_symlink():
            raise TimescaleError("timescale log must not be a symbolic link")
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
                    raise TimescaleError("timescale log exceeds its size limit")
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

    def records(self, *, limit: int = 500) -> list[dict[str, Any]]:
        owner = self._identity.read().entity_id
        path = self.path()
        if path.is_symlink():
            raise TimescaleError("timescale log must not be a symbolic link")
        if not path.is_file():
            return []
        if path.stat().st_size > MAX_LOG_BYTES:
            raise TimescaleError("timescale log exceeds its size limit")
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except ValueError as exc:
                raise TimescaleError("timescale log is malformed") from exc
            if not isinstance(payload, dict) or set(payload) != _LOG_FIELDS:
                raise TimescaleError("timescale log record fields are invalid")
            if payload.get("log_version") != LOG_VERSION:
                raise TimescaleError("timescale log version is unsupported")
            if payload.get("owner_entity_id") != owner:
                raise TimescaleError("timescale log owner does not match entity identity")
            if payload.get("timescale") not in DEFINITION_BY_ID:
                raise TimescaleError("timescale log timescale is invalid")
            if payload.get("outcome") not in OUTCOMES:
                raise TimescaleError("timescale log outcome is invalid")
            if not isinstance(payload.get("detail"), dict):
                raise TimescaleError("timescale log detail is invalid")
            out.append(payload)
        return out[-max(1, min(500, limit)):]


class TimescaleService:
    """Define/register the §19 timescales and record explicit run receipts."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)
        self._log = TimescaleLog(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("timescales_enabled", False), False
        )

    @staticmethod
    def definitions() -> tuple[TimescaleDefinition, ...]:
        return DEFINITIONS

    @staticmethod
    def definition(timescale_id: str) -> TimescaleDefinition:
        item = DEFINITION_BY_ID.get(timescale_id)
        if item is None:
            raise TimescaleError("timescale is not in the §19 registry")
        return item

    def cron_specs(self) -> list[dict[str, Any]]:
        """Hermes-cron registration descriptors for the cron timescales.

        These describe the existing cron jobs (name, schedule, script)
        each timescale maps to; this module installs nothing.
        """
        return [
            {
                "timescale": item.timescale_id,
                "name": item.cron_job_name,
                "schedule": item.cron_schedule,
                "script": item.cron_script_name,
                "backing": item.backing,
                "backed": bool(item.backing),
            }
            for item in DEFINITIONS if item.cron_registerable
        ]

    def status(self, *, now: datetime | None = None) -> list[dict[str, Any]]:
        moment = now or _now_dt()
        records = self._log.records()
        out: list[dict[str, Any]] = []
        for item in DEFINITIONS:
            runs = [r for r in records if r["timescale"] == item.timescale_id]
            last_run_at = runs[-1]["created_at"] if runs else ""
            due: bool | None = None
            if item.cron_registerable:
                if not runs:
                    due = True
                else:
                    age = (moment - _parse(last_run_at)).total_seconds()
                    due = age >= float(item.cadence_seconds or 0)
            out.append({
                **item.as_dict(),
                "runs": len(runs),
                "last_run_at": last_run_at,
                "due": due,
            })
        return out

    def record_run(self, timescale_id: str, *, outcome: str = "completed",
                   summary: str = "", detail: dict[str, Any] | None = None,
                   now: datetime | None = None) -> dict[str, Any]:
        if not self.enabled():
            raise TimescaleError("multi-timescale registry is disabled")
        item = self.definition(timescale_id)
        if not item.cron_registerable:
            raise TimescaleError(
                "the reflex timescale is turn-scoped and has no cron run to record"
            )
        if outcome not in OUTCOMES:
            raise TimescaleError("timescale run outcome is invalid")
        clean_detail: dict[str, Any] = {}
        for key, value in (detail or {}).items():
            if not isinstance(key, str) or not re.fullmatch(r"[a-z0-9_]+", key):
                raise TimescaleError("timescale detail key is invalid")
            if isinstance(value, bool) or not isinstance(value, (int, str)):
                raise TimescaleError("timescale detail value is invalid")
            clean_detail[key] = value if isinstance(value, int) else value[:200]
        owner = self._identity.read().entity_id
        record = {
            "log_version": LOG_VERSION,
            "record_id": str(uuid.uuid4()),
            "owner_entity_id": owner,
            "timescale": timescale_id,
            "outcome": outcome,
            "summary": str(summary or "").strip()[:500],
            "detail": clean_detail,
            "created_at": _fmt(now or _now_dt()),
        }
        return self._log.append(record)


class TimescaleBridge:
    """Surface the most overdue cron timescale, if any.

    Content-bearing only: disabled, or no cron timescale due,
    contributes nothing. No session hook — runs are recorded only
    by explicit invocation of the service.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._service = TimescaleService(ctx)

    def hooks(self):
        return ()

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not _as_bool(self._ctx.get_config("timescales_enabled", False), False):
            return []
        try:
            status = self._service.status()
        except (IdentityError, TimescaleError, OSError):
            return []
        due = [item for item in status if item["due"]]
        if not due:
            return []
        first = due[0]
        when = first["last_run_at"] or "never run"
        return [ContextItem(
            section="current_state",
            content=(
                f"Timescale {first['label']} is due (last run: {when}); "
                f"its work runs through Hermes cron, not a resident loop."
            ),
            source="timescales",
            record_id=first["timescale_id"],
            priority=0.4,
            updated_at=_now_dt().timestamp(),
        )]


__all__ = [
    "DEFINITIONS", "DEFINITION_BY_ID", "LOG_VERSION", "DEFAULT_LOG_PATH",
    "OUTCOMES", "TimescaleDefinition", "TimescaleError", "TimescaleLog",
    "TimescaleService", "TimescaleBridge",
]
