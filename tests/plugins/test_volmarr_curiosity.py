"""Contracts for the curiosity engine store (Slice 94).

Emergent Agency Phase 4 (roadmap §11): a versioned
``entity/curiosity.yaml`` frontier on the Phase 0 ``CuriosityQuestion``
contract — duplicate detection with resolved-question memory, the
deterministic §11 score, bounded queue, subquestion depth limit,
cooldown + attempt-limit anti-rabbit-hole controls, cost/risk
suppression, a bounded deduplicated questions-for-user queue,
restart persistence, and A->B->A profile isolation. No research is
performed by the store: the frontier's cheapest steps are local only.
Tests load the module through real plugin discovery with a minimal
config stub.
"""

from __future__ import annotations

import importlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest

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
            importlib.import_module(f"{package}.curiosity"),
            importlib.import_module(f"{package}.agency_contracts"),
        )
    except Exception:
        manager.unload()
        raise


def _store(mod, config=None):
    store = mod.CuriosityStore(_Ctx(config))
    data = store.ensure()
    return store, data["owner_entity_id"]


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


def test_create_once_byte_stable_and_score_formula():
    home = get_hermes_home()
    manager, mod, contracts = _load_modules()
    try:
        manager.invoke_hook("on_session_start", session_id="one", model="model-a")
        path = home / "entity" / "curiosity.yaml"
        first = path.read_bytes()
        manager.invoke_hook("on_session_start", session_id="two", model="model-b")
        _store_owner = None
        store, owner = _store(mod)
        question = _question(contracts, owner)
        expected = round(0.77 * 0.81 * 0.72 * 0.69 * (1 - 0.18) * (1 - 0.1), 6)
    finally:
        manager.unload()
    assert path.read_bytes() == first
    assert mod.curiosity_score(question) == expected
    assert mod.normalize_question("  Why   HAS this? ") == "why has this"


def test_duplicate_detection_and_resolved_question_memory():
    _m, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        original = _question(contracts, owner)
        store.add_question(original)
        duplicate = _question(
            contracts, owner, "why has local cognition latency increased"
        )
        returned = store.add_question(duplicate)
        assert returned.question_id == original.question_id
        assert len(store.questions()) == 1
        store.set_status(original.question_id, "investigating")
        store.set_status(original.question_id, "resolved")
        # Resolved questions are remembered: the same text is not re-asked.
        again = store.add_question(_question(contracts, owner))
        assert again.question_id == original.question_id
        assert again.status == "resolved"
        assert len(store.questions()) == 1
        with pytest.raises(mod.CuriosityError):
            store.set_status(original.question_id, "open")
    finally:
        _m.unload()


def test_subquestion_depth_limit():
    _m, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        parent = _question(contracts, owner, "Root question?")
        store.add_question(parent)
        child = _question(contracts, owner, "Child question?")
        store.add_question(child, parent_id=parent.question_id)
        grandchild = _question(contracts, owner, "Grandchild question?")
        store.add_question(grandchild, parent_id=child.question_id)
        too_deep = _question(contracts, owner, "Too deep question?")
        with pytest.raises(mod.CuriosityError):
            store.add_question(too_deep, parent_id=grandchild.question_id)
        frontier = store.frontier(now=NOW)
        depths = {entry["question_id"]: entry["depth"] for entry in frontier}
        orphan = _question(contracts, owner, "Orphan question?")
        with pytest.raises(mod.CuriosityError):
            store.add_question(orphan, parent_id=str(uuid.uuid4()))
    finally:
        _m.unload()
    assert depths[parent.question_id] == 0
    assert depths[child.question_id] == 1
    assert depths[grandchild.question_id] == 2
    # Depth 3 exceeds the limit: refused at add time, never stored.
    assert too_deep.question_id not in depths


def test_cooldown_and_attempt_limit():
    _m, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod, {"curiosity_max_attempts": 2})
        question = _question(contracts, owner)
        store.add_question(question)
        first = store.record_attempt(question.question_id, now=NOW)
        assert first.status == "investigating"
        assert first.attempts == 1
        assert first.last_investigated_at == "2026-10-30T12:00:00Z"
        with pytest.raises(mod.CuriosityError):
            store.record_attempt(question.question_id, now=NOW + timedelta(hours=1))
        later = NOW + timedelta(hours=7)
        second = store.record_attempt(question.question_id, now=later)
        # Attempt budget spent: the question defers instead of looping.
        assert second.status == "deferred"
        assert second.attempts == 2
        with pytest.raises(mod.CuriosityError):
            store.record_attempt(question.question_id, now=later + timedelta(hours=7))
    finally:
        _m.unload()


def test_frontier_cost_risk_suppression_and_local_steps_only():
    _m, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        good = _question(contracts, owner, "Good question?")
        store.add_question(good)
        risky = _question(contracts, owner, "Risky question?", risk_class=5)
        store.add_question(risky)
        costly = _question(
            contracts, owner, "Costly question?",
            novelty=0.1, uncertainty=0.1, relevance=0.1, expected_value=0.1, cost=0.95,
        )
        store.add_question(costly)
        frontier = store.frontier(now=NOW)
    finally:
        _m.unload()
    assert [entry["question_id"] for entry in frontier] == [good.question_id]
    assert frontier[0]["cheapest_step"] == "cheap_local_inspection"
    assert frontier[0]["score"] == mod.curiosity_score(good)


def test_questions_for_user_bounded_and_deduplicated():
    _m, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        flagged = _question(contracts, owner, "Needs the user?")
        store.add_question(flagged, for_user=True)
        unflagged = _question(contracts, owner, "Internal only?")
        store.add_question(unflagged)
        queue = store.questions_for_user()
        store.set_status(flagged.question_id, "investigating")
        store.set_status(flagged.question_id, "resolved")
        after = store.questions_for_user()
    finally:
        _m.unload()
    assert [entry["question_id"] for entry in queue] == [flagged.question_id]
    assert after == []  # resolved questions leave the user queue


def test_wrong_owner_malformed_and_symlink_are_refused():
    home = get_hermes_home()
    _m, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        wrong_owner = _question(
            contracts, "00000000-0000-4000-8000-000000000000", "Wrong owner?"
        )
        with pytest.raises(mod.CuriosityError):
            store.add_question(wrong_owner)
        path = home / "entity" / "curiosity.yaml"
        original = path.read_bytes()
        path.write_text("curiosity_version: 99\n", encoding="utf-8")
        with pytest.raises(mod.CuriosityError):
            store.questions()
        path.write_bytes(original)
        target = home / "entity" / "target.yaml"
        target.write_bytes(original)
        path.unlink()
        path.symlink_to(target)
        with pytest.raises(mod.CuriosityError):
            store.questions()
    finally:
        _m.unload()


def test_restart_persistence_and_a_b_a_profile_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    _m, mod, contracts = _load_modules()
    try:
        store_a, owner_a = _store(mod)
        question = _question(contracts, owner_a)
        store_a.add_question(question)
        reloaded = mod.CuriosityStore(_Ctx())
        assert [q.question_id for q in reloaded.questions()] == [question.question_id]
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            store_b, owner_b = _store(mod)
            assert store_b.questions() == []
        finally:
            reset_hermes_home_override(token)
        restored = mod.CuriosityStore(_Ctx())
    finally:
        _m.unload()
    assert owner_a != owner_b
    assert [q.question_id for q in restored.questions()] == [question.question_id]


def test_packet_frontier_and_disabled_or_missing_fails_open():
    _m, mod, contracts = _load_modules()
    try:
        store, owner = _store(mod)
        assert mod.CuriosityBridge(_Ctx()).packet_items("s1") == []
        question = _question(contracts, owner)
        store.add_question(question)
        items = mod.CuriosityBridge(_Ctx()).packet_items("s1")
        disabled = mod.CuriosityBridge(_Ctx({"curiosity_enabled": False}))
        disabled.on_session_start(session_id="one")
        assert disabled.packet_items("s1") == []
    finally:
        _m.unload()
    assert len(items) == 1
    assert items[0].section == "current_state"
    assert items[0].source == "curiosity"
    assert "cheapest step: cheap_local_inspection" in items[0].content
