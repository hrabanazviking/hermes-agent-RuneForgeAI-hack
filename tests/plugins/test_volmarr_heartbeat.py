"""Contracts for deterministic entity continuity pulses."""

from __future__ import annotations

import argparse
import json
import socket
import sys
from datetime import datetime, timedelta, timezone

import yaml

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)


class _SocketRecorder:
    def __init__(self, calls: list[dict], *_args) -> None:
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

    def sendall(self, payload: bytes) -> None:
        self._call["payload"] = json.loads(payload)


def _write_profile(home, *, stale_after: int = 900) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        f"        heartbeat_stale_after_seconds: {stale_after}\n",
        encoding="utf-8",
    )


def _load_manager():
    from hermes_cli import plugins as plugins_mod

    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    return manager


def _dispatch(manager) -> dict:
    from tools.registry import registry

    return json.loads(
        registry.dispatch("entity_heartbeat", {}, scope=manager.scope_key)
    )


def _command(manager, argv: list[str]):
    command = manager._cli_commands["volmarr"]
    parser = argparse.ArgumentParser()
    command["setup_fn"](parser)
    args = parser.parse_args(argv)
    return command["handler_fn"], args


def test_lifecycle_creates_idle_continuity_without_claiming_a_pulse():
    home = get_hermes_home()
    _write_profile(home)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
        state = json.loads(
            (home / "entity" / "continuity.json").read_text(encoding="utf-8")
        )
        identity = yaml.safe_load(
            (home / "entity" / "entity.yaml").read_text(encoding="utf-8")
        )
    finally:
        manager.unload()

    assert state == {
        "continuity_version": 1,
        "owner_entity_id": identity["entity_id"],
        "heartbeat_sequence": 0,
        "last_heartbeat_at": "",
        "last_source": "",
    }


def test_tool_pulse_persists_and_emits_content_free_verdandi_event(monkeypatch):
    home = get_hermes_home()
    _write_profile(home)
    calls: list[dict] = []
    monkeypatch.setattr(socket, "AF_UNIX", object(), raising=False)
    monkeypatch.setattr(socket, "socket", lambda *_args: _SocketRecorder(calls))
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="sensitive-session")
        calls.clear()
        report = _dispatch(manager)
    finally:
        manager.unload()

    state = json.loads(
        (home / "entity" / "continuity.json").read_text(encoding="utf-8")
    )
    event = calls[0]["payload"]
    assert report["healthy"] is True
    assert report["sequence"] == 1
    assert state["heartbeat_sequence"] == 1
    assert event["type"] == "hermes.entity.heartbeat"
    assert event["data"]["schema"] == "runeforge.entity.heartbeat"
    assert event["data"]["context"] == {
        "heartbeat_sequence": 1,
        "source": "tool",
        "resumed": False,
    }
    assert "sensitive-session" not in json.dumps(event)
    assert state["owner_entity_id"] not in json.dumps(event)


def test_cli_reports_idle_then_pulses_without_starting_a_scheduler(capsys):
    home = get_hermes_home()
    _write_profile(home)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
        handler, idle_args = _command(manager, ["heartbeat", "status", "--json"])
        assert handler(idle_args) == 1
        idle = json.loads(capsys.readouterr().out)
        handler, pulse_args = _command(
            manager,
            ["heartbeat", "pulse", "--source", "cron", "--json"],
        )
        assert handler(pulse_args) == 0
        pulse = json.loads(capsys.readouterr().out)
        handler, status_args = _command(manager, ["heartbeat", "status", "--json"])
        assert handler(status_args) == 0
        status = json.loads(capsys.readouterr().out)
    finally:
        manager.unload()

    assert idle["status"] == "idle"
    assert pulse["last_source"] == "cron"
    assert status["status"] == "healthy"
    assert status["sequence"] == 1


def test_stale_gap_is_reported_and_next_pulse_emits_resumed(monkeypatch, capsys):
    home = get_hermes_home()
    _write_profile(home, stale_after=60)
    calls: list[dict] = []
    monkeypatch.setattr(socket, "AF_UNIX", object(), raising=False)
    monkeypatch.setattr(socket, "socket", lambda *_args: _SocketRecorder(calls))
    first = datetime(2026, 9, 21, tzinfo=timezone.utc)
    current = first
    manager = _load_manager()
    try:
        package = manager._plugins["volmarr-core"].module.__package__
        heartbeat_mod = sys.modules[f"{package}.heartbeat"]
        monkeypatch.setattr(heartbeat_mod, "_utc_now", lambda: current)
        manager.invoke_hook("on_session_start", session_id="one")
        calls.clear()
        _dispatch(manager)
        current = first + timedelta(seconds=61)
        handler, status_args = _command(manager, ["heartbeat", "status", "--json"])
        assert handler(status_args) == 1
        stale = json.loads(capsys.readouterr().out)
        resumed = _dispatch(manager)
    finally:
        manager.unload()

    assert stale["status"] == "stale"
    assert stale["age_seconds"] == 61.0
    assert resumed["status"] == "resumed"
    assert resumed["resumed"] is True
    assert calls[-1]["payload"]["type"] == "hermes.entity.resumed"


def test_continuity_heartbeat_follows_a_b_a_profiles(tmp_path):
    profile_a = get_hermes_home()
    profile_b = tmp_path / "profile-b"
    _write_profile(profile_a)
    _write_profile(profile_b)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="a")
        _dispatch(manager)
        token = set_hermes_home_override(profile_b)
        try:
            manager.invoke_hook("on_session_start", session_id="b")
            state_b = json.loads(
                (profile_b / "entity" / "continuity.json").read_text(encoding="utf-8")
            )
            _dispatch(manager)
        finally:
            reset_hermes_home_override(token)
        state_a = json.loads(
            (profile_a / "entity" / "continuity.json").read_text(encoding="utf-8")
        )
    finally:
        manager.unload()

    assert state_b["heartbeat_sequence"] == 0
    assert state_a["heartbeat_sequence"] == 1


def test_wrong_owner_continuity_is_never_replaced():
    home = get_hermes_home()
    _write_profile(home)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
        path = home / "entity" / "continuity.json"
        wrong_owner = json.dumps(
            {
                "continuity_version": 1,
                "owner_entity_id": "00000000-0000-4000-8000-000000000000",
                "heartbeat_sequence": 0,
                "last_heartbeat_at": "",
                "last_source": "",
            },
            indent=2,
        ).encode()
        path.write_bytes(wrong_owner)
        result = _dispatch(manager)
    finally:
        manager.unload()

    assert "owner does not match" in result["error"]
    assert path.read_bytes() == wrong_owner
