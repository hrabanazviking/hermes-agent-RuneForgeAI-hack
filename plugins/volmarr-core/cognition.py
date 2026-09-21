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
MAX_COMPLETION_BYTES = 1024 * 1024
MAX_MODELS = 256
_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32,256}$")


class CognitionConfigurationError(ValueError):
    """The endpoint would cross its declared profile or loopback boundary."""


class CognitionRequestError(ValueError):
    """A local completion request violates the bounded text contract."""


class CognitionProtocolError(RuntimeError):
    """The endpoint returned a response outside the admitted protocol subset."""


def _bounded_probe_timeout(value: Any) -> float:
    try:
        timeout_ms = int(value)
    except (TypeError, ValueError):
        timeout_ms = DEFAULT_PROBE_TIMEOUT_MS
    return min(10_000, max(50, timeout_ms)) / 1_000


def _bounded_request_timeout(value: Any) -> float:
    try:
        timeout_ms = int(value)
    except (TypeError, ValueError):
        timeout_ms = 30_000
    return min(3_600_000, max(1_000, timeout_ms)) / 1_000


def _bounded_local_max_tokens(value: Any) -> int:
    try:
        tokens = int(value)
    except (TypeError, ValueError):
        tokens = 256
    return min(16_384, max(1, tokens))


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
    request_timeout_seconds: float
    local_max_tokens: int

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
            request_timeout_seconds=_bounded_request_timeout(
                ctx.get_config("cognition_request_timeout_ms", 30_000)
            ),
            local_max_tokens=_bounded_local_max_tokens(
                ctx.get_config("cognition_local_max_tokens", 256)
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


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open_local(request: urllib.request.Request, timeout: float):
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        _NoRedirect(),
    )
    return opener.open(request, timeout=timeout)


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
        with _open_local(request, settings.probe_timeout_seconds) as response:
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


@dataclass(frozen=True)
class AesirCompletionRequest:
    model: str
    messages: tuple[dict[str, str], ...]
    max_tokens: int

    @classmethod
    def from_mapping(
        cls,
        payload: Any,
        *,
        max_tokens_limit: int,
    ) -> "AesirCompletionRequest":
        if not isinstance(payload, dict):
            raise CognitionRequestError("local request must be a JSON object")
        unknown = sorted(set(payload) - {"model", "messages", "max_tokens"})
        if unknown:
            raise CognitionRequestError(
                "local request contains unsupported fields: " + ", ".join(unknown)
            )
        model = payload.get("model")
        if not isinstance(model, str) or not model or len(model.encode("utf-8")) > 256:
            raise CognitionRequestError("model must contain 1..256 UTF-8 bytes")
        max_tokens = payload.get("max_tokens", max_tokens_limit)
        if (
            isinstance(max_tokens, bool)
            or not isinstance(max_tokens, int)
            or not 1 <= max_tokens <= max_tokens_limit
        ):
            raise CognitionRequestError("max_tokens exceeds the configured local limit")
        rows = payload.get("messages")
        if not isinstance(rows, list) or not 1 <= len(rows) <= 128:
            raise CognitionRequestError("messages must contain 1..128 rows")
        messages: list[dict[str, str]] = []
        total_bytes = 0
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"role", "content"}:
                raise CognitionRequestError("each message requires only role and content")
            role, content = row.get("role"), row.get("content")
            if role not in {"system", "user", "assistant"} or not isinstance(content, str):
                raise CognitionRequestError("message role or content is invalid")
            content_bytes = len(content.encode("utf-8"))
            if not 1 <= content_bytes <= 65_536:
                raise CognitionRequestError("message content is outside the supported bound")
            total_bytes += content_bytes
            messages.append({"role": role, "content": content})
        if total_bytes > 65_536 or messages[-1]["role"] != "user":
            raise CognitionRequestError(
                "messages exceed 64 KiB or do not end with a user message"
            )
        return cls(model=model, messages=tuple(messages), max_tokens=max_tokens)


@dataclass(frozen=True)
class AesirCompletion:
    model: str
    text: str
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int


def complete_aesir(ctx, payload: Any) -> AesirCompletion:
    """Execute one bounded, non-streaming, tool-free local completion."""
    settings = AesirSettings.from_plugin_context(ctx)
    local_request = AesirCompletionRequest.from_mapping(
        payload,
        max_tokens_limit=settings.local_max_tokens,
    )
    key = _read_service_key(settings.key_path)
    body = json.dumps(
        {
            "model": local_request.model,
            "messages": list(local_request.messages),
            "max_tokens": local_request.max_tokens,
            "stream": False,
            "n": 1,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(body) > 128 * 1024:
        raise CognitionRequestError("local request body exceeds 128 KiB")
    request = urllib.request.Request(
        f"{settings.base_url}/chat/completions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    started = time.monotonic()
    try:
        with _open_local(request, settings.request_timeout_seconds) as response:
            raw = response.read(MAX_COMPLETION_BYTES + 1)
    except Exception as exc:
        raise CognitionProtocolError(type(exc).__name__) from exc
    latency_ms = max(0, round((time.monotonic() - started) * 1_000))
    if len(raw) > MAX_COMPLETION_BYTES:
        raise CognitionProtocolError("completion response exceeds 1 MiB")
    try:
        response_payload = json.loads(raw.decode("utf-8"))
        choices = response_payload["choices"]
        choice = choices[0] if isinstance(choices, list) and len(choices) == 1 else None
        message = choice.get("message") if isinstance(choice, dict) else None
        text = message.get("content") if isinstance(message, dict) else None
        finish_reason = choice.get("finish_reason") if isinstance(choice, dict) else None
        usage = response_payload.get("usage")
        model = response_payload.get("model")
        prompt_tokens = usage.get("prompt_tokens") if isinstance(usage, dict) else None
        completion_tokens = usage.get("completion_tokens") if isinstance(usage, dict) else None
        if (
            not isinstance(text, str)
            or not isinstance(finish_reason, str)
            or not isinstance(model, str)
            or isinstance(prompt_tokens, bool)
            or not isinstance(prompt_tokens, int)
            or isinstance(completion_tokens, bool)
            or not isinstance(completion_tokens, int)
            or prompt_tokens < 0
            or completion_tokens < 0
        ):
            raise CognitionProtocolError("completion response has an invalid shape")
    except (KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CognitionProtocolError("completion response has an invalid shape") from exc
    return AesirCompletion(
        model=model,
        text=text,
        finish_reason=finish_reason,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
    )
