"""Contracts for the autonomy policy engine (Slice 95).

Emergent Agency Phase 5 (roadmap §12): a deterministic gate between
wanting and doing. The human-authoritative policy file is seeded
create-once and never altered by the runtime; risk classes come from
the policy's capability registry, never from action names; modes
off/observe/propose/local/bounded map deterministically to
allow/require_confirmation/deny; budgets bound allowed actions; and
the circuit breaker trips on repeated failures and is never
automatically untripped. Tests load the module through real plugin
discovery with a minimal config stub; human policy edits are
simulated by editing the policy file on disk, exactly as a human
would.
"""

from __future__ import annotations

import importlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import yaml

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)

TS = "2026-10-30T12:00:00Z"
NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)


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
            importlib.import_module(f"{package}.autonomy"),
            importlib.import_module(f"{package}.agency_contracts"),
        )
    except Exception:
        manager.unload()
        raise


def _store(mod, config=None):
    store = mod.AutonomyStore(_Ctx(config))
    state = store.ensure()
    return store, state["owner_entity_id"]


def _edit_policy(home, **changes):
    """Simulate a human edit of the authoritative policy file."""
    path = home / "entity" / "autonomy_policy.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload.update(changes)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return payload


def _proposal(contracts, owner, action="world_get", *, risk_class=0,
              estimated_cost="none", expires_at=""):
    return contracts.ActionProposal(
        proposal_id=str(uuid.uuid4()),
        owner_entity_id=owner,
        action=action,
        summary=f"Proposed {action}",
        risk_class=risk_class,
        estimated_cost=estimated_cost,
        source=contracts.Provenance(source_type="drive", source_id="pytest"),
        created_at=TS,
        expires_at=expires_at,
    )


def _result(contracts, owner, proposal_id, status):
    return contracts.ActionResult(
        result_id=str(uuid.uuid4()),
        proposal_id=proposal_id,
        owner_entity_id=owner,
        status=status,
        summary=f"Action {status}",
        source=contracts.Provenance(source_type="tool_result", source_id="pytest"),
        completed_at=TS,
    )


def test_create_once_byte_stable_and_default_observe_denies():
    home = get_hermes_home()
    manager, mod, contracts = _load_modules()
    try:
        manager.invoke_hook("on_session_start", session_id="one", model="model-a")
        policy_bytes = (home / "entity" / "autonomy_policy.yaml").read_bytes()
        state_bytes = (home / "entity" / "autonomy_state.json").read_bytes()
        manager.invoke_hook("on_session_start", session_id="two", model="model-b")
        store, owner = _store(mod)
        decision = store.evaluate(_proposal(contracts, owner), now=NOW)
    finally:
        manager.unload()
    assert (home / "entity" / "autonomy_policy.yaml").read_bytes() == policy_bytes
    assert (home / "entity" / "autonomy_state.json").read_bytes() == state_bytes
    assert decision.decision == "deny"
    assert decision.reason_code == "mode_observe_no_execution"
    assert decision.risk_class == 0
    assert decision.policy_version == 1
    assert decision.budget_remaining is True


def test_mode_and_risk_table_is_deterministic():
    home = get_hermes_home()
    _m, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        _edit_policy(home, mode="off")
        assert store.evaluate(_proposal(contracts, owner), now=NOW).reason_code == "autonomy_off"
        _edit_policy(home, mode="propose")
        proposed = store.evaluate(_proposal(contracts, owner), now=NOW)
        assert proposed.decision == "require_confirmation"
        _edit_policy(home, mode="local")
        assert store.evaluate(_proposal(contracts, owner), now=NOW).decision == "allow"
        persistent = store.evaluate(
            _proposal(contracts, owner, "goal_update", risk_class=2), now=NOW
        )
        assert persistent.decision == "require_confirmation"
        assert persistent.reason_code == "persistent_local_requires_confirmation"
        external = store.evaluate(
            _proposal(contracts, owner, "github_push", risk_class=3), now=NOW
        )
        assert external.decision == "require_confirmation"
        _edit_policy(home, mode="bounded", bounded_allowlist=["github_push"])
        bounded = store.evaluate(
            _proposal(contracts, owner, "github_push", risk_class=3), now=NOW
        )
        assert bounded.decision == "allow"
        assert bounded.reason_code == "allowed_bounded_allowlist"
        not_listed = store.evaluate(
            _proposal(contracts, owner, "goal_update", risk_class=2), now=NOW
        )
        assert not_listed.decision == "require_confirmation"
    finally:
        _m.unload()


def test_registry_class_is_authoritative_and_unknown_is_denied():
    home = get_hermes_home()
    _m, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        _edit_policy(home, mode="local")
        # Proposal claims class 0, but the registry says github_push is
        # class 3: the registry wins, the name/claim is never trusted.
        decision = store.evaluate(
            _proposal(contracts, owner, "github_push", risk_class=0), now=NOW
        )
        assert decision.risk_class == 3
        assert decision.decision == "require_confirmation"
        unknown = store.evaluate(
            _proposal(contracts, owner, "world_delete", risk_class=0), now=NOW
        )
        assert unknown.decision == "deny"
        assert unknown.reason_code == "unknown_capability"
        # Classes 4-5 never auto-run, even in bounded mode.
        payload = _edit_policy(home, mode="bounded")
        payload["capabilities"]["wipe_store"] = {"class": 5, "reversible": False}
        (home / "entity" / "autonomy_policy.yaml").write_text(
            yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
        )
        never = store.evaluate(
            _proposal(contracts, owner, "wipe_store", risk_class=5), now=NOW
        )
        assert never.decision == "deny"
        assert never.reason_code == "risk_class_never_auto"
    finally:
        _m.unload()


def test_expired_proposal_and_budget_exhaustion_deny():
    home = get_hermes_home()
    _m, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        _edit_policy(home, mode="local", max_autonomous_actions=1)
        expired = store.evaluate(
            _proposal(contracts, owner, expires_at="2026-10-30T11:00:00Z"), now=NOW
        )
        assert expired.decision == "deny"
        assert expired.reason_code == "expired_proposal"
        proposal = _proposal(contracts, owner)
        assert store.evaluate(proposal, now=NOW).decision == "allow"
        store.record_result(_result(contracts, owner, proposal.proposal_id, "succeeded"))
        exhausted = store.evaluate(_proposal(contracts, owner), now=NOW)
        assert exhausted.decision == "deny"
        assert exhausted.reason_code == "budget_exhausted"
        assert exhausted.budget_remaining is False
    finally:
        _m.unload()


def test_circuit_breaker_trips_and_never_auto_untrips():
    home = get_hermes_home()
    _m, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        _edit_policy(home, mode="local", failure_threshold=2)
        first = _proposal(contracts, owner)
        store.record_result(_result(contracts, owner, first.proposal_id, "failed"))
        state = store.state()
        assert state["circuit_breaker_tripped"] is False
        second = _proposal(contracts, owner)
        store.record_result(_result(contracts, owner, second.proposal_id, "failed"))
        state = store.state()
        assert state["circuit_breaker_tripped"] is True
        assert state["paused"] is True
        assert state["pause_reason"] == "circuit_breaker_consecutive_failures"
        denied = store.evaluate(_proposal(contracts, owner), now=NOW)
        assert denied.decision == "deny"
        assert denied.reason_code == "circuit_breaker_paused"
        # A later success consumes budget but never untrips the breaker.
        third = _proposal(contracts, owner)
        store.record_result(_result(contracts, owner, third.proposal_id, "succeeded"))
        assert store.state()["circuit_breaker_tripped"] is True
        assert store.evaluate(_proposal(contracts, owner), now=NOW).decision == "deny"
    finally:
        _m.unload()


def test_runtime_never_writes_policy_and_counters_record():
    home = get_hermes_home()
    _m, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        _edit_policy(home, mode="local")
        policy_bytes = (home / "entity" / "autonomy_policy.yaml").read_bytes()
        proposal = _proposal(contracts, owner)
        decision = store.evaluate(proposal, now=NOW)
        store.record_decision(decision)
        store.record_result(
            _result(contracts, owner, proposal.proposal_id, "succeeded"),
            estimated_cost="low",
        )
        state = store.state()
    finally:
        _m.unload()
    assert (home / "entity" / "autonomy_policy.yaml").read_bytes() == policy_bytes
    assert state["proposals_considered"] == 1
    assert state["decisions_allow"] == 1
    assert state["actions_executed"] == 1
    assert state["cost_spent"] == 1
    assert state["last_action"]["proposal_id"] == proposal.proposal_id
    assert state["last_action"]["status"] == "succeeded"


def test_wrong_owner_malformed_and_symlink_are_refused():
    home = get_hermes_home()
    _m, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        wrong = _proposal(contracts, "00000000-0000-4000-8000-000000000000")
        with pytest.raises(mod.AutonomyError):
            store.evaluate(wrong, now=NOW)
        policy_path = home / "entity" / "autonomy_policy.yaml"
        original = policy_path.read_bytes()
        policy_path.write_text("autonomy_version: 99\n", encoding="utf-8")
        with pytest.raises(mod.AutonomyError):
            store.policy()
        policy_path.write_bytes(original)
        target = home / "entity" / "target.yaml"
        target.write_bytes(original)
        policy_path.unlink()
        policy_path.symlink_to(target)
        with pytest.raises(mod.AutonomyError):
            store.policy()
        state_path = home / "entity" / "autonomy_state.json"
        state_original = state_path.read_bytes()
        state_target = home / "entity" / "state-target.json"
        state_target.write_bytes(state_original)
        state_path.unlink()
        state_path.symlink_to(state_target)
        with pytest.raises(mod.AutonomyError):
            store.state()
    finally:
        _m.unload()


def test_restart_persistence_and_a_b_a_profile_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    _m, mod, contracts = _load_modules()
    try:
        store_a, owner_a = _store(mod)
        proposal = _proposal(contracts, owner_a)
        decision = store_a.evaluate(proposal, now=NOW)
        store_a.record_decision(decision)
        reloaded = mod.AutonomyStore(_Ctx())
        assert reloaded.state()["proposals_considered"] == 1
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            store_b, owner_b = _store(mod)
            assert store_b.state()["proposals_considered"] == 0
        finally:
            reset_hermes_home_override(token)
        restored = mod.AutonomyStore(_Ctx())
    finally:
        _m.unload()
    assert owner_a != owner_b
    assert restored.state()["proposals_considered"] == 1


def test_packet_and_disabled_or_missing_fails_open():
    home = get_hermes_home()
    _m, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        # Fresh observe-mode profile: the packet stays empty, exactly
        # like every prior slice's empty store (profile isolation).
        assert mod.AutonomyBridge(_Ctx()).packet_items("s1") == []
        _edit_policy(home, mode="local")
        items = mod.AutonomyBridge(_Ctx()).packet_items("s1")
        disabled = mod.AutonomyBridge(_Ctx({"autonomy_enabled": False}))
        disabled.on_session_start(session_id="one")
        assert disabled.packet_items("s1") == []
        store.trip_circuit_breaker("operator_pause_for_test")
        tripped = mod.AutonomyBridge(_Ctx()).packet_items("s1")
    finally:
        _m.unload()
    assert len(items) == 1
    assert items[0].section == "current_state"
    assert items[0].source == "autonomy"
    assert "mode local" in items[0].content
    assert "circuit breaker clear" in items[0].content
    assert "circuit breaker tripped" in tripped[0].content
