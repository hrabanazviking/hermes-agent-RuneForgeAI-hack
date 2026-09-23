"""Pure v1 translation into AIAvatarKit's presentation-side response shape."""

from __future__ import annotations

from typing import Any

from .presentation import validate_presentation_event


_RESPONSE_TYPE = {
    "speech": "chunk",
    "stop": "stop",
    "final": "final",
}


def to_aiavatarkit_response(event: dict[str, Any]) -> dict[str, Any]:
    """Translate one canonical event without invoking an AIAvatarKit pipeline."""

    canonical = validate_presentation_event(event)
    response: dict[str, Any] = {
        "type": _RESPONSE_TYPE[canonical["kind"]],
        "session_id": canonical["session_id"],
        "metadata": {
            "runeforge_contract": canonical["contract"],
            "transaction_id": canonical["transaction_id"],
            "sequence": canonical["sequence"],
        },
    }
    if canonical["kind"] != "speech":
        return response

    audio = canonical["audio"]
    response["audio_data"] = audio["data"]
    response["metadata"]["audio_sha256"] = audio["sha256"]
    expression = canonical.get("expression")
    if expression:
        control: dict[str, Any] = {}
        if "face_name" in expression:
            control["face_name"] = expression["face_name"]
            control["face_duration"] = expression["face_duration_seconds"]
        if "animation_name" in expression:
            control["animation_name"] = expression["animation_name"]
            control["animation_duration"] = expression[
                "animation_duration_seconds"
            ]
        response["avatar_control_request"] = control
    return response
