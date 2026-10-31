"""Contracts for the profile-bound ravens binding (Slice 90).

The Slice 90 Gate 0 re-audit measured the real muninn 1.0.0 / huginn
1.0.0 packages through Bifröst: Muninn is profile-bound through the
bridge, Huginn is not (the bridge constructs it with default-home
paths). This binding therefore attests the installed ravens
import-only and constructs them directly, pinned to the active
profile's store paths, with Huginn on its deterministic local backend.
Tests load the module through real plugin discovery and substitute
contract stub packages — the ravens are external packages, not Hermes
dependencies, so the stock tree must report ``package_missing``.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import types
from pathlib import Path

import pytest

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)


class _Ctx:
    def __init__(self, config=None):
        self._config = dict(config or {})

    def get_config(self, key, default=None):
        return self._config.get(key, default)


class _MuninnConfig:
    created: list["_MuninnConfig"] = []

    def __init__(self, **values) -> None:
        self.__dict__.update(values)
        self.created.append(self)


class _HuginnConfig:
    created: list["_HuginnConfig"] = []

    def __init__(self, **values) -> None:
        self.__dict__.update(values)
        self.created.append(self)


class _HebbianMemory:
    constructed: list["_MuninnConfig"] = []

    def __init__(self, config) -> None:
        self.config = config
        self.constructed.append(config)


class _HuginnMemory:
    constructed: list["_HuginnConfig"] = []

    def __init__(self, config=None, **overrides) -> None:
        self.config = config
        self.constructed.append(config)


def _install_ravens(monkeypatch, *, muninn_symbols=True, huginn_symbols=True) -> None:
    _MuninnConfig.created = []
    _HuginnConfig.created = []
    _HebbianMemory.constructed = []
    _HuginnMemory.constructed = []
    muninn = types.ModuleType("muninn")
    muninn.__version__ = "1.0.0"
    if muninn_symbols:
        muninn.HebbianMemory = _HebbianMemory
    muninn_config = types.ModuleType("muninn.config")
    muninn_config.MuninnConfig = _MuninnConfig
    huginn = types.ModuleType("huginn")
    huginn.__version__ = "1.0.0"
    if huginn_symbols:
        huginn.HuginnMemory = _HuginnMemory
    huginn_config = types.ModuleType("huginn.config")
    huginn_config.HuginnConfig = _HuginnConfig
    monkeypatch.setitem(sys.modules, "muninn", muninn)
    monkeypatch.setitem(sys.modules, "muninn.config", muninn_config)
    monkeypatch.setitem(sys.modules, "huginn", huginn)
    monkeypatch.setitem(sys.modules, "huginn.config", huginn_config)


def _load_ravens_module():
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [volmarr-core]\n", encoding="utf-8"
    )
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-core"]
        module = importlib.import_module(f"{loaded.module.__package__}.ravens")
        return manager, module
    except Exception:
        manager.unload()
        raise


def test_probe_reports_versions_and_constructs_nothing(monkeypatch):
    manager, ravens = _load_ravens_module()
    try:
        _install_ravens(monkeypatch)
        report = ravens.probe_ravens(_Ctx())
    finally:
        manager.unload()

    assert report.healthy is True
    assert report.status == "healthy"
    assert report.muninn_version == "1.0.0"
    assert report.huginn_version == "1.0.0"
    home = get_hermes_home().resolve()
    assert report.muninn_db_path == str(home / "memory" / "muninn_hebbian.db")
    assert report.huginn_db_path == str(home / "memory" / "huginn_local.db")
    # The probe is import-only: no raven was constructed, no store opened.
    assert _HebbianMemory.constructed == []
    assert _HuginnMemory.constructed == []


def test_probe_reports_package_missing_on_stock_tree(monkeypatch):
    manager, ravens = _load_ravens_module()
    try:
        for name in ("muninn", "muninn.config", "huginn", "huginn.config"):
            monkeypatch.delitem(sys.modules, name, raising=False)
        report = ravens.probe_ravens(_Ctx())
    finally:
        manager.unload()

    assert report.healthy is False
    assert report.status == "package_missing"


def test_probe_reports_contract_mismatch_when_symbol_missing(monkeypatch):
    manager, ravens = _load_ravens_module()
    try:
        _install_ravens(monkeypatch, huginn_symbols=False)
        report = ravens.probe_ravens(_Ctx())
    finally:
        manager.unload()

    assert report.healthy is False
    assert report.status == "contract_mismatch"


def test_builders_bind_store_paths_to_active_profile(tmp_path, monkeypatch):
    manager, ravens = _load_ravens_module()
    try:
        _install_ravens(monkeypatch)
        profile_a = get_hermes_home()
        profile_b = tmp_path / "profile-b"
        profile_b.mkdir(parents=True)
        seen = []
        for home in (profile_a, profile_b, profile_a):
            token = set_hermes_home_override(home)
            try:
                muninn = ravens.build_muninn_memory(_Ctx())
                huginn = ravens.build_huginn_memory(_Ctx())
            finally:
                reset_hermes_home_override(token)
            seen.append((muninn.config.db_path, huginn.config.local_db_path,
                         huginn.config.backend))
    finally:
        manager.unload()

    expected_a = (
        str((profile_a / "memory" / "muninn_hebbian.db").resolve()),
        str((profile_a / "memory" / "huginn_local.db").resolve()),
        "local",
    )
    expected_b = (
        str((profile_b / "memory" / "muninn_hebbian.db").resolve()),
        str((profile_b / "memory" / "huginn_local.db").resolve()),
        "local",
    )
    assert seen == [expected_a, expected_b, expected_a]


def test_builder_rejects_profile_escape(monkeypatch):
    manager, ravens = _load_ravens_module()
    try:
        _install_ravens(monkeypatch)
        ctx = _Ctx({"bifrost_huginn_db_path": "../foreign.db"})
        with pytest.raises(ravens.MemoryFabricConfigurationError):
            ravens.build_huginn_memory(ctx)
    finally:
        manager.unload()
    assert _HuginnMemory.constructed == []


def test_cli_ravens_health_reports_versions(capsys, monkeypatch):
    from hermes_cli import plugins as plugins_mod

    _install_ravens(monkeypatch)
    home = get_hermes_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [volmarr-core]\n", encoding="utf-8"
    )
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        command = manager._cli_commands["volmarr"]
        parser = argparse.ArgumentParser()
        command["setup_fn"](parser)
        args = parser.parse_args(["memory", "ravens", "health", "--json"])
        assert command["handler_fn"](args) == 0
        report = json.loads(capsys.readouterr().out)
    finally:
        manager.unload()

    assert report["healthy"] is True
    assert report["muninn_version"] == "1.0.0"
    assert report["huginn_version"] == "1.0.0"
    assert Path(report["huginn_db_path"]).name == "huginn_local.db"
