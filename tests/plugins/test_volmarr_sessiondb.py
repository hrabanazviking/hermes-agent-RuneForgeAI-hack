"""Preservation contracts for Hermes' canonical SessionDB."""

from __future__ import annotations

import argparse
import json
import sqlite3

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)
from hermes_state_common import SCHEMA_SQL, SCHEMA_VERSION


def _write_profile(home) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings: {}\n",
        encoding="utf-8",
    )


def _seed(home, session_id: str, content: str) -> bytes:
    database = home / "state.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(SCHEMA_SQL)
        connection.execute(
            "INSERT INTO schema_version(version) VALUES (?)",
            (SCHEMA_VERSION,),
        )
        connection.execute(
            "INSERT INTO sessions(id, source, started_at, message_count) "
            "VALUES (?, ?, ?, 1)",
            (session_id, "volmarr-preservation-test", 1.0),
        )
        connection.execute(
            "INSERT INTO messages(session_id, role, content, timestamp) "
            "VALUES (?, 'user', ?, 1.0)",
            (session_id, content),
        )
    return database.read_bytes()


def _health_command(manager):
    command = manager._cli_commands["volmarr"]
    parser = argparse.ArgumentParser()
    command["setup_fn"](parser)
    args = parser.parse_args(["memory", "sessiondb", "health", "--json"])
    return command["handler_fn"], args


def test_sessiondb_audit_tracks_profiles_without_mutating_history(
    tmp_path,
    capsys,
):
    from hermes_cli import plugins as plugins_mod

    profile_a = get_hermes_home()
    profile_b = tmp_path / "profile-b"
    _write_profile(profile_a)
    _write_profile(profile_b)
    before_a = _seed(profile_a, "session-a", "canonical-a")
    before_b = _seed(profile_b, "session-b", "canonical-b")

    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        handler, args = _health_command(manager)
        reports = []
        for home in (profile_a, profile_b, profile_a):
            token = set_hermes_home_override(home)
            try:
                assert handler(args) == 0
                reports.append(json.loads(capsys.readouterr().out))
            finally:
                reset_hermes_home_override(token)
    finally:
        manager.unload()

    assert [report["state_db_path"] for report in reports] == [
        str(profile_a / "state.db"),
        str(profile_b / "state.db"),
        str(profile_a / "state.db"),
    ]
    assert all(report["session_count"] == 1 for report in reports)
    assert all(report["message_count"] == 1 for report in reports)
    assert all(report["orphan_message_count"] == 0 for report in reports)
    assert (profile_a / "state.db").read_bytes() == before_a
    assert (profile_b / "state.db").read_bytes() == before_b


def test_volmarr_lifecycle_hooks_do_not_rewrite_sessiondb(capsys):
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    _write_profile(home)
    before = _seed(home, "canonical", "keep this exact transcript")
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        manager.invoke_hook("on_session_start", session_id="canonical")
        manager.invoke_hook(
            "pre_llm_call",
            messages=[{"role": "user", "content": "current turn"}],
            session_id="canonical",
        )
        manager.invoke_hook(
            "post_llm_call",
            response={"content": "answer"},
            session_id="canonical",
        )
        manager.invoke_hook(
            "on_session_end",
            session_id="canonical",
            completed=True,
            failed=False,
            interrupted=False,
        )
    finally:
        manager.unload()

    database = home / "state.db"
    assert database.read_bytes() == before
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT source FROM sessions WHERE id = 'canonical'"
        ).fetchone() == ("volmarr-preservation-test",)
        assert connection.execute(
            "SELECT role, content FROM messages WHERE session_id = 'canonical'"
        ).fetchall() == [("user", "keep this exact transcript")]


def test_sessiondb_audit_does_not_create_a_missing_store(capsys):
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    _write_profile(home)
    database = home / "state.db"
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        handler, args = _health_command(manager)
        assert handler(args) == 1
        report = json.loads(capsys.readouterr().out)
    finally:
        manager.unload()

    assert report["status"] == "storage_missing"
    assert not database.exists()


def test_sessiondb_audit_rejects_non_hermes_schema_without_mutation(capsys):
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    _write_profile(home)
    database = home / "state.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE unrelated (id INTEGER PRIMARY KEY)")
    before = database.read_bytes()
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        handler, args = _health_command(manager)
        assert handler(args) == 1
        report = json.loads(capsys.readouterr().out)
    finally:
        manager.unload()

    assert report["status"] == "schema_error"
    assert database.read_bytes() == before
