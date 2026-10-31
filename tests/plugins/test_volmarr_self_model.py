"""Contracts for the persistent self-model store (Slice 89).

Emergent Agency Phase 1 (roadmap §8): a durable ``entity/self_model.yaml``
store on the Phase 0 ``SelfClaim`` contract, with create-once semantics,
owner/symlink/size validation in the established GoalStore pattern, a
deterministic evidence merge (the LLM may propose; the merge layer
decides), and a bounded packet contribution. Tests load the module
through real plugin discovery and exercise the store directly with a
minimal config stub — the store's only ctx surface is ``get_config``.
"""

from __future__ import annotations

import importlib
import uuid

import pytest
import yaml

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)

TS = "2026-10-30T12:00:00Z"


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
            importlib.import_module(f"{package}.self_model"),
            importlib.import_module(f"{package}.agency_contracts"),
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


def _store(mod):
    store = mod.SelfModelStore(_Ctx())
    data = store.ensure()
    return store, data["owner_entity_id"]


def test_create_once_store_owned_by_identity_and_byte_stable():
    home = get_hermes_home()
    manager, mod, _contracts = _load_modules()
    try:
        manager.invoke_hook("on_session_start", session_id="one", model="model-a")
        identity = yaml.safe_load((home / "entity" / "entity.yaml").read_text("utf-8"))
        path = home / "entity" / "self_model.yaml"
        first_bytes = path.read_bytes()
        manager.invoke_hook("on_session_start", session_id="two", model="model-b")
    finally:
        manager.unload()
    payload = yaml.safe_load(first_bytes)
    assert payload["self_model_version"] == 1
    assert payload["owner_entity_id"] == identity["entity_id"]
    assert payload["claims"] == {}
    assert path.read_bytes() == first_bytes


def test_new_claim_confidence_is_capped_by_evidence_strength():
    _manager, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        weak = store.propose(
            _claim(contracts, owner, "capability", "weak_key", "Maybe good.", 0.9, "curiosity")
        )
        medium = store.propose(
            _claim(contracts, owner, "capability", "medium_key", "Fairly good.", 0.9, "reflection")
        )
        strong = store.propose(
            _claim(contracts, owner, "capability", "strong_key", "Proven good.", 0.9, "tool_result")
        )
    finally:
        _manager.unload()
    # Weak evidence must not create high-confidence self-beliefs (§8).
    assert weak.confidence == 0.35
    assert medium.confidence == 0.65
    assert strong.confidence == 0.9


def test_deterministic_merge_confirm_contradict_and_strong_restate():
    _manager, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        base = _claim(
            contracts, owner, "capability", "python_debugging",
            "Effective at Python debugging.", 0.5, "tool_result",
        )
        store.propose(base)
        confirmed = store.propose(
            _claim(
                contracts, owner, "capability", "python_debugging",
                "Effective at Python debugging.", 0.99, "tool_result",
            )
        )
        # Merge layer decides: fixed strong delta, not the proposed 0.99.
        assert confirmed.confidence == 0.65
        contradicted = store.propose(
            _claim(
                contracts, owner, "capability", "python_debugging",
                "Ineffective at Python debugging.", 0.9, "reflection",
            )
        )
        assert contradicted.confidence == 0.55
        assert contradicted.statement == "Effective at Python debugging."
        restated = store.propose(
            _claim(
                contracts, owner, "capability", "python_debugging",
                "Ineffective at Python debugging.", 0.9, "user_explicit",
            )
        )
        assert restated.statement == "Ineffective at Python debugging."
        # Claims survive a fresh store instance (restart persistence).
        reloaded = {c.key: c for c in mod.SelfModelStore(_Ctx()).claims()}
    finally:
        _manager.unload()
    assert reloaded["python_debugging"].statement == "Ineffective at Python debugging."
    raw = yaml.safe_load(
        (get_hermes_home() / "entity" / "self_model.yaml").read_text("utf-8")
    )
    record = next(iter(raw["claims"].values()))
    assert len(record["contradictions"]) == 1
    assert record["contradictions"][0]["statement"] == "Ineffective at Python debugging."


def test_apply_evidence_deltas_and_unknown_claim():
    _manager, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        store.propose(
            _claim(contracts, owner, "capability", "research", "Steady researcher.", 0.5, "goal")
        )
        positive = store.apply_evidence(
            "capability", "research", outcome="positive",
            source=contracts.Provenance(source_type="curiosity", source_id="pytest"),
        )
        assert positive.confidence == 0.53
        negative = store.apply_evidence(
            "capability", "research", outcome="contradiction",
            source=contracts.Provenance(source_type="tool_result", source_id="pytest"),
        )
        assert negative.confidence == 0.33
        with pytest.raises(mod.SelfModelError):
            store.apply_evidence(
                "capability", "missing", outcome="positive",
                source=contracts.Provenance(source_type="goal", source_id="pytest"),
            )
        with pytest.raises(mod.SelfModelError):
            store.apply_evidence(
                "capability", "research", outcome="sideways",
                source=contracts.Provenance(source_type="goal", source_id="pytest"),
            )
    finally:
        _manager.unload()


def test_wrong_owner_malformed_version_and_symlink_are_refused():
    home = get_hermes_home()
    _manager, mod, _contracts = _load_modules()
    try:
        store, _owner = _store(mod)
        path = home / "entity" / "self_model.yaml"
        wrong_owner = (
            "self_model_version: 1\n"
            "owner_entity_id: 00000000-0000-4000-8000-000000000000\n"
            f"updated_at: '{TS}'\n"
            "claims: {}\n"
        ).encode()
        path.write_bytes(wrong_owner)
        with pytest.raises(mod.SelfModelError):
            store.claims()
        assert path.read_bytes() == wrong_owner

        path.write_text("self_model_version: 99\n", encoding="utf-8")
        with pytest.raises(mod.SelfModelError):
            store.claims()

        target = home / "entity" / "target.yaml"
        target.write_bytes(wrong_owner)
        path.unlink()
        path.symlink_to(target)
        with pytest.raises(mod.SelfModelError):
            store.claims()
    finally:
        _manager.unload()


def test_packet_quotas_and_no_identity_rewrite():
    home = get_hermes_home()
    _manager, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        identity_path = home / "entity" / "entity.yaml"
        identity_bytes = identity_path.read_bytes()
        for index in range(5):
            store.propose(_claim(
                contracts, owner, "capability", f"cap_{index}",
                f"Capability {index}.", 0.5 + index * 0.05, "tool_result",
            ))
        for domain, count in (("limitation", 3), ("commitment", 3), ("uncertainty", 2)):
            for index in range(count):
                store.propose(_claim(
                    contracts, owner, domain, f"{domain}_{index}",
                    f"{domain} {index}.", 0.5, "goal",
                ))
        store.propose(_claim(
            contracts, owner, "preference", "style", "Prefers terse output.", 0.6, "goal"
        ))
        items = mod.SelfModelBridge(_Ctx()).packet_items("session-1")
    finally:
        _manager.unload()
    by_domain = {}
    for item in items:
        assert item.section == "current_state"
        domain = item.content.split(" ")[1]
        by_domain[domain] = by_domain.get(domain, 0) + 1
    assert by_domain == {"capability": 3, "limitation": 2, "commitment": 2, "uncertainty": 2}
    # The self-model never rewrites canonical identity.
    assert identity_path.read_bytes() == identity_bytes


def test_self_model_ledgers_follow_a_b_a_profiles(tmp_path):
    profile_a = get_hermes_home()
    profile_b = tmp_path / "profile-b"
    _manager, mod, contracts = _load_modules()
    try:
        store_a, owner_a = _store(mod)
        store_a.propose(_claim(
            contracts, owner_a, "capability", "only_a", "Profile A claim.", 0.5, "goal"
        ))
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            store_b, owner_b = _store(mod)
            assert store_b.claims() == []
            store_b.propose(_claim(
                contracts, owner_b, "capability", "only_b", "Profile B claim.", 0.5, "goal"
            ))
        finally:
            reset_hermes_home_override(token)
        restored = mod.SelfModelStore(_Ctx()).claims()
    finally:
        _manager.unload()
    assert owner_a != owner_b
    assert [claim.key for claim in restored] == ["only_a"]


def test_missing_and_disabled_self_model_packet_fails_open():
    _manager, mod, _contracts = _load_modules()
    try:
        # Identity exists via no ensure here: missing identity/store -> [].
        bridge = mod.SelfModelBridge(_Ctx())
        assert bridge.packet_items("session-1") == []
        disabled = mod.SelfModelBridge(_Ctx({"self_model_enabled": False}))
        disabled.on_session_start(session_id="one")
        assert disabled.packet_items("session-1") == []
        assert not (get_hermes_home() / "entity" / "self_model.yaml").exists()
    finally:
        _manager.unload()
