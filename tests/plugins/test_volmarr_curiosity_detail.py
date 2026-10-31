"""Contracts for the curiosity detail reconciliation (Slice 108).

Self-Aware Agency roadmap §10, reconciled against the already-banked
Emergent Agency Phase 4 curiosity frontier (Slice 94): the §10.2
origin (derived deterministically from provenance, or explicit from
the §10.4 list), the §10.3 priority product (usefulness defaults to
expected_value, affordability is 1 - cost, identity_relevance is
explicit), the §10.5 budget block evaluated read-only with cloud
refused at the default zero budget, and §10.6 outcomes (unknown is
valid; deeper_question must name its question; uncertainty_reduced
must strictly lower uncertainty) — all in one bounded log beside the
Phase 4 store, no second curiosity engine. Tests load through real
plugin discovery.
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

ENABLED = {"curiosity_detail_enabled": True}
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
            importlib.import_module(f"{package}.curiosity_detail"),
            importlib.import_module(f"{package}.agency_contracts"),
            importlib.import_module(f"{package}.curiosity"),
        )
    except Exception:
        manager.unload()
        raise


def _setup(mods, config=None):
    _m, _d, _c, curiosity = mods
    ctx = _Ctx(config)
    store = curiosity.CuriosityStore(ctx)
    owner = store.ensure()["owner_entity_id"]
    return ctx, store, owner


def _question(mods, owner, *, source_type="curiosity",
              text="Why did the local reflex route fail?", **overrides):
    contracts = mods[2]
    values = dict(
        question_id=str(uuid.uuid4()), owner_entity_id=owner,
        question=text, status="open", novelty=0.58, uncertainty=0.91,
        relevance=0.77, expected_value=0.86, cost=0.14, risk_class=1,
        source=contracts.Provenance(source_type=source_type, source_id="pytest"),
        created_at=TS,
    )
    values.update(overrides)
    return contracts.CuriosityQuestion(**values)


def test_disabled_by_default():
    mods = _load_modules()
    detail = mods[1]
    try:
        ctx, _store, owner = _setup(mods)
        service = detail.CuriosityDetailService(ctx)
        assessment = service.assess(
            _question(mods, owner), identity_relevance=0.62, recorded_at=TS)
        with pytest.raises(detail.CuriosityDetailError):
            service.record_assessment(assessment)
        assert detail.CuriosityDetailBridge(_Ctx()).packet_items("s1") == []
        # Assessing is pure and remains available.
        assert assessment["origin"] == "knowledge_gap"
    finally:
        mods[0].unload()


def test_assessment_derives_origin_and_section10_priority():
    mods = _load_modules()
    detail = mods[1]
    try:
        ctx, _store, owner = _setup(mods, ENABLED)
        service = detail.CuriosityDetailService(ctx)
        assessment = service.assess(
            _question(mods, owner), identity_relevance=0.62, recorded_at=TS)
        by_source = service.assess(
            _question(mods, owner, source_type="goal"),
            identity_relevance=0.5, recorded_at=TS)
        explicit = service.assess(
            _question(mods, owner), origin="contradiction",
            usefulness=0.5, identity_relevance=0.5, recorded_at=TS)
        with pytest.raises(detail.CuriosityDetailError):
            service.assess(_question(mods, owner), origin="random_wandering",
                           identity_relevance=0.5)
    finally:
        mods[0].unload()
    assert assessment["usefulness"] == pytest.approx(0.86)  # expected_value
    assert assessment["affordability"] == pytest.approx(0.86)  # 1 - cost
    expected = round(0.91 * 0.86 * 0.58 * 0.62 * 0.86, 6)
    assert assessment["priority"] == expected
    assert detail.curiosity_priority(
        uncertainty=0.91, usefulness=0.86, novelty=0.58,
        identity_relevance=0.62, affordability=0.86) == expected
    assert by_source["origin"] == "failed_goal"
    assert explicit["origin"] == "contradiction"
    assert detail.derive_origin(_question(mods, owner, source_type="goal")) \
        == "failed_goal"


def test_budget_defaults_and_evaluation():
    mods = _load_modules()
    detail = mods[1]
    try:
        ctx, _store, owner = _setup(mods, ENABLED)
        service = detail.CuriosityDetailService(ctx)
        budget = service.budget()
        good = service.assess(
            _question(mods, owner), identity_relevance=0.62, recorded_at=TS)
        allowed = service.evaluate_budget(good, investigations_today=2)
        cloud = service.evaluate_budget(
            good, investigations_today=0, cloud_requested=True)
        exhausted = service.evaluate_budget(good, investigations_today=8)
        too_long = service.evaluate_budget(
            good, investigations_today=0, estimated_minutes=60)
        low = service.assess(
            _question(mods, owner), usefulness=0.2,
            identity_relevance=0.5, recorded_at=TS)
        floored = service.evaluate_budget(low, investigations_today=0)
        tokens = service.evaluate_budget(
            good, investigations_today=0, local_tokens_today=50000)
    finally:
        mods[0].unload()
    assert budget == {
        "investigations_per_day": 8, "local_token_budget_per_day": 50000,
        "cloud_budget_usd_per_day": 0.0, "max_minutes_per_investigation": 20,
        "usefulness_floor": 0.35,
    }
    assert allowed == {"allowed": True, "reasons": ["within_budget"],
                       "budget": budget}
    assert cloud["allowed"] is False and cloud["reasons"] == ["cloud_budget_zero"]
    assert exhausted["reasons"] == ["investigations_per_day_exhausted"]
    assert too_long["reasons"] == ["investigation_too_long"]
    assert floored["reasons"] == ["usefulness_below_floor"]
    assert tokens["reasons"] == ["local_token_budget_exhausted"]


def test_outcome_kinds_and_their_bounds():
    mods = _load_modules()
    detail = mods[1]
    try:
        ctx, _store, owner = _setup(mods, ENABLED)
        service = detail.CuriosityDetailService(ctx)
        question = _question(mods, owner)
        unknown = service.build_outcome(
            question, outcome="unknown", summary="No evidence found locally.",
            recorded_at=TS)
        reduced = service.build_outcome(
            question, outcome="uncertainty_reduced",
            summary="Local docs explain the failure class.",
            new_uncertainty=0.4, recorded_at=TS)
        with pytest.raises(detail.CuriosityDetailError):
            service.build_outcome(
                question, outcome="uncertainty_reduced", summary="No change.",
                new_uncertainty=0.91, recorded_at=TS)
        with pytest.raises(detail.CuriosityDetailError):
            service.build_outcome(
                question, outcome="deeper_question", summary="A deeper one.",
                recorded_at=TS)
        deeper = service.build_outcome(
            question, outcome="deeper_question", summary="A deeper one.",
            deeper_question="Which operation class is affected?",
            recorded_at=TS)
        with pytest.raises(detail.CuriosityDetailError):
            service.build_outcome(
                question, outcome="wandering", summary="Nope.", recorded_at=TS)
    finally:
        mods[0].unload()
    assert unknown["outcome"] == "unknown"  # "unknown" is a valid outcome
    assert reduced["new_uncertainty"] == pytest.approx(0.4)
    assert deeper["deeper_question"] == "Which operation class is affected?"


def test_record_writes_only_its_own_log_and_rotates():
    home = get_hermes_home()
    mods = _load_modules()
    detail = mods[1]
    try:
        ctx, store, owner = _setup(
            mods, {**ENABLED, "curiosity_detail_log_limit": 10})
        question = _question(mods, owner)
        store.add_question(question)
        watched = home / "entity" / "curiosity.yaml"
        before = hashlib.sha256(watched.read_bytes()).hexdigest()
        service = detail.CuriosityDetailService(ctx)
        first = service.assess(question, identity_relevance=0.62, recorded_at=TS)
        service.record_assessment(first)
        service.record_outcome(service.build_outcome(
            question, outcome="unknown", summary="No local evidence.",
            recorded_at=TS))
        for _index in range(9):
            service.record_assessment(service.assess(
                _question(mods, owner), identity_relevance=0.5, recorded_at=TS))
        after = hashlib.sha256(watched.read_bytes()).hexdigest()
        rows = service.records()
        outcomes = service.outcomes_for(question.question_id)
    finally:
        mods[0].unload()
    # Recording applied nothing to the Phase 4 store.
    assert before == after
    assert len(rows) == 10
    assert rows[0]["record_id"] != first["record_id"]
    # Rotation dropped only the first assessment; the outcome remains.
    assert len(outcomes) == 1 and outcomes[0]["outcome"] == "unknown"


def test_outcomes_for_and_latest_assessment():
    mods = _load_modules()
    detail = mods[1]
    try:
        ctx, _store, owner = _setup(mods, ENABLED)
        service = detail.CuriosityDetailService(ctx)
        question = _question(mods, owner)
        other = _question(mods, owner, text="Another question?")
        service.record_assessment(service.assess(
            question, identity_relevance=0.62, recorded_at=TS))
        service.record_outcome(service.build_outcome(
            question, outcome="answered", summary="Found in local docs.",
            new_uncertainty=0.0, recorded_at=TS))
        service.record_outcome(service.build_outcome(
            other, outcome="unknown", summary="Nothing local.", recorded_at=TS))
        outcomes = service.outcomes_for(question.question_id)
        latest = service.latest_assessment()
    finally:
        mods[0].unload()
    assert len(outcomes) == 1 and outcomes[0]["outcome"] == "answered"
    assert latest["question_id"] == question.question_id


def test_tampered_priority_and_symlink_refused_and_packet_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    detail = mods[1]
    try:
        ctx, _store, owner = _setup(mods, ENABLED)
        service = detail.CuriosityDetailService(ctx)
        question = _question(mods, owner)
        service.record_assessment(service.assess(
            question, identity_relevance=0.62, recorded_at=TS))
        items = detail.CuriosityDetailBridge(ctx).packet_items("s1")
        path = service.path()
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["priority"] = 0.99  # disagrees with the §10.3 function
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        with pytest.raises(detail.CuriosityDetailError):
            service.records()
        # Restore a valid log by re-recording cleanly in a fresh file.
        path.unlink()
        service.record_assessment(service.assess(
            question, identity_relevance=0.62, recorded_at=TS))
        target = tmp_path / "elsewhere.jsonl"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
        with pytest.raises(detail.CuriosityDetailError):
            service.records()
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            ctx_b, _store_b, _owner_b = _setup(mods, ENABLED)
            rows_b = detail.CuriosityDetailService(ctx_b).records()
            items_b = detail.CuriosityDetailBridge(ctx_b).packet_items("s1")
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert len(items) == 1
    assert items[0].source == "curiosity_detail"
    assert "origin knowledge_gap" in items[0].content
    assert rows_b == []
    assert items_b == []
