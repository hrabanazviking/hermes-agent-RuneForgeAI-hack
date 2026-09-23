"""Bounded operator stdin runner contracts."""

from __future__ import annotations

import asyncio
import importlib
import io
import json
import queue
import socket
import wave

import pytest

from hermes_constants import get_hermes_home


TOKEN = "runner-test-token-0123456789-abcdef"


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


def _wav_bytes() -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b"\x00\x00" * 80)
    return output.getvalue()


class _QueueStream:
    def __init__(self) -> None:
        self.lines: queue.Queue[bytes] = queue.Queue()

    def readline(self, limit: int) -> bytes:
        return self.lines.get()[:limit]


def test_real_loopback_runner_delivers_canonical_stdin_event_then_eof():
    from agent.redact import clear_vault_redaction_values
    from hermes_cli.plugins import PluginManager
    from websockets.asyncio.client import connect

    home = get_hermes_home()
    _enable_plugin(home)
    manager = PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-voice"]
        presentation = importlib.import_module(f"{loaded.module.__name__}.presentation")
        loopback = importlib.import_module(f"{loaded.module.__name__}.loopback")
        runner = importlib.import_module(f"{loaded.module.__name__}.runner")
        port = _free_port()

        async def exercise():
            feed = loopback.AvatarLoopbackFeed(
                host="127.0.0.1",
                port=port,
                path="/v1/presentation",
                environ={"VOLMARR_AVATAR_TOKEN": TOKEN},
            )
            stream = _QueueStream()
            run_task = asyncio.create_task(runner.run_feed_from_stream(feed, stream))
            await asyncio.sleep(0)
            uri = f"ws://127.0.0.1:{port}/v1/presentation"
            headers = {"Authorization": f"Bearer {TOKEN}"}
            async with connect(uri, additional_headers=headers, proxy=None) as consumer:
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
                    transaction_id="turn-stdin",
                    sequence=0,
                    audio_data=_wav_bytes(),
                )
                stream.lines.put((json.dumps(event) + "\n").encode("utf-8"))
                delivered = json.loads(await consumer.recv())
                stream.lines.put(b"")
                assert await run_task == 1
                return delivered

        delivered = asyncio.run(exercise())
    finally:
        clear_vault_redaction_values()
        manager.unload()

    assert delivered["type"] == "chunk"
    assert delivered["metadata"]["transaction_id"] == "turn-stdin"


def test_runner_refuses_bad_lines_and_always_stops(monkeypatch):
    from hermes_cli.plugins import PluginManager

    home = get_hermes_home()
    _enable_plugin(home)
    manager = PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-voice"]
        runner = importlib.import_module(f"{loaded.module.__name__}.runner")

        class FakeFeed:
            def __init__(self):
                self.started = 0
                self.stopped = 0
                self.published = 0

            async def start(self):
                self.started += 1

            async def publish(self, _event):
                self.published += 1

            async def stop(self):
                self.stopped += 1

        invalid = FakeFeed()
        with pytest.raises(runner.AvatarRunnerError) as malformed:
            asyncio.run(runner.run_feed_from_stream(invalid, io.BytesIO(b"not-json\n")))
        assert str(malformed.value) == "avatar event line was refused"
        assert (invalid.started, invalid.stopped, invalid.published) == (1, 1, 0)

        monkeypatch.setattr(runner, "MAX_EVENT_LINE_BYTES", 16)
        oversized = FakeFeed()
        with pytest.raises(runner.AvatarRunnerError) as too_large:
            asyncio.run(
                runner.run_feed_from_stream(oversized, io.BytesIO(b"x" * 17 + b"\n"))
            )
        assert str(too_large.value) == "avatar event line exceeds the maximum size"
        assert (oversized.started, oversized.stopped, oversized.published) == (1, 1, 0)
    finally:
        manager.unload()
