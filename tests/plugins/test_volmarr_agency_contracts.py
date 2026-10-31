"""Contracts for Emergent Agency Phase 0 (Slice 88): agency contracts
before intelligence.

Phase 0's completion gate is that the shared schemas, bounds, owner
checks, and provenance model exist and are tested before any autonomous
behavior starts. These contracts load the module through the real
plugin discovery path and exercise construction + strict round-trip
parsing only — the module carries no behavior, stores, or execution.
"""

from __future__ import annotations

import dataclasses
import importlib
import uuid

import pytest

from hermes_constants import get_hermes_home

OWNER = "11111111-1111-4111-8111-111111111111"
OTHER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
TS = "2026-10-30T12:00:00Z"


def _contracts():
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [volmarr-core]\n", encoding="utf-8"
    )
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-core"]
        return importlib.import_module(
            f"{loaded.module.__package__}.agency_contracts"
        )
    finally:
        manager.unload()


def _provenance(mod, source_type="tool_result"):
    return mod.Provenance(source_type=source_type, source_id="pytest", event_id="e1")


def _samples(mod):
    prov = _provenance(mod)
    return [
        mod.SelfClaim(
            claim_id=str(uuid.uuid4()),
            owner_entity_id=OWNER,
            domain="capability",
            key="python_debugging",
            statement="Usually effective at diagnosing Python errors.",
            confidence=0.82,
            source=prov,
            first_seen_at=TS,
            last_confirmed_at=TS,
        ),
        mod.DriveState(
            drive_id="curiosity",
            owner_entity_id=OWNER,
            enabled=True,
            baseline=0.55,
            activation=0.72,
            satisfaction=0.31,
            source=prov,
            updated_at=TS,
        ),
        mod.ReflectionRecord(
            reflection_id=str(uuid.uuid4()),
            owner_entity_id=OWNER,
            trigger="goal_completed",
            subject_ref="goal:abc",
            observed_outcome="success",
            source=prov,
            created_at=TS,
            predicted_success=0.72,
            lessons=("Run focused tests first.",),
        ),
        mod.CuriosityQuestion(
            question_id=str(uuid.uuid4()),
            owner_entity_id=OWNER,
            question="Why has local cognition latency increased?",
            status="open",
            novelty=0.72,
            uncertainty=0.81,
            relevance=0.77,
            expected_value=0.69,
            cost=0.18,
            risk_class=0,
            source=prov,
            created_at=TS,
        ),
        mod.ActionProposal(
            proposal_id=str(uuid.uuid4()),
            owner_entity_id=OWNER,
            action="run_tests",
            summary="Run the focused contract tests.",
            risk_class=1,
            estimated_cost="low",
            source=prov,
            created_at=TS,
            drive_ref="drive:competence",
        ),
        mod.PolicyDecision(
            proposal_id=str(uuid.uuid4()),
            owner_entity_id=OWNER,
            decision="allow",
            reason_code="allowed_read_only",
            risk_class=0,
            budget_remaining=True,
            policy_version=1,
            decided_at=TS,
        ),
        mod.ActionResult(
            result_id=str(uuid.uuid4()),
            proposal_id=str(uuid.uuid4()),
            owner_entity_id=OWNER,
            status="succeeded",
            summary="Tests passed.",
            source=prov,
            completed_at=TS,
        ),
        mod.AgencyCycleReport(
            cycle_id=str(uuid.uuid4()),
            owner_entity_id=OWNER,
            status="completed",
            started_at=TS,
            finished_at=TS,
            source=prov,
            proposals_considered=3,
            decisions_allow=1,
            decisions_confirmation=1,
            decisions_deny=1,
            actions_executed=1,
        ),
    ]


def test_all_eight_contracts_round_trip_strictly():
    mod = _contracts()
    for record in _samples(mod):
        payload = record.to_dict()
        assert type(record).from_dict(payload) == record


def test_provenance_accepts_every_roadmap_source_type():
    mod = _contracts()
    for source_type in mod.SOURCE_TYPES:
        prov = _provenance(mod, source_type)
        assert mod.Provenance.from_dict(prov.to_dict()) == prov
    with pytest.raises(mod.AgencyContractError):
        _provenance(mod, "conversation_transcript")


def test_owner_must_be_canonical_uuid_on_every_contract():
    mod = _contracts()
    for record in _samples(mod):
        payload = record.to_dict()
        payload["owner_entity_id"] = "not-a-uuid"
        with pytest.raises(mod.AgencyContractError):
            type(record).from_dict(payload)
        payload["owner_entity_id"] = OTHER.upper()
        with pytest.raises(mod.AgencyContractError):
            type(record).from_dict(payload)


def test_unknown_fields_are_rejected_including_hidden_reasoning():
    mod = _contracts()
    for record in _samples(mod):
        payload = record.to_dict()
        payload["chain_of_thought"] = "secret reasoning"
        with pytest.raises(mod.AgencyContractError):
            type(record).from_dict(payload)
        payload = record.to_dict()
        payload.pop(next(iter(payload)))
        with pytest.raises(mod.AgencyContractError):
            type(record).from_dict(payload)


def test_bounds_scores_risk_timestamps_and_text():
    mod = _contracts()
    prov = _provenance(mod)
    with pytest.raises(mod.AgencyContractError):
        mod.SelfClaim(
            claim_id=str(uuid.uuid4()),
            owner_entity_id=OWNER,
            domain="capability",
            key="k",
            statement="s",
            confidence=1.5,
            source=prov,
            first_seen_at=TS,
        )
    with pytest.raises(mod.AgencyContractError):
        mod.SelfClaim(
            claim_id=str(uuid.uuid4()),
            owner_entity_id=OWNER,
            domain="capability",
            key="k",
            statement="x" * 1001,
            confidence=0.5,
            source=prov,
            first_seen_at=TS,
        )
    with pytest.raises(mod.AgencyContractError):
        mod.ActionProposal(
            proposal_id=str(uuid.uuid4()),
            owner_entity_id=OWNER,
            action="run_tests",
            summary="s",
            risk_class=6,
            estimated_cost="low",
            source=prov,
            created_at=TS,
        )
    with pytest.raises(mod.AgencyContractError):
        mod.DriveState(
            drive_id="curiosity",
            owner_entity_id=OWNER,
            enabled=True,
            baseline=0.5,
            activation=0.5,
            satisfaction=0.5,
            source=prov,
            updated_at="2026-10-30T12:00:00",  # naive: no timezone
        )
    with pytest.raises(mod.AgencyContractError):
        mod.ReflectionRecord(
            reflection_id=str(uuid.uuid4()),
            owner_entity_id=OWNER,
            trigger="goal_completed",
            subject_ref="goal:abc",
            observed_outcome="success",
            source=prov,
            created_at=TS,
            lessons=tuple("lesson" for _ in range(11)),
        )


def test_cycle_report_aggregate_invariants():
    mod = _contracts()
    prov = _provenance(mod)
    with pytest.raises(mod.AgencyContractError):
        mod.AgencyCycleReport(
            cycle_id=str(uuid.uuid4()),
            owner_entity_id=OWNER,
            status="completed",
            started_at=TS,
            finished_at=TS,
            source=prov,
            proposals_considered=1,
            decisions_allow=2,
        )
    with pytest.raises(mod.AgencyContractError):
        mod.AgencyCycleReport(
            cycle_id=str(uuid.uuid4()),
            owner_entity_id=OWNER,
            status="completed",
            started_at=TS,
            finished_at=TS,
            source=prov,
            proposals_considered=5,
            decisions_allow=1,
            actions_executed=2,
        )


def test_contracts_are_frozen():
    mod = _contracts()
    record = _samples(mod)[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.confidence = 0.1
