"""Contracts for the intrinsic-motivation drive store (Slice 91).

Emergent Agency Phase 2 (roadmap §9): a durable ``entity/motivation.yaml``
store on the Phase 0 ``DriveState`` contract — deterministic decay and
signal deltas, a bounded deduplicated intent-proposal funnel (proposals
only, never goals), rejected-proposal cooldown, anti-runaway forbidden
drives, restart persistence, and A->B->A profile isolation. Tests load
the module through real plugin discovery with a minimal config stub.
"""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone

import pytest
import yaml

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)

TS = "2026-10-30T12:00:00Z"
T0 = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)


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
            importlib.import_module(f"{package}.drives"),
            importlib.import_module(f"{package}.agency_contracts"),
        )
    except Exception:
        manager.unload()
        raise


def _store(mod, config=None):
    store = mod.DriveStore(_Ctx(config))
    data = store.ensure()
    return store, data["owner_entity_id"]


def _drive(contracts, owner, drive_id, baseline, activation, satisfaction, updated_at=TS, cooldown_until=""):
    return contracts.DriveState(
        drive_id=drive_id, owner_entity_id=owner, enabled=True,
        baseline=baseline, activation=activation, satisfaction=satisfaction,
        source=contracts.Provenance(source_type="system_observation", source_id="pytest"),
        updated_at=updated_at, cooldown_until=cooldown_until,
    )


def _prov(contracts, source_type="goal"):
    return contracts.Provenance(source_type=source_type, source_id="pytest")


def test_create_once_seeds_starter_drives_byte_stable():
    home = get_hermes_home()
    manager, mod, _c = _load_modules()
    try:
        manager.invoke_hook("on_session_start", session_id="one", model="model-a")
        identity = yaml.safe_load((home / "entity" / "entity.yaml").read_text("utf-8"))
        path = home / "entity" / "motivation.yaml"
        first = path.read_bytes()
        manager.invoke_hook("on_session_start", session_id="two", model="model-b")
    finally:
        manager.unload()
    payload = yaml.safe_load(first)
    assert payload["motivation_version"] == 1
    assert payload["owner_entity_id"] == identity["entity_id"]
    assert set(payload["drives"]) == {d for d, _b in mod.STARTER_DRIVES}
    assert path.read_bytes() == first


def test_decay_is_deterministic_toward_baseline():
    _m, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        store.set_drive(_drive(contracts, owner, "curiosity", 0.5, 0.9, 0.8))
        decayed = {s.drive_id: s for s in store.decay(now=T0 + timedelta(hours=10))}
        again = {s.drive_id: s for s in mod.DriveStore(_Ctx()).decay(now=T0 + timedelta(hours=10))}
    finally:
        _m.unload()
    assert decayed["curiosity"].activation == 0.7
    assert decayed["curiosity"].satisfaction == 0.7
    assert again["curiosity"] == decayed["curiosity"]


def test_satisfy_signal_deltas_and_cooldown_suppresses_proposals():
    _m, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        store.set_drive(_drive(contracts, owner, "curiosity", 0.55, 0.9, 0.1))
        assert [p["drive"] for p in store.proposals(now=T0)] == ["curiosity"]
        satisfied = store.record_signal("curiosity", "satisfy", source=_prov(contracts), now=T0)
        assert satisfied.activation == 0.75
        assert satisfied.satisfaction == 0.3
        assert satisfied.cooldown_until != ""
        assert store.proposals(now=T0 + timedelta(hours=1)) == []
        with pytest.raises(mod.DriveError):
            store.record_signal("curiosity", "explode", source=_prov(contracts), now=T0)
        with pytest.raises(mod.DriveError):
            store.record_signal("missing", "tension", source=_prov(contracts), now=T0)
    finally:
        _m.unload()


def test_proposals_bounded_deduped_deterministic_and_create_no_goals():
    home = get_hermes_home()
    _m, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        for drive_id, _b in mod.STARTER_DRIVES:
            store.set_drive(_drive(contracts, owner, drive_id, 0.9, 1.0, 0.0))
        first = store.proposals(now=T0)
        second = store.proposals(now=T0)
    finally:
        _m.unload()
    assert first == second  # deterministic scoring for identical inputs
    assert len(first) == mod.MAX_PROPOSALS
    assert len({p["drive"] for p in first}) == len(first)  # one per drive
    assert all(p["origin"] == "intrinsic" and p["risk"] == "read_only" for p in first)
    # The funnel stops at proposals: no goal ledger is created or promoted.
    assert not (home / "entity" / "goals.yaml").exists()


def test_rejected_proposal_suppressed_and_cooled_down():
    _m, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        store.set_drive(_drive(contracts, owner, "creation", 0.5, 1.0, 0.0))
        proposals = store.proposals(now=T0)
        assert [p["drive"] for p in proposals] == ["creation"]
        store.record_rejection("creation", proposals[0]["proposal"], now=T0)
        state = {s.drive_id: s for s in store.drives()}["creation"]
        assert state.cooldown_until != ""
        # Even after cooldown, the identical rejected proposal stays suppressed.
        assert store.proposals(now=T0 + timedelta(days=30)) == []
    finally:
        _m.unload()


def test_forbidden_autonomy_escalation_drives_are_refused():
    _m, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        for forbidden in ("authority", "permissions", "praise", "money", "compute"):
            with pytest.raises(mod.DriveError):
                store.set_drive(_drive(contracts, owner, forbidden, 0.5, 0.5, 0.5))
    finally:
        _m.unload()


def test_wrong_owner_malformed_and_symlink_are_refused():
    home = get_hermes_home()
    _m, mod, _c = _load_modules()
    try:
        store, _owner = _store(mod)
        path = home / "entity" / "motivation.yaml"
        wrong = (
            "motivation_version: 1\n"
            "owner_entity_id: 00000000-0000-4000-8000-000000000000\n"
            f"updated_at: '{TS}'\n"
            "drives: {}\nrejected: {}\n"
        ).encode()
        path.write_bytes(wrong)
        with pytest.raises(mod.DriveError):
            store.drives()
        assert path.read_bytes() == wrong
        path.write_text("motivation_version: 99\n", encoding="utf-8")
        with pytest.raises(mod.DriveError):
            store.drives()
        target = home / "entity" / "target.yaml"
        target.write_bytes(wrong)
        path.unlink()
        path.symlink_to(target)
        with pytest.raises(mod.DriveError):
            store.drives()
    finally:
        _m.unload()


def test_restart_persistence_and_a_b_a_profile_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    _m, mod, contracts = _load_modules()
    try:
        store_a, owner_a = _store(mod)
        store_a.record_signal("curiosity", "tension", source=_prov(contracts), now=T0)
        reloaded = {s.drive_id: s for s in mod.DriveStore(_Ctx()).drives()}
        assert reloaded["curiosity"].activation == 0.65
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            store_b, owner_b = _store(mod)
            assert {s.drive_id for s in store_b.drives()} == {d for d, _b in mod.STARTER_DRIVES}
            store_b.record_signal("curiosity", "satisfy", source=_prov(contracts), now=T0)
        finally:
            reset_hermes_home_override(token)
        restored = {s.drive_id: s for s in mod.DriveStore(_Ctx()).drives()}
    finally:
        _m.unload()
    assert owner_a != owner_b
    assert restored["curiosity"].activation == 0.65


def test_packet_top_three_and_disabled_or_missing_fails_open():
    _m, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        # No affective layer and no world service configured: packet is stable.
        assert mod.DriveBridge(_Ctx()).packet_items("s1") == []  # all tensions below threshold
        for drive_id, _b in mod.STARTER_DRIVES:
            store.set_drive(_drive(contracts, owner, drive_id, 0.9, 1.0, 0.0))
        items = mod.DriveBridge(_Ctx()).packet_items("s1")
        assert len(items) == 3
        assert all(item.section == "current_state" and item.source == "motivation" for item in items)
        disabled = mod.DriveBridge(_Ctx({"motivation_enabled": False}))
        disabled.on_session_start(session_id="one")
        assert disabled.packet_items("s1") == []
    finally:
        _m.unload()
