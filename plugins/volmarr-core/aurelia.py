"""X.11 Aurelia Sensations Server: private state simulation (s.46).

The Aurelia server (``hrabanazviking/RuneForgeAI-Aurelia-Sensations-Server``,
PRIVATE, audited at ``d6c2632435bd``) is Volmarr's embodied
companion-state simulation: a long-running FastAPI server
(``aurelia_agent_server.py``, app version 1.0.0, default port
8001, deployed on Mimir by its systemd template) keeping one
agent alive over the ``female_motivation`` package (303 Python
modules in the audited tree). License: Apache-2.0, text-verified
(``LICENSE`` sha256 c71d239df917...). Audited from source
structure, not README: the endpoint surface at the audited HEAD
includes ``GET /health``, ``GET /state``, ``GET /senses``,
``POST /event``, ``POST /tick``, ``POST /pause``,
``POST /resume``, ``POST /save`` and profile endpoints.

PRIVACY LAW (section 46): Aurelia data is intimate and private.
This connector, its tests and its records carry INTERFACES AND
SCHEMAS ONLY. No sensation, configuration or interaction content
is ever read, recorded or persisted here: status measures a
staged tree's structure only (HEAD, server version string,
module count, LICENSE hash) and never opens ``data/`` or
``config/`` contents. Plans accept event kinds, ids and consent
scopes only - any content field is refused by name.

Scope law (section 46): opt-in, default-off, local-only routing;
authored identity (SOUL.md canon) is separate from transient
simulated state and is NEVER edited by this connector; each
persona has an independent scope and may never see another
persona's state; lifecycle metadata for Verdandi-style records
is redacted and content-free; presentation/voice surfaces are
output consumers only - direct control of microphone, avatar,
messaging or devices is refused by name. The model is
experimental: no claims about real human psychology are made
and ``production_ready`` is False. This connector builds NO
network client: the live server runs on Mimir, and binding a
live transport is future work (ticket X11-T1).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

CANONICAL_REPO = "hrabanazviking/RuneForgeAI-Aurelia-Sensations-Server"
CANONICAL_REPO_URL = "https://github.com/hrabanazviking/RuneForgeAI-Aurelia-Sensations-Server"
AUDITED_HEAD = "d6c2632435bd3034dfcd34df1ba1e9a7a799e947"
SERVER_VERSION = "1.0.0"
PROJECT_LICENSE = "Apache-2.0"
LICENSE_SHA256 = "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"
ADAPTER_VERSION = "0.1.0"
DEPLOYMENT = "Mimir (systemd aurelia-agent.service, default port 8001)"

# Section 46 item 4 narrow data contract, each kind with its
# audited endpoint basis at the audited HEAD.
CONTRACT_KINDS = (
    {"kind": "health", "supported": True, "basis": "GET /health endpoint (real at audited HEAD)"},
    {"kind": "state_snapshot", "supported": True, "basis": "GET /state endpoint (real); snapshot shape only, contents never read by this connector"},
    {"kind": "state_event", "supported": True, "basis": "POST /event endpoint (real); planned by kind + idempotent event id + consent scope only"},
    {"kind": "simulation_step", "supported": True, "basis": "POST /tick endpoint (real)"},
    {"kind": "simulation_pause", "supported": True, "basis": "POST /pause + POST /resume endpoints (real)"},
    {"kind": "state_save", "supported": True, "basis": "POST /save endpoint (real); exact-restore checkpoint shape"},
    {"kind": "direct_device_control", "supported": False, "basis": "section 46 item 9: presentation/voice are output consumers only; direct microphone/avatar/messaging/device control is never granted"},
    {"kind": "canon_edit", "supported": False, "basis": "section 46 item 3: simulated state never overwrites human-authored SOUL.md or canonical identity"},
    {"kind": "external_egress", "supported": False, "basis": "section 46 item 7: local-only routing; no simulated events to third-party LLMs, cloud metrics, shared spaces or public logs"},
)
EGRESS_VERBS_REFUSED = ("publish", "upload", "share", "broadcast", "sync_cloud")
CONTENT_FIELDS_REFUSED = ("payload", "content", "sensation", "sensations", "body", "text", "history")


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if value is None:
        return default
    return bool(value)


def contract_catalog() -> dict[str, Any]:
    """The s.46 contract catalog: supported vs refused, honestly."""
    return {
        "schema": "runeforge.aurelia.catalog.v1",
        "service": "volmarr-aurelia",
        "canonical_repo": CANONICAL_REPO,
        "audited_head": AUDITED_HEAD,
        "server_version": SERVER_VERSION,
        "contracts": [dict(row) for row in CONTRACT_KINDS],
        "egress_verbs_refused": list(EGRESS_VERBS_REFUSED),
        "content_fields_refused": list(CONTENT_FIELDS_REFUSED),
        "sends_anything_external": False,
        "edits_canon": False,
        "experimental": True,
        "production_ready": False,
    }


def _measure_tree(root: Path) -> dict[str, Any]:
    """Measure a staged Aurelia checkout truthfully (no git call).

    Reads .git/HEAD + refs, the FastAPI version string in
    aurelia_agent_server.py, the LICENSE hash, and counts Python
    modules by filename. ``data/`` and ``config/`` contents are
    NEVER opened: intimate content cannot leak through status.
    """
    record: dict[str, Any] = {"root": str(root), "present": root.is_dir()}
    if not root.is_dir():
        record["status"] = "tree_missing"
        return record
    head = None
    head_file = root / ".git" / "HEAD"
    if head_file.is_file():
        ref = head_file.read_text(encoding="utf-8").strip()
        if ref.startswith("ref:"):
            ref_path = root / ".git" / ref[4:].strip()
            if ref_path.is_file():
                head = ref_path.read_text(encoding="utf-8").strip()
            else:
                packed = root / ".git" / "packed-refs"
                if packed.is_file():
                    for line in packed.read_text(encoding="utf-8").splitlines():
                        parts = line.split(" ", 1)
                        if len(parts) == 2 and parts[1].strip() == ref[4:].strip():
                            head = parts[0].strip()
        elif ref:
            head = ref
    record["head"] = head
    record["head_matches_audited"] = head == AUDITED_HEAD
    server = root / "aurelia_agent_server.py"
    if server.is_file():
        match = re.search(r'FastAPI\(title="Aurelia Agent Server",\s*version="([^"]+)"',
                          server.read_text(encoding="utf-8"))
        if match:
            record["server_version"] = match.group(1)
    license_file = root / "LICENSE"
    if license_file.is_file():
        record["license_sha256"] = hashlib.sha256(
            license_file.read_bytes()).hexdigest()
        record["license_matches_audited"] = (
            record["license_sha256"] == LICENSE_SHA256)
    record["module_count"] = sum(
        1 for p in root.rglob("*.py") if ".git" not in p.parts)
    record["status"] = "measured" if head else "tree_partial"
    return record


def aurelia_status(ctx, recorded_at: str | None = None) -> dict[str, Any]:
    """Truthful adapter status: config, staged tree, hard limits."""
    enabled = _as_bool(ctx.get_config("aurelia_enabled", False))
    root_value = str(ctx.get_config("aurelia_root", "") or "").strip()
    tree = _measure_tree(Path(root_value).expanduser()) if root_value else {
        "root": "", "present": False, "status": "not_configured"}
    return {
        "schema": "runeforge.aurelia.status.v1",
        "service": "volmarr-aurelia",
        "recorded_at": recorded_at,
        "enabled": enabled,
        "configured": bool(root_value),
        "canonical_repo": CANONICAL_REPO,
        "canonical_repo_url": CANONICAL_REPO_URL,
        "audited_head": AUDITED_HEAD,
        "server_version": SERVER_VERSION,
        "license": PROJECT_LICENSE,
        "deployment": DEPLOYMENT,
        "tree": tree,
        "mode": "opt-in, local-only private state simulation; planning + content-free records only, no live transport bound",
        "privacy": "local-only; interfaces and schemas only; no sensation, configuration or interaction content is read by status",
        "sends_anything_external": False,
        "edits_canon": False,
        "experimental": True,
        "production_ready": False,
    }


def check_scope(persona: str, requested_persona: str | None = None,
                target: str = "simulated_state") -> dict[str, Any]:
    """s.46 items 3+5: per-persona scopes, identity separation.

    A persona may access ONLY its own simulated-state namespace.
    Cross-persona access is refused by name, and simulated state
    may never be written into authored identity / canon.
    """
    wanted = (requested_persona or persona or "").strip()
    if target in {"authored_identity", "canon", "soul"}:
        return {"persona": persona, "requested_persona": wanted,
                "target": target, "allowed": False,
                "refused": "simulated_state_not_canon"}
    if wanted != (persona or "").strip():
        return {"persona": persona, "requested_persona": wanted,
                "target": target, "allowed": False,
                "refused": "cross_persona_scope_refused"}
    return {"persona": persona, "requested_persona": wanted,
            "target": target, "allowed": True, "refused": None}


def lifecycle_record(*, persona: str, kind: str, event_id: str) -> dict[str, Any]:
    """s.46 item 6: redacted, content-free lifecycle metadata.

    Carries only the persona scope, the contract kind and a hash
    of the event id - never any intimate event content - so it is
    safe for Verdandi-style lifecycle records and audit receipts.
    """
    digest = hashlib.sha256(
        f"{persona}:{event_id}".encode("utf-8")).hexdigest()
    return {"schema": "runeforge.aurelia.lifecycle.v1",
            "persona": persona, "kind": kind,
            "event_ref": digest[:16], "content_included": False,
            "local_only": True}


def build_event_plan(events: list[dict], *, persona: str = "",
                     consent_scopes: list[str] | None = None) -> dict[str, Any]:
    """Guarded event plan (s.46 items 4+7+8): pure, deterministic.

    Each requested event is {kind, event_id, scope}. Unknown
    kinds, audited-refused kinds (direct device control, canon
    edit, external egress) and every egress verb are refused BY
    NAME. Any content field is refused by name - plans carry no
    intimate content. An event needs an idempotent event id and
    a consent scope the persona actually holds; a repeated event
    id is an idempotent duplicate, never re-applied. Planned
    events carry provenance, bounds and an audit-receipt
    requirement (a content-free lifecycle record). The plan runs
    nothing and contacts no server.
    """
    known = {row["kind"]: row for row in CONTRACT_KINDS}
    held = set(consent_scopes or [])
    planned: list[dict[str, Any]] = []
    refused: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, event in enumerate(events or []):
        kind = str(event.get("kind") or "")
        if kind in EGRESS_VERBS_REFUSED:
            refused.append({"index": index, "kind": kind, "reason": "egress_refused"})
            continue
        content = [f for f in CONTENT_FIELDS_REFUSED if f in event]
        if content:
            refused.append({"index": index, "kind": kind,
                            "reason": "intimate_content_not_accepted",
                            "fields": content})
            continue
        row = known.get(kind)
        if row is None:
            refused.append({"index": index, "kind": kind, "reason": "unknown_contract"})
            continue
        if not row["supported"]:
            refused.append({"index": index, "kind": kind, "reason": "contract_refused"})
            continue
        scope_check = check_scope(persona, event.get("persona"), "simulated_state")
        if not scope_check["allowed"]:
            refused.append({"index": index, "kind": kind,
                            "reason": scope_check["refused"]})
            continue
        event_id = str(event.get("event_id") or "")
        if not event_id:
            refused.append({"index": index, "kind": kind, "reason": "event_id_required"})
            continue
        if event_id in seen_ids:
            refused.append({"index": index, "kind": kind,
                            "reason": "duplicate_event_idempotent"})
            continue
        scope = str(event.get("scope") or "")
        if scope not in held:
            refused.append({"index": index, "kind": kind,
                            "reason": "consent_scope_required"})
            continue
        seen_ids.add(event_id)
        planned.append({
            "index": index, "kind": kind, "event_id": event_id,
            "persona": persona, "scope": scope,
            "bounds_checked": True, "content_included": False,
            "provenance": {"audited_head": AUDITED_HEAD, "basis": row["basis"]},
            "audit_receipt": lifecycle_record(
                persona=persona, kind=kind, event_id=event_id),
        })
    body = {"events": planned, "refused": refused, "persona": persona}
    plan_key = hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()
    return {"schema": "runeforge.aurelia.plan.v1", "service": "volmarr-aurelia",
            "plan_key": plan_key, "events": planned, "refused": refused,
            "event_count": len(planned), "refused_count": len(refused),
            "persona": persona, "sends_anything_external": False,
            "edits_canon": False, "runs_server": False,
            "production_ready": False}


def grant_consent(store_dir: Path, persona: str, scope: str) -> dict[str, Any]:
    """Record an explicit, revocable consent scope (s.46 item 8)."""
    store_dir = Path(store_dir) / "consent"
    store_dir.mkdir(parents=True, exist_ok=True)
    path = store_dir / f"{persona}.json"
    record = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {
        "persona": persona, "scopes": []}
    if scope not in record["scopes"]:
        record["scopes"].append(scope)
    path.write_text(json.dumps(record, indent=1, sort_keys=True), encoding="utf-8")
    return {"schema": "runeforge.aurelia.consent.v1", "persona": persona,
            "scopes": sorted(record["scopes"]), "revoked": False}


def revoke_consent(store_dir: Path, persona: str, scope: str) -> dict[str, Any]:
    """Revoke a consent scope: later plans refuse it by name."""
    path = Path(store_dir) / "consent" / f"{persona}.json"
    record = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {
        "persona": persona, "scopes": []}
    record["scopes"] = [s for s in record["scopes"] if s != scope]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1, sort_keys=True), encoding="utf-8")
    return {"schema": "runeforge.aurelia.consent.v1", "persona": persona,
            "scopes": sorted(record["scopes"]), "revoked": True}


def write_checkpoint(store_dir: Path, plan: dict, completed: list[int]) -> dict[str, Any]:
    """Exact-restore checkpoint for a plan (s.46 item 8)."""
    store_dir = Path(store_dir) / "checkpoints"
    store_dir.mkdir(parents=True, exist_ok=True)
    path = store_dir / f"{plan['plan_key']}.json"
    record = {"plan_key": plan["plan_key"], "plan": plan,
              "completed_indexes": sorted(int(i) for i in completed)}
    path.write_text(json.dumps(record, indent=1, sort_keys=True, default=str), encoding="utf-8")
    return {"schema": "runeforge.aurelia.checkpoint.v1",
            "plan_key": plan["plan_key"], "store_path": str(path),
            "completed_count": len(record["completed_indexes"])}


def resume_plan(store_dir: Path, plan_key: str) -> dict[str, Any]:
    """Replay after interruption: exactly the uncompleted events."""
    path = Path(store_dir) / "checkpoints" / f"{plan_key}.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    done = set(record["completed_indexes"])
    remaining = [e for e in record["plan"]["events"] if e["index"] not in done]
    return {"schema": "runeforge.aurelia.resume.v1", "plan_key": plan_key,
            "completed_count": len(done), "remaining": remaining,
            "remaining_count": len(remaining), "resumed": True}


# A labelled synthetic plan for the CLI plan verb: it proves the
# guard machinery (one consent refusal, one contract refusal, one
# egress refusal) without touching any real persona state.
SYNTHETIC_EVENTS = [
    {"kind": "health", "event_id": "synthetic-health-1", "scope": "state_read"},
    {"kind": "simulation_pause", "event_id": "synthetic-pause-1", "scope": "state_read"},
    {"kind": "state_event", "event_id": "synthetic-event-1", "scope": "ungranted_scope"},
    {"kind": "direct_device_control", "event_id": "synthetic-ctl-1", "scope": "state_read"},
    {"kind": "publish", "event_id": "synthetic-pub-1", "scope": "state_read"},
]
SYNTHETIC_PERSONA = "synthetic-persona"
SYNTHETIC_CONSENT = ["state_read"]

__all__ = [
    "ADAPTER_VERSION", "AUDITED_HEAD", "CANONICAL_REPO",
    "CANONICAL_REPO_URL", "CONTENT_FIELDS_REFUSED", "CONTRACT_KINDS",
    "DEPLOYMENT", "EGRESS_VERBS_REFUSED", "LICENSE_SHA256",
    "PROJECT_LICENSE", "SERVER_VERSION", "SYNTHETIC_CONSENT",
    "SYNTHETIC_EVENTS", "SYNTHETIC_PERSONA", "aurelia_status",
    "build_event_plan", "check_scope", "contract_catalog",
    "grant_consent", "lifecycle_record", "resume_plan",
    "revoke_consent", "write_checkpoint",
]
