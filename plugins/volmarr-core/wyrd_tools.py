"""Explicit read-only Hermes tools for the official WYRD HTTP contract."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlencode

from tools.registry import tool_error, tool_result

from .wyrd import WyrdProtocolError, request_wyrd_json


_ENTITY_ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9_]{0,63})$")
_MAX_QUERY_CHARS = 8_000
_MAX_FACTS = 256


WORLD_GET_SCHEMA = {
    "name": "world_get",
    "description": (
        "Read grounded state from the configured local WYRD world model. "
        "Use mode=snapshot for the current world packet or mode=facts with an "
        "entity_id for canonical facts. This tool never changes world state."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["snapshot", "facts"],
                "description": "Read the world snapshot (default) or one entity's facts.",
            },
            "entity_id": {
                "type": "string",
                "description": "Lowercase WYRD entity ID; required for mode=facts.",
                "maxLength": 64,
            },
        },
        "additionalProperties": False,
    },
}

WORLD_QUERY_SCHEMA = {
    "name": "world_query",
    "description": (
        "Ask the local WYRD Passive Oracle for grounded context about one persona. "
        "The request always disables WYRD's turn loop, LLM generation, and memory writeback."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "persona_id": {
                "type": "string",
                "description": "Lowercase WYRD persona/entity ID.",
                "maxLength": 64,
            },
            "query": {
                "type": "string",
                "description": "Question used to select relevant world context.",
                "maxLength": _MAX_QUERY_CHARS,
            },
        },
        "required": ["persona_id", "query"],
        "additionalProperties": False,
    },
}


def _entity_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized if _ENTITY_ID_RE.fullmatch(normalized) else None


def build_world_get_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        mode = args.get("mode", "snapshot")
        try:
            if mode == "snapshot":
                payload = request_wyrd_json(ctx, "/world")
                required = {"world_id", "formatted_for_llm"}
                if not required.issubset(payload):
                    raise WyrdProtocolError("WYRD world response is missing required fields")
                return tool_result(
                    {"success": True, "mode": "snapshot", "world": payload}
                )
            if mode == "facts":
                entity_id = _entity_id(args.get("entity_id"))
                if entity_id is None:
                    return tool_error(
                        "entity_id must be 1-64 lowercase letters, digits, or underscores"
                    )
                payload = request_wyrd_json(
                    ctx,
                    f"/facts?{urlencode({'entity_id': entity_id})}",
                )
                facts = payload.get("facts")
                if not isinstance(facts, list) or len(facts) > _MAX_FACTS:
                    raise WyrdProtocolError("WYRD facts response is invalid or oversized")
                return tool_result(
                    {
                        "success": True,
                        "mode": "facts",
                        "entity_id": entity_id,
                        "facts": facts,
                    }
                )
            return tool_error("mode must be snapshot or facts")
        except WyrdProtocolError as exc:
            return tool_error(str(exc))

    return handle


def build_world_query_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        persona_id = _entity_id(args.get("persona_id"))
        if persona_id is None:
            return tool_error(
                "persona_id must be 1-64 lowercase letters, digits, or underscores"
            )
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            return tool_error("query is required")
        query = query.strip()
        if len(query) > _MAX_QUERY_CHARS:
            return tool_error(f"query exceeds {_MAX_QUERY_CHARS} characters")
        try:
            payload = request_wyrd_json(
                ctx,
                "/query",
                method="POST",
                body={
                    "persona_id": persona_id,
                    "user_input": query,
                    "use_turn_loop": False,
                },
            )
            response = payload.get("response")
            if not isinstance(response, str):
                raise WyrdProtocolError("WYRD query response has no text response")
            return tool_result(
                {
                    "success": True,
                    "persona_id": persona_id,
                    "context": response,
                    "writeback": False,
                }
            )
        except WyrdProtocolError as exc:
            return tool_error(str(exc))

    return handle


def register_wyrd_tools(ctx) -> None:
    ctx.register_tool(
        name="world_get",
        toolset="volmarr_world",
        schema=WORLD_GET_SCHEMA,
        handler=build_world_get_handler(ctx),
        description=WORLD_GET_SCHEMA["description"],
        emoji="🌍",
    )
    ctx.register_tool(
        name="world_query",
        toolset="volmarr_world",
        schema=WORLD_QUERY_SCHEMA,
        handler=build_world_query_handler(ctx),
        description=WORLD_QUERY_SCHEMA["description"],
        emoji="🔭",
    )
