"""N5 edge + research seams: meter, allocator gate, mesh, repair (W12).

Roadmap section 24 (Phase N5) asks for infrastructure and
self-repair RESEARCH: MimirAlloc evaluated first as an independent
library (correctness, sanitizer evidence, fragmentation, ABI
alignment, allocation failure, thread safety, ARM64 proofs and OOM
recovery precede any drop-in replacement), Yggdrasil node inventory
and safe schedulability experiments on static benchmark fixtures
before any authenticated peer or real inference, Lif-thrasir
tooling that is observe/report/propose ONLY, a machine resource
meter that marks unmeasurable fields unavailable, and hardware
diagnostics that stay private and opt-in. Section 24 acceptance:
low-resource failure tests never corrupt the persona corpus or the
Hermes state database, and proposed self-repair patches never
apply automatically in the early stages.

This slice is CONTRACT/ADAPTER LEVEL, built plugin-side on the
banked seams (W09 capability-bus policy + provenance envelopes,
W10/W11 honest not-claimed status). Honest stage, stated plainly:

- the meter reads only local sources (``/proc/meminfo``, the load
  average, disk usage of a caller-named path); GPU/NPU utilisation
  and temperatures come only from an explicit caller-supplied probe
  mapping -- absent a probe value the field is ``unavailable``,
  never estimated, never invented;
- telemetry is local-private, transmission ``none`` by default, and
  sharing is refused by name without an explicit opt-in and refused
  to any non-local destination even with one;
- the MimirAlloc gate is an evidence checklist: promotion is
  refused by name until EVERY evidence item carries a non-empty
  evidence reference, and even a complete checklist promotes only
  to experimental opt-in -- never to a drop-in replacement;
- Yggdrasil nodes must declare ``source == \"static-fixture\"``;
  anything else is refused by name, scheduling is a pure fit check
  over the fixtures, and a live peer connection is refused by name
  (no production mesh is assumed and none is contacted);
- Lif-thrasir proposals are recorded as proposals; applying one is
  refused by name, always -- there is no apply path in this slice;
- low-resource writes check headroom BEFORE touching the target
  and refuse by name, leaving any existing file byte-identical;
  tests exercise this only against fixtures in temp dirs.

No network, no subprocess, no telemetry transmission anywhere.
"""
from __future__ import annotations

import hashlib
import os
import shutil
from typing import Any

from .capability_bus import result_envelope

SCHEMA = "runeforge.edge-research.v1"
METER_SCHEMA = "runeforge.resource-meter.v1"
MIMIRALLOC_SCHEMA = "runeforge.mimiralloc-gate.v1"
YGGDRASIL_SCHEMA = "runeforge.yggdrasil-experiment.v1"
PROPOSAL_SCHEMA = "runeforge.self-repair-proposal.v1"

EDGE_DESCRIPTOR = {
    "schema": "runeforge.capability.v1",
    "service": "volmarr-edge-research",
    "version": "0.26.0",
    "owner": "volmarr",
    "actions": ["read", "propose", "meter"],
    "transport": "in-process",
    "auth": "scoped",
    "side_effects": True,
    "privacy_classes": ["public", "shared", "local-private"],
    "availability": "contract-implemented",
    "timeout_ms": 2000,
}

MIMIRALLOC_DESCRIPTOR = {
    "schema": "runeforge.capability.v1",
    "service": "volmarr-mimiralloc-eval",
    "version": "0.26.0",
    "owner": "volmarr",
    "actions": ["read", "evaluate"],
    "transport": "in-process",
    "auth": "scoped",
    "side_effects": False,
    "privacy_classes": ["public", "shared", "local-private"],
    "availability": "design-only",
    "timeout_ms": 2000,
}

# Probe fields the meter can report ONLY when a probe supplies them.
PROBE_FIELDS = (
    "gpu_util_percent",
    "gpu_temp_c",
    "gpu_memory_used_bytes",
    "npu_util_percent",
    "npu_temp_c",
    "cpu_temp_c",
    "disk_wear_percent",
)

# MimirAlloc evidence gate, roadmap section 24 order.
EVIDENCE_ITEMS = (
    "correctness",
    "sanitizer_evidence",
    "fragmentation",
    "abi_alignment",
    "allocation_failure",
    "thread_safety",
    "arm64_proof",
    "oom_recovery",
)

EVIDENCE_DESCRIPTIONS = {
    "correctness": "allocator correctness suite green in the library's own tree",
    "sanitizer_evidence": "ASan/TSan-style sanitizer evidence where supported",
    "fragmentation": "fragmentation measured against the ordinary allocator",
    "abi_alignment": "ABI alignment verified for Hermes' allocation call sites",
    "allocation_failure": "allocation-failure behaviour defined and tested",
    "thread_safety": "thread-safety evidence under concurrent allocation",
    "arm64_proof": "ARM64 platform proof (Pi-class target), not x86-only",
    "oom_recovery": "OOM recovery behaviour proven without state corruption",
}

DEFAULT_MIN_MEMORY_BYTES = 64 * 1024 * 1024
DEFAULT_MIN_DISK_BYTES = 16 * 1024 * 1024


class EdgeError(Exception):
    """Named, honest edge-research failure."""

    def __init__(self, name: str, detail: str) -> None:
        super().__init__(detail)
        self.name = name
        self.detail = detail


def _unavailable(reason: str) -> dict[str, Any]:
    return {"status": "unavailable", "reason": reason}


def _measured(value: Any) -> dict[str, Any]:
    return {"status": "measured", "value": value}


# ---------------------------------------------------------------- meter

_MEMINFO_KEYS = (
    "MemTotal", "MemFree", "MemAvailable", "Buffers", "Cached",
    "SwapTotal", "SwapFree",
)


def parse_meminfo(text: str) -> dict[str, int]:
    """Parse /proc/meminfo text into byte counts (kB fields only)."""
    out: dict[str, int] = {}
    for line in text.splitlines():
        name, _, rest = line.partition(":")
        name = name.strip()
        if name not in _MEMINFO_KEYS:
            continue
        parts = rest.split()
        if not parts:
            continue
        try:
            value = int(parts[0])
        except ValueError:
            continue
        out[name] = value * 1024 if len(parts) > 1 and parts[1] == "kB" else value
    return out


def _memory_block(meminfo_text: str | None) -> dict[str, Any]:
    if meminfo_text is None:
        try:
            with open("/proc/meminfo", encoding="utf-8") as handle:
                meminfo_text = handle.read()
        except OSError:
            return _unavailable("meminfo_unreadable")
    parsed = parse_meminfo(meminfo_text)
    if "MemTotal" not in parsed:
        return _unavailable("meminfo_unparseable")
    return {
        "status": "measured",
        "total_bytes": parsed.get("MemTotal"),
        "free_bytes": parsed.get("MemFree"),
        "available_bytes": parsed.get("MemAvailable"),
        "buffers_bytes": parsed.get("Buffers"),
        "cached_bytes": parsed.get("Cached"),
        "swap_total_bytes": parsed.get("SwapTotal"),
        "swap_free_bytes": parsed.get("SwapFree"),
    }


def _load_block(loadavg: Any) -> dict[str, Any]:
    if loadavg is None:
        try:
            loadavg = os.getloadavg()
        except (OSError, AttributeError):
            return _unavailable("loadavg_unreadable")
    try:
        one, five, fifteen = (float(v) for v in loadavg)
    except (TypeError, ValueError):
        return _unavailable("loadavg_unparseable")
    return {"status": "measured", "load1": one, "load5": five, "load15": fifteen}


def _disk_block(disk_path: str, disk_usage: Any) -> dict[str, Any]:
    if disk_usage is None:
        try:
            disk_usage = shutil.disk_usage(disk_path)
        except OSError:
            return _unavailable("disk_usage_unreadable")
    if isinstance(disk_usage, dict):
        total, used, free = (disk_usage.get("total"), disk_usage.get("used"),
                             disk_usage.get("free"))
    else:
        try:
            total, used, free = disk_usage
        except (TypeError, ValueError):
            return _unavailable("disk_usage_unparseable")
    if total is None or free is None:
        return _unavailable("disk_usage_unparseable")
    return {"status": "measured", "path": disk_path, "total_bytes": total,
            "used_bytes": used, "free_bytes": free}


def read_resource_meter(*, recorded_at: str, meminfo_text: str | None = None,
                        loadavg: Any = None, disk_path: str = "/",
                        disk_usage: Any = None,
                        probes: dict[str, Any] | None = None) -> dict[str, Any]:
    """Read the local resource meter; unmeasurable fields stay so.

    GPU/NPU utilisation, temperatures and disk wear are reported
    ONLY from the caller-supplied ``probes`` mapping; without a
    numeric probe value each is ``unavailable`` -- never invented.
    The reading is local-private telemetry: no transmission.
    """
    probes = probes or {}
    accel: dict[str, Any] = {}
    for field_name in PROBE_FIELDS:
        value = probes.get(field_name)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            accel[field_name] = _measured(value)
        else:
            accel[field_name] = _unavailable("not_measurable_on_this_host")
    meter = {
        "schema": METER_SCHEMA,
        "memory": _memory_block(meminfo_text),
        "load": _load_block(loadavg),
        "disk": _disk_block(disk_path, disk_usage),
        "accelerators_and_thermals": accel,
        "telemetry": {"privacy": "local-private", "transmission": "none",
                      "opt_in": False},
    }
    return result_envelope(
        EDGE_DESCRIPTOR, outputs=meter, source_ref="local-host-meter",
        recorded_at=recorded_at, confidentiality="local-private")


def telemetry_share_decision(*, destination: str,
                             opt_in: bool = False) -> dict[str, Any]:
    """Telemetry leaves this host only on explicit opt-in, locally.

    Hardware diagnostics are private and opt-in (roadmap section
    24): without opt-in every share is refused; with opt-in only a
    local destination is allowed -- host telemetry is never
    transmitted into third-party chatrooms or cloud models.
    """
    if not opt_in:
        return {"allowed": False, "reasons": ["telemetry_opt_in_required"]}
    if destination != "local":
        return {"allowed": False,
                "reasons": [f"telemetry_transmission_refused:{destination}"]}
    return {"allowed": True, "reasons": []}


# ------------------------------------------------------- MimirAlloc gate

def mimiralloc_checklist(evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    """The MimirAlloc evaluation checklist over supplied evidence.

    An item is present only when ``evidence`` maps it to a
    non-empty evidence reference; anything else is missing, named.
    The gate is experimental and opt-in ONLY: it never describes
    MimirAlloc as a drop-in replacement.
    """
    evidence = evidence or {}
    items = []
    missing = []
    for item in EVIDENCE_ITEMS:
        ref = evidence.get(item)
        present = isinstance(ref, str) and bool(ref.strip())
        if not present:
            missing.append(item)
        items.append({"item": item,
                      "description": EVIDENCE_DESCRIPTIONS[item],
                      "present": present,
                      "evidence_ref": ref if present else None})
    return {
        "schema": MIMIRALLOC_SCHEMA,
        "experimental": True,
        "opt_in_only": True,
        "drop_in_replacement": False,
        "items": items,
        "present_count": len(EVIDENCE_ITEMS) - len(missing),
        "missing": missing,
    }


def mimiralloc_promotion(evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    """Promotion decision: refused by name until evidence is complete.

    Even a complete checklist promotes MimirAlloc only to
    experimental opt-in evaluation -- ``drop_in_replacement`` stays
    False at every stage of this gate.
    """
    checklist = mimiralloc_checklist(evidence)
    if checklist["missing"]:
        reasons = ["mimiralloc_promotion_refused"] + [
            f"evidence_missing:{item}" for item in checklist["missing"]]
        return {"promoted": False, "allowed": False, "reasons": reasons,
                "scope": None, "drop_in_replacement": False,
                "checklist": checklist}
    return {"promoted": True, "allowed": True, "reasons": [],
            "scope": "experimental-opt-in-only",
            "drop_in_replacement": False, "checklist": checklist}


# ------------------------------------------------------------ Yggdrasil

def validate_node(node: Any) -> dict[str, Any]:
    """Validate one static-fixture node record, refused by name."""
    if not isinstance(node, dict):
        raise EdgeError("validation_failure", "node_not_an_object")
    source = node.get("source")
    if source != "static-fixture":
        raise EdgeError(
            "validation_failure",
            f"node_source_not_static_fixture:{source}")
    node_id = node.get("node_id")
    if not node_id or not str(node_id).strip():
        raise EdgeError("validation_failure", "node_id_required")
    for field_name in ("cpu_cores", "memory_bytes"):
        value = node.get(field_name)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise EdgeError(
                "validation_failure", f"node_field_invalid:{field_name}")
    return {"node_id": str(node_id), "cpu_cores": node["cpu_cores"],
            "memory_bytes": node["memory_bytes"], "source": source,
            "arch": str(node.get("arch", "unknown"))}


def node_inventory(nodes: list[dict[str, Any]], *,
                   recorded_at: str) -> dict[str, Any]:
    """Inventory of static-fixture nodes; no mesh is assumed or claimed."""
    validated = [validate_node(node) for node in nodes]
    inventory = {
        "schema": YGGDRASIL_SCHEMA,
        "nodes": validated,
        "node_count": len(validated),
        "live_peers": 0,
        "mesh_claimed": False,
        "basis": "static-fixtures-only",
    }
    return result_envelope(
        EDGE_DESCRIPTOR, outputs=inventory, source_ref="yggdrasil-fixtures",
        recorded_at=recorded_at, confidentiality="local-private")


def schedule_experiment(nodes: list[dict[str, Any]],
                        workload: dict[str, Any]) -> dict[str, Any]:
    """Safe schedulability check over static fixtures only.

    Pure fit check: the first fixture node (by node_id) whose CPU
    and memory cover the workload is named; no peer is contacted,
    no job is dispatched anywhere.
    """
    validated = [validate_node(node) for node in nodes]
    need_cpu = workload.get("cpu_cores")
    need_mem = workload.get("memory_bytes")
    if (not isinstance(need_cpu, int) or isinstance(need_cpu, bool)
            or not isinstance(need_mem, int) or isinstance(need_mem, bool)
            or need_cpu <= 0 or need_mem <= 0):
        raise EdgeError("validation_failure", "workload_invalid")
    for node in sorted(validated, key=lambda n: n["node_id"]):
        if node["cpu_cores"] >= need_cpu and node["memory_bytes"] >= need_mem:
            return {"scheduled": True, "node_id": node["node_id"],
                    "workload_id": workload.get("workload_id"),
                    "basis": "static-fixture", "dispatched": False}
    return {"scheduled": False, "node_id": None,
            "workload_id": workload.get("workload_id"),
            "reason": "no_static_fixture_fits", "dispatched": False}


def connect_peer(node_id: str) -> dict[str, Any]:
    """A live peer connection is never attempted by this slice."""
    raise EdgeError(
        "live_connection_refused",
        f"yggdrasil_live_peer_connection_not_claimed:{node_id}")


# ------------------------------------------------------------ Lif-thrasir

class ProposalBook:
    """Self-repair proposals: recorded, never applied (observe-only)."""

    def __init__(self) -> None:
        self._proposals: dict[str, dict[str, Any]] = {}
        self._seq = 0

    def propose(self, title: str, detail: str, *,
                recorded_at: str) -> dict[str, Any]:
        if not title or not str(title).strip():
            raise EdgeError("validation_failure", "proposal_title_required")
        self._seq += 1
        record = {
            "schema": PROPOSAL_SCHEMA,
            "proposal_id": f"proposal-{self._seq:04d}",
            "title": str(title),
            "detail": str(detail),
            "status": "proposed",
            "applied": False,
            "recorded_at": recorded_at,
        }
        self._proposals[record["proposal_id"]] = record
        return record

    def get(self, proposal_id: str) -> dict[str, Any] | None:
        return self._proposals.get(proposal_id)

    def proposals(self) -> list[dict[str, Any]]:
        return [self._proposals[key] for key in sorted(self._proposals)]


def apply_proposal(book: ProposalBook, proposal_id: str) -> dict[str, Any]:
    """Applying a self-repair proposal is refused by name, always.

    Lif-thrasir tooling in this slice is observe/report/propose
    only (roadmap section 24); there is no apply path, for any
    proposal, at any approval level.
    """
    if book.get(proposal_id) is None:
        raise EdgeError("unavailable", f"proposal_unknown:{proposal_id}")
    raise EdgeError(
        "apply_refused", f"lifthrasir_apply_refused:{proposal_id}")


def lifthrasir_report(book: ProposalBook) -> dict[str, Any]:
    """Observe/report view of the proposal book; nothing applied."""
    proposals = book.proposals()
    return {
        "schema": PROPOSAL_SCHEMA,
        "mode": "observe/report/propose",
        "proposal_count": len(proposals),
        "applied_count": sum(1 for p in proposals if p["applied"]),
        "proposals": proposals,
    }


# ------------------------------------------------------- low-resource

def check_headroom(*, mem_available_bytes: int, disk_free_bytes: int,
                   min_memory_bytes: int = DEFAULT_MIN_MEMORY_BYTES,
                   min_disk_bytes: int = DEFAULT_MIN_DISK_BYTES) -> None:
    """Refuse by name when simulated/measured headroom is too low."""
    if mem_available_bytes < min_memory_bytes:
        raise EdgeError(
            "resource_exhausted",
            f"low_memory_refused:available={mem_available_bytes}"
            f"<required={min_memory_bytes}")
    if disk_free_bytes < min_disk_bytes:
        raise EdgeError(
            "resource_exhausted",
            f"low_disk_refused:free={disk_free_bytes}"
            f"<required={min_disk_bytes}")


def _host_headroom(target: Any) -> tuple[int, int]:
    mem = _memory_block(None)
    available = mem.get("available_bytes") if mem.get("status") == "measured" else None
    if available is None:
        available = 0
    try:
        free = shutil.disk_usage(str(target)).free
    except OSError:
        free = 0
    return int(available), int(free)


def guarded_write(target: Any, data: bytes, *,
                  mem_available_bytes: int | None = None,
                  disk_free_bytes: int | None = None,
                  min_memory_bytes: int = DEFAULT_MIN_MEMORY_BYTES,
                  min_disk_bytes: int = DEFAULT_MIN_DISK_BYTES) -> dict[str, Any]:
    """Write ``data`` only with proven headroom; refuse cleanly else.

    Headroom is checked BEFORE the target is touched, so a refusal
    leaves any existing file byte-identical -- the section 24
    acceptance property for the persona corpus and Hermes state.
    The write itself is tmp-file + rename in the target directory.
    """
    from pathlib import Path

    path = Path(target)
    if mem_available_bytes is None or disk_free_bytes is None:
        host_mem, host_disk = _host_headroom(path.parent)
        if mem_available_bytes is None:
            mem_available_bytes = host_mem
        if disk_free_bytes is None:
            disk_free_bytes = host_disk
    check_headroom(mem_available_bytes=mem_available_bytes,
                   disk_free_bytes=disk_free_bytes,
                   min_memory_bytes=min_memory_bytes,
                   min_disk_bytes=min_disk_bytes)
    tmp = path.with_name(path.name + ".tmp-w12")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return {"written": True, "path": str(path), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


# ---------------------------------------------------------------- status

def edge_status(*, recorded_at: str) -> dict[str, Any]:
    """Honest N5 status: contract surfaces, no live anything claimed."""
    return {
        "schema": SCHEMA,
        "edge_research": {"service": EDGE_DESCRIPTOR["service"],
                          "availability": EDGE_DESCRIPTOR["availability"]},
        "mimiralloc": {"service": MIMIRALLOC_DESCRIPTOR["service"],
                       "availability": MIMIRALLOC_DESCRIPTOR["availability"],
                       "experimental": True, "opt_in_only": True,
                       "drop_in_replacement": False},
        "yggdrasil": {"live_peers": 0, "mesh_claimed": False,
                      "basis": "static-fixtures-only"},
        "lifthrasir": {"mode": "observe/report/propose",
                       "auto_apply": False},
        "telemetry": {"privacy": "local-private", "transmission": "none",
                      "opt_in": False},
        "live_connection": "not-claimed",
        "recorded_at": recorded_at,
    }
