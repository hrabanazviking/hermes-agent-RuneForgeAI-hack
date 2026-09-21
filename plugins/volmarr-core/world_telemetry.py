"""Content-free Verðandi events for confirmed WYRD world-model writes."""

from __future__ import annotations

from typing import Any

from .verdandi import VerdandiPublisher


WORLD_CHANGE_SCHEMA = "runeforge.wyrd.change"
WORLD_CHANGE_SCHEMA_VERSION = 1


class WorldChangeTelemetry:
    """Publish write metadata only after WYRD confirms the mutation."""

    def __init__(self, publisher: VerdandiPublisher | None = None) -> None:
        self._publisher = publisher or VerdandiPublisher()

    def record(self, ctx, change_kind: str, **metadata: Any) -> bool:
        event_type = {
            "fact": "hermes.world.fact_changed",
            "observation": "hermes.world.observation_recorded",
        }[change_kind]
        return self._publisher.publish(
            ctx,
            event_type,
            {
                "change_kind": change_kind,
                **metadata,
            },
            schema=WORLD_CHANGE_SCHEMA,
            schema_version=WORLD_CHANGE_SCHEMA_VERSION,
        )
