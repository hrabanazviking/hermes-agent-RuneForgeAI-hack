"""Contracts for limited local autonomy (Slice 98).

Emergent Agency Phase 8 (roadmap §15): a narrow set of Class 0/1
local actions may run through the Phase 5 autonomy gate. The AI can
choose when to think and what to inspect — not change anything it
wants. Read-only inspections leave every source store byte-identical;
Class 1 effects are bounded to the profile (private report log,
suggested-patch records that are never applied, the self-model's own
merge layer, the consolidation checkpoint). ``run_local_tests`` is
registered but has no built-in executor: allowed means skipped,
never executed. Existing policy files are human-authoritative and
gain the new registry entries only by human edit.
"""

from __future__ import annotations

import importlib
import uuid
from datetime import datetime, timezone

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
            importlib.import_module(f"{package}.local_autonomy"),
            importlib.import_module(f"{package}.agency_contracts"),
            importlib.import_module(f"{package}.autonomy"),
            importlib.import_module(f"{package}.self_model"),
            importlib.import_module(f"{package}.curiosity"),
        )
    except Exception:
        manager.unload()
        raise


def _seed_all(manager):
    manager.invoke_hook("on_session_start", session_id="one", model="model-a")


def _edit_policy(home, **changes):
    path = home / "entity" / "autonomy_policy.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload.update(changes)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return payload


def _entity_bytes(home):
    entity = home / "entity"
    return {
        p.name: p.read_bytes()
        for p in sorted(entity.iterdir())
        if p.is_file() and not p.name.endswith(".lock")
    }


def test_registry_is_class_0_or_1_only_and_seeded_in_new_policies():
    home = get_hermes_home()
    manager, local, contracts, autonomy_mod, *_ = _load_modules()
    try:
        _seed_all(manager)
        policy = autonomy_mod.AutonomyStore(_Ctx()).policy()
    finally:
        manager.unload()
    assert set(local.LOCAL_AUTONOMY_ACTIONS) == {
        "inspect_project_state", "check_health", "inspect_memory_integrity",
        "local_readonly_research", "run_local_tests", "generate_private_report",
        "organize_curiosity_queue", "update_self_model_evidence",
        "run_consolidation", "prepare_suggested_patch",
    }
    assert all(cls in (0, 1) for cls in local.LOCAL_AUTONOMY_ACTIONS.values())
    for action, cls in local.LOCAL_AUTONOMY_ACTIONS.items():
        assert policy["capabilities"][action]["class"] == cls
    assert "run_local_tests" not in local.BUILTIN_EXECUTOR_ACTIONS
    assert len(local.BUILTIN_EXECUTOR_ACTIONS) == 9


def test_observe_mode_executes_nothing_and_local_mode_runs_inspection():
    home = get_hermes_home()
    manager, local, contracts, autonomy_mod, *_ = _load_modules()
    try:
        _seed_all(manager)
        service = local.LocalAutonomyService(_Ctx())
        denied = service.run_action("inspect_project_state", now=NOW)
        _edit_policy(home, mode="local")
        allowed = service.run_action("inspect_project_state", now=NOW)
        state = autonomy_mod.AutonomyStore(_Ctx()).state()
    finally:
        manager.unload()
    assert denied["decision"] == "deny"
    assert denied["status"] == "not_executed"
    assert allowed["decision"] == "allow"
    assert allowed["status"] == "succeeded"
    assert "Project state inspected" in allowed["summary"]
    assert state["actions_executed"] == 1


def test_readonly_actions_leave_source_stores_byte_identical():
    home = get_hermes_home()
    manager, local, contracts, autonomy_mod, *_ = _load_modules()
    try:
        _seed_all(manager)
        _edit_policy(home, mode="local")
        before = _entity_bytes(home)
        service = local.LocalAutonomyService(_Ctx())
        health = service.run_action("check_health", now=NOW)
        integrity = service.run_action("inspect_memory_integrity", now=NOW)
        research = service.run_action(
            "local_readonly_research", "What goals exist locally?", now=NOW)
        after = _entity_bytes(home)
    finally:
        manager.unload()
    assert health["status"] == integrity["status"] == research["status"] == "succeeded"
    assert "nothing external consulted" in research["summary"]
    changed = {name for name in before if before[name] != after.get(name)}
    # Only the autonomy runtime state may change (decision/result
    # counters); every inspected source store is byte-identical and
    # no new store file appears.
    assert changed <= {"autonomy_state.json"}
    assert set(after) == set(before)


def test_private_report_and_suggested_patch_are_logged_not_applied():
    home = get_hermes_home()
    manager, local, contracts, autonomy_mod, *_ = _load_modules()
    try:
        _seed_all(manager)
        _edit_policy(home, mode="local")
        service = local.LocalAutonomyService(_Ctx())
        report = service.run_action("generate_private_report", now=NOW)
        patch = service.run_action(
            "prepare_suggested_patch", "Tidy the curiosity queue ordering",
            candidate={"patch_summary": "Sort frontier by score then id"}, now=NOW)
        log = local.LocalActionLog(_Ctx())
        records = log.records()
        packet = local.LocalAutonomyBridge(_Ctx()).packet_items("s1")
    finally:
        manager.unload()
    assert report["status"] == patch["status"] == "succeeded"
    assert [r["kind"] for r in records] == ["report", "suggested_patch"]
    assert records[0]["detail"]["claims_total"] == 0
    assert records[1]["detail"] == {"applied": "false"}
    assert "nothing was applied" in patch["summary"]
    assert len(packet) == 1 and packet[0].source == "local_autonomy"


def test_curiosity_organise_and_self_model_evidence_via_merge_layer():
    home = get_hermes_home()
    manager, local, contracts, autonomy_mod, self_model_mod, curiosity_mod = _load_modules()
    try:
        _seed_all(manager)
        _edit_policy(home, mode="local")
        owner = autonomy_mod.AutonomyStore(_Ctx()).ensure()["owner_entity_id"]
        store = self_model_mod.SelfModelStore(_Ctx())
        claim = store.propose(contracts.SelfClaim(
            claim_id=str(uuid.uuid4()), owner_entity_id=owner,
            domain="capability", key="local_inspection",
            statement="Can inspect local project state",
            confidence=0.5,
            source=contracts.Provenance(source_type="system_observation", source_id="pytest"),
            first_seen_at=TS,
        ))
        curiosity_mod.CuriosityStore(_Ctx()).add_question(contracts.CuriosityQuestion(
            question_id=str(uuid.uuid4()), owner_entity_id=owner,
            question="What does the local state contain?",
            status="open", novelty=0.9, uncertainty=0.9, relevance=0.9,
            expected_value=0.9, cost=0.1, risk_class=0,
            source=contracts.Provenance(source_type="curiosity", source_id="pytest"),
            created_at=TS,
        ))
        service = local.LocalAutonomyService(_Ctx())
        organised = service.run_action("organize_curiosity_queue", now=NOW)
        applied = service.run_action(
            "update_self_model_evidence", "Confirm local inspection",
            candidate={"evidence": {"domain": "capability",
                                    "key": "local_inspection",
                                    "outcome": "positive"}}, now=NOW)
        skipped = service.run_action(
            "update_self_model_evidence", "Confirm a missing claim",
            candidate={"evidence": {"domain": "capability",
                                    "key": "no_such_claim",
                                    "outcome": "positive"}}, now=NOW)
        after = {c.key: c for c in store.claims()}["local_inspection"]
    finally:
        manager.unload()
    assert organised["status"] == "succeeded"
    assert "1 frontier" in organised["summary"]
    assert applied["status"] == "succeeded"
    assert after.confidence > claim.confidence
    assert skipped["status"] == "succeeded"
    assert "no claim was created" in skipped["summary"]
    assert {c.key for c in store.claims()} == {"local_inspection"}


def test_consolidation_runs_and_local_tests_are_skipped_not_executed():
    home = get_hermes_home()
    manager, local, contracts, autonomy_mod, *_ = _load_modules()
    try:
        _seed_all(manager)
        _edit_policy(home, mode="local")
        service = local.LocalAutonomyService(_Ctx())
        consolidation = service.run_action("run_consolidation", now=NOW)
        tests = service.run_action("run_local_tests", now=NOW)
        state = autonomy_mod.AutonomyStore(_Ctx()).state()
        checkpoint = home / "entity" / "consolidation.json"
        assert checkpoint.is_file()
    finally:
        manager.unload()
    assert consolidation["status"] == "succeeded"
    assert "sequence 1" in consolidation["summary"]
    assert tests["decision"] == "allow"
    assert tests["status"] == "skipped"
    assert "not executed" in tests["summary"]
    assert state["actions_executed"] == 1


def test_propose_mode_unknown_action_and_disabled_service():
    home = get_hermes_home()
    manager, local, *_ = _load_modules()
    try:
        _seed_all(manager)
        _edit_policy(home, mode="propose")
        service = local.LocalAutonomyService(_Ctx())
        outcome = service.run_action("check_health", now=NOW)
        with pytest.raises(local.LocalAutonomyError):
            service.run_action("send_email_anywhere", now=NOW)
        with pytest.raises(local.LocalAutonomyError):
            local.LocalAutonomyService(
                _Ctx({"local_autonomy_enabled": False})).run_action("check_health", now=NOW)
    finally:
        manager.unload()
    assert outcome["decision"] == "require_confirmation"
    assert outcome["status"] == "not_executed"


def test_log_symlink_refused_and_a_b_a_isolation(tmp_path):
    home = get_hermes_home()
    profile_b = tmp_path / "profile-b"
    manager, local, *_ = _load_modules()
    try:
        _seed_all(manager)
        _edit_policy(home, mode="local")
        service = local.LocalAutonomyService(_Ctx())
        service.run_action("generate_private_report", now=NOW)
        log = local.LocalActionLog(_Ctx())
        assert len(log.records()) == 1
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            manager.invoke_hook("on_session_start", session_id="b", model="model-b")
            assert local.LocalActionLog(_Ctx()).records() == []
        finally:
            reset_hermes_home_override(token)
        log_path = home / "entity" / "local_actions.jsonl"
        target = home / "entity" / "log-target.jsonl"
        target.write_bytes(log_path.read_bytes())
        log_path.unlink()
        log_path.symlink_to(target)
        with pytest.raises(local.LocalAutonomyError):
            local.LocalActionLog(_Ctx()).records()
    finally:
        manager.unload()


def test_orchestrator_gains_local_executors():
    home = get_hermes_home()
    manager, local, *_ = _load_modules()
    try:
        _seed_all(manager)
        import importlib as _il
        loaded = manager._plugins["volmarr-core"]
        agency = _il.import_module(f"{loaded.module.__package__}.agency")
        assert set(local.BUILTIN_EXECUTOR_ACTIONS) <= set(agency.EXECUTOR_ACTIONS)
        assert "run_local_tests" not in agency.EXECUTOR_ACTIONS
    finally:
        manager.unload()
