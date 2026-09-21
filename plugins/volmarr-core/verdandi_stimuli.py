"""Bounded, cursor-based intake of typed Verðandi regulatory stimuli."""

from __future__ import annotations

import json
import os
import socket
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home
from utils import atomic_json_write

from .affective import AffectiveEvent, AffectiveNervousSystem
from .verdandi import VerdandiSettings


CURSOR_SCHEMA = "runeforge.verdandi-affective-cursor"
CURSOR_VERSION = 1
CURSOR_PATH = Path("affective") / "verdandi_cursor.json"
MAX_RESPONSE_BYTES = 64 * 1024

try:
    import fcntl
except ImportError:  # pragma: no cover - platform branch
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover - platform branch
    msvcrt = None


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "yes", "on", "1"}:
            return True
        if normalized in {"false", "no", "off", "0", ""}:
            return False
    return default


def _bounded_count(value: Any) -> int:
    if isinstance(value, bool):
        return 32
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return 32
    return min(128, max(1, parsed))


def _sequence(value: Any) -> int | None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > 2**63 - 1
    ):
        return None
    return value


def _scaled_intensity(data: dict[str, Any], scale: float) -> float:
    value = data.get("intensity", 1)
    if isinstance(value, bool):
        return scale
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return scale
    if parsed != parsed or parsed in {float("inf"), float("-inf")}:
        return scale
    return min(0.35, max(0.01, parsed * scale))


@dataclass(frozen=True)
class RecentBatch:
    events: tuple[dict[str, Any], ...]
    total: int


class VerdandiRecentClient:
    """Read one bounded recent-event page from the official local UDS contract."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx

    def fetch(self) -> RecentBatch | None:
        socket_family = getattr(socket, "AF_UNIX", None)
        if socket_family is None:
            return None
        settings = VerdandiSettings.from_plugin_context(self._ctx)
        count = _bounded_count(
            self._ctx.get_config("affective_verdandi_recent_count", 32)
        )
        request = json.dumps(
            {"nerve_type": "recent", "count": count},
            separators=(",", ":"),
        ).encode("utf-8") + b"\n"
        try:
            with socket.socket(socket_family, socket.SOCK_STREAM) as client:
                client.settimeout(settings.timeout_seconds)
                client.connect(str(settings.socket_path))
                client.sendall(request)
                payload = self._read_line(client)
        except Exception:
            return None
        try:
            response = json.loads(payload.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            return None
        if not isinstance(response, dict) or response.get("nerve_type") != "recent_events":
            return None
        raw_events = response.get("events")
        total = _sequence(response.get("total"))
        if not isinstance(raw_events, list) or total is None or len(raw_events) > count:
            return None
        events = tuple(event for event in raw_events if isinstance(event, dict))
        return RecentBatch(events=events, total=total)

    @staticmethod
    def _read_line(client) -> bytes:
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = client.recv(min(8192, MAX_RESPONSE_BYTES + 1 - size))
            if not chunk:
                raise ValueError("incomplete Verðandi recent response")
            newline = chunk.find(b"\n")
            if newline >= 0:
                chunk = chunk[:newline]
            chunks.append(chunk)
            size += len(chunk)
            if size > MAX_RESPONSE_BYTES:
                raise ValueError("oversized Verðandi recent response")
            if newline >= 0:
                return b"".join(chunks)


def map_stimulus(event: dict[str, Any], session_id: str) -> list[AffectiveEvent]:
    """Map official metadata fields only; external free text is intentionally ignored."""
    event_type = event.get("type")
    source = event.get("source")
    data = event.get("data")
    if not isinstance(event_type, str) or not isinstance(source, str):
        return []
    if not isinstance(data, dict):
        return []

    if event_type == "runa_reward" and source == "reward_system":
        return [
            AffectiveEvent(
                "response_completed",
                "Verðandi reported a bounded positive regulatory stimulus.",
                _scaled_intensity(data, 0.02),
                session_id,
            )
        ]
    if event_type == "runa_negative" and source == "negative_system":
        return [
            AffectiveEvent(
                "discomfort_signal",
                "Verðandi reported a bounded negative regulatory stimulus.",
                _scaled_intensity(data, 0.025),
                session_id,
            )
        ]
    if event_type == "push_reward" and source == "push_reward":
        return [
            AffectiveEvent(
                "github_pushed",
                "Verðandi confirmed a repository push reward.",
                _scaled_intensity(data, 0.03),
                session_id,
            )
        ]
    if event_type == "conv_event" and source.startswith("conv_logger:"):
        kind = data.get("event_type")
        mapping = {
            "blocker": (
                "issue_deferred",
                "Verðandi reported an unresolved conversation blocker.",
                0.08,
            ),
            "blocker_resolved": (
                "issue_fixed",
                "Verðandi reported a resolved conversation blocker.",
                0.10,
            ),
            "milestone": (
                "follow_through_completed",
                "Verðandi reported a completed conversation milestone.",
                0.08,
            ),
        }
        mapped = mapping.get(kind)
        if mapped:
            return [AffectiveEvent(*mapped, session_id=session_id)]
    return []


class VerdandiStimulusBridge:
    """Advance a durable cursor only after classified stimuli are committed."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._client = VerdandiRecentClient(ctx)
        self._enabled = _as_bool(
            ctx.get_config("affective_verdandi_enabled", True),
            True,
        )

    @staticmethod
    def _cursor_path() -> Path:
        return get_hermes_home().resolve() / CURSOR_PATH

    def sync(self, system: AffectiveNervousSystem, session_id: str) -> None:
        if not self._enabled:
            return
        batch = self._client.fetch()
        if batch is None:
            return
        with self._cursor_lock():
            cursor = self._read_cursor()
            if cursor is None:
                self._write_cursor(batch.total)
                return
            unseen = []
            max_seq = cursor
            for event in batch.events:
                seq = _sequence(event.get("_seq"))
                if seq is None or seq <= cursor:
                    continue
                max_seq = max(max_seq, seq)
                unseen.extend(map_stimulus(event, session_id))
            max_seq = max(max_seq, batch.total)
            if unseen and not system.observe_events(unseen, session_id=session_id):
                return
            self._write_cursor(max_seq)

    def _read_cursor(self) -> int | None:
        path = self._cursor_path()
        if not path.is_file() or path.is_symlink():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None
        if (
            not isinstance(data, dict)
            or data.get("schema") != CURSOR_SCHEMA
            or data.get("version") != CURSOR_VERSION
        ):
            return None
        return _sequence(data.get("last_seq"))

    def _write_cursor(self, sequence: int) -> None:
        atomic_json_write(
            self._cursor_path(),
            {
                "schema": CURSOR_SCHEMA,
                "version": CURSOR_VERSION,
                "last_seq": sequence,
            },
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            mode=0o600,
        )

    @contextmanager
    def _cursor_lock(self):
        path = self._cursor_path()
        lock_path = path.with_suffix(path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
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
