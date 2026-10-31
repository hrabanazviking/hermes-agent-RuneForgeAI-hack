"""Contracts for the flagged ravens write operations (Slice 92).

Slice 90's Gate 0 re-audit cleared Muninn reinforcement/decay/
consolidation and direct Huginn ingestion as explicit operations only.
These tests pin that enablement to the campaign law:

- every write is behind its own default-off flag, and the flag check
  happens before any package is imported or any store constructed;
- each operation constructs only its own backend, bound to the active
  profile's store paths through the Slice 90 builders, and closes it;
- reads stay pure: the health probes construct nothing even with every
  write flag enabled;
- inputs are validated before construction, and nothing is registered
  on any hook or packet path (the module is reachable only through the
  explicitly named CLI operations).

Tests load the module through real plugin discovery and substitute
contract stub packages, as in ``test_volmarr_ravens.py``.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import types

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
    instances: list["_HebbianMemory"] = []

    def __init__(self, config) -> None:
        self.config = config
        self.activated: list = []
        self.decay_calls: list = []
        self.consolidate_calls = 0
        self.closed = False
        self.instances.append(self)

    def activate_batch(self, memory_ids, emotional_valence=0.0):
        self.activated.append((list(memory_ids), emotional_valence))

    def decay(self, days=1.0):
        self.decay_calls.append(days)
        return {"decayed_edges": 3, "pruned_edges": 1}

    def consolidate(self):
        self.consolidate_calls += 1
        return {"consolidated_edges": 2}

    def close(self):
        self.closed = True


class _HuginnMemory:
    instances: list["_HuginnMemory"] = []

    def __init__(self, config=None, **overrides) -> None:
        self.config = config
        self.upserts: list = []
        self.closed = False
        self.instances.append(self)

    def upsert_memory(self, **values):
        self.upserts.append(values)
        return 7

    def close(self):
        self.closed = True


def _install_ravens(monkeypatch) -> None:
    _MuninnConfig.created = []
    _HuginnConfig.created = []
    _HebbianMemory.instances = []
    _HuginnMemory.instances = []
    muninn = types.ModuleType("muninn")
    muninn.__version__ = "1.0.0"
    muninn.HebbianMemory = _HebbianMemory
    muninn_config = types.ModuleType("muninn.config")
    muninn_config.MuninnConfig = _MuninnConfig
    huginn = types.ModuleType("huginn")
    huginn.__version__ = "1.0.0"
    huginn.HuginnMemory = _HuginnMemory
    huginn_config = types.ModuleType("huginn.config")
    huginn_config.HuginnConfig = _HuginnConfig
    monkeypatch.setitem(sys.modules, "muninn", muninn)
    monkeypatch.setitem(sys.modules, "muninn.config", muninn_config)
    monkeypatch.setitem(sys.modules, "huginn", huginn)
    monkeypatch.setitem(sys.modules, "huginn.config", huginn_config)


def _remove_ravens(monkeypatch) -> None:
    for name in ("muninn", "muninn.config", "huginn", "huginn.config"):
        monkeypatch.setitem(sys.modules, name, None)


def _load_writes_module(settings: str = ""):
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    home.mkdir(parents=True, exist_ok=True)
    config = "plugins:\n  enabled: [volmarr-core]\n"
    if settings:
        config += (
            "  entries:\n"
            "    volmarr-core:\n"
            "      settings:\n"
            + settings
        )
    (home / "config.yaml").write_text(config, encoding="utf-8")
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-core"]
        writes = importlib.import_module(f"{loaded.module.__package__}.ravens_writes")
        ravens = importlib.import_module(f"{loaded.module.__package__}.ravens")
        cli = importlib.import_module(f"{loaded.module.__package__}.cli")
        return manager, writes, ravens, cli
    except Exception:
        manager.unload()
        raise


def test_all_writes_disabled_by_default_construct_nothing(monkeypatch):
    manager, writes, _ravens, _cli = _load_writes_module()
    try:
        _install_ravens(monkeypatch)
        ctx = _Ctx()
        assert writes.reinforce_memories(ctx, [1, 2]).status == "disabled"
        assert writes.decay_memories(ctx, 1.0).status == "disabled"
        assert writes.consolidate_memories(ctx).status == "disabled"
        assert writes.ingest_memory(ctx, "a memory").status == "disabled"
    finally:
        manager.unload()
    assert _HebbianMemory.instances == []
    assert _HuginnMemory.instances == []


def test_disabled_gate_precedes_package_import(monkeypatch):
    manager, writes, _ravens, _cli = _load_writes_module()
    try:
        _remove_ravens(monkeypatch)
        ctx = _Ctx()
        result = writes.reinforce_memories(ctx, [1])
        assert result.status == "disabled"
    finally:
        manager.unload()


def test_reinforce_constructs_only_profile_bound_muninn(monkeypatch):
    manager, writes, _ravens, _cli = _load_writes_module()
    try:
        _install_ravens(monkeypatch)
        home = get_hermes_home().resolve()
        ctx = _Ctx({"bifrost_reinforcement_enabled": True})
        result = writes.reinforce_memories(ctx, [1, 2, 3], emotional_valence=0.5)
    finally:
        manager.unload()
    assert result.healthy is True
    assert result.status == "ok"
    assert result.detail == {"activated": 3, "memory_ids": [1, 2, 3]}
    assert len(_HebbianMemory.instances) == 1
    memory = _HebbianMemory.instances[0]
    assert memory.config.db_path == str(home / "memory" / "muninn_hebbian.db")
    assert memory.activated == [([1, 2, 3], 0.5)]
    assert memory.closed is True
    assert _HuginnMemory.instances == []


def test_operations_follow_the_active_profile_a_b_a(monkeypatch, tmp_path):
    manager, writes, _ravens, _cli = _load_writes_module()
    try:
        _install_ravens(monkeypatch)
        home_b = tmp_path / "profile-b"
        home_b.mkdir()
        ctx = _Ctx({"bifrost_reinforcement_enabled": True})
        profile_a = get_hermes_home().resolve()
        writes.reinforce_memories(ctx, [1])
        token = set_hermes_home_override(home_b)
        try:
            writes.reinforce_memories(ctx, [2])
        finally:
            reset_hermes_home_override(token)
        writes.reinforce_memories(ctx, [3])
    finally:
        manager.unload()
    paths = [instance.config.db_path for instance in _HebbianMemory.instances]
    assert paths == [
        str(profile_a / "memory" / "muninn_hebbian.db"),
        str(home_b.resolve() / "memory" / "muninn_hebbian.db"),
        str(profile_a / "memory" / "muninn_hebbian.db"),
    ]


def test_decay_and_consolidate_use_only_muninn(monkeypatch):
    manager, writes, _ravens, _cli = _load_writes_module()
    try:
        _install_ravens(monkeypatch)
        ctx = _Ctx(
            {"bifrost_decay_enabled": True, "bifrost_consolidation_enabled": True}
        )
        decayed = writes.decay_memories(ctx, 2.5)
        consolidated = writes.consolidate_memories(ctx)
    finally:
        manager.unload()
    assert decayed.healthy is True
    assert decayed.detail["report"] == {"decayed_edges": 3, "pruned_edges": 1}
    assert consolidated.healthy is True
    assert consolidated.detail["report"] == {"consolidated_edges": 2}
    assert [m.decay_calls for m in _HebbianMemory.instances] == [[2.5], []]
    assert [m.consolidate_calls for m in _HebbianMemory.instances] == [0, 1]
    assert all(m.closed for m in _HebbianMemory.instances)
    assert _HuginnMemory.instances == []


def test_ingest_constructs_only_direct_profile_bound_huginn(monkeypatch):
    manager, writes, _ravens, _cli = _load_writes_module()
    try:
        _install_ravens(monkeypatch)
        home = get_hermes_home().resolve()
        ctx = _Ctx({"bifrost_ingestion_enabled": True})
        result = writes.ingest_memory(
            ctx,
            "The longhouse fire was lit at dusk.",
            category="scene",
            importance=8,
            tags=["hearth"],
            emotional_valence=0.25,
        )
    finally:
        manager.unload()
    assert result.healthy is True
    assert result.detail == {"memory_id": 7}
    assert len(_HuginnMemory.instances) == 1
    memory = _HuginnMemory.instances[0]
    assert memory.config.backend == "local"
    assert memory.config.local_db_path == str(home / "memory" / "huginn_local.db")
    assert memory.upserts == [
        {
            "content": "The longhouse fire was lit at dusk.",
            "category": "scene",
            "importance": 8,
            "tags": ["hearth"],
            "emotional_valence": 0.25,
        }
    ]
    assert memory.closed is True
    assert _HebbianMemory.instances == []


def test_enabled_operations_report_package_missing(monkeypatch):
    manager, writes, _ravens, _cli = _load_writes_module()
    try:
        _remove_ravens(monkeypatch)
        ctx = _Ctx(
            {
                "bifrost_reinforcement_enabled": True,
                "bifrost_ingestion_enabled": True,
            }
        )
        assert writes.reinforce_memories(ctx, [1]).status == "package_missing"
        assert writes.ingest_memory(ctx, "text").status == "package_missing"
    finally:
        manager.unload()


def test_validation_refuses_before_construction(monkeypatch):
    manager, writes, _ravens, _cli = _load_writes_module()
    try:
        _install_ravens(monkeypatch)
        ctx = _Ctx(
            {
                "bifrost_reinforcement_enabled": True,
                "bifrost_decay_enabled": True,
                "bifrost_ingestion_enabled": True,
            }
        )
        assert writes.reinforce_memories(ctx, []).status == "validation_error"
        assert writes.reinforce_memories(ctx, [0]).status == "validation_error"
        assert writes.reinforce_memories(ctx, [True]).status == "validation_error"
        assert writes.reinforce_memories(ctx, ["x"]).status == "validation_error"
        assert (
            writes.reinforce_memories(ctx, [1], emotional_valence=2.0).status
            == "validation_error"
        )
        assert writes.decay_memories(ctx, 0).status == "validation_error"
        assert writes.decay_memories(ctx, "soon").status == "validation_error"
        assert writes.ingest_memory(ctx, "  ").status == "validation_error"
        assert (
            writes.ingest_memory(ctx, "text", importance=99).status
            == "validation_error"
        )
        assert (
            writes.ingest_memory(ctx, "text", tags="oops").status
            == "validation_error"
        )
    finally:
        manager.unload()
    assert _HebbianMemory.instances == []
    assert _HuginnMemory.instances == []


def test_profile_escaping_store_path_is_a_configuration_error(monkeypatch):
    manager, writes, _ravens, _cli = _load_writes_module()
    try:
        _install_ravens(monkeypatch)
        ctx = _Ctx(
            {
                "bifrost_ingestion_enabled": True,
                "bifrost_huginn_db_path": "../escape.db",
            }
        )
        result = writes.ingest_memory(ctx, "text")
    finally:
        manager.unload()
    assert result.status == "configuration_error"
    assert _HuginnMemory.instances == []


def test_read_probes_construct_nothing_with_all_flags_enabled(monkeypatch):
    manager, _writes, ravens, _cli = _load_writes_module()
    try:
        _install_ravens(monkeypatch)
        fabric = importlib.import_module(f"{ravens.__package__}.memory_fabric")
        ctx = _Ctx(
            {
                "bifrost_reinforcement_enabled": True,
                "bifrost_decay_enabled": True,
                "bifrost_consolidation_enabled": True,
                "bifrost_ingestion_enabled": True,
            }
        )
        assert ravens.probe_ravens(ctx).healthy is True
        assert fabric.probe_bifrost_muninn(ctx).status in {
            "package_missing",
            "unavailable_at_path",
            "storage_missing",
        }
    finally:
        manager.unload()
    assert _HebbianMemory.instances == []
    assert _HuginnMemory.instances == []


def _run_cli(manager, argv) -> int:
    command = manager._cli_commands["volmarr"]
    parser = argparse.ArgumentParser()
    command["setup_fn"](parser)
    args = parser.parse_args(argv)
    return command["handler_fn"](args)


def test_cli_decay_disabled_by_default_exits_nonzero(monkeypatch, capsys):
    manager, _writes, _ravens, _cli = _load_writes_module()
    try:
        _install_ravens(monkeypatch)
        code = _run_cli(manager, ["memory", "ravens", "decay", "--json"])
    finally:
        manager.unload()
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "disabled"
    assert payload["operation"] == "decay"
    assert _HebbianMemory.instances == []


def test_cli_ingest_enabled_writes_through_the_flag(monkeypatch, capsys):
    manager, _writes, _ravens, _cli = _load_writes_module(
        settings="        bifrost_ingestion_enabled: true\n"
    )
    try:
        _install_ravens(monkeypatch)
        code = _run_cli(
            manager,
            [
                "memory",
                "ravens",
                "ingest",
                "--content",
                "A raven landed on the roof-tree.",
                "--category",
                "omen",
                "--importance",
                "6",
                "--tags",
                "raven,roof",
                "--json",
            ],
        )
    finally:
        manager.unload()
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["detail"] == {"memory_id": 7}
    assert _HuginnMemory.instances[0].upserts[0]["tags"] == ["raven", "roof"]
