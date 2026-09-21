"""Read-only attachment probe for Hermes' bundled OpenViking provider."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit


DEFAULT_BASE_URL = "http://127.0.0.1:1933"
DEFAULT_PROBE_TIMEOUT_MS = 2_000
MINIMUM_SERVER_VERSION = "0.4.21"
MAX_HEALTH_BYTES = 64 * 1024
_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[.+-][0-9A-Za-z.-]+)?$")


class OpenVikingConfigurationError(ValueError):
    """The configured server crosses the initial loopback-only boundary."""


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = _VERSION_RE.fullmatch(value.strip())
    if not match:
        raise ValueError("OpenViking health response has an invalid version")
    return tuple(int(part) for part in match.groups())


def _loopback_base_url(value: Any) -> str:
    raw = str(value or DEFAULT_BASE_URL).strip().rstrip("/")
    parsed = urlsplit(raw)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise OpenVikingConfigurationError(
            "initial OpenViking attachment must be plain HTTP on 127.0.0.1"
        )
    try:
        port = parsed.port
    except ValueError as exc:
        raise OpenVikingConfigurationError("OpenViking endpoint has an invalid port") from exc
    if port is None or not 1 <= port <= 65535:
        raise OpenVikingConfigurationError(
            "OpenViking endpoint requires an explicit port"
        )
    return urlunsplit(("http", f"127.0.0.1:{port}", "", "", ""))


def _bounded_timeout(value: Any) -> float:
    try:
        timeout_ms = int(value)
    except (TypeError, ValueError):
        timeout_ms = DEFAULT_PROBE_TIMEOUT_MS
    return min(10_000, max(50, timeout_ms)) / 1_000


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open_local(request: urllib.request.Request, timeout: float):
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        _NoRedirect(),
    )
    return opener.open(request, timeout=timeout)


@dataclass(frozen=True)
class OpenVikingHealth:
    healthy: bool
    status: str
    base_url: str
    provider_available: bool
    server_version: str | None = None
    minimum_server_version: str = MINIMUM_SERVER_VERSION
    latency_ms: int | None = None
    error_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _bundled_provider_available() -> bool:
    from plugins.memory import list_memory_provider_names

    return "openviking" in list_memory_provider_names()


def probe_openviking(ctx) -> OpenVikingHealth:
    """Attest the bundled provider and official server without credentials or writes."""
    configured = ctx.get_config("openviking_base_url", DEFAULT_BASE_URL)
    try:
        base_url = _loopback_base_url(configured)
        timeout = _bounded_timeout(
            ctx.get_config(
                "openviking_probe_timeout_ms",
                DEFAULT_PROBE_TIMEOUT_MS,
            )
        )
        provider_available = _bundled_provider_available()
    except Exception as exc:
        return OpenVikingHealth(
            False,
            "configuration_error",
            str(configured),
            False,
            error_type=type(exc).__name__,
        )
    if not provider_available:
        return OpenVikingHealth(False, "provider_missing", base_url, False)

    request = urllib.request.Request(
        f"{base_url}/health",
        headers={
            "Accept": "application/json",
            "User-Agent": "runeforgeai-hermes-openviking-health/1",
        },
    )
    started = time.monotonic()
    try:
        with _open_local(request, timeout) as response:
            raw = response.read(MAX_HEALTH_BYTES + 1)
        latency_ms = max(0, round((time.monotonic() - started) * 1_000))
        if len(raw) > MAX_HEALTH_BYTES:
            raise ValueError("OpenViking health response exceeds 64 KiB")
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("OpenViking health response is not an object")
        version = payload.get("version")
        if payload.get("status") != "ok" or payload.get("healthy") is not True:
            return OpenVikingHealth(
                False,
                "server_unhealthy",
                base_url,
                True,
                server_version=version if isinstance(version, str) else None,
                latency_ms=latency_ms,
            )
        if not isinstance(version, str):
            raise ValueError("OpenViking health response has no version")
        if _version_tuple(version) < _version_tuple(MINIMUM_SERVER_VERSION):
            return OpenVikingHealth(
                False,
                "server_outdated",
                base_url,
                True,
                server_version=version,
                latency_ms=latency_ms,
            )
        return OpenVikingHealth(
            True,
            "healthy",
            base_url,
            True,
            server_version=version,
            latency_ms=latency_ms,
        )
    except urllib.error.HTTPError as exc:
        latency_ms = max(0, round((time.monotonic() - started) * 1_000))
        if exc.code in {301, 302, 303, 307, 308}:
            status = "protocol_error"
        elif exc.code in {401, 403}:
            status = "authentication_required"
        else:
            status = "unreachable"
        return OpenVikingHealth(
            False,
            status,
            base_url,
            True,
            latency_ms=latency_ms,
        )
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        latency_ms = max(0, round((time.monotonic() - started) * 1_000))
        return OpenVikingHealth(
            False,
            "protocol_error",
            base_url,
            True,
            latency_ms=latency_ms,
            error_type=type(exc).__name__,
        )
    except Exception as exc:
        latency_ms = max(0, round((time.monotonic() - started) * 1_000))
        return OpenVikingHealth(
            False,
            "unreachable",
            base_url,
            True,
            latency_ms=latency_ms,
            error_type=type(exc).__name__,
        )
