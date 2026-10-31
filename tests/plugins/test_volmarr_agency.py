"""Contracts for the agency orchestrator (Slice 96).

Emergent Agency Phase 6 (roadmap §13): one bounded cycle connecting
identity/continuity health, the autonomy gate, self-model, drives,
curiosity, and goals. Candidates are deduplicated, scored, and capped;
every selected action is policy-checked; only actions with a
registered local executor execute (the built-in ``world_get`` is a
read-only inspection verified by re-read); allowed-but-unexecutable
actions are recorded skipped, never as executed; the journal holds
structured facts only; significant cycles record one structured
reflection and feed evidence back to drives/curiosity.
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
            importlib.import_module(f"{package}.agency"),
            importlib.import_module(f"{package}.agency_contracts"),
            importlib.import_module(f"{package}.drives"),
            importlib.import_module(f"{package}.curiosity"),
            importlib.import_module(f"{package}.autonomy"),
            importlib.import_module(f"{package}.goals"),
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


def _raise_drive(drives_mod, contracts, owner, drive_id="curiosity"):
    store = drives_mod.DriveStore(_Ctx())
    store.set_drive(contracts.DriveState(
        drive_id=drive_id, owner_entity_id=owner, enabled=True,
        baseline=0.55, activation=0.9, satisfaction=0.0,
        source=contracts.Provenance(source_type="drive", source_id="pytest"),
        updated_at=TS,
    ))
    return store


def test_fresh_observe_cycle_is_bounded_and_empty():
    home = get_hermes_home()
    manager, agency, contracts, *_ = _load_modules()
    try:
        _seed_all(manager)
        orch = agency.AgencyOrchestrator(_Ctx())
        report = orch.run_cycle(now=NOW)
        journal = orch.journal()
        packet = agency.AgencyBridge(_Ctx()).packet_items("s1")
    finally:
        manager.unload()
    assert report.status == "completed"
    assert report.proposals_considered == 0
    assert report.actions_executed == 0
    assert len(journal) == 1
    assert journal[0]["verification"] == "not_run"
    assert journal[0]["continuity_health"] == "never"
    assert journal[0]["selected_intent_id"] == ""
    assert packet == []


def test_local_cycle_executes_world_get_and_feeds_back():
    home = get_hermes_home()
    manager, agency, contracts, drives_mod, curiosity_mod, autonomy_mod, goals_mod = _load_modules()
    try:
        _seed_all(manager)
        _edit_policy(home, mode="local")
        owner = autonomy_mod.AutonomyStore(_Ctx()).ensure()["owner_entity_id"]
        _raise_drive(drives_mod, contracts, owner)
        orch = agency.AgencyOrchestrator(_Ctx())
        report = orch.run_cycle(now=NOW)
        journal = orch.journal()
        drive = {d.drive_id: d for d in drives_mod.DriveStore(_Ctx()).drives()}["curiosity"]
        autonomy_state = autonomy_mod.AutonomyStore(_Ctx()).state()
        packet = agency.AgencyBridge(_Ctx()).packet_items("s1")
    finally:
        manager.unload()
    assert report.status == "completed"
    assert report.proposals_considered == 1
    assert report.decisions_allow == 1
    assert report.actions_executed == 1
    assert report.actions_failed == 0
    assert journal[0]["verification"] == "passed"
    assert journal[0]["reflection_id"] != ""
    # Feedback: the executed drive was satisfied and cooled down.
    assert drive.satisfaction > 0.0
    assert drive.cooldown_until != ""
    assert autonomy_state["actions_executed"] == 1
    assert len(packet) == 1
    assert packet[0].source == "agency"
    assert "1 executed" in packet[0].content


def test_propose_mode_requires_confirmation_and_executes_nothing():
    home = get_hermes_home()
    manager, agency, contracts, drives_mod, _c, autonomy_mod, _g = _load_modules()
    try:
        _seed_all(manager)
        _edit_policy(home, mode="propose")
        owner = autonomy_mod.AutonomyStore(_Ctx()).ensure()["owner_entity_id"]
        _raise_drive(drives_mod, contracts, owner)
        orch = agency.AgencyOrchestrator(_Ctx())
        report = orch.run_cycle(now=NOW)
        journal = orch.journal()
    finally:
        manager.unload()
    assert report.decisions_confirmation == 1
    assert report.actions_executed == 0
    assert journal[0]["verification"] == "not_run"
    assert journal[0]["reflection_id"] == ""


def test_tripped_breaker_pauses_the_cycle():
    home = get_hermes_home()
    manager, agency, contracts, drives_mod, _c, autonomy_mod, _g = _load_modules()
    try:
        _seed_all(manager)
        _edit_policy(home, mode="local")
        store = autonomy_mod.AutonomyStore(_Ctx())
        owner = store.ensure()["owner_entity_id"]
        _raise_drive(drives_mod, contracts, owner)
        store.trip_circuit_breaker("operator_pause_for_test")
        orch = agency.AgencyOrchestrator(_Ctx())
        report = orch.run_cycle(now=NOW)
        journal = orch.journal()
    finally:
        manager.unload()
    assert report.status == "paused"
    assert report.proposals_considered == 0
    assert journal[0]["status"] == "paused"


def test_allowed_action_without_executor_is_skipped_not_executed():
    home = get_hermes_home()
    manager, agency, contracts, _d, _c, autonomy_mod, goals_mod = _load_modules()
    try:
        _seed_all(manager)
        _edit_policy(home, mode="bounded", bounded_allowlist=["goal_update"])
        goals = goals_mod.GoalStore(_Ctx())
        goal = goals.create(title="Ship the thing", description="Do it",
                            priority=1, next_action="Write the code")
        goals.update(goal["goal_id"], {"status": "active"}, "activate")
        orch = agency.AgencyOrchestrator(_Ctx())
        report = orch.run_cycle(now=NOW)
        journal = orch.journal()
    finally:
        manager.unload()
    assert report.decisions_allow == 1
    assert report.actions_executed == 0
    assert journal[0]["actions_skipped"] == 1
    assert journal[0]["verification"] == "not_executed_no_executor"
    assert journal[0]["selected_goal_id"] == goal["goal_id"]


def test_curiosity_candidate_executes_and_records_attempt():
    home = get_hermes_home()
    manager, agency, contracts, _d, curiosity_mod, autonomy_mod, _g = _load_modules()
    try:
        _seed_all(manager)
        _edit_policy(home, mode="local")
        owner = autonomy_mod.AutonomyStore(_Ctx()).ensure()["owner_entity_id"]
        store = curiosity_mod.CuriosityStore(_Ctx())
        question = store.add_question(contracts.CuriosityQuestion(
            question_id=str(uuid.uuid4()), owner_entity_id=owner,
            question="What does the local state contain?",
            status="open", novelty=0.9, uncertainty=0.9, relevance=0.9,
            expected_value=0.9, cost=0.1, risk_class=0,
            source=contracts.Provenance(source_type="curiosity", source_id="pytest"),
            created_at=TS,
        ))
        orch = agency.AgencyOrchestrator(_Ctx())
        report = orch.run_cycle(now=NOW)
        after = {q.question_id: q for q in store.questions()}[question.question_id]
    finally:
        manager.unload()
    assert report.actions_executed == 1
    assert after.attempts == 1
    assert after.status == "investigating"


def test_executor_failure_fails_the_cycle_honestly():
    home = get_hermes_home()
    manager, agency, contracts, drives_mod, _c, autonomy_mod, _g = _load_modules()
    try:
        _seed_all(manager)
        _edit_policy(home, mode="local")
        owner = autonomy_mod.AutonomyStore(_Ctx()).ensure()["owner_entity_id"]
        _raise_drive(drives_mod, contracts, owner)

        def boom(proposal, candidate):
            raise RuntimeError("executor exploded")

        orch = agency.AgencyOrchestrator(_Ctx(), executors={"world_get": boom})
        report = orch.run_cycle(now=NOW)
        journal = orch.journal()
    finally:
        manager.unload()
    assert report.status == "failed"
    assert report.actions_failed == 1
    assert report.actions_executed == 0
    assert journal[0]["verification"] == "failed"


def test_selection_is_capped_and_journal_is_bounded():
    home = get_hermes_home()
    manager, agency, contracts, drives_mod, curiosity_mod, autonomy_mod, _g = _load_modules()
    try:
        _seed_all(manager)
        _edit_policy(home, mode="local")
        owner = autonomy_mod.AutonomyStore(_Ctx()).ensure()["owner_entity_id"]
        _raise_drive(drives_mod, contracts, owner, "curiosity")
        _raise_drive(drives_mod, contracts, owner, "creation")
        store = curiosity_mod.CuriosityStore(_Ctx())
        for index in range(3):
            store.add_question(contracts.CuriosityQuestion(
                question_id=str(uuid.uuid4()), owner_entity_id=owner,
                question=f"Open question number {index}?",
                status="open", novelty=0.9, uncertainty=0.9, relevance=0.9,
                expected_value=0.9, cost=0.1, risk_class=0,
                source=contracts.Provenance(source_type="curiosity", source_id="pytest"),
                created_at=TS,
            ))
        orch = agency.AgencyOrchestrator(_Ctx({"agency_max_candidates": 2}))
        report = orch.run_cycle(now=NOW)
    finally:
        manager.unload()
    assert report.proposals_considered == 2


def test_journal_symlink_refused_and_disabled_refused():
    home = get_hermes_home()
    manager, agency, *_ = _load_modules()
    try:
        _seed_all(manager)
        orch = agency.AgencyOrchestrator(_Ctx())
        orch.run_cycle(now=NOW)
        journal_path = home / "entity" / "agency_journal.jsonl"
        target = home / "entity" / "journal-target.jsonl"
        target.write_bytes(journal_path.read_bytes())
        journal_path.unlink()
        journal_path.symlink_to(target)
        with pytest.raises(agency.AgencyError):
            orch.run_cycle(now=NOW)
        with pytest.raises(agency.AgencyError):
            agency.AgencyOrchestrator(_Ctx({"agency_enabled": False})).run_cycle(now=NOW)
    finally:
        manager.unload()


def test_a_b_a_profile_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    manager, agency, *_ = _load_modules()
    try:
        _seed_all(manager)
        orch_a = agency.AgencyOrchestrator(_Ctx())
        orch_a.run_cycle(now=NOW)
        assert len(orch_a.journal()) == 1
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            manager.invoke_hook("on_session_start", session_id="b", model="model-b")
            orch_b = agency.AgencyOrchestrator(_Ctx())
            assert orch_b.journal() == []
        finally:
            reset_hermes_home_override(token)
        restored = agency.AgencyOrchestrator(_Ctx())
    finally:
        manager.unload()
    assert len(restored.journal()) == 1
