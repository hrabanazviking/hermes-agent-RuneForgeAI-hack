"""Explicit, profile-local relationship continuity owned by the stable entity."""

from __future__ import annotations

import math
import os
import re
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from hermes_constants import get_hermes_home, mkdir_under_hermes_home
from tools.registry import tool_error, tool_result
from utils import atomic_yaml_write

from .identity import IdentityError, IdentityStore, _as_bool


RELATIONSHIPS_VERSION = 1
DEFAULT_RELATIONSHIPS_PATH = Path("entity") / "relationships.yaml"
MAX_RELATIONSHIPS = 256
MAX_FILE_BYTES = 1024 * 1024
_ENTITY_REF_RE = re.compile(r"^[a-z0-9](?:[a-z0-9_.:-]{0,127})$")
_RELATIONSHIP_TYPE_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_STATUSES = {"active", "inactive", "archived"}

try:
    import fcntl
except ImportError:  # pragma: no cover - platform branch
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover - platform branch
    msvcrt = None


class RelationshipError(RuntimeError):
    """The relationship ledger cannot be safely read or changed."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _bounded_text(value: Any, maximum: int, *, required: bool = True) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if (required and not value) or len(value) > maximum:
        return None
    return value


def _entity_ref(value: Any) -> str | None:
    value = _bounded_text(value, 128)
    return value if value and _ENTITY_REF_RE.fullmatch(value) else None


class RelationshipStore:
    """Versioned relationship state with bounded append-only per-record history."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("relationships_enabled", True), True
        )

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(
            str(
                self._ctx.get_config(
                    "relationships_path", str(DEFAULT_RELATIONSHIPS_PATH)
                )
            )
        )
        if configured.is_absolute():
            configured = DEFAULT_RELATIONSHIPS_PATH
        candidate = (home / configured).resolve()
        if not candidate.is_relative_to(home):
            candidate = (home / DEFAULT_RELATIONSHIPS_PATH).resolve()
        if not candidate.is_relative_to(home):
            raise RelationshipError(
                "relationships path resolves outside the active profile"
            )
        return candidate

    def ensure(self) -> dict[str, Any]:
        owner = self._identity.ensure().entity_id
        path = self.path()
        with self._lock(path):
            if path.exists():
                return self._read_unlocked(path, owner)
            data = self._empty(owner)
            self._write(path, data)
            return data

    def get(self, entity_id: str | None = None) -> dict[str, Any]:
        owner = self._identity.read().entity_id
        path = self.path()
        with self._lock(path):
            data = self._read_unlocked(path, owner)
        if entity_id is None:
            return data
        record = data["relationships"].get(entity_id)
        if record is None:
            raise RelationshipError("relationship was not found")
        return record

    def upsert(
        self,
        *,
        entity_id: str,
        display_name: str,
        relationship_type: str,
        status: str,
        trust: float,
        note: str,
    ) -> dict[str, Any]:
        owner = self._identity.read().entity_id
        if entity_id == owner:
            raise RelationshipError("a relationship cannot target the owning entity")
        path = self.path()
        with self._lock(path):
            data = self._read_unlocked(path, owner)
            relationships = data["relationships"]
            if entity_id not in relationships and len(relationships) >= MAX_RELATIONSHIPS:
                raise RelationshipError("relationship ledger is full")
            timestamp = _now()
            existing = relationships.get(entity_id, {})
            history = list(existing.get("history", []))
            history.append(
                {
                    "event_id": str(uuid.uuid4()),
                    "recorded_at": timestamp,
                    "relationship_type": relationship_type,
                    "status": status,
                    "trust": trust,
                    "note": note,
                }
            )
            history = history[-self._history_limit() :]
            record = {
                "entity_id": entity_id,
                "display_name": display_name,
                "relationship_type": relationship_type,
                "status": status,
                "trust": trust,
                "updated_at": timestamp,
                "history": history,
            }
            relationships[entity_id] = record
            self._write(path, data)
            return record

    def _history_limit(self) -> int:
        try:
            value = int(self._ctx.get_config("relationships_history_limit", 100))
        except (TypeError, ValueError):
            value = 100
        return min(500, max(1, value))

    @staticmethod
    def _empty(owner: str) -> dict[str, Any]:
        return {
            "relationships_version": RELATIONSHIPS_VERSION,
            "owner_entity_id": owner,
            "relationships": {},
        }

    def _read_unlocked(self, path: Path, owner: str) -> dict[str, Any]:
        if path.is_symlink():
            raise RelationshipError("relationships file must not be a symbolic link")
        if not path.is_file():
            raise RelationshipError("relationships file is missing")
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                raise RelationshipError("relationships file exceeds its size limit")
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise RelationshipError("relationships file is unreadable or malformed") from exc
        if not isinstance(payload, dict):
            raise RelationshipError("relationships document must be a mapping")
        version = payload.get("relationships_version")
        if isinstance(version, bool) or version != RELATIONSHIPS_VERSION:
            raise RelationshipError("relationships version is unsupported")
        if payload.get("owner_entity_id") != owner:
            raise RelationshipError("relationships owner does not match entity identity")
        records = payload.get("relationships")
        if not isinstance(records, dict) or len(records) > MAX_RELATIONSHIPS:
            raise RelationshipError("relationships mapping is invalid or oversized")
        for key, record in records.items():
            self._validate_record(key, record)
        return payload

    @staticmethod
    def _validate_record(key: Any, record: Any) -> None:
        if _entity_ref(key) is None or not isinstance(record, dict):
            raise RelationshipError("relationship record is invalid")
        if record.get("entity_id") != key:
            raise RelationshipError("relationship key and entity_id do not match")
        if _bounded_text(record.get("display_name"), 128) is None:
            raise RelationshipError("relationship display_name is invalid")
        relationship_type = record.get("relationship_type")
        if not isinstance(relationship_type, str) or not _RELATIONSHIP_TYPE_RE.fullmatch(
            relationship_type
        ):
            raise RelationshipError("relationship type is invalid")
        if record.get("status") not in _STATUSES:
            raise RelationshipError("relationship status is invalid")
        trust = record.get("trust")
        if (
            isinstance(trust, bool)
            or not isinstance(trust, (int, float))
            or not math.isfinite(float(trust))
            or not 0 <= float(trust) <= 1
        ):
            raise RelationshipError("relationship trust is invalid")
        if not RelationshipStore._valid_timestamp(record.get("updated_at")):
            raise RelationshipError("relationship updated_at is invalid")
        history = record.get("history")
        if not isinstance(history, list) or len(history) > 500:
            raise RelationshipError("relationship history is invalid or oversized")
        for event in history:
            if not isinstance(event, dict):
                raise RelationshipError("relationship history event is invalid")
            try:
                event_id = uuid.UUID(event.get("event_id"))
            except (TypeError, ValueError, AttributeError) as exc:
                raise RelationshipError("relationship history event_id is invalid") from exc
            if str(event_id) != str(event.get("event_id")).lower():
                raise RelationshipError("relationship history event_id is not canonical")
            if not RelationshipStore._valid_timestamp(event.get("recorded_at")):
                raise RelationshipError("relationship history timestamp is invalid")
            event_type = event.get("relationship_type")
            if not isinstance(event_type, str) or not _RELATIONSHIP_TYPE_RE.fullmatch(
                event_type
            ):
                raise RelationshipError("relationship history type is invalid")
            if event.get("status") not in _STATUSES:
                raise RelationshipError("relationship history status is invalid")
            event_trust = event.get("trust")
            if (
                isinstance(event_trust, bool)
                or not isinstance(event_trust, (int, float))
                or not math.isfinite(float(event_trust))
                or not 0 <= float(event_trust) <= 1
            ):
                raise RelationshipError("relationship history trust is invalid")
            if _bounded_text(event.get("note"), 1000, required=False) is None:
                raise RelationshipError("relationship history note is invalid")

    @staticmethod
    def _valid_timestamp(value: Any) -> bool:
        if not isinstance(value, str):
            return False
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False
        return parsed.tzinfo is not None

    @staticmethod
    def _write(path: Path, data: dict[str, Any]) -> None:
        atomic_yaml_write(path, data, sort_keys=False, create_mode=0o600)

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


RELATIONSHIP_GET_SCHEMA = {
    "name": "relationship_get",
    "description": (
        "Read explicit relationship state from the active entity profile. "
        "Omit entity_id to list bounded relationship summaries."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "entity_id": {"type": "string", "maxLength": 128},
            "include_history": {"type": "boolean", "default": False},
        },
        "additionalProperties": False,
    },
}

RELATIONSHIP_UPSERT_SCHEMA = {
    "name": "relationship_upsert",
    "description": (
        "Create or update explicit relationship state and append one bounded history event. "
        "Use status=archived instead of deleting continuity."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "entity_id": {"type": "string", "maxLength": 128},
            "display_name": {"type": "string", "maxLength": 128},
            "relationship_type": {"type": "string", "maxLength": 64},
            "status": {
                "type": "string",
                "enum": ["active", "inactive", "archived"],
            },
            "trust": {"type": "number", "minimum": 0, "maximum": 1},
            "note": {"type": "string", "maxLength": 1000},
        },
        "required": [
            "entity_id",
            "display_name",
            "relationship_type",
            "status",
            "trust",
        ],
        "additionalProperties": False,
    },
}


def build_relationship_get_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        entity_id = args.get("entity_id")
        if entity_id is not None:
            entity_id = _entity_ref(entity_id)
            if entity_id is None:
                return tool_error("entity_id is invalid")
        include_history = args.get("include_history", False)
        if not isinstance(include_history, bool):
            return tool_error("include_history must be a boolean")
        try:
            data = RelationshipStore(ctx).get(entity_id)
        except (IdentityError, RelationshipError, OSError) as exc:
            return tool_error(str(exc))
        if entity_id is not None:
            record = dict(data)
            if not include_history:
                record.pop("history", None)
            return tool_result({"success": True, "relationship": record})
        summaries = []
        for key in sorted(data["relationships"]):
            record = data["relationships"][key]
            summaries.append({name: value for name, value in record.items() if name != "history"})
        return tool_result({"success": True, "relationships": summaries})

    return handle


def build_relationship_upsert_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        entity_id = _entity_ref(args.get("entity_id"))
        display_name = _bounded_text(args.get("display_name"), 128)
        relationship_type = _bounded_text(args.get("relationship_type"), 64)
        status = args.get("status")
        note = _bounded_text(args.get("note", ""), 1000, required=False)
        trust = args.get("trust")
        if entity_id is None:
            return tool_error("entity_id is invalid")
        if display_name is None:
            return tool_error("display_name is required and must not exceed 128 characters")
        if relationship_type is None or not _RELATIONSHIP_TYPE_RE.fullmatch(
            relationship_type
        ):
            return tool_error("relationship_type must be a lowercase identifier")
        if status not in _STATUSES:
            return tool_error("status must be active, inactive, or archived")
        if note is None:
            return tool_error("note must not exceed 1000 characters")
        if (
            isinstance(trust, bool)
            or not isinstance(trust, (int, float))
            or not math.isfinite(float(trust))
            or not 0 <= float(trust) <= 1
        ):
            return tool_error("trust must be a finite number from 0 to 1")
        try:
            record = RelationshipStore(ctx).upsert(
                entity_id=entity_id,
                display_name=display_name,
                relationship_type=relationship_type,
                status=status,
                trust=float(trust),
                note=note,
            )
        except (IdentityError, RelationshipError, OSError) as exc:
            return tool_error(str(exc))
        return tool_result(
            {
                "success": True,
                "entity_id": record["entity_id"],
                "status": record["status"],
                "history_events": len(record["history"]),
            }
        )

    return handle


class RelationshipBridge:
    def __init__(self, ctx) -> None:
        self._store = RelationshipStore(ctx)

    def hooks(self):
        return (("on_session_start", self.on_session_start),)

    def on_session_start(self, **_: Any) -> None:
        if not self._store.enabled():
            return
        try:
            self._store.ensure()
        except (IdentityError, RelationshipError, OSError):
            # Identity health remains explicit; relationship state must never block a turn.
            return


def register_relationship_tools(ctx) -> None:
    ctx.register_tool(
        name="relationship_get",
        toolset="volmarr_identity",
        schema=RELATIONSHIP_GET_SCHEMA,
        handler=build_relationship_get_handler(ctx),
        description=RELATIONSHIP_GET_SCHEMA["description"],
        emoji="🫱🏻‍🫲🏼",
    )
    ctx.register_tool(
        name="relationship_upsert",
        toolset="volmarr_identity",
        schema=RELATIONSHIP_UPSERT_SCHEMA,
        handler=build_relationship_upsert_handler(ctx),
        description=RELATIONSHIP_UPSERT_SCHEMA["description"],
        emoji="🧶",
    )
