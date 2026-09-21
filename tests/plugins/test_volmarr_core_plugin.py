"""Contracts for the first Volmarr runtime slice: Hermes lifecycle → Verðandi."""

from __future__ import annotations

import argparse
import json
import socket

from hermes_constants import get_hermes_home


class _SocketRecorder:
    def __init__(
        self,
        calls: list[dict],
        *,
        failure: Exception | None = None,
        response: bytes = b'{"nerve_type":"pong","seq":0}\n',
    ) -> None:
        self._calls = calls
        self._failure = failure
        self._response = response
        self._call: dict = {}
        calls.append(self._call)

    def __enter__(self):
        return self

    def __exit__(self, *_exc) -> None:
        return None

    def settimeout(self, timeout: float) -> None:
        self._call["timeout"] = timeout

    def connect(self, path: str) -> None:
        self._call["path"] = path
        if self._failure is not None:
            raise self._failure

    def sendall(self, payload: bytes) -> None:
        self._call["payload"] = payload

    def recv(self, _size: int) -> bytes:
        return self._response


def _load_plugin(home, monkeypatch, socket_factory, *, socket_path="state/test-runa.sock"):
    from hermes_cli import plugins as plugins_mod

    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        f"        socket_path: {socket_path}\n"
        "        timeout_ms: 25\n"
        "        source: hermes-test\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(socket, "AF_UNIX", object(), raising=False)
    monkeypatch.setattr(socket, "socket", socket_factory)
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    return manager


def test_real_discovery_publishes_versioned_metadata_without_sensitive_content(
    monkeypatch,
):
    hermes_home = get_hermes_home()
    calls: list[dict] = []
    manager = _load_plugin(
        hermes_home,
        monkeypatch,
        lambda *_args: _SocketRecorder(calls),
    )
    try:
        loaded = manager._plugins["volmarr-core"]
        assert loaded.enabled
        assert set(loaded.hooks_registered) == {
            "on_session_start",
            "on_session_end",
            "on_session_finalize",
            "pre_tool_call",
            "post_tool_call",
        }

        manager.invoke_hook(
            "on_session_start", session_id="session-1", model="local-model", platform="cli"
        )
        manager.invoke_hook(
            "pre_tool_call",
            tool_name="terminal",
            args={"command": "echo rune-secret"},
            session_id="session-1",
            task_id="task-1",
            turn_id="turn-1",
            tool_call_id="call-1",
        )
        manager.invoke_hook(
            "post_tool_call",
            tool_name="terminal",
            args={"command": "echo rune-secret"},
            result="rune-secret",
            error_message="rune-secret",
            error_type="ToolError",
            status="error",
            duration_ms=42,
            session_id="session-1",
            task_id="task-1",
            turn_id="turn-1",
            tool_call_id="call-1",
        )
        manager.invoke_hook(
            "post_tool_call",
            tool_name="terminal",
            result="safe metadata test",
            status="ok",
            duration_ms=7,
            session_id="session-1",
            task_id="task-1",
            turn_id="turn-1",
            tool_call_id="call-2",
        )
        manager.invoke_hook(
            "on_session_end",
            session_id="session-1",
            task_id="task-1",
            turn_id="turn-1",
            completed=False,
            failed=True,
            interrupted=False,
            turn_exit_reason="provider_error",
            model="local-model",
            platform="cli",
        )
        manager.invoke_hook(
            "on_session_end",
            session_id="session-1",
            task_id="task-2",
            turn_id="turn-2",
            completed=True,
            turn_exit_reason="text_response(stop)",
        )
        manager.invoke_hook(
            "on_session_end",
            session_id="session-1",
            task_id="task-3",
            turn_id="turn-3",
            interrupted=True,
            turn_exit_reason="user_interrupt",
        )
        manager.invoke_hook("on_session_finalize", session_id="session-1")

        messages = [json.loads(call["payload"].decode()) for call in calls]
        assert [message["type"] for message in messages] == [
            "hermes.session.started",
            "hermes.tool.started",
            "hermes.tool.failed",
            "hermes.tool.completed",
            "hermes.turn.failed",
            "hermes.turn.completed",
            "hermes.turn.interrupted",
            "hermes.session.ended",
        ]
        assert all(message["data"]["schema"] == "runeforge.hermes.lifecycle" for message in messages)
        assert all(message["data"]["schema_version"] == 1 for message in messages)
        assert all(message["source"] == "hermes-test" for message in messages)
        assert all(call["timeout"] == 0.025 for call in calls)
        assert all(call["path"] == str(hermes_home / "state" / "test-runa.sock") for call in calls)
        serialized = "\n".join(json.dumps(message) for message in messages)
        assert "rune-secret" not in serialized
        assert '"args"' not in serialized
        assert '"result"' not in serialized
        assert '"error_message"' not in serialized
    finally:
        manager.unload()


def test_transport_failure_is_fail_open_for_the_pre_tool_policy_hook(monkeypatch):
    hermes_home = get_hermes_home()
    calls: list[dict] = []
    manager = _load_plugin(
        hermes_home,
        monkeypatch,
        lambda *_args: _SocketRecorder(calls, failure=FileNotFoundError("hub offline")),
    )
    try:
        results = manager.invoke_hook(
            "pre_tool_call",
            tool_name="terminal",
            args={"command": "echo safe"},
            session_id="session-1",
            tool_call_id="call-1",
        )

        assert results == []
        assert len(calls) == 1
        assert "payload" not in calls[0]
    finally:
        manager.unload()


def test_missing_unix_socket_support_is_fail_open(monkeypatch, capsys):
    hermes_home = get_hermes_home()
    calls: list[dict] = []
    manager = _load_plugin(
        hermes_home,
        monkeypatch,
        lambda *_args: _SocketRecorder(calls),
    )
    monkeypatch.delattr(socket, "AF_UNIX")
    try:
        results = manager.invoke_hook(
            "pre_tool_call",
            tool_name="terminal",
            session_id="session-1",
            tool_call_id="call-1",
        )

        assert results == []
        assert calls == []

        command = manager._cli_commands["volmarr"]
        parser = argparse.ArgumentParser()
        command["setup_fn"](parser)
        args = parser.parse_args(["health", "--json"])
        assert command["handler_fn"](args) == 1
        assert json.loads(capsys.readouterr().out)["status"] == "unsupported"
    finally:
        manager.unload()


def test_relative_socket_path_cannot_escape_the_active_profile(monkeypatch):
    hermes_home = get_hermes_home()
    calls: list[dict] = []
    manager = _load_plugin(
        hermes_home,
        monkeypatch,
        lambda *_args: _SocketRecorder(calls),
        socket_path="../outside.sock",
    )
    try:
        manager.invoke_hook("on_session_start", session_id="session-1")

        assert len(calls) == 1
        assert calls[0]["path"] == str(hermes_home / "state" / "runa.sock")
    finally:
        manager.unload()


def test_registered_health_cli_requires_a_valid_verdandi_pong(monkeypatch, capsys):
    hermes_home = get_hermes_home()
    calls: list[dict] = []
    response = (
        b'{"nerve_type":"pong","seq":41,"uptime_s":12.5,"subscribers":3}\n'
    )
    manager = _load_plugin(
        hermes_home,
        monkeypatch,
        lambda *_args: _SocketRecorder(calls, response=response),
    )
    try:
        command = manager._cli_commands["volmarr"]
        parser = argparse.ArgumentParser()
        command["setup_fn"](parser)
        args = parser.parse_args(["health", "--json"])

        exit_code = command["handler_fn"](args)
        report = json.loads(capsys.readouterr().out)

        assert exit_code == 0
        assert report == {
            "error_type": None,
            "healthy": True,
            "latency_ms": report["latency_ms"],
            "sequence": 41,
            "socket_path": str(hermes_home / "state" / "test-runa.sock"),
            "status": "healthy",
            "subscribers": 3,
            "uptime_seconds": 12.5,
        }
        assert calls[0]["payload"] == b'{"nerve_type":"ping"}\n'
    finally:
        manager.unload()


def test_health_cli_rejects_a_non_pong_response(monkeypatch, capsys):
    hermes_home = get_hermes_home()
    calls: list[dict] = []
    manager = _load_plugin(
        hermes_home,
        monkeypatch,
        lambda *_args: _SocketRecorder(
            calls,
            response=b'{"nerve_type":"subscribed"}\n',
        ),
    )
    try:
        command = manager._cli_commands["volmarr"]
        parser = argparse.ArgumentParser()
        command["setup_fn"](parser)
        args = parser.parse_args(["health", "--json"])

        exit_code = command["handler_fn"](args)
        report = json.loads(capsys.readouterr().out)

        assert exit_code == 1
        assert report["healthy"] is False
        assert report["status"] == "protocol_error"
    finally:
        manager.unload()
