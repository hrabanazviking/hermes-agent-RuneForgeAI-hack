"""Contracts for the multi-timescale cognition registry (Slice 102).

Emergent Agency Phase 12 (roadmap §19): the five timescales (reflex,
frequent continuity, agency, daily sleep, weekly/long-horizon) are
defined and registered against the existing heartbeat/agency/
consolidation routines rather than any new scheduler. Reflex is
turn-scoped and has no cron run; the other four map to Hermes-cron
schedules. The registry records explicit run receipts in a bounded
log and reports due status deterministically; recording executes
nothing. Tests load the module through real plugin discovery.
"""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone

import pytest

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)

ENABLED = {"timescales_enabled": True}
BASE = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)


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
            importlib.import_module(f"{package}.timescales"),
            importlib.import_module(f"{package}.curiosity"),
        )
    except Exception:
        manager.unload()
        raise


def _setup(mods, config=None):
    _m, ts, curiosity = mods
    ctx = _Ctx(config)
    owner = curiosity.CuriosityStore(ctx).ensure()["owner_entity_id"]
    return ts.TimescaleService(ctx), owner, ctx


def test_disabled_by_default_and_no_log_created():
    home = get_hermes_home()
    mods = _load_modules()
    try:
        service, _owner, _ctx = _setup(mods)
        with pytest.raises(mods[1].TimescaleError):
            service.record_run("frequent_continuity", now=BASE)
    finally:
        mods[0].unload()
    assert not (home / "entity" / "timescales.jsonl").exists()


def test_definitions_are_the_five_section19_timescales():
    mods = _load_modules()
    try:
        service, _owner, _ctx = _setup(mods, ENABLED)
        definitions = service.definitions()
        ids = [item.timescale_id for item in definitions]
        cadences = [item.cadence_seconds for item in definitions[1:]]
    finally:
        mods[0].unload()
    assert ids == [
        "reflex", "frequent_continuity", "agency",
        "daily_sleep", "weekly_long_horizon",
    ]
    assert definitions[0].cron_registerable is False
    assert all(item.cron_registerable for item in definitions[1:])
    assert cadences == sorted(cadences)
    assert definitions[1].generative is False  # no generative wandering


def test_cron_specs_map_to_existing_routines():
    mods = _load_modules()
    try:
        service, _owner, _ctx = _setup(mods, ENABLED)
        specs = {spec["timescale"]: spec for spec in service.cron_specs()}
    finally:
        mods[0].unload()
    assert specs["frequent_continuity"]["schedule"] == "every 10m"
    assert specs["frequent_continuity"]["backed"] is True
    assert specs["agency"]["schedule"] == "every 360m"
    assert specs["agency"]["backed"] is True
    assert specs["daily_sleep"]["schedule"] == "every 1440m"
    assert specs["daily_sleep"]["backed"] is True
    # Weekly is registered by cadence/purpose only; no routine backs it yet.
    assert specs["weekly_long_horizon"]["schedule"] == "every 10080m"
    assert specs["weekly_long_horizon"]["backed"] is False
    assert "reflex" not in specs


def test_reflex_unknown_and_invalid_outcome_refused():
    mods = _load_modules()
    ts = mods[1]
    try:
        service, _owner, _ctx = _setup(mods, ENABLED)
        with pytest.raises(ts.TimescaleError):
            service.record_run("reflex", now=BASE)
        with pytest.raises(ts.TimescaleError):
            service.record_run("hourly", now=BASE)
        with pytest.raises(ts.TimescaleError):
            service.record_run("agency", outcome="wandered", now=BASE)
        assert service.status(now=BASE)[2]["runs"] == 0
    finally:
        mods[0].unload()


def test_status_due_logic_is_deterministic():
    mods = _load_modules()
    try:
        service, _owner, _ctx = _setup(mods, ENABLED)
        before = {item["timescale_id"]: item for item in service.status(now=BASE)}
        service.record_run("frequent_continuity", summary="heartbeat cycle", now=BASE)
        fresh = {item["timescale_id"]: item for item in service.status(now=BASE + timedelta(minutes=1))}
        later = {
            item["timescale_id"]: item
            for item in service.status(now=BASE + timedelta(minutes=11))
        }
    finally:
        mods[0].unload()
    assert before["frequent_continuity"]["due"] is True
    assert before["reflex"]["due"] is None
    assert fresh["frequent_continuity"]["runs"] == 1
    assert fresh["frequent_continuity"]["due"] is False
    assert later["frequent_continuity"]["due"] is True
    assert fresh["agency"]["due"] is True  # never run


def test_blocked_outcome_is_a_recorded_run():
    mods = _load_modules()
    try:
        service, _owner, _ctx = _setup(mods, ENABLED)
        record = service.record_run(
            "daily_sleep", outcome="blocked", summary="store unreadable",
            detail={"goals_total": 3}, now=BASE,
        )
        status = {item["timescale_id"]: item for item in service.status(now=BASE)}
    finally:
        mods[0].unload()
    assert record["outcome"] == "blocked"
    assert record["detail"] == {"goals_total": 3}
    assert status["daily_sleep"]["runs"] == 1
    assert status["daily_sleep"]["last_run_at"].startswith("2026-10-31T12:00")


def test_packet_surfaces_only_when_a_cron_timescale_is_due():
    mods = _load_modules()
    ts = mods[1]
    try:
        service, _owner, ctx = _setup(mods, ENABLED)
        due_items = ts.TimescaleBridge(ctx).packet_items("s1")
        now = datetime.now(timezone.utc)
        for timescale_id in (
            "frequent_continuity", "agency", "daily_sleep", "weekly_long_horizon",
        ):
            service.record_run(timescale_id, now=now)
        settled = ts.TimescaleBridge(ctx).packet_items("s1")
    finally:
        mods[0].unload()
    assert len(due_items) == 1
    assert due_items[0].source == "timescales"
    assert "due" in due_items[0].content
    assert settled == []


def test_detail_values_are_bounded_and_typed():
    mods = _load_modules()
    ts = mods[1]
    try:
        service, _owner, _ctx = _setup(mods, ENABLED)
        with pytest.raises(ts.TimescaleError):
            service.record_run("agency", detail={"Bad Key": 1}, now=BASE)
        with pytest.raises(ts.TimescaleError):
            service.record_run("agency", detail={"ok": True}, now=BASE)
        with pytest.raises(ts.TimescaleError):
            service.record_run("agency", detail={"ok": 1.5}, now=BASE)
    finally:
        mods[0].unload()


def test_log_symlink_refusal_and_a_b_a_profile_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    ts = mods[1]
    try:
        service, _owner, ctx = _setup(mods, ENABLED)
        service.record_run("agency", now=BASE)
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            service_b, _owner_b, ctx_b = _setup(mods, ENABLED)
            assert service_b.status(now=BASE)[2]["runs"] == 0
            assert ts.TimescaleBridge(ctx_b).packet_items("s1")
        finally:
            reset_hermes_home_override(token)
        records_a = ts.TimescaleLog(ctx).records()
        path = get_hermes_home() / "entity" / "timescales.jsonl"
        target = get_hermes_home() / "entity" / "target.jsonl"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
        with pytest.raises(ts.TimescaleError):
            ts.TimescaleLog(ctx).records()
    finally:
        mods[0].unload()
    assert len(records_a) == 1
