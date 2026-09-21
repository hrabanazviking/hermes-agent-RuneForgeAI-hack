"""Execute admitted local reflex work or return an explicit higher-tier directive."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .cognition import AesirCompletionRequest, AesirSettings, complete_aesir
from .routing import CognitionRequest, CognitionRouter, RoutingRequestError
from .telemetry import CognitionTelemetry


EXECUTION_SCHEMA = "runeforge.cognition.execution"
EXECUTION_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class CognitionExecutionRequest:
    route_request: CognitionRequest
    local_request: Mapping[str, Any] | None

    @classmethod
    def from_mapping(cls, payload: Any) -> "CognitionExecutionRequest":
        if not isinstance(payload, Mapping):
            raise RoutingRequestError("execution request must be a JSON object")
        unknown = sorted(set(payload) - {"schema_version", "route", "local"})
        if unknown:
            raise RoutingRequestError(
                "execution request contains unsupported fields: " + ", ".join(unknown)
            )
        schema_version = payload.get("schema_version", EXECUTION_SCHEMA_VERSION)
        if (
            isinstance(schema_version, bool)
            or not isinstance(schema_version, int)
            or schema_version != EXECUTION_SCHEMA_VERSION
        ):
            raise RoutingRequestError("unsupported execution schema version")
        route_payload = payload.get("route")
        if not isinstance(route_payload, Mapping):
            raise RoutingRequestError("execution request requires route metadata")
        local_payload = payload.get("local")
        if local_payload is not None and not isinstance(local_payload, Mapping):
            raise RoutingRequestError("local request must be a JSON object")
        return cls(
            route_request=CognitionRequest.from_mapping(route_payload),
            local_request=local_payload,
        )


@dataclass(frozen=True)
class CognitionExecutionResult:
    status: str
    decision: dict[str, Any]
    completion: dict[str, Any] | None = None
    error_type: str | None = None
    schema: str = EXECUTION_SCHEMA
    schema_version: int = EXECUTION_SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CognitionExecutor:
    """Run only local text work; cloud and deterministic tiers remain directives."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._telemetry = CognitionTelemetry()

    def execute(self, request: CognitionExecutionRequest) -> CognitionExecutionResult:
        decision = CognitionRouter.from_plugin_context(self._ctx).decide(
            request.route_request
        )
        self._telemetry.record_decision(self._ctx, decision)
        decision_payload = decision.as_dict()
        if decision.route == "deterministic":
            return CognitionExecutionResult("deterministic_required", decision_payload)
        if decision.route == "cloud":
            return CognitionExecutionResult("escalation_required", decision_payload)
        if decision.route == "blocked":
            return CognitionExecutionResult("blocked", decision_payload)
        if request.local_request is None:
            return self._local_failure(decision, "MissingLocalRequest")

        try:
            settings = AesirSettings.from_plugin_context(self._ctx)
            admitted = AesirCompletionRequest.from_mapping(
                request.local_request,
                max_tokens_limit=settings.local_max_tokens,
            )
            actual_input_bytes = sum(
                len(message["content"].encode("utf-8"))
                for message in admitted.messages
            )
            if actual_input_bytes != request.route_request.input_bytes:
                raise RoutingRequestError(
                    "route input_bytes does not match local message content"
                )
            completion = complete_aesir(self._ctx, request.local_request)
        except Exception as exc:
            return self._local_failure(decision, type(exc).__name__)

        self._telemetry.record_local_completion(self._ctx, decision, completion)
        return CognitionExecutionResult(
            "completed",
            decision_payload,
            completion={
                "model": completion.model,
                "text": completion.text,
                "finish_reason": completion.finish_reason,
                "prompt_tokens": completion.prompt_tokens,
                "completion_tokens": completion.completion_tokens,
                "latency_ms": completion.latency_ms,
            },
        )

    def _local_failure(
        self,
        decision,
        error_type: str,
    ) -> CognitionExecutionResult:
        escalation_required = decision.mode == "auto"
        self._telemetry.record_local_failure(
            self._ctx,
            decision,
            error_type,
            escalation_required=escalation_required,
        )
        return CognitionExecutionResult(
            "escalation_required" if escalation_required else "failed",
            decision.as_dict(),
            error_type=error_type,
        )
