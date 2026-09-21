"""Plugin lifecycle adapter for the preserved synthetic affective regulator."""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any

from hermes_constants import get_hermes_home

from .affective import AffectiveNervousSystem, load_affective_config
from .context_packet import ContextItem


_MAX_PENDING_TURNS = 256
_MAX_TOOL_MESSAGES = 64


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return min(maximum, max(minimum, parsed))


class AffectiveBridge:
    """Observe completed Hermes turns while leaving prompt assembly centralized."""

    def __init__(self, ctx) -> None:
        config = load_affective_config(
            {
                "enabled": ctx.get_config("affective_enabled", False),
                "render_char_budget": _bounded_int(
                    ctx.get_config("affective_render_chars", 2600),
                    2600,
                    256,
                    4000,
                ),
                "max_recent_events": _bounded_int(
                    ctx.get_config("affective_max_recent_events", 40),
                    40,
                    1,
                    100,
                ),
                "decay": ctx.get_config("affective_decay", 0.04),
            }
        )
        self._system = AffectiveNervousSystem(config)
        self._pending: OrderedDict[tuple[str, str, str], dict[str, Any]] = (
            OrderedDict()
        )
        self._pending_lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return bool(self._system.config.enabled)

    def hooks(self):
        return (
            ("on_session_start", self.on_session_start),
            ("pre_llm_call", self.pre_llm_call),
            ("post_llm_call", self.post_llm_call),
            ("post_tool_call", self.post_tool_call),
            ("on_session_end", self.on_turn_end),
        )

    @staticmethod
    def _key(session_id: str, turn_id: str) -> tuple[str, str, str]:
        return (str(get_hermes_home().resolve()), session_id, turn_id or session_id)

    def on_session_start(self, *, session_id: str = "", **_: Any) -> None:
        if self.enabled:
            self._system.initialize(session_id)

    def pre_llm_call(
        self,
        *,
        session_id: str = "",
        turn_id: str = "",
        user_message: Any = "",
        **_: Any,
    ) -> None:
        if not self.enabled:
            return
        key = self._key(session_id, turn_id)
        with self._pending_lock:
            pending = self._pending.setdefault(
                key,
                {"user": "", "assistant": "", "messages": []},
            )
            if isinstance(user_message, str) and user_message:
                pending["user"] = user_message
            self._pending.move_to_end(key)
            while len(self._pending) > _MAX_PENDING_TURNS:
                self._pending.popitem(last=False)

    def post_llm_call(
        self,
        *,
        session_id: str = "",
        turn_id: str = "",
        assistant_response: Any = "",
        response: Any = None,
        **_: Any,
    ) -> None:
        if not self.enabled:
            return
        if isinstance(assistant_response, dict):
            assistant_response = assistant_response.get("content", "")
        elif (
            not isinstance(assistant_response, str) or not assistant_response
        ) and isinstance(response, dict):
            assistant_response = response.get("content", "")
        key = self._key(session_id, turn_id)
        with self._pending_lock:
            pending = self._pending.get(key)
            if pending is not None and isinstance(assistant_response, str):
                pending["assistant"] = assistant_response

    def post_tool_call(
        self,
        *,
        session_id: str = "",
        turn_id: str = "",
        status: str = "ok",
        result: Any = None,
        error_message: Any = None,
        error_type: Any = None,
        **_: Any,
    ) -> None:
        if not self.enabled:
            return
        parts = [error_type, error_message, result] if status != "ok" else [result]
        content = " ".join(str(part) for part in parts if part not in (None, ""))
        if not content and status != "ok":
            content = f"tool status: {status}"
        if not content:
            return
        key = self._key(session_id, turn_id)
        with self._pending_lock:
            pending = self._pending.get(key)
            if pending is not None:
                messages = pending["messages"]
                messages.append({"role": "tool", "content": content})
                del messages[:-_MAX_TOOL_MESSAGES]

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
        if not self.enabled:
            return
        key = self._key(session_id, turn_id)
        with self._pending_lock:
            pending = self._pending.pop(key, None)
        if not pending or not completed or failed or interrupted:
            return
        self._system.observe_turn(
            user_content=pending.get("user"),
            assistant_content=pending.get("assistant"),
            messages=pending.get("messages", []),
            session_id=session_id,
            interrupted=False,
        )

    def packet_items(self, session_id: str) -> list[ContextItem]:
        if not self.enabled:
            return []
        context = self._system.render_context(session_id=session_id)
        if not context:
            return []
        return [
            ContextItem(
                section="current_state",
                content=context,
                source="affective_regulation",
                record_id="profile-state-v9",
                priority=2.0,
            )
        ]
