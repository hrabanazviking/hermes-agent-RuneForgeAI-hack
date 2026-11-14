"""X.02 Lifthrasir read-only diagnostics bridge (roadmap section 37).

Roadmap section 37 (Part VII workstream 2 of 15) names
RuneForgeAI-Lifthrasir as a research-stage project: its README
states the planned autonomous Linux features are not yet
implemented. The X.02 audit (docs/modernization/
X02_LIFTHRASIR_WORKSTREAM.md, 2026-11-14) re-measured the repo at
69fb1ed99cb2: the tree now also carries real executable Python
from its own separate campaign (src/lifthrasir, lab collectors,
a read-only Phase 2 host observer on another machine) -- but
Phase 3 host repairs and Phase 4 upstream delivery have not
started there, there is no installable package (no
pyproject/setup.py), no tag and no release, and its license is
GPL-2.0-only. No Lifthrasir code is incorporated into this fork;
no pin is taken. This module is original volmarr-core code
written against the section 37 contract, plugin-side only.

What this slice builds, honestly scoped to section 37 items
1-3 and 7 (research track first):

- a READ-ONLY diagnostics adapter for the local host: systemd
  service health, bounded journal logs, kernel version,
  filesystems, installed package metadata, low-memory
  telemetry and known configuration drift (only against a
  caller-supplied baseline; drift is never guessed). Every
  command comes from a fixed allowlist of read-only argv
  vectors, runs unprivileged with no shell, and any argv not
  on the allowlist is refused by name before it can run;
- a machine-readable DiagnosticReport contract
  (runeforge.lifthrasir.diagnostic-report.v1): commands
  executed, privileges used, error codes, captured evidence
  (sha256 over the REDACTED capture), timestamps, and
  redaction applied by rule (secret assignments, bearer
  tokens, token shapes, private keys and /home/<user> paths
  are redacted before anything is recorded);
- a proposal-only layer: from a validated report, Hermes may
  record an explanation, a candidate fix or an upstream bug
  report -- each explicitly marked unexecuted, requiring
  human approval. There is NO repair execution, NO deployment
  and NO autonomous system modification in this slice:
  execute_proposal refuses by name, always (section 37 items
  4-5 are a later lab slice, ticket X02-T1);
- the section 37.7 separation is structural in the data
  model: every record carries a lifecycle map distinguishing
  diagnosed / repair-proposed / repair-executed / deployed /
  verified-resolved, and a report can only ever assert
  "diagnosed".

No network, no root escalation, no mutation anywhere.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
from typing import Any, Callable

SCHEMA_PREFIX = "runeforge.lifthrasir"
REPORT_SCHEMA = f"{SCHEMA_PREFIX}.diagnostic-report.v1"
PROPOSAL_SCHEMA = f"{SCHEMA_PREFIX}.repair-proposal.v1"
SOURCE_PROJECT = "RuneForgeAI-Lifthrasir"
SOURCE_REPO = "hrabanazviking/RuneForgeAI-Lifthrasir"
SOURCE_HEAD_AUDITED = "69fb1ed99cb238cacd9f35c057c6936137041724"
SOURCE_LICENSE = ("GPL-2.0-only (LICENSE text verified X.02, "
                  "2026-11-14, sha256 8177f9751321)")
PRIVILEGE_UNPRIVILEGED = "unprivileged"
STAGE_DIAGNOSED = "diagnosed"
STAGE_REPAIR_PROPOSED = "repair-proposed"
STAGES = (STAGE_DIAGNOSED, STAGE_REPAIR_PROPOSED, "repair-executed",
          "deployed", "verified-resolved")
PROPOSAL_KINDS = frozenset(
    {"explanation", "candidate_fix", "upstream_bug_report"})
MAX_EXCERPT_CHARS = 2000
MAX_PACKAGES_RECORDED = 200
COMMAND_TIMEOUT_S = 10.0

DESCRIPTOR = {
    "schema": "runeforge.capability.v1",
    "service": "volmarr-lifthrasir",
    "version": "0.26.0",
    "owner": "volmarr",
    "actions": ["read", "diagnose", "propose"],
    "transport": "in-process",
    "auth": "scoped",
    "side_effects": False,
    "privacy_classes": ["local-private"],
    "availability": "contract-implemented",
    "timeout_ms": 10000,
}


class LifthrasirError(Exception):
    """Named refusal: malformed record or policy denial."""

    def __init__(self, name: str, detail: str) -> None:
        super().__init__(f"{name}: {detail}")
        self.name = name
        self.detail = detail


# ------------------------------------------------------------ allowlist

def _cmd(cid: str, argv: list, section: str, purpose: str) -> dict:
    return {"id": cid, "argv": list(argv), "section": section,
            "purpose": purpose}


READ_ONLY_COMMANDS = (
    _cmd("host.hostname", ["hostname"], "host",
         "local host name"),
    _cmd("kernel.uname", ["uname", "-srm"], "kernel",
         "kernel name, release and machine"),
    _cmd("systemd.failed",
         ["systemctl", "--no-pager", "--failed", "--plain",
          "--no-legend"], "systemd",
         "failed unit list (read-only query)"),
    _cmd("systemd.version", ["systemctl", "--version"], "systemd",
         "systemd version (read-only query)"),
    _cmd("logs.journal",
         ["journalctl", "--no-pager", "-n", "50", "-p", "warning",
          "-o", "short-iso"], "logs",
         "bounded recent journal at warning priority and above"),
    _cmd("packages.dpkg",
         ["dpkg-query", "-W", "-f=${Package} ${Version}\n"],
         "packages",
         "installed package metadata (dpkg database query)"),
)

_COMMAND_BY_ARGV = {tuple(c["argv"]): c for c in READ_ONLY_COMMANDS}


def is_read_only_command(argv: Any) -> bool:
    """True only for an exact allowlisted read-only argv vector."""
    if not isinstance(argv, (list, tuple)) or not argv:
        return False
    if not all(isinstance(a, str) for a in argv):
        return False
    return tuple(argv) in _COMMAND_BY_ARGV


def assert_read_only(argv: Any) -> list:
    """Return the argv as a list, or refuse by name. The adapter
    can only ever run allowlisted read-only commands; anything
    else -- mutating verbs, shells, unknown tools -- is refused
    before execution is even attempted."""
    if not is_read_only_command(argv):
        raise LifthrasirError(
            "mutating_command_refused",
            f"argv {argv!r} is not on the read-only allowlist; "
            "this adapter never executes mutating or unknown "
            "commands (section 37 item 1 is read-only)")
    return list(argv)


# ------------------------------------------------------------ redaction

_REDACTION_RULES = (
    (re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?"
                r"-----END [A-Z0-9 ]*PRIVATE KEY-----", re.S),
     "<redacted:private-key>"),
    (re.compile(r"(?i)\b(password|passwd|pwd|token|secret|"
                r"api[_-]?key|access[_-]?key|authorization)\b"
                r"(\s*[:=]\s*)\S+"),
     r"\1\2<redacted>"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-+/=]+"),
     "Bearer <redacted>"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "<redacted>"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "<redacted>"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "<redacted>"),
    (re.compile(r"/home/[^/\s:'\"]+"), "/home/<user>"),
)


def redact_text(text: str) -> tuple:
    """Apply every redaction rule; return (clean_text, count)."""
    count = 0
    out = text
    for pattern, replacement in _REDACTION_RULES:
        out, n = pattern.subn(replacement, out)
        count += n
    return out, count


# ------------------------------------------------------------ runners

Runner = Callable[[list, float], tuple]


def _default_runner(argv: list, timeout_s: float) -> tuple:
    """Run one allowlisted argv, no shell, unprivileged.
    Returns (exit_code|None, stdout, error_string)."""
    try:
        proc = subprocess.run(argv, capture_output=True, text=True,
                              timeout=timeout_s, check=False)
        return proc.returncode, proc.stdout or "", ""
    except FileNotFoundError:
        return None, "", "executable_not_found"
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        return None, out, "timeout"
    except OSError as exc:
        return None, "", f"os_error:{exc.errno}"


def _read_text(path: str, limit: int = 65536):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read(limit)
    except OSError:
        return None


def _parse_kv_lines(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            out[key.strip()] = value.strip().strip('"')
    return out


def _parse_meminfo(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].endswith(":"):
            try:
                out[parts[0][:-1]] = int(parts[1]) * 1024
            except ValueError:
                continue
    return out


def _lifecycle(**overrides: bool) -> dict:
    state = {"diagnosed": False, "repair_proposed": False,
             "repair_executed": False, "deployed": False,
             "verified_resolved": False}
    state.update(overrides)
    return state


# ------------------------------------------------------------ diagnostics

def run_diagnostics(*, runner: Runner = None, recorded_at: str = "",
                    hostname: str = None,
                    expected_os: dict = None) -> dict:
    """Collect a DiagnosticReport from THIS host, read-only.

    Every command is allowlist-checked before it runs; file
    probes read /proc and /etc/os-release directly. The report
    asserts stage "diagnosed" and nothing beyond it.
    """
    runner = runner or _default_runner
    host = hostname or platform.node() or "unknown"
    commands: list = []
    evidence: list = []
    redactions = 0

    def _evidence(eid: str, kind: str, raw: str) -> dict:
        nonlocal redactions
        clean, n = redact_text(raw)
        redactions += n
        return {"id": eid, "kind": kind,
                "sha256": hashlib.sha256(
                    clean.encode("utf-8")).hexdigest(),
                "bytes": len(clean.encode("utf-8")),
                "excerpt": clean[:MAX_EXCERPT_CHARS]}

    def _run(entry: dict) -> tuple:
        argv = assert_read_only(entry["argv"])
        rc, out, err = runner(argv, COMMAND_TIMEOUT_S)
        ev = _evidence(entry["id"], "command-output", out)
        evidence.append(ev)
        commands.append({
            "id": entry["id"], "argv": argv,
            "section": entry["section"], "purpose": entry["purpose"],
            "read_only": True,
            "privileges": PRIVILEGE_UNPRIVILEGED,
            "exit_code": rc, "error": err if rc is None else "",
            "evidence_sha256": ev["sha256"],
            "recorded_at": recorded_at})
        return rc, out

    by_id = {c["id"]: c for c in READ_ONLY_COMMANDS}
    _, uname_out = _run(by_id["kernel.uname"])
    _run(by_id["host.hostname"])
    rc_failed, failed_out = _run(by_id["systemd.failed"])
    _run(by_id["systemd.version"])
    rc_logs, logs_out = _run(by_id["logs.journal"])
    rc_pkg, pkg_out = _run(by_id["packages.dpkg"])

    failed_units = []
    if rc_failed == 0:
        for line in failed_out.splitlines():
            parts = line.split()
            if parts:
                failed_units.append(parts[0])

    pkg_lines = [ln for ln in pkg_out.splitlines() if ln.strip()]
    packages = {"available": rc_pkg == 0,
                "count": len(pkg_lines) if rc_pkg == 0 else 0,
                "recorded": pkg_lines[:MAX_PACKAGES_RECORDED],
                "truncated": len(pkg_lines) > MAX_PACKAGES_RECORDED}

    mem_raw = _read_text("/proc/meminfo") or ""
    evidence.append(_evidence("memory.meminfo", "file-read", mem_raw))
    mem = _parse_meminfo(mem_raw)
    pressure_raw = _read_text("/proc/pressure/memory") or ""
    if pressure_raw:
        evidence.append(
            _evidence("memory.pressure", "file-read", pressure_raw))
    pressure = {}
    for line in pressure_raw.splitlines():
        parts = line.split()
        if parts and parts[0] in ("some", "full"):
            for kv in parts[1:]:
                if "=" in kv:
                    k, _, v = kv.partition("=")
                    pressure[f"{parts[0]}_{k}"] = v

    mounts_raw = _read_text("/proc/mounts") or ""
    evidence.append(
        _evidence("filesystems.mounts", "file-read", mounts_raw))
    filesystems = []
    for line in mounts_raw.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] in ("/", "/home", "/boot",
                                            "/var", "/tmp"):
            entry_fs = {"device": parts[0], "mountpoint": parts[1],
                        "fstype": parts[2]}
            try:
                usage = shutil.disk_usage(parts[1])
                entry_fs["free_bytes"] = usage.free
                entry_fs["total_bytes"] = usage.total
            except OSError:
                entry_fs["free_bytes"] = "unknown"
                entry_fs["total_bytes"] = "unknown"
            filesystems.append(entry_fs)

    os_raw = _read_text("/etc/os-release") or ""
    evidence.append(_evidence("host.os-release", "file-read", os_raw))
    os_release = _parse_kv_lines(os_raw)
    os_view = {k: os_release.get(k, "unknown")
               for k in ("ID", "VERSION_ID", "PRETTY_NAME")}

    drift = []
    if expected_os:
        for key in ("ID", "VERSION_ID"):
            if key in expected_os:
                observed = os_release.get(key)
                if observed != expected_os[key]:
                    drift.append({
                        "check": f"os-release.{key}",
                        "status": "drift",
                        "expected": expected_os[key],
                        "observed": observed or "unknown"})
        if not drift:
            drift.append({"check": "os-release",
                          "status": "matches_baseline"})
    else:
        drift.append({
            "check": "os-release-baseline",
            "status": "baseline_not_supplied",
            "detail": "drift is reported only against a "
                      "caller-supplied baseline; none was "
                      "supplied, so no drift is guessed"})

    findings = [f"failed_unit:{u}" for u in failed_units]
    findings += [f"drift:{d['check']}" for d in drift
                 if d["status"] == "drift"]
    mem_avail = mem.get("MemAvailable")
    mem_total = mem.get("MemTotal")
    if (isinstance(mem_avail, int) and isinstance(mem_total, int)
            and mem_total > 0 and mem_avail < mem_total // 10):
        findings.append("low_memory: MemAvailable under 10% "
                        "of MemTotal")

    digest_src = "|".join(
        [host, recorded_at] + [e["sha256"] for e in evidence])
    report_id = "diag-" + hashlib.sha256(
        digest_src.encode("utf-8")).hexdigest()[:16]

    return {
        "schema": REPORT_SCHEMA,
        "source_project": SOURCE_PROJECT,
        "privacy_zone": "local-private",
        "report_id": report_id,
        "host": {"hostname": host, "scope": "local-host-only"},
        "stage": STAGE_DIAGNOSED,
        "lifecycle": _lifecycle(diagnosed=True),
        "started_at": recorded_at,
        "finished_at": recorded_at,
        "privileges_used": [PRIVILEGE_UNPRIVILEGED],
        "commands_executed": commands,
        "sections": {
            "kernel": {"uname": uname_out.strip() or "unknown"},
            "systemd": {"available": rc_failed is not None,
                        "failed_units": failed_units},
            "logs": {"available": rc_logs == 0,
                     "lines_captured": len(
                         logs_out.splitlines()) if rc_logs == 0 else 0},
            "packages": packages,
            "memory": {
                "mem_total_bytes": mem_total if mem_total
                is not None else "unknown",
                "mem_available_bytes": mem_avail if mem_avail
                is not None else "unknown",
                "pressure": pressure},
            "filesystems": filesystems,
            "os_release": os_view,
            "configuration_drift": drift},
        "evidence": evidence,
        "redactions_applied": redactions,
        "findings": findings,
        "repair_executed": False,
        "deployment_performed": False,
    }


def validate_report(report: Any) -> dict:
    """Strict contract check; a report may only ever assert the
    diagnosed stage -- any claim of execution, deployment or
    resolution inside a report is malformed by definition."""
    if not isinstance(report, dict):
        raise LifthrasirError("report_malformed", "report not a dict")
    if report.get("schema") != REPORT_SCHEMA:
        raise LifthrasirError("report_malformed", "wrong schema")
    if report.get("stage") != STAGE_DIAGNOSED:
        raise LifthrasirError(
            "report_malformed",
            "a DiagnosticReport stage is always 'diagnosed' "
            "(section 37.7 separation)")
    lifecycle = report.get("lifecycle")
    if not isinstance(lifecycle, dict) or not lifecycle.get("diagnosed"):
        raise LifthrasirError("report_malformed", "lifecycle.diagnosed")
    for key in ("repair_executed", "deployed", "verified_resolved"):
        if lifecycle.get(key):
            raise LifthrasirError(
                "report_malformed",
                f"lifecycle.{key} claimed inside a report")
    if report.get("repair_executed") or report.get(
            "deployment_performed"):
        raise LifthrasirError(
            "report_malformed", "report claims execution/deployment")
    for field in ("report_id", "started_at", "evidence"):
        if field not in report:
            raise LifthrasirError("report_malformed", f"missing {field}")
    for rec in report.get("commands_executed", []):
        if rec.get("read_only") is not True:
            raise LifthrasirError(
                "report_malformed", "command not marked read_only")
        if rec.get("privileges") != PRIVILEGE_UNPRIVILEGED:
            raise LifthrasirError(
                "report_malformed", "privilege not recorded truthfully")
        if "exit_code" not in rec:
            raise LifthrasirError(
                "report_malformed", "command missing exit_code")
        assert_read_only(rec.get("argv"))
    return report


# ------------------------------------------------------------ proposals

def build_proposal(report: dict, *, proposal_id: str, kind: str,
                   summary: str, rationale: str = "",
                   candidate_change: str = "",
                   recorded_at: str = "") -> dict:
    """Record one proposal from a validated report. Proposals
    are evidence-linked and explicitly unexecuted; this slice
    has no execution path at all."""
    validate_report(report)
    if kind not in PROPOSAL_KINDS:
        raise LifthrasirError(
            "proposal_malformed", f"kind {kind!r} not classified")
    if not proposal_id or not summary:
        raise LifthrasirError(
            "proposal_malformed", "proposal_id and summary required")
    clean_summary, _ = redact_text(summary)
    clean_rationale, _ = redact_text(rationale)
    clean_change, _ = redact_text(candidate_change)
    return {
        "schema": PROPOSAL_SCHEMA,
        "source_project": SOURCE_PROJECT,
        "privacy_zone": "local-private",
        "proposal_id": proposal_id,
        "kind": kind,
        "summary": clean_summary,
        "rationale": clean_rationale,
        "candidate_change": clean_change,
        "report_id": report["report_id"],
        "evidence_sha256": [e["sha256"]
                            for e in report.get("evidence", [])],
        "stage": STAGE_REPAIR_PROPOSED,
        "lifecycle": _lifecycle(diagnosed=True, repair_proposed=True),
        "executed": False,
        "status": "proposed-unexecuted",
        "requires_human_approval": True,
        "recorded_at": recorded_at,
    }


def execute_proposal(proposal: dict) -> dict:
    """Refused by name, always: prototype repair and rollback
    belong to a later disposable-lab slice (section 37 items
    4-5, ticket X02-T1). No autonomous system modification
    exists in this slice."""
    raise LifthrasirError(
        "execution_refused",
        "Lifthrasir proposals are never executed by this slice; "
        "repair prototyping is ticket X02-T1 (disposable lab) "
        "and deployment is out of scope (section 37)")


def lifthrasir_status(*, recorded_at: str = "") -> dict:
    return {
        "schema": f"{SCHEMA_PREFIX}.status.v1",
        "service": DESCRIPTOR["service"],
        "version": DESCRIPTOR["version"],
        "availability": "contract-implemented",
        "source_repo": SOURCE_REPO,
        "source_head_audited": SOURCE_HEAD_AUDITED,
        "source_license": SOURCE_LICENSE,
        "scope": "read-only local diagnostics + proposal-only "
                 "layer; no repair, no deployment",
        "autonomous_features_claimed": False,
        "repair_execution": "not implemented (X02-T1)",
        "rollback": "not implemented (X02-T1)",
        "recorded_at": recorded_at,
    }
