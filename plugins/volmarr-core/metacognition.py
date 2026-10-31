"""Metacognition store (Emergent Agency Phase 3, roadmap §10).

Structured evaluation of the entity's own cognition and behaviour:
what was expected, what happened, how confidence calibrated against
reality, what failed, and what strategy should change. Two durable
files under the stable entity identity:

- ``entity/metacognition.json`` — the compact current summary
  (calibration buckets, totals, recent lessons and strategy changes);
- ``entity/reflection_log.jsonl`` — the bounded, rotated history of
  :class:`ReflectionRecord` conclusions.

Reflections store conclusions only. The Phase 0 ``ReflectionRecord``
contract has no field that could carry raw chain-of-thought, and this
module never writes one. Recording is deterministic: the calibration
label and bucket updates are pure functions of the record. Feedback
into other systems is *proposals only* — this module may hand
self-model evidence candidates to the self-model store's own merge
layer (which validates and decides), and it never rewrites the
self-model, identity, goals, drives, or autonomy policy directly.
Reflection fails open at the bridge: a failed reflection never
invalidates durable state.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home, mkdir_under_hermes_home
from utils import atomic_json_write, atomic_write_text

from .agency_contracts import AgencyContractError, Provenance, ReflectionRecord
from .context_packet import ContextItem
from .identity import IdentityError, IdentityStore, _as_bool

METACOGNITION_VERSION = 1
DEFAULT_METACOGNITION_PATH = Path("entity") / "metacognition.json"
DEFAULT_REFLECTION_LOG_PATH = Path("entity") / "reflection_log.jsonl"
MAX_SUMMARY_BYTES = 1024 * 1024
MAX_LOG_BYTES = 8 * 1024 * 1024
MAX_LOG_ENTRIES = 500
MAX_RECENT = 10
MAX_CANDIDATES = 10
MAX_STRATEGY_CHANGES = 10
MAX_TEXT_CHARS = 500

# High-value reflection triggers only (roadmap §10) — never per token
# or per trivial message.
REFLECTION_TRIGGERS = frozenset({
    "goal_completed",
    "goal_failed",
    "repeated_tool_failure",
    "user_correction",
    "success_verified",
    "surprising_world_change",
    "significant_autonomous_action",
    "daily_consolidation",
    "model_escalation",
})

CALIBRATION_BUCKETS = ("0.0-0.2", "0.2-0.4", "0.4-0.6", "0.6-0.8", "0.8-1.0")

_CANDIDATE_DOMAINS = frozenset(
    {"identity", "capability", "preference", "commitment", "limitation", "uncertainty"}
)
_CANDIDATE_EVIDENCE = frozenset({"positive", "contradiction"})

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


class MetacognitionError(RuntimeError):
    """The metacognition store cannot be safely read or changed."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _timestamp_ok(value: Any, *, empty: bool = False) -> bool:
    if empty and value == "":
        return True
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _parse_ts(value: str) -> float:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def calibration_bucket(predicted_success: float) -> str:
    """The §10 calibration bucket for a predicted success probability."""
    index = min(4, max(0, int(predicted_success * 5)))
    return CALIBRATION_BUCKETS[index]


def calibration_label(record: ReflectionRecord) -> str:
    """Deterministic calibration verdict for one reflection.

    ``partial`` / ``unknown`` outcomes and missing predictions carry
    no calibration signal and are labelled ``uncalibrated``.
    """
    if record.predicted_success is None or record.observed_outcome not in ("success", "failure"):
        return "uncalibrated"
    if record.observed_outcome == "success":
        if record.predicted_success < 0.4:
            return "underconfident"
        return "calibrated"
    if record.predicted_success > 0.6:
        return "overconfident"
    return "calibrated"


def _empty_calibration() -> dict[str, dict[str, int]]:
    return {bucket: {"count": 0, "successes": 0} for bucket in CALIBRATION_BUCKETS}


class MetacognitionStore:
    """Versioned reflection summary + bounded JSONL reflection history."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("metacognition_enabled", True), True
        )

    def _resolve(self, key: str, default: Path) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(key, str(default))))
        if configured.is_absolute():
            configured = default
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / default
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise MetacognitionError("metacognition path resolves outside the active profile")
        # Resolution hides a symlinked final component; return the
        # lexical path in that case so the readers refuse it (the
        # Slice 87 probe lesson).
        if lexical.is_symlink():
            return lexical
        return candidate

    def summary_path(self) -> Path:
        return self._resolve("metacognition_path", DEFAULT_METACOGNITION_PATH)

    def log_path(self) -> Path:
        return self._resolve("metacognition_log_path", DEFAULT_REFLECTION_LOG_PATH)

    def _log_limit(self) -> int:
        try:
            value = int(self._ctx.get_config("metacognition_log_limit", MAX_LOG_ENTRIES))
        except (TypeError, ValueError):
            value = MAX_LOG_ENTRIES
        return min(MAX_LOG_ENTRIES, max(10, value))

    # -- lifecycle ------------------------------------------------------
    def ensure(self) -> dict[str, Any]:
        owner = self._identity.ensure().entity_id
        summary_path = self.summary_path()
        with self._lock(summary_path):
            if summary_path.exists():
                data = self._read_summary_unlocked(summary_path, owner)
            else:
                data = {
                    "metacognition_version": METACOGNITION_VERSION,
                    "owner_entity_id": owner,
                    "updated_at": _now(),
                    "total_reflections": 0,
                    "calibration": _empty_calibration(),
                    "last_reflection_at": "",
                    "recent_lessons": [],
                    "recent_strategy_changes": [],
                }
                self._write_summary(summary_path, data)
            log_path = self.log_path()
            if not log_path.exists():
                mkdir_under_hermes_home(log_path.parent)
                log_path.touch(mode=0o600)
            elif log_path.is_symlink():
                raise MetacognitionError("reflection log must not be a symbolic link")
            return data

    def summary(self) -> dict[str, Any]:
        owner = self._identity.read().entity_id
        path = self.summary_path()
        with self._lock(path):
            return self._read_summary_unlocked(path, owner)

    # -- recording --------------------------------------------------------
    def record_reflection(
        self,
        record: ReflectionRecord,
        *,
        self_model_candidates: Any = (),
        strategy_changes: Any = (),
    ) -> ReflectionRecord:
        """Append one structured reflection and fold it into the summary.

        ``self_model_candidates`` / ``strategy_changes`` are validated
        and *returned as proposals* by :meth:`proposals_for`; recording
        itself never touches another store.
        """
        if not isinstance(record, ReflectionRecord):
            raise MetacognitionError("reflection must be a ReflectionRecord contract record")
        if record.trigger not in REFLECTION_TRIGGERS:
            raise MetacognitionError("reflection trigger is not a recognised high-value trigger")
        self._validate_candidates(self_model_candidates)
        changes = self._validate_strategy_changes(strategy_changes)
        owner = self._identity.read().entity_id
        if record.owner_entity_id != owner:
            raise MetacognitionError("reflection owner does not match entity identity")
        summary_path = self.summary_path()
        log_path = self.log_path()
        with self._lock(summary_path):
            data = self._read_summary_unlocked(summary_path, owner)
            if log_path.is_symlink():
                raise MetacognitionError("reflection log must not be a symbolic link")
            line = json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True)
            mkdir_under_hermes_home(log_path.parent)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            self._rotate_log_unlocked(log_path)
            data["total_reflections"] = int(data["total_reflections"]) + 1
            data["last_reflection_at"] = record.created_at
            data["updated_at"] = _now()
            if record.predicted_success is not None and record.observed_outcome in (
                "success",
                "failure",
            ):
                bucket = data["calibration"][calibration_bucket(record.predicted_success)]
                bucket["count"] = int(bucket["count"]) + 1
                if record.observed_outcome == "success":
                    bucket["successes"] = int(bucket["successes"]) + 1
            lessons = list(data["recent_lessons"])
            for lesson in record.lessons:
                lessons.append(
                    {
                        "lesson": lesson,
                        "reflection_id": record.reflection_id,
                        "trigger": record.trigger,
                        "created_at": record.created_at,
                    }
                )
            data["recent_lessons"] = lessons[-MAX_RECENT:]
            strategies = list(data["recent_strategy_changes"])
            for change in changes:
                strategies.append(
                    {
                        "change": change,
                        "reflection_id": record.reflection_id,
                        "created_at": record.created_at,
                    }
                )
            data["recent_strategy_changes"] = strategies[-MAX_RECENT:]
            self._write_summary(summary_path, data)
            return record

    def reflections(self, *, limit: int = 20) -> list[ReflectionRecord]:
        """The most recent reflections, oldest first, strictly parsed."""
        owner = self._identity.read().entity_id
        log_path = self.log_path()
        summary_path = self.summary_path()
        with self._lock(summary_path):
            if log_path.is_symlink():
                raise MetacognitionError("reflection log must not be a symbolic link")
            if not log_path.is_file():
                raise MetacognitionError("reflection log is missing")
            try:
                if log_path.stat().st_size > MAX_LOG_BYTES:
                    raise MetacognitionError("reflection log exceeds its size limit")
                lines = log_path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeError) as exc:
                raise MetacognitionError("reflection log is unreadable") from exc
        bounded = max(1, min(MAX_LOG_ENTRIES, int(limit)))
        out: list[ReflectionRecord] = []
        for line in lines[-bounded:]:
            if not line.strip():
                continue
            try:
                record = ReflectionRecord.from_dict(json.loads(line))
            except (AgencyContractError, ValueError, TypeError, KeyError) as exc:
                raise MetacognitionError("reflection log entry is invalid") from exc
            if record.owner_entity_id != owner:
                raise MetacognitionError("reflection log entry owner does not match identity")
            out.append(record)
        return out

    def calibration(self) -> dict[str, dict[str, Any]]:
        """Per-bucket counts plus the observed success frequency (§10)."""
        data = self.summary()
        out: dict[str, dict[str, Any]] = {}
        for bucket in CALIBRATION_BUCKETS:
            entry = data["calibration"][bucket]
            count = int(entry["count"])
            successes = int(entry["successes"])
            out[bucket] = {
                "count": count,
                "successes": successes,
                "observed_success_rate": round(successes / count, 6) if count else None,
            }
        return out

    # -- feedback proposals (never direct writes) -------------------------
    @staticmethod
    def _validate_candidates(candidates: Any) -> list[dict[str, str]]:
        if candidates is None:
            return []
        if not isinstance(candidates, (list, tuple)) or len(candidates) > MAX_CANDIDATES:
            raise MetacognitionError("self-model candidates are invalid or oversized")
        out: list[dict[str, str]] = []
        for candidate in candidates:
            if not isinstance(candidate, dict) or set(candidate) != {"domain", "key", "evidence"}:
                raise MetacognitionError("self-model candidate shape is invalid")
            domain, key, evidence = candidate["domain"], candidate["key"], candidate["evidence"]
            if domain not in _CANDIDATE_DOMAINS:
                raise MetacognitionError("self-model candidate domain is not supported")
            if evidence not in _CANDIDATE_EVIDENCE:
                raise MetacognitionError("self-model candidate evidence is invalid")
            if not isinstance(key, str) or not key.strip() or len(key) > 200:
                raise MetacognitionError("self-model candidate key is invalid")
            out.append({"domain": domain, "key": key.strip(), "evidence": evidence})
        return out

    @staticmethod
    def _validate_strategy_changes(changes: Any) -> list[str]:
        if changes is None:
            return []
        if not isinstance(changes, (list, tuple)) or len(changes) > MAX_STRATEGY_CHANGES:
            raise MetacognitionError("strategy changes are invalid or oversized")
        out: list[str] = []
        for change in changes:
            if not isinstance(change, str) or not change.strip() or len(change) > MAX_TEXT_CHARS:
                raise MetacognitionError("strategy change text is invalid")
            out.append(change.strip())
        return out

    def proposals_for(
        self,
        record: ReflectionRecord,
        *,
        self_model_candidates: Any = (),
        strategy_changes: Any = (),
    ) -> list[dict[str, Any]]:
        """Bounded feedback proposals for other domains to validate/merge.

        Pure: reads nothing, writes nothing. Self-model candidates
        become evidence proposals carrying the reflection's own
        provenance; strategy changes become strategy-update proposals.
        """
        candidates = self._validate_candidates(self_model_candidates)
        changes = self._validate_strategy_changes(strategy_changes)
        proposals: list[dict[str, Any]] = []
        for candidate in candidates:
            proposals.append(
                {
                    "kind": "self_model_evidence",
                    "domain": candidate["domain"],
                    "key": candidate["key"],
                    "outcome": candidate["evidence"],
                    "source": record.source.to_dict(),
                    "reflection_id": record.reflection_id,
                }
            )
        for change in changes:
            proposals.append(
                {
                    "kind": "strategy_update",
                    "summary": change,
                    "reflection_id": record.reflection_id,
                }
            )
        return proposals

    def route_self_model_evidence(
        self,
        record: ReflectionRecord,
        *,
        self_model_candidates: Any = (),
    ) -> dict[str, int]:
        """Hand evidence candidates to the self-model's own merge layer.

        The self-model store validates and decides each application;
        candidates for claims that do not exist are skipped, never
        created from here. Returns ``{"applied": n, "skipped": n}``.
        """
        from .self_model import SelfModelError, SelfModelStore

        candidates = self._validate_candidates(self_model_candidates)
        store = SelfModelStore(self._ctx)
        applied = skipped = 0
        for candidate in candidates:
            try:
                store.apply_evidence(
                    candidate["domain"],
                    candidate["key"],
                    outcome=candidate["evidence"],
                    source=record.source,
                )
                applied += 1
            except SelfModelError:
                skipped += 1
        return {"applied": applied, "skipped": skipped}

    # -- reading / validation ---------------------------------------------
    def _read_summary_unlocked(self, path: Path, owner: str) -> dict[str, Any]:
        if path.is_symlink():
            raise MetacognitionError("metacognition file must not be a symbolic link")
        if not path.is_file():
            raise MetacognitionError("metacognition file is missing")
        try:
            if path.stat().st_size > MAX_SUMMARY_BYTES:
                raise MetacognitionError("metacognition file exceeds its size limit")
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as exc:
            raise MetacognitionError("metacognition file is unreadable or malformed") from exc
        if not isinstance(payload, dict):
            raise MetacognitionError("metacognition document must be a mapping")
        version = payload.get("metacognition_version")
        if isinstance(version, bool) or version != METACOGNITION_VERSION:
            raise MetacognitionError("metacognition version is unsupported")
        if payload.get("owner_entity_id") != owner:
            raise MetacognitionError("metacognition owner does not match entity identity")
        if not _timestamp_ok(payload.get("updated_at")):
            raise MetacognitionError("metacognition updated_at is invalid")
        if not _timestamp_ok(payload.get("last_reflection_at"), empty=True):
            raise MetacognitionError("metacognition last_reflection_at is invalid")
        total = payload.get("total_reflections")
        if isinstance(total, bool) or not isinstance(total, int) or total < 0:
            raise MetacognitionError("metacognition total_reflections is invalid")
        calibration = payload.get("calibration")
        if not isinstance(calibration, dict) or set(calibration) != set(CALIBRATION_BUCKETS):
            raise MetacognitionError("metacognition calibration mapping is invalid")
        for bucket in CALIBRATION_BUCKETS:
            entry = calibration[bucket]
            if not isinstance(entry, dict) or set(entry) != {"count", "successes"}:
                raise MetacognitionError("metacognition calibration entry is invalid")
            for value in entry.values():
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise MetacognitionError("metacognition calibration entry is invalid")
            if entry["successes"] > entry["count"]:
                raise MetacognitionError("metacognition calibration entry is invalid")
        for field, text_key in (
            ("recent_lessons", "lesson"),
            ("recent_strategy_changes", "change"),
        ):
            entries = payload.get(field)
            if not isinstance(entries, list) or len(entries) > MAX_RECENT:
                raise MetacognitionError(f"metacognition {field} is invalid or oversized")
            for entry in entries:
                if not isinstance(entry, dict) or not isinstance(entry.get(text_key), str):
                    raise MetacognitionError(f"metacognition {field} entry is invalid")
                if not isinstance(entry.get("reflection_id"), str):
                    raise MetacognitionError(f"metacognition {field} entry is invalid")
                if not _timestamp_ok(entry.get("created_at")):
                    raise MetacognitionError(f"metacognition {field} entry is invalid")
        return payload

    def _rotate_log_unlocked(self, log_path: Path) -> None:
        try:
            if log_path.stat().st_size > MAX_LOG_BYTES:
                raise MetacognitionError("reflection log exceeds its size limit")
            lines = log_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
            raise MetacognitionError("reflection log is unreadable") from exc
        limit = self._log_limit()
        if len(lines) <= limit:
            return
        kept = [line for line in lines[-limit:] if line.strip()]
        atomic_write_text(log_path, "\n".join(kept) + "\n", mode=0o600)

    @staticmethod
    def _write_summary(path: Path, data: dict[str, Any]) -> None:
        atomic_json_write(path, data, mode=0o600)

    @contextmanager
    def _lock(self, path: Path):
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
                yield
            finally:
                lock.seek(0)
                if fcntl is not None:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                elif msvcrt is not None:
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


class MetacognitionBridge:
    """Create the metacognition store at session start; offer its packet.

    Reflection recording is explicit (operator/consolidation calls);
    the bridge never reflects on its own and fails open throughout.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._store = MetacognitionStore(ctx)

    def hooks(self):
        return (("on_session_start", self.on_session_start),)

    def on_session_start(self, **_: Any) -> None:
        if not self._store.enabled():
            return
        try:
            self._store.ensure()
        except (IdentityError, MetacognitionError, OSError):
            return

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not self._store.enabled():
            return []
        try:
            data = self._store.summary()
        except (IdentityError, MetacognitionError, OSError):
            return []
        items: list[ContextItem] = []
        for entry in data["recent_lessons"][-2:]:
            items.append(
                ContextItem(
                    section="current_state",
                    content=(
                        f"Reflection lesson ({entry.get('trigger', 'reflection')}): "
                        f"{entry['lesson']}"
                    ),
                    source="metacognition",
                    record_id=entry["reflection_id"],
                    priority=0.5,
                    updated_at=_parse_ts(entry["created_at"]),
                )
            )
        for entry in data["recent_strategy_changes"][-1:]:
            items.append(
                ContextItem(
                    section="current_state",
                    content=f"Strategy change: {entry['change']}",
                    source="metacognition",
                    record_id=entry["reflection_id"],
                    priority=0.5,
                    updated_at=_parse_ts(entry["created_at"]),
                )
            )
        return items


__all__ = [
    "METACOGNITION_VERSION",
    "DEFAULT_METACOGNITION_PATH",
    "DEFAULT_REFLECTION_LOG_PATH",
    "MAX_LOG_ENTRIES",
    "REFLECTION_TRIGGERS",
    "CALIBRATION_BUCKETS",
    "MetacognitionError",
    "MetacognitionStore",
    "MetacognitionBridge",
    "calibration_bucket",
    "calibration_label",
]
