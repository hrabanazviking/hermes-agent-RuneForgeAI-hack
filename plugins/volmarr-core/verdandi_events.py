"""Verðandi event families (Self-Aware Agency roadmap §14).

Gate 0 (this slice, audited before any code): the plugin already
owns a profile-safe, fail-open Verðandi publisher
(:mod:`.verdandi`) — one JSON line per event over the profile's
Unix socket, envelope schema ``runeforge.hermes.lifecycle`` —
and lifecycle, cognition, world, heartbeat, consolidation, and
routine surfaces already publish through it. None of them emits
any of the seventeen §14 self-aware families, and the publisher's
context dict is free-form, so the §14 content-free rule cannot be
inherited from the transport: it is enforced here, in this layer.

What stands here:

- the seventeen §14 event types, named in roadmap order
  (:data:`EVENT_TYPES`);
- a strict content-free context allowlist: an event context may
  carry only a subject identifier (canonical UUID or slug), a
  subject class (slug), a unit-interval numeric score, a reason
  code (slug), an outcome (slug), and a non-negative count. There
  is no field that could carry free text, so raw private
  reflections, prompts, secrets, and conversation text cannot be
  placed on the bus through this layer — an unknown key, a
  non-slug string, or an out-of-range number is refused at build
  time and refused again on log read;
- emission is explicit only: :meth:`VerdandiEventsService.emit`
  is called by an operator or a future wiring slice, never by a
  hook, loop, scheduler, or turn-path caller. Delivery goes
  through the existing fail-open publisher under this layer's own
  schema (``runeforge.hermes.self_aware_events``); a dropped
  event (no Verðandi service listening) is recorded honestly as
  ``delivered: false`` and never raises into the caller;
- every emission attempt is recorded in this module's own bounded
  log (``entity/verdandi_events.jsonl``), so what was emitted —
  and whether it landed — is auditable without a live bus.

No store that owns the underlying facts is written by this layer;
it imports none of them. Wiring the owning stores to call
:meth:`emit` at their own transition points would change their
contracts and is a separate slice per family.

Disabled by default.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from hermes_constants import get_hermes_home, mkdir_under_hermes_home

from .context_packet import ContextItem
from .identity import IdentityError, IdentityStore, _as_bool
from .verdandi import VerdandiPublisher

EVENT_VERSION = 1
EVENT_SCHEMA = "runeforge.hermes.self_aware_events"
EVENT_SCHEMA_VERSION = 1
DEFAULT_LOG_PATH = Path("entity") / "verdandi_events.jsonl"
DEFAULT_LOG_LIMIT = 200
MAX_LOG_BYTES = 4 * 1024 * 1024

# The seventeen §14 event types, in roadmap order.
EVENT_TYPES = (
    "hermes.self_model.updated",
    "hermes.awareness.snapshot",
    "hermes.awareness.discrepancy_detected",
    "hermes.reflection.started",
    "hermes.reflection.completed",
    "hermes.motivation.drive_changed",
    "hermes.goal.intrinsic_proposed",
    "hermes.goal.intrinsic_approved",
    "hermes.curiosity.question_created",
    "hermes.curiosity.investigation_started",
    "hermes.curiosity.investigation_completed",
    "hermes.autonomy.action_proposed",
    "hermes.autonomy.action_allowed",
    "hermes.autonomy.action_blocked",
    "hermes.autonomy.approval_required",
    "hermes.agency.cycle_started",
    "hermes.agency.cycle_completed",
)

# The content-free context allowlist (§14): identifiers, classes,
# numeric scores, reason codes, and outcome metadata — nothing else.
_CONTEXT_FIELDS = frozenset({
    "subject_id", "subject_class", "score", "reason_code", "outcome",
    "count",
})
_SLUG = re.compile(r"[a-z0-9][a-z0-9_-]*")

_RECORD_FIELDS = {
    "event_version", "kind", "record_id", "event_type",
    "owner_entity_id", "recorded_at", "context", "delivered",
}

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


class VerdandiEventsError(RuntimeError):
    """A §14 Verðandi event cannot be safely built or read."""


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


def _slug(value: Any) -> bool:
    return isinstance(value, str) and _SLUG.fullmatch(value) is not None


def _validate_context(context: Any) -> dict[str, Any]:
    """Validate a §14 context against the content-free allowlist."""
    if context is None:
        return {}
    if not isinstance(context, Mapping):
        raise VerdandiEventsError("event context is invalid")
    unknown = set(context) - _CONTEXT_FIELDS
    if unknown:
        raise VerdandiEventsError(
            "event context carries a field outside the §14 allowlist: "
            + ", ".join(sorted(str(key) for key in unknown)))
    out: dict[str, Any] = {}
    for key, value in context.items():
        if key == "subject_id":
            if not (_canonical_uuid(value) or _slug(value)):
                raise VerdandiEventsError("event subject_id is invalid")
        elif key in ("subject_class", "reason_code", "outcome"):
            if not _slug(value):
                raise VerdandiEventsError(f"event {key} is invalid")
        elif key == "score":
            if isinstance(value, bool) or not isinstance(value, (int, float)) \
                    or not 0.0 <= float(value) <= 1.0:
                raise VerdandiEventsError("event score is invalid")
            value = float(value)
        elif key == "count":
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise VerdandiEventsError("event count is invalid")
        out[key] = value
    return out


def event_families() -> list[dict[str, Any]]:
    """The seventeen §14 event types, in roadmap order."""
    return [{"event_type": name} for name in EVENT_TYPES]


class VerdandiEventsService:
    """The §14 content-free event layer over the Verðandi publisher."""

    def __init__(self, ctx, publisher: VerdandiPublisher | None = None) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)
        self._publisher = publisher or VerdandiPublisher()

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("verdandi_events_enabled", False), False
        )

    def _limit(self) -> int:
        try:
            value = int(self._ctx.get_config(
                "verdandi_events_log_limit", DEFAULT_LOG_LIMIT))
        except (TypeError, ValueError):
            value = DEFAULT_LOG_LIMIT
        return min(500, max(10, value))

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(
            "verdandi_events_log_path", str(DEFAULT_LOG_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_LOG_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_LOG_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise VerdandiEventsError(
                "verdandi events log path resolves outside the profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    # -- event building ---------------------------------------------------
    def build_event(self, event_type: str,
                    context: Mapping[str, Any] | None = None, *,
                    recorded_at: str | None = None) -> dict[str, Any]:
        """Build a §14 event record. Pure; publishes and records nothing."""
        if event_type not in EVENT_TYPES:
            raise VerdandiEventsError("event type is not a §14 family")
        stamp = recorded_at or _fmt(_now_dt())
        if not _timestamp_ok(stamp):
            raise VerdandiEventsError("event recorded_at is invalid")
        record = {
            "event_version": EVENT_VERSION,
            "kind": "verdandi_event",
            "record_id": str(uuid.uuid4()),
            "event_type": event_type,
            "owner_entity_id": self._identity.read().entity_id,
            "recorded_at": stamp,
            "context": _validate_context(context),
            "delivered": False,
        }
        self._validate(record, record["owner_entity_id"])
        return record

    def emit(self, event_type: str,
             context: Mapping[str, Any] | None = None, *,
             recorded_at: str | None = None) -> dict[str, Any]:
        """Publish one §14 event (fail-open) and record the attempt."""
        if not self.enabled():
            raise VerdandiEventsError("verdandi events are disabled")
        record = self.build_event(event_type, context,
                                  recorded_at=recorded_at)
        record["delivered"] = bool(self._publisher.publish(
            self._ctx, event_type, record["context"],
            schema=EVENT_SCHEMA, schema_version=EVENT_SCHEMA_VERSION))
        self._append(record)
        return record

    def events(self, *, limit: int = 500) -> list[dict[str, Any]]:
        owner = self._identity.read().entity_id
        path = self.path()
        if path.is_symlink():
            raise VerdandiEventsError(
                "verdandi events log must not be a symbolic link")
        if not path.is_file():
            return []
        if path.stat().st_size > MAX_LOG_BYTES:
            raise VerdandiEventsError(
                "verdandi events log exceeds its size limit")
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except ValueError as exc:
                raise VerdandiEventsError(
                    "verdandi events log is malformed") from exc
            self._validate(payload, owner)
            out.append(payload)
        return out[-max(1, min(500, limit)):]

    def _validate(self, payload: Any, owner: str) -> None:
        if not isinstance(payload, dict):
            raise VerdandiEventsError("verdandi event is invalid")
        if set(payload) != _RECORD_FIELDS:
            raise VerdandiEventsError("verdandi event fields are invalid")
        if payload.get("event_version") != EVENT_VERSION:
            raise VerdandiEventsError("verdandi event version is unsupported")
        if payload.get("kind") != "verdandi_event":
            raise VerdandiEventsError("verdandi event kind is invalid")
        if payload.get("owner_entity_id") != owner:
            raise VerdandiEventsError(
                "verdandi event owner does not match entity identity")
        if not _canonical_uuid(payload.get("record_id")):
            raise VerdandiEventsError("verdandi event id is invalid")
        if payload.get("event_type") not in EVENT_TYPES:
            raise VerdandiEventsError("verdandi event type is invalid")
        if not _timestamp_ok(payload.get("recorded_at")):
            raise VerdandiEventsError("verdandi event recorded_at is invalid")
        if not isinstance(payload.get("delivered"), bool):
            raise VerdandiEventsError("verdandi event delivered is invalid")
        _validate_context(payload.get("context"))

    def _append(self, record: dict[str, Any]) -> None:
        path = self.path()
        if path.is_symlink():
            raise VerdandiEventsError(
                "verdandi events log must not be a symbolic link")
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
                    raise VerdandiEventsError(
                        "verdandi events log exceeds its size limit")
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


class VerdandiEventsBridge:
    """Surface the latest §14 event, content-bearing only.

    No session hook — events are emitted only by explicit calls.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._service = VerdandiEventsService(ctx)

    def hooks(self):
        return ()

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not _as_bool(
            self._ctx.get_config("verdandi_events_enabled", False), False
        ):
            return []
        try:
            events = self._service.events(limit=1)
        except (IdentityError, VerdandiEventsError, OSError):
            return []
        if not events:
            return []
        latest = events[-1]
        state = "delivered" if latest["delivered"] else "dropped (no listener)"
        return [ContextItem(
            section="current_state",
            content=(
                f"Verðandi event (§14): {latest['event_type']} {state}"
            ),
            source="verdandi_events",
            record_id=latest["record_id"],
            priority=0.5,
            updated_at=_epoch(latest["recorded_at"]),
        )]


__all__ = [
    "EVENT_VERSION",
    "EVENT_SCHEMA",
    "EVENT_SCHEMA_VERSION",
    "DEFAULT_LOG_PATH",
    "EVENT_TYPES",
    "VerdandiEventsError",
    "VerdandiEventsService",
    "VerdandiEventsBridge",
    "event_families",
]
