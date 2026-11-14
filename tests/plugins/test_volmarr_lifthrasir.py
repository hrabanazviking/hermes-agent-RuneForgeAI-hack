"""X.02 Lifthrasir diagnostics contracts (roadmap section 37).

These contracts pin: the DiagnosticReport is complete
(commands executed, privileges, error codes, evidence,
timestamps, redaction), redaction actually removes a seeded
secret, the adapter's read-only guarantee (it refuses and
never invokes a mutating command), the section 37.7 separation
of diagnosis from repair/deployment/resolution, and truthful
privilege recording (unprivileged only). All diagnostics here
run against a fake runner -- no real host command executes in
these tests except the CLI status verb. CLI tests drive the
real ``hermes volmarr lifthrasir`` family.
"""
from __future__ import annotations

import argparse
import importlib
import json

import pytest

from hermes_constants import get_hermes_home

SEEDED_SECRET = "hunter2-super-secret-value"


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
               for name in ("lifthrasir", "cli")}
    finally:
        manager.unload()
    return out


class FakeRunner:
    """Records every argv it is asked to run; serves canned
    read-only output, including one seeded secret in the logs."""

    def __init__(self):
        self.calls = []

    def __call__(self, argv, timeout_s):
        self.calls.append(list(argv))
        prog = argv[0]
        if prog == "uname":
            return 0, "Linux 6.8.0-test x86_64\n", ""
        if prog == "hostname":
            return 0, "testhost\n", ""
        if prog == "systemctl" and "--failed" in argv:
            return 0, "badsvc.service loaded failed failed\n", ""
        if prog == "systemctl":
            return 0, "systemd 255 (255.1-test)\n", ""
        if prog == "journalctl":
            return 0, ("2026-11-14T00:00:00 testhost app: "
                       f"password={SEEDED_SECRET} failed login\n"
                       "2026-11-14T00:01:00 testhost app: "
                       "path /home/testuser/.config touched\n"), ""
        if prog == "dpkg-query":
            return 0, "bash 5.2-1\ncoreutils 9.4-1\n", ""
        return None, "", "executable_not_found"


def _report(mods, **kw):
    lf = mods["lifthrasir"]
    runner = kw.pop("runner", None) or FakeRunner()
    report = lf.run_diagnostics(
        runner=runner, recorded_at="2026-11-14T12:00:00+00:00",
        hostname="testhost", **kw)
    return report, runner


def test_report_contract_completeness(mods):
    lf = mods["lifthrasir"]
    report, _ = _report(mods)
    assert report["schema"] == lf.REPORT_SCHEMA
    assert report["source_project"] == lf.SOURCE_PROJECT
    assert report["stage"] == "diagnosed"
    assert report["started_at"] and report["finished_at"]
    assert report["privileges_used"] == ["unprivileged"]
    assert report["report_id"].startswith("diag-")
    ids = {c["id"] for c in report["commands_executed"]}
    assert {"kernel.uname", "systemd.failed", "logs.journal",
            "packages.dpkg"} <= ids
    for rec in report["commands_executed"]:
        assert rec["read_only"] is True
        assert rec["privileges"] == "unprivileged"
        assert "exit_code" in rec and "error" in rec
        assert len(rec["evidence_sha256"]) == 64
    sections = report["sections"]
    assert sections["kernel"]["uname"].startswith("Linux 6.8.0")
    assert sections["systemd"]["failed_units"] == ["badsvc.service"]
    assert "failed_unit:badsvc.service" in report["findings"]
    assert sections["packages"]["count"] == 2
    assert isinstance(sections["memory"]["mem_total_bytes"], int)
    assert sections["filesystems"]
    assert sections["os_release"]["ID"]
    assert report["evidence"]
    assert lf.validate_report(report) is report


def test_redaction_removes_seeded_secret(mods):
    report, _ = _report(mods)
    blob = json.dumps(report)
    assert SEEDED_SECRET not in blob
    assert "hunter2" not in blob
    assert "/home/testuser" not in blob
    assert report["redactions_applied"] >= 2
    log_ev = [e for e in report["evidence"]
              if e["id"] == "logs.journal"][0]
    assert "<redacted>" in log_ev["excerpt"]
    assert "/home/<user>" in log_ev["excerpt"]


def test_read_only_guarantee_and_refusals(mods):
    lf = mods["lifthrasir"]
    report, runner = _report(mods)
    # every command the adapter actually invoked is allowlisted
    assert runner.calls, "adapter ran no commands"
    for argv in runner.calls:
        assert lf.is_read_only_command(argv)
    # mutating / unknown argv is refused by name, never run
    for bad in (["systemctl", "restart", "badsvc.service"],
                ["systemctl", "start", "x"],
                ["apt-get", "install", "x"],
                ["rm", "-rf", "/"],
                ["bash", "-c", "id"],
                ["uname", "-a", "--extra"]):
        assert not lf.is_read_only_command(bad)
        with pytest.raises(lf.LifthrasirError) as exc:
            lf.assert_read_only(bad)
        assert exc.value.name == "mutating_command_refused"


def test_diagnosis_is_not_repair_or_resolution(mods):
    lf = mods["lifthrasir"]
    report, _ = _report(mods)
    assert report["lifecycle"] == {
        "diagnosed": True, "repair_proposed": False,
        "repair_executed": False, "deployed": False,
        "verified_resolved": False}
    assert report["repair_executed"] is False
    assert report["deployment_performed"] is False
    proposal = lf.build_proposal(
        report, proposal_id="p1", kind="candidate_fix",
        summary="Restart nothing; investigate badsvc config",
        rationale="failed unit in evidence",
        candidate_change="edit /etc/badsvc.conf mode=0644",
        recorded_at="t1")
    assert proposal["schema"] == lf.PROPOSAL_SCHEMA
    assert proposal["executed"] is False
    assert proposal["status"] == "proposed-unexecuted"
    assert proposal["stage"] == "repair-proposed"
    assert proposal["lifecycle"]["repair_proposed"] is True
    assert proposal["lifecycle"]["repair_executed"] is False
    assert proposal["lifecycle"]["deployed"] is False
    assert proposal["lifecycle"]["verified_resolved"] is False
    assert proposal["report_id"] == report["report_id"]
    assert proposal["evidence_sha256"]
    assert proposal["requires_human_approval"] is True
    with pytest.raises(lf.LifthrasirError) as exc:
        lf.execute_proposal(proposal)
    assert exc.value.name == "execution_refused"


def test_privilege_recorded_truthfully_and_tamper_refused(mods):
    lf = mods["lifthrasir"]
    report, _ = _report(mods)
    tampered = json.loads(json.dumps(report))
    tampered["commands_executed"][0]["privileges"] = "root"
    with pytest.raises(lf.LifthrasirError):
        lf.validate_report(tampered)
    escalated = json.loads(json.dumps(report))
    escalated["lifecycle"]["repair_executed"] = True
    with pytest.raises(lf.LifthrasirError):
        lf.validate_report(escalated)
    mutated = json.loads(json.dumps(report))
    mutated["commands_executed"][0]["argv"] = [
        "systemctl", "restart", "x"]
    with pytest.raises(lf.LifthrasirError):
        lf.validate_report(mutated)


def test_unavailable_tools_and_drift_honesty(mods):
    lf = mods["lifthrasir"]

    def missing(argv, timeout_s):
        return None, "", "executable_not_found"

    report = lf.run_diagnostics(
        runner=missing, recorded_at="t0", hostname="h")
    assert report["sections"]["systemd"]["available"] is False
    assert report["sections"]["packages"]["available"] is False
    assert all(c["exit_code"] is None
               for c in report["commands_executed"])
    assert all(c["error"] == "executable_not_found"
               for c in report["commands_executed"])
    drift = report["sections"]["configuration_drift"]
    assert drift[0]["status"] == "baseline_not_supplied"
    report2, _ = _report(
        mods, expected_os={"ID": "definitely-not-this-os"})
    drift2 = report2["sections"]["configuration_drift"]
    assert any(d["status"] == "drift" for d in drift2)
    with pytest.raises(lf.LifthrasirError):
        lf.build_proposal(report2, proposal_id="p2",
                          kind="shell_command", summary="x")


class _Ctx:
    pass


def _run_cli(mods, argv):
    cli = mods["cli"]
    parser = argparse.ArgumentParser(prog="hermes")
    sub = parser.add_subparsers(dest="command")
    volmarr_parser = sub.add_parser("volmarr")
    cli.register_cli(volmarr_parser)
    args = parser.parse_args(argv)
    return cli.health_command(args, ctx=_Ctx())


def test_cli_lifthrasir_status(mods, capsys):
    lf = mods["lifthrasir"]
    rc = _run_cli(mods, ["volmarr", "lifthrasir", "status", "--json"])
    assert rc == 0
    record = json.loads(capsys.readouterr().out)
    assert record["service"] == "volmarr-lifthrasir"
    assert record["autonomous_features_claimed"] is False
    assert record["source_head_audited"] == lf.SOURCE_HEAD_AUDITED
    assert "GPL-2.0" in record["source_license"]
    rc2 = _run_cli(mods, ["volmarr", "lifthrasir"])
    assert rc2 == 2
    capsys.readouterr()
