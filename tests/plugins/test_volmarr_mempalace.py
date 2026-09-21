"""Contracts for the profile-scoped MemPalace attachment."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import types

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)


def _install_package(monkeypatch, version="3.10.0") -> None:
    package = types.ModuleType("mempalace")
    package.__version__ = version
    monkeypatch.setitem(sys.modules, "mempalace", package)


def _write_profile(home, collection_name="mempalace_drawers", *, create_store=True):
    home.mkdir(parents=True, exist_ok=True)
    palace = home / "memory" / "mempalace"
    if create_store:
        palace.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(palace / "chroma.sqlite3") as connection:
            connection.execute(
                "CREATE TABLE collections (id TEXT PRIMARY KEY, name TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO collections(id, name) VALUES ('drawers', ?)",
                (collection_name,),
            )
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        "        mempalace_path: memory/mempalace\n"
        f"        mempalace_collection_name: {collection_name}\n",
        encoding="utf-8",
    )
    return palace


def _health_command(manager):
    command = manager._cli_commands["volmarr"]
    parser = argparse.ArgumentParser()
    command["setup_fn"](parser)
    args = parser.parse_args(["memory", "mempalace", "health", "--json"])
    return command["handler_fn"], args


def test_mempalace_probe_tracks_the_active_profile_a_to_b_to_a(
    tmp_path,
    capsys,
    monkeypatch,
):
    from hermes_cli import plugins as plugins_mod

    _install_package(monkeypatch)
    profile_a = get_hermes_home()
    profile_b = tmp_path / "profile-b"
    palace_a = _write_profile(profile_a, "drawers_a")
    palace_b = _write_profile(profile_b, "drawers_b")

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

    assert [report["palace_path"] for report in reports] == [
        str(palace_a),
        str(palace_b),
        str(palace_a),
    ]
    assert [report["collection_name"] for report in reports] == [
        "drawers_a",
        "drawers_b",
        "drawers_a",
    ]
    assert all(report["collection_present"] for report in reports)
    assert all(report["package_version"] == "3.10.0" for report in reports)
    assert all(report["minimum_package_version"] == "3.10.0" for report in reports)


def test_mempalace_probe_rejects_pre_310_package(capsys, monkeypatch):
    from hermes_cli import plugins as plugins_mod

    _install_package(monkeypatch, "3.9.0")
    home = get_hermes_home()
    palace = _write_profile(home)
    before = (palace / "chroma.sqlite3").read_bytes()
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        handler, args = _health_command(manager)
        assert handler(args) == 1
        report = json.loads(capsys.readouterr().out)
    finally:
        manager.unload()

    assert report["status"] == "package_outdated"
    assert report["package_version"] == "3.9.0"
    assert report["minimum_package_version"] == "3.10.0"
    assert (palace / "chroma.sqlite3").read_bytes() == before


def test_mempalace_probe_is_read_only_when_storage_is_missing(
    capsys,
    monkeypatch,
):
    from hermes_cli import plugins as plugins_mod

    _install_package(monkeypatch)
    home = get_hermes_home()
    palace = _write_profile(home, create_store=False)
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        handler, args = _health_command(manager)
        assert handler(args) == 1
        report = json.loads(capsys.readouterr().out)
    finally:
        manager.unload()

    assert report["status"] == "storage_missing"
    assert not palace.exists()


def test_mempalace_probe_rejects_relative_profile_escape(capsys, monkeypatch):
    from hermes_cli import plugins as plugins_mod

    _install_package(monkeypatch)
    home = get_hermes_home()
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        "        mempalace_path: ../foreign-palace\n",
        encoding="utf-8",
    )
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        handler, args = _health_command(manager)
        assert handler(args) == 1
        report = json.loads(capsys.readouterr().out)
    finally:
        manager.unload()

    assert report["status"] == "configuration_error"
    assert report["error_type"] == "MemPalaceConfigurationError"


def test_mempalace_probe_reports_missing_collection_without_mutation(
    capsys,
    monkeypatch,
):
    from hermes_cli import plugins as plugins_mod

    _install_package(monkeypatch)
    home = get_hermes_home()
    palace = _write_profile(home, "different_collection")
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        "        mempalace_path: memory/mempalace\n"
        "        mempalace_collection_name: expected_collection\n",
        encoding="utf-8",
    )
    before = (palace / "chroma.sqlite3").read_bytes()
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        handler, args = _health_command(manager)
        assert handler(args) == 1
        report = json.loads(capsys.readouterr().out)
    finally:
        manager.unload()

    assert report["status"] == "collection_missing"
    assert report["collection_present"] is False
    assert (palace / "chroma.sqlite3").read_bytes() == before
