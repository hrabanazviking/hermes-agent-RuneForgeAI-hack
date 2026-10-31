"""Contracts for the agency-cycle reconciliation (Slice 110).

Self-Aware Agency roadmap §12, reconciled against the already-banked
Emergent Agency Phase 6 orchestrator (Slice 96): the twelve §12
steps in canonical order with an honest coverage mapping, the pure
seven-factor §12 ranking function, the hard maximum-actions-per-cycle
bound enforced at trace-record time, and cycle traces in one bounded
log beside the Phase 6 journal (which stays byte-identical across
recording). Tests load through real plugin discovery.
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

ENABLED = {"agency_cycle_detail_enabled": True}
CYCLE_ID = "123e4567-e89b-42d3-a456-426614174000"
STAMP = "2026-10-31T12:00:00Z"


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
            importlib.import_module(f"{package}.agency_cycle_detail"),
            importlib.import_module(f"{package}.agency"),
        )
    except Exception:
        manager.unload()
        raise


def _setup(mods, config=None):
    _m, _d, agency = mods
    ctx = _Ctx(config)
    orchestrator = agency.AgencyOrchestrator(ctx)
    owner = orchestrator._identity.ensure().entity_id
    return ctx, orchestrator, owner


def _steps(**overrides):
    steps = {step: "completed" for step in (
        "observe", "orient", "reflect_if_needed", "generate_candidates",
        "rank_candidates", "check_autonomy_policy",
        "act_or_request_approval", "verify_outcome", "record_experience",
        "reflect", "update_self_model", "emit_verdandi_events")}
    steps.update(overrides)
    return steps


def _trace(mods, ctx, **overrides):
    service = mods[1].AgencyCycleDetailService(ctx)
    values = dict(trigger="scheduled", steps=_steps(),
                  actions_proposed=2, actions_executed=1,
                  recorded_at=STAMP)
    values.update(overrides)
    return service.build_trace(CYCLE_ID, **values)


def test_disabled_by_default():
    mods = _load_modules()
    detail = mods[1]
    try:
        ctx, _orch, _owner = _setup(mods)
        service = detail.AgencyCycleDetailService(ctx)
        trace = _trace(mods, ctx)
        with pytest.raises(detail.AgencyCycleDetailError):
            service.record_trace(trace)
        assert detail.AgencyCycleDetailBridge(_Ctx()).packet_items("s1") == []
    finally:
        mods[0].unload()
    # Building a trace is pure and remains available.
    assert trace["cycle_id"] == CYCLE_ID
    assert trace["within_bound"] is True


def test_steps_and_coverage():
    coverage = None
    try:
        mods = _load_modules()
        detail = mods[1]
        coverage = detail.step_coverage()
    finally:
        mods[0].unload()
    assert [row["step"] for row in coverage] == list(detail.CYCLE_STEPS)
    by_step = {row["step"]: row["coverage"] for row in coverage}
    assert by_step["observe"] == "covered"
    assert by_step["check_autonomy_policy"] == "covered"
    assert by_step["orient"] == "partial"
    assert by_step["rank_candidates"] == "partial"
    assert by_step["reflect"] == "partial"
    assert by_step["update_self_model"] == "deferred"
    assert by_step["emit_verdandi_events"] == "deferred"
    assert sum(1 for v in by_step.values() if v == "covered") == 5
    assert sum(1 for v in by_step.values() if v == "deferred") == 3


def test_rank_score_pure_function():
    mods = _load_modules()
    detail = mods[1]
    try:
        perfect = detail.rank_score({
            "value": 1.0, "relevance": 1.0, "urgency": 1.0,
            "expected_benefit": 1.0, "cost": 0.0, "uncertainty": 0.0,
            "reversibility": 1.0})
        discounted = detail.rank_score({
            "value": 1.0, "relevance": 1.0, "urgency": 1.0,
            "expected_benefit": 1.0, "cost": 1.0, "uncertainty": 1.0,
            "reversibility": 1.0})
        with pytest.raises(detail.AgencyCycleDetailError):
            detail.rank_score({"value": 0.5})
        with pytest.raises(detail.AgencyCycleDetailError):
            detail.rank_score({
                "value": 1.5, "relevance": 1.0, "urgency": 1.0,
                "expected_benefit": 1.0, "cost": 0.0, "uncertainty": 0.0,
                "reversibility": 1.0})
    finally:
        mods[0].unload()
    assert perfect == pytest.approx(1.0)
    assert discounted == pytest.approx(0.25)
    assert detail.within_bound(3, 3) is True
    assert detail.within_bound(4, 3) is False


def test_trace_build_bounds():
    mods = _load_modules()
    detail = mods[1]
    try:
        ctx, _orch, _owner = _setup(mods, ENABLED)
        service = detail.AgencyCycleDetailService(ctx)
        with pytest.raises(detail.AgencyCycleDetailError):
            service.build_trace("not-a-uuid", trigger="scheduled",
                                steps=_steps(), actions_proposed=1,
                                actions_executed=0)
        missing = _steps()
        del missing["reflect"]
        with pytest.raises(detail.AgencyCycleDetailError):
            _trace(mods, ctx, steps=missing)
        with pytest.raises(detail.AgencyCycleDetailError):
            _trace(mods, ctx, steps=_steps(observe="running"))
        with pytest.raises(detail.AgencyCycleDetailError):
            _trace(mods, ctx, actions_proposed=1, actions_executed=2)
        # The hard bound: 4 executed against the default cap of 3.
        with pytest.raises(detail.AgencyCycleDetailError):
            _trace(mods, ctx, actions_proposed=5, actions_executed=4)
        with pytest.raises(detail.AgencyCycleDetailError):
            _trace(mods, ctx, max_actions=11)
        trace = _trace(mods, ctx, actions_proposed=5, actions_executed=4,
                       max_actions=5)
    finally:
        mods[0].unload()
    assert trace["max_actions"] == 5
    assert [entry["step"] for entry in trace["steps"]] == \
        list(detail.CYCLE_STEPS)


def test_record_lookup_and_journal_untouched():
    home = get_hermes_home()
    mods = _load_modules()
    detail = mods[1]
    try:
        ctx, orchestrator, _owner = _setup(mods, ENABLED)
        orchestrator.run_cycle("scheduled")
        journal = home / "entity" / "agency_journal.jsonl"
        before = hashlib.sha256(journal.read_bytes()).hexdigest()
        service = detail.AgencyCycleDetailService(ctx)
        trace = _trace(mods, ctx)
        service.record_trace(trace)
        found = service.trace_for_cycle(CYCLE_ID)
        missing = service.trace_for_cycle(str(uuid.uuid4()))
        after = hashlib.sha256(journal.read_bytes()).hexdigest()
    finally:
        mods[0].unload()
    # Recording a trace never touches the Phase 6 journal.
    assert before == after
    assert found["record_id"] == trace["record_id"]
    assert missing is None


def test_record_rotates():
    mods = _load_modules()
    detail = mods[1]
    try:
        ctx, _orch, _owner = _setup(
            mods, {**ENABLED, "agency_cycle_detail_log_limit": 10})
        service = detail.AgencyCycleDetailService(ctx)
        first = _trace(mods, ctx)
        service.record_trace(first)
        for _index in range(10):
            service.record_trace(_trace(mods, ctx))
        rows = service.traces()
    finally:
        mods[0].unload()
    assert len(rows) == 10
    assert rows[0]["record_id"] != first["record_id"]


def test_tampered_trace_symlink_refused_and_packet_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    detail = mods[1]
    try:
        ctx, _orch, _owner = _setup(mods, ENABLED)
        service = detail.AgencyCycleDetailService(ctx)
        service.record_trace(_trace(mods, ctx))
        items = detail.AgencyCycleDetailBridge(ctx).packet_items("s1")
        path = service.path()
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["within_bound"] = False  # disagrees with its counts
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        with pytest.raises(detail.AgencyCycleDetailError):
            service.traces()
        path.unlink()
        service.record_trace(_trace(mods, ctx))
        target = tmp_path / "elsewhere.jsonl"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
        with pytest.raises(detail.AgencyCycleDetailError):
            service.traces()
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            ctx_b, _orch_b, _owner_b = _setup(mods, ENABLED)
            rows_b = detail.AgencyCycleDetailService(ctx_b).traces()
            items_b = detail.AgencyCycleDetailBridge(ctx_b).packet_items("s1")
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert len(items) == 1
    assert items[0].source == "agency_cycle_detail"
    assert "within bound 3" in items[0].content
    assert rows_b == []
    assert items_b == []
