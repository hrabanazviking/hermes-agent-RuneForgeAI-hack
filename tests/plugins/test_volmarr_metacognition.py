"""Contracts for the metacognition store (Slice 93).

Emergent Agency Phase 3 (roadmap §10): a compact
``entity/metacognition.json`` summary plus a bounded, rotated
``entity/reflection_log.jsonl`` history on the Phase 0
``ReflectionRecord`` contract — deterministic calibration buckets and
labels, high-value triggers only, feedback as proposals routed through
the receiving store's own merge layer (never a direct rewrite),
restart persistence, and A->B->A profile isolation. Tests load the
module through real plugin discovery with a minimal config stub.
"""

from __future__ import annotations

import importlib
import json
import uuid

import pytest

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)

TS = "2026-10-30T12:00:00Z"


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
            importlib.import_module(f"{package}.metacognition"),
            importlib.import_module(f"{package}.agency_contracts"),
            importlib.import_module(f"{package}.self_model"),
        )
    except Exception:
        manager.unload()
        raise


def _store(mod, config=None):
    store = mod.MetacognitionStore(_Ctx(config))
    data = store.ensure()
    return store, data["owner_entity_id"]


def _record(contracts, owner, *, trigger="goal_completed", outcome="success",
            predicted=0.9, lessons=("Focused tests first reduced wasted work.",),
            source_type="reflection"):
    return contracts.ReflectionRecord(
        reflection_id=str(uuid.uuid4()),
        owner_entity_id=owner,
        trigger=trigger,
        subject_ref="goal:00000000-0000-4000-8000-000000000001",
        observed_outcome=outcome,
        source=contracts.Provenance(source_type=source_type, source_id="pytest"),
        created_at=TS,
        predicted_success=predicted,
        lessons=tuple(lessons),
    )


def test_create_once_byte_stable_and_empty_log():
    home = get_hermes_home()
    manager, mod, _c, _s = _load_modules()
    try:
        manager.invoke_hook("on_session_start", session_id="one", model="model-a")
        summary = home / "entity" / "metacognition.json"
        log = home / "entity" / "reflection_log.jsonl"
        first = summary.read_bytes()
        assert log.read_bytes() == b""
        manager.invoke_hook("on_session_start", session_id="two", model="model-b")
    finally:
        manager.unload()
    payload = json.loads(first)
    assert payload["metacognition_version"] == 1
    assert payload["total_reflections"] == 0
    assert set(payload["calibration"]) == set(mod.CALIBRATION_BUCKETS)
    assert summary.read_bytes() == first


def test_record_reflection_updates_summary_log_and_calibration():
    _m, mod, contracts, _s = _load_modules()
    try:
        store, owner = _store(mod)
        record = _record(contracts, owner)
        store.record_reflection(
            record,
            strategy_changes=("Prefer focused verification before broad tests.",),
        )
        second = _record(contracts, owner, trigger="goal_failed", outcome="failure",
                         predicted=0.9, lessons=())
        store.record_reflection(second)
        summary = store.summary()
        calibration = store.calibration()
        history = store.reflections()
    finally:
        _m.unload()
    assert summary["total_reflections"] == 2
    assert summary["last_reflection_at"] == TS
    assert summary["recent_lessons"][0]["lesson"].startswith("Focused tests")
    assert summary["recent_strategy_changes"][0]["change"].startswith("Prefer focused")
    assert calibration["0.8-1.0"] == {
        "count": 2, "successes": 1, "observed_success_rate": 0.5,
    }
    assert calibration["0.0-0.2"]["observed_success_rate"] is None
    assert [r.reflection_id for r in history] == [record.reflection_id, second.reflection_id]
    assert mod.calibration_label(record) == "calibrated"
    assert mod.calibration_label(second) == "overconfident"
    under = _record(contracts, owner, outcome="success", predicted=0.2)
    assert mod.calibration_label(under) == "underconfident"
    partial = _record(contracts, owner, outcome="partial", predicted=0.9)
    assert mod.calibration_label(partial) == "uncalibrated"
    assert mod.calibration_bucket(0.0) == "0.0-0.2"
    assert mod.calibration_bucket(1.0) == "0.8-1.0"


def test_triggers_bounded_and_no_hidden_reasoning_field():
    _m, mod, contracts, _s = _load_modules()
    try:
        store, owner = _store(mod)
        trivial = _record(contracts, owner, trigger="every_message")
        with pytest.raises(mod.MetacognitionError):
            store.record_reflection(trivial)
        wrong_owner = _record(
            contracts, "00000000-0000-4000-8000-000000000000"
        )
        with pytest.raises(mod.MetacognitionError):
            store.record_reflection(wrong_owner)
        with pytest.raises(contracts.AgencyContractError):
            contracts.ReflectionRecord.from_dict(
                {**_record(contracts, owner).to_dict(), "chain_of_thought": "secret"}
            )
    finally:
        _m.unload()


def test_log_rotation_is_bounded():
    home = get_hermes_home()
    _m, mod, contracts, _s = _load_modules()
    try:
        store, owner = _store(mod, {"metacognition_log_limit": 10})
        for _ in range(15):
            store.record_reflection(_record(contracts, owner, lessons=()))
        lines = (home / "entity" / "reflection_log.jsonl").read_text("utf-8").splitlines()
        history = store.reflections(limit=500)
        summary = store.summary()
    finally:
        _m.unload()
    assert len(lines) == 10  # rotated to the configured bound
    assert len(history) == 10
    assert summary["total_reflections"] == 15  # totals survive rotation


def test_proposals_are_pure_and_routing_uses_self_model_merge():
    home = get_hermes_home()
    _m, mod, contracts, self_mod = _load_modules()
    try:
        store, owner = _store(mod)
        self_store = self_mod.SelfModelStore(_Ctx())
        self_store.ensure()
        claim = contracts.SelfClaim(
            claim_id=str(uuid.uuid4()),
            owner_entity_id=owner,
            domain="capability",
            key="python_testing",
            statement="Focused pytest runs are reliable.",
            confidence=0.5,
            source=contracts.Provenance(source_type="tool_result", source_id="pytest"),
            first_seen_at=TS,
        )
        self_store.propose(claim)
        record = _record(contracts, owner)
        candidates = (
            {"domain": "capability", "key": "python_testing", "evidence": "positive"},
            {"domain": "capability", "key": "missing_claim", "evidence": "positive"},
        )
        proposals = store.proposals_for(
            record, self_model_candidates=candidates,
            strategy_changes=("Run focused tests first.",),
        )
        # Pure proposals: recording/routing has not happened, stores unchanged.
        before = {c.key: c for c in self_store.claims()}["python_testing"]
        assert before.confidence == 0.5
        routed = store.route_self_model_evidence(
            record, self_model_candidates=candidates
        )
        after = {c.key: c for c in self_store.claims()}["python_testing"]
        identity_bytes = (home / "entity" / "entity.yaml").read_bytes()
    finally:
        _m.unload()
    assert [p["kind"] for p in proposals] == [
        "self_model_evidence", "self_model_evidence", "strategy_update",
    ]
    assert proposals[0]["source"]["type"] == "reflection"
    # The receiving store's merge layer decided: medium (reflection)
    # evidence applies its fixed +0.08 delta; the missing claim is
    # skipped, never created by metacognition.
    assert routed == {"applied": 1, "skipped": 1}
    assert after.confidence == 0.58
    assert identity_bytes  # identity file untouched by routing


def test_wrong_owner_malformed_and_symlink_are_refused():
    home = get_hermes_home()
    _m, mod, _c, _s = _load_modules()
    try:
        store, _owner = _store(mod)
        path = home / "entity" / "metacognition.json"
        wrong = json.dumps({
            "metacognition_version": 1,
            "owner_entity_id": "00000000-0000-4000-8000-000000000000",
            "updated_at": TS,
            "total_reflections": 0,
            "calibration": {b: {"count": 0, "successes": 0} for b in mod.CALIBRATION_BUCKETS},
            "last_reflection_at": "",
            "recent_lessons": [],
            "recent_strategy_changes": [],
        }).encode()
        path.write_bytes(wrong)
        with pytest.raises(mod.MetacognitionError):
            store.summary()
        assert path.read_bytes() == wrong
        path.write_text('{"metacognition_version": 99}', encoding="utf-8")
        with pytest.raises(mod.MetacognitionError):
            store.summary()
        log = home / "entity" / "reflection_log.jsonl"
        target = home / "entity" / "target.jsonl"
        target.write_bytes(b"")
        log.unlink()
        log.symlink_to(target)
        with pytest.raises(mod.MetacognitionError):
            store.reflections()
    finally:
        _m.unload()


def test_restart_persistence_and_a_b_a_profile_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    _m, mod, contracts, _s = _load_modules()
    try:
        store_a, owner_a = _store(mod)
        store_a.record_reflection(_record(contracts, owner_a))
        reloaded = mod.MetacognitionStore(_Ctx())
        assert reloaded.summary()["total_reflections"] == 1
        assert len(reloaded.reflections()) == 1
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            store_b, owner_b = _store(mod)
            assert store_b.summary()["total_reflections"] == 0
            assert store_b.reflections() == []
        finally:
            reset_hermes_home_override(token)
        restored = mod.MetacognitionStore(_Ctx())
    finally:
        _m.unload()
    assert owner_a != owner_b
    assert restored.summary()["total_reflections"] == 1


def test_packet_lessons_and_disabled_or_missing_fails_open():
    _m, mod, contracts, _s = _load_modules()
    try:
        store, owner = _store(mod)
        assert mod.MetacognitionBridge(_Ctx()).packet_items("s1") == []
        store.record_reflection(
            _record(contracts, owner),
            strategy_changes=("Prefer focused verification.",),
        )
        items = mod.MetacognitionBridge(_Ctx()).packet_items("s1")
        disabled = mod.MetacognitionBridge(_Ctx({"metacognition_enabled": False}))
        disabled.on_session_start(session_id="one")
        assert disabled.packet_items("s1") == []
    finally:
        _m.unload()
    assert len(items) == 2  # one recent lesson + one strategy change
    assert all(
        item.section == "current_state" and item.source == "metacognition"
        for item in items
    )
