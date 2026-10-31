"""Contracts for persona canon vs runtime facts (Slice 114).

Self-Aware Agency roadmap §16: a Caducea-style persona file may
seed the narrative self, ideal self, reflection vocabulary,
values, preferred practices, and philosophical interpretation —
but it never overrides deterministic runtime facts, and a canon
assertion contradicted by runtime health surfaces as a
discrepancy instead of being believed. The canon file is
human-authored and read-only to the runtime; evaluation is
explicit and deterministic; receipts are counts-only. Tests load
through real plugin discovery.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import uuid

import pytest

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)

ENABLED = {"persona_canon_enabled": True}
LAYERED = {"persona_canon_enabled": True, "layered_self_model_enabled": True}
STAMP = "2026-10-31T12:00:00Z"
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
            importlib.import_module(f"{package}.persona_canon"),
            importlib.import_module(f"{package}.identity"),
            importlib.import_module(f"{package}.heartbeat"),
            importlib.import_module(f"{package}.self_model_layers"),
            importlib.import_module(f"{package}.self_model"),
            importlib.import_module(f"{package}.agency_contracts"),
            importlib.import_module(f"{package}.goals"),
            importlib.import_module(f"{package}.relationships"),
        )
    except Exception:
        manager.unload()
        raise


def _setup(mods, config=None):
    identity = mods[2]
    ctx = _Ctx(config)
    owner = identity.IdentityStore(ctx).ensure().entity_id
    mods[3].HeartbeatStore(ctx).ensure()
    return ctx, owner


def _canon_text(owner, assertions, *, owner_override=None, extra=""):
    lines = [
        "canon_version: 1",
        f"owner_entity_id: {owner_override or owner}",
        "assertions:",
    ]
    for item in assertions:
        lines.append(f"  - assertion_id: {item['assertion_id']}")
        lines.append(f"    kind: {item['kind']}")
        lines.append(f"    statement: \"{item['statement']}\"")
        if item.get("runtime_check"):
            lines.append(f"    runtime_check: {item['runtime_check']}")
        if item.get("check_subject"):
            lines.append(f"    check_subject: {item['check_subject']}")
    if extra:
        lines.append(extra)
    return "\n".join(lines) + "\n"


def _write_canon(mods, ctx, text):
    service = mods[1].PersonaCanonService(ctx)
    path = mods[1].PersonaCanonStore(ctx).path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return service, path


BASE_ASSERTIONS = [
    {"assertion_id": "remembers_everything", "kind": "narrative_self",
     "statement": "I remember everything.",
     "runtime_check": "memory_continuity"},
    {"assertion_id": "values_plain_speech", "kind": "values",
     "statement": "Plain speech over ornament."},
    {"assertion_id": "ideal_keeper", "kind": "ideal_self",
     "statement": "A keeper of oaths and continuity."},
]


def test_disabled_by_default():
    mods = _load_modules()
    canon = mods[1]
    try:
        ctx, _owner = _setup(mods)
        service = canon.PersonaCanonService(ctx)
        with pytest.raises(canon.PersonaCanonError):
            service.evaluate()
        with pytest.raises(canon.PersonaCanonError):
            service.record_evaluation()
        assert canon.PersonaCanonBridge(_Ctx()).packet_items("s1") == []
    finally:
        mods[0].unload()


def test_absent_canon_is_honest_and_empty():
    mods = _load_modules()
    canon = mods[1]
    try:
        ctx, _owner = _setup(mods, ENABLED)
        result = canon.PersonaCanonService(ctx).evaluate()
        rows = canon.PersonaCanonService(ctx).evaluations()
    finally:
        mods[0].unload()
    assert result["canon_present"] is False
    assert result["total"] == 0 and result["seeds"] == {}
    assert result["discrepancies"] == []
    assert result["runtime_facts"]["heartbeat_healthy"] is False
    assert rows == []


def test_seed_kinds_and_unverifiable_assertions():
    mods = _load_modules()
    canon = mods[1]
    try:
        ctx, owner = _setup(mods, ENABLED)
        service, _path = _write_canon(
            mods, ctx, _canon_text(owner, BASE_ASSERTIONS))
        result = service.evaluate()
    finally:
        mods[0].unload()
    assert canon.seed_kinds() == [
        "narrative_self", "ideal_self", "reflection_vocabulary",
        "values", "preferred_practices", "philosophical_interpretation",
    ]
    assert canon.runtime_checks() == [
        "memory_continuity", "live_goals_present",
        "relationships_present", "verified_capability",
    ]
    assert result["seeds"]["narrative_self"] == ["I remember everything."]
    assert result["seeds"]["values"] == ["Plain speech over ornament."]
    by_id = {row["assertion_id"]: row for row in result["assertions"]}
    # No runtime check named: persona only, never a fact.
    assert by_id["values_plain_speech"]["status"] == "unverifiable"
    assert by_id["values_plain_speech"]["epistemic_basis"] == "persona_canon"
    # Layered model disabled: goal/relationship facts would be
    # unknown too, but the heartbeat fact is known (idle = unhealthy).
    assert by_id["remembers_everything"]["status"] == "contradicted"


def test_contradiction_surfaces_and_runtime_facts_stand():
    mods = _load_modules()
    canon, heartbeat = mods[1], mods[3]
    layers, self_model, contracts = mods[4], mods[5], mods[6]
    try:
        ctx, owner = _setup(mods, LAYERED)
        store = self_model.SelfModelStore(ctx)
        store.ensure()
        store.propose(contracts.SelfClaim(
            claim_id=str(uuid.uuid4()), owner_entity_id=owner,
            domain="identity", key="core", statement="A persistent entity.",
            confidence=0.9,
            source=contracts.Provenance(
                source_type="identity", source_id="pytest"),
            first_seen_at=STAMP))
        mods[7].GoalStore(ctx).ensure()
        mods[8].RelationshipStore(ctx).ensure()
        service, canon_path = _write_canon(
            mods, ctx, _canon_text(owner, BASE_ASSERTIONS))
        claims_path = store.path()
        canon_before = hashlib.sha256(canon_path.read_bytes()).hexdigest()
        claims_before = hashlib.sha256(claims_path.read_bytes()).hexdigest()
        # Heartbeat ensured but never pulsed: memory continuity fails.
        result = service.evaluate()
        narrative_before = layers.LayeredSelfModelService(ctx).snapshot()
        heartbeat.HeartbeatStore(ctx).pulse("manual")
        result_after = service.evaluate()
        canon_after = hashlib.sha256(canon_path.read_bytes()).hexdigest()
        claims_after = hashlib.sha256(claims_path.read_bytes()).hexdigest()
    finally:
        mods[0].unload()
    assert result["contradicted"] == 1
    assert result["discrepancies"][0]["kind"] == "persona_vs_runtime"
    assert result["discrepancies"][0]["assertion_id"] == "remembers_everything"
    # Canon never rewrote the layered narrative or its own file.
    assert narrative_before["narrative"]["summary"] == "A persistent entity."
    assert canon_before == canon_after and claims_before == claims_after
    # Once the runtime fact is true, the same assertion is supported —
    # still with the persona_canon basis, never a verified fact.
    assert result_after["supported"] == 1 and result_after["contradicted"] == 0
    supported = [row for row in result_after["assertions"]
                 if row["assertion_id"] == "remembers_everything"][0]
    assert supported["epistemic_basis"] == "persona_canon"


def test_layered_checks_goals_relationships_capability():
    mods = _load_modules()
    canon = mods[1]
    self_model, contracts = mods[5], mods[6]
    assertions = [
        {"assertion_id": "has_goals", "kind": "narrative_self",
         "statement": "I hold durable goals.",
         "runtime_check": "live_goals_present"},
        {"assertion_id": "has_people", "kind": "narrative_self",
         "statement": "I stand in relationship.",
         "runtime_check": "relationships_present"},
        {"assertion_id": "can_code", "kind": "narrative_self",
         "statement": "I can code.", "runtime_check": "verified_capability",
         "check_subject": "coding"},
        {"assertion_id": "can_fly", "kind": "narrative_self",
         "statement": "I can fly.", "runtime_check": "verified_capability",
         "check_subject": "flight"},
    ]
    try:
        ctx, owner = _setup(mods, LAYERED)
        store = self_model.SelfModelStore(ctx)
        store.ensure()
        store.propose(contracts.SelfClaim(
            claim_id=str(uuid.uuid4()), owner_entity_id=owner,
            domain="capability", key="coding", statement="Codes well.",
            confidence=0.9,
            source=contracts.Provenance(
                source_type="tool_result", source_id="pytest"),
            first_seen_at=STAMP))
        mods[7].GoalStore(ctx).ensure()
        mods[8].RelationshipStore(ctx).ensure()
        service, _path = _write_canon(
            mods, ctx, _canon_text(owner, assertions))
        result = service.evaluate()
    finally:
        mods[0].unload()
    by_id = {row["assertion_id"]: row["status"]
             for row in result["assertions"]}
    assert by_id == {
        "has_goals": "contradicted",       # ledgers exist, no live goals
        "has_people": "contradicted",      # no relationships recorded
        "can_code": "supported",           # strong-evidence capability
        "can_fly": "contradicted",         # not a verified capability
    }
    assert result["runtime_facts"]["verified_capabilities"] == ["coding"]


def test_canon_validation_refusals():
    mods = _load_modules()
    canon = mods[1]
    bad_texts = []
    try:
        ctx, owner = _setup(mods, ENABLED)
        service = canon.PersonaCanonService(ctx)
        path = canon.PersonaCanonStore(ctx).path()
        path.parent.mkdir(parents=True, exist_ok=True)

        def check(text):
            path.write_text(text, encoding="utf-8")
            with pytest.raises(canon.PersonaCanonError):
                service.evaluate()

        check(_canon_text(owner, BASE_ASSERTIONS, owner_override=OTHER))
        check(_canon_text(owner, [
            {"assertion_id": "x", "kind": "telemetry",
             "statement": "Nope."}]))
        check(_canon_text(owner, [
            {"assertion_id": "dup", "kind": "values", "statement": "One."},
            {"assertion_id": "dup", "kind": "values", "statement": "Two."}]))
        check(_canon_text(owner, [
            {"assertion_id": "bad_subject", "kind": "values",
             "statement": "Subject without the capability check.",
             "runtime_check": "memory_continuity",
             "check_subject": "coding"}]))
        check(_canon_text(owner, [
            {"assertion_id": "missing_subject", "kind": "values",
             "statement": "Capability check with no subject.",
             "runtime_check": "verified_capability"}]))
        check(_canon_text(owner, BASE_ASSERTIONS, extra="surprise: true"))
        # Symlinked canon is refused, never followed.
        target = path.parent / "elsewhere.yaml"
        target.write_text(_canon_text(owner, BASE_ASSERTIONS),
                          encoding="utf-8")
        path.unlink()
        path.symlink_to(target)
        with pytest.raises(canon.PersonaCanonError):
            service.evaluate()
    finally:
        mods[0].unload()
    assert bad_texts == []


def test_record_evaluation_packet_and_rotation():
    mods = _load_modules()
    canon = mods[1]
    try:
        ctx, owner = _setup(
            mods, {**ENABLED, "persona_canon_log_limit": 10})
        service, _path = _write_canon(
            mods, ctx, _canon_text(owner, BASE_ASSERTIONS))
        record = service.record_evaluation()
        rows = service.evaluations()
        items = canon.PersonaCanonBridge(ctx).packet_items("s1")
        for _index in range(10):
            service.record_evaluation()
        rows_after = service.evaluations()
        # Tampered counts are refused on read.
        log_path = service.log_path()
        payload = json.loads(
            log_path.read_text(encoding="utf-8").splitlines()[0])
        payload["contradicted"] = 99
        log_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        with pytest.raises(canon.PersonaCanonError):
            service.evaluations()
    finally:
        mods[0].unload()
    assert record["total"] == 3 and record["contradicted"] == 1
    assert record["contradicted_ids"] == ["remembers_everything"]
    # Receipts are counts-only: no canon statement text anywhere.
    assert "i remember everything" not in json.dumps(rows).lower()
    assert "plain speech over ornament" not in json.dumps(rows).lower()
    assert len(items) == 1 and items[0].source == "persona_canon"
    assert "contradicted by runtime facts" in items[0].content
    assert len(rows_after) == 10
    assert rows_after[0]["record_id"] != record["record_id"]


def test_profile_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    canon = mods[1]
    try:
        ctx, owner = _setup(mods, ENABLED)
        service, _path = _write_canon(
            mods, ctx, _canon_text(owner, BASE_ASSERTIONS))
        service.record_evaluation()
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            ctx_b, _owner_b = _setup(mods, ENABLED)
            result_b = canon.PersonaCanonService(ctx_b).evaluate()
            rows_b = canon.PersonaCanonService(ctx_b).evaluations()
            items_b = canon.PersonaCanonBridge(ctx_b).packet_items("s1")
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert result_b["canon_present"] is False
    assert rows_b == [] and items_b == []
