"""Provider-free serialization for the avatar presentation v1 contract."""

from __future__ import annotations

import base64
import hashlib
import io
import math
import re
import wave
from typing import Any


CONTRACT_VERSION = "runeforge.avatar.presentation.v1"
MAX_WAV_BYTES = 16 * 1024 * 1024
MAX_AUDIO_SECONDS = 120.0

_ROUTING_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_CONTROL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


class PresentationContractError(ValueError):
    """Raised when an event cannot satisfy the presentation contract."""


def _routing_token(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _ROUTING_TOKEN.fullmatch(value):
        raise PresentationContractError(f"{field} must be a bounded opaque routing token")
    return value


def validate_routing_token(value: Any, field: str = "routing_token") -> str:
    """Validate one public session/transaction routing token."""

    return _routing_token(value, field)


def _sequence(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 2**31 - 1:
        raise PresentationContractError("sequence must be an integer from 0 through 2147483647")
    return value


def _control_name(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _CONTROL_NAME.fullmatch(value):
        raise PresentationContractError(f"{field} must be a bounded shell-owned control name")
    return value


def _duration(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PresentationContractError(f"{field} must be a finite duration")
    duration = float(value)
    if not math.isfinite(duration) or not 0.0 < duration <= 60.0:
        raise PresentationContractError(f"{field} must be greater than 0 and at most 60 seconds")
    return duration


def _validated_wav(audio_data: Any) -> tuple[bytes, dict[str, int | float]]:
    if not isinstance(audio_data, bytes):
        raise PresentationContractError("speech audio must be bytes")
    if not audio_data or len(audio_data) > MAX_WAV_BYTES:
        raise PresentationContractError("speech audio must be a non-empty WAV within 16 MiB")
    try:
        with wave.open(io.BytesIO(audio_data), "rb") as source:
            channels = source.getnchannels()
            sample_width = source.getsampwidth()
            sample_rate = source.getframerate()
            frame_count = source.getnframes()
            compression = source.getcomptype()
    except (EOFError, wave.Error) as exc:
        raise PresentationContractError("speech audio must be a valid WAV container") from exc

    if compression != "NONE":
        raise PresentationContractError("speech audio must use uncompressed PCM")
    if channels not in {1, 2} or sample_width not in {1, 2, 3, 4}:
        raise PresentationContractError("speech audio has unsupported PCM channels or sample width")
    if not 8000 <= sample_rate <= 48000 or frame_count <= 0:
        raise PresentationContractError("speech audio has unsupported rate or no frames")
    duration = frame_count / sample_rate
    if duration > MAX_AUDIO_SECONDS:
        raise PresentationContractError("speech audio exceeds the 120 second event bound")
    return audio_data, {
        "channels": channels,
        "sample_width": sample_width,
        "sample_rate": sample_rate,
        "frame_count": frame_count,
        "duration_seconds": duration,
    }


def build_presentation_event(
    *,
    kind: str,
    session_id: str,
    transaction_id: str,
    sequence: int,
    audio_data: bytes | None = None,
    face_name: str | None = None,
    face_duration_seconds: float = 4.0,
    animation_name: str | None = None,
    animation_duration_seconds: float = 4.0,
) -> dict[str, Any]:
    """Build one strict, transport-neutral avatar presentation event."""

    if kind not in {"speech", "stop", "final"}:
        raise PresentationContractError("kind must be speech, stop, or final")
    event: dict[str, Any] = {
        "contract": CONTRACT_VERSION,
        "kind": kind,
        "session_id": _routing_token(session_id, "session_id"),
        "transaction_id": _routing_token(transaction_id, "transaction_id"),
        "sequence": _sequence(sequence),
    }

    face = _control_name(face_name, "face_name")
    animation = _control_name(animation_name, "animation_name")
    if kind != "speech":
        if audio_data is not None or face is not None or animation is not None:
            raise PresentationContractError(
                "stop and final events cannot carry audio or expression"
            )
        return event
    if audio_data is None:
        raise PresentationContractError("speech events require audio")

    wav_data, wav_format = _validated_wav(audio_data)
    event["audio"] = {
        "encoding": "base64",
        "container": "wav",
        "data": base64.b64encode(wav_data).decode("ascii"),
        "sha256": hashlib.sha256(wav_data).hexdigest(),
        "format": wav_format,
    }
    expression: dict[str, Any] = {}
    if face is not None:
        expression["face_name"] = face
        expression["face_duration_seconds"] = _duration(
            face_duration_seconds, "face_duration_seconds"
        )
    if animation is not None:
        expression["animation_name"] = animation
        expression["animation_duration_seconds"] = _duration(
            animation_duration_seconds, "animation_duration_seconds"
        )
    if expression:
        event["expression"] = expression
    return event


def validate_presentation_event(event: Any) -> dict[str, Any]:
    """Return an exact canonical event or reject altered/unknown wire fields."""

    if not isinstance(event, dict):
        raise PresentationContractError("presentation event must be an object")
    try:
        kind = event["kind"]
        audio = event.get("audio")
        expression = event.get("expression") or {}
        if audio is not None:
            if not isinstance(audio, dict):
                raise PresentationContractError("audio must be an object")
            if audio.get("encoding") != "base64" or audio.get("container") != "wav":
                raise PresentationContractError("audio encoding must be base64 WAV")
            encoded = audio.get("data")
            if not isinstance(encoded, str):
                raise PresentationContractError("audio data must be base64 text")
            try:
                audio_data = base64.b64decode(encoded, validate=True)
            except (ValueError, TypeError) as exc:
                raise PresentationContractError("audio data is not valid base64") from exc
        else:
            audio_data = None
        if not isinstance(expression, dict):
            raise PresentationContractError("expression must be an object")
        rebuilt = build_presentation_event(
            kind=kind,
            session_id=event["session_id"],
            transaction_id=event["transaction_id"],
            sequence=event["sequence"],
            audio_data=audio_data,
            face_name=expression.get("face_name"),
            face_duration_seconds=expression.get("face_duration_seconds", 4.0),
            animation_name=expression.get("animation_name"),
            animation_duration_seconds=expression.get(
                "animation_duration_seconds", 4.0
            ),
        )
    except KeyError as exc:
        raise PresentationContractError("presentation event is missing a required field") from exc
    if rebuilt != event:
        raise PresentationContractError("presentation event is not canonical or was altered")
    return rebuilt
