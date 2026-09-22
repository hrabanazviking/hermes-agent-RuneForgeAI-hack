"""Contracts for explicit relationship continuity."""

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
        f"        relationships_history_limit: {history_limit}\n",
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


def test_lifecycle_creates_empty_ledger_owned_by_stable_identity():
    home = get_hermes_home()
    _write_profile(home)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one", model="model-a")
        identity = yaml.safe_load(
            (home / "entity" / "entity.yaml").read_text(encoding="utf-8")
        )
        path = home / "entity" / "relationships.yaml"
        first_bytes = path.read_bytes()
        manager.invoke_hook("on_session_start", session_id="two", model="model-b")
    finally:
        manager.unload()

    ledger = yaml.safe_load(first_bytes)
    assert ledger == {
        "relationships_version": 1,
        "owner_entity_id": identity["entity_id"],
        "relationships": {},
    }
    assert path.read_bytes() == first_bytes


def test_explicit_tools_update_read_and_archive_without_deleting_history():
    home = get_hermes_home()
    _write_profile(home)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
        loaded = manager._plugins["volmarr-core"]
        assert {"relationship_get", "relationship_upsert"}.issubset(
            loaded.tools_registered
        )
        created = _dispatch(
            manager,
            "relationship_upsert",
            {
                "entity_id": "volmarr",
                "display_name": "Volmarr",
                "relationship_type": "collaborator",
                "status": "active",
                "trust": 0.8,
                "note": "Identity slice completed together.",
            },
        )
        archived = _dispatch(
            manager,
            "relationship_upsert",
            {
                "entity_id": "volmarr",
                "display_name": "Volmarr",
                "relationship_type": "collaborator",
                "status": "archived",
                "trust": 0.75,
                "note": "Preserve history rather than delete it.",
            },
        )
        current = _dispatch(
            manager,
            "relationship_get",
            {"entity_id": "volmarr"},
        )
        with_history = _dispatch(
            manager,
            "relationship_get",
            {"entity_id": "volmarr", "include_history": True},
        )
    finally:
        manager.unload()

    assert created["history_events"] == 1
    assert archived["history_events"] == 2
    assert current["relationship"]["status"] == "archived"
    assert "history" not in current["relationship"]
    assert [event["status"] for event in with_history["relationship"]["history"]] == [
        "active",
        "archived",
    ]


def test_relationship_history_is_bounded_and_survives_reload():
    home = get_hermes_home()
    _write_profile(home, history_limit=2)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
        for index in range(3):
            result = _dispatch(
                manager,
                "relationship_upsert",
                {
                    "entity_id": "person_1",
                    "display_name": "Person One",
                    "relationship_type": "friend",
                    "status": "active",
                    "trust": 0.5 + index / 10,
                    "note": f"event-{index}",
                },
            )
            assert result["success"] is True
    finally:
        manager.unload()

    manager = _load_manager()
    try:
        restored = _dispatch(
            manager,
            "relationship_get",
            {"entity_id": "person_1", "include_history": True},
        )
    finally:
        manager.unload()

    assert [event["note"] for event in restored["relationship"]["history"]] == [
        "event-1",
        "event-2",
    ]


def test_relationship_ledgers_follow_a_b_a_profiles(tmp_path):
    profile_a = get_hermes_home()
    profile_b = tmp_path / "profile-b"
    _write_profile(profile_a)
    _write_profile(profile_b)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="a")
        _dispatch(
            manager,
            "relationship_upsert",
            {
                "entity_id": "a_friend",
                "display_name": "A Friend",
                "relationship_type": "friend",
                "status": "active",
                "trust": 0.9,
            },
        )
        token = set_hermes_home_override(profile_b)
        try:
            manager.invoke_hook("on_session_start", session_id="b")
            before_b = _dispatch(manager, "relationship_get", {})
            _dispatch(
                manager,
                "relationship_upsert",
                {
                    "entity_id": "b_friend",
                    "display_name": "B Friend",
                    "relationship_type": "friend",
                    "status": "active",
                    "trust": 0.6,
                },
            )
        finally:
            reset_hermes_home_override(token)
        restored_a = _dispatch(manager, "relationship_get", {})
    finally:
        manager.unload()

    assert before_b["relationships"] == []
    assert [row["entity_id"] for row in restored_a["relationships"]] == ["a_friend"]


def test_corrupt_or_wrong_owner_ledger_is_never_replaced():
    home = get_hermes_home()
    _write_profile(home)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
        path = home / "entity" / "relationships.yaml"
        path.write_bytes(
            b"relationships_version: 1\n"
            b"owner_entity_id: 00000000-0000-4000-8000-000000000000\n"
            b"relationships: {}\n"
        )
        original = path.read_bytes()
        manager.invoke_hook("on_session_start", session_id="two")
        result = _dispatch(manager, "relationship_get", {})
    finally:
        manager.unload()

    assert "owner does not match" in result["error"]
    assert path.read_bytes() == original


def test_relationship_tool_rejects_invalid_fields_before_write():
    home = get_hermes_home()
    _write_profile(home)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
        path = home / "entity" / "relationships.yaml"
        original = path.read_bytes()
        bad_id = _dispatch(
            manager,
            "relationship_upsert",
            {
                "entity_id": "../escape",
                "display_name": "No",
                "relationship_type": "friend",
                "status": "active",
                "trust": 1,
            },
        )
        bad_trust = _dispatch(
            manager,
            "relationship_upsert",
            {
                "entity_id": "friend",
                "display_name": "No",
                "relationship_type": "friend",
                "status": "active",
                "trust": True,
            },
        )
    finally:
        manager.unload()

    assert "error" in bad_id
    assert "error" in bad_trust
    assert path.read_bytes() == original


def test_disabling_identity_prevents_relationship_state_creation():
    home = get_hermes_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        "        identity_enabled: false\n"
        "        relationships_enabled: true\n",
        encoding="utf-8",
    )
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
    finally:
        manager.unload()

    assert not (home / "entity" / "entity.yaml").exists()
    assert not (home / "entity" / "relationships.yaml").exists()
    assert not (home / "entity" / "goals.yaml").exists()
