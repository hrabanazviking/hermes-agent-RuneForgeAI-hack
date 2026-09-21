"""Profile-safe attachment to A.E.S.I.R.'s bounded local text endpoint."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from hermes_constants import get_hermes_home


DEFAULT_BASE_URL = "http://127.0.0.1:18434/v1"
DEFAULT_KEY_PATH = Path("secrets") / "aesir.key"
DEFAULT_PROBE_TIMEOUT_MS = 2_000
MAX_CATALOG_BYTES = 256 * 1024
MAX_MODELS = 256
_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32,256}$")


class CognitionConfigurationError(ValueError):
    """The endpoint would cross its declared profile or loopback boundary."""


def _bounded_probe_timeout(value: Any) -> float:
    try:
        timeout_ms = int(value)
    except (TypeError, ValueError):
        timeout_ms = DEFAULT_PROBE_TIMEOUT_MS
    return min(10_000, max(50, timeout_ms)) / 1_000


def _profile_path(value: Any) -> Path:
    home = get_hermes_home().resolve()
    configured = Path(str(value or DEFAULT_KEY_PATH))
    if configured.is_absolute():
        return configured
    resolved = (home / configured).resolve()
    if not resolved.is_relative_to(home):
        raise CognitionConfigurationError("relative credential path escapes the active profile")
    return resolved


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
    ):
        raise CognitionConfigurationError(
            "local cognition endpoint must be plain HTTP on 127.0.0.1"
        )
    try:
        port = parsed.port
    except ValueError as exc:
        raise CognitionConfigurationError("local cognition endpoint has an invalid port") from exc
    if port is None or not (1 <= port <= 65535):
        raise CognitionConfigurationError("local cognition endpoint requires an explicit port")
    path = parsed.path.rstrip("/")
    if path != "/v1":
        raise CognitionConfigurationError("local cognition endpoint path must be /v1")
    return urlunsplit(("http", f"127.0.0.1:{port}", path, "", ""))


@dataclass(frozen=True)
class AesirSettings:
    base_url: str
    key_path: Path
    probe_timeout_seconds: float

    @classmethod
    def from_plugin_context(cls, ctx) -> "AesirSettings":
        return cls(
            base_url=_loopback_base_url(
                ctx.get_config("cognition_base_url", DEFAULT_BASE_URL)
            ),
            key_path=_profile_path(
                ctx.get_config("cognition_api_key_file", str(DEFAULT_KEY_PATH))
            ),
            probe_timeout_seconds=_bounded_probe_timeout(
                ctx.get_config("cognition_probe_timeout_ms", DEFAULT_PROBE_TIMEOUT_MS)
            ),
        )


def _read_service_key(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise CognitionConfigurationError("A.E.S.I.R. credential file is missing or unsafe")
    if os.name != "nt" and path.stat().st_mode & 0o077:
        raise CognitionConfigurationError("A.E.S.I.R. credential file must use mode 0600")
    raw = path.read_bytes()
    if len(raw) > 257:
        raise CognitionConfigurationError("A.E.S.I.R. credential is too large")
    try:
        key = raw.decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise CognitionConfigurationError("A.E.S.I.R. credential is not ASCII") from exc
    if not _KEY_PATTERN.fullmatch(key):
        raise CognitionConfigurationError("A.E.S.I.R. credential format is invalid")
    return key


@dataclass(frozen=True)
class AesirHealth:
    healthy: bool
    status: str
    base_url: str
    models: tuple[str, ...] = ()
    latency_ms: int | None = None
    error_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["models"] = list(self.models)
        return payload


def _catalog_models(payload: Any) -> tuple[str, ...]:
    if not isinstance(payload, dict) or payload.get("object") != "list":
        raise ValueError("catalog is not an OpenAI model list")
    rows = payload.get("data")
    if not isinstance(rows, list) or len(rows) > MAX_MODELS:
        raise ValueError("catalog has an invalid model collection")
    models: list[str] = []
    for row in rows:
        model_id = row.get("id") if isinstance(row, dict) else None
        if not isinstance(model_id, str) or not model_id or len(model_id) > 256:
            raise ValueError("catalog has an invalid model id")
        models.append(model_id)
    return tuple(models)


def probe_aesir(ctx) -> AesirHealth:
    """Verify the configured A.E.S.I.R. catalog without exposing its bearer key."""
    try:
        settings = AesirSettings.from_plugin_context(ctx)
        key = _read_service_key(settings.key_path)
    except Exception as exc:
        return AesirHealth(
            False,
            "configuration_error",
            str(ctx.get_config("cognition_base_url", DEFAULT_BASE_URL)),
            error_type=type(exc).__name__,
        )

    started = time.monotonic()
    request = urllib.request.Request(
        f"{settings.base_url}/models",
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=settings.probe_timeout_seconds,
        ) as response:
            raw = response.read(MAX_CATALOG_BYTES + 1)
        latency_ms = max(0, round((time.monotonic() - started) * 1_000))
        if len(raw) > MAX_CATALOG_BYTES:
            raise ValueError("catalog response exceeds the configured bound")
        models = _catalog_models(json.loads(raw.decode("utf-8")))
        return AesirHealth(True, "healthy", settings.base_url, models, latency_ms)
    except urllib.error.HTTPError as exc:
        latency_ms = max(0, round((time.monotonic() - started) * 1_000))
        status = "authentication_error" if exc.code in {401, 403} else "unreachable"
        return AesirHealth(False, status, settings.base_url, latency_ms=latency_ms)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        latency_ms = max(0, round((time.monotonic() - started) * 1_000))
        return AesirHealth(
            False,
            "protocol_error",
            settings.base_url,
            latency_ms=latency_ms,
            error_type=type(exc).__name__,
        )
    except Exception as exc:
        latency_ms = max(0, round((time.monotonic() - started) * 1_000))
        return AesirHealth(
            False,
            "unreachable",
            settings.base_url,
            latency_ms=latency_ms,
            error_type=type(exc).__name__,
        )
