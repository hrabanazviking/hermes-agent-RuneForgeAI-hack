"""Compact, profile-scoped facts that are true or relevant right now."""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from hermes_constants import get_hermes_home
from utils import atomic_json_write

from .context_packet import ContextItem, ContextPacketBuilder


SCHEMA_VERSION = 1
DEFAULT_STATE_PATH = Path("memory") / "present_state.json"
_MAX_PENDING_TURNS = 256

try:
    import fcntl
except ImportError:  # pragma: no cover - platform branch
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover - platform branch
    msvcrt = None


def _clean_text(value: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", value.strip()) if isinstance(value, str) else ""
    text = text.strip(" -:\t\r\n")
    if limit > 0 and len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def _fact_id(scope: str, target: str, content: str, session_id: str = "") -> str:
    normalized = re.sub(r"\s+", " ", content.strip()).casefold()
    raw = "|".join((scope, target, session_id if scope == "session" else "", normalized))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class PresentStateFact:
    id: str
    scope: str
    target: str
    content: str
    source: str
    session_id: str
    created_at: float
    updated_at: float
    confidence: float


class PresentStateStore:
    """Versioned live-state store whose path is resolved on every operation."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx

    def _path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(
            str(self._ctx.get_config("present_state_path", str(DEFAULT_STATE_PATH)))
        )
        if configured.is_absolute():
            return configured.resolve()
        resolved = (home / configured).resolve()
        if not resolved.is_relative_to(home):
            return home / DEFAULT_STATE_PATH
        return resolved

    def _limits(self) -> tuple[int, int, int]:
        return (
            self._bounded_config("present_state_max_profile_facts", 40, 1, 200),
            self._bounded_config("present_state_max_session_facts", 20, 1, 100),
            self._bounded_config("present_state_render_chars", 4000, 256, 12000),
        )

    def _bounded_config(self, key: str, default: int, minimum: int, maximum: int) -> int:
        try:
            value = int(self._ctx.get_config(key, default))
        except (TypeError, ValueError):
            value = default
        return min(maximum, max(minimum, value))

    def initialize(self, session_id: str) -> None:
        with self._locked_state() as state:
            state["active_session_id"] = session_id
            state["updated_at"] = time.time()

    def packet_items(self, session_id: str) -> list[ContextItem]:
        with self._locked_state(write=False) as state:
            profile = self._facts(state.get("profile_facts"))
            session_row = state.get("sessions", {}).get(session_id, {})
            session = self._facts(
                session_row.get("facts") if isinstance(session_row, dict) else []
            )
        profile = profile[:5]
        session = session[:5]
        budget = self._limits()[2]
        items: list[ContextItem] = []
        used = 0
        for fact in (*profile, *session):
            remaining = budget - used
            if remaining <= 0:
                break
            content = fact.content
            if len(content) > remaining:
                if remaining < 32:
                    break
                content = content[: remaining - 1].rstrip() + "…"
            items.append(
                ContextItem(
                    section="current_state",
                    content=content,
                    source=f"present_state/{fact.scope}/{fact.source}",
                    record_id=fact.id,
                    priority=fact.confidence,
                    updated_at=fact.updated_at,
                )
            )
            used += len(content)
        return items

    def capture_memory_write(
        self,
        action: str,
        target: str,
        content: Any,
        session_id: str,
    ) -> None:
        if action not in {"add", "replace"}:
            return
        clean = _clean_text(content, 360)
        if clean:
            self._upsert(
                self._make_fact(
                    "profile",
                    "user" if target == "user" else "memory",
                    clean,
                    "memory_tool",
                    session_id,
                    1.0,
                )
            )

    def capture_turn(self, user: Any, assistant: Any, session_id: str) -> None:
        user_text = user if isinstance(user, str) else ""
        assistant_text = assistant if isinstance(assistant, str) else ""
        for fact in self._extract_user_facts(user_text, session_id):
            self._upsert(fact)
        for fact in self._extract_session_facts(user_text, assistant_text, session_id):
            self._upsert(fact)

    def _extract_user_facts(
        self,
        text: str,
        session_id: str,
    ) -> Iterable[PresentStateFact]:
        patterns = (
            (r"\bremember(?:\s+(?:that|this))?:?\s+([^\.\n!?]+)", "memory", "{0}"),
            (r"\bcall me\s+([^\.\n!?]+)", "user", "User wants to be called {0}."),
            (r"\bi prefer\s+([^\.\n!?]+)", "user", "User prefers {0}."),
            (r"\bi use\s+([^\.\n!?]+)", "user", "User uses {0}."),
        )
        for pattern, target, template in patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                content = _clean_text(template.format(match.group(1).strip()), 360)
                if content:
                    yield self._make_fact(
                        "profile", target, content, "user_statement", session_id, 0.9
                    )

    def _extract_session_facts(
        self,
        user: str,
        assistant: str,
        session_id: str,
    ) -> Iterable[PresentStateFact]:
        for pattern in (
            r"\bwe(?:'re| are) working on\s+([^\.\n!?]+)",
            r"\bcurrent (?:goal|task) is\s+([^\.\n!?]+)",
            r"\bthe (?:goal|task) is\s+([^\.\n!?]+)",
        ):
            for match in re.finditer(pattern, user, flags=re.IGNORECASE):
                content = _clean_text(f"Current goal: {match.group(1).strip()}.", 360)
                yield self._make_fact(
                    "session", "conversation", content, "user_goal", session_id, 0.9
                )
        if re.search(
            r"\b(done|implemented|added|fixed|changed|updated|completed)\b",
            assistant,
            re.IGNORECASE,
        ):
            summary = _clean_text(re.split(r"(?<=[.!?])\s", assistant, maxsplit=1)[0], 360)
            if summary:
                yield self._make_fact(
                    "session",
                    "conversation",
                    f"Latest assistant outcome: {summary}",
                    "assistant_outcome",
                    session_id,
                    0.75,
                )

    @staticmethod
    def _make_fact(
        scope: str,
        target: str,
        content: str,
        source: str,
        session_id: str,
        confidence: float,
    ) -> PresentStateFact:
        now = time.time()
        return PresentStateFact(
            id=_fact_id(scope, target, content, session_id),
            scope=scope,
            target=target,
            content=content,
            source=source,
            session_id=session_id,
            created_at=now,
            updated_at=now,
            confidence=confidence,
        )

    def _upsert(self, fact: PresentStateFact) -> None:
        profile_limit, session_limit, _render_limit = self._limits()
        with self._locked_state() as state:
            if fact.scope == "session":
                sessions = state.setdefault("sessions", {})
                row = sessions.setdefault(fact.session_id, {"facts": []})
                row["facts"] = self._upsert_list(row.get("facts"), fact, session_limit)
            else:
                state["profile_facts"] = self._upsert_list(
                    state.get("profile_facts"), fact, profile_limit
                )
            state["active_session_id"] = fact.session_id
            state["updated_at"] = time.time()

    def _upsert_list(self, raw: Any, fact: PresentStateFact, limit: int) -> list[dict]:
        facts = self._facts(raw)
        existing = next((item for item in facts if item.id == fact.id), None)
        if existing is not None:
            facts.remove(existing)
            fact = PresentStateFact(
                **{
                    **asdict(fact),
                    "created_at": existing.created_at,
                    "updated_at": time.time(),
                }
            )
        facts.append(fact)
        facts.sort(key=lambda item: item.updated_at, reverse=True)
        return [asdict(item) for item in facts[:limit]]

    @staticmethod
    def _facts(raw: Any) -> list[PresentStateFact]:
        if not isinstance(raw, list):
            return []
        facts = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                fact = PresentStateFact(
                    id=str(item["id"]),
                    scope=str(item["scope"]),
                    target=str(item["target"]),
                    content=_clean_text(item["content"], 360),
                    source=str(item["source"]),
                    session_id=str(item.get("session_id") or ""),
                    created_at=float(item["created_at"]),
                    updated_at=float(item["updated_at"]),
                    confidence=float(item["confidence"]),
                )
            except (KeyError, TypeError, ValueError):
                continue
            if fact.content and fact.scope in {"profile", "session"}:
                facts.append(fact)
        facts.sort(key=lambda item: item.updated_at, reverse=True)
        return facts

    @staticmethod
    def _default_state() -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "active_session_id": "",
            "profile_facts": [],
            "sessions": {},
            "updated_at": time.time(),
        }

    def _read_unlocked(self, path: Path) -> dict[str, Any]:
        if not path.is_file() or path.is_symlink():
            return self._default_state()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return self._default_state()
        if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
            return self._default_state()
        if not isinstance(data.get("sessions"), dict):
            data["sessions"] = {}
        if not isinstance(data.get("profile_facts"), list):
            data["profile_facts"] = []
        return data

    @contextmanager
    def _locked_state(self, *, write: bool = True):
        path = self._path()
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
                state = self._read_unlocked(path)
                yield state
                if write:
                    atomic_json_write(
                        path,
                        state,
                        indent=2,
                        sort_keys=True,
                        ensure_ascii=False,
                        mode=0o600,
                    )
            finally:
                lock.seek(0)
                if fcntl is not None:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                elif msvcrt is not None:
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


class PresentStateBridge:
    """Attach present state to existing lifecycle hooks without changing Hermes core."""

    def __init__(
        self,
        ctx,
        *,
        packet_sources: Iterable[Callable[[str], Iterable[ContextItem]]] = (),
    ) -> None:
        self._store = PresentStateStore(ctx)
        self._packet = ContextPacketBuilder(ctx)
        self._packet_sources = (self._store.packet_items, *tuple(packet_sources))
        self._pending: OrderedDict[tuple[str, str, str], dict[str, Any]] = OrderedDict()
        self._pending_lock = threading.Lock()

    def hooks(self):
        return (
            ("on_session_start", self.on_session_start),
            ("pre_llm_call", self.pre_llm_call),
            ("post_llm_call", self.post_llm_call),
            ("on_session_end", self.on_turn_end),
            ("post_tool_call", self.post_tool_call),
        )

    @staticmethod
    def _key(session_id: str, turn_id: str) -> tuple[str, str, str]:
        return (str(get_hermes_home().resolve()), session_id, turn_id or session_id)

    def on_session_start(self, *, session_id: str = "", **_: Any) -> None:
        self._store.initialize(session_id)

    def pre_llm_call(
        self,
        *,
        session_id: str = "",
        turn_id: str = "",
        user_message: Any = "",
        **_: Any,
    ) -> dict[str, str] | None:
        key = self._key(session_id, turn_id)
        with self._pending_lock:
            self._pending[key] = {"user": user_message, "assistant": ""}
            self._pending.move_to_end(key)
            while len(self._pending) > _MAX_PENDING_TURNS:
                self._pending.popitem(last=False)
        items = []
        for source in self._packet_sources:
            try:
                items.extend(source(session_id))
            except Exception:
                continue
        context = self._packet.build(items)
        return {"context": context} if context else None

    def post_llm_call(
        self,
        *,
        session_id: str = "",
        turn_id: str = "",
        assistant_response: Any = "",
        **_: Any,
    ) -> None:
        key = self._key(session_id, turn_id)
        with self._pending_lock:
            pending = self._pending.get(key)
            if pending is not None:
                pending["assistant"] = assistant_response

    def on_turn_end(
        self,
        *,
        session_id: str = "",
        turn_id: str = "",
        completed: bool = False,
        failed: bool = False,
        interrupted: bool = False,
        **_: Any,
    ) -> None:
        key = self._key(session_id, turn_id)
        with self._pending_lock:
            pending = self._pending.pop(key, None)
        if pending and completed and not failed and not interrupted:
            self._store.capture_turn(
                pending.get("user"), pending.get("assistant"), session_id
            )

    def post_tool_call(
        self,
        *,
        tool_name: str = "",
        args: Any = None,
        session_id: str = "",
        status: str = "ok",
        **_: Any,
    ) -> None:
        if tool_name != "memory" or status != "ok" or not isinstance(args, dict):
            return
        operations = args.get("operations")
        if not isinstance(operations, list):
            operations = [args]
        for operation in operations:
            if not isinstance(operation, dict):
                continue
            self._store.capture_memory_write(
                str(operation.get("action") or ""),
                str(operation.get("target") or args.get("target") or "memory"),
                operation.get("content") or operation.get("new_text"),
                session_id,
            )
