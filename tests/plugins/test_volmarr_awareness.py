"""Contracts for the self-awareness layer (Slice 104).

Self-Aware Agency roadmap §6: one bounded, replaceable current
snapshot (attention, load, uncertainty, active goals, salient state)
built on the Slice 103 layered self-model and its discrepancy list.
Reflection is recommended only on named §6.5 triggers — never as
constant rumination. The snapshot survives restart as current state;
refresh replaces it. Tests load through real plugin discovery.
"""

from __future__ import annotations

import hashlib
import importlib
import uuid

import pytest

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)

ENABLED = {"layered_self_model_enabled": True, "awareness_enabled": True}
TS = "2026-10-31T12:00:00Z"
TS2 = "2026-10-31T13:00:00Z"


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
            importlib.import_module(f"{package}.awareness"),
            importlib.import_module(f"{package}.self_model"),
            importlib.import_module(f"{package}.agency_contracts"),
            importlib.import_module(f"{package}.goals"),
            importlib.import_module(f"{package}.heartbeat"),
            importlib.import_module(f"{package}.relationships"),
        )
    except Exception:
        manager.unload()
        raise


def _claim(contracts, owner, domain, key, statement, confidence, source_type):
    return contracts.SelfClaim(
        claim_id=str(uuid.uuid4()),
        owner_entity_id=owner,
        domain=domain,
        key=key,
        statement=statement,
        confidence=confidence,
        source=contracts.Provenance(source_type=source_type, source_id="pytest"),
        first_seen_at=TS,
    )


def _setup(mods, config=None):
    _m, awareness, self_model, _c, goals, heartbeat, relationships = mods
    ctx = _Ctx(config)
    store = self_model.SelfModelStore(ctx)
    owner = store.ensure()["owner_entity_id"]
    goals.GoalStore(ctx).ensure()
    heartbeat.HeartbeatStore(ctx).ensure()
    relationships.RelationshipStore(ctx).ensure()
    return awareness.AwarenessStore(ctx), store, owner, ctx


def _seed_rich(mods, store, owner, ctx):
    _m, _a, _sm, contracts, goals, heartbeat, _r = mods
    store.propose(_claim(contracts, owner, "identity", "core", "A persistent entity.", 0.9, "identity"))
    store.propose(_claim(contracts, owner, "capability", "coding", "Codes well.", 0.9, "tool_result"))
    store.propose(_claim(contracts, owner, "uncertainty", "uptime", "Unsure of uptime.", 0.2, "reflection"))
    goal_store = goals.GoalStore(ctx)
    active = goal_store.create(title="Active work", description="d", priority=1, next_action="work")
    goal_store.update(active["goal_id"], {"status": "active"}, "go")
    blocked = goal_store.create(title="Stuck work", description="d", priority=2, next_action="")
    goal_store.update(blocked["goal_id"], {"status": "blocked"}, "halt")
    return active


def test_disabled_by_default():
    mods = _load_modules()
    awareness = mods[1]
    try:
        store, _sm, _owner, _ctx = _setup(mods)
        with pytest.raises(awareness.AwarenessError):
            store.refresh()
        assert awareness.AwarenessBridge(_Ctx()).packet_items("s1") == []
    finally:
        mods[0].unload()


def test_refresh_builds_snapshot_from_layered_model():
    mods = _load_modules()
    try:
        store, claims, owner, ctx = _setup(mods, ENABLED)
        active = _seed_rich(mods, claims, owner, ctx)
        snap = store.refresh(now=TS)
    finally:
        mods[0].unload()
    assert snap["awareness_version"] == 1
    assert snap["owner_entity_id"] == owner
    assert snap["observed_at"] == TS
    assert snap["attention_target"] == "Active work"
    assert snap["current_goal_ids"] == [active["goal_id"]]
    assert snap["cognitive_load"] == 0.5
    assert snap["uncertainty"] == 0.8
    assert snap["salient_discrepancies"]  # blocked goal / health / uncertainty
    assert any("uptime" in spot for spot in snap["known_blind_spots"])


def test_snapshot_survives_restart_as_current_state():
    mods = _load_modules()
    awareness = mods[1]
    try:
        store, claims, owner, ctx = _setup(mods, ENABLED)
        _seed_rich(mods, claims, owner, ctx)
        written = store.refresh(now=TS)
        reread = awareness.AwarenessStore(ctx).read()
        ensured = awareness.AwarenessStore(ctx).ensure()
    finally:
        mods[0].unload()
    assert reread == written
    assert ensured == written  # ensure never replaces an existing snapshot


def test_refresh_is_replaceable_and_bounded():
    mods = _load_modules()
    try:
        store, claims, owner, ctx = _setup(mods, ENABLED)
        _seed_rich(mods, claims, owner, ctx)
        first = store.refresh(now=TS)
        mods[5].HeartbeatStore(ctx).pulse("manual")
        second = store.refresh(now=TS2)
    finally:
        mods[0].unload()
    assert first["observed_at"] == TS
    assert second["observed_at"] == TS2
    assert len(second["salient_discrepancies"]) <= 5
    assert len(second["known_blind_spots"]) <= 5
    assert len(second["current_goal_ids"]) <= 10
    # The healthy heartbeat cleared the capability-vs-health discrepancy.
    assert len(second["salient_discrepancies"]) < len(first["salient_discrepancies"])


def test_reflection_recommended_only_on_named_triggers():
    mods = _load_modules()
    try:
        store, claims, owner, ctx = _setup(mods, ENABLED)
        _seed_rich(mods, claims, owner, ctx)
        snap = store.refresh(now=TS)
    finally:
        mods[0].unload()
    assert snap["reflection_recommended"] is True
    assert "blocked_goal" in snap["reflection_triggers"]
    assert "high_uncertainty" in snap["reflection_triggers"]
    assert "salient_discrepancy" in snap["reflection_triggers"]


def test_clean_state_recommends_no_reflection():
    mods = _load_modules()
    try:
        store, claims, owner, ctx = _setup(mods, ENABLED)
        contracts = mods[3]
        claims.propose(_claim(contracts, owner, "identity", "core", "A persistent entity.", 0.9, "identity"))
        claims.propose(_claim(contracts, owner, "uncertainty", "uptime", "Sure of uptime.", 0.9, "tool_result"))
        mods[5].HeartbeatStore(ctx).pulse("manual")
        snap = store.refresh(now=TS)
    finally:
        mods[0].unload()
    assert snap["salient_discrepancies"] == []
    assert snap["reflection_triggers"] == []
    assert snap["reflection_recommended"] is False
    assert snap["uncertainty"] == pytest.approx(0.1)


def test_contradiction_trigger_is_named():
    mods = _load_modules()
    try:
        store, claims, owner, ctx = _setup(mods, ENABLED)
        contracts = mods[3]
        claims.propose(_claim(contracts, owner, "capability", "coding", "Codes well.", 0.9, "tool_result"))
        claims.propose(_claim(contracts, owner, "capability", "coding", "Codes poorly.", 0.9, "curiosity"))
        snap = store.refresh(now=TS)
    finally:
        mods[0].unload()
    assert "unresolved_contradiction" in snap["reflection_triggers"]
    assert snap["reflection_recommended"] is True


def test_refresh_writes_only_the_awareness_file():
    home = get_hermes_home()
    mods = _load_modules()
    try:
        store, claims, owner, ctx = _setup(mods, ENABLED)
        _seed_rich(mods, claims, owner, ctx)
        paths = [
            home / "entity" / "self_model.yaml",
            home / "entity" / "goals.yaml",
        ]
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        store.refresh(now=TS)
        after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        assert (home / "entity" / "awareness.json").is_file()
    finally:
        mods[0].unload()
    assert before == after


def test_symlinked_snapshot_is_refused(tmp_path):
    mods = _load_modules()
    awareness = mods[1]
    try:
        store, claims, owner, ctx = _setup(mods, ENABLED)
        _seed_rich(mods, claims, owner, ctx)
        store.refresh(now=TS)
        path = store.path()
        target = tmp_path / "elsewhere.json"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
        with pytest.raises(awareness.AwarenessError):
            store.read()
        with pytest.raises(awareness.AwarenessError):
            store.refresh(now=TS2)
    finally:
        mods[0].unload()


def test_packet_content_bearing_only_and_a_b_a_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    awareness = mods[1]
    try:
        store, claims, owner, ctx = _setup(mods, ENABLED)
        assert awareness.AwarenessBridge(ctx).packet_items("s1") == []
        _seed_rich(mods, claims, owner, ctx)
        store.refresh(now=TS)
        items = awareness.AwarenessBridge(ctx).packet_items("s1")
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            store_b, _c, _o, ctx_b = _setup(mods, ENABLED)
            store_b.ensure()
            items_b = awareness.AwarenessBridge(ctx_b).packet_items("s1")
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert len(items) == 1
    assert items[0].source == "awareness"
    assert "attention: Active work" in items[0].content
    assert items_b == []  # profile B's neutral snapshot bears no content
