"""Metadata-only cognition telemetry carried by the Verðandi signal spine."""

from __future__ import annotations

from .routing import CognitionDecision
from .verdandi import VerdandiPublisher


COGNITION_TELEMETRY_SCHEMA = "runeforge.cognition.telemetry"
COGNITION_TELEMETRY_SCHEMA_VERSION = 1
_ROUTE_EVENTS = {
    "deterministic": "hermes.cognition.deterministic",
    "local": "hermes.cognition.local",
    "cloud": "hermes.cognition.escalated",
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
            },
            schema=COGNITION_TELEMETRY_SCHEMA,
            schema_version=COGNITION_TELEMETRY_SCHEMA_VERSION,
        )
