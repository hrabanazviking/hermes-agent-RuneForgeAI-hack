"""Contracts for the detailed reflection records (Slice 107).

Self-Aware Agency roadmap §9, reconciled against the already-banked
Emergent Agency Phase 3 metacognition store (Slice 93): the §9.2
detailed record (confidence before/after, assumptions, evidence,
error class, self-model change proposals, next test) lives in its
own bounded log beside the Phase 3 store — no second metacognition
engine — the §9.3 reflection level is a deterministic function the
stored record must agree with, and §9.4 self-model changes stay
proposal text that is never applied here. Tests load through real
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

ENABLED = {"reflection_detail_enabled": True}
CREATED = "2026-10-31T12:00:00Z"


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
            importlib.import_module(f"{package}.reflection_detail"),
            importlib.import_module(f"{package}.agency_contracts"),
            importlib.import_module(f"{package}.metacognition"),
            importlib.import_module(f"{package}.self_model"),
        )
    except Exception:
        manager.unload()
        raise


def _setup(mods, config=None):
    _m, _rd, _c, metacognition, self_model = mods
    ctx = _Ctx(config)
    owner = self_model.SelfModelStore(ctx).ensure()["owner_entity_id"]
    metacognition.MetacognitionStore(ctx).ensure()
    return ctx, owner


def _reflection(mods, owner, *, trigger="repeated_tool_failure",
                subject="goal:route-check", predicted=0.82,
                outcome="failure", lessons=("Check capability first.",)):
    contracts = mods[2]
    return contracts.ReflectionRecord(
        reflection_id=str(uuid.uuid4()),
        owner_entity_id=owner,
        trigger=trigger,
        subject_ref=subject,
        observed_outcome=outcome,
        source=contracts.Provenance(
            source_type="system_observation", source_id="pytest"),
        created_at=CREATED,
        predicted_success=predicted,
        lessons=lessons,
    )


def _detail(mods, ctx, owner, **kwargs):
    service = mods[1].ReflectionDetailService(ctx)
    record = _reflection(mods, owner, **kwargs.pop("record_kwargs", {}))
    return service.build_detail(record, **kwargs)


def test_disabled_by_default():
    mods = _load_modules()
    detail_mod = mods[1]
    try:
        ctx, owner = _setup(mods)
        service = detail_mod.ReflectionDetailService(ctx)
        detail = _detail(mods, ctx, owner, confidence_after=0.54)
        with pytest.raises(detail_mod.ReflectionDetailError):
            service.record_detail(detail)
        assert detail_mod.ReflectionDetailBridge(_Ctx()).packet_items("s1") == []
        # Building a detail is pure and remains available.
        assert detail["reflection_id"]
    finally:
        mods[0].unload()


def test_build_detail_derives_identity_fields_from_phase3_record():
    mods = _load_modules()
    try:
        ctx, owner = _setup(mods, ENABLED)
        detail = _detail(
            mods, ctx, owner,
            confidence_after=0.54,
            assumptions=["local endpoint supported required operation"],
            evidence=["execution returned unsupported capability"],
            error_class="capability_mismatch",
            self_model_changes=["reduce confidence in local capability"],
            next_test="run route health probe before retry",
        )
    finally:
        mods[0].unload()
    assert detail["reflection_version"] == 1
    assert detail["owner_entity_id"] == owner
    assert detail["recorded_at"] == CREATED
    assert detail["trigger"] == "repeated_tool_failure"
    assert detail["subject"] == "goal:route-check"
    assert detail["confidence_before"] == pytest.approx(0.82)
    assert detail["confidence_after"] == pytest.approx(0.54)
    assert detail["lesson"] == "Check capability first."
    assert detail["error_class"] == "capability_mismatch"


def test_reflection_levels_are_deterministic():
    mods = _load_modules()
    detail_mod = mods[1]
    try:
        ctx, owner = _setup(mods, ENABLED)
        deterministic = _detail(mods, ctx, owner, confidence_after=0.5)
        mismatch = _detail(
            mods, ctx, owner, confidence_after=0.5,
            record_kwargs={"trigger": "user_correction", "predicted": 0.9},
        )
        deep = _detail(
            mods, ctx, owner, confidence_after=0.3,
            error_class="identity_conflict",
            record_kwargs={"trigger": "user_correction", "predicted": 0.6},
        )
        local = _detail(
            mods, ctx, owner, confidence_after=0.6,
            evidence=["execution returned unsupported capability"],
            record_kwargs={"trigger": "user_correction", "predicted": 0.6},
        )
    finally:
        mods[0].unload()
    assert deterministic["reflection_level"] == 0
    assert mismatch["reflection_level"] == 0  # confidence/evidence mismatch
    assert deep["reflection_level"] == 2
    assert local["reflection_level"] == 1
    for detail in (deterministic, mismatch, deep, local):
        assert detail_mod.reflection_level(detail) == detail["reflection_level"]


def test_build_detail_requires_confidence_before_without_prediction():
    mods = _load_modules()
    detail_mod = mods[1]
    try:
        ctx, owner = _setup(mods, ENABLED)
        service = detail_mod.ReflectionDetailService(ctx)
        record = _reflection(mods, owner, predicted=None)
        with pytest.raises(detail_mod.ReflectionDetailError):
            service.build_detail(record, confidence_after=0.5)
        detail = service.build_detail(
            record, confidence_before=0.4, confidence_after=0.5)
    finally:
        mods[0].unload()
    assert detail["confidence_before"] == pytest.approx(0.4)


def test_record_writes_only_its_own_log_and_rotates():
    home = get_hermes_home()
    mods = _load_modules()
    detail_mod = mods[1]
    try:
        ctx, owner = _setup(
            mods, {**ENABLED, "reflection_detail_log_limit": 10})
        watched = [
            home / "entity" / "metacognition.json",
            home / "entity" / "reflection_log.jsonl",
            home / "entity" / "self_model.yaml",
        ]
        before = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in watched
        }
        service = detail_mod.ReflectionDetailService(ctx)
        first = _detail(mods, ctx, owner, confidence_after=0.54,
                        error_class="capability_mismatch")
        service.record_detail(first)
        for _index in range(10):
            service.record_detail(
                _detail(mods, ctx, owner, confidence_after=0.5))
        after = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in watched
        }
        rows = service.records()
    finally:
        mods[0].unload()
    # §9.4: recording applied nothing anywhere else, self-model
    # change proposals included.
    assert before == after
    assert len(rows) == 10
    assert rows[0]["reflection_id"] != first["reflection_id"]


def test_history_for_counts_prior_failures():
    mods = _load_modules()
    detail_mod = mods[1]
    try:
        ctx, owner = _setup(mods, ENABLED)
        service = detail_mod.ReflectionDetailService(ctx)
        service.record_detail(_detail(
            mods, ctx, owner, confidence_after=0.54,
            error_class="capability_mismatch", next_test="probe first"))
        service.record_detail(_detail(
            mods, ctx, owner, confidence_after=0.6,
            record_kwargs={"trigger": "success_verified",
                           "outcome": "success"}))
        service.record_detail(_detail(
            mods, ctx, owner, confidence_after=0.5,
            record_kwargs={"subject": "goal:other"}))
        history = service.history_for("goal:route-check")
        empty = service.history_for("goal:never-reflected")
    finally:
        mods[0].unload()
    assert history["count"] == 2
    assert history["failures"] == 1
    assert history["last_next_test"] == ""
    assert history["last_lesson"] == "Check capability first."
    assert history["last_recorded_at"] == CREATED
    assert empty == {
        "subject": "goal:never-reflected", "count": 0, "failures": 0,
        "last_lesson": "", "last_next_test": "", "last_recorded_at": "",
    }


def test_tampered_level_and_symlink_refused_and_packet_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    detail_mod = mods[1]
    try:
        ctx, owner = _setup(mods, ENABLED)
        service = detail_mod.ReflectionDetailService(ctx)
        service.record_detail(_detail(
            mods, ctx, owner, confidence_after=0.54,
            next_test="run route health probe before retry"))
        items = detail_mod.ReflectionDetailBridge(ctx).packet_items("s1")
        path = service.path()
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["reflection_level"] = 2  # disagrees with the §9.3 function
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        with pytest.raises(detail_mod.ReflectionDetailError):
            service.records()
        payload["reflection_level"] = 0
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        target = tmp_path / "elsewhere.jsonl"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
        with pytest.raises(detail_mod.ReflectionDetailError):
            service.records()
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            ctx_b, _owner_b = _setup(mods, ENABLED)
            rows_b = detail_mod.ReflectionDetailService(ctx_b).records()
            items_b = detail_mod.ReflectionDetailBridge(ctx_b).packet_items("s1")
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert len(items) == 1
    assert items[0].source == "reflection_detail"
    assert "level 0" in items[0].content
    assert "Next test: run route health probe before retry" in items[0].content
    assert rows_b == []
    assert items_b == []
