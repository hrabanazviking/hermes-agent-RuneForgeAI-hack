"""Contracts for bounded Verðandi-to-affective stimulus intake."""

from __future__ import annotations

import json
import socket

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)


class _Socket:
    def __init__(self, factory) -> None:
        self._factory = factory
        self.payload = b""
        self.timeout = None
        self.path = ""
        factory.calls.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *_exc) -> None:
        return None

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout

    def connect(self, path: str) -> None:
        self.path = path

    def sendall(self, payload: bytes) -> None:
        self.payload = payload

    def recv(self, _size: int) -> bytes:
        request = json.loads(self.payload.decode("utf-8"))
        if request.get("nerve_type") != "recent":
            return b""
        return self._factory.responses.pop(0)


class _SocketFactory:
    def __init__(self, responses: list[bytes]) -> None:
        self.responses = list(responses)
        self.calls: list[_Socket] = []

    def __call__(self, *_args):
        return _Socket(self)


def _response(events: list[dict], total: int) -> bytes:
    return (
        json.dumps(
            {
                "nerve_type": "recent_events",
                "events": events,
                "count": len(events),
                "total": total,
            }
        ).encode("utf-8")
        + b"\n"
    )


def _write_profile(home) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        "        socket_path: state/runa.sock\n"
        "        timeout_ms: 25\n"
        "        affective_enabled: true\n"
        "        affective_decay: 0\n"
        "        pad_enabled: true\n"
        "        pad_decay: 0\n"
        "        affective_verdandi_enabled: true\n"
        "        affective_verdandi_recent_count: 16\n",
        encoding="utf-8",
    )


def test_real_plugin_applies_only_unseen_allowlisted_metadata(monkeypatch):
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    _write_profile(home)
    old = {
        "type": "runa_reward",
        "source": "reward_system",
        "data": {"intensity": 7, "context": "old-secret"},
        "_seq": 10,
    }
    unseen = [
        old,
        {
            "type": "runa_reward",
            "source": "reward_system",
            "data": {"intensity": 7, "context": "private-nerve-content"},
            "_seq": 11,
        },
        {
            "type": "push_reward",
            "source": "push_reward",
            "data": {"intensity": 2, "repo": "private-repo-name"},
            "_seq": 12,
        },
        {
            "type": "runa_negative",
            "source": "untrusted-spoofer",
            "data": {"intensity": 7, "context": "must-not-apply"},
            "_seq": 13,
        },
        {
            "type": "conv_event",
            "source": "conv_logger:other-session",
            "data": {"event_type": "blocker", "content": "private blocker"},
            "_seq": 14,
        },
        {
            "type": "conv_event",
            "source": "conv_logger:other-session",
            "data": {
                "event_type": "blocker_resolved",
                "content": "private resolution",
            },
            "_seq": 15,
        },
        {
            "type": "conv_event",
            "source": "conv_logger:other-session",
            "data": {"event_type": "milestone", "content": "private milestone"},
            "_seq": 16,
        },
    ]
    factory = _SocketFactory(
        [
            _response([old], 10),
            _response(unseen, 16),
            _response(unseen, 16),
        ]
    )
    monkeypatch.setattr(socket, "AF_UNIX", object(), raising=False)
    monkeypatch.setattr(socket, "socket", factory)
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        manager.invoke_hook("on_session_start", session_id="session-1")
        first = manager.invoke_hook(
            "pre_llm_call",
            session_id="session-1",
            turn_id="turn-1",
            user_message="continue",
        )
        state_path = home / "affective" / "AFFECTIVE_NERVOUS_SYSTEM.json"
        state_before_repeat = state_path.read_bytes()
        manager.invoke_hook(
            "pre_llm_call",
            session_id="session-1",
            turn_id="turn-1",
            user_message="continue",
        )
    finally:
        manager.unload()

    state = json.loads(state_before_repeat)
    pad_path = home / "affective" / "pad_state.json"
    pad_before_repeat = pad_path.read_bytes()
    pad = json.loads(pad_before_repeat)
    serialized = state_before_repeat.decode("utf-8")
    contexts = [row["context"] for row in first if isinstance(row, dict)]
    cursor = json.loads(
        (home / "affective" / "verdandi_cursor.json").read_text(encoding="utf-8")
    )
    recent_requests = [
        json.loads(call.payload.decode("utf-8"))
        for call in factory.calls
        if b'"nerve_type":"recent"' in call.payload
    ]

    assert state_path.read_bytes() == state_before_repeat
    assert pad_path.read_bytes() == pad_before_repeat
    assert state["reward"] > 0.0
    assert state["github_push"] > 0.0
    assert 0.0 < state["discomfort"] < 0.05
    assert state["issue_repair"] > 0.0
    assert state["follow_through"] > 0.0
    assert pad["observation_count"] == 1
    assert pad["valence"] > 0.0
    assert pad["energy"] > 0.15
    assert pad["agency"] > 0.10
    assert "private-nerve-content" not in serialized
    assert "private-repo-name" not in serialized
    assert "must-not-apply" not in serialized
    assert "private blocker" not in serialized
    assert "private resolution" not in serialized
    assert "private milestone" not in serialized
    assert cursor == {
        "last_seq": 16,
        "schema": "runeforge.verdandi-affective-cursor",
        "version": 1,
    }
    assert recent_requests == [
        {"nerve_type": "recent", "count": 16},
        {"nerve_type": "recent", "count": 16},
        {"nerve_type": "recent", "count": 16},
    ]
    assert len(contexts) == 1
    assert "source=affective_regulation" in contexts[0]
    assert "source=pad_emotional_state" in contexts[0]
    assert all(call.timeout == 0.025 for call in factory.calls)
    assert all(call.path == str(home / "state" / "runa.sock") for call in factory.calls)


def test_malformed_recent_response_is_fail_open_and_does_not_create_cursor(
    monkeypatch,
):
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    _write_profile(home)
    factory = _SocketFactory([b"{broken\n"])
    monkeypatch.setattr(socket, "AF_UNIX", object(), raising=False)
    monkeypatch.setattr(socket, "socket", factory)
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        manager.invoke_hook("on_session_start", session_id="session-1")
    finally:
        manager.unload()

    state = json.loads(
        (home / "affective" / "AFFECTIVE_NERVOUS_SYSTEM.json").read_text(
            encoding="utf-8"
        )
    )
    assert state["reward"] == 0.0
    assert not (home / "affective" / "verdandi_cursor.json").exists()


def test_verdandi_cursor_and_stimuli_follow_profile_a_b_a(monkeypatch, tmp_path):
    from hermes_cli import plugins as plugins_mod

    profile_a = get_hermes_home()
    profile_b = tmp_path / "profile-b"
    _write_profile(profile_a)
    _write_profile(profile_b)
    reward = {
        "type": "runa_reward",
        "source": "reward_system",
        "data": {"intensity": 5},
        "_seq": 2,
    }
    factory = _SocketFactory(
        [
            _response([], 1),
            _response([], 10),
            _response([reward], 2),
        ]
    )
    monkeypatch.setattr(socket, "AF_UNIX", object(), raising=False)
    monkeypatch.setattr(socket, "socket", factory)
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        manager.invoke_hook("on_session_start", session_id="session-a")
        token = set_hermes_home_override(profile_b)
        try:
            manager.invoke_hook("on_session_start", session_id="session-b")
        finally:
            reset_hermes_home_override(token)
        manager.invoke_hook(
            "pre_llm_call",
            session_id="session-a",
            turn_id="turn-a",
            user_message="continue",
        )
    finally:
        manager.unload()

    cursor_a = json.loads(
        (profile_a / "affective" / "verdandi_cursor.json").read_text(
            encoding="utf-8"
        )
    )
    cursor_b = json.loads(
        (profile_b / "affective" / "verdandi_cursor.json").read_text(
            encoding="utf-8"
        )
    )
    state_a = json.loads(
        (profile_a / "affective" / "AFFECTIVE_NERVOUS_SYSTEM.json").read_text(
            encoding="utf-8"
        )
    )
    state_b = json.loads(
        (profile_b / "affective" / "AFFECTIVE_NERVOUS_SYSTEM.json").read_text(
            encoding="utf-8"
        )
    )
    pad_a = json.loads(
        (profile_a / "affective" / "pad_state.json").read_text(encoding="utf-8")
    )
    pad_b = json.loads(
        (profile_b / "affective" / "pad_state.json").read_text(encoding="utf-8")
    )
    assert cursor_a["last_seq"] == 2
    assert cursor_b["last_seq"] == 10
    assert state_a["reward"] > 0.0
    assert state_b["reward"] == 0.0
    assert pad_a["valence"] > pad_b["valence"]
    assert pad_a["active_session_id"] == "session-a"
    assert pad_b["active_session_id"] == "session-b"
