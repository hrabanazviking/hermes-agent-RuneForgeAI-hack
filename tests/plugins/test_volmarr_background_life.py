"""Contracts for background-life integration (Slice 113).

Self-Aware Agency roadmap §15: do not create another scheduler —
use Hermes cron. The four §15 routines are registered against the
routines that already exist (frequent continuity and daily
consolidation backed; reflection and curiosity honestly unbacked),
their gates are pure functions, the daily digest extension is
named, and explicit run receipts land in one bounded log. Tests
load through real plugin discovery.
"""

from __future__ import annotations

import hashlib
import importlib
import json

import pytest

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)

ENABLED = {"background_life_enabled": True}
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
            importlib.import_module(f"{package}.background_life"),
            importlib.import_module(f"{package}.identity"),
            importlib.import_module(f"{package}.routines"),
            importlib.import_module(f"{package}.consolidation"),
        )
    except Exception:
        manager.unload()
        raise


def _setup(mods, config=None):
    identity = mods[2]
    ctx = _Ctx(config)
    owner = identity.IdentityStore(ctx).ensure().entity_id
    return ctx, owner


def test_disabled_by_default():
    mods = _load_modules()
    life = mods[1]
    try:
        ctx, _owner = _setup(mods)
        service = life.BackgroundLifeService(ctx)
        receipt = service.build_receipt(
            "frequent_continuity", outcome="completed", recorded_at=STAMP)
        with pytest.raises(life.BackgroundLifeError):
            service.record_receipt(receipt)
        assert life.BackgroundLifeBridge(_Ctx()).packet_items("s1") == []
    finally:
        mods[0].unload()
    # Building a receipt is pure and remains available.
    assert receipt["routine"] == "frequent_continuity"
    assert receipt["counts"] == {}


def test_routine_definitions_are_the_four_section15_routines():
    mods = _load_modules()
    life = mods[1]
    try:
        rows = life.routine_definitions()
        specs = life.BackgroundLifeService(_Ctx()).cron_specs()
    finally:
        mods[0].unload()
    assert [row["routine_id"] for row in rows] == [
        "frequent_continuity", "reflection", "curiosity",
        "daily_consolidation",
    ]
    assert [row["schedule"] for row in rows] == [
        "every 10m", "every 120m", "every 240m", "every 1440m"]
    # Backed honestly: the two pre-existing routines only.
    assert [row["backed"] for row in rows] == [True, False, False, True]
    assert all(row["paused_by_default"] for row in rows)
    assert all(row["llm_required"] is False for row in rows)
    assert specs[0]["name"] == "Volmarr Frequent Continuity"
    assert specs[3]["name"] == "Volmarr Daily Consolidation"
    assert specs[1]["backed"] is False and specs[2]["backed"] is False


def test_frequent_coverage_and_daily_digest_fields():
    mods = _load_modules()
    life = mods[1]
    try:
        coverage = {row["item"]: row["coverage"]
                    for row in life.frequent_coverage()}
        fields = life.daily_digest_fields()
    finally:
        mods[0].unload()
    assert coverage == {
        "heartbeat": "covered",
        "health": "partial",
        "aggregate_goals": "covered",
        "stale_blocked_goal_detection": "partial",
        "discrepancy_detection": "deferred",
    }
    assert fields == [
        "self_model_digest", "awareness_digest", "drive_state_digest",
        "curiosity_counts", "reflection_counts",
        "autonomy_action_counts", "intrinsic_goal_counts",
    ]
    assert life.DAILY_CANON_RULE == "never_rewrite_personality_canon"


def test_routine_gates():
    mods = _load_modules()
    life = mods[1]
    try:
        frequent = life.routine_gate("frequent_continuity")
        daily = life.routine_gate("daily_consolidation")
        refl_blocked = life.routine_gate("reflection")
        refl_ok = life.routine_gate(
            "reflection", reflection_trigger_pending=True)
        cur_none = life.routine_gate("curiosity")
        cur_low = life.routine_gate("curiosity", curiosity_top_score=0.05)
        cur_ok = life.routine_gate("curiosity", curiosity_top_score=0.5)
        with pytest.raises(life.BackgroundLifeError):
            life.routine_gate("not_a_routine")
        with pytest.raises(life.BackgroundLifeError):
            life.routine_gate("curiosity", curiosity_top_score=1.5)
    finally:
        mods[0].unload()
    assert frequent["allowed"] is True and daily["allowed"] is True
    assert refl_blocked["allowed"] is False
    assert refl_blocked["reason_code"] == "no_trigger_pending"
    assert refl_ok["allowed"] is True and refl_ok["selected"] == 1
    assert cur_none["reason_code"] == "no_open_question"
    assert cur_low["allowed"] is False
    assert cur_low["reason_code"] == "below_usefulness_floor"
    # At most one question, and the default is a proposal only.
    assert cur_ok["allowed"] is True and cur_ok["selected"] == 1
    assert cur_ok["default_action"] == "research_proposal"


def test_receipt_record_packet_and_source_stores_untouched():
    mods = _load_modules()
    life, routines_mod, consolidation_mod = mods[1], mods[3], mods[4]
    try:
        ctx, _owner = _setup(mods, ENABLED)
        # The backed routines' own stores: recording a receipt here
        # must not touch the consolidation checkpoint file.
        consolidation_mod.ConsolidationService(ctx).run("manual")
        checkpoint = consolidation_mod.ConsolidationStore(ctx).path()
        before = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        service = life.BackgroundLifeService(ctx)
        receipt = service.build_receipt(
            "curiosity", outcome="blocked", reason_code="no_open_question",
            counts={"open_questions": 0}, recorded_at=STAMP)
        service.record_receipt(receipt)
        rows = service.receipts()
        items = life.BackgroundLifeBridge(ctx).packet_items("s1")
        after = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    finally:
        mods[0].unload()
    assert rows[0]["record_id"] == receipt["record_id"]
    assert before == after
    assert len(items) == 1
    assert items[0].source == "background_life"
    assert "Curiosity routine last run blocked" in items[0].content
    assert routines_mod.FREQUENT_SCHEDULE == "every 10m"


def test_receipt_validation_and_rotation():
    mods = _load_modules()
    life = mods[1]
    try:
        ctx, _owner = _setup(mods, {**ENABLED, "background_life_log_limit": 10})
        service = life.BackgroundLifeService(ctx)
        with pytest.raises(life.BackgroundLifeError):
            service.build_receipt("weekly_review", outcome="completed",
                                  recorded_at=STAMP)
        with pytest.raises(life.BackgroundLifeError):
            service.build_receipt("reflection", outcome="ran",
                                  recorded_at=STAMP)
        with pytest.raises(life.BackgroundLifeError):
            service.build_receipt(
                "reflection", outcome="completed",
                reason_code="Free Text Reason", recorded_at=STAMP)
        with pytest.raises(life.BackgroundLifeError):
            service.build_receipt(
                "reflection", outcome="completed",
                counts={"notes": "free text"}, recorded_at=STAMP)
        with pytest.raises(life.BackgroundLifeError):
            service.build_receipt(
                "reflection", outcome="completed",
                counts={"runs": -1}, recorded_at=STAMP)
        first = service.build_receipt(
            "reflection", outcome="blocked",
            reason_code="no_trigger_pending", recorded_at=STAMP)
        service.record_receipt(first)
        for _index in range(10):
            service.record_receipt(service.build_receipt(
                "reflection", outcome="blocked",
                reason_code="no_trigger_pending", recorded_at=STAMP))
        rows = service.receipts()
    finally:
        mods[0].unload()
    assert len(rows) == 10
    assert rows[0]["record_id"] != first["record_id"]


def test_tampered_log_symlink_refused_and_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    life = mods[1]
    try:
        ctx, _owner = _setup(mods, ENABLED)
        service = life.BackgroundLifeService(ctx)
        service.record_receipt(service.build_receipt(
            "daily_consolidation", outcome="completed",
            counts={"goals_total": 3}, recorded_at=STAMP))
        path = service.path()
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["counts"] = {"goals_total": "three"}
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        with pytest.raises(life.BackgroundLifeError):
            service.receipts()
        path.unlink()
        service.record_receipt(service.build_receipt(
            "daily_consolidation", outcome="completed", recorded_at=STAMP))
        target = tmp_path / "elsewhere.jsonl"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
        with pytest.raises(life.BackgroundLifeError):
            service.receipts()
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            ctx_b, _owner_b = _setup(mods, ENABLED)
            rows_b = life.BackgroundLifeService(ctx_b).receipts()
            items_b = life.BackgroundLifeBridge(ctx_b).packet_items("s1")
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert rows_b == []
    assert items_b == []
