"""X.10 Mythic Scribing Foundry: private writing workflow (s.45).

The Foundry (``hrabanazviking/Mythic-Scribing-Foundry``, PRIVATE,
audited at ``9da00e5ba77c``) is Volmarr's automated long-form
production system: package ``mythscribe`` 0.1.0 (Proprietary, no
LICENSE file; license text in pyproject only), a click CLI whose
pipeline is INGEST -> DISTILL -> CANONIZE -> DISCOVER ->
ARCHITECT -> SOURCE -> SCRIBE -> CRITIQUE -> REFORGE -> VERIFY
-> KEEP -> PUBLISH -> LEARN. Audited from source, not README:
the ingest/outline/draft/draft-status/draft-retry commands and
the council review, publisher build-book and models cost
commands are real; the ``verify`` and ``revise`` commands are
still stubs announcing NOT_IMPLEMENTED, so claim verification
and revision are reported UNSUPPORTED here, never faked.

This module is the Hermes-side connector. It is original
volmarr-core code; no Foundry source is copied or vendored, and
NO manuscript text, author notes or corpus content ever passes
through it: it measures a staged tree's structure only (HEAD,
package version, module count), plans stepwise jobs, verifies
citations against source text supplied by the caller, and keeps
suggestions, checkpoints and receipts in a local store.

Scope law (section 45): opt-in, default-off, local-only.
``author_work`` and ``persona_core`` are separate namespaces and
a manuscript is never a persona instruction by default.
Suggestions/diffs live in their own store until accepted.
Citations are exact: a quote is supported only as a verbatim
substring within the quote-length policy. Every job carries
provenance and a cost-receipt requirement; long jobs checkpoint
per chapter and resume. There is NO publish/upload path: the
Foundry's own publish verb is refused by name here.
``production_ready`` is False.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

CANONICAL_REPO = "hrabanazviking/Mythic-Scribing-Foundry"
CANONICAL_REPO_URL = "https://github.com/hrabanazviking/Mythic-Scribing-Foundry"
AUDITED_HEAD = "9da00e5ba77c39a43c670e9e2f7398dbeaa4c594"
PACKAGE_VERSION = "0.1.0"
PROJECT_LICENSE = "Proprietary"
ADAPTER_VERSION = "0.1.0"
QUOTE_MAX_CHARS = 250
NAMESPACES = ("author_work", "persona_core")
MANUSCRIPT_KINDS = ("manuscript", "draft", "chapter", "book")

# Section 45 item 4 step kinds, each with its audited basis.
STEP_KINDS = (
    {"kind": "research_indexing", "supported": True, "basis": "mythscribe ingest CLI (real) + well.ingest / well.search SemanticIndex"},
    {"kind": "outlining", "supported": True, "basis": "mythscribe outline CLI (real) + architect package"},
    {"kind": "planning", "supported": True, "basis": "propose-books / create-book CLI (real) + architect packets"},
    {"kind": "drafting", "supported": True, "basis": "draft / draft-status / draft-retry CLI (real) + scribe.jobs JobStore"},
    {"kind": "claim_verification", "supported": False, "basis": "mythscribe verify CLI is a stub announcing NOT_IMPLEMENTED at the audited HEAD"},
    {"kind": "style_consistency", "supported": True, "basis": "scribe.voice + scribe.rules modules (no dedicated CLI verb)"},
    {"kind": "critique", "supported": True, "basis": "council review CLI (real, replaces the stub) + council editors"},
    {"kind": "revision", "supported": False, "basis": "mythscribe revise CLI is a stub at the audited HEAD; reforger module has no verified CLI path"},
    {"kind": "publication_preparation", "supported": True, "basis": "publisher build-book CLI (real) + exporters for epub/pdf/docx/markdown/html; preparation only"},
)
PUBLISH_VERBS_REFUSED = ("publish", "upload", "distribute", "release")


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if value is None:
        return default
    return bool(value)


def steps_catalog() -> dict[str, Any]:
    """The s.45 step catalog: supported vs unsupported, honestly."""
    return {
        "schema": "runeforge.scribing.catalog.v1",
        "service": "volmarr-scribing",
        "canonical_repo": CANONICAL_REPO,
        "audited_head": AUDITED_HEAD,
        "package_version": PACKAGE_VERSION,
        "steps": [dict(row) for row in STEP_KINDS],
        "publish_verbs_refused": list(PUBLISH_VERBS_REFUSED),
        "publishes_anything": False,
        "namespaces": list(NAMESPACES),
        "quote_max_chars": QUOTE_MAX_CHARS,
        "production_ready": False,
    }


def _measure_tree(root: Path) -> dict[str, Any]:
    """Measure a staged Foundry checkout truthfully (no git call).

    Reads .git/HEAD + refs and pyproject.toml only, and counts
    Python modules by filename. Manuscript and corpus files are
    NEVER opened: private content cannot leak through status.
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
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8")
        match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
        if match:
            record["package_version"] = match.group(1)
    pkg = root / "mythscribe"
    if pkg.is_dir():
        record["module_count"] = sum(1 for _ in pkg.rglob("*.py"))
    record["status"] = "measured" if head else "tree_partial"
    return record


def scribing_status(ctx, recorded_at: str | None = None) -> dict[str, Any]:
    """Truthful adapter status: config, staged tree, hard limits."""
    enabled = _as_bool(ctx.get_config("scribing_enabled", False))
    root_value = str(ctx.get_config("scribing_root", "") or "").strip()
    tree = _measure_tree(Path(root_value).expanduser()) if root_value else {
        "root": "", "present": False, "status": "not_configured"}
    return {
        "schema": "runeforge.scribing.status.v1",
        "service": "volmarr-scribing",
        "recorded_at": recorded_at,
        "enabled": enabled,
        "configured": bool(root_value),
        "canonical_repo": CANONICAL_REPO,
        "canonical_repo_url": CANONICAL_REPO_URL,
        "audited_head": AUDITED_HEAD,
        "package_version": PACKAGE_VERSION,
        "license": PROJECT_LICENSE,
        "tree": tree,
        "mode": "opt-in, local-only private writing workflow; planning + local store only",
        "privacy": "local-only; private-source egress denied; no manuscript content is read by status",
        "publishes_anything": False,
        "production_ready": False,
    }


def assign_namespace(kind: str, requested: str | None = None) -> dict[str, Any]:
    """s.45 item 3: author_work / persona_core separation.

    Default namespace is author_work. A manuscript-kind item can
    NEVER be assigned to persona_core: a manuscript is not a
    persona instruction by default, and the refusal is named.
    """
    wanted = (requested or "author_work").strip()
    if wanted not in NAMESPACES:
        return {"namespace": "author_work", "requested": wanted,
                "refused": "unknown_namespace", "persona_instruction": False}
    if kind in MANUSCRIPT_KINDS and wanted == "persona_core":
        return {"namespace": "author_work", "requested": wanted,
                "refused": "manuscript_not_persona_instruction",
                "persona_instruction": False}
    return {"namespace": wanted, "requested": wanted, "refused": None,
            "persona_instruction": wanted == "persona_core" and kind not in MANUSCRIPT_KINDS}


def verify_citation(source_text: str, quote: str, source_id: str = "") -> dict[str, Any]:
    """s.45 item 6: exact citation check (fabrication refused).

    A citation is supported ONLY when its quote is a non-empty
    verbatim substring of the source text AND within the
    quote-length policy (QUOTE_MAX_CHARS). Anything else is
    unsupported with the reason named - never repaired.
    """
    reasons = []
    if not quote:
        reasons.append("no_quote")
    elif len(quote) > QUOTE_MAX_CHARS:
        reasons.append("quote_exceeds_policy")
    elif quote not in (source_text or ""):
        reasons.append("quote_not_in_source")
    return {"schema": "runeforge.scribing.citation.v1",
            "source_id": source_id, "supported": not reasons,
            "unsupported_reasons": reasons,
            "quote_chars": len(quote or ""),
            "quote_max_chars": QUOTE_MAX_CHARS}


def build_job_plan(steps: list[dict], *, book_ref: str = "",
                   created_by: str = "") -> dict[str, Any]:
    """Stepwise job plan (s.45 items 4+7): pure and deterministic.

    Each requested step is {kind, chapter}. Unknown kinds,
    audited-unsupported kinds and every publish verb are refused
    BY NAME. Planned steps carry provenance (namespace, creator,
    audited HEAD), a chapter checkpoint, and a cost-receipt
    requirement mirroring the Foundry's own CostLedger. The
    plan runs nothing and reads no manuscript.
    """
    known = {row["kind"]: row for row in STEP_KINDS}
    planned: list[dict[str, Any]] = []
    refused: list[dict[str, Any]] = []
    for index, step in enumerate(steps or []):
        kind = str(step.get("kind") or "")
        if kind in PUBLISH_VERBS_REFUSED:
            refused.append({"index": index, "kind": kind, "reason": "publish_refused"})
            continue
        row = known.get(kind)
        if row is None:
            refused.append({"index": index, "kind": kind, "reason": "unknown_step"})
            continue
        if not row["supported"]:
            refused.append({"index": index, "kind": kind, "reason": "step_unsupported"})
            continue
        chapter = step.get("chapter")
        planned.append({
            "index": index, "kind": kind, "chapter": chapter,
            "namespace": "author_work", "persona_instruction": False,
            "checkpoint": f"chapter-{chapter}" if chapter is not None else f"step-{index}",
            "provenance": {"created_by": created_by, "book_ref": book_ref,
                           "audited_head": AUDITED_HEAD, "basis": row["basis"]},
            "cost_receipt_required": True,
        })
    body = {"steps": planned, "refused": refused, "book_ref": book_ref}
    plan_key = hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()
    return {"schema": "runeforge.scribing.plan.v1", "service": "volmarr-scribing",
            "plan_key": plan_key, "steps": planned, "refused": refused,
            "step_count": len(planned), "refused_count": len(refused),
            "namespace": "author_work", "publishes_anything": False,
            "runs_foundry": False, "production_ready": False}


def cost_receipt(*, plan_key: str, provider: str, model: str,
                 tokens_in: int, tokens_out: int,
                 rate_per_1k: float = 0.0) -> dict[str, Any]:
    """A cost receipt for a planned job (s.45 item 7)."""
    total_tokens = int(tokens_in) + int(tokens_out)
    return {"schema": "runeforge.scribing.receipt.v1", "plan_key": plan_key,
            "provider": provider, "model": model,
            "tokens_in": int(tokens_in), "tokens_out": int(tokens_out),
            "estimated_cost": round(total_tokens / 1000.0 * float(rate_per_1k), 6),
            "local_only": True}


def _suggestion_key(suggestion: dict) -> str:
    canonical = json.dumps(suggestion, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def draft_suggestion(store_dir: Path, suggestion: dict) -> dict[str, Any]:
    """s.45 item 5: suggestions live separately until accepted.

    The suggestion is written ONLY under ``store_dir/suggestions``
    with status ``proposed`` - never into any manuscript location
    (this adapter holds no manuscript path at all). Retrying the
    same suggestion returns the same key with duplicate True.
    """
    store_dir = Path(store_dir) / "suggestions"
    store_dir.mkdir(parents=True, exist_ok=True)
    key = _suggestion_key(suggestion)
    path = store_dir / f"{key}.json"
    duplicate = path.is_file()
    if not duplicate:
        record = {"key": key, "status": "proposed", "accepted": False,
                  "suggestion": suggestion, "applied_text": None}
        path.write_text(json.dumps(record, indent=1, sort_keys=True, default=str), encoding="utf-8")
    return {"schema": "runeforge.scribing.suggestion.v1", "key": key,
            "duplicate": duplicate, "status": "proposed",
            "store_path": str(path), "applied": False}


def _load_suggestion(store_dir: Path, key: str) -> tuple[Path, dict]:
    path = Path(store_dir) / "suggestions" / f"{key}.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    return path, record


def accept_suggestion(store_dir: Path, key: str) -> dict[str, Any]:
    """Accept a suggestion: its proposed text becomes applied.

    The record keeps BOTH the previous text and the proposed
    text, so an editorial rollback can restore exactly.
    """
    path, record = _load_suggestion(store_dir, key)
    suggestion = record["suggestion"]
    record["status"] = "accepted"
    record["accepted"] = True
    record["applied_text"] = suggestion.get("proposed_text")
    record["previous_text"] = suggestion.get("previous_text")
    path.write_text(json.dumps(record, indent=1, sort_keys=True, default=str), encoding="utf-8")
    return {"schema": "runeforge.scribing.suggestion.v1", "key": key,
            "status": "accepted", "applied": True,
            "applied_text": record["applied_text"]}


def rollback_suggestion(store_dir: Path, key: str) -> dict[str, Any]:
    """Editorial rollback: restore the pre-acceptance text."""
    path, record = _load_suggestion(store_dir, key)
    restored = record.get("previous_text")
    record["status"] = "rolled_back"
    record["accepted"] = False
    record["applied_text"] = restored
    path.write_text(json.dumps(record, indent=1, sort_keys=True, default=str), encoding="utf-8")
    return {"schema": "runeforge.scribing.suggestion.v1", "key": key,
            "status": "rolled_back", "applied": False,
            "restored_text": restored}


def write_checkpoint(store_dir: Path, plan: dict, completed: list[int]) -> dict[str, Any]:
    """Chapter-level checkpoint for a plan (s.45 item 7)."""
    store_dir = Path(store_dir) / "checkpoints"
    store_dir.mkdir(parents=True, exist_ok=True)
    path = store_dir / f"{plan['plan_key']}.json"
    record = {"plan_key": plan["plan_key"], "plan": plan,
              "completed_indexes": sorted(int(i) for i in completed)}
    path.write_text(json.dumps(record, indent=1, sort_keys=True, default=str), encoding="utf-8")
    return {"schema": "runeforge.scribing.checkpoint.v1",
            "plan_key": plan["plan_key"], "store_path": str(path),
            "completed_count": len(record["completed_indexes"])}


def resume_plan(store_dir: Path, plan_key: str) -> dict[str, Any]:
    """Resume after interruption: the steps not yet checkpointed."""
    path = Path(store_dir) / "checkpoints" / f"{plan_key}.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    done = set(record["completed_indexes"])
    remaining = [s for s in record["plan"]["steps"] if s["index"] not in done]
    return {"schema": "runeforge.scribing.resume.v1", "plan_key": plan_key,
            "completed_count": len(done), "remaining": remaining,
            "remaining_count": len(remaining), "resumed": True}


# A labelled synthetic plan for the CLI plan verb: it proves the
# planning machinery (one unsupported refusal, one publish
# refusal) without touching any real manuscript or corpus.
SYNTHETIC_STEPS = [
    {"kind": "research_indexing", "chapter": 1},
    {"kind": "drafting", "chapter": 1},
    {"kind": "claim_verification", "chapter": 1},
    {"kind": "publish", "chapter": 1},
]

__all__ = [
    "ADAPTER_VERSION", "AUDITED_HEAD", "CANONICAL_REPO",
    "CANONICAL_REPO_URL", "MANUSCRIPT_KINDS", "NAMESPACES",
    "PACKAGE_VERSION", "PROJECT_LICENSE", "PUBLISH_VERBS_REFUSED",
    "QUOTE_MAX_CHARS", "STEP_KINDS", "SYNTHETIC_STEPS",
    "accept_suggestion", "assign_namespace", "build_job_plan",
    "cost_receipt", "draft_suggestion", "resume_plan",
    "rollback_suggestion", "scribing_status", "steps_catalog",
    "verify_citation", "write_checkpoint",
]
