"""Contracts for the SELF STATE context integration (Slice 111).

Self-Aware Agency roadmap §13: the context packet upgrades to
schema v2 with an explicit SELF STATE section between CURRENT
STATE and RELEVANT EPISODES, carrying at most the seven compact
§13 fields assembled deterministically and read-only from the
layered self-model (Slice 103), Phase 9 intrinsic-goal
arbitration, and the Phase 4 curiosity frontier — never a full
self-model dump. Tests load through real plugin discovery.
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

ENABLED = {"layered_self_model_enabled": True, "self_state_enabled": True}
TS = "2026-10-31T12:00:00Z"


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
            importlib.import_module(f"{package}.self_state"),
            importlib.import_module(f"{package}.self_model"),
            importlib.import_module(f"{package}.agency_contracts"),
            importlib.import_module(f"{package}.goals"),
            importlib.import_module(f"{package}.relationships"),
            importlib.import_module(f"{package}.heartbeat"),
            importlib.import_module(f"{package}.curiosity"),
            importlib.import_module(f"{package}.context_packet"),
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
    (_m, _ss, self_model, _c, goals, relationships, heartbeat,
     curiosity, _p) = mods
    ctx = _Ctx(config)
    store = self_model.SelfModelStore(ctx)
    owner = store.ensure()["owner_entity_id"]
    goals.GoalStore(ctx).ensure()
    relationships.RelationshipStore(ctx).ensure()
    heartbeat.HeartbeatStore(ctx).ensure()
    curiosity.CuriosityStore(ctx).ensure()
    return ctx, store, owner


def _seed(mods, ctx, store, owner):
    (_m, _ss, _sm, contracts, goals, _r, _h, curiosity, _p) = mods
    store.propose(_claim(contracts, owner, "identity", "core",
                         "A persistent entity.", 0.9, "identity"))
    store.propose(_claim(contracts, owner, "limitation", "no_network",
                         "No network access.", 0.8, "tool_result"))
    store.propose(_claim(contracts, owner, "uncertainty", "uptime",
                         "Unsure of uptime.", 0.2, "reflection"))
    goal_store = goals.GoalStore(ctx)
    active = goal_store.create(title="Ship the slice", description="d",
                               priority=1, next_action="work")
    goal_store.update(active["goal_id"], {"status": "active"}, "start")
    goal_store.create(title="Explore the frontier", description="d",
                      priority=5, next_action="look", origin="intrinsic",
                      origin_ref="curiosity")
    curiosity.CuriosityStore(ctx).add_question(contracts.CuriosityQuestion(
        question_id=str(uuid.uuid4()),
        owner_entity_id=owner,
        question="Why has local cognition latency increased?",
        status="open",
        novelty=0.72, uncertainty=0.81, relevance=0.77,
        expected_value=0.69, cost=0.18, risk_class=1,
        source=contracts.Provenance(source_type="curiosity", source_id="pytest"),
        created_at=TS,
    ))


def test_disabled_by_default_and_layered_required():
    mods = _load_modules()
    ss = mods[1]
    try:
        ctx, _store, _owner = _setup(mods)
        with pytest.raises(ss.SelfStateError):
            ss.SelfStateService(ctx).assemble()
        assert ss.SelfStateBridge(_Ctx()).packet_items("s1") == []
        # self_state on but the layered self-model off: refused, not partial.
        ctx2, _s2, _o2 = _setup(mods, {"self_state_enabled": True})
        with pytest.raises(ss.SelfStateError):
            ss.SelfStateService(ctx2).assemble()
        assert ss.SelfStateBridge(ctx2).packet_items("s1") == []
    finally:
        mods[0].unload()


def test_fields_are_the_seven_section13_fields():
    mods = _load_modules()
    ss = mods[1]
    try:
        ctx, store, owner = _setup(mods, ENABLED)
        _seed(mods, ctx, store, owner)
        assembled = ss.SelfStateService(ctx).assemble()
    finally:
        mods[0].unload()
    fields = assembled["fields"]
    assert list(fields) == list(ss.SELF_STATE_FIELDS)
    assert fields["identity_summary"] == "A persistent entity."
    assert fields["current_attention"] == "Ship the slice"
    assert fields["active_self_originated_goal"] == "Explore the frontier"
    assert "uncertainty is 0.80" in fields["major_discrepancy"]
    assert fields["confidence_uncertainty"] == \
        "uncertainty 0.80; confidence 0.20"
    assert fields["known_limitation"] == "No network access."
    assert fields["curiosity_target"] == \
        "Why has local cognition latency increased?"
    assert assembled["owner_entity_id"] == owner


def test_empty_profile_omits_absent_fields():
    mods = _load_modules()
    ss = mods[1]
    try:
        ctx, _store, _owner = _setup(mods, ENABLED)
        fields = ss.SelfStateService(ctx).assemble()["fields"]
    finally:
        mods[0].unload()
    # Only the always-derivable fields: no invented attention,
    # limitation, discrepancy, intrinsic goal, or curiosity target.
    assert set(fields) == {"identity_summary", "confidence_uncertainty"}
    assert fields["confidence_uncertainty"] == \
        "uncertainty 0.00; confidence 1.00"


def test_assembly_is_read_only():
    home = get_hermes_home()
    mods = _load_modules()
    ss = mods[1]
    try:
        ctx, store, owner = _setup(mods, ENABLED)
        _seed(mods, ctx, store, owner)
        watched = [
            home / "entity" / "self_model.yaml",
            home / "entity" / "goals.yaml",
            home / "entity" / "curiosity.yaml",
        ]
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
        ss.SelfStateService(ctx).assemble()
        ss.SelfStateBridge(ctx).packet_items("s1")
        after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
    finally:
        mods[0].unload()
    assert before == after


def test_packet_items_land_in_self_state_section_of_packet_v2():
    mods = _load_modules()
    ss, packet_mod = mods[1], mods[8]
    try:
        ctx, store, owner = _setup(mods, ENABLED)
        _seed(mods, ctx, store, owner)
        items = ss.SelfStateBridge(ctx).packet_items("s1")

        class _PacketCtx:
            @staticmethod
            def get_config(_key, default):
                return 6000 if _key == "context_packet_max_chars" else default

        packet = packet_mod.ContextPacketBuilder(_PacketCtx()).build(
            items + [packet_mod.ContextItem(
                "current_state", "now fact", "present", "1", 1, 1),
                packet_mod.ContextItem(
                    "relevant_episodes", "old episode", "mimir", "2", 1, 1)]
        )
    finally:
        mods[0].unload()
    assert len(items) == 7
    assert all(item.section == "self_state" for item in items)
    assert [item.record_id for item in items] == list(ss.SELF_STATE_FIELDS)
    assert "version=2" in packet
    assert packet.index("CURRENT STATE") < packet.index("SELF STATE")
    assert packet.index("SELF STATE") < packet.index("RELEVANT EPISODES")
    assert packet.count("source=self_state") == 7
    assert "Identity: A persistent entity." in packet


def test_field_text_is_bounded():
    mods = _load_modules()
    ss = mods[1]
    try:
        ctx, store, owner = _setup(mods, ENABLED)
        contracts = mods[3]
        store.propose(_claim(contracts, owner, "identity", "core",
                             "x" * 1000, 0.9, "identity"))
        fields = ss.SelfStateService(ctx).assemble()["fields"]
    finally:
        mods[0].unload()
    assert len(fields["identity_summary"]) == ss.MAX_FIELD_CHARS


def test_profile_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    ss = mods[1]
    try:
        ctx, store, owner = _setup(mods, ENABLED)
        _seed(mods, ctx, store, owner)
        items_a = ss.SelfStateBridge(ctx).packet_items("s1")
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            items_b = ss.SelfStateBridge(_Ctx(ENABLED)).packet_items("s1")
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert len(items_a) == 7
    assert items_b == []
