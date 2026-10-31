"""Contracts for the proposal-only agency routine (Slice 97).

Emergent Agency Phase 7 (roadmap §14): the "Volmarr Agency Review"
routine is disabled by default, installed only explicitly and paused
by default, local-first, one bounded run per invocation, bounded in
proposals / runtime / model calls (zero spent), and non-destructive:
it proposes intrinsic goals, research questions, maintenance tasks,
project improvements, and self-improvement experiments — and executes
nothing. Repetition is measured by fingerprint suppression, and the
evaluation counts are read back from the bounded log.
"""

from __future__ import annotations

import hashlib
import importlib
import uuid
from datetime import datetime, timezone

import pytest

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)

TS = "2026-10-30T12:00:00Z"
NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
ENABLED = {"agency_routine_enabled": True}


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
            importlib.import_module(f"{package}.agency_routines"),
            importlib.import_module(f"{package}.agency_contracts"),
            importlib.import_module(f"{package}.drives"),
            importlib.import_module(f"{package}.curiosity"),
            importlib.import_module(f"{package}.autonomy"),
            importlib.import_module(f"{package}.goals"),
            importlib.import_module(f"{package}.self_model"),
        )
    except Exception:
        manager.unload()
        raise


def _seed_all(manager):
    manager.invoke_hook("on_session_start", session_id="one", model="model-a")


def _raise_drive(drives_mod, contracts, owner, drive_id="curiosity"):
    store = drives_mod.DriveStore(_Ctx())
    store.set_drive(contracts.DriveState(
        drive_id=drive_id, owner_entity_id=owner, enabled=True,
        baseline=0.55, activation=0.9, satisfaction=0.0,
        source=contracts.Provenance(source_type="drive", source_id="pytest"),
        updated_at=TS,
    ))
    return store


def _snapshot(home, *relative):
    return {
        rel: hashlib.sha256((home / rel).read_bytes()).hexdigest()
        for rel in relative
        if (home / rel).is_file()
    }


def test_disabled_by_default_and_no_packet():
    manager, routines, *_ = _load_modules()
    try:
        _seed_all(manager)
        service = routines.AgencyRoutineService(_Ctx())
        assert service.enabled() is False
        with pytest.raises(routines.AgencyRoutineError):
            service.run_once(now=NOW)
        assert routines.AgencyRoutineBridge(_Ctx()).packet_items("s1") == []
        assert not (get_hermes_home() / "entity" / "agency_proposals.jsonl").exists()
    finally:
        manager.unload()


def test_empty_enabled_run_is_bounded_and_logged():
    manager, routines, *_ = _load_modules()
    try:
        _seed_all(manager)
        service = routines.AgencyRoutineService(_Ctx(ENABLED))
        report = service.run_once(now=NOW)
        log = service.log()
        evaluation = service.evaluation()
    finally:
        manager.unload()
    assert report.status == "completed"
    assert report.proposals == ()
    assert report.model_calls_used == 0
    assert report.truncated is False
    assert len(log) == 1
    assert log[0]["candidates_considered"] == 0
    assert evaluation["runs"] == 1
    assert evaluation["proposals_total"] == 0


def test_proposals_cover_kinds_and_execute_nothing():
    home = get_hermes_home()
    (manager, routines, contracts, drives_mod, curiosity_mod,
     autonomy_mod, goals_mod, self_model_mod) = _load_modules()
    try:
        _seed_all(manager)
        owner = autonomy_mod.AutonomyStore(_Ctx()).ensure()["owner_entity_id"]
        _raise_drive(drives_mod, contracts, owner)
        curiosity = curiosity_mod.CuriosityStore(_Ctx())
        curiosity.add_question(contracts.CuriosityQuestion(
            question_id=str(uuid.uuid4()), owner_entity_id=owner,
            question="What does the local state contain?",
            status="open", novelty=0.9, uncertainty=0.9, relevance=0.9,
            expected_value=0.9, cost=0.1, risk_class=0,
            source=contracts.Provenance(source_type="curiosity", source_id="pytest"),
            created_at=TS,
        ))
        goals = goals_mod.GoalStore(_Ctx())
        blocked = goals.create(title="Fix the gate", description="Unblock it",
                               priority=1, next_action="Inspect the gate")
        goals.update(blocked["goal_id"], {"status": "blocked"}, "block")
        active = goals.create(title="Polish the hall", description="Improve it",
                              priority=2, next_action="Draft the polish")
        goals.update(active["goal_id"], {"status": "active"}, "activate")
        self_model = self_model_mod.SelfModelStore(_Ctx())
        self_model.propose(contracts.SelfClaim(
            claim_id=str(uuid.uuid4()), owner_entity_id=owner,
            domain="limitation", key="slow-recall",
            statement="Recall is slower than it should be.",
            confidence=0.3,
            source=contracts.Provenance(source_type="reflection", source_id="pytest"),
            first_seen_at=TS,
        ))
        watched = (
            "entity/motivation.yaml", "entity/curiosity.yaml",
            "entity/goals.yaml", "entity/autonomy_state.json",
            "entity/autonomy_policy.yaml", "entity/self_model.yaml",
        )
        before = _snapshot(home, *watched)
        service = routines.AgencyRoutineService(_Ctx(ENABLED))
        report = service.run_once(now=NOW)
        after = _snapshot(home, *watched)
        packet = routines.AgencyRoutineBridge(_Ctx(ENABLED)).packet_items("s1")
    finally:
        manager.unload()
    kinds = {proposal["kind"] for proposal in report.proposals}
    assert kinds == {
        "intrinsic_goal", "research_question", "maintenance_task",
        "project_improvement", "self_improvement_experiment",
    }
    # Non-destructive: every source store is byte-identical after the run.
    assert before == after
    assert report.model_calls_used == 0
    assert len(packet) == 1
    assert packet[0].source == "agency_routine"
    assert "nothing was executed" in packet[0].content


def test_second_run_suppresses_repeats_and_evaluation_counts_them():
    manager, routines, contracts, drives_mod, _c, autonomy_mod, _g, _s = _load_modules()
    try:
        _seed_all(manager)
        owner = autonomy_mod.AutonomyStore(_Ctx()).ensure()["owner_entity_id"]
        _raise_drive(drives_mod, contracts, owner)
        service = routines.AgencyRoutineService(_Ctx(ENABLED))
        first = service.run_once(now=NOW)
        second = service.run_once(now=NOW)
        evaluation = service.evaluation()
    finally:
        manager.unload()
    assert len(first.proposals) == 1
    assert second.proposals == ()
    assert second.duplicates_suppressed == 1
    assert evaluation["runs"] == 2
    assert evaluation["proposals_total"] == 1
    assert evaluation["duplicates_suppressed"] == 1
    assert evaluation["repetition_rate"] > 0.0
    assert evaluation["proposals_per_kind"]["intrinsic_goal"] == 1


def test_max_proposals_caps_and_truncates():
    manager, routines, contracts, drives_mod, curiosity_mod, autonomy_mod, _g, _s = _load_modules()
    try:
        _seed_all(manager)
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
        service = routines.AgencyRoutineService(
            _Ctx({**ENABLED, "agency_routine_max_proposals": 2}))
        report = service.run_once(now=NOW)
    finally:
        manager.unload()
    assert len(report.proposals) == 2
    assert report.truncated is True
    assert report.candidates_considered == 5


def test_manager_definition_is_paused_first_and_bounded():
    manager, routines, *_ = _load_modules()
    try:
        _seed_all(manager)
        routine_manager = routines.AgencyRoutineManager(_Ctx())
        script = routine_manager._script_content
    finally:
        manager.unload()
    assert routines.AGENCY_ROUTINE_NAME == "Volmarr Agency Review"
    assert routines.AGENCY_ROUTINE_SCHEDULE == "every 360m"
    assert '"agency"' in script
    assert '"run"' in script
    assert "timeout=60" in script


def test_log_symlink_refused():
    home = get_hermes_home()
    manager, routines, *_ = _load_modules()
    try:
        _seed_all(manager)
        service = routines.AgencyRoutineService(_Ctx(ENABLED))
        service.run_once(now=NOW)
        log_path = home / "entity" / "agency_proposals.jsonl"
        target = home / "entity" / "proposals-target.jsonl"
        target.write_bytes(log_path.read_bytes())
        log_path.unlink()
        log_path.symlink_to(target)
        with pytest.raises(routines.AgencyRoutineError):
            service.run_once(now=NOW)
    finally:
        manager.unload()


def test_a_b_a_profile_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    manager, routines, *_ = _load_modules()
    try:
        _seed_all(manager)
        service_a = routines.AgencyRoutineService(_Ctx(ENABLED))
        service_a.run_once(now=NOW)
        assert len(service_a.log()) == 1
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            manager.invoke_hook("on_session_start", session_id="b", model="model-b")
            service_b = routines.AgencyRoutineService(_Ctx(ENABLED))
            assert service_b.log() == []
            assert service_b.evaluation()["runs"] == 0
        finally:
            reset_hermes_home_override(token)
        restored = routines.AgencyRoutineService(_Ctx(ENABLED))
    finally:
        manager.unload()
    assert len(restored.log()) == 1
