"""Derived memory digest: bounded, verbatim, source-linked (W06 / M3).

Design: docs/modernization/P5_DESIGN_DRAFT.md section 4.3 and
ticket P.015. The digest is what a small-context model receives
by default. Its laws:

- **Verbatim only.** Following the persona runtime's section 7
  law, digest entries are verbatim source sections, selected --
  never paraphrased, never summarised. No generated summary text
  exists anywhere in this module.
- **Source-linked.** Every entry carries its stable section id,
  its section hash and its source hash, so each digest line is
  traceable to exact source bytes via ``PersonaIndex.cite()``.
- **Generation-bound.** A digest names the corpus generation it
  was derived from; a stale digest is labelled stale, never
  silently served as current.
- **Derived only.** The digest lives under ``generated/`` and
  may be deleted and rebuilt at any time. It never writes back
  over an authored source (P.015: authored entries outrank agent
  observations, always).
- **Optional.** Digest generation is a second, separate opt-in
  (``memory_corpus_digest_enabled``, default false). A profile
  may run retrieval-only with no digest at all.

Selection is deterministic: explicitly pinned headings first (in
source order), then -- when a query is supplied -- the W04
retrieval order for that query, then remaining sections in
source order, whole sections only, until the character budget
is spent. A section that does not fit whole is excluded and
reported, never truncated.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .memory_corpus import MemoryCorpus, MemoryCorpusError

__all__ = [
    "DEFAULT_DIGEST_MAX_CHARS", "DIGEST_KIND", "build_digest",
    "digest_path", "digest_status", "load_digest", "save_digest",
]

DIGEST_KIND = "volmarr-memory-digest"
DIGEST_VERSION = 1
DEFAULT_DIGEST_MAX_CHARS = 6000


def digest_path(corpus: MemoryCorpus) -> Path:
    return corpus.root / "generated" / "memory_digest.json"


def _sections(corpus: MemoryCorpus) -> list[dict[str, Any]]:
    """All corpus sections in source order, with provenance."""
    manifest = corpus.library.store.load()
    out: list[dict[str, Any]] = []
    docs = sorted(manifest["documents"].values(),
                  key=lambda d: d["path"])
    for doc in docs:
        for span in doc.get("sections") or []:
            out.append({
                "stable_id": span["stable_id"],
                "document_id": doc["document_id"],
                "role": doc["role"], "path": doc["path"],
                "heading": span.get("heading", ""),
                "byte_start": span["byte_start"],
                "byte_end": span["byte_end"],
                "section_sha256": span["sha256"],
                "source_sha256": doc["sha256"],
                "trust_class": doc.get("trust_class", ""),
                "privacy_class": doc.get("privacy_class", "")})
    return out


def build_digest(corpus: MemoryCorpus, *,
                 max_chars: int = DEFAULT_DIGEST_MAX_CHARS,
                 pinned_headings: Any = (),
                 query: str = "") -> dict[str, Any]:
    """Build the digest for the corpus's CURRENT generation."""
    budget = max(256, int(max_chars))
    pinned = {str(h).strip().casefold() for h in pinned_headings or ()}
    sections = _sections(corpus)
    by_id = {s["stable_id"]: s for s in sections}
    order: list[str] = []
    seen: set[str] = set()

    def _take(stable_id: str) -> None:
        if stable_id in by_id and stable_id not in seen:
            seen.add(stable_id)
            order.append(stable_id)

    for section in sections:
        if str(section["heading"]).strip().casefold() in pinned:
            _take(section["stable_id"])
    if query:
        try:
            found = corpus.retrieve(query, limit=20)
            for row in found["results"]:
                _take(row["stable_id"])
        except Exception:
            pass  # an unbuilt index degrades to source order only
    for section in sections:
        _take(section["stable_id"])

    entries: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    used = 0
    for stable_id in order:
        section = by_id[stable_id]
        cited = corpus.cite(stable_id)
        text = cited["text"]
        if entries and used + len(text) > budget:
            excluded.append({"stable_id": stable_id,
                             "reason": "over_digest_budget",
                             "section_chars": len(text)})
            continue
        if not entries and len(text) > budget:
            excluded.append({"stable_id": stable_id,
                             "reason": "section_exceeds_digest_budget",
                             "section_chars": len(text)})
            continue
        entries.append({
            "stable_id": stable_id,
            "document_id": section["document_id"],
            "role": section["role"], "heading": section["heading"],
            "byte_start": section["byte_start"],
            "byte_end": section["byte_end"],
            "section_sha256": section["section_sha256"],
            "source_sha256": section["source_sha256"],
            "provenance": "authored",
            "text": text})
        used += len(text)
    generation = corpus.library.store.load()["generation"]
    return {"kind": DIGEST_KIND, "version": DIGEST_VERSION,
            "namespace_id": corpus.namespace_id,
            "corpus_generation": generation, "stale": False,
            "max_chars": budget, "total_chars": used,
            "entries": entries, "excluded": excluded}


def digest_status(corpus: MemoryCorpus,
                  digest: dict[str, Any] | None) -> dict[str, Any]:
    """Honest digest state: absent / current / stale, by name."""
    current = corpus.library.store.load()["generation"]
    if digest is None:
        return {"state": "absent", "corpus_generation": current,
                "digest_generation": None}
    stale = digest.get("corpus_generation") != current
    return {"state": "stale" if stale else "current",
            "corpus_generation": current,
            "digest_generation": digest.get("corpus_generation"),
            "entries": len(digest.get("entries") or []),
            "total_chars": digest.get("total_chars", 0)}


def save_digest(corpus: MemoryCorpus,
                digest: dict[str, Any]) -> Path:
    path = digest_path(corpus)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(digest, indent=2, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    return path


def load_digest(corpus: MemoryCorpus) -> dict[str, Any] | None:
    path = digest_path(corpus)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MemoryCorpusError(f"digest unreadable: {exc}") from exc
    if not isinstance(data, dict) or data.get("kind") != DIGEST_KIND:
        raise MemoryCorpusError("digest file has the wrong kind")
    status = digest_status(corpus, data)
    data["stale"] = status["state"] == "stale"
    return data
