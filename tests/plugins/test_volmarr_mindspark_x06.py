"""X.06 MindSpark ThoughtForge contracts (roadmap section 41).

These contracts pin the section 41 test gates on the
deterministic-first adapter: measured quality across small
tasks (synthetic-case accuracy of the deterministic baseline),
zero hidden cloud fallback, budget adherence, model crash
recovery, and verified kernel consistency -- plus the item 5
single-compiler rule, item 6 policy inheritance, item 8
failure discipline and item 9 truthful unconfigured behaviour.
Every fixture is synthetic; no ThoughtForge source and no
real model is involved -- model runners are injected fakes.
"""
from __future__ import annotations

import argparse
import importlib
import json
import threading

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
               for name in ("mindspark", "cli")}
    finally:
        manager.unload()
    return out


class FakeCtx:
    def __init__(self, cfg=None):
        self._cfg = cfg or {}

    def get_config(self, key, default=None):
        return self._cfg.get(key, default)


def _compiled_fixture():
    return {
        "index": [
            {"role": "core", "section_id": "who",
             "heading": "Identity",
             "text": "My name and identity: I am a keeper of lore."},
            {"role": "core", "section_id": "talk",
             "heading": "Voice",
             "text": "My voice and speech stay calm."},
            {"role": "core", "section_id": "edge",
             "heading": "Limits",
             "text": "I must not cross this boundary; never share it."},
        ],
        "kernel": {"sources": [{"role": "core", "section_id": "who"}]},
    }


def test_profile_catalog_is_the_section_41_six(mods):
    m = mods["mindspark"]
    catalog = m.profile_catalog()
    names = [p["name"] for p in catalog["profiles"]]
    assert names == ["classifier", "router", "reflection",
                     "persona_tagging", "budget_planner", "validation"]
    assert all(p["method"] == "deterministic"
               for p in catalog["profiles"])
    assert catalog["model_benefit_proven"] is False


def test_classifier_baseline_accuracy_and_determinism(mods):
    m = mods["mindspark"]
    bench = m.benchmark_deterministic()
    assert bench["cases"] == len(m.BENCHMARK_CASES)
    assert bench["accuracy"] == 1.0  # synthetic authored labels
    assert bench["latency_ms_max"] >= bench["latency_ms_mean"] >= 0
    assert bench["model_numbers"] is None
    assert bench["cross_device_numbers"] is None
    first = m.classify_task("The api function will not compile")
    second = m.classify_task("The api function will not compile")
    assert first == second and first["model_called"] is False


def test_router_proposal_keeps_authority_in_hermes(mods):
    m = mods["mindspark"]
    plain = m.propose_route("classifier", "hello there")
    assert plain["route"] == "deterministic"
    assert plain["proposal_only"] is True
    assert plain["final_authority"] == "hermes"
    assert plain["budget_enforced_by"] == "hermes"
    eager = m.propose_route("classifier", "hello there",
                            model_configured=True)
    assert eager["route"] == "model"  # a proposal, never an order
    denied = m.propose_route(
        "classifier", "hello there", model_configured=True,
        parent_policy={"allow_model": False})
    assert denied["route"] == "deterministic"
    assert denied["parent_policy_inherited"] is True


def test_budget_planner_never_exceeds_parent_or_cap(mods):
    m = mods["mindspark"]
    plan = m.plan_token_budget("reflection", input_chars=4000,
                               parent_budget_tokens=100)
    assert plan["granted_tokens"] == 100
    assert plan["clamped_by"] == "parent_budget"
    assert plan["enforced_by"] == "hermes"
    capped = m.plan_token_budget("classifier", input_chars=100000)
    assert capped["granted_tokens"] == 64  # the profile cap
    zero = m.plan_token_budget("classifier", input_chars=10,
                               parent_budget_tokens=0)
    assert zero["granted_tokens"] == 0


def test_validation_reports_malformed_as_data(mods):
    m = mods["mindspark"]
    bad = m.validate_output("classifier", "not json at all")
    assert bad["valid"] is False and "output_not_json" in bad["errors"]
    missing = m.validate_output("classifier", '{"route": "x"}')
    assert missing["valid"] is False
    assert "missing_key:intent" in missing["errors"]
    good = m.validate_output("classifier", '{"intent": "factual"}')
    assert good["valid"] is True and good["parsed"]["intent"] == "factual"
    assert m.validate_output("reflection", "")["valid"] is False
    assert m.validate_output("reflection", "a short note")["valid"] is True


def test_reflection_is_extractive_and_bounded(mods):
    m = mods["mindspark"]
    text = ("The river runs cold in winter. "
            "The river carries ice from the high fells. "
            "A single crow watched the grey road all morning.")
    out = m.reflect_short(text, max_chars=80)
    assert out["model_called"] is False
    for sentence in out["reflection"].split(". "):
        assert sentence.strip().rstrip(".") in text
    assert len(out["reflection"]) <= 120


def test_persona_tagging_requires_the_single_compiler(mods):
    m = mods["mindspark"]
    with pytest.raises(m.MindSparkError) as exc:
        m.tag_persona_sections("raw persona text, not a compile")
    assert exc.value.name == "persona_compiler_artefact_required"
    with pytest.raises(m.MindSparkError) as exc:
        m.tag_persona_sections({"index": []})  # no kernel: not a compile
    assert exc.value.name == "persona_compiler_artefact_required"
    tagged = m.tag_persona_sections(_compiled_fixture())
    tags = {row["section_id"]: row["tag"] for row in tagged["sections"]}
    assert tags == {"who": "identity", "talk": "voice", "edge": "boundary"}
    assert tagged["kernel_consistent"] is True
    broken = _compiled_fixture()
    broken["kernel"] = {"sources": [{"role": "core",
                                     "section_id": "ghost"}]}
    verdict = m.tag_persona_sections(broken)
    assert verdict["kernel_consistent"] is False
    assert verdict["kernel_unresolved"] == 1


def test_model_failures_fall_back_deterministically(mods):
    m = mods["mindspark"]

    def crash(prompt, max_tokens):
        raise RuntimeError("synthetic crash")

    def oom(prompt, max_tokens):
        raise MemoryError("synthetic oom")

    def garbage(prompt, max_tokens):
        return "definitely not json"

    text = "What is the capital of Norway"
    for runner, reason in ((crash, "model_crash"),
                           (oom, "model_out_of_memory"),
                           (garbage, "model_malformed_output")):
        out = m.run_profile("classifier", text, runner=runner)
        assert out["engine"] == "deterministic"
        assert out["fallback"] == {"used": True, "reason": reason}
        assert out["intent"] == "factual"
    cancelled = threading.Event()
    cancelled.set()
    out = m.run_profile("classifier", text, runner=crash, cancel=cancelled)
    assert out["fallback"]["reason"] == "cancelled"


def test_model_partial_output_is_flagged_never_completed(mods):
    m = mods["mindspark"]

    def partial(prompt, max_tokens):
        return {"text": "A short partial reflect", "partial": True}

    out = m.run_profile("reflection", "Some text to reflect on.",
                        runner=partial)
    assert out["engine"] == "model" and out["partial"] is True
    assert out["complete"] is False

    def whole(prompt, max_tokens):
        return '{"intent": "factual"}'

    out = m.run_profile("classifier", "What is the capital of Norway",
                        runner=whole)
    assert out["engine"] == "model" and out["complete"] is True
    assert out["budget"]["granted_tokens"] <= 64


def test_policy_inheritance_and_zero_cloud_fallback(mods):
    m = mods["mindspark"]
    calls = []

    def runner(prompt, max_tokens):
        calls.append(prompt)
        return '{"intent": "factual"}'

    out = m.run_profile("classifier", "What is the capital of Norway",
                        runner=runner,
                        parent_policy={"allow_model": False})
    assert out["engine"] == "deterministic"
    assert out["fallback"]["reason"] == "parent_policy_denies_model"
    assert calls == []  # the model was never invoked
    with pytest.raises(m.MindSparkError) as exc:
        m.LocalModelRunner("https://api.example.invalid/v1", "m")
    assert exc.value.name == "cloud_endpoint_refused"
    with pytest.raises(m.MindSparkError) as exc:
        m.LocalModelRunner("http://192.0.2.10:1234/v1", "m")
    assert exc.value.name == "cloud_endpoint_refused"
    local = m.LocalModelRunner("http://127.0.0.1:9999/v1", "tiny")
    assert local.base_url == "http://127.0.0.1:9999/v1"


def test_status_is_truthful_when_unconfigured(mods):
    m = mods["mindspark"]
    record = m.mindspark_status(FakeCtx(), recorded_at="t")
    assert record["enabled"] is False
    assert record["model_configured"] is False
    assert record["model"]["reason"].startswith("no model configured")
    assert record["model_benefit_proven"] is False
    assert record["pin_taken_in_x06"] is False
    assert record["production_ready"] is False
    assert record["source_head_audited"] == m.SOURCE_HEAD_AUDITED
    half = m.mindspark_status(FakeCtx({"mindspark_model_name": "tiny"}))
    assert half["model_configured"] is False
    assert "incomplete" in half["model"]["reason"]
    cloud = m.mindspark_status(FakeCtx({
        "mindspark_model_base_url": "https://api.example.invalid/v1",
        "mindspark_model_name": "tiny"}))
    assert cloud["model_configured"] is False
    assert "cloud_endpoint_refused" in cloud["model"]["reason"]


def _run_cli(mods, argv, ctx):
    cli = mods["cli"]
    parser = argparse.ArgumentParser(prog="hermes")
    sub = parser.add_subparsers(dest="command")
    volmarr_parser = sub.add_parser("volmarr")
    cli.register_cli(volmarr_parser)
    args = parser.parse_args(argv)
    return cli.health_command(args, ctx=ctx)


def test_cli_mindspark_family(mods, capsys):
    m = mods["mindspark"]
    ctx = FakeCtx()
    rc = _run_cli(mods, ["volmarr", "mindspark", "status", "--json"], ctx)
    assert rc == 0
    record = json.loads(capsys.readouterr().out)
    assert record["service"] == "volmarr-mindspark"
    assert record["model_configured"] is False  # truthful absence
    assert record["design"] == "deterministic-first"
    rc = _run_cli(mods, ["volmarr", "mindspark", "profiles", "--json"], ctx)
    assert rc == 0
    catalog = json.loads(capsys.readouterr().out)
    assert len(catalog["profiles"]) == 6
    rc = _run_cli(mods, ["volmarr", "mindspark", "classify",
                         "What is the capital of Norway", "--json"], ctx)
    assert rc == 0
    verdict = json.loads(capsys.readouterr().out)
    assert verdict["intent"] == "factual"
    assert verdict["engine"] == "deterministic"
    rc = _run_cli(mods, ["volmarr", "mindspark", "benchmark", "--json"], ctx)
    assert rc == 0
    bench = json.loads(capsys.readouterr().out)
    assert bench["accuracy"] == 1.0 and bench["model_numbers"] is None
    rc = _run_cli(mods, ["volmarr", "mindspark"], ctx)
    assert rc == 2
    capsys.readouterr()
    assert m.SOURCE_HEAD_AUDITED == "68aa4d1cd29f6d6c57d1266e70833584c9b1a74e"
