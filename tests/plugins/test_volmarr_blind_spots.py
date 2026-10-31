"""Contracts for explicit blind-spot tracking (Slice 115).

Self-Aware Agency roadmap §17: blind spots are tracked over the
thirteen named categories with records carrying category /
evidence_count / confidence / mitigation / last_observed_at.
They affect metacognitive confidence, never become permanent
identity labels, and decay or retire after contrary evidence.
Tests load through real plugin discovery.
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

ENABLED = {"blind_spots_enabled": True}
STAMP = "2026-10-31T12:00:00Z"
LATER = "2026-10-31T13:00:00Z"


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
            importlib.import_module(f"{package}.blind_spots"),
            importlib.import_module(f"{package}.identity"),
            importlib.import_module(f"{package}.self_model"),
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
    spots = mods[1]
    try:
        ctx, _owner = _setup(mods)
        service = spots.BlindSpotService(ctx)
        with pytest.raises(spots.BlindSpotError):
            service.observe("overconfidence", confidence=0.5)
        with pytest.raises(spots.BlindSpotError):
            service.record_contrary_evidence("overconfidence")
        assert spots.BlindSpotBridge(_Ctx()).packet_items("s1") == []
    finally:
        mods[0].unload()


def test_categories_and_record_shape():
    mods = _load_modules()
    spots = mods[1]
    try:
        ctx, _owner = _setup(mods, ENABLED)
        service = spots.BlindSpotService(ctx)
        record = service.observe(
            "overconfidence", confidence=0.74,
            mitigation=["verify before claiming completion",
                        "require tool evidence"],
            observed_at=STAMP)
        current = service.current()
    finally:
        mods[0].unload()
    assert spots.categories() == [
        "confirmation_bias", "self_serving_bias", "relationship_bias",
        "overconfidence", "underconfidence", "capability_confusion",
        "source_confusion", "temporal_blindness", "goal_tunnel_vision",
        "affective_distortion", "novelty_bias", "authority_confusion",
        "unknown_unknown",
    ]
    # The §17 record shape, verbatim fields.
    assert record["category"] == "overconfidence"
    assert record["evidence_count"] == 1
    assert record["confidence"] == 0.74
    assert record["mitigation"] == [
        "verify before claiming completion", "require tool evidence"]
    assert record["last_observed_at"] == STAMP
    assert record["status"] == "active" and record["contrary_count"] == 0
    assert current == [record]


def test_observe_increments_and_carries_mitigation():
    mods = _load_modules()
    spots = mods[1]
    try:
        ctx, _owner = _setup(mods, ENABLED)
        service = spots.BlindSpotService(ctx)
        service.observe("source_confusion", confidence=0.4,
                        mitigation=["cite the source"], observed_at=STAMP)
        second = service.observe(
            "source_confusion", confidence=0.6, observed_at=LATER)
        rows = service.records()
    finally:
        mods[0].unload()
    assert second["evidence_count"] == 2
    assert second["confidence"] == 0.6
    assert second["mitigation"] == ["cite the source"]  # carried over
    assert second["last_observed_at"] == LATER
    assert len(rows) == 2 and service.current()[0]["record_id"] == second["record_id"]


def test_contrary_evidence_decays_then_retires():
    mods = _load_modules()
    spots = mods[1]
    try:
        ctx, _owner = _setup(mods, ENABLED)
        service = spots.BlindSpotService(ctx)
        service.observe("overconfidence", confidence=0.74,
                        mitigation=["verify first"], observed_at=STAMP)
        first = service.record_contrary_evidence(
            "overconfidence", observed_at=LATER)
        second = service.record_contrary_evidence("overconfidence")
        third = service.record_contrary_evidence("overconfidence")
        with pytest.raises(spots.BlindSpotError):
            service.record_contrary_evidence("overconfidence")
        revived = service.observe(
            "overconfidence", confidence=0.3, observed_at=LATER)
    finally:
        mods[0].unload()
    assert first["status"] == "decayed" and first["confidence"] == 0.49
    assert first["evidence_count"] == 1  # contrary is not an observation
    assert first["last_observed_at"] == STAMP
    assert second["status"] == "decayed" and second["confidence"] == 0.24
    assert third["status"] == "retired" and third["contrary_count"] == 3
    # A retired spot is not permanent: a fresh observation starts over.
    assert revived["status"] == "active" and revived["evidence_count"] == 1
    assert revived["contrary_count"] == 0


def test_confidence_discount_is_pure_and_status_aware():
    mods = _load_modules()
    spots = mods[1]
    try:
        ctx, _owner = _setup(mods, ENABLED)
        service = spots.BlindSpotService(ctx)
        service.observe("overconfidence", confidence=0.8,
                        observed_at=STAMP)
        active = service.discount_for(0.9)
        service.record_contrary_evidence("overconfidence")
        decayed = service.discount_for(0.9)
        for _ in range(2):
            service.record_contrary_evidence("overconfidence")
        retired = service.discount_for(0.9)
    finally:
        mods[0].unload()
    # active: 0.9 * (1 - 0.5*0.8) = 0.54; decayed (conf 0.55):
    # 0.9 * (1 - 0.25*0.55) = 0.7763 (rounded); retired: no discount.
    assert active == {"base": 0.9, "adjusted": 0.54,
                      "discount": 0.36, "driver": "overconfidence"}
    assert decayed["adjusted"] == 0.7763 and decayed["driver"] == "overconfidence"
    assert retired == {"base": 0.9, "adjusted": 0.9,
                       "discount": 0.0, "driver": None}
    assert spots.adjusted_confidence(0.5, []) == 0.5
    with pytest.raises(spots.BlindSpotError):
        spots.adjusted_confidence(1.5, [])


def test_validation_refusals_and_tamper():
    mods = _load_modules()
    spots = mods[1]
    try:
        ctx, _owner = _setup(mods, ENABLED)
        service = spots.BlindSpotService(ctx)
        with pytest.raises(spots.BlindSpotError):
            service.observe("pride", confidence=0.5)
        with pytest.raises(spots.BlindSpotError):
            service.observe("overconfidence", confidence=1.5)
        with pytest.raises(spots.BlindSpotError):
            service.observe("overconfidence", confidence=0.5,
                            mitigation=["x"] * 6)
        with pytest.raises(spots.BlindSpotError):
            service.record_contrary_evidence("novelty_bias")
        service.observe("novelty_bias", confidence=0.5, observed_at=STAMP)
        # A stored status that disagrees with the §17 function is refused.
        log_path = service.path()
        payload = json.loads(
            log_path.read_text(encoding="utf-8").splitlines()[0])
        payload["status"] = "retired"
        log_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        with pytest.raises(spots.BlindSpotError):
            service.records()
    finally:
        mods[0].unload()


def test_packet_rotation_and_no_identity_write():
    mods = _load_modules()
    spots, self_model = mods[1], mods[3]
    try:
        ctx, _owner = _setup(
            mods, {**ENABLED, "blind_spots_log_limit": 10})
        claims = self_model.SelfModelStore(ctx)
        claims.ensure()
        claims_path = claims.path()
        before = hashlib.sha256(claims_path.read_bytes()).hexdigest()
        service = spots.BlindSpotService(ctx)
        service.observe("goal_tunnel_vision", confidence=0.66,
                        mitigation=["re-check the wider goal list"],
                        observed_at=STAMP)
        items = spots.BlindSpotBridge(ctx).packet_items("s1")
        for _index in range(10):
            service.observe("goal_tunnel_vision", confidence=0.66)
        rows = service.records()
        after = hashlib.sha256(claims_path.read_bytes()).hexdigest()
    finally:
        mods[0].unload()
    assert len(items) == 1 and items[0].source == "blind_spots"
    assert "goal_tunnel_vision" in items[0].content
    assert "not an identity label" in items[0].content
    assert "re-check the wider goal list" in items[0].content
    assert len(rows) == 10
    # Blind spots never write the self-model / identity stores.
    assert before == after


def test_profile_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    spots = mods[1]
    try:
        ctx, _owner = _setup(mods, ENABLED)
        spots.BlindSpotService(ctx).observe(
            "overconfidence", confidence=0.7, observed_at=STAMP)
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            ctx_b, _owner_b = _setup(mods, ENABLED)
            current_b = spots.BlindSpotService(ctx_b).current()
            items_b = spots.BlindSpotBridge(ctx_b).packet_items("s1")
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert current_b == [] and items_b == []
