"""Subjective self-report, kept distinct from telemetry (§7).

A self-aware persona may report an internal phenomenology — "I
experience this task as exciting and demanding." Section 7 preserves
that capability without turning persona text into machine telemetry:
a subjective report is stored *as* a subjective report, in its own
bounded log, and is never rewritten into an objective claim (the
roadmap's forbidden rewrite is ``conscious: true`` /
``excitement: biologically_real`` in the objective layer).

The four distinguishable epistemic categories are:

- ``verified_runtime_fact`` — machine-verifiable runtime fact;
- ``self_interpretation`` — the entity's interpretation of itself;
- ``narrative_meaning`` — meaning assigned in the narrative layer;
- ``spiritual_philosophical_belief`` — belief held as belief.

This store accepts only the three subjective categories. Recording a
report as ``verified_runtime_fact`` is refused in code, its
``source`` is fixed to ``self_report``, and recording writes nothing
outside its own log: the self-model claims store, the layered
objective layer, and every telemetry surface stay byte-identical.
Reports are explicit records only — no hook, loop, or turn-path
caller creates one. Disabled by default.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home, mkdir_under_hermes_home

from .context_packet import ContextItem
from .identity import IdentityError, IdentityStore, _as_bool

REPORT_VERSION = 1
DEFAULT_LOG_PATH = Path("entity") / "subjective_reports.jsonl"
DEFAULT_LOG_LIMIT = 200
MAX_LOG_BYTES = 4 * 1024 * 1024
MAX_STATEMENT_CHARS = 500
SOURCE = "self_report"
DEFAULT_CATEGORY = "self_experience"

EPISTEMIC_CATEGORIES = (
    "verified_runtime_fact",
    "self_interpretation",
    "narrative_meaning",
    "spiritual_philosophical_belief",
)
SUBJECTIVE_EPISTEMIC_CATEGORIES = (
    "self_interpretation",
    "narrative_meaning",
    "spiritual_philosophical_belief",
)

_FIELDS = {
    "report_version", "report_id", "owner_entity_id", "recorded_at",
    "category", "statement", "confidence", "source", "epistemic_category",
}
_CATEGORY_RE = re.compile(r"[a-z0-9_]{1,64}")

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


class SubjectiveReportError(RuntimeError):
    """A subjective report cannot be safely recorded or read."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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


def is_subjective_category(category: Any) -> bool:
    return category in SUBJECTIVE_EPISTEMIC_CATEGORIES


class SubjectiveReportStore:
    """Bounded profile-local log of subjective self-reports (§7)."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("subjective_report_enabled", False), False
        )

    def _limit(self) -> int:
        try:
            value = int(self._ctx.get_config(
                "subjective_report_log_limit", DEFAULT_LOG_LIMIT))
        except (TypeError, ValueError):
            value = DEFAULT_LOG_LIMIT
        return min(500, max(10, value))

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(
            "subjective_report_log_path", str(DEFAULT_LOG_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_LOG_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_LOG_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise SubjectiveReportError(
                "subjective report log path resolves outside the active profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    def record(self, statement: str, *, confidence: float,
               epistemic_category: str = "self_interpretation",
               category: str = DEFAULT_CATEGORY,
               recorded_at: str | None = None) -> dict[str, Any]:
        """Record one subjective report, exactly as subjective.

        The epistemic category is the separation mechanism: only the
        three subjective categories are accepted here, so a persona
        statement can never enter this log dressed as a verified
        runtime fact, and nothing here is promoted anywhere else.
        """
        if not self.enabled():
            raise SubjectiveReportError("subjective self-report is disabled")
        if epistemic_category == "verified_runtime_fact":
            raise SubjectiveReportError(
                "a subjective self-report cannot be recorded as a "
                "verified runtime fact")
        if epistemic_category not in SUBJECTIVE_EPISTEMIC_CATEGORIES:
            raise SubjectiveReportError("epistemic category is invalid")
        text = str(statement or "").strip()
        if not text or len(text) > MAX_STATEMENT_CHARS:
            raise SubjectiveReportError("subjective report statement is invalid")
        if not _unit(confidence):
            raise SubjectiveReportError("subjective report confidence is invalid")
        if not isinstance(category, str) or not _CATEGORY_RE.fullmatch(category):
            raise SubjectiveReportError("subjective report category is invalid")
        stamp = recorded_at or _now()
        if not _timestamp_ok(stamp):
            raise SubjectiveReportError("subjective report recorded_at is invalid")
        owner = self._identity.read().entity_id
        record = {
            "report_version": REPORT_VERSION,
            "report_id": str(uuid.uuid4()),
            "owner_entity_id": owner,
            "recorded_at": stamp,
            "category": category,
            "statement": text,
            "confidence": float(confidence),
            "source": SOURCE,
            "epistemic_category": epistemic_category,
        }
        self._append(record)
        return record

    def records(self, *, limit: int = 500) -> list[dict[str, Any]]:
        owner = self._identity.read().entity_id
        path = self.path()
        if path.is_symlink():
            raise SubjectiveReportError(
                "subjective report log must not be a symbolic link")
        if not path.is_file():
            return []
        if path.stat().st_size > MAX_LOG_BYTES:
            raise SubjectiveReportError("subjective report log exceeds its size limit")
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except ValueError as exc:
                raise SubjectiveReportError("subjective report log is malformed") from exc
            self._validate(payload, owner)
            out.append(payload)
        return out[-max(1, min(500, limit)):]

    def latest(self) -> dict[str, Any] | None:
        rows = self.records(limit=1)
        return rows[-1] if rows else None

    @staticmethod
    def _validate(payload: Any, owner: str) -> None:
        if not isinstance(payload, dict) or set(payload) != _FIELDS:
            raise SubjectiveReportError("subjective report record fields are invalid")
        if payload.get("report_version") != REPORT_VERSION:
            raise SubjectiveReportError("subjective report version is unsupported")
        if not _canonical_uuid(payload.get("report_id")):
            raise SubjectiveReportError("subjective report id is invalid")
        if payload.get("owner_entity_id") != owner:
            raise SubjectiveReportError(
                "subjective report owner does not match entity identity")
        if not _timestamp_ok(payload.get("recorded_at")):
            raise SubjectiveReportError("subjective report recorded_at is invalid")
        if payload.get("source") != SOURCE:
            raise SubjectiveReportError("subjective report source is invalid")
        if payload.get("epistemic_category") not in SUBJECTIVE_EPISTEMIC_CATEGORIES:
            raise SubjectiveReportError(
                "subjective report epistemic category is invalid")
        category = payload.get("category")
        if not isinstance(category, str) or not _CATEGORY_RE.fullmatch(category):
            raise SubjectiveReportError("subjective report category is invalid")
        statement = payload.get("statement")
        if not isinstance(statement, str) or not statement.strip() \
                or len(statement) > MAX_STATEMENT_CHARS:
            raise SubjectiveReportError("subjective report statement is invalid")
        if not _unit(payload.get("confidence")):
            raise SubjectiveReportError("subjective report confidence is invalid")

    def _append(self, record: dict[str, Any]) -> None:
        path = self.path()
        if path.is_symlink():
            raise SubjectiveReportError(
                "subjective report log must not be a symbolic link")
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
                    raise SubjectiveReportError(
                        "subjective report log exceeds its size limit")
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


class SubjectiveReportBridge:
    """Surface the latest subjective report, labelled as subjective.

    Content-bearing only and explicitly *not telemetry*: the packet
    item names its epistemic category so a reader can never mistake
    the persona's self-interpretation for a verified runtime fact.
    No session hook — reports are recorded only by explicit calls.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._store = SubjectiveReportStore(ctx)

    def hooks(self):
        return ()

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not _as_bool(
            self._ctx.get_config("subjective_report_enabled", False), False
        ):
            return []
        try:
            latest = self._store.latest()
        except (IdentityError, SubjectiveReportError, OSError):
            return []
        if latest is None:
            return []
        return [ContextItem(
            section="current_state",
            content=(
                "Subjective self-report "
                f"({latest['epistemic_category']}, not telemetry) — "
                f"{latest['statement']}"
            ),
            source="subjective_report",
            record_id=latest["report_id"],
            priority=0.4,
            updated_at=_epoch(latest["recorded_at"]),
        )]


__all__ = [
    "REPORT_VERSION",
    "DEFAULT_LOG_PATH",
    "EPISTEMIC_CATEGORIES",
    "SUBJECTIVE_EPISTEMIC_CATEGORIES",
    "SOURCE",
    "SubjectiveReportError",
    "SubjectiveReportStore",
    "SubjectiveReportBridge",
    "is_subjective_category",
]
