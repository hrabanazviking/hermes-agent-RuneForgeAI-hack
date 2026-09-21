"""Read-only health contracts for Volmarr integration transports."""

from __future__ import annotations

import json
import socket
import time
from dataclasses import asdict, dataclass
from typing import Any

from .verdandi import VerdandiSettings


MAX_HEALTH_RESPONSE_BYTES = 64 * 1024


@dataclass(frozen=True)
class VerdandiHealth:
    healthy: bool
    status: str
    socket_path: str
    latency_ms: int | None = None
    sequence: int | None = None
    uptime_seconds: float | None = None
    subscribers: int | None = None
    error_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _optional_number(payload: dict[str, Any], key: str, expected_type):
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, expected_type):
        return None
    return value


def probe_verdandi(ctx) -> VerdandiHealth:
    """Ping the active profile's hub and classify the transport without mutating it."""
    settings = VerdandiSettings.from_plugin_context(ctx)
    socket_path = str(settings.socket_path)
    socket_family = getattr(socket, "AF_UNIX", None)
    if socket_family is None:
        return VerdandiHealth(False, "unsupported", socket_path)

    started = time.monotonic()
    try:
        with socket.socket(socket_family, socket.SOCK_STREAM) as client:
            client.settimeout(settings.timeout_seconds)
            client.connect(socket_path)
            client.sendall(b'{"nerve_type":"ping"}\n')
            response = client.recv(MAX_HEALTH_RESPONSE_BYTES)
        latency_ms = max(0, round((time.monotonic() - started) * 1_000))
        payload = json.loads(response.decode("utf-8").strip())
        if not isinstance(payload, dict) or payload.get("nerve_type") != "pong":
            return VerdandiHealth(False, "protocol_error", socket_path, latency_ms)
        return VerdandiHealth(
            True,
            "healthy",
            socket_path,
            latency_ms,
            sequence=_optional_number(payload, "seq", int),
            uptime_seconds=_optional_number(payload, "uptime_s", (int, float)),
            subscribers=_optional_number(payload, "subscribers", int),
        )
    except (json.JSONDecodeError, UnicodeDecodeError):
        latency_ms = max(0, round((time.monotonic() - started) * 1_000))
        return VerdandiHealth(False, "protocol_error", socket_path, latency_ms)
    except Exception as exc:
        latency_ms = max(0, round((time.monotonic() - started) * 1_000))
        return VerdandiHealth(
            False,
            "unreachable",
            socket_path,
            latency_ms,
            error_type=type(exc).__name__,
        )
