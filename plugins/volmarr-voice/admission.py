"""Pre-socket admission validation for the future avatar loopback feed."""

from __future__ import annotations

import hmac
import json
from dataclasses import dataclass
from typing import Any, Mapping

from .presentation import CONTRACT_VERSION, validate_routing_token


AVATAR_TOKEN_ENV = "VOLMARR_AVATAR_TOKEN"
LISTENER_HOST = "127.0.0.1"
LISTENER_PATH = "/v1/presentation"
MAX_READY_BYTES = 512

_GENERIC_REFUSAL = "avatar presentation admission refused"
_PLACEHOLDERS = frozenset(
    {
        "changeme",
        "change-me",
        "replace-me",
        "your-token-here",
        "example",
        "password",
    }
)


class AvatarAdmissionError(ValueError):
    """Raised without echoing rejected credentials or payloads."""


class AvatarBearerToken:
    """A validated bearer whose representation never exposes its value."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        self._value = value

    def __repr__(self) -> str:
        return "AvatarBearerToken(<redacted>)"

    def authorizes(self, authorization: Any) -> bool:
        if not isinstance(authorization, str):
            return False
        scheme, separator, supplied = authorization.partition(" ")
        if separator != " " or scheme.casefold() != "bearer" or not supplied:
            return False
        if supplied.strip() != supplied or " " in supplied:
            return False
        return hmac.compare_digest(supplied, self._value)


@dataclass(frozen=True)
class ReadyRequest:
    contract: str
    session_id: str


def validate_listener_target(
    *, host: Any, port: Any, path: Any, origin: Any = None
) -> tuple[str, int, str]:
    """Validate the fixed loopback target before any socket creation."""

    if host != LISTENER_HOST:
        raise AvatarAdmissionError("avatar listener requires literal IPv4 loopback")
    if isinstance(port, bool) or not isinstance(port, int) or not 1024 <= port <= 65535:
        raise AvatarAdmissionError("avatar listener port must be an unprivileged TCP port")
    if path != LISTENER_PATH:
        raise AvatarAdmissionError("avatar listener path is not supported")
    if origin not in {None, ""}:
        raise AvatarAdmissionError("browser-origin avatar connections are not supported")
    return LISTENER_HOST, port, LISTENER_PATH


def load_avatar_token(environ: Mapping[str, str]) -> AvatarBearerToken:
    """Load and register the active profile's strong environment-only bearer."""

    value = environ.get(AVATAR_TOKEN_ENV)
    if not isinstance(value, str):
        raise AvatarAdmissionError(_GENERIC_REFUSAL)
    if not 32 <= len(value) <= 256:
        raise AvatarAdmissionError(_GENERIC_REFUSAL)
    if value.casefold() in _PLACEHOLDERS or any(not 33 <= ord(char) <= 126 for char in value):
        raise AvatarAdmissionError(_GENERIC_REFUSAL)

    from agent.redact import register_vault_redaction_value

    register_vault_redaction_value(value)
    return AvatarBearerToken(value)


def authorize_bearer(authorization: Any, token: AvatarBearerToken) -> None:
    """Fail closed with a credential-independent error."""

    if not isinstance(token, AvatarBearerToken) or not token.authorizes(authorization):
        raise AvatarAdmissionError(_GENERIC_REFUSAL)


def parse_ready_message(raw: Any) -> ReadyRequest:
    """Accept only the bounded presentation-only readiness envelope."""

    if isinstance(raw, bytes):
        if len(raw) > MAX_READY_BYTES:
            raise AvatarAdmissionError("avatar readiness message is too large")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AvatarAdmissionError("avatar readiness message must be UTF-8 JSON") from exc
    elif isinstance(raw, str):
        if len(raw.encode("utf-8")) > MAX_READY_BYTES:
            raise AvatarAdmissionError("avatar readiness message is too large")
        text = raw
    else:
        raise AvatarAdmissionError("avatar readiness message must be JSON text")
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise AvatarAdmissionError("avatar readiness message must be valid JSON") from exc
    if not isinstance(payload, dict) or set(payload) != {"type", "contract", "session_id"}:
        raise AvatarAdmissionError("avatar readiness message has unsupported fields")
    if payload["type"] != "ready" or payload["contract"] != CONTRACT_VERSION:
        raise AvatarAdmissionError("avatar readiness protocol is not supported")
    try:
        session_id = validate_routing_token(payload["session_id"], "session_id")
    except ValueError as exc:
        raise AvatarAdmissionError("avatar readiness session is invalid") from exc
    return ReadyRequest(contract=CONTRACT_VERSION, session_id=session_id)
