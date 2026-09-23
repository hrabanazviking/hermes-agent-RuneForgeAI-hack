"""Explicit operator serve-action contracts."""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import queue
import socket
import sys
import threading

from hermes_constants import get_hermes_home


TOKEN = "cli-serve-token-0123456789-abcdef"


def _enable_plugin(home) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [volmarr-voice]\n",
        encoding="utf-8",
    )


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


class _QueueStream:
    def __init__(self) -> None:
        self.lines: queue.Queue[bytes] = queue.Queue()

    def readline(self, limit: int) -> bytes:
        return self.lines.get()[:limit]


class _Stdin:
    def __init__(self, stream: _QueueStream) -> None:
        self.buffer = stream


def _command(manager, argv):
    command = manager._cli_commands["volmarr-voice"]
    parser = argparse.ArgumentParser(prog="hermes volmarr-voice")
    command["setup_fn"](parser)
    return command["handler_fn"], parser.parse_args(argv)


def test_serve_refuses_missing_token_before_socket_creation(monkeypatch, capsys):
    from hermes_cli.plugins import PluginManager

    _enable_plugin(get_hermes_home())
    manager = PluginManager()
    manager.discover_and_load()
    try:
        handler, args = _command(manager, ["serve", "--port", "8765"])
        monkeypatch.delenv("VOLMARR_AVATAR_TOKEN", raising=False)

        def forbidden_socket(*_args, **_kwargs):
            raise AssertionError("missing token must fail before socket creation")

        monkeypatch.setattr(socket, "socket", forbidden_socket)
        assert handler(args) == 1
        captured = capsys.readouterr()
    finally:
        manager.unload()

    assert captured.out == ""
    assert captured.err == "Avatar presentation feed failed\n"


def test_serve_delivers_one_stdin_event_and_stops_on_eof(monkeypatch, capsys):
    from agent.redact import clear_vault_redaction_values
    from hermes_cli.plugins import PluginManager
    from websockets.asyncio.client import connect

    home = get_hermes_home()
    _enable_plugin(home)
    manager = PluginManager()
    manager.discover_and_load()
    port = _free_port()
    stream = _QueueStream()
    monkeypatch.setenv("VOLMARR_AVATAR_TOKEN", TOKEN)
    monkeypatch.setattr(sys, "stdin", _Stdin(stream))
    try:
        loaded = manager._plugins["volmarr-voice"]
        presentation = importlib.import_module(f"{loaded.module.__name__}.presentation")
        handler, args = _command(manager, ["serve", "--port", str(port)])
        result = []
        worker = threading.Thread(target=lambda: result.append(handler(args)), daemon=True)
        worker.start()

        async def consume():
            uri = f"ws://127.0.0.1:{port}/v1/presentation"
            headers = {"Authorization": f"Bearer {TOKEN}"}
            last_error = None
            for _ in range(50):
                try:
                    consumer = await connect(uri, additional_headers=headers, proxy=None)
                    break
                except OSError as exc:
                    last_error = exc
                    await asyncio.sleep(0.02)
            else:
                raise AssertionError("operator feed did not start") from last_error
            async with consumer:
                await consumer.send(
                    json.dumps(
                        {
                            "type": "ready",
                            "contract": "runeforge.avatar.presentation.v1",
                            "session_id": "avatar-session",
                        }
                    )
                )
                assert json.loads(await consumer.recv())["type"] == "connected"
                event = presentation.build_presentation_event(
                    kind="speech",
                    session_id="avatar-session",
                    transaction_id="turn-cli",
                    sequence=0,
                    audio_data=_wave_bytes(),
                )
                stream.lines.put((json.dumps(event) + "\n").encode("utf-8"))
                delivered = json.loads(await consumer.recv())
                stream.lines.put(b"")
                return delivered

        delivered = asyncio.run(consume())
        worker.join(timeout=5)
        assert not worker.is_alive()
        captured = capsys.readouterr()
    finally:
        stream.lines.put(b"")
        clear_vault_redaction_values()
        manager.unload()

    assert result == [0]
    assert delivered["type"] == "chunk"
    assert captured.out == ""
    assert captured.err == "Avatar presentation feed stopped after 1 event(s)\n"
    assert TOKEN not in captured.err
    assert delivered["audio_data"] not in captured.err


def _wave_bytes() -> bytes:
    import io
    import wave

    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b"\x00\x00" * 80)
    return output.getvalue()
