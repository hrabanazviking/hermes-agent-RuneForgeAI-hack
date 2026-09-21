"""Opt-in relevant WYRD context for the central user-side context packet."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from .context_packet import ContextItem
from .wyrd import WyrdProtocolError, request_wyrd_json


_ENTITY_ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9_]{0,63})$")
_MAX_QUERY_CHARS = 8_000


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


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return min(maximum, max(minimum, parsed))


class WyrdContextBridge:
    """Read a fresh Passive Oracle render only when explicitly configured."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx

    def packet_items(
        self,
        session_id: str,
        user_message: Any = "",
    ) -> list[ContextItem]:
        if not _as_bool(self._ctx.get_config("wyrd_context_enabled", False), False):
            return []
        persona_id = str(self._ctx.get_config("wyrd_context_persona_id", "")).strip()
        if not _ENTITY_ID_RE.fullmatch(persona_id):
            return []
        query = user_message.strip() if isinstance(user_message, str) else ""
        if not query:
            query = "What is the current world state?"
        query = query[:_MAX_QUERY_CHARS]
        try:
            payload = request_wyrd_json(
                self._ctx,
                "/query",
                method="POST",
                body={
                    "persona_id": persona_id,
                    "user_input": query,
                    "use_turn_loop": False,
                },
            )
        except WyrdProtocolError:
            return []
        context = payload.get("response")
        if not isinstance(context, str) or not context.strip():
            return []
        budget = _bounded_int(
            self._ctx.get_config("wyrd_context_render_chars", 1800),
            1800,
            256,
            4000,
        )
        context = context.strip()
        if len(context) > budget:
            context = context[: budget - 1].rstrip() + "…"
        record_id = hashlib.sha256(context.encode("utf-8")).hexdigest()[:16]
        return [
            ContextItem(
                section="world_state",
                content=context,
                source="wyrd/passive_oracle",
                record_id=record_id,
                priority=1.0,
            )
        ]
