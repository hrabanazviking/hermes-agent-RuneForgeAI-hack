"""Contracts for the five-layer persistent self-model (Slice 103).

Self-Aware Agency roadmap §5: the layered view (objective, narrative,
ideal, relational, experiential) is assembled deterministically and
read-only over the existing claims store, goals ledger, relationships
ledger, and heartbeat probe. Cross-layer disagreement surfaces as
structured discrepancies; unreadable sources degrade to an empty
layer plus a discrepancy, never to invented content. The module owns
no writes. Tests load through real plugin discovery.
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

ENABLED = {"layered_self_model_enabled": True}
TS = "2026-10-31T12:00:00Z"
OTHER = "11111111-1111-4111-8111-111111111111"


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
            importlib.import_module(f"{package}.self_model_layers"),
            importlib.import_module(f"{package}.self_model"),
            importlib.import_module(f"{package}.agency_contracts"),
            importlib.import_module(f"{package}.goals"),
            importlib.import_module(f"{package}.relationships"),
            importlib.import_module(f"{package}.heartbeat"),
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
    _m, layers, self_model, contracts, goals, relationships, heartbeat = mods
    ctx = _Ctx(config)
    store = self_model.SelfModelStore(ctx)
    owner = store.ensure()["owner_entity_id"]
    goals.GoalStore(ctx).ensure()
    relationships.RelationshipStore(ctx).ensure()
    heartbeat.HeartbeatStore(ctx).ensure()
    return layers.LayeredSelfModelService(ctx), store, owner, ctx


def _seed(mods, store, owner):
    _m, _layers, _sm, contracts, _g, _r, _h = mods
    store.propose(_claim(contracts, owner, "identity", "core", "A persistent entity.", 0.9, "identity"))
    store.propose(_claim(contracts, owner, "capability", "coding", "Codes well.", 0.9, "tool_result"))
    store.propose(_claim(contracts, owner, "capability", "guesswork", "Guesses.", 0.9, "curiosity"))
    store.propose(_claim(contracts, owner, "limitation", "no_network", "No network access.", 0.8, "tool_result"))
    store.propose(_claim(contracts, owner, "preference", "plain_speech", "Prefers plain speech.", 0.7, "user_explicit"))
    store.propose(_claim(contracts, owner, "commitment", "keep_oaths", "Keeps oaths.", 0.85, "user_explicit"))
    store.propose(_claim(contracts, owner, "uncertainty", "uptime", "Unsure of uptime.", 0.2, "reflection"))


def test_disabled_by_default():
    mods = _load_modules()
    layers = mods[1]
    try:
        service, _store, _owner, _ctx = _setup(mods)
        with pytest.raises(layers.LayeredSelfModelError):
            service.snapshot()
        assert layers.LayeredSelfModelBridge(_Ctx()).packet_items("s1") == []
    finally:
        mods[0].unload()


def test_layers_are_the_five_section5_layers_in_order():
    mods = _load_modules()
    try:
        service, _store, _owner, _ctx = _setup(mods, ENABLED)
        snap = service.snapshot()
    finally:
        mods[0].unload()
    assert mods[1].LayeredSelfModelService.layers() == (
        "objective", "narrative", "ideal", "relational", "experiential",
    )
    for name in mods[1].LayeredSelfModelService.layers():
        assert name in snap
    assert snap["layers_version"] == 1
    assert snap["objective"]["home_runtime"] == "hermes"


def test_objective_layer_counts_and_verified_capabilities():
    mods = _load_modules()
    try:
        service, store, owner, ctx = _setup(mods, ENABLED)
        _seed(mods, store, owner)
        mods[4].GoalStore(ctx).create(
            title="Ship it", description="d", priority=1, next_action="work"
        )
        mods[5].RelationshipStore(ctx).upsert(
            entity_id=OTHER, display_name="Volmarr", relationship_type="principal",
            status="active", trust=0.9, note="",
        )
        snap = service.snapshot()
    finally:
        mods[0].unload()
    objective = snap["objective"]
    assert objective["entity_id"] == owner
    assert objective["claim_count"] == 7
    assert objective["current_goal_count"] == 1
    assert objective["relationship_count"] == 1
    # Only the strong-evidence capability is verified; the weak-evidence
    # (curiosity) capability claim is a belief, not an objective fact.
    assert objective["verified_capabilities"] == ["coding"]
    assert snap["relational"]["summaries"][0]["display_name"] == "Volmarr"
    assert snap["relational"]["summaries"][0]["trust"] == 0.9


def test_narrative_ideal_limitations_and_assumptions():
    mods = _load_modules()
    try:
        service, store, owner, _ctx = _setup(mods, ENABLED)
        _seed(mods, store, owner)
        snap = service.snapshot()
    finally:
        mods[0].unload()
    assert snap["narrative"]["summary"] == "A persistent entity."
    assert snap["ideal"]["traits"] == ["Prefers plain speech."]
    assert snap["ideal"]["principles"] == ["Keeps oaths."]
    assert snap["ideal"]["capabilities"] == ["no_network"]
    assert snap["known_limitations"] == ["No network access."]
    assert snap["growth_targets"] == ["no_network"]
    assumptions = {(a["domain"], a["key"]) for a in snap["active_assumptions"]}
    assert ("capability", "guesswork") in assumptions  # weak-capped at 0.35
    assert ("uncertainty", "uptime") in assumptions


def test_experiential_layer_from_goals_and_uncertainty():
    mods = _load_modules()
    try:
        service, store, owner, ctx = _setup(mods, ENABLED)
        _seed(mods, store, owner)
        goal_store = mods[4].GoalStore(ctx)
        goal = goal_store.create(
            title="Active work", description="d", priority=1, next_action="work"
        )
        goal_store.update(goal["goal_id"], {"status": "active"}, "go")
        blocked = goal_store.create(
            title="Stuck work", description="d", priority=2, next_action=""
        )
        goal_store.update(blocked["goal_id"], {"status": "blocked"}, "halt")
        snap = service.snapshot()
    finally:
        mods[0].unload()
    experiential = snap["experiential"]
    assert experiential["attention"] == "Active work"
    assert experiential["active_goal_ids"] == [goal["goal_id"]]
    assert experiential["blocked"] is True
    assert experiential["load"] == 0.5
    assert experiential["uncertainty"] == 0.8  # 1 - 0.2 confidence
    kinds = {item["kind"] for item in snap["discrepancies"]}
    assert "blocked_goal_without_next_action" in kinds
    assert "high_uncertainty" in kinds


def test_contradictions_and_health_discrepancies_are_explicit():
    mods = _load_modules()
    layers, contracts = mods[1], mods[3]
    try:
        service, store, owner, ctx = _setup(mods, ENABLED)
        _seed(mods, store, owner)
        # Weak evidence restating a claim records a contradiction.
        store.propose(
            _claim(contracts, owner, "capability", "coding", "Codes poorly.", 0.9, "curiosity")
        )
        snap = service.snapshot()
    finally:
        mods[0].unload()
    assert snap["unresolved_contradictions"][0]["key"] == "coding"
    assert snap["unresolved_contradictions"][0]["count"] == 1
    kinds = {item["kind"] for item in snap["discrepancies"]}
    assert "contradicted_claim" in kinds
    # No heartbeat pulse yet -> not healthy, and coding is high-confidence.
    assert snap["objective"]["heartbeat_healthy"] is False
    assert "capability_claim_vs_health" in kinds


def test_healthy_heartbeat_clears_health_discrepancy():
    mods = _load_modules()
    try:
        service, store, owner, ctx = _setup(mods, ENABLED)
        _seed(mods, store, owner)
        mods[6].HeartbeatStore(ctx).pulse("manual")
        snap = service.snapshot()
    finally:
        mods[0].unload()
    assert snap["objective"]["heartbeat_status"] == "healthy"
    assert snap["objective"]["heartbeat_healthy"] is True
    assert "capability_claim_vs_health" not in {
        item["kind"] for item in snap["discrepancies"]
    }


def test_snapshot_is_read_only_over_source_stores():
    home = get_hermes_home()
    mods = _load_modules()
    try:
        service, store, owner, ctx = _setup(mods, ENABLED)
        _seed(mods, store, owner)
        paths = [
            home / "entity" / "self_model.yaml",
            home / "entity" / "goals.yaml",
            home / "entity" / "relationships.yaml",
        ]
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        service.snapshot()
        mods[1].LayeredSelfModelBridge(ctx).packet_items("s1")
        after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    finally:
        mods[0].unload()
    assert before == after


def test_packet_content_bearing_only_and_a_b_a_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    layers = mods[1]
    try:
        service, store, owner, ctx = _setup(mods, ENABLED)
        empty_items = layers.LayeredSelfModelBridge(ctx).packet_items("s1")
        _seed(mods, store, owner)
        items = layers.LayeredSelfModelBridge(ctx).packet_items("s1")
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            service_b, _store_b, _owner_b, ctx_b = _setup(mods, ENABLED)
            snap_b = service_b.snapshot()
            items_b = layers.LayeredSelfModelBridge(ctx_b).packet_items("s1")
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert empty_items == []
    assert len(items) == 1
    assert items[0].source == "self_model_layers"
    assert "identity:" in items[0].content
    assert snap_b["objective"]["claim_count"] == 0
    assert snap_b["narrative"]["summary"] == ""
    assert items_b == []
