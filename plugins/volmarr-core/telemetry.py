"""Metadata-only cognition telemetry carried by the Verðandi signal spine."""

from __future__ import annotations

from .cognition import AesirCompletion
from .routing import CognitionDecision
from .verdandi import VerdandiPublisher


COGNITION_TELEMETRY_SCHEMA = "runeforge.cognition.telemetry"
COGNITION_TELEMETRY_SCHEMA_VERSION = 1
_ROUTE_EVENTS = {
    "deterministic": "hermes.cognition.deterministic",
    "local": "hermes.cognition.local",
    "cloud": "hermes.cognition.escalated",
    "blocked": "hermes.cognition.blocked",
}


class CognitionTelemetry:
    """Publish routing facts without prompts, messages, credentials, or responses."""

    def __init__(self, publisher: VerdandiPublisher | None = None) -> None:
        self._publisher = publisher or VerdandiPublisher()

    def record_decision(self, ctx, decision: CognitionDecision) -> bool:
        return self._publisher.publish(
            ctx,
            _ROUTE_EVENTS[decision.route],
            {
                "operation": decision.operation,
                "route": decision.route,
                "reason": decision.reason,
                "input_bytes": decision.input_bytes,
                "local_input_limit_bytes": decision.local_input_limit_bytes,
                "mode": decision.mode,
            },
            schema=COGNITION_TELEMETRY_SCHEMA,
            schema_version=COGNITION_TELEMETRY_SCHEMA_VERSION,
        )

    def record_local_completion(
        self,
        ctx,
        decision: CognitionDecision,
        completion: AesirCompletion,
    ) -> bool:
        return self._publisher.publish(
            ctx,
            "hermes.cognition.local_completed",
            {
                "operation": decision.operation,
                "route": decision.route,
                "reason": decision.reason,
                "mode": decision.mode,
                "model": completion.model,
                "latency_ms": completion.latency_ms,
                "input_tokens": completion.prompt_tokens,
                "output_tokens": completion.completion_tokens,
                "finish_reason": completion.finish_reason,
            },
            schema=COGNITION_TELEMETRY_SCHEMA,
            schema_version=COGNITION_TELEMETRY_SCHEMA_VERSION,
        )

    def record_local_failure(
        self,
        ctx,
        decision: CognitionDecision,
        error_type: str,
        *,
        escalation_required: bool,
    ) -> bool:
        return self._publisher.publish(
            ctx,
            "hermes.cognition.local_failed",
            {
                "operation": decision.operation,
                "route": decision.route,
                "reason": decision.reason,
                "mode": decision.mode,
                "error_type": error_type[:128],
                "escalation_required": escalation_required,
            },
            schema=COGNITION_TELEMETRY_SCHEMA,
            schema_version=COGNITION_TELEMETRY_SCHEMA_VERSION,
        )
