"""Contracts for model-independent, profile-scoped entity identity."""

from __future__ import annotations

import argparse
import json
import uuid

import yaml

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)


def _write_profile(home, *, identity_path: str = "entity/entity.yaml") -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        f"        identity_path: {identity_path}\n",
        encoding="utf-8",
    )


def _load_manager():
    from hermes_cli import plugins as plugins_mod

    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    return manager


def test_session_start_creates_once_and_never_touches_soul():
    home = get_hermes_home()
    _write_profile(home)
    soul = home / "SOUL.md"
    soul.write_bytes(b"# Hand-authored soul\r\nKeep this exact.\r\n")
    original_soul = soul.read_bytes()
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one", model="model-a")
        path = home / "entity" / "entity.yaml"
        first_bytes = path.read_bytes()
        first = yaml.safe_load(first_bytes)
        manager.invoke_hook("on_session_start", session_id="two", model="model-b")
    finally:
        manager.unload()

    assert path.read_bytes() == first_bytes
    assert soul.read_bytes() == original_soul
    assert first["identity_version"] == 1
    assert first["home_runtime"] == "hermes"
    assert first["name"] == "undecided"
    assert uuid.UUID(first["entity_id"])
    assert first["created_at"].endswith("Z")


def test_identity_follows_a_b_a_profile_switches(tmp_path):
    profile_a = get_hermes_home()
    profile_b = tmp_path / "profile-b"
    _write_profile(profile_a)
    _write_profile(profile_b)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="a1")
        path_a = profile_a / "entity" / "entity.yaml"
        bytes_a = path_a.read_bytes()
        id_a = yaml.safe_load(bytes_a)["entity_id"]

        token = set_hermes_home_override(profile_b)
        try:
            manager.invoke_hook("on_session_start", session_id="b1")
            id_b = yaml.safe_load(
                (profile_b / "entity" / "entity.yaml").read_text(encoding="utf-8")
            )["entity_id"]
        finally:
            reset_hermes_home_override(token)

        manager.invoke_hook("on_session_start", session_id="a2")
    finally:
        manager.unload()

    assert id_a != id_b
    assert path_a.read_bytes() == bytes_a


def test_corrupt_identity_is_reported_and_never_replaced(capsys):
    home = get_hermes_home()
    _write_profile(home)
    path = home / "entity" / "entity.yaml"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"identity_version: [broken\n")
    original = path.read_bytes()
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
        command = manager._cli_commands["volmarr"]
        parser = argparse.ArgumentParser()
        command["setup_fn"](parser)
        exit_code = command["handler_fn"](
            parser.parse_args(["identity", "health", "--json"])
        )
    finally:
        manager.unload()

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert report["status"] == "invalid"
    assert report["error_type"] == "IdentityError"
    assert path.read_bytes() == original


def test_existing_valid_identity_is_preserved_exactly(capsys):
    home = get_hermes_home()
    _write_profile(home)
    path = home / "entity" / "entity.yaml"
    path.parent.mkdir(parents=True)
    original = (
        "# deliberately hand-maintained\n"
        "entity_id: 11111111-2222-4333-8444-555555555555\n"
        "name: Runa\n"
        "created_at: '2026-09-21T00:00:00Z'\n"
        "identity_version: 1\n"
        "persona_pack: northern-light\n"
        "home_runtime: hermes\n"
    ).encode()
    path.write_bytes(original)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one", model="replacement")
        command = manager._cli_commands["volmarr"]
        parser = argparse.ArgumentParser()
        command["setup_fn"](parser)
        exit_code = command["handler_fn"](
            parser.parse_args(["identity", "health", "--json"])
        )
    finally:
        manager.unload()

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert report["entity_id"] == "11111111-2222-4333-8444-555555555555"
    assert report["name"] == "Runa"
    assert path.read_bytes() == original


def test_relative_escape_falls_back_inside_profile():
    home = get_hermes_home()
    _write_profile(home, identity_path="../../outside/entity.yaml")
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
    finally:
        manager.unload()

    assert (home / "entity" / "entity.yaml").is_file()
    assert not (home.parent / "outside" / "entity.yaml").exists()
