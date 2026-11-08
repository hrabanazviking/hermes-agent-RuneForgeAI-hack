"""W09/N1 capability bus: descriptors, registry, policy, envelopes.

Roadmap section 20 proposes a versioned Capability Descriptor and a
shared bus instead of a monolith. These contracts pin the first
slice: descriptors validate strictly and malformed contracts are
refused by name, the registry expires cached descriptors, discovery
refuses malformed files by name, the permission policy is fail-closed
(writes need approval, local-private data never travels to the cloud,
cross-owner calls need scoped auth + approval), results cannot be
constructed without provenance, jobs are idempotent, and the three
built-in seed descriptors describe real fork tools at their real
plugin.yaml versions with their adapter files present in this tree.
CLI tests drive the real ``hermes volmarr capabilities`` family
through the plugin's own argparse registration and dispatcher.
"""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

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
               for name in ("capability_bus", "cli")}
    finally:
        manager.unload()
    return out


def _descriptor(**overrides):
    base = {
        "schema": "runeforge.capability.v1",
        "service": "example",
        "version": "1.2.3",
        "owner": "volmarr",
        "actions": ["read", "propose", "write"],
        "transport": "loopback-http",
        "auth": "scoped",
        "side_effects": True,
        "privacy_classes": ["public", "shared", "local-private"],
        "availability": "proven-by-live-probe",
        "timeout_ms": 2000,
    }
    base.update(overrides)
    return base


def test_valid_descriptor_passes(mods):
    bus = mods["capability_bus"]
    assert bus.validate_descriptor(_descriptor()) == []
    assert bus.require_valid(_descriptor())["service"] == "example"


def test_malformed_descriptors_refused_by_name(mods):
    bus = mods["capability_bus"]
    bad = _descriptor()
    del bad["owner"]
    assert bus.validate_descriptor(bad) == ["missing_field:owner"]
    assert "schema_mismatch:other" in bus.validate_descriptor(
        _descriptor(schema="other"))
    assert "transport_unknown:smoke-signal" in bus.validate_descriptor(
        _descriptor(transport="smoke-signal"))
    assert "actions_invalid" in bus.validate_descriptor(_descriptor(actions=[]))
    assert "timeout_ms_out_of_range" in bus.validate_descriptor(
        _descriptor(timeout_ms=0))
    assert "privacy_classes_invalid" in bus.validate_descriptor(
        _descriptor(privacy_classes=["secret"]))
    with pytest.raises(bus.CapabilityError) as exc:
        bus.require_valid(_descriptor(auth="open"))
    assert exc.value.name == "validation_failure"


def test_registry_expiry_and_replacement(mods):
    bus = mods["capability_bus"]
    reg = bus.CapabilityRegistry()
    reg.register(_descriptor(ttl_s=10), now=100.0)
    assert reg.get("example", now=109.0)["version"] == "1.2.3"
    assert reg.get("example", now=110.0) is None
    assert reg.services(now=110.0) == []
    reg.register(_descriptor(version="2.0.0", ttl_s=10), now=200.0)
    assert reg.get("example", now=201.0)["version"] == "2.0.0"
    assert reg.services(now=201.0) == ["example"]


def test_discovery_refuses_malformed_files_by_name(mods, tmp_path):
    bus = mods["capability_bus"]
    (tmp_path / "good.json").write_text(
        json.dumps(_descriptor(service="goodsvc")), encoding="utf-8")
    (tmp_path / "bad.json").write_text(
        json.dumps({"schema": "nope"}), encoding="utf-8")
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    reg = bus.CapabilityRegistry()
    record = reg.discover(tmp_path, now=0.0)
    assert record["loaded"] == ["goodsvc"]
    assert any(p.startswith("bad.json:") for p in record["problems"])
    assert any(p.startswith("broken.json:unreadable") for p in record["problems"])
    missing = reg.discover(tmp_path / "nope", now=0.0)
    assert missing["loaded"] == []
    assert missing["problems"]


def test_policy_allows_plain_local_read(mods):
    bus = mods["capability_bus"]
    decision = bus.authorize(
        _descriptor(), caller="volmarr", action="read",
        data_owner="volmarr", data_class="local-private",
        destination="local")
    assert decision == {"allowed": True, "reasons": []}


def test_policy_refuses_absent_service_and_unoffered_action(mods):
    bus = mods["capability_bus"]
    assert bus.authorize(
        None, caller="volmarr", action="read", data_owner="volmarr",
        data_class="public", destination="local"
    ) == {"allowed": False, "reasons": ["service_unavailable"]}
    decision = bus.authorize(
        _descriptor(), caller="volmarr", action="execute",
        data_owner="volmarr", data_class="public", destination="local",
        approved=True)
    assert not decision["allowed"]
    assert "action_not_offered:execute" in decision["reasons"]


def test_policy_write_and_side_effects_require_approval(mods):
    bus = mods["capability_bus"]
    decision = bus.authorize(
        _descriptor(), caller="volmarr", action="write",
        data_owner="volmarr", data_class="public", destination="local")
    assert not decision["allowed"]
    assert "write_action_requires_approval" in decision["reasons"]
    assert "side_effect_service_requires_approval" in decision["reasons"]
    ok = bus.authorize(
        _descriptor(), caller="volmarr", action="write",
        data_owner="volmarr", data_class="public", destination="local",
        approved=True)
    assert ok["allowed"]


def test_policy_privacy_travel_is_fail_closed(mods):
    bus = mods["capability_bus"]
    decision = bus.authorize(
        _descriptor(), caller="volmarr", action="read",
        data_owner="volmarr", data_class="local-private",
        destination="cloud")
    assert not decision["allowed"]
    assert "privacy_travel_refused:local-private->cloud" in decision["reasons"]
    shared = bus.authorize(
        _descriptor(), caller="volmarr", action="read",
        data_owner="volmarr", data_class="shared", destination="public")
    assert not shared["allowed"]
    public = bus.authorize(
        _descriptor(), caller="volmarr", action="read",
        data_owner="volmarr", data_class="public", destination="cloud")
    assert public["allowed"]


def test_policy_owner_rules(mods):
    bus = mods["capability_bus"]
    scoped = bus.authorize(
        _descriptor(), caller="yrsa", action="read",
        data_owner="volmarr", data_class="public", destination="local")
    assert not scoped["allowed"]
    assert "cross_owner_requires_approval" in scoped["reasons"]
    assert bus.authorize(
        _descriptor(), caller="yrsa", action="read",
        data_owner="volmarr", data_class="public", destination="local",
        approved=True)["allowed"]
    owner_only = bus.authorize(
        _descriptor(auth="owner-only"), caller="yrsa", action="read",
        data_owner="yrsa", data_class="public", destination="local",
        approved=True)
    assert not owner_only["allowed"]
    assert "owner_only_service" in owner_only["reasons"]
    unscoped = bus.authorize(
        _descriptor(auth="none"), caller="yrsa", action="read",
        data_owner="volmarr", data_class="public", destination="local",
        approved=True)
    assert not unscoped["allowed"]
    assert "cross_owner_requires_scoped_auth" in unscoped["reasons"]


def test_policy_device_restriction(mods):
    bus = mods["capability_bus"]
    descriptor = _descriptor(devices=["purplelongship"])
    refused = bus.authorize(
        descriptor, caller="volmarr", action="read",
        data_owner="volmarr", data_class="public", destination="local",
        device="mimir")
    assert not refused["allowed"]
    assert "device_not_allowed:mimir" in refused["reasons"]
    assert bus.authorize(
        descriptor, caller="volmarr", action="read",
        data_owner="volmarr", data_class="public", destination="local",
        device="purplelongship")["allowed"]


def test_result_envelope_requires_provenance(mods):
    bus = mods["capability_bus"]
    env = bus.result_envelope(
        _descriptor(), outputs={"answer": 42}, source_ref="fixture:1",
        recorded_at="2026-11-08T04:30:00-05:00",
        confidentiality="local-private")
    assert env["status"] == "completed"
    assert env["provenance"]["source_ref"] == "fixture:1"
    assert env["provenance"]["service"] == "example"
    with pytest.raises(bus.CapabilityError):
        bus.result_envelope(
            _descriptor(), outputs={}, source_ref="",
            recorded_at="2026-11-08T04:30:00-05:00",
            confidentiality="public")
    with pytest.raises(bus.CapabilityError):
        bus.result_envelope(
            _descriptor(), outputs={}, source_ref="fixture:1",
            recorded_at="2026-11-08T04:30:00-05:00",
            confidentiality="secret")


def test_error_envelope_categories(mods):
    bus = mods["capability_bus"]
    env = bus.error_envelope(
        _descriptor(), category="timeout", detail="svc slow",
        recorded_at="2026-11-08T04:30:00-05:00")
    assert env["status"] == "timeout"
    assert env["service"] == "example"
    for category in bus.ERROR_CATEGORIES:
        assert bus.error_envelope(
            None, category=category, detail="d",
            recorded_at="t")["status"] == category
    with pytest.raises(bus.CapabilityError):
        bus.error_envelope(
            None, category="exploded", detail="d", recorded_at="t")


def test_jobs_are_idempotent_and_transition_guarded(mods):
    bus = mods["capability_bus"]
    book = bus.JobBook()
    job = book.create(
        _descriptor(), action="read", idempotency_key="k-1", now=1.0)
    again = book.create(
        _descriptor(), action="read", idempotency_key="k-1", now=2.0)
    assert again["job_id"] == job["job_id"]
    assert book.transition(job["job_id"], "running")["status"] == "running"
    with pytest.raises(bus.CapabilityError):
        book.transition(job["job_id"], "created")
    assert book.transition(job["job_id"], "completed")["status"] == "completed"
    with pytest.raises(bus.CapabilityError):
        book.transition(job["job_id"], "cancelled")
    with pytest.raises(bus.CapabilityError):
        book.create(_descriptor(), action="execute",
                    idempotency_key="k-2", now=3.0)


def test_builtin_seeds_are_real_fork_tools(mods):
    bus = mods["capability_bus"]
    status = bus.builtin_status()
    assert status["status"] == "ok", status["problems"]
    assert status["service_count"] == 3
    by_service = {row["service"]: row for row in status["services"]}
    assert by_service["volmarr-astrology"]["version"] == "0.7.0"
    assert by_service["volmarr-tarot"]["version"] == "0.3.0"
    assert by_service["volmarr-seidr"]["version"] == "0.4.0"
    assert all(row["adapter_present"] for row in status["services"])
    assert all(
        row["availability"] == "contract-implemented"
        for row in status["services"])


class _Ctx:
    def __init__(self, config=None):
        self._config = dict(config or {})

    def get_config(self, key, default=None):
        return self._config.get(key, default)


def _run_cli(mods, argv):
    cli = mods["cli"]
    parser = argparse.ArgumentParser(prog="hermes")
    sub = parser.add_subparsers(dest="command")
    volmarr_parser = sub.add_parser("volmarr")
    cli.register_cli(volmarr_parser)
    args = parser.parse_args(argv)
    return cli.health_command(args, ctx=_Ctx())


def test_cli_capabilities_list_show_validate(mods, capsys):
    assert _run_cli(mods, ["volmarr", "capabilities", "list", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["service_count"] == 3
    assert _run_cli(mods, ["volmarr", "capabilities", "validate"]) == 0
    assert "valid" in capsys.readouterr().out
    assert _run_cli(
        mods, ["volmarr", "capabilities", "show", "volmarr-tarot",
               "--json"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["service"] == "volmarr-tarot"
    assert shown["actions"] == ["draw_tarot"]
    assert _run_cli(
        mods, ["volmarr", "capabilities", "show", "nope"]) == 1
    capsys.readouterr()


def test_cli_capabilities_authorize(mods, capsys):
    rc = _run_cli(mods, [
        "volmarr", "capabilities", "authorize",
        "--service", "volmarr-tarot", "--caller", "volmarr",
        "--action", "draw_tarot", "--data-owner", "volmarr",
        "--data-class", "local-private", "--destination", "local",
        "--json"])
    assert rc == 0
    decision = json.loads(capsys.readouterr().out)
    assert decision["allowed"]
    rc = _run_cli(mods, [
        "volmarr", "capabilities", "authorize",
        "--service", "volmarr-tarot", "--caller", "volmarr",
        "--action", "draw_tarot", "--data-owner", "volmarr",
        "--data-class", "local-private", "--destination", "cloud",
        "--json"])
    assert rc == 1
    decision = json.loads(capsys.readouterr().out)
    assert not decision["allowed"]
    assert "privacy_travel_refused:local-private->cloud" in decision["reasons"]
