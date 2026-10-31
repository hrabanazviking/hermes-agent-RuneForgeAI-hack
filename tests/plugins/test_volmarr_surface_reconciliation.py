"""Contracts for the §§19-21 surface reconciliation (Slice 117).

Self-Aware Agency roadmap §§19-21 proposed a repository layout,
configuration keys, and a ``hermes volmarr`` CLI surface that the
domain slices (§§5-18) did not always land under the proposed
names. The reconciliation tables classify every proposed item
exact / equivalent / missing / deferred — no proposed name is
recreated as a shim — and the one genuine gap, §21's operator
inspection commands, stands as a read-only, LLM-free inspection
service wired into the CLI. Tests load through real plugin
discovery.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path

import pytest

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)

ENABLED = {"awareness_enabled": True}


class _Ctx:
    def __init__(self, config=None):
        self._config = dict(config or {})

    def get_config(self, key, default=None):
        return self._config.get(key, default)


def _write_profile(home) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [volmarr-core]\n", encoding="utf-8"
    )


def _load_modules():
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    _write_profile(home)
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-core"]
        package = loaded.module.__package__
        return (
            manager,
            importlib.import_module(f"{package}.surface_reconciliation"),
            importlib.import_module(f"{package}.identity"),
            importlib.import_module(f"{package}.self_model"),
            importlib.import_module(f"{package}.awareness"),
            importlib.import_module(f"{package}.metacognition"),
            importlib.import_module(f"{package}.drives"),
            importlib.import_module(f"{package}.curiosity"),
            importlib.import_module(f"{package}.autonomy"),
        )
    except Exception:
        manager.unload()
        raise


def _ensure_stores(mods, config=None):
    ctx = _Ctx(config)
    mods[2].IdentityStore(ctx).ensure()
    mods[3].SelfModelStore(ctx).ensure()
    mods[4].AwarenessStore(ctx).ensure()
    mods[5].MetacognitionStore(ctx).ensure()
    mods[6].DriveStore(ctx).ensure()
    mods[7].CuriosityStore(ctx).ensure()
    mods[8].AutonomyStore(ctx).ensure()
    return ctx


def _entity_hashes(home: Path) -> dict[str, str]:
    entity = home / "entity"
    return {
        str(path.relative_to(home)):
            hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(entity.rglob("*")) if path.is_file()
    }


def test_reconciliation_tables_cover_every_proposal():
    mods = _load_modules()
    rec = mods[1]
    try:
        summary = rec.reconciliation_summary()
    finally:
        mods[0].unload()
    # §19: ten proposed modules, eleven proposed state files.
    assert summary["repository"] == {"exact": 7, "equivalent": 3}
    assert summary["state_files"] == {"exact": 10, "equivalent": 1}
    # §20: fourteen proposed keys; one honestly missing.
    assert summary["configuration"] == {
        "exact": 9, "equivalent": 4, "missing": 1}
    missing = [row for row in rec.configuration_additions()
               if row["status"] == "missing"]
    assert [row["proposed"] for row in missing] == [
        "reflection_local_first"]
    # §21: nineteen proposed commands.
    assert summary["cli"] == {
        "implemented": 9, "exact": 1, "deferred": 9}
    # Equivalent items always name what they stand as; a missing
    # or deferred item always names why, never a shim target.
    for row in rec.repository_additions() + rec.state_files():
        if row["status"] == "equivalent":
            assert row["stands_as"]
    for row in rec.cli_commands():
        assert row["stands_as"]


def test_inspection_statuses_on_a_fresh_profile():
    mods = _load_modules()
    rec = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        report = rec.SurfaceInspectionService(_Ctx()).inspect_all()
    finally:
        mods[0].unload()
    # Enabled-by-default stores are not_created until seeded;
    # the opt-in awareness layer reports disabled.
    assert report["self"]["status"] == "not_created"
    assert report["reflection"]["status"] == "not_created"
    assert report["motivation"]["status"] == "not_created"
    assert report["curiosity"]["status"] == "not_created"
    assert report["autonomy"]["status"] == "not_created"
    assert report["awareness"]["status"] == "disabled"
    assert report["awareness"]["enabled"] is False


def test_inspection_reads_seeded_surfaces():
    mods = _load_modules()
    rec = mods[1]
    try:
        ctx = _ensure_stores(mods, ENABLED)
        service = rec.SurfaceInspectionService(ctx)
        report = service.inspect_all()
    finally:
        mods[0].unload()
    assert {name: row["status"] for name, row in report.items()} == {
        name: "ok" for name in rec.SURFACES}
    assert report["self"]["detail"]["claims"] == 0
    assert report["motivation"]["detail"]["drives"] == 8
    assert report["motivation"]["detail"]["enabled_drives"] == 8
    assert report["curiosity"]["detail"]["questions"] == 0
    assert report["autonomy"]["detail"]["mode"] == "observe"
    assert report["autonomy"]["detail"]["circuit_breaker_tripped"] \
        is False
    assert report["reflection"]["detail"]["total_reflections"] == 0
    assert report["awareness"]["detail"]["current_goals"] == 0


def test_inspection_is_read_only_and_unknown_surface():
    mods = _load_modules()
    rec = mods[1]
    try:
        ctx = _ensure_stores(mods, ENABLED)
        home = get_hermes_home()
        before = _entity_hashes(home)
        service = rec.SurfaceInspectionService(ctx)
        service.inspect_all()
        unknown = service.inspect("bogus")
        after = _entity_hashes(home)
    finally:
        mods[0].unload()
    assert before == after
    assert unknown["status"] == "unknown_surface"


def test_cli_motivation_show_and_self_health(capsys):
    mods = _load_modules()
    manager = mods[0]
    try:
        _ensure_stores(mods)
        command = manager._cli_commands["volmarr"]
        parser = argparse.ArgumentParser()
        command["setup_fn"](parser)
        args = parser.parse_args(["motivation", "show", "--json"])
        code = command["handler_fn"](args)
        shown = json.loads(capsys.readouterr().out)
        parser = argparse.ArgumentParser()
        command["setup_fn"](parser)
        args = parser.parse_args(["self", "health", "--json"])
        code_health = command["handler_fn"](args)
        health = json.loads(capsys.readouterr().out)
        parser = argparse.ArgumentParser()
        command["setup_fn"](parser)
        with pytest.raises(SystemExit) as excinfo:
            parser.parse_args(["curiosity", "bogus"])
        code_usage = excinfo.value.code
        capsys.readouterr()
    finally:
        manager.unload()
    assert code == 0
    assert shown["surface"] == "motivation"
    assert shown["status"] == "ok"
    assert shown["detail"]["drives"] == 8
    # The seeded self-model store exists, so health is ok too.
    assert code_health == 0 and health["status"] == "ok"
    assert code_usage == 2


def test_cli_health_reports_not_created(capsys):
    mods = _load_modules()
    manager = mods[0]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        command = manager._cli_commands["volmarr"]
        parser = argparse.ArgumentParser()
        command["setup_fn"](parser)
        args = parser.parse_args(["autonomy", "show", "--json"])
        code = command["handler_fn"](args)
        payload = json.loads(capsys.readouterr().out)
    finally:
        manager.unload()
    assert payload["status"] == "not_created"
    # A show command displays an uncreated surface without failing.
    assert code == 0


def test_profile_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    rec = mods[1]
    try:
        ctx = _ensure_stores(mods, ENABLED)
        assert rec.SurfaceInspectionService(ctx).inspect(
            "motivation")["status"] == "ok"
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            mods[2].IdentityStore(_Ctx()).ensure()
            report_b = rec.SurfaceInspectionService(
                _Ctx(ENABLED)).inspect_all()
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert report_b["motivation"]["status"] == "not_created"
    assert report_b["autonomy"]["status"] == "not_created"
