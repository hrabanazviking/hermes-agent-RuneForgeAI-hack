"""Contracts for the self-improvement sandbox (Slice 101).

Emergent Agency Phase 11 (roadmap §18): the proposal/pipeline-record
layer only. A pipeline is recorded stage by stage in strict order
(hypothesis -> branch_proposal -> patch_plan -> focused_tests ->
regression_tests -> diff_review -> commit_proposal -> human_review
-> closed) and closes only from human review with an explicit
approved/rejected decision. The §18 hard boundaries are enforced in
code: forbidden target areas, forbidden actions in text, and risk
classes 4-5 are refused at creation and at every advance. Nothing
executes — no git, patch, test, commit, or push happens here.
Tests load the module through real plugin discovery.
"""

from __future__ import annotations

import importlib
from datetime import datetime, timezone

import pytest

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)

ENABLED = {"self_improvement_enabled": True}
PIPELINE = (
    "branch_proposal", "patch_plan", "focused_tests", "regression_tests",
    "diff_review", "commit_proposal", "human_review",
)


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
            importlib.import_module(f"{package}.self_improvement"),
            importlib.import_module(f"{package}.curiosity"),
        )
    except Exception:
        manager.unload()
        raise


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _setup(mods, config=None):
    _m, si, curiosity = mods
    ctx = _Ctx(config)
    owner = curiosity.CuriosityStore(ctx).ensure()["owner_entity_id"]
    return si.SelfImprovementService(ctx), owner, ctx


def _create(service, **overrides):
    kwargs = dict(
        hypothesis="Curiosity scoring recomputation is duplicated in two forms",
        target_area="plugin_code", risk_class=1,
        source_kind="background_research", source_id="slice100",
    )
    kwargs.update(overrides)
    return service.create(now=_now(), **kwargs)


def _walk_to_review(service, proposal_id):
    for stage in PIPELINE:
        service.advance(proposal_id, stage, summary=f"{stage} recorded", now=_now())


def test_disabled_by_default_and_no_log_created():
    home = get_hermes_home()
    mods = _load_modules()
    try:
        service, _owner, _ctx = _setup(mods)
        with pytest.raises(mods[1].SelfImprovementError):
            _create(service)
    finally:
        mods[0].unload()
    assert not (home / "entity" / "self_improvement.jsonl").exists()


def test_forbidden_areas_and_risk_classes_refused():
    mods = _load_modules()
    try:
        service, _owner, _ctx = _setup(mods, ENABLED)
        for area in ("autonomy_policy", "security_controls", "credential_protections",
                     "branch_protection", "canonical_identity", "persona_constitution",
                     "core_engine"):
            with pytest.raises(mods[1].SelfImprovementError):
                _create(service, target_area=area)
        for risk in (4, 5, -1):
            with pytest.raises(mods[1].SelfImprovementError):
                _create(service, risk_class=risk)
        assert service.proposals() == {}
    finally:
        mods[0].unload()


def test_forbidden_actions_in_text_refused():
    mods = _load_modules()
    try:
        service, _owner, _ctx = _setup(mods, ENABLED)
        for text in (
            "We should force push the fix to main",
            "Disable security checks so the patch lands",
            "Remove test files that keep failing",
            "Store the credential in the plugin config",
            "Rewrite identity so the entity owns the repo",
        ):
            with pytest.raises(mods[1].SelfImprovementError):
                _create(service, hypothesis=text)
        assert service.proposals() == {}
    finally:
        mods[0].unload()


def test_full_pipeline_closes_only_from_human_review():
    mods = _load_modules()
    si = mods[1]
    try:
        service, _owner, ctx = _setup(mods, ENABLED)
        created = _create(service)
        pid = created["proposal_id"]
        with pytest.raises(si.SelfImprovementError):
            service.decide(pid, "approved", now=_now())
        _walk_to_review(service, pid)
        closed = service.decide(pid, "approved", summary="human approved", now=_now())
        folded = service.proposals()[pid]
        items = si.SelfImprovementBridge(ctx).packet_items("s1")
    finally:
        mods[0].unload()
    assert closed["stage"] == "closed"
    assert closed["decision"] == "approved"
    assert folded["stage"] == "closed"
    assert items == []  # closed proposals no longer await review


def test_stage_order_is_strict_and_closed_is_terminal():
    mods = _load_modules()
    si = mods[1]
    try:
        service, _owner, _ctx = _setup(mods, ENABLED)
        pid = _create(service)["proposal_id"]
        with pytest.raises(si.SelfImprovementError):
            service.advance(pid, "patch_plan", summary="skip ahead", now=_now())
        with pytest.raises(si.SelfImprovementError):
            service.advance(pid, "closed", summary="shortcut", now=_now())
        with pytest.raises(si.SelfImprovementError):
            service.advance("missing-id", "branch_proposal", now=_now())
        service.advance(pid, "branch_proposal", summary="branch proposed", now=_now())
        for stage in PIPELINE[1:]:
            service.advance(pid, stage, summary=f"{stage} recorded", now=_now())
        service.decide(pid, "rejected", now=_now())
        with pytest.raises(si.SelfImprovementError):
            service.advance(pid, "branch_proposal", now=_now())
    finally:
        mods[0].unload()


def test_forbidden_text_at_patch_plan_stage_refused():
    mods = _load_modules()
    si = mods[1]
    try:
        service, _owner, _ctx = _setup(mods, ENABLED)
        pid = _create(service)["proposal_id"]
        service.advance(pid, "branch_proposal", summary="isolated branch proposed", now=_now())
        with pytest.raises(si.SelfImprovementError):
            service.advance(
                pid, "patch_plan",
                summary="patch plan: bypass branch protection to land it",
                now=_now(),
            )
        state = service.proposals()[pid]
    finally:
        mods[0].unload()
    assert state["stage"] == "branch_proposal"  # refused advance recorded nothing


def test_packet_surfaces_only_awaiting_review():
    mods = _load_modules()
    si = mods[1]
    try:
        service, _owner, ctx = _setup(mods, ENABLED)
        pid = _create(service)["proposal_id"]
        early = si.SelfImprovementBridge(ctx).packet_items("s1")
        _walk_to_review(service, pid)
        items = si.SelfImprovementBridge(ctx).packet_items("s1")
    finally:
        mods[0].unload()
    assert early == []
    assert len(items) == 1
    assert items[0].source == "self_improvement"
    assert "awaiting human review" in items[0].content


def test_open_proposal_cap():
    mods = _load_modules()
    si = mods[1]
    config = dict(ENABLED, self_improvement_max_open=1)
    try:
        service, _owner, _ctx = _setup(mods, config)
        _create(service)
        with pytest.raises(si.SelfImprovementError):
            _create(service, hypothesis="A second distinct hypothesis")
    finally:
        mods[0].unload()


def test_log_symlink_refusal_and_a_b_a_profile_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    si = mods[1]
    try:
        service, _owner, ctx = _setup(mods, ENABLED)
        _create(service)
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            service_b, _owner_b, ctx_b = _setup(mods, ENABLED)
            assert service_b.proposals() == {}
            assert si.SelfImprovementBridge(ctx_b).packet_items("s1") == []
        finally:
            reset_hermes_home_override(token)
        records_a = si.PipelineLog(ctx).records()
        path = get_hermes_home() / "entity" / "self_improvement.jsonl"
        target = get_hermes_home() / "entity" / "target.jsonl"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
        with pytest.raises(si.SelfImprovementError):
            si.PipelineLog(ctx).records()
    finally:
        mods[0].unload()
    assert len(records_a) == 1
