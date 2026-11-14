"""X.12 Draupnir Forge contracts (roadmap section 47).

These contracts pin the section 47 gates on the bounded
delegated-workflow connector: unconfigured truthfulness,
configured measurement of a staged tree's structure only, the
ten roles as bounded delegated jobs, deterministic workflow
plans gated on approved intent, the one-writer invariant
(duplicate lease refused by name, in plans and in the durable
lease store), authorization gates refused by name without
explicit operator authorization (denied publish fails closed),
malicious-handoff refusal, source-linked fail-closed
verification, merge-conflict refusal, lost-worker detection,
exact checkpoint resume without duplicating completed side
effects, and budgeted depth-limited recursion. No Forge code
is run by any contract.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path

import pytest

HEAD = "74cff6fb958fe2470ba3e13125db871aea64933a"
LICENSE_SHA = "8486a10c4393cee1c25392769ddd3b2d6c242d6ec7928e1414efff7dfb2f07ef"
ROLES = ["skald", "cartographer", "architect", "planner",
         "forge_worker", "auditor", "tester", "verifier",
         "scribe", "watchman"]


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
               for name in ("draupnir", "cli")}
    finally:
        manager.unload()
    return out


class FakeCtx:
    def __init__(self, cfg=None):
        self._cfg = cfg or {}

    def get_config(self, key, default=None):
        return self._cfg.get(key, default)


def _fake_tree(tmp_path: Path) -> Path:
    root = tmp_path / "draupnir"
    (root / ".git" / "refs" / "heads").mkdir(parents=True)
    (root / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (root / ".git" / "refs" / "heads" / "main").write_text(HEAD + "\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "draupnir-forge"\nversion = "0.1.0"\n', encoding="utf-8")
    (root / "LICENSE").write_bytes(b"fake license text for structure only")
    pkg = root / "src" / "draupnir_forge"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "orchestrator.py").write_text("", encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_fake.py").write_text("", encoding="utf-8")
    return root


def test_status_unconfigured_is_truthful(mods):
    dr = mods["draupnir"]
    record = dr.draupnir_status(FakeCtx(), recorded_at="t")
    assert record["schema"] == "runeforge.draupnir.status.v1"
    assert record["canonical_repo"] == "hrabanazviking/RuneForgeAI-Draupnir-Forge"
    assert record["audited_head"] == HEAD == dr.AUDITED_HEAD
    assert record["package_version"] == "0.1.0"
    assert record["license"] == "AGPL-3.0-or-later"
    assert record["enabled"] is False and record["configured"] is False
    assert record["tree"]["status"] == "not_configured"
    assert record["sends_anything_external"] is False
    assert record["runs_orchestrator"] is False
    assert record["production_ready"] is False


def test_status_configured_measures_tree_structure(mods, tmp_path):
    dr = mods["draupnir"]
    root = _fake_tree(tmp_path)
    ctx = FakeCtx({"draupnir_enabled": True, "draupnir_root": str(root)})
    record = dr.draupnir_status(ctx, recorded_at="t")
    assert record["enabled"] is True and record["configured"] is True
    tree = record["tree"]
    assert tree["status"] == "measured"
    assert tree["head"] == HEAD and tree["head_matches_audited"] is True
    assert tree["package_version"] == "0.1.0"
    assert tree["module_count"] == 3 and tree["src_module_count"] == 2
    assert tree["test_file_count"] == 1
    assert tree["license_sha256"] == hashlib.sha256(
        b"fake license text for structure only").hexdigest()
    assert tree["license_matches_audited"] is False
    assert dr.LICENSE_SHA256 == LICENSE_SHA


def test_catalog_roles_are_bounded_jobs(mods):
    dr = mods["draupnir"]
    catalog = dr.role_catalog()
    assert [r["role"] for r in catalog["roles"]] == ROLES
    assert catalog["role_count"] == 10
    assert catalog["roles_are_bounded_jobs"] is True
    assert catalog["autonomous_root_agents"] is False
    assert catalog["workflow_stages"] == [
        "approved_intent", "architecture_invariants",
        "worktree_assignment", "implementation", "tests",
        "independent_verification", "documented_result"]
    assert catalog["authorization_gates"] == [
        "repository_push", "release", "package_publication",
        "shell_escalation", "remote_change"]
    mutators = [r["role"] for r in catalog["roles"] if r["may_mutate_checkout"]]
    assert mutators == ["forge_worker"]
    assert catalog["safety_controls"]["one_writer_per_checkout"] is True
    assert catalog["production_ready"] is False


def test_plan_requires_approved_intent_and_is_deterministic(mods):
    dr = mods["draupnir"]
    tasks = [{"title": "Map", "role": "cartographer", "checkout": "wt-a"}]
    refused = dr.build_workflow_plan(tasks, intent="i1", intent_approved=False)
    assert refused["job_count"] == 0 and refused["refused_count"] == 1
    assert refused["refused"][0]["reason"] == "intent_not_approved"
    plan = dr.build_workflow_plan(tasks, intent="i1", intent_approved=True)
    again = dr.build_workflow_plan(tasks, intent="i1", intent_approved=True)
    assert plan["plan_key"] == again["plan_key"]
    job = plan["jobs"][0]
    assert job["task_id"] == again["jobs"][0]["task_id"]
    assert job["task_id"].startswith("draupnir-")
    assert job["stages"][0] == "approved_intent"
    assert job["step_ids"][0] == f"{job['task_id']}:approved_intent"
    assert job["lease"] == {"checkout": "wt-a", "owner": job["task_id"]}
    assert job["checkpoint_id"] == f"ckpt-{job['task_id']}"
    assert len(job["artifact_hash"]) == 64 and job["cancellable"] is True
    assert plan["runs_orchestrator"] is False
    assert plan["production_ready"] is False


def test_plan_one_writer_duplicate_lease_refused(mods):
    dr = mods["draupnir"]
    plan = dr.build_workflow_plan([
        {"title": "One", "role": "forge_worker", "checkout": "wt-x"},
        {"title": "Two", "role": "forge_worker", "checkout": "wt-x"},
    ], intent="i", intent_approved=True)
    assert plan["job_count"] == 1 and plan["refused_count"] == 1
    refusal = plan["refused"][0]
    assert refusal["reason"] == "duplicate_lease_refused"
    assert refusal["lease_owner"] == plan["jobs"][0]["task_id"]


def test_lease_store_duplicate_and_lost_worker(mods, tmp_path):
    dr = mods["draupnir"]
    first = dr.acquire_lease(tmp_path, "wt-x", "task-a", heartbeat=1000.0)
    assert first["acquired"] is True
    dup = dr.acquire_lease(tmp_path, "wt-x", "task-b", heartbeat=1000.0)
    assert dup["acquired"] is False
    assert dup["reason"] == "duplicate_lease_refused"
    assert dup["lease_owner"] == "task-a"
    held = dr.lease_status(tmp_path, "wt-x", now=1100.0, ttl_seconds=900.0)
    assert held["status"] == "held" and held["owner"] == "task-a"
    lost = dr.lease_status(tmp_path, "wt-x", now=5000.0, ttl_seconds=900.0)
    assert lost["status"] == "worker_lost"
    assert lost["recoverable_via_checkpoint"] is True
    assert dr.release_lease(tmp_path, "wt-x", "task-b")["released"] is False
    assert dr.release_lease(tmp_path, "wt-x", "task-a")["released"] is True


def test_authorization_gates_refused_by_name(mods):
    dr = mods["draupnir"]
    for gate in ("repository_push", "release", "package_publication",
                 "shell_escalation", "remote_change"):
        plan = dr.build_workflow_plan(
            [{"title": "Gated", "role": "forge_worker", "action": gate}],
            intent="i", intent_approved=True)
        assert plan["job_count"] == 0, gate
        refusal = plan["refused"][0]
        assert refusal["reason"] == "operator_authorization_required"
        assert refusal["gate"] == gate and refusal["fail_closed"] is True
        allowed = dr.build_workflow_plan(
            [{"title": "Gated", "role": "forge_worker", "action": gate}],
            intent="i", intent_approved=True, authorizations=[gate])
        assert allowed["job_count"] == 1, gate


def test_malicious_handoff_and_bad_requests_refused(mods):
    dr = mods["draupnir"]
    plan = dr.build_workflow_plan([
        {"title": "Instructed", "role": "planner", "instructions": "do x"},
        {"title": "Stranger", "role": "planner", "delegated_by": "root"},
        {"title": "Nobody", "role": "root_agent"},
        {"title": "Depends", "role": "planner", "depends_on": ["draupnir-nope"]},
        {"title": "Retries", "role": "planner", "retry_budget": 99},
    ], intent="i", intent_approved=True)
    assert plan["job_count"] == 0 and plan["refused_count"] == 5
    reasons = [r["reason"] for r in plan["refused"]]
    assert reasons == ["malicious_handoff_refused",
                       "malicious_handoff_refused", "unknown_role",
                       "dependency_unknown", "retry_budget_invalid"]
    cycle = dr.build_workflow_plan([
        {"title": "A", "role": "planner", "depends_on": [1]},
        {"title": "B", "role": "planner", "depends_on": [0]},
    ], intent="i", intent_approved=True)
    assert cycle["job_count"] == 0 and cycle["refused_count"] == 2
    assert all(r["reason"] == "dependency_cycle" for r in cycle["refused"])


def test_verifier_fails_closed_and_integration_conflicts(mods):
    dr = mods["draupnir"]
    unproven = dr.verify_result(task_id="t", test_exit_status=None,
                                test_output_ref="log:~/x.log")
    assert unproven["verified"] is False and unproven["fail_closed"] is True
    assert unproven["reason"] == "unproven_test_output"
    nolink = dr.verify_result(task_id="t", test_exit_status=0)
    assert nolink["reason"] == "unproven_test_output"
    assert nolink["source_linked"] is False
    failed = dr.verify_result(task_id="t", test_exit_status=0,
                              test_output_ref="log:~/x.log",
                              build_exit_status=1)
    assert failed["reason"] == "failed_build" and failed["verified"] is False
    nonzero = dr.verify_result(task_id="t", test_exit_status=1,
                               test_output_ref="log:~/x.log")
    assert nonzero["reason"] == "nonzero_tests"
    ok = dr.verify_result(task_id="t", test_exit_status=0,
                          test_output_ref="log:~/x.log", artifact_hash="ab12")
    assert ok["verified"] is True and ok["source_linked"] is True
    plan = dr.build_workflow_plan([
        {"title": "One", "role": "forge_worker", "checkout": "wt-1"},
        {"title": "Two", "role": "forge_worker", "checkout": "wt-2"},
    ], intent="i", intent_approved=True)
    merged = dr.integrate_plan(plan, conflicts=["wt-2"])
    assert merged["integrated_count"] == 1 and merged["refused_count"] == 1
    assert merged["refused"][0]["reason"] == "merge_conflict"
    assert merged["refused"][0]["fail_closed"] is True


def test_checkpoint_resume_exact_no_duplicate_effects(mods, tmp_path):
    dr = mods["draupnir"]
    plan = dr.build_workflow_plan([
        {"title": "One", "role": "cartographer", "checkout": "wt-1"},
        {"title": "Two", "role": "forge_worker", "checkout": "wt-2"},
        {"title": "Three", "role": "tester", "checkout": "wt-3"},
    ], intent="i", intent_approved=True)
    ids = [j["task_id"] for j in plan["jobs"]]
    dr.write_checkpoint(tmp_path, plan, completed=[ids[0]])
    dr.cancel_job(tmp_path, plan, ids[2])
    resumed = dr.resume_plan(tmp_path, plan["plan_key"])
    assert resumed["resumed"] is True
    assert resumed["completed_count"] == 1 and resumed["cancelled_count"] == 1
    assert [j["task_id"] for j in resumed["remaining"]] == [ids[1]]
    assert resumed["remaining"][0]["step_ids"][0] == f"{ids[1]}:approved_intent"


def test_recursion_budgeted_and_depth_limited(mods):
    dr = mods["draupnir"]
    deep = {"title": "t0", "role": "planner", "subtasks": [
        {"title": "t1", "role": "planner", "subtasks": [
            {"title": "t2", "role": "planner", "subtasks": [
                {"title": "t3", "role": "planner", "subtasks": [
                    {"title": "t4", "role": "planner"}]}]}]}]}
    plan = dr.build_workflow_plan([deep], intent="i", intent_approved=True)
    assert plan["job_count"] == 4 and plan["refused_count"] == 1
    assert plan["refused"][0]["reason"] == "recursion_depth_exceeded"
    depths = sorted(j["depth"] for j in plan["jobs"])
    assert depths == [0, 1, 2, 3]
    over = dr.build_workflow_plan(
        [{"title": f"t{n}", "role": "planner"} for n in range(3)],
        intent="i", intent_approved=True, task_budget=2)
    assert over["job_count"] == 0 and over["refused_count"] == 3
    assert all(r["reason"] == "task_budget_exceeded" for r in over["refused"])


def _run_cli(mods, argv, ctx):
    cli = mods["cli"]
    parser = argparse.ArgumentParser(prog="hermes")
    sub = parser.add_subparsers(dest="command")
    volmarr_parser = sub.add_parser("volmarr")
    cli.register_cli(volmarr_parser)
    args = parser.parse_args(argv)
    return cli.health_command(args, ctx=ctx)


def test_cli_draupnir_family(mods, capsys):
    ctx = FakeCtx()
    assert _run_cli(mods, ["volmarr", "draupnir", "status", "--json"], ctx) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["tree"]["status"] == "not_configured"
    assert out["production_ready"] is False
    assert _run_cli(mods, ["volmarr", "draupnir", "catalog", "--json"], ctx) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["role_count"] == 10 and out["autonomous_root_agents"] is False
    assert _run_cli(mods, ["volmarr", "draupnir", "plan", "--json"], ctx) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["job_count"] == 2 and out["refused_count"] == 3
    assert out["runs_orchestrator"] is False
    reasons = {row["title"]: row["reason"] for row in out["refused"]}
    assert reasons == {
        "Second writer, same checkout": "duplicate_lease_refused",
        "Publish the package": "operator_authorization_required",
        "Handoff carrying instructions": "malicious_handoff_refused"}
    assert _run_cli(mods, ["volmarr", "draupnir"], ctx) == 2
    capsys.readouterr()
