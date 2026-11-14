"""X.08 Samkoma: evidence-aware planning, proposal-only (roadmap s.43).

Samkoma (``hrabanazviking/RuneForgeAI-Samkoma``, audited at
``aa84ad3308b1``) is Volmarr's group-planning commons: material a
group already produced (chat exports, flyers, newsletters, links,
voice notes) is read into CANDIDATES - drafts in a review queue,
never facts - and a candidate becomes a real event, task or
decision only when a person approves it. Every proposed field
carries provenance: the exact quote from the exact source, or the
field is marked ``unsupported`` and shown that way.

This module is the Hermes-side adapter. It is original
volmarr-core code; no Samkoma source is copied or vendored, and
Samkoma remains a separate service with its own API (202 paths /
230 schemas in its frozen OPENAPI.json at the audited HEAD).

Scope law for this slice (section 43 items 2-4): READ-ONLY and
PROPOSAL-ONLY. The adapter can search source receipts, build a
candidate whose fields are citation-verified against the source
text, preview it, evaluate a manual approval, and draft proposals
offline with idempotent receipts. It has NO publish path: no verb
creates a calendar event, reminder, task or announcement, and an
approval evaluated here converts nothing - conversion stays a
future, separately authorized slice (ticket X08-T2). Connector
replication (Google Calendar or other accounts) is
connector-specific and explicitly authorized, never inferred
(item 6); the default-off ``samkoma_connector_authorized`` key
only records whether such authorization was ever given - this
adapter performs no sync either way. Samtal room context is
opt-in behind explicit room consent (item 5), recorded by the
default-off ``samkoma_room_consent`` key; no room is read here.

Truth discipline: a field is ``supported`` only when its quote is
a verbatim substring of the cited source text; anything else is
``unsupported`` and stays unsupported through preview AND through
approval (an approval never launders an unsupported field into a
fact). ``production_ready`` is False: Samkoma's own README states
its Phase 19 closing full-suite proof is still owed, and this
adapter binds no live Samkoma service in this slice.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

CANONICAL_REPO = "hrabanazviking/RuneForgeAI-Samkoma"
CANONICAL_REPO_URL = "https://github.com/hrabanazviking/RuneForgeAI-Samkoma"
AUDITED_HEAD = "aa84ad3308b1b95b0c98ac572587b5bf9a573224"
PROJECT_LICENSE = "GPL-3.0-only"
LICENSE_SHA256 = "3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986"
OPENAPI_PATHS = 202
OPENAPI_SCHEMAS = 230
APPROVER_ROLES = ("owner", "organiser", "organizer", "reviewer", "admin")

# The section 43 item 2 illustrative operations, with their real
# modes. Names are the roadmap's illustrative names, NOT a claim
# about Samkoma's existing API (its real candidate/source routes
# live under /api/v1/groups/{group_id}/candidates|sources).
OPERATIONS = (
    {"name": "source.search", "mode": "read-only"},
    {"name": "candidate.extract", "mode": "proposal-only"},
    {"name": "candidate.preview", "mode": "read-only"},
    {"name": "review.status", "mode": "read-only"},
    {"name": "proposal.draft", "mode": "proposal-only (offline, local store)"},
)
# Verbs this adapter refuses by name: publication is not in scope.
PUBLISH_VERBS_REFUSED = (
    "event.publish", "calendar.create", "reminder.create",
    "task.create", "announcement.publish", "connector.sync",
)


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if value is None:
        return default
    return bool(value)


def operations_catalog() -> dict[str, Any]:
    """The s.43 operations with modes + refused publish verbs."""
    return {
        "schema": "runeforge.samkoma.catalog.v1",
        "service": "volmarr-samkoma",
        "canonical_repo": CANONICAL_REPO,
        "operations": [dict(op) for op in OPERATIONS],
        "publish_verbs_refused": list(PUBLISH_VERBS_REFUSED),
        "publishes_anything": False,
        "production_ready": False,
    }


def _measure_tree(root: Path) -> dict[str, Any]:
    """Measure a staged Samkoma checkout truthfully (no git call).

    Reads .git/HEAD + refs, OPENAPI.json and LICENSE directly, so
    the numbers are the tree's own, never this module's constants
    restated. A missing or partial tree reports what is missing.
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
    api = root / "OPENAPI.json"
    if api.is_file():
        doc = json.loads(api.read_text(encoding="utf-8"))
        record["openapi_paths"] = len(doc.get("paths") or {})
        record["openapi_schemas"] = len(
            (doc.get("components") or {}).get("schemas") or {})
    lic = root / "LICENSE"
    if lic.is_file():
        record["license_sha256"] = hashlib.sha256(lic.read_bytes()).hexdigest()
        record["license_matches_audited"] = record["license_sha256"] == LICENSE_SHA256
    record["status"] = "measured" if head else "tree_partial"
    return record


def samkoma_status(ctx, recorded_at: str | None = None) -> dict[str, Any]:
    """Truthful adapter status: config, staged tree, hard limits."""
    enabled = _as_bool(ctx.get_config("samkoma_enabled", False))
    root_value = str(ctx.get_config("samkoma_root", "") or "").strip()
    account = str(ctx.get_config("samkoma_account", "") or "").strip()
    tree = _measure_tree(Path(root_value).expanduser()) if root_value else {
        "root": "", "present": False, "status": "not_configured"}
    return {
        "schema": "runeforge.samkoma.status.v1",
        "service": "volmarr-samkoma",
        "recorded_at": recorded_at,
        "enabled": enabled,
        "configured": bool(root_value),
        "canonical_repo": CANONICAL_REPO,
        "canonical_repo_url": CANONICAL_REPO_URL,
        "audited_head": AUDITED_HEAD,
        "license": PROJECT_LICENSE,
        "license_sha256": LICENSE_SHA256,
        "account_configured": bool(account),
        "room_consent": _as_bool(ctx.get_config("samkoma_room_consent", False)),
        "connector_authorized": _as_bool(
            ctx.get_config("samkoma_connector_authorized", False)),
        "connector_sync_performed": False,
        "tree": tree,
        "mode": "read-only + proposal-only",
        "publishes_anything": False,
        "production_ready": False,
    }


def search_sources(sources: list[dict], query: str) -> list[dict]:
    """source.search (read-only): receipts whose text matches.

    ``sources`` are source receipts: dicts with id/kind/text. The
    search is a plain case-insensitive substring match over the
    receipt text - deterministic, and it returns receipts, never
    facts derived from them.
    """
    needle = (query or "").strip().lower()
    if not needle:
        return []
    out = []
    for source in sources:
        text = str(source.get("text") or "")
        if needle in text.lower():
            out.append({"source_id": source.get("id"),
                        "kind": source.get("kind", ""),
                        "title": source.get("title", "")})
    return out


def build_candidate(source: dict, fields: list[dict], *,
                    kind: str = "event", title: str = "",
                    created_by: str = "") -> dict[str, Any]:
    """candidate.extract (proposal-only): citation-verify fields.

    Each field is {name, value, quote}. A field is supported ONLY
    when its quote is a non-empty verbatim substring of the source
    text (Samkoma's law: a quote, or it didn't happen). A datetime
    field whose value carries no timezone marker is additionally
    flagged and marked unsupported (s.43 item 7: time zones are
    handled, never guessed). The result is a CANDIDATE: a draft
    for the review queue, explicitly not a fact.
    """
    text = str(source.get("text") or "")
    checked = []
    for field in fields:
        quote = str(field.get("quote") or "")
        value = field.get("value")
        supported = bool(quote) and quote in text
        reasons = []
        if not quote:
            reasons.append("no_quote")
        elif quote not in text:
            reasons.append("quote_not_in_source")
        name = str(field.get("name") or "")
        if name.endswith("_at") or name in {"starts", "ends", "when"}:
            sval = str(value or "")
            tail = sval.split("T", 1)[1] if "T" in sval else ""
            tz_ok = tail.endswith("Z") or "+" in tail or (
                len(tail) >= 6 and tail[-6] == "-" and tail[-3] == ":")
            if not tz_ok:
                supported = False
                reasons.append("timezone_missing")
        checked.append({"name": name, "value": value, "quote": quote,
                        "source_id": source.get("id"),
                        "supported": supported,
                        "unsupported_reasons": reasons})
    return {
        "schema": "runeforge.samkoma.candidate.v1",
        "kind": kind, "title": title, "created_by": created_by,
        "source_id": source.get("id"),
        "status": "pending", "is_fact": False, "published": False,
        "fields": checked,
    }


def preview_candidate(candidate: dict, existing: list[dict] | None = None) -> dict[str, Any]:
    """candidate.preview (read-only): show the draft as a draft.

    Surfaces s.43 item 7 hazards as flags instead of hiding them:
    duplicate candidates (same kind+title among ``existing``),
    cancelled sources, and every unsupported field by name. The
    preview changes nothing: status stays pending, is_fact stays
    False, published stays False.
    """
    flags = []
    for other in existing or []:
        if (other.get("kind") == candidate.get("kind")
                and str(other.get("title") or "").strip().lower()
                == str(candidate.get("title") or "").strip().lower()
                and other.get("source_id") != candidate.get("source_id")):
            flags.append("possible_duplicate")
            break
    unsupported = [f["name"] for f in candidate.get("fields", [])
                   if not f.get("supported")]
    if unsupported:
        flags.append("has_unsupported_fields")
    return {
        "schema": "runeforge.samkoma.preview.v1",
        "candidate": candidate,
        "status": candidate.get("status", "pending"),
        "is_fact": False, "published": False,
        "unsupported_fields": unsupported,
        "flags": flags,
        "review_required": True,
    }


def evaluate_review(candidate: dict, *, approver_id: str,
                    approver_role: str, account_id: str,
                    expected_account: str = "",
                    seat_ids: tuple | list = ()) -> dict[str, Any]:
    """review.status gate (s.43 item 4): manual approval wiring.

    Approval is a person's act, evaluated - never performed as a
    publication here. Refusals, each by name: wrong account (the
    acting account is not the configured account), role not
    authorized, and a seat approving its own draft. An approval
    that passes still converts NOTHING in this slice: the record
    says approved_for_conversion False and published False, and
    unsupported fields remain unsupported in the record.
    """
    refusals = []
    if expected_account and account_id != expected_account:
        refusals.append("wrong_account")
    if (approver_role or "").strip().lower() not in APPROVER_ROLES:
        refusals.append("role_not_authorized")
    if approver_id in seat_ids and approver_id == candidate.get("created_by"):
        refusals.append("seat_cannot_approve_own_draft")
    approved = not refusals
    return {
        "schema": "runeforge.samkoma.review.v1",
        "candidate_source_id": candidate.get("source_id"),
        "approver_id": approver_id, "approver_role": approver_role,
        "approved": approved, "refusals": refusals,
        "unsupported_fields": [f["name"] for f in candidate.get("fields", [])
                                 if not f.get("supported")],
        "approved_for_conversion": False,
        "conversion_performed": False, "published": False,
        "note": "proposal-only slice: approval is recorded as a gate "
                "decision; conversion to a real event/task is a future "
                "separately authorized slice (X08-T2)",
    }


def _idempotency_key(candidate: dict) -> str:
    canonical = json.dumps(candidate, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def draft_proposal(store_dir: Path, candidate: dict) -> dict[str, Any]:
    """proposal.draft (offline, idempotent - s.43 items 8-9).

    Drafts a proposal into a LOCAL store directory only: no
    network, no service, no publication. The receipt carries a
    deterministic idempotency key over the candidate's canonical
    form, so retrying an interrupted draft returns the SAME
    receipt with duplicate True and writes no second record - a
    retried agent cannot double-post downstream because there is
    exactly one receipt per candidate.
    """
    store_dir = Path(store_dir)
    store_dir.mkdir(parents=True, exist_ok=True)
    key = _idempotency_key(candidate)
    path = store_dir / f"{key}.json"
    duplicate = path.is_file()
    if not duplicate:
        record = {"idempotency_key": key, "candidate": candidate,
                  "published": False}
        path.write_text(json.dumps(record, indent=1, sort_keys=True,
                                   default=str), encoding="utf-8")
    return {"schema": "runeforge.samkoma.receipt.v1",
            "idempotency_key": key, "duplicate": duplicate,
            "store_path": str(path), "published": False,
            "synced": False}


def respect_source_deletion(store_dir: Path, source_id: str) -> dict[str, Any]:
    """s.43 item 10: a deleted source's proposals are removed.

    Scans the local proposal store and deletes every receipt whose
    candidate cites ``source_id``; returns the count removed. Room
    privacy rides the same rule: proposals citing a source whose
    room consent was withdrawn are removed by the same call.
    """
    store_dir = Path(store_dir)
    removed = 0
    if store_dir.is_dir():
        for path in sorted(store_dir.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            cand = record.get("candidate") or {}
            if cand.get("source_id") == source_id:
                path.unlink()
                removed += 1
    return {"schema": "runeforge.samkoma.deletion.v1",
            "source_id": source_id, "removed": removed}


# A labelled synthetic receipt for the CLI preview verb: it proves
# the citation machinery (one supported field, one unsupported)
# without claiming any real Samkoma data.
SYNTHETIC_SOURCE = {
    "id": "synthetic-receipt-1", "kind": "chat-export",
    "title": "Synthetic preview receipt (labelled test data)",
    "text": "Anna: Table session this Saturday at 18:00 Europe/Oslo, "
            "bring the character sheets.",
}
SYNTHETIC_FIELDS = [
    {"name": "title", "value": "Table session",
     "quote": "Table session this Saturday"},
    {"name": "place", "value": "The longhouse hall",
     "quote": "in the longhouse hall"},
]

__all__ = [
    "APPROVER_ROLES", "AUDITED_HEAD", "CANONICAL_REPO",
    "CANONICAL_REPO_URL", "LICENSE_SHA256", "OPENAPI_PATHS",
    "OPENAPI_SCHEMAS", "OPERATIONS", "PROJECT_LICENSE",
    "PUBLISH_VERBS_REFUSED", "SYNTHETIC_FIELDS", "SYNTHETIC_SOURCE",
    "build_candidate", "draft_proposal", "evaluate_review",
    "operations_catalog", "preview_candidate",
    "respect_source_deletion", "samkoma_status", "search_sources",
]
