"""Disposable real-loopback presentation feed contracts."""

from __future__ import annotations

import asyncio
import base64
import importlib
import io
import json
import socket
import wave

import pytest

from hermes_constants import get_hermes_home


TOKEN = "avatar-test-token-0123456789-abcdef"


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


def _ready(session_id="avatar-session") -> str:
    return json.dumps(
        {
            "type": "ready",
            "contract": "runeforge.avatar.presentation.v1",
            "session_id": session_id,
        }
    )


def test_real_loopback_delivers_complete_wav_then_tears_down():
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
        port = _free_port()

        async def exercise():
            feed = loopback.AvatarLoopbackFeed(
                host="127.0.0.1",
                port=port,
                path="/v1/presentation",
                environ={"VOLMARR_AVATAR_TOKEN": TOKEN},
            )
            await feed.start()
            try:
                async with connect(
                    f"ws://127.0.0.1:{port}/v1/presentation",
                    additional_headers={"Authorization": f"Bearer {TOKEN}"},
                    proxy=None,
                ) as consumer:
                    await consumer.send(_ready())
                    connected = json.loads(await consumer.recv())
                    speech = presentation.build_presentation_event(
                        kind="speech",
                        session_id="avatar-session",
                        transaction_id="turn-live",
                        sequence=0,
                        audio_data=_wav_bytes(),
                        face_name="joy",
                    )
                    assert await feed.publish(speech) == 1
                    chunk = json.loads(await consumer.recv())
                    final = presentation.build_presentation_event(
                        kind="final",
                        session_id="avatar-session",
                        transaction_id="turn-live",
                        sequence=1,
                    )
                    assert await feed.publish(final) == 1
                    completed = json.loads(await consumer.recv())
                    return connected, chunk, completed
            finally:
                await feed.stop()

        connected, chunk, completed = asyncio.run(exercise())
    finally:
        clear_vault_redaction_values()
        manager.unload()

    assert connected["type"] == "connected"
    assert chunk["type"] == "chunk"
    assert base64.b64decode(chunk["audio_data"], validate=True) == _wav_bytes()
    assert chunk["avatar_control_request"]["face_name"] == "joy"
    assert completed["type"] == "final"


def test_real_loopback_refuses_bad_auth_duplicate_owner_and_client_input():
    from agent.redact import clear_vault_redaction_values
    from hermes_cli.plugins import PluginManager
    from websockets.asyncio.client import connect
    from websockets.exceptions import ConnectionClosedError

    home = get_hermes_home()
    _enable_plugin(home)
    manager = PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-voice"]
        loopback = importlib.import_module(f"{loaded.module.__name__}.loopback")
        port = _free_port()

        async def exercise():
            feed = loopback.AvatarLoopbackFeed(
                host="127.0.0.1",
                port=port,
                path="/v1/presentation",
                environ={"VOLMARR_AVATAR_TOKEN": TOKEN},
            )
            await feed.start()
            uri = f"ws://127.0.0.1:{port}/v1/presentation"
            try:
                async with connect(
                    uri,
                    additional_headers={"Authorization": "Bearer wrong"},
                    proxy=None,
                ) as rejected:
                    with pytest.raises(ConnectionClosedError) as auth_closed:
                        await rejected.send(_ready())
                        await rejected.recv()
                    assert auth_closed.value.rcvd.code == 1008

                headers = {"Authorization": f"Bearer {TOKEN}"}
                async with connect(uri, additional_headers=headers, proxy=None) as owner:
                    await owner.send(_ready())
                    assert json.loads(await owner.recv())["type"] == "connected"
                    async with connect(uri, additional_headers=headers, proxy=None) as duplicate:
                        with pytest.raises(ConnectionClosedError) as duplicate_closed:
                            await duplicate.send(_ready())
                            await duplicate.recv()
                        assert duplicate_closed.value.rcvd.code == 1008
                    await owner.send(json.dumps({"type": "invoke", "text": "forbidden"}))
                    with pytest.raises(ConnectionClosedError) as input_closed:
                        await owner.recv()
                    assert input_closed.value.rcvd.code == 1003
            finally:
                await feed.stop()

        asyncio.run(exercise())
    finally:
        clear_vault_redaction_values()
        manager.unload()
