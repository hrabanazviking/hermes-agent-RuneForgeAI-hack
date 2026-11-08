"""N4 embodiment/world seams: interchange, world facts, presence (W11).

Roadmap section 23 (Phase N4) asks for Runmal import/export of
personas and lorebooks with versioned schema translation and exact
authorship, WYRD world state as typed events with provenance that
are never blended into fictional/persona memory, permission-scoped
Heimdall/Second Life access, display-safe Hlidskjalfr HUD events,
and honest connected/offline availability. Section 30's W11 gate is
owner-authorized end-to-end behavior.

This slice is CONTRACT/ADAPTER LEVEL, built plugin-side on the
banked seams (W03 canonical library record shape, W09 capability
bus policy + provenance envelopes, W08 WYRD contract row). Honest
stage, stated plainly:

- the interchange is a versioned JSON bundle: source documents ride
  as base64 bytes so a round trip is byte-identical, authorship is
  a required field carried verbatim, unknown schema names and
  unsupported versions are refused by name, and shared documents
  import read-only unless the operator passes the explicit
  promotion flag;
- world events are typed records whose provenance (service, source
  ref, recorded-at, confidentiality) is mandatory; routing a world
  event into a persona/fictional store is refused by name -- the
  separation guard is a hard refusal, not a warning;
- a remote-presence identity is authorized through the W09 policy
  against an owner-only descriptor that does not declare
  local-private data, so private persona reads are refused by name;
- the HUD filter is an allow-list: only display-safe fields pass,
  sensitive fields are dropped by name and unknown fields by
  default;
- availability comes only from an explicit probe result object: no
  probe (absent service) reports unavailable and exposes no
  capabilities -- nothing a device does not expose is implied;
- Heimdall/Second Life has NO credentials and NO live connection
  in this slice: its descriptor is design-only, an opt-in bot
  service scope on the bus, nothing more. No fake SL client exists.

No network, no subprocess, no writes outside caller-supplied data.
"""
from __future__ import annotations

import base64
import hashlib
from typing import Any

from .capability_bus import authorize, result_envelope

SCHEMA = "runeforge.world-interchange.v1"
SCHEMA_NAME = "runeforge.world-interchange"
SUPPORTED_VERSIONS = (1,)
WORLD_EVENT_SCHEMA = "runeforge.world-event.v1"
PRESENCE_SCHEMA = "runeforge.remote-presence.v1"

RUNMAL_DESCRIPTOR = {
    "schema": "runeforge.capability.v1",
    "service": "volmarr-runmal-interchange",
    "version": "0.26.0",
    "owner": "volmarr",
    "actions": ["read", "propose", "export", "import"],
    "transport": "in-process",
    "auth": "scoped",
    "side_effects": True,
    "privacy_classes": ["public", "shared", "local-private"],
    "availability": "contract-implemented",
    "timeout_ms": 2000,
}

HEIMDALL_DESCRIPTOR = {
    "schema": "runeforge.capability.v1",
    "service": "volmarr-heimdall-presence",
    "version": "0.26.0",
    "owner": "volmarr",
    "actions": ["read", "presence"],
    "transport": "authenticated-remote",
    "auth": "owner-only",
    "side_effects": True,
    "privacy_classes": ["public", "shared"],
    "availability": "design-only",
    "timeout_ms": 2000,
}

WORLD_STORES = ("wyrd", "world")
FORBIDDEN_STORES = ("persona", "fictional", "persona-memory", "memory")
EVENT_KINDS = ("observation", "location", "action-outcome", "availability")
HUD_SAFE_FIELDS = ("kind", "title", "value", "unit", "status", "service", "recorded_at")
HUD_SENSITIVE_FIELDS = ("transcript", "content", "text", "secret", "token", "persona_text", "prompt")
AVATAR_VIEW_FIELDS = ("view", "camera", "viewport")
AVATAR_ANIMATION_FIELDS = ("gesture", "emotion_animation", "expression")
AVATAR_DECISION_FIELDS = ("decision", "choice", "intent", "plan")


class WorldError(Exception):
    """Named, honest world-bridge failure."""

    def __init__(self, name: str, detail: str) -> None:
        super().__init__(detail)
        self.name = name
        self.detail = detail


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def export_bundle(documents: list[dict[str, Any]], *, recorded_at: str) -> dict[str, Any]:
    """Export persona/lorebook documents as a versioned bundle.

    Each document needs verbatim ``authorship`` and raw ``content``
    (bytes or str). Content rides base64 so the round trip is
    byte-identical; the sha256 of the raw bytes is pinned per doc.
    """
    if not documents:
        raise WorldError("validation_failure", "bundle_empty")
    out_docs = []
    for doc in documents:
        authorship = doc.get("authorship")
        if not authorship or not str(authorship).strip():
            raise WorldError("validation_failure", "authorship_required")
        if "content" not in doc:
            raise WorldError("validation_failure", "content_required")
        raw = doc["content"]
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        if not isinstance(raw, (bytes, bytearray)):
            raise WorldError("validation_failure", "content_not_bytes")
        raw = bytes(raw)
        privacy = doc.get("privacy_class", "shared")
        if privacy not in ("public", "shared", "local-private"):
            raise WorldError("validation_failure", f"privacy_class_unknown:{privacy}")
        out_docs.append({
            "doc_id": str(doc.get("doc_id") or _sha256(raw)[:16]),
            "title": str(doc.get("title", "")),
            "kind": str(doc.get("kind", "persona")),
            "authorship": authorship,
            "privacy_class": privacy,
            "sha256": _sha256(raw),
            "size_bytes": len(raw),
            "content_b64": base64.b64encode(raw).decode("ascii"),
        })
    bundle = {
        "schema": SCHEMA,
        "schema_name": SCHEMA_NAME,
        "version": 1,
        "recorded_at": recorded_at,
        "documents": out_docs,
    }
    return result_envelope(
        RUNMAL_DESCRIPTOR, outputs=bundle, source_ref="runmal-export",
        recorded_at=recorded_at, confidentiality="shared")


def import_bundle(bundle: Any, *, promote_shared: bool = False) -> list[dict[str, Any]]:
    """Import a bundle produced by :func:`export_bundle`.

    Unknown schema names and unsupported versions are refused by
    name. Hash mismatches are refused. Shared documents import
    read-only unless ``promote_shared`` is explicitly true.
    """
    payload = bundle.get("outputs", bundle) if isinstance(bundle, dict) else None
    if not isinstance(payload, dict):
        raise WorldError("validation_failure", "bundle_not_object")
    name = payload.get("schema_name") or str(payload.get("schema", "")).rsplit(".v", 1)[0]
    if name != SCHEMA_NAME:
        raise WorldError("validation_failure", f"schema_unknown:{name}")
    version = payload.get("version")
    if version not in SUPPORTED_VERSIONS:
        raise WorldError("validation_failure", f"schema_version_unsupported:{version}")
    docs = []
    for entry in payload.get("documents", []):
        if not entry.get("authorship"):
            raise WorldError("validation_failure", "authorship_required")
        try:
            raw = base64.b64decode(entry["content_b64"], validate=True)
        except Exception as exc:
            raise WorldError("validation_failure", f"content_b64_invalid:{exc}") from exc
        if _sha256(raw) != entry.get("sha256"):
            raise WorldError("validation_failure", f"content_hash_mismatch:{entry.get('doc_id')}")
        shared = entry.get("privacy_class") == "shared"
        docs.append({
            "doc_id": entry["doc_id"],
            "title": entry.get("title", ""),
            "kind": entry.get("kind", "persona"),
            "authorship": entry["authorship"],
            "privacy_class": entry.get("privacy_class", "shared"),
            "sha256": entry["sha256"],
            "content": raw,
            "read_only": bool(shared and not promote_shared),
        })
    if not docs:
        raise WorldError("validation_failure", "bundle_empty")
    return docs


def make_world_event(kind: str, payload: Any, *, provenance: dict[str, Any]) -> dict[str, Any]:
    """Build a typed WYRD world event; provenance is mandatory."""
    if kind not in EVENT_KINDS:
        raise WorldError("validation_failure", f"event_kind_unknown:{kind}")
    if not isinstance(provenance, dict):
        raise WorldError("validation_failure", "provenance_required")
    for field_name in ("service", "source_ref", "recorded_at", "confidentiality"):
        if not provenance.get(field_name):
            raise WorldError("validation_failure", f"provenance_field_required:{field_name}")
    if provenance["confidentiality"] not in ("public", "shared", "local-private"):
        raise WorldError(
            "validation_failure",
            f"confidentiality_unknown:{provenance['confidentiality']}")
    return {
        "schema": WORLD_EVENT_SCHEMA,
        "kind": kind,
        "payload": payload,
        "provenance": {
            "service": provenance["service"],
            "source_ref": provenance["source_ref"],
            "recorded_at": provenance["recorded_at"],
            "confidentiality": provenance["confidentiality"],
        },
    }


def route_world_event(event: dict[str, Any], target_store: str) -> dict[str, Any]:
    """Route a world event to a world store -- never persona memory."""
    if target_store in FORBIDDEN_STORES:
        raise WorldError(
            "separation_refused",
            f"world_event_persona_blending_refused:{target_store}")
    if target_store not in WORLD_STORES:
        raise WorldError("validation_failure", f"target_store_unknown:{target_store}")
    if event.get("schema") != WORLD_EVENT_SCHEMA:
        raise WorldError("validation_failure", "world_event_schema_required")
    return {"routed_to": target_store, "event": event}


def authorize_presence(*, caller: str, action: str, data_owner: str,
                       data_class: str, destination: str = "local",
                       approved: bool = False) -> dict[str, Any]:
    """Authorize a remote-presence action through the W09 policy.

    The Heimdall descriptor is owner-only and does not declare
    local-private data, so private persona reads are refused by
    name by the policy itself.
    """
    return authorize(
        HEIMDALL_DESCRIPTOR, caller=caller, action=action,
        data_owner=data_owner, data_class=data_class,
        destination=destination, approved=approved)


def hud_filter(event: dict[str, Any]) -> dict[str, Any]:
    """Filter an event down to display-safe HUD fields (allow-list)."""
    passed: dict[str, Any] = {}
    dropped_sensitive: list[str] = []
    dropped_unknown: list[str] = []
    for key, value in event.items():
        if key in HUD_SAFE_FIELDS:
            passed[key] = value
        elif key in HUD_SENSITIVE_FIELDS:
            dropped_sensitive.append(key)
        else:
            dropped_unknown.append(key)
    return {
        "event": passed,
        "dropped_sensitive": sorted(dropped_sensitive),
        "dropped_unknown": sorted(dropped_unknown),
    }


def separate_avatar_layers(payload: dict[str, Any]) -> dict[str, Any]:
    """Separate view/animation signals from actual decisions.

    Avatar/VR presentation (view, gesture, simulated emotion) is
    returned apart from any decision fields; decision fields are
    named, never silently merged into the animation layer.
    """
    view = {k: payload[k] for k in AVATAR_VIEW_FIELDS if k in payload}
    animation = {k: payload[k] for k in AVATAR_ANIMATION_FIELDS if k in payload}
    decisions = sorted(k for k in AVATAR_DECISION_FIELDS if k in payload)
    return {"view": view, "animation": animation, "decision_fields_named": decisions}


def availability(probe: Any) -> dict[str, Any]:
    """Honest availability from an explicit probe result only."""
    if not isinstance(probe, dict) or not probe.get("ok"):
        return {"available": False, "capabilities": [], "reason": "no_probe_result"}
    exposed = probe.get("exposed")
    if not isinstance(exposed, list):
        return {"available": False, "capabilities": [], "reason": "probe_exposed_missing"}
    return {"available": True, "capabilities": list(exposed), "reason": "probe_ok"}


class WorkQueue:
    """Offline work queue: items wait, then flush in order, once."""

    def __init__(self) -> None:
        self._items: list[dict[str, Any]] = []
        self._done: set[str] = set()

    def enqueue(self, item_id: str, payload: Any) -> dict[str, Any]:
        if item_id in self._done or any(i["item_id"] == item_id for i in self._items):
            return {"queued": False, "reason": "duplicate_item"}
        self._items.append({"item_id": item_id, "payload": payload})
        return {"queued": True, "pending": len(self._items)}

    def flush(self, *, online: bool) -> dict[str, Any]:
        if not online:
            return {"flushed": [], "pending": len(self._items), "reason": "offline"}
        flushed = [i["item_id"] for i in self._items]
        self._done.update(flushed)
        self._items = []
        return {"flushed": flushed, "pending": 0, "reason": "online"}

    def pending(self) -> int:
        return len(self._items)
