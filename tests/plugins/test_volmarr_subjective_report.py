"""Contracts for subjective self-report (Slice 105).

Self-Aware Agency roadmap §7: a persona may report an internal
phenomenology, kept as a subjective self-report — epistemically
labelled, source ``self_report`` — and never rewritten into, or
recorded as, a verified runtime fact / objective telemetry. Tests
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

ENABLED = {"subjective_report_enabled": True}
TS = "2026-10-31T12:00:00Z"
TS2 = "2026-10-31T13:00:00Z"
STATEMENT = "I experience this task as exciting and demanding."


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
            importlib.import_module(f"{package}.subjective_report"),
            importlib.import_module(f"{package}.self_model"),
        )
    except Exception:
        manager.unload()
        raise


def _setup(mods, config=None):
    _m, reports, self_model = mods
    ctx = _Ctx(config)
    owner = self_model.SelfModelStore(ctx).ensure()["owner_entity_id"]
    return reports.SubjectiveReportStore(ctx), owner, ctx


def test_disabled_by_default():
    mods = _load_modules()
    reports = mods[1]
    try:
        store, _owner, _ctx = _setup(mods)
        with pytest.raises(reports.SubjectiveReportError):
            store.record(STATEMENT, confidence=0.82, recorded_at=TS)
        assert reports.SubjectiveReportBridge(_Ctx()).packet_items("s1") == []
    finally:
        mods[0].unload()


def test_record_matches_section7_shape():
    mods = _load_modules()
    try:
        store, owner, _ctx = _setup(mods, ENABLED)
        record = store.record(STATEMENT, confidence=0.82, recorded_at=TS)
        reread = store.records()
    finally:
        mods[0].unload()
    assert record["report_version"] == 1
    assert record["owner_entity_id"] == owner
    assert record["recorded_at"] == TS
    assert record["category"] == "self_experience"
    assert record["statement"] == STATEMENT
    assert record["confidence"] == 0.82
    assert record["source"] == "self_report"
    assert record["epistemic_category"] == "self_interpretation"
    assert reread == [record]


def test_verified_runtime_fact_is_refused():
    mods = _load_modules()
    reports = mods[1]
    try:
        store, _owner, _ctx = _setup(mods, ENABLED)
        with pytest.raises(reports.SubjectiveReportError):
            store.record(
                STATEMENT, confidence=0.9,
                epistemic_category="verified_runtime_fact", recorded_at=TS,
            )
        assert store.records() == []
    finally:
        mods[0].unload()


def test_all_subjective_categories_accepted_and_distinguished():
    mods = _load_modules()
    reports = mods[1]
    try:
        store, _owner, _ctx = _setup(mods, ENABLED)
        for category in reports.SUBJECTIVE_EPISTEMIC_CATEGORIES:
            store.record(STATEMENT, confidence=0.5,
                         epistemic_category=category, recorded_at=TS)
        rows = store.records()
    finally:
        mods[0].unload()
    assert [row["epistemic_category"] for row in rows] == list(
        reports.SUBJECTIVE_EPISTEMIC_CATEGORIES)
    assert "verified_runtime_fact" in reports.EPISTEMIC_CATEGORIES
    assert reports.is_subjective_category("narrative_meaning") is True
    assert reports.is_subjective_category("verified_runtime_fact") is False


def test_invalid_inputs_refused():
    mods = _load_modules()
    reports = mods[1]
    try:
        store, _owner, _ctx = _setup(mods, ENABLED)
        for kwargs in (
            {"confidence": 1.5},
            {"confidence": True},
            {"confidence": 0.5, "epistemic_category": "telemetry"},
            {"confidence": 0.5, "category": "Not A Slug!"},
        ):
            with pytest.raises(reports.SubjectiveReportError):
                store.record(STATEMENT, recorded_at=TS, **kwargs)
        with pytest.raises(reports.SubjectiveReportError):
            store.record(STATEMENT, confidence=0.5, recorded_at="not-a-time")
        with pytest.raises(reports.SubjectiveReportError):
            store.record("  ", confidence=0.5, recorded_at=TS)
        with pytest.raises(reports.SubjectiveReportError):
            store.record("x" * 501, confidence=0.5, recorded_at=TS)
        assert store.records() == []
    finally:
        mods[0].unload()


def test_recording_writes_only_its_own_log():
    home = get_hermes_home()
    mods = _load_modules()
    try:
        store, _owner, ctx = _setup(mods, ENABLED)
        claims_path = home / "entity" / "self_model.yaml"
        before = hashlib.sha256(claims_path.read_bytes()).hexdigest()
        store.record(STATEMENT, confidence=0.82, recorded_at=TS)
        after = hashlib.sha256(claims_path.read_bytes()).hexdigest()
        assert (home / "entity" / "subjective_reports.jsonl").is_file()
    finally:
        mods[0].unload()
    assert before == after  # never promoted into the claims/objective layer


def test_log_rotation_is_bounded():
    mods = _load_modules()
    try:
        store, _owner, _ctx = _setup(
            mods, {**ENABLED, "subjective_report_log_limit": 10})
        for index in range(12):
            store.record(f"Report {index}.", confidence=0.5, recorded_at=TS)
        rows = store.records()
    finally:
        mods[0].unload()
    assert len(rows) == 10
    assert rows[0]["statement"] == "Report 2."
    assert rows[-1]["statement"] == "Report 11."


def test_tampered_objective_record_is_refused_on_read():
    mods = _load_modules()
    reports = mods[1]
    try:
        store, _owner, _ctx = _setup(mods, ENABLED)
        store.record(STATEMENT, confidence=0.82, recorded_at=TS)
        path = store.path()
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["epistemic_category"] = "verified_runtime_fact"
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        with pytest.raises(reports.SubjectiveReportError):
            store.records()
    finally:
        mods[0].unload()


def test_symlinked_log_is_refused(tmp_path):
    mods = _load_modules()
    reports = mods[1]
    try:
        store, _owner, _ctx = _setup(mods, ENABLED)
        store.record(STATEMENT, confidence=0.82, recorded_at=TS)
        path = store.path()
        target = tmp_path / "elsewhere.jsonl"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
        with pytest.raises(reports.SubjectiveReportError):
            store.records()
        with pytest.raises(reports.SubjectiveReportError):
            store.record(STATEMENT, confidence=0.5, recorded_at=TS2)
    finally:
        mods[0].unload()


def test_packet_labels_latest_report_as_not_telemetry_and_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    reports = mods[1]
    try:
        store, _owner, ctx = _setup(mods, ENABLED)
        assert reports.SubjectiveReportBridge(ctx).packet_items("s1") == []
        store.record(STATEMENT, confidence=0.82, recorded_at=TS)
        store.record("A later report.", confidence=0.4,
                     epistemic_category="narrative_meaning", recorded_at=TS2)
        items = reports.SubjectiveReportBridge(ctx).packet_items("s1")
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            _store_b, _o, ctx_b = _setup(mods, ENABLED)
            items_b = reports.SubjectiveReportBridge(ctx_b).packet_items("s1")
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert len(items) == 1
    assert items[0].source == "subjective_report"
    assert "not telemetry" in items[0].content
    assert "narrative_meaning" in items[0].content
    assert "A later report." in items[0].content
    assert items_b == []
