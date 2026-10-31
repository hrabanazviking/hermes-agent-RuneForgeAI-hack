"""Contracts for durable intrinsic goals (Slice 99).

Emergent Agency Phase 9 (roadmap §16): the goal ledger migrates to
schema v2 with origin preserved; drive intent proposals promote into
durable intrinsic goals under a quota; priority arbitration is a
deterministic, configurable tier order (user goals normally outrank
intrinsic ones); a user can approve, archive, or reject intrinsic
goals; rejection puts the goal's fingerprint into cooldown and
near-duplicate rewordings are refused as evasion. Tests load the
module through real plugin discovery with a minimal config stub.
"""

from __future__ import annotations

import importlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import yaml

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)


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
            importlib.import_module(f"{package}.intrinsic_goals"),
            importlib.import_module(f"{package}.goals"),
        )
    except Exception:
        manager.unload()
        raise


def _service(mod, goals_mod, config=None):
    ctx = _Ctx(config)
    goals_mod.GoalStore(ctx).ensure()
    return mod.IntrinsicGoalService(ctx), goals_mod.GoalStore(ctx)


def _proposal(text="Strengthen the local consolidation checkpoint",
              drive="competence", value=0.8):
    return {
        "origin": "intrinsic",
        "drive": drive,
        "proposal": text,
        "expected_value": value,
        "urgency": 0.5,
        "estimated_cost": "low",
        "risk": "read_only",
    }


def test_v2_ledger_create_once_and_origin_defaults():
    home = get_hermes_home()
    manager, mod, goals_mod = _load_modules()
    try:
        manager.invoke_hook("on_session_start", session_id="one", model="model-a")
        path = home / "entity" / "goals.yaml"
        first = path.read_bytes()
        manager.invoke_hook("on_session_start", session_id="two", model="model-b")
        # Create-once: the second session start left the ledger untouched.
        assert path.read_bytes() == first
        service, store = _service(mod, goals_mod)
        goal = store.create(
            title="User goal", description="", priority=70, next_action=""
        )
        reloaded = store.get(goal["goal_id"])
    finally:
        manager.unload()
    document = yaml.safe_load(first)
    assert document["goals_version"] == 2
    assert document["rejected_fingerprints"] == {}
    assert reloaded["origin"] == "user"
    assert reloaded["origin_ref"] == ""
    assert reloaded["urgency"] == "normal"
    assert reloaded["approved"] is False


def test_v1_file_migrates_with_origin_preserved_as_user():
    home = get_hermes_home()
    manager, mod, goals_mod = _load_modules()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
        path = home / "entity" / "goals.yaml"
        owner = yaml.safe_load(path.read_bytes())["owner_entity_id"]
        goal_id = str(uuid.uuid4())
        event_id = str(uuid.uuid4())
        v1 = {
            "goals_version": 1,
            "owner_entity_id": owner,
            "goals": {
                goal_id: {
                    "goal_id": goal_id,
                    "title": "Legacy goal",
                    "description": "Written before schema v2.",
                    "status": "active",
                    "priority": 40,
                    "next_action": "Keep going.",
                    "created_at": "2026-10-01T00:00:00Z",
                    "updated_at": "2026-10-01T00:00:00Z",
                    "completed_at": "",
                    "history": [{
                        "event_id": event_id,
                        "recorded_at": "2026-10-01T00:00:00Z",
                        "status": "planned",
                        "note": "Goal created.",
                    }],
                }
            },
        }
        path.write_text(yaml.safe_dump(v1), encoding="utf-8")
        store = goals_mod.GoalStore(_Ctx())
        migrated = store.ensure()
        on_disk = yaml.safe_load(path.read_text(encoding="utf-8"))
    finally:
        manager.unload()
    assert migrated["goals_version"] == 2
    assert migrated["goals"][goal_id]["origin"] == "user"
    assert on_disk["goals_version"] == 2
    assert on_disk["goals"][goal_id]["origin"] == "user"
    assert on_disk["rejected_fingerprints"] == {}


def test_promotion_creates_intrinsic_goal_and_duplicate_returns_existing():
    _m, mod, goals_mod = _load_modules()
    try:
        service, _store = _service(mod, goals_mod)
        goal = service.promote(_proposal(), now=NOW)
        assert goal["origin"] == "intrinsic"
        assert goal["origin_ref"] == "competence"
        assert goal["approved"] is False
        assert goal["priority"] == 40  # 0.8 expected value -> lower half
        again = service.promote(
            _proposal("  strengthen THE local consolidation checkpoint "),
            now=NOW,
        )
    finally:
        _m.unload()
    assert again["goal_id"] == goal["goal_id"]


def test_promotion_quota_is_enforced():
    _m, mod, goals_mod = _load_modules()
    try:
        service, _store = _service(mod, goals_mod, {"intrinsic_goal_quota": 1})
        service.promote(_proposal(), now=NOW)
        with pytest.raises(mod.IntrinsicGoalError):
            service.promote(_proposal("Map the profile's memory stores"), now=NOW)
        # Archiving frees the quota slot.
        rows = [r for r in service.arbitrate() if r["origin"] == "intrinsic"]
        service.archive(rows[0]["goal_id"])
        freed = service.promote(_proposal("Map the profile's memory stores"), now=NOW)
    finally:
        _m.unload()
    assert freed["origin"] == "intrinsic"


def test_rejection_cooldown_and_near_duplicate_evasion_refused():
    _m, mod, goals_mod = _load_modules()
    try:
        service, store = _service(mod, goals_mod)
        goal = service.promote(
            _proposal("Improve local memory consolidation reliability"), now=NOW
        )
        rejected = service.reject(goal["goal_id"], now=NOW)
        assert rejected["status"] == "archived"
        fingerprints = store.rejected_fingerprints()
        assert len(fingerprints) == 1
        with pytest.raises(mod.IntrinsicGoalError):
            service.promote(
                _proposal("Improve local memory consolidation reliability"),
                now=NOW + timedelta(hours=1),
            )
        # One extra word is a near-duplicate (Jaccard 5/6 >= 0.8): evasion.
        with pytest.raises(mod.IntrinsicGoalError):
            service.promote(
                _proposal("Improve local memory consolidation reliability today"),
                now=NOW + timedelta(hours=1),
            )
        # A genuinely different goal is not blocked by the rejection.
        other = service.promote(_proposal("Catalogue the rune library"), now=NOW)
        # After the cooldown the original may be proposed again.
        revived = service.promote(
            _proposal("Improve local memory consolidation reliability"),
            now=NOW + timedelta(hours=169),
        )
    finally:
        _m.unload()
    assert other["origin"] == "intrinsic"
    assert revived["goal_id"] != goal["goal_id"]


def test_user_actions_refuse_non_intrinsic_goals():
    _m, mod, goals_mod = _load_modules()
    try:
        service, store = _service(mod, goals_mod)
        user_goal = store.create(
            title="User's own goal", description="", priority=80, next_action=""
        )
        for action in (service.approve, service.archive, service.reject):
            with pytest.raises(mod.IntrinsicGoalError):
                action(user_goal["goal_id"])
        intrinsic = service.promote(_proposal(), now=NOW)
        approved = service.approve(intrinsic["goal_id"])
        archived = service.archive(intrinsic["goal_id"])
    finally:
        _m.unload()
    assert approved["approved"] is True
    assert archived["status"] == "archived"
    # Origin survives every update: it is never rewritten.
    assert archived["origin"] == "intrinsic"


def test_arbitration_default_and_configured_tier_order():
    _m, mod, goals_mod = _load_modules()
    try:
        service, store = _service(mod, goals_mod)
        urgent = store.create(
            title="Urgent user goal", description="", priority=10,
            next_action="", urgency="urgent",
        )
        normal = store.create(
            title="Normal user goal", description="", priority=95, next_action=""
        )
        maintenance = store.create(
            title="Continuity maintenance", description="", priority=99,
            next_action="", origin="maintenance",
        )
        approved_goal = service.promote(_proposal("Approved intrinsic"), now=NOW)
        service.approve(approved_goal["goal_id"])
        fresh = service.promote(_proposal("Fresh intrinsic"), now=NOW)
        rows = service.arbitrate()
        custom, _s2 = _service(
            mod, goals_mod,
            {"intrinsic_goal_tier_order": "new_intrinsic,approved_intrinsic"},
        )
        custom_rows = custom.arbitrate()
    finally:
        _m.unload()
    assert [row["goal_id"] for row in rows] == [
        urgent["goal_id"], normal["goal_id"], maintenance["goal_id"],
        approved_goal["goal_id"], fresh["goal_id"],
    ]
    assert [row["tier"] for row in rows] == [
        "explicit_urgent_user", "explicit_normal_user", "safety_continuity",
        "approved_intrinsic", "new_intrinsic",
    ]
    # Configured order puts new intrinsic proposals first; missing
    # tiers fall back to the roadmap order after the named ones.
    assert custom_rows[0]["goal_id"] == fresh["goal_id"]
    assert custom_rows[1]["goal_id"] == approved_goal["goal_id"]


def test_packet_top_intrinsic_and_disabled_fails_open():
    _m, mod, goals_mod = _load_modules()
    try:
        service, _store = _service(mod, goals_mod)
        bridge = mod.IntrinsicGoalBridge(_Ctx())
        assert bridge.packet_items("s1") == []
        goal = service.promote(_proposal(), now=NOW)
        items = bridge.packet_items("s1")
        disabled = mod.IntrinsicGoalBridge(_Ctx({"intrinsic_goals_enabled": False}))
        assert disabled.packet_items("s1") == []
    finally:
        _m.unload()
    assert len(items) == 1
    assert items[0].section == "current_state"
    assert items[0].source == "intrinsic_goals"
    assert items[0].record_id == goal["goal_id"]
    assert "tier new_intrinsic" in items[0].content


def test_a_b_a_profile_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    _m, mod, goals_mod = _load_modules()
    try:
        service_a, _store_a = _service(mod, goals_mod)
        goal = service_a.promote(_proposal(), now=NOW)
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            service_b, _store_b = _service(mod, goals_mod)
            assert service_b.arbitrate() == []
        finally:
            reset_hermes_home_override(token)
        restored, _s = _service(mod, goals_mod)
    finally:
        _m.unload()
    assert [row["goal_id"] for row in restored.arbitrate()] == [goal["goal_id"]]
