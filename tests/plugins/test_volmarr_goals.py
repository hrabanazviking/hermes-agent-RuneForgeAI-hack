"""Contracts for durable entity goals and task state."""

from __future__ import annotations

import json

import yaml

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)


def _write_profile(home, *, history_limit: int = 100) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        f"        goals_history_limit: {history_limit}\n",
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


def test_lifecycle_creates_empty_goal_ledger_owned_by_identity():
    home = get_hermes_home()
    _write_profile(home)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one", model="model-a")
        identity = yaml.safe_load(
            (home / "entity" / "entity.yaml").read_text(encoding="utf-8")
        )
        path = home / "entity" / "goals.yaml"
        first_bytes = path.read_bytes()
        manager.invoke_hook("on_session_start", session_id="two", model="model-b")
    finally:
        manager.unload()

    assert yaml.safe_load(first_bytes) == {
        "goals_version": 1,
        "owner_entity_id": identity["entity_id"],
        "goals": {},
    }
    assert path.read_bytes() == first_bytes


def test_goal_tools_create_advance_complete_and_archive_with_history():
    home = get_hermes_home()
    _write_profile(home)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
        assert {"goal_get", "goal_create", "goal_update"}.issubset(
            manager._plugins["volmarr-core"].tools_registered
        )
        created = _dispatch(
            manager,
            "goal_create",
            {
                "title": "Build persistent goals",
                "description": "Keep task state independent of a model.",
                "priority": 90,
                "next_action": "Write behavior contracts.",
            },
        )
        goal_id = created["goal_id"]
        active = _dispatch(
            manager,
            "goal_update",
            {
                "goal_id": goal_id,
                "status": "active",
                "next_action": "Run focused tests.",
                "note": "Implementation started.",
            },
        )
        completed = _dispatch(
            manager,
            "goal_update",
            {
                "goal_id": goal_id,
                "status": "completed",
                "next_action": "",
                "note": "Acceptance contracts passed.",
            },
        )
        restored = _dispatch(
            manager,
            "goal_get",
            {"goal_id": goal_id, "include_history": True},
        )["goal"]
        archived = _dispatch(
            manager,
            "goal_update",
            {"goal_id": goal_id, "status": "archived"},
        )
        archived_goal = _dispatch(
            manager,
            "goal_get",
            {"goal_id": goal_id},
        )["goal"]
    finally:
        manager.unload()

    assert created["status"] == "planned"
    assert active["status"] == "active"
    assert completed["status"] == "completed"
    assert restored["completed_at"].endswith("Z")
    assert [row["status"] for row in restored["history"]] == [
        "planned",
        "active",
        "completed",
    ]
    assert archived["status"] == "archived"
    assert archived_goal["completed_at"] == restored["completed_at"]


def test_goal_state_and_bounded_history_survive_plugin_reload():
    home = get_hermes_home()
    _write_profile(home, history_limit=2)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
        goal_id = _dispatch(
            manager,
            "goal_create",
            {"title": "Survive restart"},
        )["goal_id"]
        for status in ("active", "blocked", "active"):
            _dispatch(
                manager,
                "goal_update",
                {"goal_id": goal_id, "status": status, "note": status},
            )
    finally:
        manager.unload()

    manager = _load_manager()
    try:
        goal = _dispatch(
            manager,
            "goal_get",
            {"goal_id": goal_id, "include_history": True},
        )["goal"]
    finally:
        manager.unload()

    assert goal["status"] == "active"
    assert [row["status"] for row in goal["history"]] == ["blocked", "active"]


def test_goal_lists_are_priority_ordered_and_status_filtered():
    home = get_hermes_home()
    _write_profile(home)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
        low = _dispatch(
            manager,
            "goal_create",
            {"title": "Low", "priority": 10},
        )["goal_id"]
        high = _dispatch(
            manager,
            "goal_create",
            {"title": "High", "priority": 90},
        )["goal_id"]
        _dispatch(manager, "goal_update", {"goal_id": high, "status": "active"})
        all_goals = _dispatch(manager, "goal_get", {})["goals"]
        planned = _dispatch(manager, "goal_get", {"status": "planned"})["goals"]
    finally:
        manager.unload()

    assert [row["goal_id"] for row in all_goals] == [high, low]
    assert [row["goal_id"] for row in planned] == [low]
    assert all("description" not in row and "history" not in row for row in all_goals)


def test_goal_ledgers_follow_a_b_a_profiles(tmp_path):
    profile_a = get_hermes_home()
    profile_b = tmp_path / "profile-b"
    _write_profile(profile_a)
    _write_profile(profile_b)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="a")
        goal_a = _dispatch(manager, "goal_create", {"title": "Profile A"})["goal_id"]
        token = set_hermes_home_override(profile_b)
        try:
            manager.invoke_hook("on_session_start", session_id="b")
            before_b = _dispatch(manager, "goal_get", {})
            _dispatch(manager, "goal_create", {"title": "Profile B"})
        finally:
            reset_hermes_home_override(token)
        restored_a = _dispatch(manager, "goal_get", {})
    finally:
        manager.unload()

    assert before_b["goals"] == []
    assert [row["goal_id"] for row in restored_a["goals"]] == [goal_a]


def test_wrong_owner_and_invalid_mutations_preserve_goal_bytes():
    home = get_hermes_home()
    _write_profile(home)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
        path = home / "entity" / "goals.yaml"
        wrong_owner = (
            "goals_version: 1\n"
            "owner_entity_id: 00000000-0000-4000-8000-000000000000\n"
            "goals: {}\n"
        ).encode()
        path.write_bytes(wrong_owner)
        manager.invoke_hook("on_session_start", session_id="two")
        read = _dispatch(manager, "goal_get", {})
        invalid = _dispatch(
            manager,
            "goal_create",
            {"title": "Invalid", "priority": True},
        )
    finally:
        manager.unload()

    assert "owner does not match" in read["error"]
    assert "error" in invalid
    assert path.read_bytes() == wrong_owner
