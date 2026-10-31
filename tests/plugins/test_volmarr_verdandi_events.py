"""Contracts for the Verðandi event families (Slice 112).

Self-Aware Agency roadmap §14: the seventeen content-free event
families over the plugin's existing fail-open Verðandi publisher.
The content-free rule is enforced by a strict context allowlist —
no field can carry free text — emission is explicit only, dropped
events are recorded honestly as not delivered, and every attempt
lands in one bounded log. Tests load through real plugin discovery.
"""

from __future__ import annotations

import importlib
import json

import pytest

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)

ENABLED = {"verdandi_events_enabled": True}
STAMP = "2026-10-31T12:00:00Z"
EXPECTED_TYPES = [
    "hermes.self_model.updated",
    "hermes.awareness.snapshot",
    "hermes.awareness.discrepancy_detected",
    "hermes.reflection.started",
    "hermes.reflection.completed",
    "hermes.motivation.drive_changed",
    "hermes.goal.intrinsic_proposed",
    "hermes.goal.intrinsic_approved",
    "hermes.curiosity.question_created",
    "hermes.curiosity.investigation_started",
    "hermes.curiosity.investigation_completed",
    "hermes.autonomy.action_proposed",
    "hermes.autonomy.action_allowed",
    "hermes.autonomy.action_blocked",
    "hermes.autonomy.approval_required",
    "hermes.agency.cycle_started",
    "hermes.agency.cycle_completed",
]


class _Ctx:
    def __init__(self, config=None):
        self._config = dict(config or {})

    def get_config(self, key, default=None):
        return self._config.get(key, default)


class _Publisher:
    def __init__(self, result=True):
        self._result = result
        self.calls = []

    def publish(self, ctx, event_type, context, *, schema, schema_version):
        self.calls.append({
            "event_type": event_type, "context": dict(context),
            "schema": schema, "schema_version": schema_version,
        })
        return self._result


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
            importlib.import_module(f"{package}.verdandi_events"),
            importlib.import_module(f"{package}.identity"),
        )
    except Exception:
        manager.unload()
        raise


def _setup(mods, config=None):
    _m, _e, identity = mods
    ctx = _Ctx(config)
    owner = identity.IdentityStore(ctx).ensure().entity_id
    return ctx, owner


def test_disabled_by_default():
    mods = _load_modules()
    events = mods[1]
    try:
        ctx, _owner = _setup(mods)
        service = events.VerdandiEventsService(ctx, _Publisher())
        with pytest.raises(events.VerdandiEventsError):
            service.emit("hermes.agency.cycle_started", recorded_at=STAMP)
        assert events.VerdandiEventsBridge(_Ctx()).packet_items("s1") == []
        built = service.build_event(
            "hermes.agency.cycle_started", recorded_at=STAMP)
    finally:
        mods[0].unload()
    # Building an event is pure and remains available.
    assert built["delivered"] is False
    assert built["context"] == {}


def test_event_types_are_the_seventeen_roadmap_families():
    mods = _load_modules()
    events = mods[1]
    try:
        families = events.event_families()
    finally:
        mods[0].unload()
    assert list(events.EVENT_TYPES) == EXPECTED_TYPES
    assert [row["event_type"] for row in families] == EXPECTED_TYPES


def test_content_free_allowlist():
    mods = _load_modules()
    events = mods[1]
    try:
        ctx, _owner = _setup(mods, ENABLED)
        service = events.VerdandiEventsService(ctx, _Publisher())
        ok = service.build_event(
            "hermes.autonomy.action_blocked",
            {"subject_id": "inspect_project_state",
             "subject_class": "local_action", "score": 0.25,
             "reason_code": "policy_mode_observe", "outcome": "blocked",
             "count": 2},
            recorded_at=STAMP)
        with pytest.raises(events.VerdandiEventsError):
            service.build_event("hermes.session.started", recorded_at=STAMP)
        # No field may carry free text: unknown keys are refused.
        with pytest.raises(events.VerdandiEventsError):
            service.build_event(
                "hermes.reflection.completed",
                {"reflection": "I feel curious about the fjord"},
                recorded_at=STAMP)
        with pytest.raises(events.VerdandiEventsError):
            service.build_event(
                "hermes.reflection.completed",
                {"prompt": "secret prompt text"}, recorded_at=STAMP)
        # Slugs only: spaces / capitals / prose are refused.
        with pytest.raises(events.VerdandiEventsError):
            service.build_event(
                "hermes.reflection.completed",
                {"reason_code": "Because Reasons"}, recorded_at=STAMP)
        with pytest.raises(events.VerdandiEventsError):
            service.build_event(
                "hermes.curiosity.question_created",
                {"score": 1.5}, recorded_at=STAMP)
        with pytest.raises(events.VerdandiEventsError):
            service.build_event(
                "hermes.curiosity.question_created",
                {"count": -1}, recorded_at=STAMP)
        with pytest.raises(events.VerdandiEventsError):
            service.build_event(
                "hermes.curiosity.question_created",
                {"subject_id": "not an identifier"}, recorded_at=STAMP)
    finally:
        mods[0].unload()
    assert ok["context"]["reason_code"] == "policy_mode_observe"
    assert ok["context"]["score"] == pytest.approx(0.25)


def test_emit_delivered_records_and_packets():
    mods = _load_modules()
    events = mods[1]
    try:
        ctx, _owner = _setup(mods, ENABLED)
        publisher = _Publisher(result=True)
        service = events.VerdandiEventsService(ctx, publisher)
        record = service.emit(
            "hermes.agency.cycle_completed",
            {"subject_class": "agency_cycle", "outcome": "completed",
             "count": 1},
            recorded_at=STAMP)
        rows = service.events()
        items = events.VerdandiEventsBridge(ctx).packet_items("s1")
    finally:
        mods[0].unload()
    assert record["delivered"] is True
    assert rows[0]["record_id"] == record["record_id"]
    assert publisher.calls[0]["event_type"] == "hermes.agency.cycle_completed"
    assert publisher.calls[0]["schema"] == events.EVENT_SCHEMA
    assert publisher.calls[0]["context"] == {
        "subject_class": "agency_cycle", "outcome": "completed", "count": 1}
    assert len(items) == 1
    assert items[0].source == "verdandi_events"
    assert "hermes.agency.cycle_completed delivered" in items[0].content


def test_emit_dropped_is_fail_open_and_honest():
    mods = _load_modules()
    events = mods[1]
    try:
        ctx, _owner = _setup(mods, ENABLED)
        service = events.VerdandiEventsService(ctx, _Publisher(result=False))
        record = service.emit(
            "hermes.awareness.snapshot", recorded_at=STAMP)
        items = events.VerdandiEventsBridge(ctx).packet_items("s1")
    finally:
        mods[0].unload()
    # No listener: the publisher drops the event, emit does not raise,
    # and the log says so plainly.
    assert record["delivered"] is False
    assert "dropped (no listener)" in items[0].content


def test_emit_rotates():
    mods = _load_modules()
    events = mods[1]
    try:
        ctx, _owner = _setup(
            mods, {**ENABLED, "verdandi_events_log_limit": 10})
        service = events.VerdandiEventsService(ctx, _Publisher())
        first = service.emit("hermes.reflection.started", recorded_at=STAMP)
        for _index in range(10):
            service.emit("hermes.reflection.completed", recorded_at=STAMP)
        rows = service.events()
    finally:
        mods[0].unload()
    assert len(rows) == 10
    assert rows[0]["record_id"] != first["record_id"]


def test_tampered_log_symlink_refused_and_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    events = mods[1]
    try:
        ctx, _owner = _setup(mods, ENABLED)
        service = events.VerdandiEventsService(ctx, _Publisher())
        service.emit("hermes.self_model.updated", recorded_at=STAMP)
        path = service.path()
        payload = json.loads(path.read_text(encoding="utf-8"))
        # A tampered record smuggling free text into the context is
        # refused on read — the allowlist holds on the way back in.
        payload["context"] = {"reflection": "raw private reflection"}
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        with pytest.raises(events.VerdandiEventsError):
            service.events()
        path.unlink()
        service.emit("hermes.self_model.updated", recorded_at=STAMP)
        target = tmp_path / "elsewhere.jsonl"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
        with pytest.raises(events.VerdandiEventsError):
            service.events()
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            ctx_b, _owner_b = _setup(mods, ENABLED)
            rows_b = events.VerdandiEventsService(
                ctx_b, _Publisher()).events()
            items_b = events.VerdandiEventsBridge(ctx_b).packet_items("s1")
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert rows_b == []
    assert items_b == []
