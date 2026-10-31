"""Self-awareness layer (Self-Aware Agency roadmap §6).

The self-model is stored knowledge about the entity; self-awareness
is the current-state process that asks what is true about the entity
right now and what deserves its attention. This module keeps exactly
one small, non-historical snapshot at ``entity/awareness.json``:

- ``attention_target`` — the top active goal's title;
- ``current_goal_ids`` — the active goal ids;
- ``uncertainty`` / ``cognitive_load`` — the experiential layer's
  uncertainty and the blocked share of live goals;
- ``salient_discrepancies`` — bounded detail strings taken from the
  Slice 103 layered self-model's structured discrepancy list (§6.4:
  objective vs narrative/ideal, current state vs active goal,
  confidence vs evidence — the layered assembly already performs
  those deterministic comparisons, so this layer surfaces them
  rather than duplicating a second discrepancy engine);
- ``known_blind_spots`` — the layered model's low-confidence active
  assumptions, formatted as bounded strings;
- ``reflection_recommended`` + ``reflection_triggers`` — §6.5's
  no-constant-rumination bound in code: reflection is recommended
  only when a named trigger is present (a salient discrepancy, a
  blocked goal, high uncertainty, or unresolved contradictions).
  A clean snapshot recommends nothing; this module never reflects,
  loops, or observes itself observing.

The snapshot is current state, not a diary: ``refresh()`` replaces
the file atomically with a newly assembled snapshot, and historical
observations belong in the reflection/memory stores, not here. The
only file this module ever writes is its own snapshot. Disabled by
default; assembling a snapshot additionally requires the layered
self-model (Slice 103), which owns the underlying comparisons.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home, mkdir_under_hermes_home
from utils import atomic_json_write

from .context_packet import ContextItem
from .identity import IdentityError, IdentityStore, _as_bool
from .self_model_layers import LayeredSelfModelError, LayeredSelfModelService

AWARENESS_VERSION = 1
DEFAULT_AWARENESS_PATH = Path("entity") / "awareness.json"
MAX_SNAPSHOT_BYTES = 64 * 1024
MAX_GOAL_IDS = 10
MAX_DISCREPANCIES = 5
MAX_BLIND_SPOTS = 5
MAX_TEXT_CHARS = 500
HIGH_UNCERTAINTY = 0.7

_FIELDS = {
    "awareness_version", "owner_entity_id", "observed_at",
    "attention_target", "current_goal_ids", "uncertainty",
    "cognitive_load", "salient_discrepancies", "known_blind_spots",
    "reflection_recommended", "reflection_triggers",
}
TRIGGERS = frozenset({
    "salient_discrepancy", "blocked_goal", "high_uncertainty",
    "unresolved_contradiction",
})

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


class AwarenessError(RuntimeError):
    """The awareness snapshot cannot be safely read or refreshed."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_ts(value: str) -> float:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _timestamp_ok(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _unit(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and 0.0 <= float(value) <= 1.0
    )


class AwarenessStore:
    """The bounded, replaceable current awareness snapshot (§6.2)."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("awareness_enabled", False), False
        )

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(
            "awareness_path", str(DEFAULT_AWARENESS_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_AWARENESS_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_AWARENESS_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise AwarenessError("awareness path resolves outside the active profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    # -- lifecycle ------------------------------------------------------
    def _empty(self, owner: str) -> dict[str, Any]:
        return {
            "awareness_version": AWARENESS_VERSION,
            "owner_entity_id": owner,
            "observed_at": _now(),
            "attention_target": "",
            "current_goal_ids": [],
            "uncertainty": 0.0,
            "cognitive_load": 0.0,
            "salient_discrepancies": [],
            "known_blind_spots": [],
            "reflection_recommended": False,
            "reflection_triggers": [],
        }

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

    def refresh(self, *, now: str | None = None) -> dict[str, Any]:
        """Replace the snapshot with one assembled from Slice 103.

        Deterministic in its sources: identical layered state yields
        identical content apart from ``observed_at``. §6.5 triggers
        are computed here and nowhere else.
        """
        if not self.enabled():
            raise AwarenessError("self-awareness layer is disabled")
        owner = self._identity.read().entity_id
        try:
            layered = LayeredSelfModelService(self._ctx).snapshot()
        except LayeredSelfModelError as exc:
            raise AwarenessError(str(exc)) from exc
        experiential = layered["experiential"]
        discrepancies = [
            str(item["detail"])[:MAX_TEXT_CHARS]
            for item in layered["discrepancies"][:MAX_DISCREPANCIES]
        ]
        blind_spots = [
            f"{item['domain']}/{item['key']}: low confidence "
            f"{float(item['confidence']):.2f}"
            for item in layered["active_assumptions"][:MAX_BLIND_SPOTS]
        ]
        triggers: list[str] = []
        if discrepancies:
            triggers.append("salient_discrepancy")
        if experiential["blocked"]:
            triggers.append("blocked_goal")
        if float(experiential["uncertainty"]) >= HIGH_UNCERTAINTY:
            triggers.append("high_uncertainty")
        if layered["unresolved_contradictions"]:
            triggers.append("unresolved_contradiction")
        data = {
            "awareness_version": AWARENESS_VERSION,
            "owner_entity_id": owner,
            "observed_at": now or _now(),
            "attention_target": str(experiential["attention"])[:MAX_TEXT_CHARS],
            "current_goal_ids": [
                str(goal_id) for goal_id in experiential["active_goal_ids"][:MAX_GOAL_IDS]
            ],
            "uncertainty": float(experiential["uncertainty"]),
            "cognitive_load": float(experiential["load"]),
            "salient_discrepancies": discrepancies,
            "known_blind_spots": blind_spots,
            "reflection_recommended": bool(triggers),
            "reflection_triggers": triggers,
        }
        path = self.path()
        with self._lock(path):
            self._write(path, data)
        return data

    # -- reading / validation ---------------------------------------------
    def _read_unlocked(self, path: Path, owner: str) -> dict[str, Any]:
        if path.is_symlink():
            raise AwarenessError("awareness file must not be a symbolic link")
        if not path.is_file():
            raise AwarenessError("awareness file is missing")
        try:
            if path.stat().st_size > MAX_SNAPSHOT_BYTES:
                raise AwarenessError("awareness file exceeds its size limit")
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as exc:
            raise AwarenessError("awareness file is unreadable or malformed") from exc
        if not isinstance(payload, dict) or set(payload) != _FIELDS:
            raise AwarenessError("awareness document fields are invalid")
        version = payload.get("awareness_version")
        if isinstance(version, bool) or version != AWARENESS_VERSION:
            raise AwarenessError("awareness version is unsupported")
        if payload.get("owner_entity_id") != owner:
            raise AwarenessError("awareness owner does not match entity identity")
        if not _timestamp_ok(payload.get("observed_at")):
            raise AwarenessError("awareness observed_at is invalid")
        if not isinstance(payload.get("attention_target"), str) or len(
            payload["attention_target"]
        ) > MAX_TEXT_CHARS:
            raise AwarenessError("awareness attention_target is invalid")
        for field, limit in (
            ("current_goal_ids", MAX_GOAL_IDS),
            ("salient_discrepancies", MAX_DISCREPANCIES),
            ("known_blind_spots", MAX_BLIND_SPOTS),
        ):
            entries = payload.get(field)
            if not isinstance(entries, list) or len(entries) > limit:
                raise AwarenessError(f"awareness {field} is invalid or oversized")
            for entry in entries:
                if not isinstance(entry, str) or len(entry) > MAX_TEXT_CHARS:
                    raise AwarenessError(f"awareness {field} entry is invalid")
        if not _unit(payload.get("uncertainty")) or not _unit(payload.get("cognitive_load")):
            raise AwarenessError("awareness uncertainty/load must be unit-interval numbers")
        if not isinstance(payload.get("reflection_recommended"), bool):
            raise AwarenessError("awareness reflection_recommended is invalid")
        triggers = payload.get("reflection_triggers")
        if not isinstance(triggers, list) or not set(triggers) <= TRIGGERS:
            raise AwarenessError("awareness reflection_triggers are invalid")
        if payload["reflection_recommended"] != bool(triggers):
            raise AwarenessError("awareness reflection flag disagrees with its triggers")
        return payload

    @staticmethod
    def _write(path: Path, data: dict[str, Any]) -> None:
        if path.is_symlink():
            raise AwarenessError("awareness file must not be a symbolic link")
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


class AwarenessBridge:
    """Create the awareness snapshot at session start; offer its packet.

    Refreshing is explicit — no hook, loop, or turn-path caller runs
    awareness on its own (§6.5). The bridge fails open throughout.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._store = AwarenessStore(ctx)

    def hooks(self):
        return (("on_session_start", self.on_session_start),)

    def on_session_start(self, **_: Any) -> None:
        if not self._store.enabled():
            return
        try:
            self._store.ensure()
        except (IdentityError, AwarenessError, OSError):
            return

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not _as_bool(self._ctx.get_config("awareness_enabled", False), False):
            return []
        try:
            data = self._store.read()
        except (IdentityError, AwarenessError, OSError):
            return []
        parts: list[str] = []
        if data["attention_target"]:
            parts.append(f"attention: {data['attention_target']}")
        if data["salient_discrepancies"]:
            parts.append(f"discrepancies: {len(data['salient_discrepancies'])} salient")
        if data["reflection_recommended"]:
            parts.append("reflection recommended")
        if not parts:
            return []
        return [
            ContextItem(
                section="current_state",
                content="Self-awareness — " + "; ".join(parts) + ".",
                source="awareness",
                record_id=data["owner_entity_id"],
                priority=0.4,
                updated_at=_parse_ts(data["observed_at"]),
            )
        ]


__all__ = [
    "AWARENESS_VERSION",
    "DEFAULT_AWARENESS_PATH",
    "TRIGGERS",
    "HIGH_UNCERTAINTY",
    "AwarenessError",
    "AwarenessStore",
    "AwarenessBridge",
]
