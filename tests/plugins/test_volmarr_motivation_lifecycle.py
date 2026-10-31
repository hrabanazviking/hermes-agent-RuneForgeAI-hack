"""Contracts for the intrinsic-motivation lifecycle (Slice 106).

Self-Aware Agency roadmap §8, reconciled against the already-banked
Emergent Agency Phase 2 drive store (Slice 91) and Phase 9 durable
intrinsic goals (Slice 99): §8.2 drive coverage is mapped onto the
existing store (direct / alias / honestly missing), and one drive
intent proposal is walked deterministically through the §8.5 stages
(drive pressure, deduplication, value/identity check, resource
check, autonomy-policy check) carrying the §8.4 motivation block.
Evaluation creates no goal and writes nothing; only an explicit
record appends to the module's own bounded log. Tests load through
real plugin discovery.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from datetime import datetime, timezone

import pytest
import yaml

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)

ENABLED = {"motivation_lifecycle_enabled": True}
NOW = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
TITLE = "Strengthen the local consolidation checkpoint"


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
            importlib.import_module(f"{package}.motivation_lifecycle"),
            importlib.import_module(f"{package}.drives"),
            importlib.import_module(f"{package}.goals"),
            importlib.import_module(f"{package}.intrinsic_goals"),
            importlib.import_module(f"{package}.autonomy"),
            importlib.import_module(f"{package}.agency_contracts"),
            importlib.import_module(f"{package}.self_model"),
        )
    except Exception:
        manager.unload()
        raise


def _setup(mods, config=None):
    _m, _lc, drives, goals, _ig, autonomy, _c, self_model = mods
    ctx = _Ctx(config)
    owner = self_model.SelfModelStore(ctx).ensure()["owner_entity_id"]
    drives.DriveStore(ctx).ensure()
    goals.GoalStore(ctx).ensure()
    autonomy.AutonomyStore(ctx).ensure()
    return ctx, owner


def _service(mods, ctx):
    return mods[1].MotivationLifecycleService(ctx)


def _pressure(mods, ctx, drive="competence"):
    _m, _lc, drives, _g, _ig, _a, contracts, _sm = mods
    store = drives.DriveStore(ctx)
    source = contracts.Provenance(
        source_type="system_observation", source_id="pytest")
    store.record_signal(drive, "frustrate", source=source, now=NOW)
    return store.record_signal(drive, "frustrate", source=source, now=NOW)


def _proposal(drive="competence", title=TITLE):
    return {"proposal": title, "drive": drive, "expected_value": 0.8}


def _stage(evaluation, name):
    return next(row for row in evaluation["stages"] if row["stage"] == name)


def test_disabled_by_default():
    mods = _load_modules()
    lifecycle = mods[1]
    try:
        ctx, _owner = _setup(mods)
        service = _service(mods, ctx)
        with pytest.raises(lifecycle.MotivationLifecycleError):
            service.record_evaluation(_proposal(), now=NOW)
        assert lifecycle.MotivationLifecycleBridge(_Ctx()).packet_items("s1") == []
        # Evaluation itself is read-only and remains available.
        assert service.evaluate(_proposal(), now=NOW)["outcome"] == "rejected"
    finally:
        mods[0].unload()


def test_coverage_maps_section8_drives_onto_existing_store():
    mods = _load_modules()
    lifecycle = mods[1]
    try:
        ctx, _owner = _setup(mods, ENABLED)
        rows = _service(mods, ctx).coverage()
    finally:
        mods[0].unload()
    assert [row["section8_drive"] for row in rows] == list(
        lifecycle.SECTION8_DRIVES)
    by_drive = {row["section8_drive"]: row for row in rows}
    assert by_drive["continuity"]["status"] == "direct"
    assert by_drive["relationship_care"]["backing_drive"] == "relationship_care"
    assert by_drive["creative_expression"]["status"] == "alias"
    assert by_drive["creative_expression"]["backing_drive"] == "creation"
    assert by_drive["resource_stewardship"]["backing_drive"] == "stewardship"
    assert by_drive["world_understanding"]["backing_drive"] == "exploration"
    for missing in ("goal_completion", "truthfulness", "system_health",
                    "self_improvement"):
        assert by_drive[missing]["status"] == "missing"
        assert by_drive[missing]["tension"] is None


def test_low_tension_is_rejected_at_drive_pressure():
    mods = _load_modules()
    try:
        ctx, _owner = _setup(mods, ENABLED)
        evaluation = _service(mods, ctx).evaluate(_proposal(), now=NOW)
    finally:
        mods[0].unload()
    assert evaluation["outcome"] == "rejected"
    stage = _stage(evaluation, "drive_pressure")
    assert stage["status"] == "fail"
    assert stage["reason"] == "tension_below_threshold"
    assert evaluation["motivation"]["drive"] == "competence"
    assert evaluation["motivation"]["score"] == pytest.approx(0.275)
    assert [row["stage"] for row in evaluation["stages"]] == list(mods[1].STAGES)


def test_pressured_proposal_awaits_approval_under_observe_policy():
    mods = _load_modules()
    try:
        ctx, _owner = _setup(mods, ENABLED)
        _pressure(mods, ctx)
        evaluation = _service(mods, ctx).evaluate(_proposal(), now=NOW)
    finally:
        mods[0].unload()
    assert evaluation["outcome"] == "awaiting_approval"
    assert _stage(evaluation, "drive_pressure")["status"] == "pass"
    assert _stage(evaluation, "deduplication")["status"] == "pass"
    assert _stage(evaluation, "value_identity_check")["status"] == "pass"
    assert _stage(evaluation, "resource_check")["status"] == "pass"
    autonomy_stage = _stage(evaluation, "autonomy_policy_check")
    assert autonomy_stage["status"] == "awaiting"
    assert autonomy_stage["reason"] == "policy_mode_requires_approval"
    assert evaluation["motivation"]["score"] == pytest.approx(0.595)


def test_pressured_proposal_is_planned_candidate_under_propose_policy():
    home = get_hermes_home()
    mods = _load_modules()
    autonomy = mods[5]
    try:
        ctx, _owner = _setup(mods, ENABLED)
        _pressure(mods, ctx)
        # Human edit of the human-authoritative policy (the only way
        # an existing policy file ever changes).
        store = autonomy.AutonomyStore(ctx)
        policy = store.policy()
        policy["mode"] = "propose"
        store.policy_path().write_text(yaml.safe_dump(policy), encoding="utf-8")
        assert (home / "entity" / "autonomy_policy.yaml").is_file()
        evaluation = _service(mods, ctx).evaluate(_proposal(), now=NOW)
    finally:
        mods[0].unload()
    assert evaluation["outcome"] == "planned_candidate"
    assert all(row["status"] == "pass" for row in evaluation["stages"])
    assert "tension 0.59" in evaluation["motivation"]["rationale_summary"] or \
        "tension 0.60" in evaluation["motivation"]["rationale_summary"]


def test_forbidden_and_unknown_drives_are_rejected():
    mods = _load_modules()
    try:
        ctx, _owner = _setup(mods, ENABLED)
        forbidden = _service(mods, ctx).evaluate(_proposal("authority"), now=NOW)
        unknown = _service(mods, ctx).evaluate(_proposal("nonsense_xyz"), now=NOW)
    finally:
        mods[0].unload()
    assert forbidden["outcome"] == "rejected"
    assert _stage(forbidden, "value_identity_check")["reason"] == "forbidden_drive"
    assert unknown["outcome"] == "rejected"
    assert _stage(unknown, "value_identity_check")["reason"] == "unknown_drive"


def test_duplicate_of_live_intrinsic_goal_is_already_exists():
    mods = _load_modules()
    intrinsic = mods[4]
    try:
        ctx, _owner = _setup(mods, ENABLED)
        _pressure(mods, ctx)
        goal = intrinsic.IntrinsicGoalService(ctx).promote(_proposal(), now=NOW)
        evaluation = _service(mods, ctx).evaluate(_proposal(), now=NOW)
    finally:
        mods[0].unload()
    assert evaluation["outcome"] == "already_exists"
    assert evaluation["existing_goal_id"] == goal["goal_id"]
    assert _stage(evaluation, "deduplication")["status"] == "duplicate"


def test_full_quota_is_rejected_at_resource_check():
    mods = _load_modules()
    try:
        ctx, _owner = _setup(mods, {**ENABLED, "intrinsic_goal_quota": 0})
        _pressure(mods, ctx)
        evaluation = _service(mods, ctx).evaluate(_proposal(), now=NOW)
    finally:
        mods[0].unload()
    assert evaluation["outcome"] == "rejected"
    stage = _stage(evaluation, "resource_check")
    assert stage["status"] == "fail"
    assert stage["reason"] == "intrinsic_goal_quota_full"


def test_record_writes_only_its_own_log_and_rotates():
    home = get_hermes_home()
    mods = _load_modules()
    lifecycle = mods[1]
    try:
        ctx, _owner = _setup(
            mods, {**ENABLED, "motivation_lifecycle_log_limit": 10})
        _pressure(mods, ctx)
        watched = [
            home / "entity" / "motivation.yaml",
            home / "entity" / "goals.yaml",
            home / "entity" / "autonomy_policy.yaml",
        ]
        before = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in watched
        }
        service = _service(mods, ctx)
        first = service.record_evaluation(_proposal(), now=NOW)
        after = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in watched
        }
        goals = mods[3].GoalStore(ctx).get()
        for index in range(11):
            service.record_evaluation(
                _proposal(title=f"Candidate {index}"), now=NOW)
        rows = service.records()
    finally:
        mods[0].unload()
    assert before == after  # evaluation + recording touched no source store
    assert goals["goals"] == {}  # and created no goal
    assert first["outcome"] == "awaiting_approval"
    assert len(rows) == 10
    assert rows[-1]["title"] == "Candidate 10"


def test_tampered_record_and_symlink_refused_and_packet_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    lifecycle = mods[1]
    try:
        ctx, _owner = _setup(mods, ENABLED)
        _pressure(mods, ctx)
        service = _service(mods, ctx)
        service.record_evaluation(_proposal(), now=NOW)
        items = lifecycle.MotivationLifecycleBridge(ctx).packet_items("s1")
        path = service.path()
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["outcome"] = "bogus_outcome"
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        with pytest.raises(lifecycle.MotivationLifecycleError):
            service.records()
        path.write_text(json.dumps({**payload, "outcome": "awaiting_approval"})
                        + "\n", encoding="utf-8")
        target = tmp_path / "elsewhere.jsonl"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
        with pytest.raises(lifecycle.MotivationLifecycleError):
            service.records()
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            ctx_b, _owner_b = _setup(mods, ENABLED)
            rows_b = _service(mods, ctx_b).records()
            items_b = lifecycle.MotivationLifecycleBridge(ctx_b).packet_items("s1")
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert len(items) == 1
    assert items[0].source == "motivation_lifecycle"
    assert "awaiting_approval" in items[0].content
    assert rows_b == []
    assert items_b == []
