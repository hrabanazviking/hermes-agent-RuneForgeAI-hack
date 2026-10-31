"""Contracts for the bounded-autonomy reconciliation (Slice 109).

Self-Aware Agency roadmap §11, reconciled against the already-banked
Emergent Agency Phase 5 autonomy policy engine (Slice 95) and Phase 8
limited local autonomy (Slice 98): the §11.3 risk-class taxonomy, the
§11.4 permission block with its own defaults (deny never upgraded,
allow bounded by the default class limit, ask lifted only by an
active grant), §11.5 short-lived operation-scoped capability grants
in one bounded log beside the Phase 5 stores, and a read-only
registry reconciliation that surfaces class differences instead of
fixing them. Tests load through real plugin discovery.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from datetime import datetime, timedelta, timezone

import pytest

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)

ENABLED = {"autonomy_detail_enabled": True}
ISSUED = "2026-10-31T12:00:00Z"
EXPIRES = "2026-10-31T14:00:00Z"
AT_13 = datetime(2026, 10, 31, 13, 0, tzinfo=timezone.utc)
AT_15 = datetime(2026, 10, 31, 15, 0, tzinfo=timezone.utc)


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
            importlib.import_module(f"{package}.autonomy_detail"),
            importlib.import_module(f"{package}.autonomy"),
        )
    except Exception:
        manager.unload()
        raise


def _setup(mods, config=None):
    _m, _d, autonomy = mods
    ctx = _Ctx(config)
    store = autonomy.AutonomyStore(ctx)
    owner = store.ensure()["owner_entity_id"]
    return ctx, store, owner


def _grant(mods, ctx, **overrides):
    service = mods[1].AutonomyDetailService(ctx)
    values = dict(scope="local project", expires_at=EXPIRES,
                  max_actions=1, issued_at=ISSUED)
    values.update(overrides)
    return service.build_grant("git_branch_create", **values)


def test_disabled_by_default():
    mods = _load_modules()
    detail = mods[1]
    try:
        ctx, _store, _owner = _setup(mods)
        service = detail.AutonomyDetailService(ctx)
        grant = _grant(mods, ctx)
        with pytest.raises(detail.AutonomyDetailError):
            service.record_grant(grant)
        assert detail.AutonomyDetailBridge(_Ctx()).packet_items("s1") == []
    finally:
        mods[0].unload()
    # Building a grant is pure and remains available.
    assert grant["operation"] == "git_branch_create"


def test_taxonomy_and_permission_defaults():
    mods = _load_modules()
    detail = mods[1]
    try:
        ctx, _store, _owner = _setup(mods, ENABLED)
        service = detail.AutonomyDetailService(ctx)
        names = [detail.class_disposition(i)["name"] for i in range(6)]
        with pytest.raises(detail.AutonomyDetailError):
            detail.class_disposition(6)
        denied = service.permission_decision("file_delete")
        allowed = service.permission_decision("self_model_update")
        asked = service.permission_decision("web_research", now=AT_13)
        with pytest.raises(detail.AutonomyDetailError):
            service.permission_decision("teleport")
        limited_ctx, _s, _o = _setup(
            mods, {**ENABLED, "autonomy_detail_default_class_limit": 1})
        above = detail.AutonomyDetailService(
            limited_ctx).permission_decision("self_model_update")
    finally:
        mods[0].unload()
    assert names == ["observe", "think", "local_reversible",
                     "external_reversible", "consequential",
                     "sensitive_destructive"]
    assert detail.class_disposition(5)["rule"] == \
        "always_requires_explicit_human_approval"
    assert list(detail.PERMISSIONS.values()).count("allow") == 5
    assert list(detail.PERMISSIONS.values()).count("ask") == 6
    assert list(detail.PERMISSIONS.values()).count("deny") == 3
    assert detail.PERMISSION_RISK_CLASS["github_push"] == 4
    assert detail.PERMISSION_RISK_CLASS["local_test_run"] == 2
    assert denied["decision"] == "deny"
    assert denied["reason"] == "permission_denied_by_default"
    assert allowed["decision"] == "allow"
    assert asked["decision"] == "require_confirmation"
    assert asked["reason"] == "no_active_capability_grant"
    assert above["decision"] == "require_confirmation"
    assert above["reason"] == "above_default_class_limit"


def test_grant_build_bounds():
    mods = _load_modules()
    detail = mods[1]
    try:
        ctx, _store, _owner = _setup(mods, ENABLED)
        service = detail.AutonomyDetailService(ctx)
        with pytest.raises(detail.AutonomyDetailError):
            service.build_grant("file_delete", scope="x",
                                expires_at=EXPIRES, issued_at=ISSUED)
        with pytest.raises(detail.AutonomyDetailError):
            service.build_grant("self_model_update", scope="x",
                                expires_at=EXPIRES, issued_at=ISSUED)
        with pytest.raises(detail.AutonomyDetailError):
            service.build_grant("git_branch_create", scope="x",
                                expires_at=ISSUED, issued_at=ISSUED)
        with pytest.raises(detail.AutonomyDetailError):
            service.build_grant(
                "git_branch_create", scope="x", issued_at=ISSUED,
                expires_at="2026-11-30T12:00:00Z")  # beyond the 168h bound
        with pytest.raises(detail.AutonomyDetailError):
            service.build_grant("git_branch_create", scope="x",
                                expires_at=EXPIRES, max_actions=0,
                                issued_at=ISSUED)
        grant = _grant(mods, ctx)
    finally:
        mods[0].unload()
    assert detail.grant_status(grant, 0, now=AT_13) == "active"
    assert detail.grant_status(grant, 0, now=AT_15) == "expired"
    assert detail.grant_status(grant, 1, now=AT_13) == "exhausted"


def test_grant_lifts_ask_until_used_or_expired():
    mods = _load_modules()
    detail = mods[1]
    try:
        ctx, _store, _owner = _setup(mods, ENABLED)
        service = detail.AutonomyDetailService(ctx)
        grant = _grant(mods, ctx)
        service.record_grant(grant)
        lifted = service.permission_decision("git_branch_create", now=AT_13)
        service.record_use(grant["grant_id"],
                           recorded_at="2026-10-31T13:00:00Z")
        exhausted = service.permission_decision("git_branch_create", now=AT_13)
        with pytest.raises(detail.AutonomyDetailError):
            service.record_use(grant["grant_id"],
                               recorded_at="2026-10-31T13:30:00Z")
        expired = service.permission_decision("git_branch_create", now=AT_15)
    finally:
        mods[0].unload()
    assert lifted["decision"] == "allow"
    assert lifted["reason"] == "active_capability_grant"
    assert lifted["grant_id"] == grant["grant_id"]
    assert exhausted["decision"] == "require_confirmation"
    assert expired["decision"] == "require_confirmation"


def test_reconcile_registry_surfaces_differences():
    mods = _load_modules()
    detail = mods[1]
    try:
        _ctx, store, _owner = _setup(mods, ENABLED)
        report = detail.AutonomyDetailService.reconcile_registry(store.policy())
    finally:
        mods[0].unload()
    rows = {row["action"]: row for row in report["rows"]}
    assert rows["world_get"]["agreement"] == "agrees"
    assert rows["goal_update"]["agreement"] == "agrees"
    assert rows["github_push"]["registry_class"] == 3
    assert rows["github_push"]["expected_class"] == 4
    assert rows["github_push"]["agreement"] == "differs"
    assert rows["generate_private_report"]["agreement"] == "unmapped"
    assert sorted(report["differs"]) == [
        "github_push", "organize_curiosity_queue",
        "run_local_tests", "update_self_model_evidence",
    ]
    assert report["agrees"] == 6


def test_record_writes_only_its_own_log_and_rotates():
    home = get_hermes_home()
    mods = _load_modules()
    detail = mods[1]
    try:
        ctx, _store, _owner = _setup(
            mods, {**ENABLED, "autonomy_detail_log_limit": 10})
        watched = [
            home / "entity" / "autonomy_policy.yaml",
            home / "entity" / "autonomy_state.json",
        ]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in watched]
        service = detail.AutonomyDetailService(ctx)
        first = _grant(mods, ctx)
        service.record_grant(first)
        for _index in range(10):
            service.record_grant(_grant(mods, ctx))
        after = [hashlib.sha256(p.read_bytes()).hexdigest() for p in watched]
        rows = service.records()
    finally:
        mods[0].unload()
    # Recording grants never touches the Phase 5 policy or state.
    assert before == after
    assert len(rows) == 10
    assert rows[0]["grant_id"] != first["grant_id"]


def test_tampered_grant_symlink_refused_and_packet_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    detail = mods[1]
    try:
        ctx, _store, _owner = _setup(mods, ENABLED)
        service = detail.AutonomyDetailService(ctx)
        now = datetime.now(timezone.utc)
        live = service.build_grant(
            "git_branch_create", scope="local project",
            expires_at=(now + timedelta(hours=2)).isoformat()
            .replace("+00:00", "Z"),
            issued_at=now.isoformat().replace("+00:00", "Z"))
        service.record_grant(live)
        items = detail.AutonomyDetailBridge(ctx).packet_items("s1")
        path = service.path()
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["operation"] = "file_delete"  # a grant can never cover deny
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        with pytest.raises(detail.AutonomyDetailError):
            service.records()
        path.unlink()
        service.record_grant(_grant(mods, ctx))
        target = tmp_path / "elsewhere.jsonl"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
        with pytest.raises(detail.AutonomyDetailError):
            service.records()
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            ctx_b, _store_b, _owner_b = _setup(mods, ENABLED)
            rows_b = detail.AutonomyDetailService(ctx_b).records()
            items_b = detail.AutonomyDetailBridge(ctx_b).packet_items("s1")
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert len(items) == 1
    assert items[0].source == "autonomy_detail"
    assert "git_branch_create" in items[0].content
    assert rows_b == []
    assert items_b == []
