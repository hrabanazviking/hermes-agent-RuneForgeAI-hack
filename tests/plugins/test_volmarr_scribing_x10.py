"""X.10 Mythic Scribing Foundry contracts (roadmap section 45).

These contracts pin the section 45 gates on the private
writing-workflow connector: unconfigured truthfulness, configured
measurement of a staged tree's structure only (private-source
egress denial: manuscript content in the tree never appears in
any record), author_work/persona_core namespace separation (a
manuscript is never a persona instruction), citation fabrication
refusal, unsupported step kinds reported honestly (the Foundry's
verify/revise CLIs are stubs at the audited HEAD), publish verbs
refused by name, chapter-checkpoint resume after interruption,
and editorial rollback of an accepted suggestion.
"""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

import pytest

HEAD = "9da00e5ba77c39a43c670e9e2f7398dbeaa4c594"
CANARY = "PRIVATE-CANARY-MANUSCRIPT-TEXT-7f3a"


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
               for name in ("scribing", "cli")}
    finally:
        manager.unload()
    return out


class FakeCtx:
    def __init__(self, cfg=None):
        self._cfg = cfg or {}

    def get_config(self, key, default=None):
        return self._cfg.get(key, default)


def _fake_tree(tmp_path: Path) -> Path:
    root = tmp_path / "foundry"
    (root / ".git" / "refs" / "heads").mkdir(parents=True)
    (root / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (root / ".git" / "refs" / "heads" / "main").write_text(HEAD + "\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "mythscribe"\nversion = "0.1.0"\n', encoding="utf-8")
    pkg = root / "mythscribe"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "cli.py").write_text("", encoding="utf-8")
    (root / "manuscript.md").write_text(CANARY, encoding="utf-8")
    return root


def test_status_unconfigured_is_truthful(mods):
    sc = mods["scribing"]
    record = sc.scribing_status(FakeCtx(), recorded_at="t")
    assert record["schema"] == "runeforge.scribing.status.v1"
    assert record["canonical_repo"] == "hrabanazviking/Mythic-Scribing-Foundry"
    assert record["audited_head"] == HEAD == sc.AUDITED_HEAD
    assert record["package_version"] == "0.1.0"
    assert record["license"] == "Proprietary"
    assert record["enabled"] is False
    assert record["configured"] is False
    assert record["tree"]["status"] == "not_configured"
    assert record["publishes_anything"] is False
    assert record["production_ready"] is False


def test_status_configured_measures_tree_and_denies_egress(mods, tmp_path):
    sc = mods["scribing"]
    root = _fake_tree(tmp_path)
    ctx = FakeCtx({"scribing_enabled": True, "scribing_root": str(root)})
    record = sc.scribing_status(ctx, recorded_at="t")
    assert record["enabled"] is True and record["configured"] is True
    tree = record["tree"]
    assert tree["status"] == "measured"
    assert tree["head"] == HEAD and tree["head_matches_audited"] is True
    assert tree["package_version"] == "0.1.0"
    assert tree["module_count"] == 2
    # Egress-denial canary: private manuscript content staged in
    # the tree never appears in status, catalog or plan output.
    blob = json.dumps(record) + json.dumps(sc.steps_catalog())
    blob += json.dumps(sc.build_job_plan(sc.SYNTHETIC_STEPS))
    assert CANARY not in blob


def test_namespace_separation_manuscript_never_persona(mods):
    sc = mods["scribing"]
    forced = sc.assign_namespace("manuscript", "persona_core")
    assert forced["namespace"] == "author_work"
    assert forced["refused"] == "manuscript_not_persona_instruction"
    assert forced["persona_instruction"] is False
    default = sc.assign_namespace("chapter")
    assert default["namespace"] == "author_work" and default["refused"] is None
    unknown = sc.assign_namespace("note", "bogus")
    assert unknown["refused"] == "unknown_namespace"


def test_citation_fabrication_refused(mods):
    sc = mods["scribing"]
    source = "The author wrote this exact sentence in the source."
    ok = sc.verify_citation(source, "this exact sentence", source_id="s1")
    assert ok["supported"] is True and ok["unsupported_reasons"] == []
    fabricated = sc.verify_citation(source, "a sentence never written", source_id="s1")
    assert fabricated["supported"] is False
    assert fabricated["unsupported_reasons"] == ["quote_not_in_source"]
    too_long = sc.verify_citation(source, "x" * (sc.QUOTE_MAX_CHARS + 1))
    assert too_long["supported"] is False
    assert too_long["unsupported_reasons"] == ["quote_exceeds_policy"]
    empty = sc.verify_citation(source, "")
    assert empty["unsupported_reasons"] == ["no_quote"]


def test_catalog_and_plan_report_unsupported_and_refuse_publish(mods):
    sc = mods["scribing"]
    catalog = sc.steps_catalog()
    by_kind = {row["kind"]: row for row in catalog["steps"]}
    assert by_kind["claim_verification"]["supported"] is False
    assert by_kind["revision"]["supported"] is False
    assert by_kind["drafting"]["supported"] is True
    assert by_kind["publication_preparation"]["supported"] is True
    assert catalog["publishes_anything"] is False
    plan = sc.build_job_plan([
        {"kind": "drafting", "chapter": 2},
        {"kind": "claim_verification", "chapter": 2},
        {"kind": "publish", "chapter": 2},
        {"kind": "bogus", "chapter": 2},
    ], book_ref="b1", created_by="tester")
    assert plan["step_count"] == 1 and plan["refused_count"] == 3
    reasons = {row["kind"]: row["reason"] for row in plan["refused"]}
    assert reasons == {"claim_verification": "step_unsupported",
                       "publish": "publish_refused", "bogus": "unknown_step"}
    step = plan["steps"][0]
    assert step["namespace"] == "author_work" and step["persona_instruction"] is False
    assert step["checkpoint"] == "chapter-2"
    assert step["cost_receipt_required"] is True
    assert step["provenance"]["audited_head"] == HEAD
    again = sc.build_job_plan([{"kind": "drafting", "chapter": 2}], book_ref="b1")
    receipt = sc.cost_receipt(plan_key=plan["plan_key"], provider="local",
                              model="m", tokens_in=1000, tokens_out=500)
    assert receipt["local_only"] is True and receipt["plan_key"] == plan["plan_key"]


def test_checkpoint_resume_after_interruption(mods, tmp_path):
    sc = mods["scribing"]
    plan = sc.build_job_plan([
        {"kind": "research_indexing", "chapter": 1},
        {"kind": "outlining", "chapter": 1},
        {"kind": "drafting", "chapter": 2},
    ])
    sc.write_checkpoint(tmp_path, plan, completed=[0])
    resumed = sc.resume_plan(tmp_path, plan["plan_key"])
    assert resumed["resumed"] is True and resumed["completed_count"] == 1
    assert [s["kind"] for s in resumed["remaining"]] == ["outlining", "drafting"]


def test_suggestion_separate_until_accepted_and_rollback(mods, tmp_path):
    sc = mods["scribing"]
    suggestion = {"target": "chapter-1", "previous_text": "original",
                  "proposed_text": "revised"}
    drafted = sc.draft_suggestion(tmp_path, suggestion)
    assert drafted["status"] == "proposed" and drafted["applied"] is False
    retry = sc.draft_suggestion(tmp_path, suggestion)
    assert retry["duplicate"] is True and retry["key"] == drafted["key"]
    accepted = sc.accept_suggestion(tmp_path, drafted["key"])
    assert accepted["applied_text"] == "revised"
    rolled = sc.rollback_suggestion(tmp_path, drafted["key"])
    assert rolled["status"] == "rolled_back" and rolled["restored_text"] == "original"


def _run_cli(mods, argv, ctx):
    cli = mods["cli"]
    parser = argparse.ArgumentParser(prog="hermes")
    sub = parser.add_subparsers(dest="command")
    volmarr_parser = sub.add_parser("volmarr")
    cli.register_cli(volmarr_parser)
    args = parser.parse_args(argv)
    return cli.health_command(args, ctx=ctx)


def test_cli_scribing_family(mods, capsys):
    ctx = FakeCtx()
    assert _run_cli(mods, ["volmarr", "scribing", "status", "--json"], ctx) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["tree"]["status"] == "not_configured"
    assert out["production_ready"] is False
    assert _run_cli(mods, ["volmarr", "scribing", "catalog", "--json"], ctx) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["publishes_anything"] is False
    assert _run_cli(mods, ["volmarr", "scribing", "plan", "--json"], ctx) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["step_count"] == 2 and out["refused_count"] == 2
    assert out["runs_foundry"] is False
    assert _run_cli(mods, ["volmarr", "scribing"], ctx) == 2
    capsys.readouterr()
