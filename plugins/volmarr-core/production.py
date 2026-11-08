"""Q0-Q4 production seams: boundary, threat, evidence, status (W13).

Roadmap Part V (sections 25-29, Phases Q0-Q4), the section 28.3
evidence hierarchy, the section 30 W13 gate and the section 32
release scorecard. This slice is CONTRACT LEVEL, plugin-side only,
built on the banked seams (W08 integration ledger, W09 capability
bus). It is deliberately honest about its evidence stage:

- Q0: an account descriptor must keep ``agent_identity_id`` and
  ``credential_owner_id`` as distinct required fields; conflation
  is refused by name. A local-private packet routed to a non-local
  destination without a scoped, reversible, logged owner election
  is refused by name. Planted canaries are unretrievable through
  the public query path, audit records carry labels only (never
  payload text), and one agent inheriting another agent's scopes
  is refused by name.
- Q1: the section 26 threat checklist counts an item only with a
  named evidence reference; gaps are listed by name. Rendered
  receipts/audit/scorecard output is exact-value redacted, so a
  planted secret canary never appears in it.
- Q2: a performance/durability EVIDENCE RECORD STRUCTURE only.
  A percentile field without a measured value from a named
  benchmark log is ``unmeasured`` -- never estimated, never
  filled in. No benchmark is run or claimed by this slice.
- Q3: the section 28.3 promotion guard: promotion without the
  minimum proof for the target stage is refused by name, and a
  deferred/blocked stage is valid only with an explicit reason.
- Q4: production status aggregates the W08 ledger and the W09
  registry from disk; an engine is shown as working ONLY at the
  end-to-end-working or production-qualified stage -- unknown or
  unavailable engines are labelled honestly, never as working.
- Section 32: the release scorecard marks an item ``met`` only
  with a named evidence reference. ``releasable`` is True only
  when every item is met; the honest W13 outcome is NOT
  releasable, with the unmet/deferred set named.

No network, no subprocess, no credentials, no live services.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .capability_bus import result_envelope

SCHEMA = "runeforge.production.v1"
ACCOUNT_SCHEMA = "runeforge.account-descriptor.v1"
FLOW_SCHEMA = "runeforge.data-flow-audit.v1"
RECEIPT_SCHEMA = "runeforge.operator-receipt.v1"
THREAT_SCHEMA = "runeforge.threat-checklist.v1"
PERF_SCHEMA = "runeforge.performance-evidence.v1"
SCORECARD_SCHEMA = "runeforge.release-scorecard.v1"

PRODUCTION_DESCRIPTOR = {
    "schema": "runeforge.capability.v1",
    "service": "volmarr-production",
    "version": "0.26.0",
    "owner": "volmarr",
    "actions": ["read", "audit", "evaluate"],
    "transport": "in-process",
    "auth": "scoped",
    "side_effects": False,
    "privacy_classes": ["public", "shared", "local-private"],
    "availability": "contract-implemented",
    "timeout_ms": 2000,
}

LOCAL_DESTINATION = "local"


class ProductionError(Exception):
    """Named, honest production-seam failure."""

    def __init__(self, name: str, detail: str) -> None:
        super().__init__(detail)
        self.name = name
        self.detail = detail


# ------------------------------------------------------------------ Q0

def validate_account_descriptor(descriptor: Any) -> list[str]:
    """Named problems with an account descriptor ([] = valid).

    Section 25: ``agent_identity_id`` (who the agent is) and
    ``credential_owner_id`` (whose credentials/accounts are in
    use) are distinct required fields, independent of any display
    name and of the human owner's accounts. A descriptor that
    conflates them -- the same value in both fields -- is refused
    by name, never repaired silently.
    """
    problems: list[str] = []
    if not isinstance(descriptor, dict):
        return ["descriptor_not_an_object"]
    for field in ("agent_identity_id", "credential_owner_id"):
        if field not in descriptor:
            problems.append(f"missing_field:{field}")
        elif not isinstance(descriptor[field], str) or not descriptor[field].strip():
            problems.append(f"{field}_empty")
    if problems:
        return problems
    if descriptor["agent_identity_id"] == descriptor["credential_owner_id"]:
        problems.append(
            "account_identity_conflated:"
            "agent_identity_id==credential_owner_id")
    scopes = descriptor.get("scopes")
    if scopes is not None and (
        not isinstance(scopes, list)
        or not all(isinstance(s, str) and s.strip() for s in scopes)
    ):
        problems.append("scopes_invalid")
    return problems


def require_account_descriptor(descriptor: Any) -> dict:
    problems = validate_account_descriptor(descriptor)
    if problems:
        raise ProductionError("validation_failure", "; ".join(problems))
    return descriptor


def _election_complete(election: Any, destination: str) -> bool:
    """A scoped, reversible, logged owner election for one flow."""
    if not isinstance(election, dict):
        return False
    if election.get("scoped") is not True:
        return False
    if election.get("reversible") is not True:
        return False
    if election.get("logged") is not True:
        return False
    elected_by = election.get("elected_by") or election.get("owner")
    if not isinstance(elected_by, str) or not elected_by.strip():
        return False
    destinations = election.get("destinations")
    if destinations is not None and destination not in destinations:
        return False
    return True


def audit_data_flow(packet: Any, election: Any = None) -> dict[str, Any]:
    """Decide one data flow from its provenance/destination labels.

    Every packet carries a source privacy class and a destination.
    A local-private source routed to a non-local destination is
    refused by name (``q0_private_egress_refused:<destination>``)
    unless the owner has elected that flow with a scoped,
    reversible, logged election. Filters run here, before any
    request could be constructed -- never after it is sent.
    """
    if not isinstance(packet, dict):
        raise ProductionError("validation_failure", "packet_not_an_object")
    source = packet.get("source_class")
    destination = packet.get("destination")
    reasons: list[str] = []
    if not isinstance(source, str) or not source.strip():
        reasons.append("packet_label_missing:source_class")
    if not isinstance(destination, str) or not destination.strip():
        reasons.append("packet_label_missing:destination")
    if reasons:
        return {"allowed": False, "reasons": reasons,
                "source_class": source, "destination": destination}
    if source == "local-private" and destination != LOCAL_DESTINATION:
        if not _election_complete(election, destination):
            return {"allowed": False,
                    "reasons": [f"q0_private_egress_refused:{destination}"],
                    "source_class": source, "destination": destination}
    return {"allowed": True, "reasons": [],
            "source_class": source, "destination": destination}


class FlowLog:
    """Data-flow audit records: labels and decisions ONLY.

    Payload text is never copied into an audit record, so a
    secret carried in a packet cannot leak through the audit
    surface (section 26 secret-exposure control).
    """

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []

    def record(self, packet: Any, election: Any = None, *,
               recorded_at: str) -> dict[str, Any]:
        decision = audit_data_flow(packet, election)
        record = {
            "schema": FLOW_SCHEMA,
            "source_class": decision["source_class"],
            "destination": decision["destination"],
            "allowed": decision["allowed"],
            "reasons": list(decision["reasons"]),
            "recorded_at": recorded_at,
        }
        self._records.append(record)
        return record

    def records(self) -> list[dict[str, Any]]:
        return list(self._records)

    def external_flows(self) -> int:
        """Allowed flows that actually left this device."""
        return sum(1 for r in self._records
                   if r["allowed"] and r["destination"] != LOCAL_DESTINATION)


class CanaryStore:
    """Public/private document store for the section 25 canary.

    The public query path searches public documents ONLY: a
    planted local-private canary is unretrievable through it by
    construction, not by a filter applied after retrieval.
    """

    def __init__(self) -> None:
        self._public: dict[str, str] = {}
        self._private: dict[str, str] = {}

    def add_public(self, doc_id: str, text: str) -> None:
        self._public[str(doc_id)] = str(text)

    def add_private(self, doc_id: str, text: str) -> None:
        self._private[str(doc_id)] = str(text)

    def public_query(self, term: str) -> list[str]:
        return sorted(doc_id for doc_id, text in self._public.items()
                      if term in text)

    def local_query(self, term: str) -> list[str]:
        hits = [d for d, t in self._public.items() if term in t]
        hits += [d for d, t in self._private.items() if term in t]
        return sorted(hits)


def new_local_session() -> dict[str, Any]:
    """A fresh local-only session record (zero external requests)."""
    return {"mode": "local-only", "external_requests": 0, "destinations": []}


def record_session_request(session: dict[str, Any], destination: str) -> dict[str, Any]:
    """Record one would-be request; non-local destinations count.

    Embeddings, logging and model fallback all pass through this
    counter in the contract: any of them leaving the device in a
    local-only session makes the canary contract fail.
    """
    session.setdefault("destinations", []).append(destination)
    if destination != LOCAL_DESTINATION:
        session["external_requests"] = int(session.get("external_requests", 0)) + 1
    return session


def canary_contract(store: CanaryStore, canary: str, session: dict[str, Any]) -> dict[str, Any]:
    """Section 25 acceptance: canary hidden + zero external requests.

    The result names the canary only as ``planted-canary`` -- the
    canary text itself never appears in any rendered output.
    """
    if not canary or not str(canary).strip():
        raise ProductionError("validation_failure", "canary_required")
    retrievable = bool(store.public_query(canary))
    external = int(session.get("external_requests", 0))
    return {
        "schema": SCHEMA,
        "canary_label": "planted-canary",
        "canary_retrievable_via_public": retrievable,
        "external_requests": external,
        "passed": (not retrievable) and external == 0,
    }


OPERATOR_ACTIONS = ("disconnect", "export", "delete")


class OperatorBook:
    """Per-account disconnect/export/delete, recorded with receipts.

    Receipts carry metadata only (action, account, timestamp) --
    never document text, tokens or other payload content.
    """

    def __init__(self) -> None:
        self._receipts: list[dict[str, Any]] = []
        self._seq = 0

    def record(self, action: str, account_id: str, *,
               recorded_at: str) -> dict[str, Any]:
        if action not in OPERATOR_ACTIONS:
            raise ProductionError(
                "validation_failure", f"operator_action_unknown:{action}")
        if not account_id or not str(account_id).strip():
            raise ProductionError("validation_failure", "account_id_required")
        self._seq += 1
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "receipt_id": f"receipt-{self._seq:04d}",
            "action": action,
            "account_id": str(account_id),
            "recorded_at": recorded_at,
            "status": "recorded",
        }
        self._receipts.append(receipt)
        return receipt

    def receipts(self) -> list[dict[str, Any]]:
        return list(self._receipts)


def check_scope_inheritance(*, requester_agent_id: str,
                            source_agent_id: str, scope: str) -> dict[str, Any]:
    """One agent inheriting another's scopes is refused by name.

    Connected Drive/email/calendar are individually authorized
    scopes, not omniscient resources (section 25): an agent may
    use its OWN scopes, but silently inheriting a different
    agent's Drive/email/calendar scope is refused, always.
    """
    if not scope or not str(scope).strip():
        raise ProductionError("validation_failure", "scope_required")
    if requester_agent_id == source_agent_id:
        return {"allowed": True, "reasons": [], "scope": scope}
    return {"allowed": False,
            "reasons": [f"q0_scope_inheritance_refused:{scope}"],
            "scope": scope}


# ------------------------------------------------------------- rendering

def redact_text(text: str, secrets: Any = ()) -> str:
    """Exact-value redaction (section 26 control), applied on render."""
    out = str(text)
    for secret in secrets or ():
        if isinstance(secret, str) and secret:
            out = out.replace(secret, "[REDACTED]")
    return out


def render_json(payload: Any, secrets: Any = ()) -> str:
    """Render any production record; known secrets never appear."""
    return redact_text(json.dumps(payload, sort_keys=True, default=str), secrets)


def render_receipt(receipt: Any, secrets: Any = ()) -> str:
    return render_json(receipt, secrets)


def render_audit(records: Any, secrets: Any = ()) -> str:
    return render_json(records, secrets)


def render_scorecard(scorecard: Any, secrets: Any = ()) -> str:
    return render_json(scorecard, secrets)


# ------------------------------------------------------------------ Q1

THREAT_ITEMS = (
    "prompt_injection",
    "heading_role_impersonation",
    "path_escape_symlink_include",
    "malformed_utf8",
    "giant_file_dos",
    "supply_chain",
    "secret_exposure",
    "profile_leakage",
    "privilege_escalation",
    "egress",
    "wal_index_attacks",
    "replayed_capability_descriptors",
)

THREAT_DESCRIPTIONS = {
    "prompt_injection": "prompt injection from READMEs, rooms, web pages, imported Markdown and tool outputs",
    "heading_role_impersonation": "malicious heading/role metadata impersonating system authority",
    "path_escape_symlink_include": "path escapes, symlink swaps and Markdown includes",
    "malformed_utf8": "malformed UTF-8 inputs to loaders and transports",
    "giant_file_dos": "giant-file denial of service against bounded readers",
    "supply_chain": "dependency supply-chain attacks, unsigned plugins, package confusion, release substitution",
    "secret_exposure": "secret exposure via logs, previews, exports, telemetry or environment inheritance",
    "profile_leakage": "profile leakage during gateway switching, background tasks or host migration",
    "privilege_escalation": "command-execution privilege escalation, autonomous writes, unauthorized posts",
    "egress": "local audio activation, avatar camera/mic ownership and network egress",
    "wal_index_attacks": "database corruption, races, WAL desync and stale index pointer attacks",
    "replayed_capability_descriptors": "compromised external services and replayed signed capability descriptors",
}


def threat_checklist(evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    """Section 26 checklist: an item counts only with evidence.

    ``evidence`` maps a threat item to a named evidence reference
    (test or log). Anything else is a gap, listed by name -- the
    same evidence discipline as the W12 MimirAlloc gate.
    """
    evidence = evidence or {}
    items = []
    gaps = []
    for item in THREAT_ITEMS:
        ref = evidence.get(item)
        present = isinstance(ref, str) and bool(ref.strip())
        if not present:
            gaps.append(item)
        items.append({"item": item,
                      "description": THREAT_DESCRIPTIONS[item],
                      "present": present,
                      "evidence_ref": ref if present else None})
    return {"schema": THREAT_SCHEMA, "items": items,
            "present_count": len(THREAT_ITEMS) - len(gaps), "gaps": gaps}


def scan_rendered(outputs: Any, secret: str) -> dict[str, Any]:
    """Secret-scan contract over already-rendered output strings."""
    if not secret:
        raise ProductionError("validation_failure", "secret_canary_required")
    leaked = any(secret in str(out) for out in outputs)
    return {"leaked": leaked, "passed": not leaked}


# ------------------------------------------------------------------ Q2

PERF_METRICS = (
    "index_throughput",
    "query_latency",
    "persona_compile",
    "prompt_preparation",
    "first_token",
    "tool_invocation",
    "audio_latency",
    "gateway_restart_recovery",
)

PERF_DESCRIPTIONS = {
    "index_throughput": "corpus index throughput",
    "query_latency": "retrieval query latency",
    "persona_compile": "persona compile time",
    "prompt_preparation": "prompt preparation time",
    "first_token": "first-token time",
    "tool_invocation": "tool invocation latency",
    "audio_latency": "audio latency",
    "gateway_restart_recovery": "gateway restart recovery time",
}

COUNTER_FIELDS = (
    "cache_hit_ratio",
    "source_hash_generation",
    "section_count",
    "fts_size_bytes",
    "embedding_provider",
    "reindex_backlog",
    "receipt_store_size_bytes",
)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _metric_block(raw: Any) -> dict[str, Any]:
    """Measured only with p50/p95/p99 AND a named benchmark log."""
    if isinstance(raw, dict):
        log = raw.get("benchmark_log")
        if (_is_number(raw.get("p50")) and _is_number(raw.get("p95"))
                and _is_number(raw.get("p99"))
                and isinstance(log, str) and log.strip()):
            return {"status": "measured", "p50": raw["p50"],
                    "p95": raw["p95"], "p99": raw["p99"],
                    "benchmark_log": log}
    return {"status": "unmeasured", "p50": "unmeasured",
            "p95": "unmeasured", "p99": "unmeasured",
            "benchmark_log": None}


def _counter_block(raw: Any) -> dict[str, Any]:
    """A counter is measured only with a value AND a named source."""
    if isinstance(raw, dict):
        source = raw.get("source")
        value = raw.get("value")
        if (isinstance(source, str) and source.strip()
                and (_is_number(value) or (isinstance(value, str) and value.strip()))):
            return {"status": "measured", "value": value, "source": source}
    return {"status": "unmeasured", "value": "unmeasured", "source": None}


def performance_record(measurements: dict[str, Any] | None = None,
                       counters: dict[str, Any] | None = None) -> dict[str, Any]:
    """Q2 evidence record STRUCTURE only -- no benchmark is run here.

    Every section 27 metric carries P50/P95/P99 fields. A field
    without a measured value from a named benchmark log stays
    ``unmeasured``: missing percentiles are never estimated from
    the ones present, and partial measurements stay unmeasured.
    """
    measurements = measurements or {}
    counters = counters or {}
    metrics = {name: _metric_block(measurements.get(name)) for name in PERF_METRICS}
    counter_blocks = {name: _counter_block(counters.get(name)) for name in COUNTER_FIELDS}
    unmeasured = [n for n in PERF_METRICS if metrics[n]["status"] != "measured"]
    unmeasured += [n for n in COUNTER_FIELDS if counter_blocks[n]["status"] != "measured"]
    return {
        "schema": PERF_SCHEMA,
        "basis": "structure-only-no-benchmark-run-in-this-slice",
        "metrics": metrics,
        "counters": counter_blocks,
        "measured_count": (len(PERF_METRICS) + len(COUNTER_FIELDS)) - len(unmeasured),
        "unmeasured": unmeasured,
    }


# ------------------------------------------------------------------ Q3

# Section 28.3 evidence hierarchy, verbatim stage names and order.
EVIDENCE_STAGES = (
    "documented-only",
    "contract-implemented",
    "installed-integration",
    "end-to-end-working",
    "production-qualified",
)
DEFERRED_STAGE = "deferred/blocked"

# Minimum proof per stage, section 28.3 table, as named proof keys.
PROOF_REQUIREMENTS = {
    "documented-only": ("design_ref",),
    "contract-implemented": ("module_ref", "tests_ref"),
    "installed-integration": ("dependency_ref", "discovery_ref", "probe_ref"),
    "end-to-end-working": ("call_ref", "output_ref", "side_effects_ref", "failure_path_ref"),
    "production-qualified": ("security_ref", "persistence_ref", "performance_ref", "operating_limits_ref", "rollback_ref", "cross_platform_ref"),
}


def stage_rank(stage: str) -> int:
    """Rank in the 28.3 hierarchy; -1 for deferred/unknown stages."""
    if stage in EVIDENCE_STAGES:
        return EVIDENCE_STAGES.index(stage)
    return -1


def promotion_decision(current: str, target: str,
                       proofs: dict[str, Any] | None = None,
                       reason: str | None = None) -> dict[str, Any]:
    """Section 28.3 promotion guard: never promote by renaming.

    Promotion to a stage requires the minimum proof named for
    THAT stage; anything missing refuses the promotion by name.
    Moving to deferred/blocked is allowed only with an explicit
    reason, scope and reconsideration condition carried in
    ``reason``. Backward or same-stage moves are not promotions.
    """
    proofs = proofs or {}
    if current != DEFERRED_STAGE and current not in EVIDENCE_STAGES:
        return {"promoted": False, "allowed": False,
                "reasons": [f"evidence_stage_unknown:{current}"],
                "stage": current}
    if target == DEFERRED_STAGE:
        if isinstance(reason, str) and reason.strip():
            return {"promoted": False, "allowed": True, "deferred": True,
                    "reasons": [], "stage": DEFERRED_STAGE, "reason": reason}
        return {"promoted": False, "allowed": False,
                "reasons": ["deferred_reason_required"], "stage": current}
    if target not in EVIDENCE_STAGES:
        return {"promoted": False, "allowed": False,
                "reasons": [f"evidence_stage_unknown:{target}"],
                "stage": current}
    if stage_rank(target) <= stage_rank(current):
        return {"promoted": False, "allowed": False,
                "reasons": ["evidence_promotion_refused",
                            f"not_a_promotion:{current}->{target}"],
                "stage": current}
    missing = [key for key in PROOF_REQUIREMENTS[target]
               if not (isinstance(proofs.get(key), str) and proofs[key].strip())]
    if missing:
        return {"promoted": False, "allowed": False,
                "reasons": ["evidence_promotion_refused"]
                           + [f"proof_missing:{key}" for key in missing],
                "stage": current}
    return {"promoted": True, "allowed": True, "reasons": [], "stage": target}


# ------------------------------------------------------------------ Q4

DOCS_DELIVERABLES = (
    ("beginner_setup", ("docs/modernization/LAUNCH_RECIPE.md",)),
    ("migration", ("docs/modernization/MIGRATION_GUIDE.md", "MIGRATION.md")),
    ("threat_model", ("SECURITY.md",)),
    ("troubleshooting", ("docs/modernization/TROUBLESHOOTING.md", "TROUBLESHOOTING.md")),
    ("benchmark_instructions", ("docs/modernization/BENCHMARKS.md", "docs/modernization/BENCHMARK_INSTRUCTIONS.md")),
)

# Ledger stage spellings (W08 lock) that count as actually working.
WORKING_STAGES = frozenset({"end-to-end working", "production qualified"})


def repo_root(module_file: str | Path | None = None) -> Path:
    """Repository root for this plugin (plugins/volmarr-core -> root)."""
    return Path(module_file or __file__).resolve().parents[2]


def docs_deliverables(root: Path | None = None) -> list[dict[str, Any]]:
    """Section 29 docs list, each present/absent BY PATH from disk."""
    base = Path(root) if root is not None else repo_root()
    rows = []
    for name, candidates in DOCS_DELIVERABLES:
        found = next((c for c in candidates if (base / c).is_file()), None)
        rows.append({"deliverable": name, "present": found is not None,
                     "path": found if found is not None else candidates[0]})
    return rows


def _engines_block(engines_status: Any) -> dict[str, Any]:
    if not isinstance(engines_status, dict) or "engines" not in engines_status:
        return {"status": "unavailable", "reason": "ledger_status_unavailable",
                "engine_count": 0, "working_count": 0, "engines": []}
    rows = []
    for row in engines_status.get("engines") or []:
        stage = row.get("evidence_stage")
        rows.append({
            "name": row.get("name"),
            "evidence_stage": stage,
            "verification": row.get("verification"),
            "working": stage in WORKING_STAGES,
            "label": stage if isinstance(stage, str) and stage else "unknown",
        })
    return {"status": engines_status.get("status", "unknown"),
            "engine_count": len(rows),
            "working_count": sum(1 for r in rows if r["working"]),
            "engines": rows}


def _capabilities_block(capabilities_status: Any) -> dict[str, Any]:
    if not isinstance(capabilities_status, dict) or "services" not in capabilities_status:
        return {"status": "unavailable", "reason": "registry_status_unavailable",
                "service_count": 0, "services": []}
    rows = [{"service": s.get("service"), "version": s.get("version"),
             "availability": s.get("availability"),
             "working": s.get("availability") in ("proven-by-live-probe",)}
            for s in capabilities_status.get("services") or []]
    return {"status": capabilities_status.get("status", "unknown"),
            "service_count": len(rows), "services": rows}


def production_status(*, recorded_at: str, root: Path | None = None,
                      engines_status: Any = None,
                      capabilities_status: Any = None) -> dict[str, Any]:
    """Q4 aggregation from disk + W08 ledger + W09 registry.

    With no injected status, the live W08/W09 readers are used;
    any reader failure degrades that block to ``unavailable``
    with its reason named -- never to a fabricated working state.
    Nothing here claims a live connection.
    """
    if engines_status is None:
        try:
            from .integration_ledger import integration_status
            engines_status = integration_status()
        except Exception as exc:  # ledger missing/invalid: say so
            engines_status = {"status": "unavailable",
                              "reason": f"{type(exc).__name__}", "engines": []}
    if capabilities_status is None:
        try:
            from .capability_bus import builtin_status
            capabilities_status = builtin_status()
        except Exception as exc:
            capabilities_status = {"status": "unavailable",
                                   "reason": f"{type(exc).__name__}", "services": []}
    engines = _engines_block(engines_status)
    capabilities = _capabilities_block(capabilities_status)
    docs = docs_deliverables(root)
    missing_docs = [d["deliverable"] for d in docs if not d["present"]]
    if missing_docs:
        next_action = "author missing operator docs: " + ", ".join(missing_docs)
    elif engines["working_count"] == 0:
        next_action = "no engine is end-to-end working; production qualification remains open"
    else:
        next_action = "evaluate the section 32 release scorecard"
    return {
        "schema": SCHEMA,
        "service": PRODUCTION_DESCRIPTOR["service"],
        "version": PRODUCTION_DESCRIPTOR["version"],
        "availability": PRODUCTION_DESCRIPTOR["availability"],
        "engines": engines,
        "capabilities": capabilities,
        "docs": docs,
        "docs_present": len(docs) - len(missing_docs),
        "linked_profile": "unknown",
        "model_location": "unknown",
        "offline_status": "unknown",
        "live_connection": "not-claimed",
        "next_required_action": next_action,
        "recorded_at": recorded_at,
    }


# ------------------------------------------------------------- scorecard

SCORECARD_ITEMS = (
    "upstream_and_personal_revision_recorded",
    "readme_and_markdown_protected_backed_up",
    "no_artificial_size_cutoff",
    "persona_memory_byte_identity_tested",
    "gateway_prompts_contain_kernel_with_receipts",
    "isolation_tests_pass",
    "critical_security_tests_pass",
    "external_engines_installed_smoke_pass",
    "unavailable_engines_labelled_honestly",
    "offline_session_no_cloud_requests",
    "scoped_authorization_for_writes",
    "native_deploy_rollback_demonstrated",
    "performance_budgets_measured",
    "no_hidden_regressions",
    "docs_code_capability_agree",
)

SCORECARD_DESCRIPTIONS = {
    "upstream_and_personal_revision_recorded": "target upstream SHA/release and personal revision are recorded",
    "readme_and_markdown_protected_backed_up": "personal README and all source Markdown are protected and backed up",
    "no_artificial_size_cutoff": "source files have no artificial hard size cutoff in the persona corpus",
    "persona_memory_byte_identity_tested": "full persona/memory byte-identity tested under real upgrades and restores",
    "gateway_prompts_contain_kernel_with_receipts": "actual gateway prompts contain the pinned kernel and retrieved sections with receipts",
    "isolation_tests_pass": "cross-profile, cross-persona, remote and delegate isolation tests pass",
    "critical_security_tests_pass": "critical security tests pass, including secret/exfiltration and prompt-injection cases",
    "external_engines_installed_smoke_pass": "all enabled external engine versions have passing installed smoke tests",
    "unavailable_engines_labelled_honestly": "all disabled/unavailable/design-only engines are labeled honestly",
    "offline_session_no_cloud_requests": "offline-only session sends no cloud model, vector or telemetry request",
    "scoped_authorization_for_writes": "any file-write or high-impact action has correctly scoped authorization",
    "native_deploy_rollback_demonstrated": "native deploy/rollback is demonstrated on supported hardware",
    "performance_budgets_measured": "performance/energy budgets have reproducible measurements",
    "no_hidden_regressions": "no regressions remain hidden behind a test-environment explanation",
    "docs_code_capability_agree": "docs, code and actual capability matrix agree",
}

# Blockers known at W13, named honestly on the default scorecard.
KNOWN_DEFERRED = {
    "readme_and_markdown_protected_backed_up": "W00.03-ENC backup encryption open (owner key decision); backup exists unencrypted-local",
    "external_engines_installed_smoke_pass": "W08 ledger carries contract-only and documented-only rows; installed smoke has not passed for every enabled engine",
    "performance_budgets_measured": "W13/Q2 records structure only; no benchmark was run, every field unmeasured",
    "no_hidden_regressions": "7 live-transport contract failures remain open (section 28.2); no live Verdandi service on this host",
    "docs_code_capability_agree": "W00.05 fixture archive and W00.06 boundary review still open",
}


def evaluate_scorecard(evidence: dict[str, Any] | None = None,
                       deferred: dict[str, Any] | None = None) -> dict[str, Any]:
    """Section 32 evaluator: ``met`` only with a named reference.

    An item with a non-empty evidence reference is met; an item
    with a named deferral reason and no evidence is deferred;
    everything else is unmet, named. ``releasable`` is True ONLY
    when every one of the 15 items is met.
    """
    evidence = evidence or {}
    deferred = deferred or {}
    items = []
    unmet: list[str] = []
    deferred_list: list[str] = []
    for item in SCORECARD_ITEMS:
        ref = evidence.get(item)
        reason = deferred.get(item)
        if isinstance(ref, str) and ref.strip():
            items.append({"item": item, "status": "met", "verdict": "met",
                          "description": SCORECARD_DESCRIPTIONS[item],
                          "evidence_ref": ref, "reason": None})
        elif isinstance(reason, str) and reason.strip():
            verdict = f"deferred:{item}:{reason}"
            deferred_list.append(verdict)
            items.append({"item": item, "status": "deferred", "verdict": verdict,
                          "description": SCORECARD_DESCRIPTIONS[item],
                          "evidence_ref": None, "reason": reason})
        else:
            verdict = f"unmet:{item}"
            unmet.append(verdict)
            items.append({"item": item, "status": "unmet", "verdict": verdict,
                          "description": SCORECARD_DESCRIPTIONS[item],
                          "evidence_ref": None, "reason": None})
    met_count = sum(1 for i in items if i["status"] == "met")
    return {"schema": SCORECARD_SCHEMA, "items": items,
            "met_count": met_count, "unmet": unmet, "deferred": deferred_list,
            "releasable": met_count == len(SCORECARD_ITEMS)}


def production_audit(*, recorded_at: str,
                     threat_evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    """Audit aggregate: threat gaps + unmeasured perf + Q0 policy.

    Carried in a W09 provenance envelope (service
    volmarr-production, local-private): the audit shows what is
    proven and what is not, and nothing else.
    """
    audit = {
        "schema": SCHEMA,
        "threat": threat_checklist(threat_evidence),
        "performance": performance_record(),
        "q0_policy": {
            "private_egress_refusal": "q0_private_egress_refused:<destination>",
            "scope_inheritance_refusal": "q0_scope_inheritance_refused:<scope>",
            "account_fields_distinct": ["agent_identity_id", "credential_owner_id"],
        },
        "recorded_at": recorded_at,
    }
    return result_envelope(
        PRODUCTION_DESCRIPTOR, outputs=audit, source_ref="production-audit",
        recorded_at=recorded_at, confidentiality="local-private")
