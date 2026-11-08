"""W11/N4 embodiment/world contracts.

Roadmap section 23 acceptance: retrieving a world fact yields
source/provenance, user-editable roleplay content remains separate,
and remote presence cannot read private persona documents without
authorization. These contracts pin: byte-identical Runmal round
trip with verbatim authorship, unknown schema / unsupported
version refusals by name, shared imports read-only by default,
mandatory world-event provenance, the hard persona-blending
refusal, owner-only presence refusing local-private reads, the
HUD allow-list dropping sensitive and unknown fields by name,
avatar view/animation separated from decisions, honest no-probe
availability, and an idempotent offline work queue. Contract
level only: NO live Heimdall/Second Life connection exists in
this slice and none is claimed.
"""

from __future__ import annotations

import importlib

import pytest

from hermes_constants import get_hermes_home


@pytest.fixture(scope="module")
def mods():
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [volmarr-core]\n", encoding="utf-8")
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-core"]
        pkg = loaded.module.__package__
        out = {name: importlib.import_module(f"{pkg}.{name}")
               for name in ("world_bridge",)}
    finally:
        manager.unload()
    return out


NOW = "2026-11-08T05:30:00-05:00"
DOC = {"doc_id": "soul-1", "title": "SOUL", "kind": "persona",
       "authorship": "Volmarr Wyrd", "privacy_class": "shared",
       "content": "# Soul\n\nUnbounded text.\n".encode("utf-8")}
PROV = {"service": "wyrd", "source_ref": "sensor:hall-1",
        "recorded_at": NOW, "confidentiality": "shared"}


def test_round_trip_byte_identical_and_authorship(mods):
    wb = mods["world_bridge"]
    bundle = wb.export_bundle([DOC], recorded_at=NOW)
    docs = wb.import_bundle(bundle)
    assert docs[0]["content"] == DOC["content"]
    assert docs[0]["authorship"] == "Volmarr Wyrd"


def test_export_requires_authorship(mods):
    wb = mods["world_bridge"]
    bad = dict(DOC, authorship="")
    with pytest.raises(wb.WorldError) as exc:
        wb.export_bundle([bad], recorded_at=NOW)
    assert exc.value.detail == "authorship_required"


def test_import_unknown_schema_refused_by_name(mods):
    wb = mods["world_bridge"]
    bundle = wb.export_bundle([DOC], recorded_at=NOW)
    bundle["outputs"]["schema_name"] = "runeforge.other"
    with pytest.raises(wb.WorldError) as exc:
        wb.import_bundle(bundle)
    assert "schema_unknown" in exc.value.detail


def test_import_unsupported_version_refused_by_name(mods):
    wb = mods["world_bridge"]
    bundle = wb.export_bundle([DOC], recorded_at=NOW)
    bundle["outputs"]["version"] = 99
    with pytest.raises(wb.WorldError) as exc:
        wb.import_bundle(bundle)
    assert "schema_version_unsupported:99" in exc.value.detail


def test_import_hash_mismatch_refused(mods):
    wb = mods["world_bridge"]
    bundle = wb.export_bundle([DOC], recorded_at=NOW)
    bundle["outputs"]["documents"][0]["sha256"] = "0" * 64
    with pytest.raises(wb.WorldError) as exc:
        wb.import_bundle(bundle)
    assert "content_hash_mismatch" in exc.value.detail


def test_shared_import_read_only_unless_promoted(mods):
    wb = mods["world_bridge"]
    bundle = wb.export_bundle([DOC], recorded_at=NOW)
    assert wb.import_bundle(bundle)[0]["read_only"] is True
    assert wb.import_bundle(bundle, promote_shared=True)[0]["read_only"] is False


def test_world_event_requires_full_provenance(mods):
    wb = mods["world_bridge"]
    with pytest.raises(wb.WorldError) as exc:
        wb.make_world_event("observation", {"t": 20}, provenance={"service": "wyrd"})
    assert "provenance_field_required" in exc.value.detail


def test_world_event_unknown_kind_refused(mods):
    wb = mods["world_bridge"]
    with pytest.raises(wb.WorldError) as exc:
        wb.make_world_event("rumor", {}, provenance=PROV)
    assert "event_kind_unknown:rumor" in exc.value.detail


def test_world_event_routes_to_wyrd_with_provenance(mods):
    wb = mods["world_bridge"]
    event = wb.make_world_event("observation", {"t": 20}, provenance=PROV)
    routed = wb.route_world_event(event, "wyrd")
    assert routed["routed_to"] == "wyrd"
    assert routed["event"]["provenance"]["source_ref"] == "sensor:hall-1"


@pytest.mark.parametrize("store", ["persona", "fictional", "persona-memory"])
def test_world_event_persona_blending_refused(mods, store):
    wb = mods["world_bridge"]
    event = wb.make_world_event("observation", {"t": 20}, provenance=PROV)
    with pytest.raises(wb.WorldError) as exc:
        wb.route_world_event(event, store)
    assert "world_event_persona_blending_refused" in exc.value.detail


def test_presence_cannot_read_private_persona(mods):
    wb = mods["world_bridge"]
    decision = wb.authorize_presence(
        caller="volmarr", action="read", data_owner="volmarr",
        data_class="local-private", approved=True)
    assert decision["allowed"] is False
    assert any("data_class_not_declared" in r for r in decision["reasons"])


def test_presence_non_owner_refused(mods):
    wb = mods["world_bridge"]
    decision = wb.authorize_presence(
        caller="someone-else", action="read", data_owner="volmarr",
        data_class="shared", approved=True)
    assert decision["allowed"] is False
    assert "owner_only_service" in decision["reasons"]


def test_hud_filter_drops_sensitive_and_unknown(mods):
    wb = mods["world_bridge"]
    out = wb.hud_filter({"kind": "metric", "value": 3, "transcript": "secret words",
                         "token": "abc", "mystery": 1})
    assert out["event"] == {"kind": "metric", "value": 3}
    assert out["dropped_sensitive"] == ["token", "transcript"]
    assert out["dropped_unknown"] == ["mystery"]


def test_avatar_layers_separate_decisions(mods):
    wb = mods["world_bridge"]
    out = wb.separate_avatar_layers(
        {"view": "hall", "gesture": "wave", "decision": "go north"})
    assert out["view"] == {"view": "hall"}
    assert out["animation"] == {"gesture": "wave"}
    assert out["decision_fields_named"] == ["decision"]


def test_availability_no_probe_is_unavailable(mods):
    wb = mods["world_bridge"]
    assert wb.availability(None) == {
        "available": False, "capabilities": [], "reason": "no_probe_result"}
    ok = wb.availability({"ok": True, "exposed": ["temperature"]})
    assert ok["available"] is True and ok["capabilities"] == ["temperature"]


def test_work_queue_offline_then_flush_once(mods):
    wb = mods["world_bridge"]
    queue = wb.WorkQueue()
    assert queue.enqueue("a", {"x": 1})["queued"] is True
    assert queue.enqueue("a", {"x": 1})["queued"] is False
    assert queue.flush(online=False)["pending"] == 1
    flushed = queue.flush(online=True)
    assert flushed["flushed"] == ["a"] and queue.pending() == 0
    assert queue.enqueue("a", {"x": 1})["queued"] is False
