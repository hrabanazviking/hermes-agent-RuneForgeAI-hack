"""Contracts for the read-only Bifröst Muninn association-store probe (Slice 87).

The Slice 86 Gate 0 audit showed every Bifröst bridge method lazily
constructs the write backends, so this probe imports no ``bifrost`` or
``muninn`` package and constructs no bridge: it attests the active
profile's Muninn store directly through a read-only sqlite open,
requiring the ``hebbian_connections`` / ``activation_log`` schema the
audited bridge code expects and reporting both row counts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)


def _write_profile(
    home: Path,
    connection_count: int,
    activation_count: int,
    *,
    muninn_path: str = "memory/muninn_hebbian.db",
    tables: tuple[str, ...] = ("hebbian_connections", "activation_log"),
) -> Path | None:
    (home / "memory").mkdir(parents=True, exist_ok=True)
    database = None
    if not muninn_path.startswith(".."):
        database = home / muninn_path
        database.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(database) as connection:
            if "hebbian_connections" in tables:
                connection.execute(
                    "CREATE TABLE hebbian_connections ("
                    "memory_a_id TEXT NOT NULL, memory_b_id TEXT NOT NULL, "
                    "strength REAL NOT NULL, co_activation_count INTEGER NOT NULL)"
                )
                connection.executemany(
                    "INSERT INTO hebbian_connections VALUES (?, ?, ?, ?)",
                    [
                        (f"mem-{index}", f"mem-{index + 1}", 0.5, 1)
                        for index in range(connection_count)
                    ],
                )
            if "activation_log" in tables:
                connection.execute(
                    "CREATE TABLE activation_log ("
                    "id INTEGER PRIMARY KEY, memory_id TEXT NOT NULL)"
                )
                connection.executemany(
                    "INSERT INTO activation_log(memory_id) VALUES (?)",
                    [(f"mem-{index}",) for index in range(activation_count)],
                )
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        "        bifrost_mimir_db_path: memory/runa_memory.db\n"
        f"        bifrost_muninn_db_path: {muninn_path}\n",
        encoding="utf-8",
    )
    return database


def _muninn_health_command(manager):
    command = manager._cli_commands["volmarr"]
    parser = argparse.ArgumentParser()
    command["setup_fn"](parser)
    args = parser.parse_args(["memory", "muninn", "health", "--json"])
    return command["handler_fn"], args


def _run_health(manager, capsys, home=None):
    handler, args = _muninn_health_command(manager)
    if home is None:
        code = handler(args)
        return code, json.loads(capsys.readouterr().out)
    token = set_hermes_home_override(str(home))
    try:
        code = handler(args)
        return code, json.loads(capsys.readouterr().out)
    finally:
        reset_hermes_home_override(token)


def test_muninn_probe_reports_counts_without_any_bifrost_package(capsys):
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    _write_profile(home, 3, 5)
    sys.modules.pop("bifrost", None)
    sys.modules.pop("muninn", None)

    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        code, report = _run_health(manager, capsys)
    finally:
        manager.unload()

    assert code == 0
    assert report["status"] == "healthy"
    assert report["healthy"] is True
    assert report["connection_count"] == 3
    assert report["activation_count"] == 5
    assert report["muninn_db_path"] == str(home / "memory" / "muninn_hebbian.db")
    # The probe must not have imported either unauditable package.
    assert sys.modules.get("bifrost") is None
    assert sys.modules.get("muninn") is None


def test_muninn_probe_isolates_stores_per_active_profile(tmp_path, capsys):
    from hermes_cli import plugins as plugins_mod

    profile_a = get_hermes_home()
    profile_b = tmp_path / "profile-b"
    _write_profile(profile_a, 1, 2)
    _write_profile(profile_b, 4, 7)

    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        reports = [
            _run_health(manager, capsys, home)[1]
            for home in (profile_a, profile_b, profile_a)
        ]
    finally:
        manager.unload()

    assert [(r["connection_count"], r["activation_count"]) for r in reports] == [
        (1, 2),
        (4, 7),
        (1, 2),
    ]
    assert all(r["status"] == "healthy" for r in reports)


def test_muninn_probe_reports_missing_storage_without_creating_it(capsys):
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [volmarr-core]\n",
        encoding="utf-8",
    )
    expected = home / "memory" / "muninn_hebbian.db"

    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        code, report = _run_health(manager, capsys)
    finally:
        manager.unload()

    assert code == 1
    assert report["status"] == "storage_missing"
    assert not expected.exists()


def test_muninn_probe_reports_schema_missing_without_activation_log(capsys):
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    _write_profile(home, 2, 0, tables=("hebbian_connections",))

    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        code, report = _run_health(manager, capsys)
    finally:
        manager.unload()

    assert code == 1
    assert report["status"] == "schema_missing"
    assert report["connection_count"] is None


def test_muninn_probe_reports_schema_missing_without_hebbian_connections(capsys):
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    _write_profile(home, 0, 2, tables=("activation_log",))

    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        code, report = _run_health(manager, capsys)
    finally:
        manager.unload()

    assert code == 1
    assert report["status"] == "schema_missing"
    assert report["activation_count"] is None


def test_muninn_probe_leaves_store_bytes_identical(capsys):
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    database = _write_profile(home, 3, 3)
    assert database is not None
    before = hashlib.sha256(database.read_bytes()).hexdigest()

    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        code, report = _run_health(manager, capsys)
    finally:
        manager.unload()

    assert code == 0
    assert report["status"] == "healthy"
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before
    assert not (database.parent / "muninn_hebbian.db-wal").exists()
    assert not (database.parent / "muninn_hebbian.db-shm").exists()


def test_muninn_probe_rejects_profile_escape_as_configuration_error(capsys):
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    _write_profile(home, 0, 0, muninn_path="../foreign.db")

    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        code, report = _run_health(manager, capsys)
    finally:
        manager.unload()

    assert code == 1
    assert report["status"] == "configuration_error"
    assert report["error_type"] == "MemoryFabricConfigurationError"


def test_muninn_probe_refuses_symlinked_store(capsys, tmp_path):
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    real = _write_profile(tmp_path / "elsewhere", 1, 1)
    assert real is not None
    link_dir = home / "memory"
    link_dir.mkdir(parents=True, exist_ok=True)
    (link_dir / "muninn_hebbian.db").symlink_to(real)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        "        bifrost_muninn_db_path: memory/muninn_hebbian.db\n",
        encoding="utf-8",
    )

    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        code, report = _run_health(manager, capsys)
    finally:
        manager.unload()

    assert code == 1
    assert report["status"] == "storage_missing"
