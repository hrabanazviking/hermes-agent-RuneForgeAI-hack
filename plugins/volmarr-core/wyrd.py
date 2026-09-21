"""Read-only attachment probe for the official WYRD HTTP world-model service."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit


DEFAULT_BASE_URL = "http://127.0.0.1:8765"
DEFAULT_PROBE_TIMEOUT_MS = 2_000
MINIMUM_SERVER_VERSION = "1.0.0"
API_CONTRACT = "wyrd-http-v1"
MAX_HEALTH_BYTES = 64 * 1024
_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[.+-][0-9A-Za-z.-]+)?$")


class WyrdConfigurationError(ValueError):
    """The configured service crosses the initial loopback-only boundary."""


class WyrdProtocolError(ValueError):
    """The local service did not satisfy the bounded WYRD HTTP contract."""


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = _VERSION_RE.fullmatch(value.strip())
    if not match:
        raise ValueError("WYRD health response has an invalid version")
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
        raise WyrdConfigurationError(
            "initial WYRD attachment must be plain HTTP on 127.0.0.1"
        )
    try:
        port = parsed.port
    except ValueError as exc:
        raise WyrdConfigurationError("WYRD endpoint has an invalid port") from exc
    if port is None or not 1 <= port <= 65535:
        raise WyrdConfigurationError("WYRD endpoint requires an explicit port")
    return urlunsplit(("http", f"127.0.0.1:{port}", "", "", ""))


def _bounded_timeout(value: Any) -> float:
    if isinstance(value, bool):
        value = DEFAULT_PROBE_TIMEOUT_MS
    try:
        timeout_ms = int(value)
    except (TypeError, ValueError, OverflowError):
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


def request_wyrd_json(
    ctx,
    path: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call one allowlisted local WYRD route with bounded JSON transport."""
    if not path.startswith("/") or "#" in path:
        raise WyrdProtocolError("invalid WYRD request path")
    base_url = _loopback_base_url(ctx.get_config("wyrd_base_url", DEFAULT_BASE_URL))
    timeout = _bounded_timeout(
        ctx.get_config("wyrd_probe_timeout_ms", DEFAULT_PROBE_TIMEOUT_MS)
    )
    encoded = None
    headers = {
        "Accept": "application/json",
        "User-Agent": "runeforgeai-hermes-wyrd-tools/1",
    }
    if body is not None:
        encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        if len(encoded) > 32 * 1024:
            raise WyrdProtocolError("WYRD request exceeds 32 KiB")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=encoded,
        method=method,
        headers=headers,
    )
    try:
        with _open_local(request, timeout) as response:
            raw = response.read(MAX_HEALTH_BYTES + 1)
    except urllib.error.HTTPError as exc:
        if exc.code in {301, 302, 303, 307, 308}:
            raise WyrdProtocolError("WYRD refused a redirected response") from exc
        raise WyrdProtocolError(f"WYRD returned HTTP {exc.code}") from exc
    except Exception as exc:
        raise WyrdProtocolError("WYRD service is unreachable") from exc
    if len(raw) > MAX_HEALTH_BYTES:
        raise WyrdProtocolError("WYRD response exceeds 64 KiB")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WyrdProtocolError("WYRD response is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise WyrdProtocolError("WYRD response is not an object")
    return payload


@dataclass(frozen=True)
class WyrdHealth:
    healthy: bool
    status: str
    base_url: str
    api_contract: str = API_CONTRACT
    server_version: str | None = None
    minimum_server_version: str = MINIMUM_SERVER_VERSION
    latency_ms: int | None = None
    error_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def probe_wyrd(ctx) -> WyrdHealth:
    """Probe the official read-only liveness contract without credentials or writes."""
    configured = ctx.get_config("wyrd_base_url", DEFAULT_BASE_URL)
    try:
        base_url = _loopback_base_url(configured)
        timeout = _bounded_timeout(
            ctx.get_config("wyrd_probe_timeout_ms", DEFAULT_PROBE_TIMEOUT_MS)
        )
    except Exception as exc:
        return WyrdHealth(
            False,
            "configuration_error",
            str(configured),
            error_type=type(exc).__name__,
        )

    request = urllib.request.Request(
        f"{base_url}/health",
        headers={
            "Accept": "application/json",
            "User-Agent": "runeforgeai-hermes-wyrd-health/1",
        },
    )
    started = time.monotonic()
    try:
        with _open_local(request, timeout) as response:
            raw = response.read(MAX_HEALTH_BYTES + 1)
        latency_ms = max(0, round((time.monotonic() - started) * 1_000))
        if len(raw) > MAX_HEALTH_BYTES:
            raise ValueError("WYRD health response exceeds 64 KiB")
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("WYRD health response is not an object")
        version = payload.get("version")
        if version is not None and not isinstance(version, str):
            raise ValueError("WYRD health response has an invalid version")
        if payload.get("status") != "ok":
            return WyrdHealth(
                False,
                "server_unhealthy",
                base_url,
                server_version=version,
                latency_ms=latency_ms,
            )
        # The official 1.0.0 implementation returns only {"status": "ok"},
        # while its published HTTP documentation also shows a version field.
        # Accept both. If a server volunteers a version, enforce the minimum.
        if version is not None and _version_tuple(version) < _version_tuple(
            MINIMUM_SERVER_VERSION
        ):
            return WyrdHealth(
                False,
                "server_outdated",
                base_url,
                server_version=version,
                latency_ms=latency_ms,
            )
        return WyrdHealth(
            True,
            "healthy",
            base_url,
            server_version=version,
            latency_ms=latency_ms,
        )
    except urllib.error.HTTPError as exc:
        latency_ms = max(0, round((time.monotonic() - started) * 1_000))
        status = (
            "protocol_error"
            if exc.code in {301, 302, 303, 307, 308}
            else "unreachable"
        )
        return WyrdHealth(False, status, base_url, latency_ms=latency_ms)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        latency_ms = max(0, round((time.monotonic() - started) * 1_000))
        return WyrdHealth(
            False,
            "protocol_error",
            base_url,
            latency_ms=latency_ms,
            error_type=type(exc).__name__,
        )
    except Exception as exc:
        latency_ms = max(0, round((time.monotonic() - started) * 1_000))
        return WyrdHealth(
            False,
            "unreachable",
            base_url,
            latency_ms=latency_ms,
            error_type=type(exc).__name__,
        )
