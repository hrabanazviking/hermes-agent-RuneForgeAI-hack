"""Detailed reflection records (Self-Aware Agency roadmap §9).

Emergent Agency Phase 3 (Slice 93) already built the metacognition
store: a compact summary plus a bounded log of ``ReflectionRecord``
conclusions (trigger, subject, predicted success, observed outcome,
lessons). What it does not carry is this roadmap's own §9.2
reflection shape, which is therefore built here as a reconciliation,
not a second metacognition engine:

- §9.2 record: the detailed record at ``entity/reflections.jsonl``
  adds the fields the Phase 3 record has no place for —
  ``confidence_before`` / ``confidence_after``, ``assumptions``,
  ``evidence``, ``error_class``, ``self_model_changes`` (proposal
  text only), and ``next_test`` — beside the shared identity fields.
  :meth:`ReflectionDetailService.build_detail` derives a detail
  record from a Phase 3 ``ReflectionRecord`` so the two logs stay
  about the same reflections;
- §9.3 reflection levels: the level is a deterministic function of
  the record, never a stored opinion — Level 0 for the named
  deterministic triggers (repeated tool failure, repeated route
  escalation) and for a confidence/evidence mismatch (confidence
  ≥ 0.8 with no evidence), Level 2 for the deep-reflection error
  classes (identity conflict, major contradiction, ethical
  conflict, long-term planning failure), Level 1 otherwise. The
  stored level must agree with the function on read, exactly as
  the §6.5 awareness flag must agree with its triggers;
- §9.1 monitoring question "have I failed at this before":
  :meth:`history_for` counts prior detail records for a subject
  (a failure = a record carrying an ``error_class``) and returns
  the most recent lesson and next test.

§9.4's bounds stand: ``self_model_changes`` are recorded as
proposal text and never applied here — this module imports no
self-model, goal, drive, or autonomy store and writes only its own
bounded log, only on an explicit ``record_detail`` call. The
cognition router remains authoritative for any Level 2 reasoning;
this module classifies, it does not reason. Disabled by default.
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

from .agency_contracts import ReflectionRecord
from .context_packet import ContextItem
from .identity import IdentityError, IdentityStore, _as_bool

REFLECTION_DETAIL_VERSION = 1
DEFAULT_LOG_PATH = Path("entity") / "reflections.jsonl"
DEFAULT_LOG_LIMIT = 200
MAX_LOG_BYTES = 4 * 1024 * 1024
MAX_LIST_ITEMS = 5
MAX_TEXT_CHARS = 500
MAX_SUBJECT_CHARS = 200

_SLUG = re.compile(r"^[a-z][a-z0-9_]*$")

# §9.3 Level 0 — deterministic, no LLM required.
DETERMINISTIC_TRIGGERS = frozenset({"repeated_tool_failure", "model_escalation"})
CONFIDENCE_EVIDENCE_MISMATCH = 0.8
# §9.3 Level 2 — deep reflection error classes.
DEEP_ERROR_CLASSES = frozenset({
    "identity_conflict", "major_contradiction", "ethical_conflict",
    "long_term_planning_failure",
})
LEVELS = frozenset({0, 1, 2})

_FIELDS = {
    "reflection_version", "reflection_id", "owner_entity_id",
    "recorded_at", "trigger", "subject", "reflection_level",
    "confidence_before", "confidence_after", "assumptions",
    "evidence", "error_class", "lesson", "self_model_changes",
    "next_test",
}

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


class ReflectionDetailError(RuntimeError):
    """A reflection detail record cannot be safely built or read."""


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


def _text_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)) or len(value) > MAX_LIST_ITEMS:
        raise ReflectionDetailError(f"reflection {field} is invalid or oversized")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip() \
                or len(item.strip()) > MAX_TEXT_CHARS:
            raise ReflectionDetailError(f"reflection {field} entry is invalid")
        out.append(item.strip())
    return out


def reflection_level(record: dict[str, Any]) -> int:
    """The §9.3 level of a detail record — a pure function of it."""
    if record.get("error_class") in DEEP_ERROR_CLASSES:
        return 2
    if record.get("trigger") in DETERMINISTIC_TRIGGERS:
        return 0
    confidence = record.get("confidence_before")
    if _unit(confidence) and float(confidence) >= CONFIDENCE_EVIDENCE_MISMATCH \
            and not record.get("evidence"):
        return 0  # confidence/evidence mismatch (§9.3 Level 0 example)
    return 1


class ReflectionDetailService:
    """The §9.2 detailed reflection log beside the Phase 3 store."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("reflection_detail_enabled", False), False
        )

    def _limit(self) -> int:
        try:
            value = int(self._ctx.get_config(
                "reflection_detail_log_limit", DEFAULT_LOG_LIMIT))
        except (TypeError, ValueError):
            value = DEFAULT_LOG_LIMIT
        return min(500, max(10, value))

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(
            "reflection_detail_log_path", str(DEFAULT_LOG_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_LOG_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_LOG_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise ReflectionDetailError(
                "reflection detail log path resolves outside the profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    # -- §9.2 record construction -------------------------------------------
    def build_detail(
        self,
        record: ReflectionRecord,
        *,
        confidence_after: float,
        confidence_before: float | None = None,
        assumptions: Any = (),
        evidence: Any = (),
        error_class: str = "",
        self_model_changes: Any = (),
        next_test: str = "",
    ) -> dict[str, Any]:
        """Derive a §9.2 detail record from a Phase 3 reflection.

        Identity fields (id, owner, time, trigger, subject) come from
        the Phase 3 record; ``confidence_before`` defaults to its
        predicted success and ``lesson`` to its first lesson. Pure:
        reads nothing, writes nothing.
        """
        if not isinstance(record, ReflectionRecord):
            raise ReflectionDetailError(
                "detail must derive from a ReflectionRecord contract record")
        before = record.predicted_success if confidence_before is None \
            else confidence_before
        if before is None:
            raise ReflectionDetailError(
                "confidence_before is required when the reflection "
                "carries no predicted success")
        detail = {
            "reflection_version": REFLECTION_DETAIL_VERSION,
            "reflection_id": record.reflection_id,
            "owner_entity_id": record.owner_entity_id,
            "recorded_at": record.created_at,
            "trigger": record.trigger,
            "subject": record.subject_ref,
            "reflection_level": 1,  # replaced below by the §9.3 function
            "confidence_before": before,
            "confidence_after": confidence_after,
            "assumptions": _text_list(assumptions, "assumptions"),
            "evidence": _text_list(evidence, "evidence"),
            "error_class": error_class,
            "lesson": record.lessons[0] if record.lessons else "",
            "self_model_changes": _text_list(
                self_model_changes, "self_model_changes"),
            "next_test": next_test,
        }
        detail["reflection_level"] = reflection_level(detail)
        self._validate(detail, record.owner_entity_id)
        return detail

    # -- bounded log ----------------------------------------------------------
    def record_detail(self, detail: dict[str, Any]) -> dict[str, Any]:
        """Append one validated detail record to this module's own log.

        The only write this module ever performs. The record's
        ``self_model_changes`` stay proposal text (§9.4): nothing is
        applied to any other store.
        """
        if not self.enabled():
            raise ReflectionDetailError("reflection detail is disabled")
        owner = self._identity.read().entity_id
        self._validate(detail, owner)
        self._append(detail)
        return detail

    def records(self, *, limit: int = 500) -> list[dict[str, Any]]:
        owner = self._identity.read().entity_id
        path = self.path()
        if path.is_symlink():
            raise ReflectionDetailError(
                "reflection detail log must not be a symbolic link")
        if not path.is_file():
            return []
        if path.stat().st_size > MAX_LOG_BYTES:
            raise ReflectionDetailError(
                "reflection detail log exceeds its size limit")
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except ValueError as exc:
                raise ReflectionDetailError(
                    "reflection detail log is malformed") from exc
            self._validate(payload, owner)
            out.append(payload)
        return out[-max(1, min(500, limit)):]

    def latest(self) -> dict[str, Any] | None:
        rows = self.records(limit=1)
        return rows[-1] if rows else None

    def history_for(self, subject: str) -> dict[str, Any]:
        """§9.1: prior detail records for one subject, failures counted.

        A failure is a record carrying an ``error_class``. Read-only.
        """
        if not isinstance(subject, str) or not subject.strip() \
                or len(subject.strip()) > MAX_SUBJECT_CHARS:
            raise ReflectionDetailError("history subject is invalid")
        rows = [row for row in self.records(limit=500)
                if row["subject"] == subject.strip()]
        last = rows[-1] if rows else None
        return {
            "subject": subject.strip(),
            "count": len(rows),
            "failures": sum(1 for row in rows if row["error_class"]),
            "last_lesson": last["lesson"] if last else "",
            "last_next_test": last["next_test"] if last else "",
            "last_recorded_at": last["recorded_at"] if last else "",
        }

    @staticmethod
    def _validate(payload: Any, owner: str) -> None:
        if not isinstance(payload, dict) or set(payload) != _FIELDS:
            raise ReflectionDetailError("reflection detail fields are invalid")
        if payload.get("reflection_version") != REFLECTION_DETAIL_VERSION:
            raise ReflectionDetailError("reflection detail version is unsupported")
        if not _canonical_uuid(payload.get("reflection_id")):
            raise ReflectionDetailError("reflection detail id is invalid")
        if payload.get("owner_entity_id") != owner:
            raise ReflectionDetailError(
                "reflection detail owner does not match entity identity")
        if not _timestamp_ok(payload.get("recorded_at")):
            raise ReflectionDetailError("reflection detail recorded_at is invalid")
        trigger = payload.get("trigger")
        if not isinstance(trigger, str) or not _SLUG.match(trigger):
            raise ReflectionDetailError("reflection detail trigger is invalid")
        subject = payload.get("subject")
        if not isinstance(subject, str) or not subject.strip() \
                or len(subject) > MAX_SUBJECT_CHARS:
            raise ReflectionDetailError("reflection detail subject is invalid")
        if not _unit(payload.get("confidence_before")) \
                or not _unit(payload.get("confidence_after")):
            raise ReflectionDetailError("reflection detail confidence is invalid")
        for field in ("assumptions", "evidence", "self_model_changes"):
            _text_list(payload.get(field), field)
        error_class = payload.get("error_class")
        if not isinstance(error_class, str) \
                or (error_class and not _SLUG.match(error_class)):
            raise ReflectionDetailError("reflection detail error_class is invalid")
        for field in ("lesson", "next_test"):
            value = payload.get(field)
            if not isinstance(value, str) or len(value) > MAX_TEXT_CHARS:
                raise ReflectionDetailError(f"reflection detail {field} is invalid")
        level = payload.get("reflection_level")
        if isinstance(level, bool) or level not in LEVELS:
            raise ReflectionDetailError("reflection detail level is invalid")
        if level != reflection_level(payload):
            raise ReflectionDetailError(
                "reflection detail level disagrees with the §9.3 function")

    def _append(self, record: dict[str, Any]) -> None:
        path = self.path()
        if path.is_symlink():
            raise ReflectionDetailError(
                "reflection detail log must not be a symbolic link")
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
                    raise ReflectionDetailError(
                        "reflection detail log exceeds its size limit")
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


class ReflectionDetailBridge:
    """Surface the latest detailed reflection, when one exists.

    Content-bearing only. No session hook — detail records are
    written only by explicit ``record_detail`` calls.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._service = ReflectionDetailService(ctx)

    def hooks(self):
        return ()

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not _as_bool(
            self._ctx.get_config("reflection_detail_enabled", False), False
        ):
            return []
        try:
            latest = self._service.latest()
        except (IdentityError, ReflectionDetailError, OSError):
            return []
        if latest is None or not latest["lesson"]:
            return []
        content = (
            f"Reflection detail (§9 level {latest['reflection_level']}, "
            f"{latest['trigger']}): {latest['lesson']}"
        )
        if latest["next_test"]:
            content += f" Next test: {latest['next_test']}"
        return [ContextItem(
            section="current_state",
            content=content,
            source="reflection_detail",
            record_id=latest["reflection_id"],
            priority=0.4,
            updated_at=_epoch(latest["recorded_at"]),
        )]


__all__ = [
    "REFLECTION_DETAIL_VERSION",
    "DEFAULT_LOG_PATH",
    "DETERMINISTIC_TRIGGERS",
    "DEEP_ERROR_CLASSES",
    "ReflectionDetailError",
    "ReflectionDetailService",
    "ReflectionDetailBridge",
    "reflection_level",
]
