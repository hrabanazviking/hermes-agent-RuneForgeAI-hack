"""X.15 Seidr-Smidja contracts (roadmap section 50).

These contracts pin the section 50 test gates on the forge
connector at record level with fakes: unconfigured
truthfulness, configured measurement of a staged tree, the
forge spec v1 catalog with its honest capability matrix,
fake render prerequisite failure, invalid spec rejection by
name, the asset license gate, the VRM inspection record,
cancellation cleanup, wrong-host refusal, approval refusal,
Hamr incompatibility errors, privacy refusals and
presentation-only routing. No Blender, engine or remote
control is run by any contract.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path

import pytest

PIN = "32cdbd7a87358bc1f6f046c4e1449c35f4d5d40a"
LICENSE_SHA = "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"
CONFLICT = "CONFLICT: root Apache-2.0; pyproject MIT (E14-T1)"


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
               for name in ("smidja_forge", "cli")}
    finally:
        manager.unload()
    return out


class FakeCtx:
    def __init__(self, cfg=None):
        self._cfg = cfg or {}

    def get_config(self, key, default=None):
        return self._cfg.get(key, default)


def _fake_tree(tmp_path: Path) -> Path:
    root = tmp_path / "smidja"
    (root / ".git" / "refs" / "heads").mkdir(parents=True)
    (root / ".git" / "HEAD").write_text(
        "ref: refs/heads/development\n", encoding="utf-8")
    (root / ".git" / "refs" / "heads" / "development").write_text(
        PIN + "\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "seidr-smidja"\nversion = "0.1.0.dev0"\n'
        'license = { text = "MIT" }\n', encoding="utf-8")
    (root / "LICENSE").write_bytes(b"fake license text for structure only")
    pkg = root / "src" / "seidr_smidja"
    for module in ("loom", "hoard", "gate", "oracle_eye", "forge", "brunhand"):
        (pkg / module).mkdir(parents=True)
    return root


def _spec(root: Path, **overrides):
    spec = {
        "job_id": "forge-test-001", "spec_version": "runeforge.smidja.forge.v1",
        "avatar_id": "test_avatar_v1", "host": "test-host",
        "spec_path": str(root / "specs" / "a.yaml"),
        "output_dir": str(root / "output"),
        "metadata": {"version": "1.0"}, "blender_version": "4.2",
        "export": {"format": "vrm", "vrm_version": "1.0", "exporter": "io_scene_vrm"},
        "budget": {"cpu_cores": 4, "gpu_required": False, "max_memory_mb": 1500.0,
                   "max_triangles": 50000, "max_texture_resolution": 1024},
        "timeout_seconds": 120.0,
        "log_capture": {"mode": "record"},
        "cancellation": {"mode": "record_cancel"},
        "cleanup": {"mode": "record_level",
                    "artifact_paths": [str(root / "output" / "a.vrm")]},
        "assets": [{"asset_id": "vroid/sample_a", "provenance": "hoard catalog",
                    "license": "CC0-1.0", "path": str(root / "assets" / "a.vrm")}],
    }
    spec.update(overrides)
    return spec


def _plan(mods, tmp_path, **request_overrides):
    sf = mods["smidja_forge"]
    root = tmp_path / "approved"
    request = {"spec": _spec(root), "destination": "local_only"}
    request.update(request_overrides)
    return sf.plan_build(request, approved_roots=[str(root)], host="test-host")


def test_status_unconfigured_is_truthful(mods):
    sf = mods["smidja_forge"]
    record = sf.smidja_forge_status(FakeCtx(), recorded_at="t")
    assert record["schema"] == "runeforge.smidja.status.v1"
    assert record["canonical_repo"] == "hrabanazviking/Seidr-Smidja"
    assert record["audited_pin"] == PIN == sf.AUDITED_PIN
    assert record["engine_version"] == "0.1.0.dev0"
    assert record["license"] == "Apache-2.0"
    assert record["license_conflict"] == CONFLICT
    assert record["enabled"] is False and record["configured"] is False
    assert "Configure smidja_forge_enabled" in record["configuration_error"]
    assert record["tree"]["status"] == "not_configured"
    assert record["sends_anything_external"] is False
    assert record["executes_operations"] is False
    assert record["production_ready"] is False


def test_status_configured_measures_tree(mods, tmp_path):
    sf = mods["smidja_forge"]
    root = _fake_tree(tmp_path)
    ctx = FakeCtx({"smidja_forge_enabled": True, "smidja_forge_root": str(root)})
    record = sf.smidja_forge_status(ctx, recorded_at="t")
    assert record["enabled"] is True and record["configured"] is True
    assert "configuration_error" not in record
    tree = record["tree"]
    assert tree["status"] == "measured"
    assert tree["head"] == PIN and tree["head_matches_pin"] is True
    assert tree["package_name"] == "seidr-smidja"
    assert tree["package_version"] == "0.1.0.dev0"
    assert tree["pyproject_license_declared"] == "MIT"
    assert tree["modules_present"] == ["loom", "hoard", "gate", "oracle_eye", "forge", "brunhand"]
    assert tree["modules_missing"] == []
    assert tree["license_sha256"] == hashlib.sha256(
        b"fake license text for structure only").hexdigest()
    assert tree["license_matches_audited"] is False
    assert sf.LICENSE_SHA256 == LICENSE_SHA


def test_catalog_forge_schema_and_honest_matrix(mods):
    sf = mods["smidja_forge"]
    catalog = sf.forge_catalog()
    assert catalog["schema"] == "runeforge.smidja.catalog.v1"
    assert catalog["forge_spec_schema"]["version"] == "runeforge.smidja.forge.v1"
    assert catalog["license_conflict"] == CONFLICT
    assert catalog["preflight_adapter"]["preserved_untouched"] is True
    assert catalog["preflight_adapter"]["only_live_engine_surface"] is True
    matrix = {row["capability"]: row["live"] for row in catalog["capability_matrix"]}
    assert matrix["read_only_preflight"] is True
    assert matrix["dry_run_build_plan"] is True
    assert matrix["live_remote_control"] is False
    assert matrix["blender_build"] is False
    assert matrix["vrm_export"] is False
    assert matrix["visual_validation"] is False
    assert catalog["hamr_reconciliation"]["one_avatar_standard"] is True
    assert catalog["production_ready"] is False
    assert catalog["executes_operations"] is False


def test_plan_dry_run_executes_nothing(mods, tmp_path):
    sf = mods["smidja_forge"]
    plan = _plan(mods, tmp_path)
    assert plan["schema"] == "runeforge.smidja.plan.v1"
    assert plan["outcome"] == "plan" and plan["accepted"] is True
    assert plan["dry_run"] is True and plan["job_state"] == "planned"
    assert plan["job_id"] == "forge-test-001"
    assert len(plan["plan_key"]) == 64
    assert plan["asset_inventory"][0]["license_known"] is True
    assert plan["license_gaps_named"] == []
    assert plan["executes_operations"] is False and plan["writes_files"] is False
    assert plan["runs_engine"] is False and plan["production_ready"] is False
    assert plan["license_conflict"] == CONFLICT
    assert plan["latency_ms"] < sf.PERFORMANCE_BUDGET_MS == 250
    again = _plan(mods, tmp_path)
    assert again["plan_key"] == plan["plan_key"]


def test_fake_render_prerequisite_fail(mods, tmp_path):
    plan = _plan(mods, tmp_path, render_prerequisites={"blender_available": False})
    assert plan["outcome"] == "failure"
    assert plan["failure"] == "render_prerequisite_failed"
    assert plan["prerequisite"] == "blender_available"
    assert plan["fail_closed"] is True


def test_invalid_spec_rejected_by_name(mods, tmp_path):
    sf = mods["smidja_forge"]
    root = tmp_path / "approved"
    bad_version = sf.plan_build({"spec": _spec(root, spec_version="v9")},
                                approved_roots=[str(root)], host="test-host")
    assert bad_version["failure"] == "spec_version_unsupported"
    bad_job = sf.plan_build({"spec": _spec(root, job_id="nope")},
                            approved_roots=[str(root)], host="test-host")
    assert bad_job["failure"] == "job_id_invalid"
    traversal = sf.plan_build(
        {"spec": _spec(root, spec_path="/etc/passwd.yaml")},
        approved_roots=[str(root)], host="test-host")
    assert traversal["failure"] == "path_traversal_refused"
    assert traversal["validation"]["field"] == "spec_path"
    no_meta = sf.plan_build({"spec": _spec(root, metadata={})},
                            approved_roots=[str(root)], host="test-host")
    assert no_meta["failure"] == "metadata_version_missing"
    not_mapping = sf.plan_build("nope", approved_roots=[str(root)], host="test-host")
    assert not_mapping["failure"] == "request_not_mapping"


def test_asset_license_gate(mods, tmp_path):
    sf = mods["smidja_forge"]
    root = tmp_path / "approved"
    unknown = [{"asset_id": "mystery/asset", "provenance": "hoard catalog",
                "path": str(root / "assets" / "m.bin")}]
    refused = sf.plan_build(
        {"spec": _spec(root, assets=unknown), "redistribution": True},
        approved_roots=[str(root)], host="test-host")
    assert refused["failure"] == "asset_license_unknown_redistribution_refused"
    assert refused["assets"] == ["mystery/asset"]
    named = sf.plan_build({"spec": _spec(root, assets=unknown)},
                          approved_roots=[str(root)], host="test-host")
    assert named["outcome"] == "plan"
    assert named["license_gaps_named"] == ["mystery/asset"]
    assert named["asset_inventory"][0]["license_known"] is False
    no_prov = sf.plan_build(
        {"spec": _spec(root, assets=[{"asset_id": "x/y", "license": "CC0-1.0"}])},
        approved_roots=[str(root)], host="test-host")
    assert no_prov["failure"] == "asset_provenance_missing"


def test_vrm_inspection_record(mods):
    sf = mods["smidja_forge"]
    record = sf.inspect_vrm_record(
        {"artifact_id": "out/a", "format": "vrm", "vrm_version": "1.0"})
    assert record["inspected"] is True
    assert record["inspection_scope"] == "metadata_only"
    assert record["compliance_performed"] is False
    assert record["visual_validation_performed"] is False
    bad = sf.inspect_vrm_record({"artifact_id": "out/a", "format": "blend"})
    assert bad["failure"] == "artifact_format_unsupported"
    missing = sf.inspect_vrm_record({"format": "vrm"})
    assert missing["failure"] == "artifact_id_missing"


def test_approval_gate_refusal_and_pass_executes_nothing(mods, tmp_path):
    sf = mods["smidja_forge"]
    plan = _plan(mods, tmp_path)
    refused = sf.approve_job(plan)
    assert refused["approved"] is False
    assert refused["reason"] == "approval_refused_operator_authorization_required"
    assert refused["executed"] is False
    no_operator = sf.approve_job(plan, operator_authorized=True)
    assert no_operator["approved"] is False
    approved = sf.approve_job(plan, operator_authorized=True, operator="volmarr")
    assert approved["approved"] is True and approved["job_state"] == "approved"
    assert approved["authorization_recorded"] is True
    assert approved["executed"] is False and approved["runs_engine"] is False
    not_planned = sf.approve_job({"job_state": "cancelled"},
                                 operator_authorized=True, operator="volmarr")
    assert not_planned["reason"] == "job_not_planned"


def test_cancellation_cleanup_record(mods, tmp_path):
    sf = mods["smidja_forge"]
    root = tmp_path / "approved"
    plan = _plan(mods, tmp_path)
    record = sf.cancel_job(plan, approved_roots=[str(root)])
    assert record["cancelled"] is True and record["job_state"] == "cancelled"
    cleanup = record["cleanup_record"]
    assert cleanup["mode"] == "record_level_only" and cleanup["deleted"] is False
    assert cleanup["artifact_paths"][0]["validated_under_approved_root"] is True
    assert record["executes_operations"] is False
    missing = sf.cancel_job({})
    assert missing["failure"] == "job_missing"


def test_wrong_host_refusal(mods, tmp_path):
    sf = mods["smidja_forge"]
    root = tmp_path / "approved"
    plan = sf.plan_build({"spec": _spec(root, host="some-other-host")},
                         approved_roots=[str(root)], host="test-host")
    assert plan["failure"] == "wrong_host_refused"
    assert plan["validation"]["host"] == "some-other-host"
    assert plan["validation"]["local_host"] == "test-host"


def test_hamr_translation_incompatibilities_named(mods, tmp_path):
    sf = mods["smidja_forge"]
    ok = sf.translate_hamr_to_forge(
        {"name": "avatar_a", "version": "1.0",
         "export": {"format": "vrm1", "license": "CC-BY-4.0"},
         "budget": {"tier": "balanced"}})
    assert ok["translated"] is True
    assert ok["forge_partial"]["export"] == {
        "format": "vrm", "vrm_version": "1.0",
        "exporter": "io_scene_vrm", "license": "CC-BY-4.0"}
    assert ok["forge_partial"]["budget"]["max_triangles"] == 50000
    assert "job_id" in ok["missing_forge_fields_named"]
    blend = sf.translate_hamr_to_forge({"export": {"format": "blend"}})
    assert blend["translated"] is False and blend["failure"] == "hamr_incompatibility"
    assert blend["incompatibilities"][0]["field"] == "export.format"
    physics = sf.translate_hamr_to_forge(
        {"export": {"format": "glb"}, "physics": {"hair": True}})
    assert physics["translated"] is False
    assert any(e["field"] == "physics" for e in physics["incompatibilities"])
    bad_tier = sf.translate_hamr_to_forge(
        {"export": {"format": "glb"}, "budget": {"tier": "ultra"}})
    assert bad_tier["translated"] is False
    assert any(e["field"] == "budget.tier" for e in bad_tier["incompatibilities"])
    root = tmp_path / "approved"
    back = sf.translate_forge_to_hamr(_spec(root))
    assert back["translated"] is True
    assert back["hamr_partial"]["export"]["format"] == "vrm1"
    assert back["hamr_partial"]["budget"]["tier"] == "balanced"
    off_tier = _spec(root)
    off_tier["budget"] = dict(off_tier["budget"], max_triangles=49999)
    refused = sf.translate_forge_to_hamr(off_tier)
    assert refused["translated"] is False
    assert any(e["field"] == "budget" for e in refused["incompatibilities"])


def test_privacy_refusals(mods, tmp_path):
    sf = mods["smidja_forge"]
    root = tmp_path / "approved"
    private_assets = [{"asset_id": "private/ref", "provenance": "operator upload",
                       "license": "CC0-1.0", "private": True,
                       "path": str(root / "assets" / "ref.png")}]
    for destination in ("public_readme", "training", "telemetry", "publication"):
        refused = sf.plan_build(
            {"spec": _spec(root, assets=private_assets), "destination": destination},
            approved_roots=[str(root)], host="test-host")
        assert refused["failure"] == "private_asset_egress_refused", destination
        assert refused["destination"] == destination, destination
    public_assets = _spec(root)["assets"]
    egress = sf.plan_build(
        {"spec": _spec(root, assets=public_assets), "destination": "training"},
        approved_roots=[str(root)], host="test-host")
    assert egress["failure"] == "artifact_egress_refused"
    unknown_dest = _plan(mods, tmp_path, destination="moon")
    assert unknown_dest["failure"] == "destination_unknown"


def test_presentation_routing_refuses_control(mods):
    sf = mods["smidja_forge"]
    record = {"artifact_id": "out/a", "format": "vrm"}
    routed = sf.route_presentation(record, {"client": "vrm_viewer", "muted": True})
    assert routed["routed"] is True and routed["consumer_mode"] == "presentation_only"
    assert routed["secret_access"] is False and routed["cognitive_control"] is False
    for field in ("secrets", "credentials", "cognitive_control", "gui_control"):
        refused = sf.route_presentation(record, {field: True})
        assert refused["routed"] is False, field
        assert refused["failure"] == "presentation_payload_refused_by_name", field
        assert refused["refused_field"] == field, field


def test_offline_no_egress_everywhere(mods, tmp_path):
    sf = mods["smidja_forge"]
    assert sf.smidja_forge_status(FakeCtx())["sends_anything_external"] is False
    assert sf.forge_catalog()["sends_anything_external"] is False
    plan = _plan(mods, tmp_path)
    assert plan["sends_anything_external"] is False and plan["runs_engine"] is False


def _run_cli(mods, argv, ctx):
    cli = mods["cli"]
    parser = argparse.ArgumentParser(prog="hermes")
    sub = parser.add_subparsers(dest="command")
    volmarr_parser = sub.add_parser("volmarr")
    cli.register_cli(volmarr_parser)
    args = parser.parse_args(argv)
    return cli.health_command(args, ctx=ctx)


def test_cli_smidja_forge_family(mods, capsys):
    ctx = FakeCtx()
    assert _run_cli(mods, ["volmarr", "smidja-forge", "status", "--json"], ctx) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["tree"]["status"] == "not_configured"
    assert out["license_conflict"] == CONFLICT
    assert out["production_ready"] is False
    assert _run_cli(mods, ["volmarr", "smidja-forge", "catalog", "--json"], ctx) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["forge_spec_schema"]["version"] == "runeforge.smidja.forge.v1"
    matrix = {r["capability"]: r["live"] for r in out["capability_matrix"]}
    assert matrix["blender_build"] is False and matrix["live_remote_control"] is False
    assert _run_cli(mods, ["volmarr", "smidja-forge", "plan", "--json"], ctx) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["outcome"] == "plan" and out["dry_run"] is True
    assert out["executes_operations"] is False
    assert "synthetic" in out["source_label"]
    assert _run_cli(mods, ["volmarr", "smidja-forge"], ctx) == 2
    capsys.readouterr()
