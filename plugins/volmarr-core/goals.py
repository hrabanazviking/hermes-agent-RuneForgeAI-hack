"""Durable, explicit goals and task continuity for the stable entity."""

from __future__ import annotations

import os
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


GOALS_VERSION = 1
DEFAULT_GOALS_PATH = Path("entity") / "goals.yaml"
MAX_GOALS = 256
MAX_FILE_BYTES = 2 * 1024 * 1024
GOAL_STATUSES = {"planned", "active", "blocked", "completed", "archived"}

try:
    import fcntl
except ImportError:  # pragma: no cover - platform branch
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover - platform branch
    msvcrt = None


class GoalError(RuntimeError):
    """The goal ledger cannot be safely read or changed."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_uuid(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        return None
    return value if str(parsed) == value.lower() else None


def _text(value: Any, maximum: int, *, required: bool = True) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if (required and not value) or len(value) > maximum:
        return None
    return value


def _priority(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if 0 <= value <= 100 else None


def _timestamp(value: Any, *, empty: bool = False) -> bool:
    if empty and value == "":
        return True
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


class GoalStore:
    """Versioned goal ledger with bounded, append-only transition history."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("goals_enabled", True), True
        )

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(
            str(self._ctx.get_config("goals_path", str(DEFAULT_GOALS_PATH)))
        )
        if configured.is_absolute():
            configured = DEFAULT_GOALS_PATH
        candidate = (home / configured).resolve()
        if not candidate.is_relative_to(home):
            candidate = (home / DEFAULT_GOALS_PATH).resolve()
        if not candidate.is_relative_to(home):
            raise GoalError("goals path resolves outside the active profile")
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

    def get(self, goal_id: str | None = None) -> dict[str, Any]:
        owner = self._identity.read().entity_id
        path = self.path()
        with self._lock(path):
            data = self._read_unlocked(path, owner)
        if goal_id is None:
            return data
        goal = data["goals"].get(goal_id)
        if goal is None:
            raise GoalError("goal was not found")
        return goal

    def create(
        self,
        *,
        title: str,
        description: str,
        priority: int,
        next_action: str,
    ) -> dict[str, Any]:
        owner = self._identity.read().entity_id
        path = self.path()
        with self._lock(path):
            data = self._read_unlocked(path, owner)
            if len(data["goals"]) >= MAX_GOALS:
                raise GoalError("goal ledger is full")
            goal_id = str(uuid.uuid4())
            timestamp = _now()
            goal = {
                "goal_id": goal_id,
                "title": title,
                "description": description,
                "status": "planned",
                "priority": priority,
                "next_action": next_action,
                "created_at": timestamp,
                "updated_at": timestamp,
                "completed_at": "",
                "history": [
                    {
                        "event_id": str(uuid.uuid4()),
                        "recorded_at": timestamp,
                        "status": "planned",
                        "note": "Goal created.",
                    }
                ],
            }
            data["goals"][goal_id] = goal
            self._write(path, data)
            return goal

    def update(self, goal_id: str, changes: dict[str, Any], note: str) -> dict[str, Any]:
        owner = self._identity.read().entity_id
        path = self.path()
        with self._lock(path):
            data = self._read_unlocked(path, owner)
            existing = data["goals"].get(goal_id)
            if existing is None:
                raise GoalError("goal was not found")
            goal = dict(existing)
            timestamp = _now()
            for field in ("title", "description", "status", "priority", "next_action"):
                if field in changes:
                    goal[field] = changes[field]
            if "status" in changes:
                if changes["status"] == "completed":
                    goal["completed_at"] = timestamp
                elif changes["status"] != "archived":
                    goal["completed_at"] = ""
            goal["updated_at"] = timestamp
            history = list(goal["history"])
            history.append(
                {
                    "event_id": str(uuid.uuid4()),
                    "recorded_at": timestamp,
                    "status": goal["status"],
                    "note": note,
                }
            )
            goal["history"] = history[-self._history_limit() :]
            data["goals"][goal_id] = goal
            self._write(path, data)
            return goal

    def _history_limit(self) -> int:
        try:
            value = int(self._ctx.get_config("goals_history_limit", 100))
        except (TypeError, ValueError):
            value = 100
        return min(500, max(1, value))

    @staticmethod
    def _empty(owner: str) -> dict[str, Any]:
        return {
            "goals_version": GOALS_VERSION,
            "owner_entity_id": owner,
            "goals": {},
        }

    def _read_unlocked(self, path: Path, owner: str) -> dict[str, Any]:
        if path.is_symlink():
            raise GoalError("goals file must not be a symbolic link")
        if not path.is_file():
            raise GoalError("goals file is missing")
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                raise GoalError("goals file exceeds its size limit")
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise GoalError("goals file is unreadable or malformed") from exc
        if not isinstance(payload, dict):
            raise GoalError("goals document must be a mapping")
        version = payload.get("goals_version")
        if isinstance(version, bool) or version != GOALS_VERSION:
            raise GoalError("goals version is unsupported")
        if payload.get("owner_entity_id") != owner:
            raise GoalError("goals owner does not match entity identity")
        goals = payload.get("goals")
        if not isinstance(goals, dict) or len(goals) > MAX_GOALS:
            raise GoalError("goals mapping is invalid or oversized")
        for key, goal in goals.items():
            self._validate_goal(key, goal)
        return payload

    @staticmethod
    def _validate_goal(key: Any, goal: Any) -> None:
        if _canonical_uuid(key) is None or not isinstance(goal, dict):
            raise GoalError("goal record is invalid")
        if goal.get("goal_id") != key:
            raise GoalError("goal key and goal_id do not match")
        if _text(goal.get("title"), 200) is None:
            raise GoalError("goal title is invalid")
        if _text(goal.get("description"), 4000, required=False) is None:
            raise GoalError("goal description is invalid")
        if goal.get("status") not in GOAL_STATUSES:
            raise GoalError("goal status is invalid")
        if _priority(goal.get("priority")) is None:
            raise GoalError("goal priority is invalid")
        if _text(goal.get("next_action"), 1000, required=False) is None:
            raise GoalError("goal next_action is invalid")
        if not _timestamp(goal.get("created_at")) or not _timestamp(
            goal.get("updated_at")
        ):
            raise GoalError("goal timestamps are invalid")
        if not _timestamp(goal.get("completed_at"), empty=True):
            raise GoalError("goal completed_at is invalid")
        if goal["status"] == "completed" and not goal["completed_at"]:
            raise GoalError("goal completion status and timestamp disagree")
        if goal["status"] in {"planned", "active", "blocked"} and goal["completed_at"]:
            raise GoalError("goal completion status and timestamp disagree")
        history = goal.get("history")
        if not isinstance(history, list) or not history or len(history) > 500:
            raise GoalError("goal history is invalid or oversized")
        for event in history:
            if not isinstance(event, dict) or _canonical_uuid(event.get("event_id")) is None:
                raise GoalError("goal history event is invalid")
            if not _timestamp(event.get("recorded_at")):
                raise GoalError("goal history timestamp is invalid")
            if event.get("status") not in GOAL_STATUSES:
                raise GoalError("goal history status is invalid")
            if _text(event.get("note"), 1000, required=False) is None:
                raise GoalError("goal history note is invalid")

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


GOAL_GET_SCHEMA = {
    "name": "goal_get",
    "description": (
        "Read durable entity goals. Omit goal_id for compact summaries; use a goal_id "
        "to retrieve its full description and optionally its bounded history."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "goal_id": {"type": "string", "format": "uuid"},
            "status": {"type": "string", "enum": sorted(GOAL_STATUSES)},
            "include_history": {"type": "boolean", "default": False},
        },
        "additionalProperties": False,
    },
}

GOAL_CREATE_SCHEMA = {
    "name": "goal_create",
    "description": "Create one durable planned goal owned by the active stable entity.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "maxLength": 200},
            "description": {"type": "string", "maxLength": 4000},
            "priority": {"type": "integer", "minimum": 0, "maximum": 100},
            "next_action": {"type": "string", "maxLength": 1000},
        },
        "required": ["title"],
        "additionalProperties": False,
    },
}

GOAL_UPDATE_SCHEMA = {
    "name": "goal_update",
    "description": (
        "Update explicit goal state and append a bounded transition event. "
        "Use status=archived instead of deleting continuity."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "goal_id": {"type": "string", "format": "uuid"},
            "title": {"type": "string", "maxLength": 200},
            "description": {"type": "string", "maxLength": 4000},
            "status": {"type": "string", "enum": sorted(GOAL_STATUSES)},
            "priority": {"type": "integer", "minimum": 0, "maximum": 100},
            "next_action": {"type": "string", "maxLength": 1000},
            "note": {"type": "string", "maxLength": 1000},
        },
        "required": ["goal_id"],
        "additionalProperties": False,
    },
}


def build_goal_get_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        raw_id = args.get("goal_id")
        goal_id = None if raw_id is None else _canonical_uuid(raw_id)
        if raw_id is not None and goal_id is None:
            return tool_error("goal_id must be a canonical UUID")
        status = args.get("status")
        if status is not None and status not in GOAL_STATUSES:
            return tool_error("status filter is invalid")
        include_history = args.get("include_history", False)
        if not isinstance(include_history, bool):
            return tool_error("include_history must be a boolean")
        try:
            data = GoalStore(ctx).get(goal_id)
        except (IdentityError, GoalError, OSError) as exc:
            return tool_error(str(exc))
        if goal_id is not None:
            goal = dict(data)
            if not include_history:
                goal.pop("history", None)
            return tool_result({"success": True, "goal": goal})
        summaries = []
        for key in sorted(data["goals"]):
            goal = data["goals"][key]
            if status is not None and goal["status"] != status:
                continue
            summaries.append(
                {
                    field: goal[field]
                    for field in (
                        "goal_id",
                        "title",
                        "status",
                        "priority",
                        "next_action",
                        "updated_at",
                    )
                }
            )
        summaries.sort(key=lambda row: (-row["priority"], row["goal_id"]))
        return tool_result({"success": True, "goals": summaries})

    return handle


def build_goal_create_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        title = _text(args.get("title"), 200)
        description = _text(args.get("description", ""), 4000, required=False)
        next_action = _text(args.get("next_action", ""), 1000, required=False)
        priority = _priority(args.get("priority", 50))
        if title is None:
            return tool_error("title is required and must not exceed 200 characters")
        if description is None:
            return tool_error("description must not exceed 4000 characters")
        if next_action is None:
            return tool_error("next_action must not exceed 1000 characters")
        if priority is None:
            return tool_error("priority must be an integer from 0 to 100")
        try:
            goal = GoalStore(ctx).create(
                title=title,
                description=description,
                priority=priority,
                next_action=next_action,
            )
        except (IdentityError, GoalError, OSError) as exc:
            return tool_error(str(exc))
        return tool_result(
            {"success": True, "goal_id": goal["goal_id"], "status": goal["status"]}
        )

    return handle


def build_goal_update_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        goal_id = _canonical_uuid(args.get("goal_id"))
        if goal_id is None:
            return tool_error("goal_id must be a canonical UUID")
        changes: dict[str, Any] = {}
        limits = {
            "title": (200, True),
            "description": (4000, False),
            "next_action": (1000, False),
        }
        for field, (maximum, required) in limits.items():
            if field in args:
                value = _text(args[field], maximum, required=required)
                if value is None:
                    return tool_error(f"{field} is invalid or exceeds {maximum} characters")
                changes[field] = value
        if "status" in args:
            if args["status"] not in GOAL_STATUSES:
                return tool_error("status is invalid")
            changes["status"] = args["status"]
        if "priority" in args:
            priority = _priority(args["priority"])
            if priority is None:
                return tool_error("priority must be an integer from 0 to 100")
            changes["priority"] = priority
        note = _text(args.get("note", ""), 1000, required=False)
        if note is None:
            return tool_error("note must not exceed 1000 characters")
        if not changes and not note:
            return tool_error("at least one goal change or note is required")
        try:
            goal = GoalStore(ctx).update(goal_id, changes, note)
        except (IdentityError, GoalError, OSError) as exc:
            return tool_error(str(exc))
        return tool_result(
            {
                "success": True,
                "goal_id": goal["goal_id"],
                "status": goal["status"],
                "history_events": len(goal["history"]),
            }
        )

    return handle


class GoalBridge:
    def __init__(self, ctx) -> None:
        self._store = GoalStore(ctx)

    def hooks(self):
        return (("on_session_start", self.on_session_start),)

    def on_session_start(self, **_: Any) -> None:
        if not self._store.enabled():
            return
        try:
            self._store.ensure()
        except (IdentityError, GoalError, OSError):
            return


def register_goal_tools(ctx) -> None:
    for name, schema, handler, emoji in (
        ("goal_get", GOAL_GET_SCHEMA, build_goal_get_handler(ctx), "🎯"),
        ("goal_create", GOAL_CREATE_SCHEMA, build_goal_create_handler(ctx), "🌱"),
        ("goal_update", GOAL_UPDATE_SCHEMA, build_goal_update_handler(ctx), "🧭"),
    ):
        ctx.register_tool(
            name=name,
            toolset="volmarr_identity",
            schema=schema,
            handler=handler,
            description=schema["description"],
            emoji=emoji,
        )
