"""Contracts for the reusable confidence contract (Slice 116).

Self-Aware Agency roadmap §18: every important self-belief may
carry confidence, a basis list from the seven named values, and
last_verified_at, and is described by one of the seven epistemic
labels. The label derives deterministically from the record —
it is never asserted independently — and subjective/symbolic
beliefs cannot be promoted by confidence alone. Tests load
through real plugin discovery.
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

ENABLED = {"epistemics_enabled": True}
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
            importlib.import_module(f"{package}.epistemics"),
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
    epi = mods[1]
    try:
        ctx, _owner = _setup(mods)
        service = epi.EpistemicsService(ctx)
        with pytest.raises(epi.EpistemicError):
            service.assess("goal_count", claim="four active goals",
                           confidence=0.9, basis=["runtime_fact"])
        assert epi.EpistemicsBridge(_Ctx()).packet_items("s1") == []
    finally:
        mods[0].unload()


def test_basis_and_label_vocabularies():
    mods = _load_modules()
    epi = mods[1]
    try:
        _setup(mods, ENABLED)
    finally:
        mods[0].unload()
    assert epi.basis_values() == [
        "runtime_fact", "memory", "user_feedback", "self_report",
        "inference", "persona_canon", "external_source",
    ]
    assert epi.labels() == [
        "verified", "strongly_supported", "supported", "uncertain",
        "speculative", "subjective", "symbolic",
    ]


def test_label_derivation_matches_section_18_examples():
    mods = _load_modules()
    epi = mods[1]
    try:
        _setup(mods, ENABLED)
    finally:
        mods[0].unload()
    label = epi.label_for
    # Verified: a runtime fact, high confidence, actually verified.
    assert label(0.95, ["runtime_fact"], last_verified_at=STAMP) == "verified"
    # The same belief without a verification stamp is only supported.
    assert label(0.95, ["runtime_fact"]) == "supported"
    # Two independent evidence bases at high confidence.
    assert label(0.8, ["memory", "user_feedback"]) == "strongly_supported"
    # Supported: one evidence base at moderate confidence.
    assert label(0.6, ["memory", "inference"]) == "supported"
    # Subjective and symbolic are basis-determined at any confidence.
    assert label(0.99, ["self_report"]) == "subjective"
    assert label(0.99, ["persona_canon"]) == "symbolic"
    assert label(0.7, ["self_report", "persona_canon"]) == "subjective"
    # Pure inference is uncertain, then speculative as it weakens.
    assert label(0.5, ["inference"]) == "uncertain"
    assert label(0.2, ["inference"]) == "speculative"
    with pytest.raises(epi.EpistemicError):
        label(0.5, ["vibes"])
    with pytest.raises(epi.EpistemicError):
        label(1.5, ["memory"])


def test_assess_round_trip_and_contract_fields():
    mods = _load_modules()
    epi = mods[1]
    try:
        ctx, _owner = _setup(mods, ENABLED)
        service = epi.EpistemicsService(ctx)
        record = service.assess(
            "goal_count", claim="I have four active durable goals.",
            confidence=0.97, basis=["runtime_fact"],
            last_verified_at=STAMP, recorded_at=STAMP)
        latest = service.latest_for("goal_count")
        fields = epi.make_assessment_fields(
            confidence=0.4, basis=["inference", "memory", "memory"])
    finally:
        mods[0].unload()
    # The §18 record shape, verbatim fields.
    assert record["confidence"] == 0.97
    assert record["basis"] == ["runtime_fact"]
    assert record["last_verified_at"] == STAMP
    assert record["label"] == "verified"
    assert latest == record
    # The reusable contract normalises basis into roadmap order.
    assert fields == {"confidence": 0.4, "basis": ["memory", "inference"],
                      "last_verified_at": None, "label": "uncertain"}


def test_summary_groups_latest_claims_by_label():
    mods = _load_modules()
    epi = mods[1]
    try:
        ctx, _owner = _setup(mods, ENABLED)
        service = epi.EpistemicsService(ctx)
        service.assess("goals", claim="four active goals", confidence=0.97,
                       basis=["runtime_fact"], last_verified_at=STAMP,
                       recorded_at=STAMP)
        service.assess("mood", claim="this project feels exciting",
                       confidence=0.8, basis=["self_report"],
                       recorded_at=STAMP)
        service.assess("taste", claim="a stable preference may be forming",
                       confidence=0.2, basis=["inference"], recorded_at=STAMP)
        # A newer assessment of the same subject replaces it in the summary.
        service.assess("goals", claim="five active goals", confidence=0.6,
                       basis=["memory"], recorded_at=STAMP)
        summary = service.summary_by_label()
    finally:
        mods[0].unload()
    assert summary["supported"] == ["five active goals"]
    assert summary["verified"] == []
    assert summary["subjective"] == ["this project feels exciting"]
    assert summary["speculative"] == ["a stable preference may be forming"]
    assert list(summary) == epi.labels()


def test_validation_refusals_and_tampered_label():
    mods = _load_modules()
    epi = mods[1]
    try:
        ctx, _owner = _setup(mods, ENABLED)
        service = epi.EpistemicsService(ctx)
        with pytest.raises(epi.EpistemicError):
            service.assess("Bad Subject", claim="x", confidence=0.5,
                           basis=["memory"])
        with pytest.raises(epi.EpistemicError):
            service.assess("ok", claim="x", confidence=0.5, basis=[])
        with pytest.raises(epi.EpistemicError):
            service.assess("ok", claim="x", confidence=0.5,
                           basis=["memory"], last_verified_at="not-a-date")
        service.assess("ok", claim="a modest belief", confidence=0.5,
                       basis=["memory"], recorded_at=STAMP)
        # A stored label stronger than the function allows is refused.
        log_path = service.path()
        payload = json.loads(
            log_path.read_text(encoding="utf-8").splitlines()[0])
        payload["label"] = "verified"
        log_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        with pytest.raises(epi.EpistemicError):
            service.assessments()
    finally:
        mods[0].unload()


def test_packet_rotation_and_no_other_store_write():
    mods = _load_modules()
    epi, self_model = mods[1], mods[3]
    try:
        ctx, _owner = _setup(mods, {**ENABLED, "epistemics_log_limit": 10})
        claims = self_model.SelfModelStore(ctx)
        claims.ensure()
        claims_path = claims.path()
        before = hashlib.sha256(claims_path.read_bytes()).hexdigest()
        service = epi.EpistemicsService(ctx)
        service.assess("heartbeat", claim="continuity heartbeat is fresh",
                       confidence=0.96, basis=["runtime_fact"],
                       last_verified_at=STAMP, recorded_at=STAMP)
        items = epi.EpistemicsBridge(ctx).packet_items("s1")
        for index in range(10):
            service.assess(f"belief_{index}", claim=f"belief {index}",
                           confidence=0.4, basis=["inference"])
        rows = service.assessments()
        after = hashlib.sha256(claims_path.read_bytes()).hexdigest()
    finally:
        mods[0].unload()
    assert len(items) == 1 and items[0].source == "epistemics"
    assert "verified 1" in items[0].content
    assert "heartbeat" in items[0].content
    assert len(rows) == 10
    # The epistemics layer never writes the self-model store.
    assert before == after


def test_profile_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    epi = mods[1]
    try:
        ctx, _owner = _setup(mods, ENABLED)
        epi.EpistemicsService(ctx).assess(
            "goals", claim="four active goals", confidence=0.9,
            basis=["runtime_fact"], last_verified_at=STAMP,
            recorded_at=STAMP)
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            ctx_b, _owner_b = _setup(mods, ENABLED)
            rows_b = epi.EpistemicsService(ctx_b).assessments()
            items_b = epi.EpistemicsBridge(ctx_b).packet_items("s1")
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert rows_b == [] and items_b == []
