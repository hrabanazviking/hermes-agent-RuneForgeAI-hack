"""X.13 HugrGate contracts (roadmap section 48).

These contracts pin the section 48 gates on the structured-
uncertainty connector: unconfigured truthfulness, configured
measurement of a staged tree's structure only, the contract
catalog claiming only the types a bundled backend verifies at
the audited HEAD (numeric / multilabel refused as unverified),
the honest inference ladder (cloud rung never offered, never
a fallback), schema conformance, a deterministic pure-rules
evaluation with typed results, versioned calibration metrics
computed only from supplied examples, deterministic fallback,
abstention as a first-class outcome, offline/no-egress,
timeout, cyclic route refusal, refused decision subjects, and
the performance budget. No engine code is run by any contract.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
from pathlib import Path

import pytest

HEAD = "2aa74350fa76bc4a35a0841db4582d6fa8b12ae9"
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
               for name in ("hugrgate", "cli")}
    finally:
        manager.unload()
    return out


class FakeCtx:
    def __init__(self, cfg=None):
        self._cfg = cfg or {}

    def get_config(self, key, default=None):
        return self._cfg.get(key, default)


def _fake_tree(tmp_path: Path) -> Path:
    root = tmp_path / "hugrgate"
    (root / ".git" / "refs" / "heads").mkdir(parents=True)
    (root / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (root / ".git" / "refs" / "heads" / "main").write_text(HEAD + "\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "hugrgate"\nversion = "1.0.0"\n', encoding="utf-8")
    (root / "LICENSE").write_bytes(b"fake license text for structure only")
    pkg = root / "hugrgate"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "spec.py").write_text("", encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_fake.py").write_text("", encoding="utf-8")
    return root


def _binary_request(**overrides):
    request = {
        "spec": {"type": "binary", "statement": "Route the candidate"},
        "features": {"queue_depth": 2},
        "use": "candidate_routing",
        "rules": [{"field": "queue_depth", "op": "lte", "value": 3,
                   "outcome": "true", "confidence": 0.9}],
    }
    request.update(overrides)
    return request


def test_status_unconfigured_is_truthful(mods):
    hg = mods["hugrgate"]
    record = hg.hugrgate_status(FakeCtx(), recorded_at="t")
    assert record["schema"] == "runeforge.hugrgate.status.v1"
    assert record["canonical_repo"] == "hrabanazviking/RuneForgeAI-HugrGate"
    assert record["audited_head"] == HEAD == hg.AUDITED_HEAD
    assert record["package_version"] == "1.0.0"
    assert record["license"] == "Apache-2.0"
    assert record["enabled"] is False and record["configured"] is False
    assert record["tree"]["status"] == "not_configured"
    assert record["sends_anything_external"] is False
    assert record["runs_engine"] is False
    assert record["production_ready"] is False


def test_status_configured_measures_tree_structure(mods, tmp_path):
    hg = mods["hugrgate"]
    root = _fake_tree(tmp_path)
    ctx = FakeCtx({"hugrgate_enabled": True, "hugrgate_root": str(root)})
    record = hg.hugrgate_status(ctx, recorded_at="t")
    assert record["enabled"] is True and record["configured"] is True
    tree = record["tree"]
    assert tree["status"] == "measured"
    assert tree["head"] == HEAD and tree["head_matches_audited"] is True
    assert tree["package_version"] == "1.0.0"
    assert tree["module_count"] == 3 and tree["package_module_count"] == 2
    assert tree["test_file_count"] == 1
    assert tree["license_sha256"] == hashlib.sha256(
        b"fake license text for structure only").hexdigest()
    assert tree["license_matches_audited"] is False
    assert hg.LICENSE_SHA256 == LICENSE_SHA


def test_catalog_claims_only_verified_contract_types(mods):
    hg = mods["hugrgate"]
    catalog = hg.decision_catalog()
    assert catalog["schema"] == "runeforge.hugrgate.catalog.v1"
    by_type = {row["type"]: row for row in catalog["contracts"]}
    assert set(by_type) == {"binary", "categorical", "ordinal",
                            "numeric", "multilabel"}
    for kind in ("binary", "categorical", "ordinal"):
        assert by_type[kind]["verified_at_audited_head"] is True
        assert by_type[kind]["connector_evaluation"] == "deterministic_rules"
    for kind in ("numeric", "multilabel"):
        assert by_type[kind]["declared_in_engine_schema"] is True
        assert by_type[kind]["verified_at_audited_head"] is False
        assert by_type[kind]["connector_evaluation"] == "refused_unverified"
    assert catalog["verified_types"] == ["binary", "categorical", "ordinal"]
    assert catalog["unverified_types"] == ["numeric", "multilabel"]
    assert catalog["production_ready"] is False


def test_catalog_ladder_is_honest_and_cloud_never_offered(mods):
    hg = mods["hugrgate"]
    catalog = hg.decision_catalog()
    ladder = {row["rung"]: row for row in catalog["inference_ladder"]}
    assert list(ladder) == ["pure_rules", "classical_statistics_ml",
                            "embeddings_onnx", "tiny_local_llm",
                            "larger_local_model", "authorized_cloud_model"]
    assert ladder["pure_rules"]["offered_by_connector"] is True
    assert ladder["pure_rules"]["connector_binds"] is True
    for rung in ("classical_statistics_ml", "embeddings_onnx",
                 "tiny_local_llm", "larger_local_model"):
        assert ladder[rung]["exists_in_engine"] is True
        assert ladder[rung]["connector_binds"] is False
    cloud = ladder["authorized_cloud_model"]
    assert cloud["exists_in_engine"] is False
    assert cloud["offered_by_connector"] is False
    assert cloud["requires_authorization"] is True
    assert catalog["cloud_rung_offered"] is False
    assert catalog["cloud_requires_explicit_authorization"] is True
    assert catalog["refused_subjects"] == [
        "secrets_access", "destructive_action_authorization"]
    assert catalog["cyclic_routes_refused"] == [
        "hugrgate", "aesir", "thoughtforge", "mindspark"]
    assert catalog["allowed_uses"] == [
        "candidate_routing", "relevance_classification",
        "observational_prioritization"]
    assert catalog["performance_budget_ms"] == 250
    assert catalog["sends_anything_external"] is False


def test_schema_conformance_valid_and_invalid_specs(mods):
    hg = mods["hugrgate"]
    cat = hg.evaluate_decision({
        "spec": {"type": "categorical", "options": ["low", "high"]},
        "features": {"score": 9},
        "rules": [{"field": "score", "op": "gte", "value": 5,
                   "outcome": "high", "confidence": 0.8}]})
    assert cat["outcome"] == "decision" and cat["value"] == "high"
    assert cat["decision_type"] == "categorical"
    ordinal = hg.evaluate_decision({
        "spec": {"type": "ordinal", "levels": ["low", "mid", "high"]},
        "features": {"score": 1},
        "rules": [{"field": "score", "op": "lte", "value": 2,
                   "outcome": "low", "confidence": 0.7}]})
    assert ordinal["outcome"] == "decision" and ordinal["value"] == "low"
    assert ordinal["decision_type"] == "ordinal"
    cases = [
        ({"spec": {"type": "weird"}}, "spec_type_unknown"),
        ({"spec": {"type": "binary"}}, "spec_statement_missing"),
        ({"spec": {"type": "categorical", "options": ["only"]}},
         "spec_options_invalid"),
        ({"spec": {"type": "categorical", "options": ["a", "a"]}},
         "spec_options_invalid"),
        ({"spec": {"type": "ordinal", "levels": ["a", "a"]}},
         "spec_levels_invalid"),
        ({"spec": {"type": "numeric", "minimum": 5, "maximum": 5}},
         "spec_bounds_invalid"),
        ({"spec": {"type": "multilabel", "labels": []}},
         "spec_labels_invalid"),
        ({"spec": "nope"}, "spec_not_mapping"),
        ("nope", "request_not_mapping"),
    ]
    for request, reason in cases:
        result = hg.evaluate_decision(request)
        assert result["outcome"] == "failure", (request, result)
        assert result["failure"] == reason, (request, result)
        assert result["fail_closed"] is True and result["value"] is None


def test_deterministic_evaluation_typed_result(mods):
    hg = mods["hugrgate"]
    result = hg.evaluate_decision(_binary_request())
    assert result["schema"] == "runeforge.hugrgate.result.v1"
    assert result["outcome"] == "decision" and result["accepted"] is True
    assert result["decision_type"] == "binary"
    assert result["value"] == "true"
    assert result["probability"] == pytest.approx(0.9)
    assert result["confidence"] == result["probability"]
    assert result["distribution"] == {"true": pytest.approx(0.9),
                                      "false": pytest.approx(0.1)}
    assert sum(result["distribution"].values()) == pytest.approx(1.0)
    assert result["distribution"][result["value"]] == result["probability"]
    assert result["uncertainty"] == pytest.approx(0.1)
    assert result["backend"] == "deterministic_rules"
    assert result["source_revision"] == HEAD
    assert result["calibration_profile"] == "none"
    assert result["fallback_used"] is False
    assert result["privacy_label"] == "local-private"
    assert result["provenance"]["audited_head"] == HEAD
    assert "secrets access" in result["task_control_effect"]
    again = hg.evaluate_decision(_binary_request())
    for key in ("value", "probability", "distribution", "uncertainty"):
        assert again[key] == result[key]
    labelled = hg.evaluate_decision(_binary_request(privacy_label="shared"))
    assert labelled["privacy_label"] == "shared"


def test_unverified_contract_types_refused_by_name(mods):
    hg = mods["hugrgate"]
    numeric = hg.evaluate_decision({
        "spec": {"type": "numeric", "minimum": 0, "maximum": 10},
        "features": {"score": 5}, "rules": []})
    assert numeric["outcome"] == "failure"
    assert numeric["failure"] == "contract_type_unverified"
    assert numeric["decision_type"] == "numeric"
    multilabel = hg.evaluate_decision({
        "spec": {"type": "multilabel", "labels": ["a", "b"]},
        "features": {}, "rules": []})
    assert multilabel["failure"] == "contract_type_unverified"
    assert multilabel["fail_closed"] is True


def test_calibration_metrics_from_real_examples_only(mods):
    hg = mods["hugrgate"]
    empty = hg.calibration_metrics([])
    assert empty["computed"] is False and empty["reason"] == "no_examples"
    assert "brier_score" not in empty
    assert empty["claims_production_calibration"] is False
    metrics = hg.calibration_metrics([
        {"probability": 0.9, "actual": True, "synthetic": True},
        {"probability": 0.1, "actual": False, "synthetic": True}])
    assert metrics["computed"] is True
    assert metrics["metrics_version"] == "runeforge.hugrgate.calibration.v1"
    assert metrics["brier_score"] == pytest.approx(0.01)
    assert metrics["log_loss"] == pytest.approx(-math.log(0.9))
    assert metrics["abstention_rate"] == 0.0
    assert metrics["source_label"] == "synthetic fixtures (labelled)"
    assert metrics["production_calibration"] == "unproven"
    mixed = hg.calibration_metrics([
        {"probability": 0.9, "actual": True},
        {"probability": 0.1, "actual": False},
        {"probability": 0.5, "actual": True},
        {"abstained": True}])
    assert mixed["abstention_rate"] == pytest.approx(0.25)
    assert mixed["scored_count"] == 3 and mixed["abstained_count"] == 1
    bad = hg.calibration_metrics([{"probability": 2.0, "actual": True}])
    assert bad["computed"] is False and bad["reason"] == "malformed_example"


def test_deterministic_fallback_and_cloud_refusals(mods):
    hg = mods["hugrgate"]
    fell_back = hg.evaluate_decision(_binary_request(rung="tiny_local_llm"))
    assert fell_back["outcome"] == "decision"
    assert fell_back["fallback_used"] is True
    assert fell_back["fallback_reason"] == "rung_not_bound:tiny_local_llm"
    assert fell_back["provenance"]["rung_used"] == "pure_rules"
    assert fell_back["value"] == "true"
    malformed = hg.evaluate_decision(_binary_request(rules=[
        {"field": "queue_depth", "op": "lte", "value": 3,
         "outcome": "true", "confidence": 1.5}]))
    assert malformed["outcome"] == "failure"
    assert malformed["failure"] == "malformed_rule"
    assert malformed["fallback_applied"] == "deterministic_abstain"
    cloud = hg.evaluate_decision(
        _binary_request(rung="authorized_cloud_model"))
    assert cloud["outcome"] == "failure"
    assert cloud["failure"] == "cloud_not_authorized"
    assert cloud["value"] is None and cloud["sends_anything_external"] is False
    authorized = hg.evaluate_decision(
        _binary_request(rung="authorized_cloud_model"), cloud_authorized=True)
    assert authorized["failure"] == "cloud_adapter_unavailable"
    unknown = hg.evaluate_decision(_binary_request(rung="psychic"))
    assert unknown["failure"] == "unknown_rung"


def test_abstention_is_first_class_with_task_control(mods):
    hg = mods["hugrgate"]
    result = hg.evaluate_decision(_binary_request(features={"queue_depth": 99}))
    assert result["outcome"] == "abstain"
    assert result["value"] is None and result["accepted"] is False
    assert result["abstain_reason"] == "no_rule_matched"
    assert result["uncertainty"] == 1.0 and result["probability"] == 0.0
    assert result["task_control_effect"].startswith(
        "hold_and_use_deterministic_default")
    assert result["source_revision"] == HEAD
    assert result["production_ready"] is False


def test_refused_subjects_and_cyclic_routes_by_name(mods):
    hg = mods["hugrgate"]
    for subject in ("secrets_access", "destructive_action_authorization"):
        result = hg.evaluate_decision(_binary_request(subject=subject))
        assert result["outcome"] == "failure"
        assert result["failure"] == "decision_subject_refused"
        assert result["subject"] == subject
    for route in ("aesir", "thoughtforge", "mindspark", "hugrgate"):
        result = hg.evaluate_decision(_binary_request(route_via=[route]))
        assert result["failure"] == "cyclic_route_refused", route
        assert result["route"] == route
    bad_use = hg.evaluate_decision(_binary_request(use="secrets_access"))
    assert bad_use["failure"] == "use_not_allowed"


def test_timeout_and_performance_budget(mods):
    hg = mods["hugrgate"]
    timed_out = hg.evaluate_decision(_binary_request(), elapsed_ms=10000.0)
    assert timed_out["outcome"] == "failure"
    assert timed_out["failure"] == "timeout"
    assert timed_out["fail_closed"] is True
    within = hg.evaluate_decision(_binary_request(), elapsed_ms=10.0)
    assert within["outcome"] == "decision"
    result = hg.evaluate_decision(_binary_request())
    assert result["latency_ms"] < hg.PERFORMANCE_BUDGET_MS == 250
    oversized = hg.evaluate_decision(
        _binary_request(features={f"f{i}": i for i in range(40)}))
    assert oversized["failure"] == "input_too_large"
    not_mapping = hg.evaluate_decision(_binary_request(features=["x"]))
    assert not_mapping["failure"] == "features_not_mapping"


def test_offline_no_egress_everywhere(mods):
    hg = mods["hugrgate"]
    assert hg.hugrgate_status(FakeCtx())["sends_anything_external"] is False
    assert hg.decision_catalog()["sends_anything_external"] is False
    decision = hg.evaluate_decision(_binary_request())
    assert decision["sends_anything_external"] is False
    assert decision["runs_engine"] is False
    abstain = hg.evaluate_decision(_binary_request(features={"queue_depth": 99}))
    assert abstain["sends_anything_external"] is False
    failure = hg.evaluate_decision(_binary_request(subject="secrets_access"))
    assert failure["sends_anything_external"] is False


def _run_cli(mods, argv, ctx):
    cli = mods["cli"]
    parser = argparse.ArgumentParser(prog="hermes")
    sub = parser.add_subparsers(dest="command")
    volmarr_parser = sub.add_parser("volmarr")
    cli.register_cli(volmarr_parser)
    args = parser.parse_args(argv)
    return cli.health_command(args, ctx=ctx)


def test_cli_hugrgate_family(mods, capsys):
    ctx = FakeCtx()
    assert _run_cli(mods, ["volmarr", "hugrgate", "status", "--json"], ctx) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["tree"]["status"] == "not_configured"
    assert out["production_ready"] is False
    assert _run_cli(mods, ["volmarr", "hugrgate", "catalog", "--json"], ctx) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["verified_types"] == ["binary", "categorical", "ordinal"]
    assert out["cloud_rung_offered"] is False
    assert _run_cli(mods, ["volmarr", "hugrgate", "evaluate", "--json"], ctx) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["decision"]["outcome"] == "decision"
    assert out["decision"]["value"] == "true"
    assert out["decision"]["probability"] == pytest.approx(0.9)
    assert out["abstention_case"]["outcome"] == "abstain"
    assert out["abstention_case"]["abstain_reason"] == "no_rule_matched"
    assert "synthetic" in out["source_label"]
    assert _run_cli(mods, ["volmarr", "hugrgate"], ctx) == 2
    capsys.readouterr()
