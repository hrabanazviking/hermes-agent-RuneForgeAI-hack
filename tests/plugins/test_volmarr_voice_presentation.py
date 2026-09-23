"""Contracts for the provider-free avatar presentation serializer."""

from __future__ import annotations

import base64
import hashlib
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
        audio.setframerate(8000)
        audio.writeframes(b"\x00\x00" * 80)
    return output.getvalue()


def test_real_discovery_serializes_complete_wav_and_explicit_controls():
    from hermes_cli.plugins import PluginManager

    _enable_plugin(get_hermes_home())
    manager = PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-voice"]
        presentation = importlib.import_module(f"{loaded.module.__name__}.presentation")
        source = _wav_bytes()
        event = presentation.build_presentation_event(
            kind="speech",
            session_id="avatar-session",
            transaction_id="turn-7",
            sequence=0,
            audio_data=source,
            face_name="joy",
            animation_name="wave_hands",
        )
    finally:
        manager.unload()

    assert event["contract"] == "runeforge.avatar.presentation.v1"
    assert event["kind"] == "speech"
    assert base64.b64decode(event["audio"]["data"], validate=True) == source
    assert event["audio"]["sha256"] == hashlib.sha256(source).hexdigest()
    assert event["audio"]["format"] == {
        "channels": 1,
        "sample_width": 2,
        "sample_rate": 8000,
        "frame_count": 80,
        "duration_seconds": 0.01,
    }
    assert event["expression"] == {
        "face_name": "joy",
        "face_duration_seconds": 4.0,
        "animation_name": "wave_hands",
        "animation_duration_seconds": 4.0,
    }
    assert "text" not in event and "path" not in event


def test_serializer_rejects_invalid_ownership_and_builds_control_events():
    from hermes_cli.plugins import PluginManager

    _enable_plugin(get_hermes_home())
    manager = PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-voice"]
        presentation = importlib.import_module(f"{loaded.module.__name__}.presentation")
        with pytest.raises(presentation.PresentationContractError):
            presentation.build_presentation_event(
                kind="speech",
                session_id="avatar-session",
                transaction_id="turn-7",
                sequence=0,
                audio_data=b"not-wave",
            )
        with pytest.raises(presentation.PresentationContractError):
            presentation.build_presentation_event(
                kind="stop",
                session_id="avatar-session",
                transaction_id="turn-7",
                sequence=1,
                audio_data=_wav_bytes(),
            )
        stop = presentation.build_presentation_event(
            kind="stop",
            session_id="avatar-session",
            transaction_id="turn-7",
            sequence=1,
        )
        final = presentation.build_presentation_event(
            kind="final",
            session_id="avatar-session",
            transaction_id="turn-7",
            sequence=2,
        )
    finally:
        manager.unload()

    assert stop == {
        "contract": "runeforge.avatar.presentation.v1",
        "kind": "stop",
        "session_id": "avatar-session",
        "transaction_id": "turn-7",
        "sequence": 1,
    }
    assert final["kind"] == "final"
    assert "audio" not in final and "expression" not in final
