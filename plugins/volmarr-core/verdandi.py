"""Profile-safe, fail-open publisher for Verðandi's JSON-line socket protocol."""

from __future__ import annotations

import json
import logging
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from hermes_constants import get_hermes_home


logger = logging.getLogger(__name__)

SCHEMA = "runeforge.hermes.lifecycle"
SCHEMA_VERSION = 1
DEFAULT_SOCKET_PATH = Path("state") / "runa.sock"
DEFAULT_TIMEOUT_MS = 100
MAX_TIMEOUT_MS = 1_000


def _bounded_timeout(value: Any) -> int:
    try:
        timeout = int(value)
    except (TypeError, ValueError):
        timeout = DEFAULT_TIMEOUT_MS
    return min(MAX_TIMEOUT_MS, max(1, timeout))


def _socket_path(value: Any) -> Path:
    home = get_hermes_home().resolve()
    configured = Path(str(value or DEFAULT_SOCKET_PATH))
    if configured.is_absolute():
        return configured
    resolved = (home / configured).resolve()
    if not resolved.is_relative_to(home):
        return home / DEFAULT_SOCKET_PATH
    return resolved


@dataclass(frozen=True)
class VerdandiSettings:
    socket_path: Path
    timeout_seconds: float
    source: str

    @classmethod
    def from_plugin_context(cls, ctx) -> "VerdandiSettings":
        timeout_ms = _bounded_timeout(ctx.get_config("timeout_ms", DEFAULT_TIMEOUT_MS))
        source = str(ctx.get_config("source", "hermes-agent") or "hermes-agent")[:128]
        return cls(
            socket_path=_socket_path(ctx.get_config("socket_path", str(DEFAULT_SOCKET_PATH))),
            timeout_seconds=timeout_ms / 1_000,
            source=source,
        )


def build_envelope(event_type: str, context: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "event_id": str(uuid4()),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        "context": dict(context),
    }


class VerdandiPublisher:
    """Publish one event without allowing transport failure into the agent turn."""

    def publish(self, ctx, event_type: str, context: Mapping[str, Any]) -> bool:
        try:
            socket_family = getattr(socket, "AF_UNIX", None)
            if socket_family is None:
                logger.debug("Verðandi lifecycle event dropped (AF_UNIX unavailable)")
                return False
            settings = VerdandiSettings.from_plugin_context(ctx)
            payload = {
                "type": event_type,
                "source": settings.source,
                "data": build_envelope(event_type, context),
            }
            encoded = (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
            with socket.socket(socket_family, socket.SOCK_STREAM) as client:
                client.settimeout(settings.timeout_seconds)
                client.connect(str(settings.socket_path))
                client.sendall(encoded)
            return True
        except Exception as exc:
            logger.debug("Verðandi lifecycle event dropped (%s)", type(exc).__name__)
            return False
