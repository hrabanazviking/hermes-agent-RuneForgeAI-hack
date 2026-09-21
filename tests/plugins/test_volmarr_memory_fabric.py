"""Contracts for the profile-scoped Bifröst bridge attachment."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import types
from pathlib import Path

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)


class _MemoryBackend:
    MIMIR = "mimir"


class _BifrostConfig:
    created: list["_BifrostConfig"] = []

    def __init__(self, **values) -> None:
        self.__dict__.update(values)
        self.created.append(self)


class _BifrostBridge:
    def __init__(self, config) -> None:
        self.config = config


def _install_bifrost_contract(monkeypatch) -> None:
    _BifrostConfig.created = []
    package = types.ModuleType("bifrost")
    package.BifrostConfig = _BifrostConfig
    package.BifrostBridge = _BifrostBridge
    package.MemoryBackend = _MemoryBackend
    monkeypatch.setitem(sys.modules, "bifrost", package)


def _write_profile(home: Path, memory_count: int, *, db_path="memory/runa_memory.db"):
    (home / "memory").mkdir(parents=True, exist_ok=True)
    if not db_path.startswith(".."):
        database = home / db_path
        database.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(database) as connection:
            connection.execute(
                "CREATE TABLE memories (id INTEGER PRIMARY KEY, content TEXT NOT NULL)"
            )
            connection.executemany(
                "INSERT INTO memories(content) VALUES (?)",
                [(f"memory-{index}",) for index in range(memory_count)],
            )
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        f"        bifrost_mimir_db_path: {db_path}\n"
        "        bifrost_muninn_db_path: memory/muninn_hebbian.db\n",
        encoding="utf-8",
    )


def _memory_health_command(manager):
    command = manager._cli_commands["volmarr"]
    parser = argparse.ArgumentParser()
    command["setup_fn"](parser)
    args = parser.parse_args(["memory", "health", "--json"])
    return command["handler_fn"], args


def test_bifrost_bridge_resolves_storage_per_active_profile_without_optional_backends(
    tmp_path,
    capsys,
    monkeypatch,
):
    from hermes_cli import plugins as plugins_mod

    _install_bifrost_contract(monkeypatch)
    profile_a = get_hermes_home()
    profile_b = tmp_path / "profile-b"
    _write_profile(profile_a, 1)
    _write_profile(profile_b, 2)

    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        handler, args = _memory_health_command(manager)
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

    assert [report["memory_count"] for report in reports] == [1, 2, 1]
    assert all(report["package_attached"] for report in reports)
    assert [Path(config.mimir_db_path) for config in _BifrostConfig.created] == [
        profile_a / "memory" / "runa_memory.db",
        profile_b / "memory" / "runa_memory.db",
        profile_a / "memory" / "runa_memory.db",
    ]
    assert all(
        config.default_backend == _MemoryBackend.MIMIR
        and config.enable_hebbian_reinforcement is False
        and config.auto_consolidate is False
        and config.auto_decay is False
        for config in _BifrostConfig.created
    )


def test_bifrost_probe_reports_missing_storage_without_creating_it(
    tmp_path,
    capsys,
    monkeypatch,
):
    from hermes_cli import plugins as plugins_mod

    _install_bifrost_contract(monkeypatch)
    home = get_hermes_home()
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n",
        encoding="utf-8",
    )
    expected = home / "memory" / "runa_memory.db"

    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        handler, args = _memory_health_command(manager)
        assert handler(args) == 1
        report = json.loads(capsys.readouterr().out)
    finally:
        manager.unload()

    assert report["status"] == "storage_missing"
    assert report["package_attached"] is True
    assert not expected.exists()


def test_bifrost_probe_rejects_profile_escape_before_constructing_bridge(
    capsys,
    monkeypatch,
):
    from hermes_cli import plugins as plugins_mod

    _install_bifrost_contract(monkeypatch)
    home = get_hermes_home()
    _write_profile(home, 0, db_path="../foreign.db")

    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        handler, args = _memory_health_command(manager)
        assert handler(args) == 1
        report = json.loads(capsys.readouterr().out)
    finally:
        manager.unload()

    assert report["status"] == "configuration_error"
    assert report["error_type"] == "MemoryFabricConfigurationError"
    assert _BifrostConfig.created == []
