"""Operator WAV-to-event encoder contracts."""

from __future__ import annotations

import argparse
import base64
import importlib
import io
import json
import socket
import wave

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


def _command(manager, argv):
    command = manager._cli_commands["volmarr-voice"]
    parser = argparse.ArgumentParser(prog="hermes volmarr-voice")
    command["setup_fn"](parser)
    return command["handler_fn"], parser.parse_args(argv)


def test_encode_emits_one_canonical_path_free_event_without_socket(tmp_path, monkeypatch, capsys):
    from hermes_cli.plugins import PluginManager

    home = get_hermes_home()
    _enable_plugin(home)
    source = tmp_path / "spoken.wav"
    source.write_bytes(_wav_bytes())
    manager = PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-voice"]
        presentation = importlib.import_module(f"{loaded.module.__name__}.presentation")
        handler, args = _command(
            manager,
            [
                "encode",
                "--audio",
                str(source),
                "--session",
                "avatar-session",
                "--transaction",
                "turn-encode",
                "--face",
                "joy",
            ],
        )

        def forbidden_socket(*_args, **_kwargs):
            raise AssertionError("encode must not create a socket")

        monkeypatch.setattr(socket, "socket", forbidden_socket)
        assert handler(args) == 0
        captured = capsys.readouterr()
        event = json.loads(captured.out)
        assert presentation.validate_presentation_event(event) == event
    finally:
        manager.unload()

    assert captured.err == ""
    assert base64.b64decode(event["audio"]["data"], validate=True) == _wav_bytes()
    assert event["expression"]["face_name"] == "joy"
    assert str(source) not in captured.out
    assert "path" not in event and "text" not in event


def test_encode_rejects_invalid_audio_without_echoing_path_or_content(tmp_path, capsys):
    from hermes_cli.plugins import PluginManager

    home = get_hermes_home()
    _enable_plugin(home)
    source = tmp_path / "secret-name.wav"
    source.write_bytes(b"private-invalid-audio-content")
    manager = PluginManager()
    manager.discover_and_load()
    try:
        handler, args = _command(
            manager,
            [
                "encode",
                "--audio",
                str(source),
                "--session",
                "avatar-session",
                "--transaction",
                "turn-invalid",
            ],
        )
        assert handler(args) == 1
        captured = capsys.readouterr()
    finally:
        manager.unload()

    assert captured.out == ""
    assert captured.err == "Avatar presentation event encoding failed\n"
    assert str(source) not in captured.err
    assert "private-invalid-audio-content" not in captured.err
