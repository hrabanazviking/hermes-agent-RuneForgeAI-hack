"""X.14 Mythic Agent Coder CLI contracts (roadmap section 49).

These contracts pin the section 49 test gates on the Mythic
Engineering workflow connector: unconfigured truthfulness,
configured measurement of a staged tree's structure only, the
versioned workflow schema catalog (six roles, one writing
role, honest GitHub/Samverk/platform findings), the
one-leased-writer invariant, per-operation permission gates
with refusals by name, private repo denial, profile isolation
(approved context subset only), read-only plan shaping,
malformed build output, failed push recovery log shape,
independent verification of generated patches, and outcome
metrics that never inflate claimed done into true acceptance.
No Mythic code is run by any contract.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path

import pytest

HEAD = "e991a526c412c3668016809be66dbf50148128c3"
LICENSE_SHA = "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"


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
               for name in ("mythic_coder", "cli")}
    finally:
        manager.unload()
    return out


class FakeCtx:
    def __init__(self, cfg=None):
        self._cfg = cfg or {}

    def get_config(self, key, default=None):
        return self._cfg.get(key, default)


def _fake_tree(tmp_path: Path) -> Path:
    root = tmp_path / "mythic"
    (root / ".git" / "refs" / "heads").mkdir(parents=True)
    (root / ".git" / "HEAD").write_text(
        "ref: refs/heads/development\n", encoding="utf-8")
    (root / ".git" / "refs" / "heads" / "development").write_text(
        HEAD + "\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "mythic-agent"\n', encoding="utf-8")
    (root / "LICENSE").write_bytes(b"fake license text for structure only")
    pkg = root / "mythic_agent"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__version__.py").write_text(
        '__version__ = "0.1.0"\n', encoding="utf-8")
    (pkg / "cli.py").write_text("", encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_fake.py").write_text("", encoding="utf-8")
    return root


def _research_request(**overrides):
    request = {
        "operation": "repo_research",
        "repo": {"name": "hrabanazviking/Mythic_Agent_Coder_CLI",
                 "visibility": "public"},
        "steps": ["orient", "architect"],
        "context": {"persona_role": "cartographer"},
    }
    request.update(overrides)
    return request


def test_status_unconfigured_is_truthful(mods):
    mc = mods["mythic_coder"]
    record = mc.mythic_status(FakeCtx(), recorded_at="t")
    assert record["schema"] == "runeforge.mythic.status.v1"
    assert record["canonical_repo"] == "hrabanazviking/Mythic_Agent_Coder_CLI"
    assert record["default_branch"] == "development"
    assert record["audited_head"] == HEAD == mc.AUDITED_HEAD
    assert record["package_name"] == "mythic-agent"
    assert record["package_version"] == "0.1.0"
    assert record["license"] == "Apache-2.0"
    assert record["enabled"] is False and record["configured"] is False
    assert record["tree"]["status"] == "not_configured"
    assert record["sends_anything_external"] is False
    assert record["runs_engine"] is False
    assert record["executes_operations"] is False
    assert record["production_ready"] is False


def test_status_configured_measures_tree_structure(mods, tmp_path):
    mc = mods["mythic_coder"]
    root = _fake_tree(tmp_path)
    ctx = FakeCtx({"mythic_enabled": True, "mythic_root": str(root)})
    record = mc.mythic_status(ctx, recorded_at="t")
    assert record["enabled"] is True and record["configured"] is True
    tree = record["tree"]
    assert tree["status"] == "measured"
    assert tree["head"] == HEAD and tree["head_matches_audited"] is True
    assert tree["package_name"] == "mythic-agent"
    assert tree["package_version"] == "0.1.0"
    assert tree["module_count"] == 4 and tree["package_module_count"] == 3
    assert tree["test_file_count"] == 1
    assert tree["license_sha256"] == hashlib.sha256(
        b"fake license text for structure only").hexdigest()
    assert tree["license_matches_audited"] is False
    assert mc.LICENSE_SHA256 == LICENSE_SHA


def test_catalog_workflow_schema_and_honest_findings(mods):
    mc = mods["mythic_coder"]
    catalog = mc.workflow_catalog()
    assert catalog["schema"] == "runeforge.mythic.catalog.v1"
    schema = catalog["workflow_schema"]
    assert schema["version"] == "runeforge.mythic.workflow.v1"
    roles = [row["role"] for row in schema["roles"]]
    assert roles == ["skald", "cartographer", "architect",
                     "forge_worker", "auditor", "scribe"]
    assert schema["writing_roles"] == ["forge_worker"]
    stages = [row["stage"] for row in schema["stages"]]
    assert stages == ["orient", "architect", "forge", "audit", "bank"]
    assert catalog["read_only_operations"] == [
        "repo_research", "architecture_mapping", "roadmap_construction",
        "test_discovery", "diff_proposal", "source_linked_review"]
    assert catalog["refused_operations"] == [
        "secrets_access", "credential_read", "private_companion_data_access",
        "private_author_data_access"]
    assert catalog["provider_registry"]["provider_count"] == 16
    assert catalog["provider_registry"]["credentials_read_by_connector"] is False
    assert catalog["github_integration"]["wired_into_cli_at_audited_head"] is False
    assert catalog["samverk_integration"]["live"] is False
    assert catalog["subagent_support"]["real"] is True
    assert catalog["checkout_lease"]["exists_in_audited_source"] is False
    assert catalog["checkout_lease"]["one_writer_invariant"] is True
    platforms = {row["platform"]: row["status"]
                 for row in catalog["platform_evaluation"]}
    assert platforms["arm64_linux"] == "unproven_upstream"
    assert platforms["termux"] == "no_path_in_source"
    assert platforms["windows"] == "not_equivalent_not_assumed"
    assert catalog["sends_anything_external"] is False
    assert catalog["executes_operations"] is False
    assert catalog["production_ready"] is False


def test_one_leased_writer_invariant(mods, tmp_path):
    mc = mods["mythic_coder"]
    store = tmp_path / "store"
    first = mc.acquire_lease(store, "repo-a", "team-01", heartbeat=100.0)
    assert first["acquired"] is True and first["owner"] == "team-01"
    second = mc.acquire_lease(store, "repo-a", "team-02", heartbeat=100.0)
    assert second["acquired"] is False
    assert second["reason"] == "duplicate_lease_refused"
    assert second["lease_owner"] == "team-01"
    other = mc.acquire_lease(store, "repo-b", "team-02", heartbeat=100.0)
    assert other["acquired"] is True
    refresh = mc.acquire_lease(store, "repo-a", "team-01", heartbeat=200.0)
    assert refresh["acquired"] is True
    held = mc.lease_status(store, "repo-a", now=250.0)
    assert held["status"] == "held" and held["owner"] == "team-01"
    stale = mc.lease_status(store, "repo-a", now=200.0 + 901.0)
    assert stale["status"] == "worker_lost"
    assert stale["recoverable_via_checkpoint"] is True
    wrong = mc.release_lease(store, "repo-a", "team-02")
    assert wrong["released"] is False and wrong["reason"] == "not_lease_owner"
    released = mc.release_lease(store, "repo-a", "team-01")
    assert released["released"] is True
    gone = mc.lease_status(store, "repo-a", now=300.0)
    assert gone["status"] == "unleased" and gone["owner"] is None
    missing = mc.acquire_lease(store, "", "team-01")
    assert missing["acquired"] is False and missing["reason"] == "checkout_missing"


def test_permission_gates_refuse_by_name(mods):
    mc = mods["mythic_coder"]
    no_lease = mc.gate_operation("checkout_write")
    assert no_lease["allowed"] is False and no_lease["reason"] == "lease_required"
    leased = mc.gate_operation("checkout_write", lease_owner="team-01")
    assert leased["allowed"] is True and leased["executed"] is False
    push_no_auth = mc.gate_operation("push", lease_owner="team-01")
    assert push_no_auth["allowed"] is False
    assert push_no_auth["reason"] == "operator_authorization_required"
    push_ok = mc.gate_operation("push", lease_owner="team-01",
                                operator_authorized=True)
    assert push_ok["allowed"] is True and push_ok["executed"] is False
    release_no_auth = mc.gate_operation("release")
    assert release_no_auth["reason"] == "operator_authorization_required"
    for op in ("secrets_access", "credential_read",
               "private_companion_data_access", "private_author_data_access"):
        refused = mc.gate_operation(op, lease_owner="team-01",
                                    operator_authorized=True)
        assert refused["allowed"] is False, op
        assert refused["reason"] == "operation_refused_by_name", op
        assert refused["executed"] is False, op
    unknown = mc.gate_operation("teleport")
    assert unknown["allowed"] is False and unknown["reason"] == "unknown_operation"


def test_plan_research_shapes_read_only_plan(mods):
    mc = mods["mythic_coder"]
    plan = mc.plan_research(_research_request())
    assert plan["schema"] == "runeforge.mythic.plan.v1"
    assert plan["outcome"] == "plan" and plan["accepted"] is True
    assert plan["workflow_schema"] == "runeforge.mythic.workflow.v1"
    assert len(plan["plan_key"]) == 64
    assert plan["read_only"] is True and plan["lease_required"] is False
    assert [s["stage"] for s in plan["steps"]] == ["orient", "architect"]
    assert all(s["write"] is False for s in plan["steps"])
    assert plan["context_keys"] == ["persona_role"]
    assert plan["context_subset_only"] is True
    assert plan["source_revision"] == HEAD
    assert plan["executes_operations"] is False
    again = mc.plan_research(_research_request())
    assert again["plan_key"] == plan["plan_key"]
    assert plan["latency_ms"] < mc.PERFORMANCE_BUDGET_MS == 250


def test_plan_private_repo_denied_and_profile_isolation(mods):
    mc = mods["mythic_coder"]
    denied = mc.plan_research(_research_request(
        repo={"name": "volmarr/private-notes", "visibility": "private"}))
    assert denied["outcome"] == "failure"
    assert denied["failure"] == "private_repo_denied"
    assert denied["fail_closed"] is True
    allowed = mc.plan_research(_research_request(
        repo={"name": "volmarr/private-notes", "visibility": "private"},
        operator_authorized=True))
    assert allowed["outcome"] == "plan" and allowed["visibility"] == "private"
    for key in ("companion_data", "author_data", "private_memory", "credentials"):
        refused = mc.plan_research(_research_request(context={key: "x"}))
        assert refused["failure"] == "private_context_refused", key
        assert refused["context_key"] == key, key
    unapproved = mc.plan_research(_research_request(context={"diary": "x"}))
    assert unapproved["failure"] == "context_key_not_approved"


def test_plan_write_and_unknown_operations_gated(mods):
    mc = mods["mythic_coder"]
    write = mc.plan_research(_research_request(operation="push"))
    assert write["failure"] == "operation_requires_gate"
    assert write["gate"]["reason"] == "lease_required"
    refused = mc.plan_research(_research_request(operation="secrets_access"))
    assert refused["failure"] == "operation_refused_by_name"
    unknown = mc.plan_research(_research_request(operation="teleport"))
    assert unknown["failure"] == "unknown_operation"
    write_stage = mc.plan_research(_research_request(steps=["orient", "forge"]))
    assert write_stage["failure"] == "write_stage_in_read_only_plan"
    bad_stage = mc.plan_research(_research_request(steps=["dance"]))
    assert bad_stage["failure"] == "unknown_stage"
    no_repo = mc.plan_research({"operation": "repo_research"})
    assert no_repo["failure"] == "repo_missing"
    not_mapping = mc.plan_research("nope")
    assert not_mapping["failure"] == "request_not_mapping"


GOOD_DIFF = (
    "diff --git a/src/app.py b/src/app.py\n"
    "--- a/src/app.py\n"
    "+++ b/src/app.py\n"
    "@@ -1,2 +1,2 @@\n"
    "-old line\n"
    "+new line\n")


def test_verify_patch_independent_of_claims(mods):
    mc = mods["mythic_coder"]
    verified = mc.verify_patch(GOOD_DIFF, [{"kind": "runner_output"}])
    assert verified["verified"] is True and verified["independent"] is True
    assert verified["files"] == ["src/app.py"] and verified["hunks"] == 1
    assert verified["held_evidence"] == ["runner_output"]
    claim_only = mc.verify_patch(GOOD_DIFF, [{"kind": "summary"},
                                             {"kind": "assertion"}])
    assert claim_only["verified"] is False
    assert claim_only["failure"] == "unverified_claim"
    assert claim_only["bare_claims"] == ["summary", "assertion"]
    no_evidence = mc.verify_patch(GOOD_DIFF, [])
    assert no_evidence["failure"] == "no_evidence"
    unknown_kind = mc.verify_patch(GOOD_DIFF, [{"kind": "vibes"}])
    assert unknown_kind["failure"] == "unknown_evidence_kind"
    malformed = mc.verify_patch("this is not a diff at all",
                                [{"kind": "runner_output"}])
    assert malformed["verified"] is False
    assert malformed["failure"] == "malformed_diff"
    empty = mc.verify_patch("", [{"kind": "runner_output"}])
    assert empty["failure"] == "malformed_diff"


def test_parse_build_output_malformed_fails_closed(mods):
    mc = mods["mythic_coder"]
    good = mc.parse_build_output(
        "src/app.py:10:5: error: name 'x' is not defined\n"
        "src/app.py:12:1: warning: unused import\n")
    assert good["parsed"] is True and good["finding_count"] == 2
    assert good["error_count"] == 1
    assert good["findings"][0]["line"] == 10
    bad = mc.parse_build_output("src/app.py:10:5: error: boom\ngarbage line\n")
    assert bad["parsed"] is False and bad["failure"] == "malformed_build_output"
    assert bad["offending_line"] == "garbage line"
    empty = mc.parse_build_output("")
    assert empty["parsed"] is False and empty["failure"] == "malformed_build_output"


def test_failed_push_recovery_log_shape(mods):
    mc = mods["mythic_coder"]
    record = mc.recovery_record({
        "operation": "push", "failure": "non-fast-forward",
        "branch_strategy": "team_branch",
        "recovery_action": "retry_after_fetch", "resolved": True,
        "repo": "hrabanazviking/hermes-agent-RuneForgeAI-hack",
        "pr_receipt": "PR #13 (labelled synthetic receipt)"})
    assert record["recorded"] is True and len(record["record_key"]) == 64
    assert record["resolved"] is True and record["executes_operations"] is False
    wrong_op = mc.recovery_record({
        "operation": "commit", "failure": "x",
        "branch_strategy": "team_branch",
        "recovery_action": "retry_after_fetch", "resolved": True})
    assert wrong_op["failure"] == "recovery_operation_not_push"
    bad_action = mc.recovery_record({
        "operation": "push", "failure": "x",
        "branch_strategy": "team_branch",
        "recovery_action": "force_push", "resolved": True})
    assert bad_action["failure"] == "unknown_recovery_action"
    bad_strategy = mc.recovery_record({
        "operation": "push", "failure": "x", "branch_strategy": "main_direct",
        "recovery_action": "retry_after_fetch", "resolved": True})
    assert bad_strategy["failure"] == "unknown_branch_strategy"
    no_outcome = mc.recovery_record({
        "operation": "push", "failure": "x",
        "branch_strategy": "team_branch",
        "recovery_action": "abort_and_report"})
    assert no_outcome["failure"] == "recovery_outcome_missing"
    not_mapping = mc.recovery_record("nope")
    assert not_mapping["failure"] == "malformed_recovery_record"


def test_outcome_metrics_never_inflate_done(mods):
    mc = mods["mythic_coder"]
    empty = mc.outcome_metrics([])
    assert empty["computed"] is False and empty["reason"] == "no_records"
    assert "patch_test_pass_rate" not in empty
    metrics = mc.outcome_metrics([
        {"tests_passed": 10, "tests_total": 10, "review_findings": 4,
         "review_resolved": 4, "clean_diff": True, "recovered": True,
         "claimed_done": True, "independently_verified": True,
         "synthetic": True},
        {"tests_passed": 3, "tests_total": 4, "review_findings": 2,
         "review_resolved": 1, "clean_diff": False, "recovered": False,
         "claimed_done": True, "independently_verified": False,
         "synthetic": True}])
    assert metrics["computed"] is True
    assert metrics["metrics_version"] == "runeforge.mythic.outcomes.v1"
    assert metrics["patch_test_pass_rate"] == pytest.approx(13 / 14)
    assert metrics["review_resolution_rate"] == pytest.approx(5 / 6)
    assert metrics["clean_diff_rate"] == pytest.approx(0.5)
    assert metrics["recovered_sessions"] == 1
    assert metrics["claimed_done"] == 2 and metrics["truly_accepted"] == 1
    assert metrics["inflated_done"] == 1
    assert metrics["true_acceptance_rate"] == pytest.approx(0.5)
    assert metrics["source_label"] == "synthetic fixtures (labelled)"
    assert metrics["claims_production_outcomes"] is False
    malformed = mc.outcome_metrics([
        {"tests_passed": 5, "tests_total": 4, "review_findings": 0,
         "review_resolved": 0}])
    assert malformed["computed"] is False
    assert malformed["reason"] == "malformed_record"


def test_offline_no_egress_everywhere(mods, tmp_path):
    mc = mods["mythic_coder"]
    assert mc.mythic_status(FakeCtx())["sends_anything_external"] is False
    assert mc.workflow_catalog()["sends_anything_external"] is False
    plan = mc.plan_research(_research_request())
    assert plan["sends_anything_external"] is False
    assert plan["runs_engine"] is False
    gate = mc.gate_operation("push", lease_owner="t",
                             operator_authorized=True)
    assert gate["sends_anything_external"] is False and gate["executed"] is False
    lease = mc.acquire_lease(tmp_path / "s", "repo", "team-01")
    assert lease["sends_anything_external"] is False
    verified = mc.verify_patch(GOOD_DIFF, [{"kind": "runner_output"}])
    assert verified["sends_anything_external"] is False


def _run_cli(mods, argv, ctx):
    cli = mods["cli"]
    parser = argparse.ArgumentParser(prog="hermes")
    sub = parser.add_subparsers(dest="command")
    volmarr_parser = sub.add_parser("volmarr")
    cli.register_cli(volmarr_parser)
    args = parser.parse_args(argv)
    return cli.health_command(args, ctx=ctx)


def test_cli_mythic_family(mods, capsys):
    ctx = FakeCtx()
    assert _run_cli(mods, ["volmarr", "mythic", "status", "--json"], ctx) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["tree"]["status"] == "not_configured"
    assert out["production_ready"] is False
    assert _run_cli(mods, ["volmarr", "mythic", "catalog", "--json"], ctx) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["workflow_schema"]["version"] == "runeforge.mythic.workflow.v1"
    assert out["checkout_lease"]["exists_in_audited_source"] is False
    assert _run_cli(mods, ["volmarr", "mythic", "plan", "--json"], ctx) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["outcome"] == "plan" and out["operation"] == "architecture_mapping"
    assert out["read_only"] is True and out["executes_operations"] is False
    assert "synthetic" in out["source_label"]
    assert _run_cli(mods, ["volmarr", "mythic"], ctx) == 2
    capsys.readouterr()
