"""AIAvatarKit presentation-response translation contracts."""

from __future__ import annotations

import base64
import importlib
import io
import wave

import pytest

from hermes_constants import get_hermes_home


def _enable_plugin(home) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [volmarr-voice]\n",
        encoding="utf-8",
    )


def _wav_bytes() -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\x00\x00" * 160)
    return output.getvalue()


def _consume_like_aiavatarkit(response):
    assert set(response) <= {
        "type",
        "session_id",
        "metadata",
        "audio_data",
        "avatar_control_request",
    }
    consumed = {"type": response["type"], "session_id": response["session_id"]}
    if response["type"] == "chunk":
        audio_data = base64.b64decode(response["audio_data"], validate=True)
        with wave.open(io.BytesIO(audio_data), "rb") as audio:
            consumed["frames"] = audio.getnframes()
        consumed["controls"] = response.get("avatar_control_request")
    return consumed


def test_real_discovery_translates_speech_for_presentation_only_consumer():
    from hermes_cli.plugins import PluginManager

    _enable_plugin(get_hermes_home())
    manager = PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-voice"]
        presentation = importlib.import_module(f"{loaded.module.__name__}.presentation")
        adapter = importlib.import_module(f"{loaded.module.__name__}.aiavatarkit")
        event = presentation.build_presentation_event(
            kind="speech",
            session_id="avatar-session",
            transaction_id="turn-8",
            sequence=0,
            audio_data=_wav_bytes(),
            face_name="joy",
            animation_name="wave_hands",
        )
        response = adapter.to_aiavatarkit_response(event)
        consumed = _consume_like_aiavatarkit(response)
    finally:
        manager.unload()

    assert consumed == {
        "type": "chunk",
        "session_id": "avatar-session",
        "frames": 160,
        "controls": {
            "face_name": "joy",
            "face_duration": 4.0,
            "animation_name": "wave_hands",
            "animation_duration": 4.0,
        },
    }
    assert set(response["metadata"]) == {
        "runeforge_contract",
        "transaction_id",
        "sequence",
        "audio_sha256",
    }
    assert "text" not in response and "voice_text" not in response


def test_translation_maps_control_events_and_refuses_tampering():
    from hermes_cli.plugins import PluginManager

    _enable_plugin(get_hermes_home())
    manager = PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-voice"]
        presentation = importlib.import_module(f"{loaded.module.__name__}.presentation")
        adapter = importlib.import_module(f"{loaded.module.__name__}.aiavatarkit")
        stop_event = presentation.build_presentation_event(
            kind="stop",
            session_id="avatar-session",
            transaction_id="turn-8",
            sequence=1,
        )
        final_event = presentation.build_presentation_event(
            kind="final",
            session_id="avatar-session",
            transaction_id="turn-8",
            sequence=2,
        )
        stop = adapter.to_aiavatarkit_response(stop_event)
        final = adapter.to_aiavatarkit_response(final_event)
        altered = dict(stop_event, text="unexpected second-mind input")
        with pytest.raises(presentation.PresentationContractError):
            adapter.to_aiavatarkit_response(altered)
    finally:
        manager.unload()

    assert _consume_like_aiavatarkit(stop)["type"] == "stop"
    assert _consume_like_aiavatarkit(final)["type"] == "final"
    assert "audio_data" not in stop and "avatar_control_request" not in stop
    assert "audio_data" not in final and "avatar_control_request" not in final
