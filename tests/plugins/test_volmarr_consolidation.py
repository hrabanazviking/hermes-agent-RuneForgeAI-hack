"""Contracts for non-destructive sleep/consolidation checkpoints."""

from __future__ import annotations

import argparse
import json
import socket

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


def _write_profile(home) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n",
        encoding="utf-8",
    )


def _load_manager():
    from hermes_cli import plugins as plugins_mod

    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    return manager


def _dispatch(manager, name: str, args: dict) -> dict:
    from tools.registry import registry

    return json.loads(registry.dispatch(name, args, scope=manager.scope_key))


def _command_json(manager, argv: list[str], capsys) -> tuple[int, dict]:
    command = manager._cli_commands["volmarr"]
    parser = argparse.ArgumentParser()
    command["setup_fn"](parser)
    args = parser.parse_args(argv)
    code = command["handler_fn"](args)
    captured = capsys.readouterr()
    assert captured.err == ""
    return code, json.loads(captured.out)


def test_sleep_cycle_checkpoints_state_without_rewriting_source_ledgers():
    home = get_hermes_home()
    _write_profile(home)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
        _dispatch(
            manager,
            "relationship_upsert",
            {
                "entity_id": "volmarr",
                "display_name": "Volmarr",
                "relationship_type": "collaborator",
                "status": "active",
                "trust": 0.9,
            },
        )
        active = _dispatch(
            manager,
            "goal_create",
            {"title": "Active private goal", "priority": 90},
        )["goal_id"]
        _dispatch(manager, "goal_update", {"goal_id": active, "status": "active"})
        _dispatch(manager, "goal_create", {"title": "Planned private goal"})
        source_paths = [
            home / "entity" / "entity.yaml",
            home / "entity" / "relationships.yaml",
            home / "entity" / "goals.yaml",
            home / "entity" / "continuity.json",
        ]
        before = {path: path.read_bytes() for path in source_paths}
        report = _dispatch(manager, "entity_sleep_cycle", {})
    finally:
        manager.unload()

    checkpoint = json.loads(
        (home / "entity" / "consolidation.json").read_text(encoding="utf-8")
    )
    assert report["healthy"] is True
    assert report["sequence"] == 1
    assert checkpoint["summary"] == {
        "relationships_total": 1,
        "relationships_active": 1,
        "goals_total": 2,
        "goals_planned": 1,
        "goals_active": 1,
        "goals_blocked": 0,
        "goals_completed": 0,
        "heartbeat_sequence": 0,
    }
    assert set(checkpoint["component_digests"]) == {
        "identity",
        "relationships",
        "goals",
        "continuity",
    }
    assert all(path.read_bytes() == before[path] for path in source_paths)


def test_checkpoint_sequence_survives_plugin_reload(capsys):
    home = get_hermes_home()
    _write_profile(home)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
        first = _dispatch(manager, "entity_sleep_cycle", {})
    finally:
        manager.unload()

    manager = _load_manager()
    try:
        second = _dispatch(manager, "entity_sleep_cycle", {})
        code, status = _command_json(
            manager,
            ["sleep", "status", "--json"],
            capsys,
        )
    finally:
        manager.unload()

    assert first["sequence"] == 1
    assert second["sequence"] == 2
    assert code == 0
    assert status["sequence"] == 2


def test_consolidation_event_contains_counts_not_entity_content(monkeypatch):
    home = get_hermes_home()
    _write_profile(home)
    calls: list[dict] = []
    monkeypatch.setattr(socket, "AF_UNIX", object(), raising=False)
    monkeypatch.setattr(socket, "socket", lambda *_args: _SocketRecorder(calls))
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="secret-session")
        _dispatch(
            manager,
            "goal_create",
            {"title": "never-publish-this-title", "description": "private-description"},
        )
        calls.clear()
        report = _dispatch(manager, "entity_sleep_cycle", {})
    finally:
        manager.unload()

    event = calls[-1]["payload"]
    serialized = json.dumps(event)
    assert event["type"] == "hermes.entity.consolidation.completed"
    assert event["data"]["schema"] == "runeforge.entity.consolidation"
    assert report["summary"]["goals_total"] == 1
    assert "never-publish-this-title" not in serialized
    assert "private-description" not in serialized
    assert "secret-session" not in serialized
    assert "owner_entity_id" not in serialized


def test_corrupt_checkpoint_is_reported_and_never_replaced(capsys):
    home = get_hermes_home()
    _write_profile(home)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
        path = home / "entity" / "consolidation.json"
        path.write_bytes(b'{"consolidation_version": [broken}')
        original = path.read_bytes()
        result = _dispatch(manager, "entity_sleep_cycle", {})
        code, status = _command_json(
            manager,
            ["sleep", "status", "--json"],
            capsys,
        )
    finally:
        manager.unload()

    assert "error" in result
    assert code == 1
    assert status["status"] == "invalid"
    assert path.read_bytes() == original


def test_daily_sleep_install_is_paused_idempotent_and_independent(capsys):
    home = get_hermes_home()
    _write_profile(home)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
        _, frequent = _command_json(
            manager,
            ["routines", "install", "--json"],
            capsys,
        )
        code, sleep = _command_json(
            manager,
            ["sleep", "install", "--json"],
            capsys,
        )
        _, sleep_again = _command_json(
            manager,
            ["sleep", "install", "--json"],
            capsys,
        )
    finally:
        manager.unload()

    jobs = json.loads((home / "cron" / "jobs.json").read_text(encoding="utf-8"))[
        "jobs"
    ]
    sleep_jobs = [job for job in jobs if job["name"] == "Volmarr Daily Consolidation"]
    assert code == 0
    assert sleep["status"] == "installed_paused", sleep
    assert sleep_again["job_id"] == sleep["job_id"]
    assert sleep["job_id"] != frequent["job_id"]
    assert len(sleep_jobs) == 1
    assert sleep_jobs[0]["enabled"] is False
    assert sleep_jobs[0]["no_agent"] is True
    assert sleep_jobs[0]["schedule_display"] == "every 1440m"


def test_consolidation_checkpoints_follow_a_b_a_profiles(tmp_path):
    profile_a = get_hermes_home()
    profile_b = tmp_path / "profile-b"
    _write_profile(profile_a)
    _write_profile(profile_b)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="a")
        _dispatch(manager, "entity_sleep_cycle", {})
        token = set_hermes_home_override(profile_b)
        try:
            manager.invoke_hook("on_session_start", session_id="b")
            _dispatch(manager, "entity_sleep_cycle", {})
            checkpoint_b = json.loads(
                (profile_b / "entity" / "consolidation.json").read_text(
                    encoding="utf-8"
                )
            )
        finally:
            reset_hermes_home_override(token)
        _dispatch(manager, "entity_sleep_cycle", {})
        checkpoint_a = json.loads(
            (profile_a / "entity" / "consolidation.json").read_text(
                encoding="utf-8"
            )
        )
    finally:
        manager.unload()

    assert checkpoint_a["consolidation_sequence"] == 2
    assert checkpoint_b["consolidation_sequence"] == 1
    assert checkpoint_a["owner_entity_id"] != checkpoint_b["owner_entity_id"]
