"""X.11 Aurelia Sensations Server contracts (roadmap section 46).

These contracts pin the section 46 gates on the private
state-simulation connector: unconfigured truthfulness, configured
measurement of a staged tree's structure only (privacy canary:
intimate content staged under data/ in the tree never appears in
any record), the narrow contract catalog with direct device
control / canon edit / external egress refused, per-persona scope
isolation, simulated state never written into authored canon,
guarded event plans (idempotent event ids, consent scopes,
content fields refused by name), redacted content-free lifecycle
records, revocable consent, and checkpoint replay after
interruption. No live server is contacted by any contract.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path

import pytest

HEAD = "d6c2632435bd3034dfcd34df1ba1e9a7a799e947"
LICENSE_SHA = "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"
CANARY = "PRIVATE-CANARY-SENSATION-DATA-9c41"


@pytest.fixture(scope="module")
def mods():
    from hermes_cli import plugins as plugins_mod
    from hermes_constants import get_hermes_home

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
               for name in ("aurelia", "cli")}
    finally:
        manager.unload()
    return out


class FakeCtx:
    def __init__(self, cfg=None):
        self._cfg = cfg or {}

    def get_config(self, key, default=None):
        return self._cfg.get(key, default)


def _fake_tree(tmp_path: Path) -> Path:
    root = tmp_path / "aurelia"
    (root / ".git" / "refs" / "heads").mkdir(parents=True)
    (root / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (root / ".git" / "refs" / "heads" / "main").write_text(HEAD + "\n", encoding="utf-8")
    (root / "aurelia_agent_server.py").write_text(
        'app = FastAPI(title="Aurelia Agent Server", version="1.0.0",\n'
        '              lifespan=lifespan)\n', encoding="utf-8")
    license_bytes = b"fake license text for structure only"
    (root / "LICENSE").write_bytes(license_bytes)
    pkg = root / "female_motivation"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "agent.py").write_text("", encoding="utf-8")
    data = root / "data"
    data.mkdir()
    (data / "sensations.yaml").write_text(CANARY, encoding="utf-8")
    return root


def test_status_unconfigured_is_truthful(mods):
    au = mods["aurelia"]
    record = au.aurelia_status(FakeCtx(), recorded_at="t")
    assert record["schema"] == "runeforge.aurelia.status.v1"
    assert record["canonical_repo"] == "hrabanazviking/RuneForgeAI-Aurelia-Sensations-Server"
    assert record["audited_head"] == HEAD == au.AUDITED_HEAD
    assert record["server_version"] == "1.0.0"
    assert record["license"] == "Apache-2.0"
    assert record["enabled"] is False
    assert record["configured"] is False
    assert record["tree"]["status"] == "not_configured"
    assert record["sends_anything_external"] is False
    assert record["edits_canon"] is False
    assert record["experimental"] is True
    assert record["production_ready"] is False


def test_status_configured_measures_tree_and_denies_egress(mods, tmp_path):
    au = mods["aurelia"]
    root = _fake_tree(tmp_path)
    ctx = FakeCtx({"aurelia_enabled": True, "aurelia_root": str(root)})
    record = au.aurelia_status(ctx, recorded_at="t")
    assert record["enabled"] is True and record["configured"] is True
    tree = record["tree"]
    assert tree["status"] == "measured"
    assert tree["head"] == HEAD and tree["head_matches_audited"] is True
    assert tree["server_version"] == "1.0.0"
    assert tree["module_count"] == 3
    assert tree["license_sha256"] == hashlib.sha256(
        b"fake license text for structure only").hexdigest()
    assert tree["license_matches_audited"] is False
    # Privacy canary: intimate content staged under data/ in the
    # tree never appears in status, catalog or plan output.
    blob = json.dumps(record) + json.dumps(au.contract_catalog())
    blob += json.dumps(au.build_event_plan(
        au.SYNTHETIC_EVENTS, persona=au.SYNTHETIC_PERSONA,
        consent_scopes=au.SYNTHETIC_CONSENT))
    assert CANARY not in blob
    assert au.LICENSE_SHA256 == LICENSE_SHA


def test_catalog_refuses_control_canon_and_egress(mods):
    au = mods["aurelia"]
    catalog = au.contract_catalog()
    by_kind = {row["kind"]: row for row in catalog["contracts"]}
    assert by_kind["health"]["supported"] is True
    assert by_kind["state_snapshot"]["supported"] is True
    assert by_kind["state_event"]["supported"] is True
    assert by_kind["simulation_pause"]["supported"] is True
    assert by_kind["direct_device_control"]["supported"] is False
    assert by_kind["canon_edit"]["supported"] is False
    assert by_kind["external_egress"]["supported"] is False
    assert "publish" in catalog["egress_verbs_refused"]
    assert "payload" in catalog["content_fields_refused"]
    assert catalog["sends_anything_external"] is False
    assert catalog["production_ready"] is False


def test_scope_isolation_and_canon_separation(mods):
    au = mods["aurelia"]
    own = au.check_scope("persona-a", "persona-a")
    assert own["allowed"] is True and own["refused"] is None
    cross = au.check_scope("persona-a", "persona-b")
    assert cross["allowed"] is False
    assert cross["refused"] == "cross_persona_scope_refused"
    canon = au.check_scope("persona-a", "persona-a", target="canon")
    assert canon["allowed"] is False
    assert canon["refused"] == "simulated_state_not_canon"


def test_event_plan_guards(mods):
    au = mods["aurelia"]
    plan = au.build_event_plan([
        {"kind": "health", "event_id": "e1", "scope": "state_read"},
        {"kind": "health", "event_id": "e1", "scope": "state_read"},
        {"kind": "state_event", "event_id": "e2", "scope": "ungranted"},
        {"kind": "state_event", "scope": "state_read"},
        {"kind": "direct_device_control", "event_id": "e3", "scope": "state_read"},
        {"kind": "canon_edit", "event_id": "e4", "scope": "state_read"},
        {"kind": "publish", "event_id": "e5", "scope": "state_read"},
        {"kind": "state_event", "event_id": "e6", "scope": "state_read",
         "payload": "intimate"},
        {"kind": "bogus", "event_id": "e7", "scope": "state_read"},
        {"kind": "state_event", "event_id": "e8", "scope": "state_read",
         "persona": "persona-b"},
    ], persona="persona-a", consent_scopes=["state_read"])
    assert plan["event_count"] == 1 and plan["refused_count"] == 9
    reasons = {row["index"]: row["reason"] for row in plan["refused"]}
    assert reasons == {1: "duplicate_event_idempotent",
                       2: "consent_scope_required",
                       3: "event_id_required",
                       4: "contract_refused",
                       5: "contract_refused",
                       6: "egress_refused",
                       7: "intimate_content_not_accepted",
                       8: "unknown_contract",
                       9: "cross_persona_scope_refused"}
    step = plan["events"][0]
    assert step["content_included"] is False and step["bounds_checked"] is True
    assert step["provenance"]["audited_head"] == HEAD
    receipt = step["audit_receipt"]
    assert receipt["content_included"] is False and receipt["local_only"] is True
    assert plan["runs_server"] is False and plan["edits_canon"] is False
    assert plan["production_ready"] is False


def test_lifecycle_record_is_content_free(mods):
    au = mods["aurelia"]
    record = au.lifecycle_record(persona="persona-a", kind="state_event",
                                 event_id="evt-123")
    assert record["content_included"] is False
    assert "evt-123" not in json.dumps(record)
    again = au.lifecycle_record(persona="persona-a", kind="state_event",
                                event_id="evt-123")
    assert again["event_ref"] == record["event_ref"]


def test_consent_grant_and_revoke(mods, tmp_path):
    au = mods["aurelia"]
    granted = au.grant_consent(tmp_path, "persona-a", "state_read")
    assert granted["scopes"] == ["state_read"] and granted["revoked"] is False
    plan = au.build_event_plan(
        [{"kind": "health", "event_id": "e1", "scope": "state_read"}],
        persona="persona-a", consent_scopes=granted["scopes"])
    assert plan["event_count"] == 1
    revoked = au.revoke_consent(tmp_path, "persona-a", "state_read")
    assert revoked["scopes"] == [] and revoked["revoked"] is True
    plan = au.build_event_plan(
        [{"kind": "health", "event_id": "e1", "scope": "state_read"}],
        persona="persona-a", consent_scopes=revoked["scopes"])
    assert plan["event_count"] == 0
    assert plan["refused"][0]["reason"] == "consent_scope_required"


def test_checkpoint_resume_after_interruption(mods, tmp_path):
    au = mods["aurelia"]
    plan = au.build_event_plan([
        {"kind": "health", "event_id": "e1", "scope": "state_read"},
        {"kind": "simulation_step", "event_id": "e2", "scope": "state_read"},
        {"kind": "simulation_pause", "event_id": "e3", "scope": "state_read"},
    ], persona="persona-a", consent_scopes=["state_read"])
    au.write_checkpoint(tmp_path, plan, completed=[0])
    resumed = au.resume_plan(tmp_path, plan["plan_key"])
    assert resumed["resumed"] is True and resumed["completed_count"] == 1
    assert [e["kind"] for e in resumed["remaining"]] == [
        "simulation_step", "simulation_pause"]


def _run_cli(mods, argv, ctx):
    cli = mods["cli"]
    parser = argparse.ArgumentParser(prog="hermes")
    sub = parser.add_subparsers(dest="command")
    volmarr_parser = sub.add_parser("volmarr")
    cli.register_cli(volmarr_parser)
    args = parser.parse_args(argv)
    return cli.health_command(args, ctx=ctx)


def test_cli_aurelia_family(mods, capsys):
    ctx = FakeCtx()
    assert _run_cli(mods, ["volmarr", "aurelia", "status", "--json"], ctx) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["tree"]["status"] == "not_configured"
    assert out["production_ready"] is False
    assert _run_cli(mods, ["volmarr", "aurelia", "catalog", "--json"], ctx) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["sends_anything_external"] is False
    assert _run_cli(mods, ["volmarr", "aurelia", "plan", "--json"], ctx) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event_count"] == 2 and out["refused_count"] == 3
    assert out["runs_server"] is False
    reasons = {row["kind"]: row["reason"] for row in out["refused"]}
    assert reasons == {"state_event": "consent_scope_required",
                       "direct_device_control": "contract_refused",
                       "publish": "egress_refused"}
    assert _run_cli(mods, ["volmarr", "aurelia"], ctx) == 2
    capsys.readouterr()
