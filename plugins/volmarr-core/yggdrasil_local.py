"""X.01 Yggdrasil local-host prototype: envelopes, discovery, placement.

Roadmap section 36 (Part VII workstream 1 of 15) names the
Yggdrasil Distributed Inference System as a design-phase
architecture proposal whose node agents, scheduler, transport,
registry and model adapters are to be evaluated as design
contracts until a working implementation is proven. The X.01
audit (docs/modernization/X01_YGGDRASIL_WORKSTREAM.md) found the
source repo carries a large real Python library (Parts I-II of
its own campaign banked) whose mesh behaviour is nevertheless
proven only in-process/simulated: no host-to-host live proof
exists, so NO working mesh is claimed here (section 36
deliverable 10).

This slice is the honestly buildable local part, plugin-side in
volmarr-core (personal code in plugins, never core):

- versioned envelopes NodeCapability, TaskRequest,
  PlacementDecision, TaskLease, TaskOutcome, EvidenceReceipt,
  each carrying source/project identity and a privacy zone,
  validated strictly and refused by name when malformed;
- a READ-ONLY local-host discovery prototype: processor, RAM,
  disk and load are read from local /proc + stdlib sources;
  accelerator, available models, supported context lengths and
  peer topology are reported ONLY from an explicit caller probe
  mapping -- absent a probe value they stay "unknown", never
  guessed, never estimated. No peer discovery, no socket, no
  network anywhere in this module;
- placement as a pure function over measured/probe values and
  policy: local-host only, wrong-owner refusal, budget
  enforcement, and any non-local destination refused by name
  (no accidental cloud egress; encrypted peer channels are a
  future separately-authorized step, section 36 deliverable 5);
- task lifecycle ownership stays with Hermes: a lease here is a
  local record mapped onto Hermes cron/gateway session
  ownership -- this module introduces NO second scheduler and
  executes nothing.

No network, no subprocess, no mutation outside caller-owned
records.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
from typing import Any

SCHEMA_PREFIX = "runeforge.yggdrasil"
CAPABILITY_SCHEMA = f"{SCHEMA_PREFIX}.node-capability.v1"
TASK_REQUEST_SCHEMA = f"{SCHEMA_PREFIX}.task-request.v1"
PLACEMENT_SCHEMA = f"{SCHEMA_PREFIX}.placement-decision.v1"
LEASE_SCHEMA = f"{SCHEMA_PREFIX}.task-lease.v1"
OUTCOME_SCHEMA = f"{SCHEMA_PREFIX}.task-outcome.v1"
RECEIPT_SCHEMA = f"{SCHEMA_PREFIX}.evidence-receipt.v1"
SOURCE_PROJECT = "Yggdrasil-Distributed-Inference-System"
SOURCE_REPO = "hrabanazviking/Yggdrasil-Distributed-Inference-System"
SOURCE_HEAD_AUDITED = "1af750f1ad2fb7b3f39776f7cefb56a68359772a"
PRIVACY_ZONES = frozenset({"local-private", "shared", "public"})
UNKNOWN = "unknown"

DESCRIPTOR = {
    "schema": "runeforge.capability.v1",
    "service": "volmarr-yggdrasil-local",
    "version": "0.26.0",
    "owner": "volmarr",
    "actions": ["read", "discover", "place"],
    "transport": "in-process",
    "auth": "scoped",
    "side_effects": False,
    "privacy_classes": ["local-private", "shared", "public"],
    "availability": "contract-implemented",
    "timeout_ms": 2000,
}


class YggdrasilLocalError(Exception):
    """Named refusal: malformed envelope or policy denial."""

    def __init__(self, name: str, detail: str) -> None:
        super().__init__(f"{name}: {detail}")
        self.name = name
        self.detail = detail


def _require(mapping: Any, field: str, kind: type, env: str) -> Any:
    if not isinstance(mapping, dict) or field not in mapping:
        raise YggdrasilLocalError(
            "envelope_malformed", f"{env}: missing field {field!r}")
    value = mapping[field]
    if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
        raise YggdrasilLocalError(
            "envelope_malformed", f"{env}: field {field!r} has wrong type")
    return value


def _identity(mapping: dict[str, Any], env: str) -> tuple[str, str]:
    source = _require(mapping, "source_project", str, env)
    zone = _require(mapping, "privacy_zone", str, env)
    if zone not in PRIVACY_ZONES:
        raise YggdrasilLocalError(
            "envelope_malformed", f"{env}: privacy_zone {zone!r} not classified")
    return source, zone


def _meminfo() -> dict[str, int]:
    out: dict[str, int] = {}
    try:
        with open("/proc/meminfo", encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) >= 2 and parts[0].endswith(":"):
                    try:
                        out[parts[0][:-1]] = int(parts[1]) * 1024
                    except ValueError:
                        continue
    except OSError:
        pass
    return out


def discover_local_node(*, probes: dict[str, Any] | None = None,
                        recorded_at: str = "") -> dict[str, Any]:
    """Read-only NodeCapability for THIS host only.

    Measured locally: processor, architecture, core count, RAM,
    disk, load. Probe-only (else "unknown"): accelerator,
    models, context lengths, peer topology.
    """
    probes = probes or {}
    mem = _meminfo()
    try:
        load1 = round(os.getloadavg()[0], 3)
    except (OSError, AttributeError):
        load1 = None
    try:
        disk_free = shutil.disk_usage("/").free
    except OSError:
        disk_free = None
    models_probe = probes.get("models")
    models: Any = UNKNOWN
    contexts: Any = UNKNOWN
    if isinstance(models_probe, list):
        models = [str(m) for m in models_probe]
        ctx = probes.get("context_lengths")
        contexts = dict(ctx) if isinstance(ctx, dict) else UNKNOWN
    health = {
        "meminfo_readable": bool(mem),
        "load_readable": load1 is not None,
        "disk_readable": disk_free is not None,
        "probe_supplied": bool(probes),
    }
    return {
        "schema": CAPABILITY_SCHEMA,
        "source_project": SOURCE_PROJECT,
        "privacy_zone": "local-private",
        "node_id": str(probes.get("node_id") or platform.node() or UNKNOWN),
        "scope": "local-host-only",
        "processor": platform.processor() or platform.machine() or UNKNOWN,
        "architecture": platform.machine() or UNKNOWN,
        "cpu_cores": os.cpu_count() or UNKNOWN,
        "ram_total_bytes": mem.get("MemTotal", UNKNOWN),
        "ram_available_bytes": mem.get("MemAvailable", UNKNOWN),
        "disk_free_bytes": disk_free if disk_free is not None else UNKNOWN,
        "load_average_1m": load1 if load1 is not None else UNKNOWN,
        "accelerator": probes.get("accelerator", UNKNOWN),
        "models": models,
        "context_lengths": contexts,
        "network_topology": {
            "scope": "local-host-only",
            "peers": UNKNOWN,
            "peer_discovery": "not-implemented (X01-T1)",
        },
        "health": health,
        "mesh_claimed": False,
        "live_peers": 0,
        "recorded_at": recorded_at,
    }


def validate_capability(cap: dict[str, Any]) -> dict[str, Any]:
    if _require(cap, "schema", str, "NodeCapability") != CAPABILITY_SCHEMA:
        raise YggdrasilLocalError(
            "envelope_malformed", "NodeCapability: wrong schema")
    _identity(cap, "NodeCapability")
    _require(cap, "node_id", str, "NodeCapability")
    return cap


def build_task_request(*, request_id: str, owner: str, model: str,
                       est_tokens: int, est_seconds: int,
                       budget_tokens: int, budget_seconds: int,
                       required_ram_bytes: int = 0,
                       requires_accelerator: bool = False,
                       destination: str = "local",
                       privacy_zone: str = "local-private",
                       recorded_at: str = "") -> dict[str, Any]:
    if not request_id or not owner or not model:
        raise YggdrasilLocalError(
            "envelope_malformed",
            "TaskRequest: request_id, owner and model are required")
    if privacy_zone not in PRIVACY_ZONES:
        raise YggdrasilLocalError(
            "envelope_malformed",
            f"TaskRequest: privacy_zone {privacy_zone!r} not classified")
    for label, value in (("est_tokens", est_tokens),
                         ("est_seconds", est_seconds),
                         ("budget_tokens", budget_tokens),
                         ("budget_seconds", budget_seconds),
                         ("required_ram_bytes", required_ram_bytes)):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise YggdrasilLocalError(
                "envelope_malformed", f"TaskRequest: {label} must be int >= 0")
    return {
        "schema": TASK_REQUEST_SCHEMA,
        "source_project": SOURCE_PROJECT,
        "privacy_zone": privacy_zone,
        "request_id": request_id,
        "owner": owner,
        "model": model,
        "est_tokens": est_tokens,
        "est_seconds": est_seconds,
        "budget_tokens": budget_tokens,
        "budget_seconds": budget_seconds,
        "required_ram_bytes": required_ram_bytes,
        "requires_accelerator": bool(requires_accelerator),
        "destination": destination,
        "recorded_at": recorded_at,
    }


def validate_task_request(req: dict[str, Any]) -> dict[str, Any]:
    if _require(req, "schema", str, "TaskRequest") != TASK_REQUEST_SCHEMA:
        raise YggdrasilLocalError(
            "envelope_malformed", "TaskRequest: wrong schema")
    _identity(req, "TaskRequest")
    for field in ("request_id", "owner", "model", "destination"):
        _require(req, field, str, "TaskRequest")
    for field in ("est_tokens", "est_seconds", "budget_tokens",
                  "budget_seconds", "required_ram_bytes"):
        _require(req, field, int, "TaskRequest")
    return req


def place_task(capability: dict[str, Any], request: dict[str, Any], *,
               caller: str, measured_latency_ms: float | None = None,
               latency_budget_ms: float | None = None,
               recorded_at: str = "") -> dict[str, Any]:
    """Pure local placement. Refusals are named decisions, not errors,
    except wrong-owner and malformed envelopes, which raise."""
    validate_capability(capability)
    validate_task_request(request)
    if caller != request["owner"]:
        raise YggdrasilLocalError(
            "wrong_owner",
            f"caller {caller!r} does not own request {request['request_id']!r}")
    reasons: list[str] = []
    if request["destination"] != "local":
        reasons.append("egress_not_authorized: local-host scheduling only; "
                       "non-local placement is a future separately "
                       "authorized step (section 36 deliverable 5)")
    if request["privacy_zone"] == "local-private" and request["destination"] != "local":
        reasons.append("cloud_egress_refused: local-private data never "
                       "leaves this host in this slice")
    if request["est_tokens"] > request["budget_tokens"]:
        reasons.append("budget_exceeded: est_tokens over budget_tokens")
    if request["est_seconds"] > request["budget_seconds"]:
        reasons.append("budget_exceeded: est_seconds over budget_seconds")
    avail = capability.get("ram_available_bytes")
    if request["required_ram_bytes"]:
        if avail == UNKNOWN or not isinstance(avail, int):
            reasons.append("capability_unknown: ram_available_bytes unknown; "
                           "a memory-bound task is never guessed placeable")
        elif request["required_ram_bytes"] > avail:
            reasons.append("insufficient_memory: required over available")
    models = capability.get("models")
    if models == UNKNOWN:
        reasons.append("capability_unknown: model catalogue unknown; "
                       "placement is never guessed")
    elif isinstance(models, list) and request["model"] not in models:
        reasons.append(f"model_unavailable: {request['model']!r} not on this node")
    contexts = capability.get("context_lengths")
    if isinstance(contexts, dict) and request["model"] in contexts:
        limit = contexts[request["model"]]
        if isinstance(limit, int) and request["est_tokens"] > limit:
            reasons.append("token_limit_exceeded: est_tokens over the "
                           "model's supported context length")
    if request["requires_accelerator"]:
        acc = capability.get("accelerator")
        if acc == UNKNOWN:
            reasons.append("capability_unknown: accelerator unknown; an "
                           "accelerator-bound task is never guessed")
        elif acc in (None, "none"):
            reasons.append("accelerator_unavailable: task requires one")
    if (measured_latency_ms is not None and latency_budget_ms is not None
            and measured_latency_ms > latency_budget_ms):
        reasons.append("latency_budget_exceeded: measured over budget")
    placed = not reasons
    return {
        "schema": PLACEMENT_SCHEMA,
        "source_project": SOURCE_PROJECT,
        "privacy_zone": request["privacy_zone"],
        "request_id": request["request_id"],
        "owner": request["owner"],
        "node_id": capability["node_id"],
        "decision": "place_local" if placed else "refuse",
        "reasons": reasons,
        "measured_latency_ms": measured_latency_ms,
        "scheduler_owner": "hermes-cron-gateway",
        "recorded_at": recorded_at,
    }


def issue_lease(decision: dict[str, Any], *, caller: str,
                lease_id: str, recorded_at: str = "") -> dict[str, Any]:
    if _require(decision, "schema", str, "PlacementDecision") != PLACEMENT_SCHEMA:
        raise YggdrasilLocalError(
            "envelope_malformed", "PlacementDecision: wrong schema")
    if caller != decision.get("owner"):
        raise YggdrasilLocalError(
            "wrong_owner", "lease caller does not own the placement decision")
    if decision.get("decision") != "place_local":
        raise YggdrasilLocalError(
            "lease_refused", "a refused placement cannot be leased")
    return {
        "schema": LEASE_SCHEMA,
        "source_project": SOURCE_PROJECT,
        "privacy_zone": decision["privacy_zone"],
        "lease_id": lease_id,
        "request_id": decision["request_id"],
        "owner": decision["owner"],
        "node_id": decision["node_id"],
        "state": "leased",
        "scheduler_owner": "hermes-cron-gateway",
        "execution": "not-started: this slice schedules records only; "
                     "Hermes owns execution lifecycle",
        "recorded_at": recorded_at,
    }


def complete_task(lease: dict[str, Any], *, caller: str, status: str,
                  detail: str = "", recorded_at: str = "") -> tuple[dict[str, Any], dict[str, Any]]:
    if _require(lease, "schema", str, "TaskLease") != LEASE_SCHEMA:
        raise YggdrasilLocalError(
            "envelope_malformed", "TaskLease: wrong schema")
    if caller != lease.get("owner"):
        raise YggdrasilLocalError(
            "wrong_owner", "completion caller does not own the lease")
    if status not in ("succeeded", "failed", "cancelled"):
        raise YggdrasilLocalError(
            "envelope_malformed", f"TaskOutcome: status {status!r} not classified")
    outcome = {
        "schema": OUTCOME_SCHEMA,
        "source_project": SOURCE_PROJECT,
        "privacy_zone": lease["privacy_zone"],
        "lease_id": lease["lease_id"],
        "request_id": lease["request_id"],
        "owner": lease["owner"],
        "node_id": lease["node_id"],
        "status": status,
        "detail": detail,
        "recorded_at": recorded_at,
    }
    canonical = json.dumps(outcome, sort_keys=True).encode("utf-8")
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "source_project": SOURCE_PROJECT,
        "privacy_zone": lease["privacy_zone"],
        "lease_id": lease["lease_id"],
        "request_id": lease["request_id"],
        "owner": lease["owner"],
        "evidence_sha256": hashlib.sha256(canonical).hexdigest(),
        "evidence_kind": "local-outcome-record",
        "live_mesh_proof": False,
        "recorded_at": recorded_at,
    }
    return outcome, receipt


def yggdrasil_status(*, recorded_at: str = "") -> dict[str, Any]:
    return {
        "schema": f"{SCHEMA_PREFIX}.status.v1",
        "service": DESCRIPTOR["service"],
        "version": DESCRIPTOR["version"],
        "availability": "contract-implemented",
        "source_repo": SOURCE_REPO,
        "source_head_audited": SOURCE_HEAD_AUDITED,
        "source_license": "MIT (text verified X.01, 2026-11-14)",
        "scope": "local-host discovery + placement records only",
        "mesh_claimed": False,
        "live_peers": 0,
        "peer_discovery": "not implemented (X01-T1)",
        "scheduler_owner": "hermes-cron-gateway (no second scheduler)",
        "recorded_at": recorded_at,
    }
