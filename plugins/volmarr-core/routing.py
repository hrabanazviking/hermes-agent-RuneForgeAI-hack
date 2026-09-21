"""Versioned, content-free route decisions for Volmarr cognition operations."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping


ROUTING_SCHEMA = "runeforge.cognition.route"
ROUTING_SCHEMA_VERSION = 1
DEFAULT_LOCAL_INPUT_LIMIT_BYTES = 32_768
MAX_LOCAL_INPUT_LIMIT_BYTES = 65_536
MAX_DECLARED_INPUT_BYTES = 128 * 1024 * 1024
_OPERATION_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "operation",
        "input_bytes",
        "complexity",
        "deterministic_available",
        "requires_tools",
        "requires_vision",
        "requires_external_data",
        "local_failures",
    }
)


class RoutingRequestError(ValueError):
    """A routing request is malformed or attempts to include undeclared content."""


def _strict_bool(payload: Mapping[str, Any], key: str) -> bool:
    value = payload.get(key, False)
    if not isinstance(value, bool):
        raise RoutingRequestError(f"{key} must be a boolean")
    return value


def _strict_int(payload: Mapping[str, Any], key: str, default: int = 0) -> int:
    value = payload.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise RoutingRequestError(f"{key} must be an integer")
    return value


@dataclass(frozen=True)
class CognitionRequest:
    operation: str
    input_bytes: int
    complexity: str = "low"
    deterministic_available: bool = False
    requires_tools: bool = False
    requires_vision: bool = False
    requires_external_data: bool = False
    local_failures: int = 0

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "CognitionRequest":
        if not isinstance(payload, Mapping):
            raise RoutingRequestError("routing request must be a JSON object")
        unknown = sorted(set(payload) - _REQUEST_FIELDS)
        if unknown:
            raise RoutingRequestError(
                "routing request contains unsupported fields: " + ", ".join(unknown)
            )
        schema_version = _strict_int(payload, "schema_version", ROUTING_SCHEMA_VERSION)
        if schema_version != ROUTING_SCHEMA_VERSION:
            raise RoutingRequestError("unsupported routing schema version")
        operation = payload.get("operation")
        if not isinstance(operation, str) or not _OPERATION_PATTERN.fullmatch(operation):
            raise RoutingRequestError("operation must be a lowercase dotted identifier")
        input_bytes = _strict_int(payload, "input_bytes")
        if not 0 <= input_bytes <= MAX_DECLARED_INPUT_BYTES:
            raise RoutingRequestError("input_bytes is outside the supported range")
        complexity = payload.get("complexity", "low")
        if complexity not in {"low", "medium", "high"}:
            raise RoutingRequestError("complexity must be low, medium, or high")
        local_failures = _strict_int(payload, "local_failures")
        if not 0 <= local_failures <= 1_000:
            raise RoutingRequestError("local_failures is outside the supported range")
        return cls(
            operation=operation,
            input_bytes=input_bytes,
            complexity=complexity,
            deterministic_available=_strict_bool(payload, "deterministic_available"),
            requires_tools=_strict_bool(payload, "requires_tools"),
            requires_vision=_strict_bool(payload, "requires_vision"),
            requires_external_data=_strict_bool(payload, "requires_external_data"),
            local_failures=local_failures,
        )


@dataclass(frozen=True)
class RoutingSettings:
    local_input_limit_bytes: int

    @classmethod
    def from_plugin_context(cls, ctx) -> "RoutingSettings":
        raw = ctx.get_config(
            "cognition_local_input_limit_bytes",
            DEFAULT_LOCAL_INPUT_LIMIT_BYTES,
        )
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = DEFAULT_LOCAL_INPUT_LIMIT_BYTES
        return cls(min(MAX_LOCAL_INPUT_LIMIT_BYTES, max(1, value)))


@dataclass(frozen=True)
class CognitionDecision:
    route: str
    reason: str
    operation: str
    input_bytes: int
    local_input_limit_bytes: int
    schema: str = ROUTING_SCHEMA
    schema_version: int = ROUTING_SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CognitionRouter:
    """Choose a capability tier without choosing or calling a cloud provider."""

    def __init__(self, settings: RoutingSettings) -> None:
        self._settings = settings

    @classmethod
    def from_plugin_context(cls, ctx) -> "CognitionRouter":
        return cls(RoutingSettings.from_plugin_context(ctx))

    def decide(self, request: CognitionRequest) -> CognitionDecision:
        if request.deterministic_available:
            route, reason = "deterministic", "deterministic.available"
        elif request.requires_tools:
            route, reason = "cloud", "capability.tools"
        elif request.requires_vision:
            route, reason = "cloud", "capability.vision"
        elif request.requires_external_data:
            route, reason = "cloud", "capability.external_data"
        elif request.local_failures:
            route, reason = "cloud", "local.previous_failure"
        elif request.complexity == "high":
            route, reason = "cloud", "complexity.high"
        elif request.input_bytes > self._settings.local_input_limit_bytes:
            route, reason = "cloud", "input.over_local_limit"
        else:
            route, reason = "local", "local.within_bounds"
        return CognitionDecision(
            route=route,
            reason=reason,
            operation=request.operation,
            input_bytes=request.input_bytes,
            local_input_limit_bytes=self._settings.local_input_limit_bytes,
        )
