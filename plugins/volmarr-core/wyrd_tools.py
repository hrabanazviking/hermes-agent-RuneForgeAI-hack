"""Explicit read-only Hermes tools for the official WYRD HTTP contract."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlencode

from tools.registry import tool_error, tool_result

from .wyrd import WyrdProtocolError, request_wyrd_json
from .world_telemetry import WorldChangeTelemetry


_ENTITY_ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9_]{0,63})$")
_MAX_QUERY_CHARS = 8_000
_MAX_FACTS = 256
_FACT_KEY_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_DOMAIN_RE = re.compile(r"^[a-z0-9](?:[a-z0-9_.-]{0,63})$")


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

WORLD_SET_SCHEMA = {
    "name": "world_set",
    "description": (
        "Write one canonical fact through WYRD's official fact event contract. "
        "Use only for grounded world facts; successful writes emit content-free change metadata."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "subject_id": {
                "type": "string",
                "description": "Lowercase WYRD subject/entity ID.",
                "maxLength": 64,
            },
            "key": {
                "type": "string",
                "description": "Bounded lowercase fact key.",
                "maxLength": 64,
            },
            "value": {
                "type": "string",
                "description": "Grounded fact value.",
                "maxLength": 2000,
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Optional confidence; defaults to WYRD's 0.85.",
            },
            "domain": {
                "type": "string",
                "description": "Optional lowercase world-fact domain.",
                "maxLength": 64,
            },
        },
        "required": ["subject_id", "key", "value"],
        "additionalProperties": False,
    },
}

WORLD_OBSERVE_SCHEMA = {
    "name": "world_observe",
    "description": (
        "Record one bounded observation through WYRD's official observation event contract. "
        "Successful writes emit content-free change metadata."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Short observation title.",
                "maxLength": 200,
            },
            "summary": {
                "type": "string",
                "description": "Grounded observation summary.",
                "maxLength": 2000,
            },
        },
        "required": ["title", "summary"],
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


def _bounded_text(value: Any, *, maximum: int) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if text and len(text) <= maximum else None


def build_world_set_handler(ctx, telemetry: WorldChangeTelemetry):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        subject_id = _entity_id(args.get("subject_id"))
        key = _bounded_text(args.get("key"), maximum=64)
        value = _bounded_text(args.get("value"), maximum=2000)
        domain = _bounded_text(args.get("domain", ""), maximum=64) or ""
        if subject_id is None:
            return tool_error("subject_id must be a valid lowercase WYRD entity ID")
        if key is None or not _FACT_KEY_RE.fullmatch(key):
            return tool_error("key must be a valid lowercase WYRD fact key")
        if value is None:
            return tool_error("value is required and must not exceed 2000 characters")
        if domain and not _DOMAIN_RE.fullmatch(domain):
            return tool_error("domain must be a valid lowercase WYRD domain")
        payload: dict[str, Any] = {
            "subject_id": subject_id,
            "key": key,
            "value": value,
        }
        if domain:
            payload["domain"] = domain
        if "confidence" in args:
            confidence = args.get("confidence")
            if isinstance(confidence, bool):
                return tool_error("confidence must be a number from 0 to 1")
            try:
                parsed_confidence = float(confidence)
            except (TypeError, ValueError, OverflowError):
                return tool_error("confidence must be a number from 0 to 1")
            if not 0.0 <= parsed_confidence <= 1.0:
                return tool_error("confidence must be a number from 0 to 1")
            payload["confidence"] = parsed_confidence
        try:
            response = request_wyrd_json(
                ctx,
                "/event",
                method="POST",
                body={"event_type": "fact", "payload": payload},
            )
            if response.get("ok") is not True:
                raise WyrdProtocolError("WYRD did not confirm the fact write")
        except WyrdProtocolError as exc:
            return tool_error(str(exc))
        published = telemetry.record(
            ctx,
            "fact",
            value_chars=len(value),
            confidence_supplied="confidence" in payload,
            domain_supplied=bool(domain),
        )
        return tool_result(
            {
                "success": True,
                "write": "fact",
                "event_published": published,
            }
        )

    return handle


def build_world_observe_handler(ctx, telemetry: WorldChangeTelemetry):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        title = _bounded_text(args.get("title"), maximum=200)
        summary = _bounded_text(args.get("summary"), maximum=2000)
        if title is None:
            return tool_error("title is required and must not exceed 200 characters")
        if summary is None:
            return tool_error("summary is required and must not exceed 2000 characters")
        try:
            response = request_wyrd_json(
                ctx,
                "/event",
                method="POST",
                body={
                    "event_type": "observation",
                    "payload": {"title": title, "summary": summary},
                },
            )
            if response.get("ok") is not True:
                raise WyrdProtocolError("WYRD did not confirm the observation write")
        except WyrdProtocolError as exc:
            return tool_error(str(exc))
        published = telemetry.record(
            ctx,
            "observation",
            title_chars=len(title),
            summary_chars=len(summary),
        )
        return tool_result(
            {
                "success": True,
                "write": "observation",
                "event_published": published,
            }
        )

    return handle


def register_wyrd_tools(ctx) -> None:
    telemetry = WorldChangeTelemetry()
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
    ctx.register_tool(
        name="world_set",
        toolset="volmarr_world",
        schema=WORLD_SET_SCHEMA,
        handler=build_world_set_handler(ctx, telemetry),
        description=WORLD_SET_SCHEMA["description"],
        emoji="🧭",
    )
    ctx.register_tool(
        name="world_observe",
        toolset="volmarr_world",
        schema=WORLD_OBSERVE_SCHEMA,
        handler=build_world_observe_handler(ctx, telemetry),
        description=WORLD_OBSERVE_SCHEMA["description"],
        emoji="👁️",
    )
