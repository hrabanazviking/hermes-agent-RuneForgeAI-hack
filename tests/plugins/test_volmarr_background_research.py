"""Contracts for background curiosity and research (Slice 100).

Emergent Agency Phase 10 (roadmap §17): low-cost exploration runs
only when every gate holds — no urgent user goal pending, health
good (fresh heartbeat), the daily resource budget permits, and the
curiosity frontier has a sufficiently valuable open question. The
first safe forms are local only (inspect local stores, examine own
metrics, compare self-model claims, find documentation/state
inconsistencies, deterministic experiment); external/network forms
are refused outright. One explicit run investigates one question
through the Phase 4 attempt bounds and writes only its own bounded
log record besides. Tests load the module through real plugin
discovery with a minimal config stub.
"""

from __future__ import annotations

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
ENABLED = {"background_research_enabled": True}


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
            importlib.import_module(f"{package}.background_research"),
            importlib.import_module(f"{package}.curiosity"),
            importlib.import_module(f"{package}.agency_contracts"),
            importlib.import_module(f"{package}.goals"),
            importlib.import_module(f"{package}.heartbeat"),
            importlib.import_module(f"{package}.metacognition"),
            importlib.import_module(f"{package}.self_model"),
        )
    except Exception:
        manager.unload()
        raise


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _setup(mods, config=None):
    """Ensure every local store and return (service, curiosity, owner)."""
    _m, bg, curiosity, contracts, goals, heartbeat, metacognition, self_model = mods
    ctx = _Ctx(config)
    store = curiosity.CuriosityStore(ctx)
    owner = store.ensure()["owner_entity_id"]
    goals.GoalStore(ctx).ensure()
    metacognition.MetacognitionStore(ctx).ensure()
    self_model.SelfModelStore(ctx).ensure()
    return bg.BackgroundResearchService(ctx), store, owner, ctx


def _pulse(mods, ctx) -> None:
    heartbeat = mods[5]
    store = heartbeat.HeartbeatStore(ctx)
    store.ensure()
    store.pulse("manual")


def _question(contracts, owner, text="Why has local cognition latency increased?",
              *, novelty=0.72, uncertainty=0.81, relevance=0.77,
              expected_value=0.69, cost=0.18, risk_class=1):
    return contracts.CuriosityQuestion(
        question_id=str(uuid.uuid4()),
        owner_entity_id=owner,
        question=text,
        status="open",
        novelty=novelty,
        uncertainty=uncertainty,
        relevance=relevance,
        expected_value=expected_value,
        cost=cost,
        risk_class=risk_class,
        source=contracts.Provenance(source_type="curiosity", source_id="pytest"),
        created_at=TS,
    )


def test_disabled_by_default_and_no_log_created():
    home = get_hermes_home()
    mods = _load_modules()
    try:
        service, _store, _owner, _ctx = _setup(mods)
        with pytest.raises(mods[1].BackgroundResearchError):
            service.run_once(now=_now())
    finally:
        mods[0].unload()
    assert not (home / "entity" / "background_research.jsonl").exists()


def test_external_and_unknown_forms_are_refused():
    mods = _load_modules()
    try:
        service, _store, _owner, _ctx = _setup(mods, ENABLED)
        for form in ("web_research", "repository_discovery", "external_reading", "nonsense"):
            with pytest.raises(mods[1].BackgroundResearchError):
                service.run_once(form, now=_now())
    finally:
        mods[0].unload()


def test_gates_block_without_health_or_valuable_question():
    mods = _load_modules()
    try:
        service, _store, _owner, _ctx = _setup(mods, ENABLED)
        report = service.run_once(now=_now())
        gates = service.gates(now=_now())
    finally:
        mods[0].unload()
    assert report["ran"] is False
    assert "health_good" in report["blocked_by"]
    assert "valuable_question" in report["blocked_by"]
    assert gates["no_urgent_user_goal"] is True
    assert gates["budget_permits"] is True


def test_successful_run_records_attempt_log_and_packet():
    home = get_hermes_home()
    mods = _load_modules()
    bg = mods[1]
    try:
        service, store, owner, ctx = _setup(mods, ENABLED)
        _pulse(mods, ctx)
        question = _question(mods[3], owner)
        store.add_question(question)
        goals_before = (home / "entity" / "goals.yaml").read_bytes()
        report = service.run_once("inspect_local_stores", now=_now())
        after = {q.question_id: q for q in store.questions()}[question.question_id]
        records = bg.ResearchLog(ctx).records()
        items = bg.BackgroundResearchBridge(ctx).packet_items("s1")
    finally:
        mods[0].unload()
    assert report["ran"] is True
    assert report["question_id"] == question.question_id
    assert report["detail"]["questions"] == 1
    assert after.attempts == 1
    assert after.status == "investigating"
    assert len(records) == 1
    assert records[0]["form"] == "inspect_local_stores"
    assert records[0]["outcome"] == "completed"
    # The run is read-only apart from the curiosity attempt + its log:
    assert (home / "entity" / "goals.yaml").read_bytes() == goals_before
    assert len(items) == 1
    assert items[0].source == "background_research"
    assert "inspect_local_stores" in items[0].content


def test_urgent_user_goal_blocks_and_archiving_unblocks():
    mods = _load_modules()
    goals_mod = mods[4]
    try:
        service, store, owner, ctx = _setup(mods, ENABLED)
        _pulse(mods, ctx)
        store.add_question(_question(mods[3], owner))
        goal_store = goals_mod.GoalStore(ctx)
        normal = goal_store.create(
            title="Normal goal", description="d", priority=50,
            next_action="wait", urgency="normal",
        )
        first = service.run_once(now=_now())
        store.add_question(_question(mods[3], owner, "A second open question?"))
        urgent = goal_store.create(
            title="Urgent goal", description="d", priority=90,
            next_action="now", urgency="urgent",
        )
        blocked = service.run_once(now=_now())
        goal_store.update(urgent["goal_id"], {"status": "archived"}, "done")
        goal_store.update(normal["goal_id"], {"status": "archived"}, "done")
    finally:
        mods[0].unload()
    assert first["ran"] is True
    assert blocked["ran"] is False
    assert blocked["blocked_by"] == ["no_urgent_user_goal"]


def test_daily_budget_gate_blocks_beyond_budget():
    mods = _load_modules()
    config = dict(ENABLED, background_research_daily_budget=1)
    try:
        service, store, owner, ctx = _setup(mods, config)
        _pulse(mods, ctx)
        store.add_question(_question(mods[3], owner))
        store.add_question(_question(mods[3], owner, "Another valuable question?"))
        first = service.run_once(now=_now())
        second = service.run_once(now=_now())
    finally:
        mods[0].unload()
    assert first["ran"] is True
    assert second["ran"] is False
    assert second["blocked_by"] == ["budget_permits"]
    assert second["gates"]["runs_today"] == 1


def test_value_gate_requires_sufficiently_valuable_question():
    mods = _load_modules()
    config = dict(ENABLED, background_research_min_score=0.99)
    try:
        service, store, owner, ctx = _setup(mods, config)
        _pulse(mods, ctx)
        store.add_question(_question(mods[3], owner))
        report = service.run_once(now=_now())
    finally:
        mods[0].unload()
    assert report["ran"] is False
    assert report["blocked_by"] == ["valuable_question"]
    assert report["gates"]["top_score"] < 0.99


def test_local_forms_produce_deterministic_findings():
    mods = _load_modules()
    try:
        service, store, owner, ctx = _setup(mods, ENABLED)
        _pulse(mods, ctx)
        for text in ("Question one?", "Question two?", "Question three?"):
            store.add_question(_question(mods[3], owner, text))
        inconsistencies = service.run_once("find_doc_inconsistencies", now=_now())
        experiment = service.run_once("deterministic_experiment", now=_now())
        comparison = service.run_once("compare_self_model_claims", now=_now())
    finally:
        mods[0].unload()
    assert inconsistencies["ran"] is True
    assert inconsistencies["detail"]["inconsistencies"] == 0
    assert experiment["detail"]["deterministic"] == "true"
    assert experiment["detail"]["questions_scored"] == 3
    assert comparison["detail"]["claims"] == 0
    assert comparison["detail"]["weakest_claim"] == "none"


def test_log_symlink_refusal_and_a_b_a_profile_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    bg = mods[1]
    try:
        service, store, owner, ctx = _setup(mods, ENABLED)
        _pulse(mods, ctx)
        store.add_question(_question(mods[3], owner))
        assert service.run_once(now=_now())["ran"] is True
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            service_b, _store_b, _owner_b, ctx_b = _setup(mods, ENABLED)
            assert bg.ResearchLog(ctx_b).records() == []
            assert bg.BackgroundResearchBridge(ctx_b).packet_items("s1") == []
        finally:
            reset_hermes_home_override(token)
        records_a = bg.ResearchLog(ctx).records()
        path = get_hermes_home() / "entity" / "background_research.jsonl"
        target = get_hermes_home() / "entity" / "target.jsonl"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
        with pytest.raises(bg.BackgroundResearchError):
            bg.ResearchLog(ctx).records()
    finally:
        mods[0].unload()
    assert len(records_a) == 1
