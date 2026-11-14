"""W13/Q0-Q4 production contracts.

Roadmap Part V acceptance, pinned deterministically: Q0 account
identity/credential ownership stays distinct, local-private egress
is refused by name without a scoped/reversible/logged owner
election, planted canaries are unretrievable through the public
path and local-only sessions emit zero external requests; Q1
threat items count only with named evidence and a planted secret
canary never appears in rendered receipts/audit/scorecard output;
Q2 performance fields are ``unmeasured`` without a measured value
from a named benchmark log (structure only, no benchmark run);
Q3 section 28.3 promotions are refused by name without minimum
proof; Q4 status labels unknown/unavailable engines honestly and
marks docs present/absent by path; the section 32 scorecard is
releasable only when all 15 items are met -- the honest W13
outcome is NOT releasable. CLI tests drive the real
``hermes volmarr production`` family.
"""

from __future__ import annotations

import argparse
import importlib
import json

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
               for name in ("production", "cli")}
    finally:
        manager.unload()
    return out


NOW = "2026-11-08T06:30:00-05:00"
CANARY = "CANARY-PRIVATE-7f3a-never-public"
SECRET = "SECRET-CANARY-9b1e-do-not-render"
DESCRIPTOR = {
    "agent_identity_id": "agent-yrsa-01",
    "credential_owner_id": "owner-volmarr-01",
    "display_name": "Yrsa",
    "scopes": ["drive", "email", "calendar"],
}
ELECTION = {"scoped": True, "reversible": True, "logged": True,
            "elected_by": "owner-volmarr-01", "destinations": ["cloud"]}
FULL_THREAT_EVIDENCE = {
    item: f"evidence://threat/{item}-2026-11" for item in (
        "prompt_injection", "heading_role_impersonation",
        "path_escape_symlink_include", "malformed_utf8",
        "giant_file_dos", "supply_chain", "secret_exposure",
        "profile_leakage", "privilege_escalation", "egress",
        "wal_index_attacks", "replayed_capability_descriptors")}
FULL_SCORECARD_EVIDENCE = {
    item: f"evidence://scorecard/{item}" for item in (
        "upstream_and_personal_revision_recorded",
        "readme_and_markdown_protected_backed_up",
        "no_artificial_size_cutoff",
        "persona_memory_byte_identity_tested",
        "gateway_prompts_contain_kernel_with_receipts",
        "isolation_tests_pass", "critical_security_tests_pass",
        "external_engines_installed_smoke_pass",
        "unavailable_engines_labelled_honestly",
        "offline_session_no_cloud_requests",
        "scoped_authorization_for_writes",
        "native_deploy_rollback_demonstrated",
        "performance_budgets_measured", "no_hidden_regressions",
        "docs_code_capability_agree")}


# ------------------------------------------------------------------ Q0

def test_account_descriptor_valid_with_distinct_ids(mods):
    prod = mods["production"]
    assert prod.validate_account_descriptor(DESCRIPTOR) == []
    assert prod.require_account_descriptor(DESCRIPTOR) is DESCRIPTOR


def test_account_descriptor_missing_fields_refused_by_name(mods):
    prod = mods["production"]
    problems = prod.validate_account_descriptor({"display_name": "Yrsa"})
    assert "missing_field:agent_identity_id" in problems
    assert "missing_field:credential_owner_id" in problems
    with pytest.raises(prod.ProductionError) as exc:
        prod.require_account_descriptor({})
    assert "missing_field:agent_identity_id" in exc.value.detail


def test_account_descriptor_conflation_refused_by_name(mods):
    prod = mods["production"]
    bad = dict(DESCRIPTOR, credential_owner_id=DESCRIPTOR["agent_identity_id"])
    problems = prod.validate_account_descriptor(bad)
    assert any(p.startswith("account_identity_conflated") for p in problems)
    with pytest.raises(prod.ProductionError) as exc:
        prod.require_account_descriptor(bad)
    assert "account_identity_conflated" in exc.value.detail


def test_data_flow_local_private_to_local_allowed(mods):
    prod = mods["production"]
    decision = prod.audit_data_flow(
        {"source_class": "local-private", "destination": "local"})
    assert decision["allowed"] is True
    assert decision["reasons"] == []


def test_data_flow_private_egress_refused_by_name(mods):
    prod = mods["production"]
    decision = prod.audit_data_flow(
        {"source_class": "local-private", "destination": "cloud"})
    assert decision["allowed"] is False
    assert decision["reasons"] == ["q0_private_egress_refused:cloud"]


def test_data_flow_private_egress_complete_election_allowed(mods):
    prod = mods["production"]
    packet = {"source_class": "local-private", "destination": "cloud"}
    assert prod.audit_data_flow(packet, ELECTION)["allowed"] is True
    other = dict(ELECTION, destinations=["shared"])
    decision = prod.audit_data_flow(packet, other)
    assert decision["reasons"] == ["q0_private_egress_refused:cloud"]


def test_data_flow_incomplete_election_refused(mods):
    prod = mods["production"]
    packet = {"source_class": "local-private", "destination": "cloud"}
    for broken in (dict(ELECTION, logged=False),
                   dict(ELECTION, reversible=False),
                   dict(ELECTION, scoped=False),
                   {"scoped": True, "reversible": True, "logged": True}):
        decision = prod.audit_data_flow(packet, broken)
        assert decision["allowed"] is False
        assert decision["reasons"] == ["q0_private_egress_refused:cloud"]


def test_flow_log_records_labels_only_never_payload(mods):
    prod = mods["production"]
    log = prod.FlowLog()
    packet = {"source_class": "local-private", "destination": "local",
              "payload": SECRET}
    record = log.record(packet, recorded_at=NOW)
    assert "payload" not in record
    assert SECRET not in prod.render_audit(log.records())
    assert log.external_flows() == 0


def test_canary_unretrievable_via_public_path(mods):
    prod = mods["production"]
    store = prod.CanaryStore()
    store.add_public("pub-1", "a public note about the weather")
    store.add_private("priv-1", f"diary entry {CANARY}")
    assert store.public_query(CANARY) == []
    assert store.public_query("weather") == ["pub-1"]
    assert store.local_query(CANARY) == ["priv-1"]


def test_local_only_session_zero_external_requests(mods):
    prod = mods["production"]
    store = prod.CanaryStore()
    store.add_private("priv-1", CANARY)
    session = prod.new_local_session()
    prod.record_session_request(session, "local")
    prod.record_session_request(session, "local")
    result = prod.canary_contract(store, CANARY, session)
    assert result["external_requests"] == 0
    assert result["canary_retrievable_via_public"] is False
    assert result["passed"] is True
    assert CANARY not in prod.render_json(result)


def test_session_external_request_fails_canary_contract(mods):
    prod = mods["production"]
    store = prod.CanaryStore()
    store.add_private("priv-1", CANARY)
    session = prod.new_local_session()
    prod.record_session_request(session, "cloud")
    result = prod.canary_contract(store, CANARY, session)
    assert result["external_requests"] == 1
    assert result["passed"] is False


def test_operator_receipts_recorded_per_account(mods):
    prod = mods["production"]
    book = prod.OperatorBook()
    receipts = [book.record(action, "owner-volmarr-01", recorded_at=NOW)
                for action in ("disconnect", "export", "delete")]
    assert [r["action"] for r in receipts] == ["disconnect", "export", "delete"]
    assert len({r["receipt_id"] for r in receipts}) == 3
    assert all(r["status"] == "recorded" for r in receipts)
    with pytest.raises(prod.ProductionError) as exc:
        book.record("impersonate", "owner-volmarr-01", recorded_at=NOW)
    assert "operator_action_unknown:impersonate" in exc.value.detail


def test_scope_inheritance_cross_agent_refused_by_name(mods):
    prod = mods["production"]
    for scope in ("drive", "email", "calendar"):
        decision = prod.check_scope_inheritance(
            requester_agent_id="agent-other-02",
            source_agent_id="agent-yrsa-01", scope=scope)
        assert decision["allowed"] is False
        assert decision["reasons"] == [f"q0_scope_inheritance_refused:{scope}"]
    own = prod.check_scope_inheritance(
        requester_agent_id="agent-yrsa-01",
        source_agent_id="agent-yrsa-01", scope="drive")
    assert own["allowed"] is True


# ------------------------------------------------------------------ Q1

def test_threat_checklist_empty_evidence_all_gaps(mods):
    prod = mods["production"]
    checklist = prod.threat_checklist()
    assert checklist["present_count"] == 0
    assert checklist["gaps"] == list(prod.THREAT_ITEMS)
    assert len(checklist["items"]) == 12


def test_threat_checklist_full_evidence_no_gaps(mods):
    prod = mods["production"]
    checklist = prod.threat_checklist(FULL_THREAT_EVIDENCE)
    assert checklist["present_count"] == 12
    assert checklist["gaps"] == []
    forged = dict(FULL_THREAT_EVIDENCE, egress="   ")
    assert prod.threat_checklist(forged)["gaps"] == ["egress"]


def test_secret_canary_absent_from_rendered_outputs(mods):
    prod = mods["production"]
    book = prod.OperatorBook()
    receipt = book.record("export", "owner-volmarr-01", recorded_at=NOW)
    log = prod.FlowLog()
    log.record({"source_class": "local-private", "destination": "local",
                "payload": SECRET}, recorded_at=NOW)
    scorecard = prod.evaluate_scorecard({}, deferred=dict(prod.KNOWN_DEFERRED))
    rendered = [
        prod.render_receipt(receipt, secrets=[SECRET]),
        prod.render_audit(log.records(), secrets=[SECRET]),
        prod.render_scorecard(scorecard, secrets=[SECRET]),
        prod.render_receipt({"note": f"leaked {SECRET}"}, secrets=[SECRET]),
    ]
    for out in rendered:
        assert SECRET not in out
    assert "[REDACTED]" in rendered[-1]
    assert prod.scan_rendered(rendered, SECRET)["passed"] is True
    assert prod.scan_rendered([f"raw {SECRET}"], SECRET)["leaked"] is True


# ------------------------------------------------------------------ Q2

def test_perf_record_empty_all_unmeasured(mods):
    prod = mods["production"]
    record = prod.performance_record()
    assert record["basis"] == "structure-only-no-benchmark-run-in-this-slice"
    assert record["measured_count"] == 0
    for name in prod.PERF_METRICS:
        block = record["metrics"][name]
        assert block["status"] == "unmeasured"
        assert block["p50"] == "unmeasured"
        assert block["p95"] == "unmeasured"
        assert block["p99"] == "unmeasured"
    assert set(record["unmeasured"]) == set(prod.PERF_METRICS) | set(prod.COUNTER_FIELDS)


def test_perf_record_measured_requires_named_log(mods):
    prod = mods["production"]
    full = {"p50": 1.5, "p95": 4.0, "p99": 9.25,
            "benchmark_log": "bench/query-2026-11.log"}
    record = prod.performance_record({"query_latency": full})
    block = record["metrics"]["query_latency"]
    assert block == {"status": "measured", "p50": 1.5, "p95": 4.0,
                     "p99": 9.25, "benchmark_log": "bench/query-2026-11.log"}
    no_log = {"p50": 1.5, "p95": 4.0, "p99": 9.25}
    assert prod.performance_record(
        {"query_latency": no_log})["metrics"]["query_latency"]["status"] == "unmeasured"
    partial = {"p50": 1.5, "benchmark_log": "bench/query-2026-11.log"}
    block = prod.performance_record(
        {"query_latency": partial})["metrics"]["query_latency"]
    assert block["status"] == "unmeasured"
    assert block["p95"] == "unmeasured"  # never estimated from p50


def test_perf_counters_measured_only_with_named_source(mods):
    prod = mods["production"]
    record = prod.performance_record(
        counters={"section_count": {"value": 2500, "source": "index/status-2026-11"},
                  "fts_size_bytes": {"value": 12345}})
    assert record["counters"]["section_count"]["status"] == "measured"
    assert record["counters"]["section_count"]["value"] == 2500
    assert record["counters"]["fts_size_bytes"]["status"] == "unmeasured"


# ------------------------------------------------------------------ Q3

def test_promotion_refused_without_minimum_proof(mods):
    prod = mods["production"]
    decision = prod.promotion_decision(
        "documented-only", "contract-implemented", {})
    assert decision["promoted"] is False
    assert "evidence_promotion_refused" in decision["reasons"]
    assert "proof_missing:module_ref" in decision["reasons"]
    assert "proof_missing:tests_ref" in decision["reasons"]
    partial = prod.promotion_decision(
        "documented-only", "contract-implemented",
        {"module_ref": "plugins/volmarr-core/production.py"})
    assert partial["promoted"] is False
    assert "proof_missing:tests_ref" in partial["reasons"]


def test_promotion_with_complete_proof_allowed(mods):
    prod = mods["production"]
    decision = prod.promotion_decision(
        "documented-only", "contract-implemented",
        {"module_ref": "plugins/volmarr-core/production.py",
         "tests_ref": "tests/plugins/test_volmarr_production.py"})
    assert decision["promoted"] is True
    assert decision["stage"] == "contract-implemented"
    full = {key: f"evidence://prod/{key}" for key in (
        "security_ref", "persistence_ref", "performance_ref",
        "operating_limits_ref", "rollback_ref", "cross_platform_ref")}
    jump = prod.promotion_decision("documented-only", "production-qualified", full)
    assert jump["promoted"] is True


def test_promotion_backward_and_unknown_refused(mods):
    prod = mods["production"]
    back = prod.promotion_decision(
        "contract-implemented", "documented-only", {"design_ref": "x"})
    assert back["promoted"] is False
    assert "evidence_promotion_refused" in back["reasons"]
    unknown = prod.promotion_decision("documented-only", "live", {})
    assert unknown["allowed"] is False
    assert "evidence_stage_unknown:live" in unknown["reasons"]


def test_deferred_requires_reason(mods):
    prod = mods["production"]
    no_reason = prod.promotion_decision(
        "contract-implemented", "deferred/blocked", {})
    assert no_reason["allowed"] is False
    assert "deferred_reason_required" in no_reason["reasons"]
    with_reason = prod.promotion_decision(
        "contract-implemented", "deferred/blocked", {},
        reason="no live Verdandi service on this host; E.01 owns the proof")
    assert with_reason["allowed"] is True
    assert with_reason["deferred"] is True


# ------------------------------------------------------------------ Q4

def test_docs_deliverables_present_absent_by_path(mods, tmp_path):
    prod = mods["production"]
    (tmp_path / "docs" / "modernization").mkdir(parents=True)
    (tmp_path / "docs" / "modernization" / "LAUNCH_RECIPE.md").write_text("x")
    (tmp_path / "SECURITY.md").write_text("x")
    rows = {r["deliverable"]: r for r in prod.docs_deliverables(tmp_path)}
    assert rows["beginner_setup"]["present"] is True
    assert rows["beginner_setup"]["path"] == "docs/modernization/LAUNCH_RECIPE.md"
    assert rows["threat_model"]["present"] is True
    assert rows["migration"]["present"] is False
    assert rows["troubleshooting"]["present"] is False
    assert rows["benchmark_instructions"]["present"] is False


def test_production_status_labels_engines_honestly(mods, tmp_path):
    prod = mods["production"]
    engines = {"status": "ok", "engines": [
        {"name": "A", "evidence_stage": "contract implemented", "verification": "verified"},
        {"name": "B", "evidence_stage": None, "verification": "unverified"},
        {"name": "C", "evidence_stage": "end-to-end working", "verification": "verified"}]}
    caps = {"status": "ok", "services": [
        {"service": "volmarr-astrology", "version": "0.7.0",
         "availability": "contract-implemented"}]}
    status = prod.production_status(
        recorded_at=NOW, root=tmp_path,
        engines_status=engines, capabilities_status=caps)
    rows = {r["name"]: r for r in status["engines"]["engines"]}
    assert rows["A"]["working"] is False
    assert rows["B"]["working"] is False
    assert rows["B"]["label"] == "unknown"
    assert rows["C"]["working"] is True
    assert status["engines"]["working_count"] == 1
    assert status["capabilities"]["services"][0]["working"] is False
    assert status["live_connection"] == "not-claimed"
    assert "migration" in status["next_required_action"]
    assert status["linked_profile"] == "unknown"


# ------------------------------------------------------------- scorecard

def test_scorecard_empty_not_releasable_all_named(mods):
    prod = mods["production"]
    card = prod.evaluate_scorecard({})
    assert card["releasable"] is False
    assert card["met_count"] == 0
    assert len(card["items"]) == 15
    assert card["unmet"] == [f"unmet:{i}" for i in prod.SCORECARD_ITEMS]


def test_scorecard_full_evidence_releasable(mods):
    prod = mods["production"]
    card = prod.evaluate_scorecard(FULL_SCORECARD_EVIDENCE)
    assert card["releasable"] is True
    assert card["met_count"] == 15
    assert card["unmet"] == []
    assert card["deferred"] == []


def test_scorecard_deferred_named_and_blocks_release(mods):
    prod = mods["production"]
    evidence = dict(FULL_SCORECARD_EVIDENCE)
    del evidence["no_hidden_regressions"]
    del evidence["performance_budgets_measured"]
    evidence["isolation_tests_pass"] = "   "  # blank ref never counts
    card = prod.evaluate_scorecard(
        evidence, deferred={"no_hidden_regressions": "7 live-transport failures open"})
    assert card["releasable"] is False
    assert "deferred:no_hidden_regressions:7 live-transport failures open" in card["deferred"]
    assert "unmet:performance_budgets_measured" in card["unmet"]
    assert "unmet:isolation_tests_pass" in card["unmet"]


# ------------------------------------------------------------------- CLI

class _Ctx:
    def __init__(self):
        self._config = {}

    def config_get(self, key, default=None):
        return self._config.get(key, default)


def _run_cli(mods, argv):
    cli = mods["cli"]
    parser = argparse.ArgumentParser(prog="hermes")
    sub = parser.add_subparsers(dest="command")
    volmarr_parser = sub.add_parser("volmarr")
    cli.register_cli(volmarr_parser)
    args = parser.parse_args(argv)
    return cli.health_command(args, ctx=_Ctx())


def test_cli_production_status_scorecard_audit(mods, capsys):
    prod = mods["production"]
    rc = _run_cli(mods, ["volmarr", "production", "status", "--json"])
    assert rc == 0
    status = json.loads(capsys.readouterr().out)
    assert status["live_connection"] == "not-claimed"
    assert status["engines"]["engine_count"] == 28
    assert status["engines"]["working_count"] == 0
    docs = {d["deliverable"]: d["present"] for d in status["docs"]}
    assert docs["beginner_setup"] is True
    assert docs["threat_model"] is True
    assert docs["migration"] is False
    rc = _run_cli(mods, ["volmarr", "production", "scorecard", "--json"])
    assert rc == 1  # honest: not releasable
    card = json.loads(capsys.readouterr().out)
    assert card["releasable"] is False
    assert any(d.startswith("deferred:no_hidden_regressions:") for d in card["deferred"])
    assert any("W00.03-ENC" in d for d in card["deferred"])
    assert SECRET not in prod.render_scorecard(card, secrets=[SECRET])
    rc = _run_cli(mods, ["volmarr", "production", "audit", "--json"])
    assert rc == 0
    audit = json.loads(capsys.readouterr().out)
    assert audit["provenance"]["service"] == "volmarr-production"
    assert audit["outputs"]["threat"]["gaps"] == list(prod.THREAT_ITEMS)
    assert audit["outputs"]["performance"]["measured_count"] == 0
