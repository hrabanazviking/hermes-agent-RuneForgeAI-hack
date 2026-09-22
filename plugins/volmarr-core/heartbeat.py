"""Deterministic continuity heartbeat; scheduling remains owned by Hermes cron."""

from __future__ import annotations

import json
import math
import os
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home, mkdir_under_hermes_home
from tools.registry import tool_error, tool_result
from utils import atomic_json_write

from .identity import IdentityError, IdentityStore, _as_bool
from .verdandi import VerdandiPublisher


CONTINUITY_VERSION = 1
HEARTBEAT_SCHEMA = "runeforge.entity.heartbeat"
HEARTBEAT_SCHEMA_VERSION = 1
DEFAULT_CONTINUITY_PATH = Path("entity") / "continuity.json"
MAX_FILE_BYTES = 64 * 1024
PULSE_SOURCES = {"manual", "cron", "tool"}

try:
    import fcntl
except ImportError:  # pragma: no cover - platform branch
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover - platform branch
    msvcrt = None


class HeartbeatError(RuntimeError):
    """Continuity heartbeat state cannot be safely read or changed."""


@dataclass(frozen=True)
class HeartbeatReport:
    healthy: bool
    status: str
    continuity_path: str
    sequence: int | None = None
    last_heartbeat_at: str | None = None
    age_seconds: float | None = None
    stale_after_seconds: int | None = None
    last_source: str | None = None
    event_published: bool | None = None
    resumed: bool | None = None
    error_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _format_time(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _parse_time(value: Any, *, empty: bool = False) -> datetime | None:
    if empty and value == "":
        return None
    if not isinstance(value, str):
        raise HeartbeatError("heartbeat timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HeartbeatError("heartbeat timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise HeartbeatError("heartbeat timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


class HeartbeatStore:
    """Persist pulse receipts while leaving cadence and dispatch to Hermes cron."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("heartbeat_enabled", True), True
        )

    def stale_after_seconds(self) -> int:
        try:
            value = int(self._ctx.get_config("heartbeat_stale_after_seconds", 900))
        except (TypeError, ValueError):
            value = 900
        return min(86_400, max(60, value))

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(
            str(self._ctx.get_config("continuity_path", str(DEFAULT_CONTINUITY_PATH)))
        )
        if configured.is_absolute():
            configured = DEFAULT_CONTINUITY_PATH
        candidate = (home / configured).resolve()
        if not candidate.is_relative_to(home):
            candidate = (home / DEFAULT_CONTINUITY_PATH).resolve()
        if not candidate.is_relative_to(home):
            raise HeartbeatError("continuity path resolves outside the active profile")
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

    def read(self) -> dict[str, Any]:
        owner = self._identity.read().entity_id
        path = self.path()
        with self._lock(path):
            return self._read_unlocked(path, owner)

    def pulse(self, source: str) -> tuple[dict[str, Any], bool]:
        if source not in PULSE_SOURCES:
            raise HeartbeatError("heartbeat source is invalid")
        owner = self._identity.read().entity_id
        path = self.path()
        with self._lock(path):
            data = self._read_unlocked(path, owner)
            now = _utc_now()
            previous = _parse_time(data["last_heartbeat_at"], empty=True)
            resumed = bool(
                previous is not None
                and (now - previous).total_seconds() > self.stale_after_seconds()
            )
            data["heartbeat_sequence"] += 1
            data["last_heartbeat_at"] = _format_time(now)
            data["last_source"] = source
            self._write(path, data)
            return data, resumed

    @staticmethod
    def _empty(owner: str) -> dict[str, Any]:
        return {
            "continuity_version": CONTINUITY_VERSION,
            "owner_entity_id": owner,
            "heartbeat_sequence": 0,
            "last_heartbeat_at": "",
            "last_source": "",
        }

    def _read_unlocked(self, path: Path, owner: str) -> dict[str, Any]:
        if path.is_symlink():
            raise HeartbeatError("continuity file must not be a symbolic link")
        if not path.is_file():
            raise HeartbeatError("continuity file is missing")
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                raise HeartbeatError("continuity file exceeds its size limit")
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise HeartbeatError("continuity file is unreadable or malformed") from exc
        if not isinstance(payload, dict):
            raise HeartbeatError("continuity document must be a mapping")
        version = payload.get("continuity_version")
        if isinstance(version, bool) or version != CONTINUITY_VERSION:
            raise HeartbeatError("continuity version is unsupported")
        if payload.get("owner_entity_id") != owner:
            raise HeartbeatError("continuity owner does not match entity identity")
        sequence = payload.get("heartbeat_sequence")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
            raise HeartbeatError("heartbeat sequence is invalid")
        last_at = payload.get("last_heartbeat_at")
        last_source = payload.get("last_source")
        if sequence == 0:
            if last_at != "" or last_source != "":
                raise HeartbeatError("idle continuity state is inconsistent")
        else:
            _parse_time(last_at)
            if last_source not in PULSE_SOURCES:
                raise HeartbeatError("last heartbeat source is invalid")
        return payload

    @staticmethod
    def _write(path: Path, data: dict[str, Any]) -> None:
        atomic_json_write(
            path,
            data,
            indent=2,
            sort_keys=False,
            ensure_ascii=False,
            mode=0o600,
        )

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


class HeartbeatService:
    def __init__(self, ctx, publisher: VerdandiPublisher | None = None) -> None:
        self._ctx = ctx
        self._store = HeartbeatStore(ctx)
        self._publisher = publisher or VerdandiPublisher()

    def pulse(self, source: str) -> HeartbeatReport:
        self._store.ensure()
        data, resumed = self._store.pulse(source)
        event_type = "hermes.entity.resumed" if resumed else "hermes.entity.heartbeat"
        published = self._publisher.publish(
            self._ctx,
            event_type,
            {
                "heartbeat_sequence": data["heartbeat_sequence"],
                "source": source,
                "resumed": resumed,
            },
            schema=HEARTBEAT_SCHEMA,
            schema_version=HEARTBEAT_SCHEMA_VERSION,
        )
        return HeartbeatReport(
            True,
            "resumed" if resumed else "healthy",
            str(self._store.path()),
            sequence=data["heartbeat_sequence"],
            last_heartbeat_at=data["last_heartbeat_at"],
            age_seconds=0.0,
            stale_after_seconds=self._store.stale_after_seconds(),
            last_source=source,
            event_published=published,
            resumed=resumed,
        )


def probe_heartbeat(ctx) -> HeartbeatReport:
    store = HeartbeatStore(ctx)
    try:
        path = store.path()
    except HeartbeatError as exc:
        return HeartbeatReport(False, "unsafe_path", "", error_type=type(exc).__name__)
    if not store.enabled():
        return HeartbeatReport(False, "disabled", str(path))
    try:
        data = store.read()
        threshold = store.stale_after_seconds()
        if data["heartbeat_sequence"] == 0:
            return HeartbeatReport(
                False,
                "idle",
                str(path),
                sequence=0,
                stale_after_seconds=threshold,
            )
        last = _parse_time(data["last_heartbeat_at"])
        age = max(0.0, (_utc_now() - last).total_seconds())
        if not math.isfinite(age):
            raise HeartbeatError("heartbeat age is invalid")
        healthy = age <= threshold
        return HeartbeatReport(
            healthy,
            "healthy" if healthy else "stale",
            str(path),
            sequence=data["heartbeat_sequence"],
            last_heartbeat_at=data["last_heartbeat_at"],
            age_seconds=round(age, 3),
            stale_after_seconds=threshold,
            last_source=data["last_source"],
        )
    except (IdentityError, HeartbeatError, OSError) as exc:
        status = "missing" if not path.exists() else "invalid"
        return HeartbeatReport(
            False,
            status,
            str(path),
            error_type=type(exc).__name__,
        )


ENTITY_HEARTBEAT_SCHEMA = {
    "name": "entity_heartbeat",
    "description": (
        "Record one deterministic continuity pulse for the active entity. "
        "Hermes cron owns recurring scheduling; this tool starts no background loop."
    ),
    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
}


def build_entity_heartbeat_handler(ctx):
    def handle(_args: dict[str, Any], **_kwargs: Any) -> str:
        try:
            report = HeartbeatService(ctx).pulse("tool")
        except (IdentityError, HeartbeatError, OSError) as exc:
            return tool_error(str(exc))
        return tool_result(report.as_dict())

    return handle


class HeartbeatBridge:
    def __init__(self, ctx) -> None:
        self._store = HeartbeatStore(ctx)

    def hooks(self):
        return (("on_session_start", self.on_session_start),)

    def on_session_start(self, **_: Any) -> None:
        if not self._store.enabled():
            return
        try:
            self._store.ensure()
        except (IdentityError, HeartbeatError, OSError):
            return


def register_heartbeat_tool(ctx) -> None:
    ctx.register_tool(
        name="entity_heartbeat",
        toolset="volmarr_identity",
        schema=ENTITY_HEARTBEAT_SCHEMA,
        handler=build_entity_heartbeat_handler(ctx),
        description=ENTITY_HEARTBEAT_SCHEMA["description"],
        emoji="💓",
    )
