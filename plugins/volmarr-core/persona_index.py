"""Incremental section index, retrieval and full-fidelity read (W04 / P2).

Implements roadmap tickets P.006/P.007 per
docs/modernization/P2_DESIGN_DRAFT.md, building on the W03
canonical library (``canonical_library`` manifest, byte ranges
and source-byte hashes) and on the section 13 scorer in
``persona_runtime`` -- there is no second compiler, parser,
slugger or scorer here (roadmap section 8 law).

Surfaces:

- ``PersonaIndex.sync`` -- incremental SQLite FTS5 section
  index at ``generated/sections.sqlite``: sections, logical
  subspans with continuation handles, an append-only indexing
  journal, per-document transactions keyed on the W03 manifest
  generation + per-document source hashes.
- ``PersonaIndex.retrieve`` -- FTS candidate generation
  (unicode61 + trigram tables over ONE search projection)
  re-scored by the untouched section 13 ``retrieval_score``;
  the section 13 contact rule survives; a named BM25 fusion
  weight is added on top and recorded. Every call writes a
  retrieval receipt (draft section 6).
- ``PersonaIndex.cite`` -- exact-citation mode: text sliced
  from the canonical source at serve time and hash-verified;
  never served from the FTS store.
- ``PersonaIndex.read_page`` / ``read_section_page`` -- paged
  full-fidelity read: no redaction, no formatting; page
  concatenation reproduces the source byte-for-byte.
- Embeddings consent gate (P.007): off by default. Vectors
  live in a separate ``generated/semantic/embeddings.sqlite``;
  a source is embedded only under an explicit per-source
  consent record, cloud embedding of a private source is
  refused at grant time without a recorded override, and
  revocation deletes the source's vectors in the same
  transaction. Without a consented vector the section 13
  ``semantic`` component stays ``None`` -- never faked.

One deviation from the draft's literal schema, recorded in
the W04 implementation record: ``search_rows.row_pk`` uses a
large offset for subspan rows (the draft's ``= section_pk or
subspan_pk`` collides between the two populations; FTS5
content rowids must be unique).
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import sqlite3
import struct
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .canonical_library import ManifestStore
from .persona_runtime import (
    classify_task,
    priority_level,
    retrieval_score,
    retrieve_sections,
    section_priority,
    section_tags,
)

__all__ = [
    "BM25_FUSION_WEIGHT", "CANDIDATE_CAP", "ConsentError",
    "CitationError", "DEFAULT_PAGE_BYTES", "INDEX_SCHEMA_VERSION",
    "IndexNotBuiltError", "MAX_FTS_QUERY_CHARS", "PersonaIndex",
    "PersonaIndexError", "SEMANTIC_FUSION_WEIGHT",
    "SUBSPAN_OVERLAP_BYTES", "SUBSPAN_TARGET_BYTES",
    "SUBSPAN_THRESHOLD_BYTES", "fallback_retrieve",
    "measure_tokenizers", "normalize_search_text",
]

INDEX_SCHEMA_VERSION = 1
SUBSPAN_THRESHOLD_BYTES = 32 * 1024
SUBSPAN_TARGET_BYTES = 8 * 1024
SUBSPAN_OVERLAP_BYTES = 256
CANDIDATE_CAP = 200
MAX_FTS_QUERY_CHARS = 2048
BM25_FUSION_WEIGHT = 0.15
SEMANTIC_FUSION_WEIGHT = 0.20
DEFAULT_PAGE_BYTES = 64 * 1024
_SUBSPAN_ROW_OFFSET = 1 << 40
_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)


class PersonaIndexError(Exception):
    """A persona-index failure."""


class IndexNotBuiltError(PersonaIndexError):
    """No index has been built for this library yet."""


class CitationError(PersonaIndexError):
    """An exact-citation failure (unknown id or hash mismatch)."""


class ConsentError(PersonaIndexError):
    """An embeddings consent-gate refusal."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_search_text(text: str) -> str:
    """The ONE search-projection normalisation (draft 3.2).

    Unicode NFC + casefold; diacritics are preserved in the
    stored field (the tokenizer folds at tokenise time).
    Source bytes are never touched by this function.
    """
    return unicodedata.normalize("NFC", text).casefold()


def _word_terms(query: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for term in _WORD_RE.findall((query or "")[:MAX_FTS_QUERY_CHARS]):
        folded = term.casefold()
        if folded not in seen:
            seen.add(folded)
            terms.append(folded)
    return terms


def _fts_phrase(text: str) -> str:
    return '"' + text.replace('"', '""') + '"'


def _slice_bytes(path: Path, start: int, end: int,
                 work_unit: int = 1024 * 1024) -> bytes:
    out = bytearray()
    remaining = end - start
    with open(path, "rb") as fh:
        fh.seek(start)
        while remaining > 0:
            chunk = fh.read(min(work_unit, remaining))
            if not chunk:
                break
            out += chunk
            remaining -= len(chunk)
    return bytes(out)


def _hash_file(path: Path, work_unit: int = 1024 * 1024) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(work_unit)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def _line_span(path: Path, byte_start: int, byte_end: int) -> tuple[int, int]:
    """1-based (line_start, line_end) for a byte range, streamed."""
    newlines_before = 0
    newlines_inside = 0
    pos = 0
    with open(path, "rb") as fh:
        while pos < byte_end:
            chunk = fh.read(min(1024 * 1024, byte_end - pos))
            if not chunk:
                break
            if pos < byte_start:
                cut = min(len(chunk), byte_start - pos)
                newlines_before += chunk[:cut].count(b"\n")
                if pos + len(chunk) > byte_start:
                    rest = chunk[cut:]
                    newlines_inside += rest.count(b"\n")
            else:
                newlines_inside += chunk.count(b"\n")
            pos += len(chunk)
    line_start = newlines_before + 1
    line_end = line_start + newlines_inside
    return line_start, line_end


def _subspan_bounds(data: bytes, target: int,
                    overlap: int) -> list[tuple[int, int, str, int]]:
    """Split *data* into (start, end, boundary_kind, overlap_prev).

    Boundaries prefer paragraph breaks, then sentence ends,
    then line breaks, else a hard split. ASCII separators are
    safe search keys in UTF-8: they never occur inside a
    multi-byte sequence. Concatenating the spans while
    dropping each span's first ``overlap_prev`` bytes
    reproduces *data* exactly.
    """
    bounds: list[tuple[int, int, str, int]] = []
    start = 0
    overlap_prev = 0
    total = len(data)
    while total - start > target:
        want = start + target
        floor = start + target // 2
        end = -1
        kind = "hard"
        for sep, name in ((b"\n\n", "paragraph"), (b". ", "sentence"),
                          (b"\n", "line")):
            idx = data.rfind(sep, floor, want)
            if idx >= 0:
                end = idx + len(sep)
                kind = name
                break
        if end <= start:
            end = want
            kind = "hard"
        bounds.append((start, end, kind, overlap_prev))
        nxt = end - overlap if end - overlap > start else end
        overlap_prev = end - nxt
        start = nxt
    bounds.append((start, total, "end", overlap_prev))
    return bounds

_SCHEMA = """
CREATE TABLE IF NOT EXISTS index_meta(
  key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS documents(
  document_id TEXT PRIMARY KEY, persona_id TEXT NOT NULL,
  role TEXT NOT NULL, path TEXT NOT NULL, sha256 TEXT NOT NULL,
  byte_length INTEGER NOT NULL, revision INTEGER NOT NULL,
  manifest_generation INTEGER NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sections(
  section_pk INTEGER PRIMARY KEY,
  document_id TEXT NOT NULL REFERENCES documents,
  stable_id TEXT NOT NULL, section_id TEXT NOT NULL,
  role TEXT NOT NULL, heading TEXT NOT NULL, level INTEGER NOT NULL,
  ordinal INTEGER NOT NULL, byte_start INTEGER NOT NULL,
  byte_end INTEGER NOT NULL, line_start INTEGER NOT NULL,
  line_end INTEGER NOT NULL, section_sha256 TEXT NOT NULL,
  priority REAL NOT NULL, priority_level TEXT NOT NULL,
  tags TEXT NOT NULL, in_kernel INTEGER NOT NULL,
  UNIQUE(document_id, section_id));
CREATE TABLE IF NOT EXISTS subspans(
  subspan_pk INTEGER PRIMARY KEY,
  section_pk INTEGER NOT NULL REFERENCES sections,
  ordinal INTEGER NOT NULL, byte_start INTEGER NOT NULL,
  byte_end INTEGER NOT NULL, overlap_prev_bytes INTEGER NOT NULL,
  boundary_kind TEXT NOT NULL, subspan_sha256 TEXT NOT NULL,
  UNIQUE(section_pk, ordinal));
CREATE TABLE IF NOT EXISTS search_rows(
  row_pk INTEGER PRIMARY KEY, granularity TEXT NOT NULL,
  section_pk INTEGER NOT NULL REFERENCES sections,
  heading_norm TEXT NOT NULL, body_norm TEXT NOT NULL,
  tags_text TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS index_journal(
  generation INTEGER NOT NULL, document_id TEXT NOT NULL,
  old_sha256 TEXT, new_sha256 TEXT, change_kind TEXT NOT NULL,
  sections_added INTEGER, sections_removed INTEGER,
  committed_at TEXT NOT NULL,
  PRIMARY KEY(generation, document_id));
"""

_FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS sections_fts USING fts5(
  heading_norm, body_norm, tags_text,
  content='search_rows', content_rowid='row_pk',
  tokenize='unicode61 remove_diacritics 2');
CREATE VIRTUAL TABLE IF NOT EXISTS sections_fts_trigram USING fts5(
  body_norm, content='search_rows', content_rowid='row_pk',
  tokenize='trigram');
"""


class PersonaIndex:
    """The P2 index + retrieval service over one W03 library.

    ``root`` is the library root (sources in place, derived
    state under ``root/generated``). Thresholds are operations
    values, injectable for tests; they never appear on a
    document record and never limit what may be indexed.
    """

    def __init__(self, root: Path, persona_id: str, *,
                 subspan_threshold: int = SUBSPAN_THRESHOLD_BYTES,
                 subspan_target: int = SUBSPAN_TARGET_BYTES,
                 subspan_overlap: int = SUBSPAN_OVERLAP_BYTES,
                 candidate_cap: int = CANDIDATE_CAP) -> None:
        self.root = Path(root)
        self.persona_id = persona_id
        self.generated = self.root / "generated"
        self.db_path = self.generated / "sections.sqlite"
        self.receipts_dir = self.generated / "receipts"
        self.semantic_dir = self.generated / "semantic"
        self.embeddings_path = self.semantic_dir / "embeddings.sqlite"
        self.subspan_threshold = subspan_threshold
        self.subspan_target = subspan_target
        self.subspan_overlap = subspan_overlap
        self.candidate_cap = candidate_cap

    # -- plumbing -------------------------------------------------

    def _manifest(self) -> dict[str, Any]:
        return ManifestStore(self.root).load()

    def _connect(self, readonly: bool = False) -> sqlite3.Connection:
        if readonly:
            conn = sqlite3.connect(
                f"file:{self.db_path}?mode=ro", uri=True)
        else:
            self.generated.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(_SCHEMA)
        conn.executescript(_FTS_SCHEMA)
        conn.execute(
            "INSERT OR IGNORE INTO index_meta(key, value) VALUES "
            "('schema_version', ?)", (str(INDEX_SCHEMA_VERSION),))
        conn.execute(
            "INSERT OR IGNORE INTO index_meta(key, value) VALUES "
            "('built_from_manifest_generation', '0')")
        conn.commit()

    def _meta(self, conn: sqlite3.Connection, key: str) -> str | None:
        row = conn.execute(
            "SELECT value FROM index_meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def _source_path(self, relpath: str) -> Path:
        candidate = (self.root / relpath).resolve()
        root_resolved = self.root.resolve()
        if candidate != root_resolved and \
                root_resolved not in candidate.parents:
            raise PersonaIndexError(f"path escapes library root: {relpath}")
        return candidate

    def index_status(self) -> dict[str, Any]:
        if not self.db_path.exists():
            return {"status": "unbuilt", "index_generation": 0,
                    "manifest_generation": self._manifest()["generation"]}
        conn = self._connect(readonly=True)
        try:
            built = int(self._meta(conn, "built_from_manifest_generation") or 0)
            sections = conn.execute("SELECT COUNT(*) c FROM sections").fetchone()["c"]
            subspans = conn.execute("SELECT COUNT(*) c FROM subspans").fetchone()["c"]
        finally:
            conn.close()
        gen = self._manifest()["generation"]
        return {"status": "current" if built == gen else "outdated",
                "index_generation": built, "manifest_generation": gen,
                "sections": sections, "subspans": subspans}

    # -- P.006a/b: incremental indexer ----------------------------

    def sync(self, force: bool = False) -> dict[str, Any]:
        """Bring the index to the manifest generation.

        Unchanged documents (same source hash) are not touched;
        each changed document is replaced in ONE transaction;
        the manifest generation advances in ``index_meta`` only
        after every document transaction has committed, so a
        crash leaves the index honestly ``outdated``, never
        mixed. ``force`` re-indexes every document.
        """
        manifest = self._manifest()
        generation = int(manifest["generation"])
        docs = manifest["documents"]
        conn = self._connect()
        changed: list[str] = []
        removed: list[str] = []
        try:
            self._ensure_schema(conn)
            built = int(self._meta(conn, "built_from_manifest_generation") or 0)
            if built == generation and not force:
                conn.close()
                status = self.index_status()
                status.update({"changed": [], "removed": [],
                               "generation": generation})
                return status
            known = {row["document_id"]: row["sha256"] for row in
                     conn.execute("SELECT document_id, sha256 FROM documents")}
            for doc_id in sorted(known):
                if doc_id not in docs:
                    self._drop_document(conn, doc_id, known[doc_id], generation)
                    removed.append(doc_id)
            for doc_id in sorted(docs):
                record = docs[doc_id]
                if not force and known.get(doc_id) == record["sha256"]:
                    conn.execute(
                        "UPDATE documents SET manifest_generation = ? "
                        "WHERE document_id = ?", (generation, doc_id))
                    conn.commit()
                    continue
                self._index_document(conn, record, generation,
                                     known.get(doc_id))
                changed.append(doc_id)
            conn.execute(
                "INSERT INTO sections_fts(sections_fts) VALUES('rebuild')")
            conn.execute(
                "INSERT INTO sections_fts_trigram(sections_fts_trigram) "
                "VALUES('rebuild')")
            conn.execute(
                "INSERT OR REPLACE INTO index_meta(key, value) VALUES "
                "('built_from_manifest_generation', ?)", (str(generation),))
            conn.execute(
                "INSERT OR REPLACE INTO index_meta(key, value) VALUES "
                "('rebuilt_at', ?)", (_utc_now(),))
            conn.commit()
        finally:
            conn.close()
        status = self.index_status()
        status.update({"changed": changed, "removed": removed,
                       "generation": generation})
        return status

    def _drop_document(self, conn: sqlite3.Connection, doc_id: str,
                       old_sha: str | None, generation: int) -> None:
        pks = [r["section_pk"] for r in conn.execute(
            "SELECT section_pk FROM sections WHERE document_id = ?",
            (doc_id,))]
        for pk in pks:
            conn.execute("DELETE FROM search_rows WHERE section_pk = ?", (pk,))
            conn.execute("DELETE FROM subspans WHERE section_pk = ?", (pk,))
        conn.execute("DELETE FROM sections WHERE document_id = ?", (doc_id,))
        conn.execute("DELETE FROM documents WHERE document_id = ?", (doc_id,))
        conn.execute(
            "INSERT OR REPLACE INTO index_journal VALUES "
            "(?, ?, ?, NULL, 'removed', 0, ?, ?)",
            (generation, doc_id, old_sha, len(pks), _utc_now()))
        conn.commit()

    def _index_document(self, conn: sqlite3.Connection,
                        record: dict[str, Any], generation: int,
                        old_sha: str | None) -> None:
        doc_id = record["document_id"]
        source = self._source_path(record["path"])
        old_count = conn.execute(
            "SELECT COUNT(*) c FROM sections WHERE document_id = ?",
            (doc_id,)).fetchone()["c"]
        old_pks = [r["section_pk"] for r in conn.execute(
            "SELECT section_pk FROM sections WHERE document_id = ?", (doc_id,))]
        for pk in old_pks:
            conn.execute("DELETE FROM search_rows WHERE section_pk = ?", (pk,))
            conn.execute("DELETE FROM subspans WHERE section_pk = ?", (pk,))
        conn.execute("DELETE FROM sections WHERE document_id = ?", (doc_id,))
        conn.execute(
            "INSERT OR REPLACE INTO documents VALUES (?,?,?,?,?,?,?,?,?)",
            (doc_id, record.get("persona_id", self.persona_id),
             record["role"], record["path"], record["sha256"],
             int(record["byte_length"]), int(record.get("revision", 1)),
             generation, "indexed"))
        added = 0
        for ordinal, span in enumerate(record.get("sections") or []):
            data = _slice_bytes(source, int(span["byte_start"]),
                                int(span["byte_end"]))
            digest = hashlib.sha256(data).hexdigest()
            if digest != span["sha256"]:
                conn.rollback()
                raise PersonaIndexError(
                    f"section slice hash mismatch indexing {doc_id}/"
                    f"{span['section_id']}: manifest {span['sha256']} "
                    f"vs source {digest}")
            text = data.decode("utf-8")
            entry_like = {"role": record["role"],
                          "heading": span["heading"],
                          "section_id": span["section_id"]}
            prio = section_priority(record["role"], span["heading"])
            plevel = priority_level(record["role"], span["heading"])
            tags = section_tags(entry_like)
            line_start, line_end = _line_span(
                source, int(span["byte_start"]), int(span["byte_end"]))
            cur = conn.execute(
                "INSERT INTO sections(document_id, stable_id, section_id, "
                "role, heading, level, ordinal, byte_start, byte_end, "
                "line_start, line_end, section_sha256, priority, "
                "priority_level, tags, in_kernel) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)",
                (doc_id, span["stable_id"], span["section_id"],
                 record["role"], span["heading"], int(span["level"]),
                 ordinal, int(span["byte_start"]), int(span["byte_end"]),
                 line_start, line_end, digest, prio, plevel,
                 json.dumps(tags)))
            section_pk = int(cur.lastrowid)
            conn.execute(
                "INSERT INTO search_rows VALUES (?,?,?,?,?,?)",
                (section_pk, "section", section_pk,
                 normalize_search_text(span["heading"]),
                 normalize_search_text(text), " ".join(tags)))
            if len(data) > self.subspan_threshold:
                for sub_ord, (s0, s1, kind, ov) in enumerate(_subspan_bounds(
                        data, self.subspan_target, self.subspan_overlap)):
                    sub_data = data[s0:s1]
                    sub_digest = hashlib.sha256(sub_data).hexdigest()
                    scur = conn.execute(
                        "INSERT INTO subspans(section_pk, ordinal, "
                        "byte_start, byte_end, overlap_prev_bytes, "
                        "boundary_kind, subspan_sha256) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (section_pk, sub_ord,
                         int(span["byte_start"]) + s0,
                         int(span["byte_start"]) + s1, ov, kind, sub_digest))
                    sub_pk = int(scur.lastrowid)
                    # Search projection only: a subspan window may
                    # start/end mid-character (overlap rewind and
                    # hard splits are byte operations), so its
                    # normalised text decodes tolerantly. The exact
                    # bytes and the subspan hash are unaffected;
                    # serving always slices source bytes.
                    conn.execute(
                        "INSERT INTO search_rows VALUES (?,?,?,?,?,?)",
                        (_SUBSPAN_ROW_OFFSET + sub_pk, "subspan", section_pk,
                         normalize_search_text(span["heading"]),
                         normalize_search_text(
                             sub_data.decode("utf-8", errors="ignore")),
                         " ".join(tags)))
            added += 1
        conn.execute(
            "INSERT OR REPLACE INTO index_journal VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?)",
            (generation, doc_id, old_sha, record["sha256"],
             "added" if old_sha is None else "changed", added, old_count,
             _utc_now()))
        conn.commit()

    # -- receipts (draft section 6) --------------------------------

    def _write_receipt(self, receipt: dict[str, Any]) -> dict[str, Any]:
        self.receipts_dir.mkdir(parents=True, exist_ok=True)
        path = self.receipts_dir / "receipts.jsonl"
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(receipt, sort_keys=True) + "\n")
        return receipt

    def _base_receipt(self, kind: str, query: str = "") -> dict[str, Any]:
        status = self.index_status()
        return {
            "receipt_id": str(uuid.uuid4()), "ts": _utc_now(),
            "kind": kind, "persona_id": self.persona_id,
            "profile_scope": self.persona_id, "query": query,
            "task_tags": classify_task(query) if query else [],
            "index_generation": status.get("index_generation", 0),
            "manifest_generation": status.get("manifest_generation", 0),
            "index_status": status.get("status", "unbuilt"),
            "candidate_count": 0, "candidate_cap": self.candidate_cap,
            "budget": None, "chosen": [], "omitted": [],
            "continuations_issued": [],
            "embeddings": "off", "cloud_egress": 0, "latency_ms": 0,
        }

    # -- P.006c: FTS candidate generation + section 13 re-score ----

    def _candidates(self, conn: sqlite3.Connection,
                    query: str) -> tuple[dict[int, float], set[int]]:
        """(row_pk -> raw bm25 (lower is better), exact-phrase row_pks).

        The exact-phrase set matters because the section 13
        slug vocabulary is ASCII-only: a query written in runes
        or CJK tokenises to the empty set there, so token
        contact can never fire for it, while a verbatim trigram
        phrase hit is stronger contact evidence than token
        overlap. The fusion layer (this module) therefore
        accepts a trigram exact-phrase hit as contact; the
        section 13 scorer itself is untouched.
        """
        found: dict[int, float] = {}
        phrase_hits: set[int] = set()
        terms = _word_terms(query)
        if terms:
            match = " OR ".join(_fts_phrase(t) for t in terms[:32])
            try:
                rows = conn.execute(
                    "SELECT rowid AS rp, bm25(sections_fts, 10.0, 1.0, 5.0) "
                    "AS b FROM sections_fts WHERE sections_fts MATCH ? "
                    "ORDER BY b LIMIT ?", (match, self.candidate_cap))
                for row in rows:
                    found[int(row["rp"])] = float(row["b"])
            except sqlite3.OperationalError:
                pass
        phrase = (query or "").strip()
        if len(phrase) >= 3:
            try:
                rows = conn.execute(
                    "SELECT rowid AS rp, bm25(sections_fts_trigram) AS b "
                    "FROM sections_fts_trigram "
                    "WHERE sections_fts_trigram MATCH ? ORDER BY b LIMIT ?",
                    (_fts_phrase(normalize_search_text(phrase)),
                     self.candidate_cap))
                for row in rows:
                    rp = int(row["rp"])
                    phrase_hits.add(rp)
                    if rp not in found or float(row["b"]) < found[rp]:
                        found[rp] = float(row["b"])
            except sqlite3.OperationalError:
                pass
        return found, phrase_hits

    def retrieve(self, query: str, limit: int = 5,
                 task_text: str | None = None,
                 query_vector: list[float] | None = None,
                 window_bytes: int | None = None) -> dict[str, Any]:
        """Ranked retrieval: FTS narrows, section 13 decides.

        Returns ``{"results": [...], "receipt": {...}}``. The
        section 13 contact rule is enforced after fusion; the
        receipt names every omitted candidate and its reason.
        With ``query_vector`` supplied, a candidate gains its
        semantic component ONLY from a currently-consented
        stored vector (P.007); otherwise ``semantic`` is None
        and the five-component total is bit-identical to the
        in-memory path.
        """
        started = time.perf_counter()
        if not self.db_path.exists():
            raise IndexNotBuiltError(
                "persona index not built; call sync() first")
        bounded = max(1, min(100, int(limit)))
        window = int(window_bytes) if window_bytes else self.subspan_threshold
        receipt = self._base_receipt(
            "retrieval", query if task_text is None else task_text)
        receipt["query_sanitised_terms"] = _word_terms(query)
        receipt["budget"] = {"limit": bounded, "window_bytes": window}
        manifest = self._manifest()
        conn = self._connect(readonly=True)
        try:
            cand, phrase_rows = self._candidates(conn, query)
            receipt["candidate_count"] = len(cand)
            per_section: dict[int, float] = {}
            phrase_sections: set[int] = set()
            for rp, bm in cand.items():
                row = conn.execute(
                    "SELECT section_pk FROM search_rows WHERE row_pk = ?",
                    (rp,)).fetchone()
                if row is None:
                    continue
                pk = int(row["section_pk"])
                if pk not in per_section or bm < per_section[pk]:
                    per_section[pk] = bm
                if rp in phrase_rows:
                    phrase_sections.add(pk)
            scored: list[dict[str, Any]] = []
            omitted: list[dict[str, Any]] = []
            if per_section:
                values = list(per_section.values())
                lo, hi = min(values), max(values)
                for pk, bm in per_section.items():
                    srow = conn.execute(
                        "SELECT * FROM sections WHERE section_pk = ?",
                        (pk,)).fetchone()
                    drow = conn.execute(
                        "SELECT * FROM documents WHERE document_id = ?",
                        (srow["document_id"],)).fetchone()
                    source = self._source_path(drow["path"])
                    data = _slice_bytes(source, int(srow["byte_start"]),
                                        int(srow["byte_end"]))
                    if hashlib.sha256(data).hexdigest() != srow["section_sha256"]:
                        omitted.append({"stable_id": srow["stable_id"],
                                        "reason": "source_hash_mismatch"})
                        continue
                    entry = {"role": srow["role"], "heading": srow["heading"],
                             "section_id": srow["section_id"],
                             "text": data.decode("utf-8"),
                             "priority": float(srow["priority"])}
                    tags_wanted = classify_task(
                        task_text if task_text is not None else query)
                    score = retrieval_score(entry, query=query,
                                            task_tags_=tags_wanted)
                    semantic = None
                    if query_vector is not None:
                        semantic = self._semantic_for(
                            srow["document_id"], srow["stable_id"],
                            srow["section_sha256"], query_vector)
                        if semantic is not None:
                            score = dict(score, semantic=round(semantic, 6))
                    bm_norm = 1.0 if hi == lo else (hi - bm) / (hi - lo)
                    fused = score["total"] + BM25_FUSION_WEIGHT * bm_norm
                    if semantic is not None:
                        fused += SEMANTIC_FUSION_WEIGHT * semantic
                    exact_phrase = pk in phrase_sections
                    if not (score["keyword"] or score["heading"]
                            or score["task"]) and not exact_phrase:
                        omitted.append({"stable_id": srow["stable_id"],
                                        "reason": "no_contact"})
                        continue
                    result = {
                        "stable_id": srow["stable_id"],
                        "section_id": srow["section_id"],
                        "document_id": srow["document_id"],
                        "role": srow["role"], "heading": srow["heading"],
                        "path": drow["path"],
                        "byte_start": int(srow["byte_start"]),
                        "byte_end": int(srow["byte_end"]),
                        "line_start": int(srow["line_start"]),
                        "line_end": int(srow["line_end"]),
                        "section_sha256": srow["section_sha256"],
                        "source_sha256": drow["sha256"],
                        "priority": float(srow["priority"]),
                        "tags": json.loads(srow["tags"]),
                        "score": score, "exact_phrase_hit": exact_phrase,
                        "bm25": round(bm, 6),
                        "bm25_norm": round(bm_norm, 6),
                        "fused_total": round(fused, 6),
                        "privacy_class": (manifest["documents"].get(
                            srow["document_id"]) or {}).get(
                                "privacy_class", ""),
                        "trust_class": (manifest["documents"].get(
                            srow["document_id"]) or {}).get(
                                "trust_class", ""),
                    }
                    if len(data) <= window:
                        result["text"] = entry["text"]
                        result["windowed"] = False
                    else:
                        win = data[:window]
                        while win:
                            try:
                                win_text = win.decode("utf-8")
                                break
                            except UnicodeDecodeError:
                                win = win[:-1]
                        else:
                            win_text = ""
                        handle = self._make_handle(
                            srow["document_id"], srow["stable_id"],
                            int(srow["byte_start"]) + len(win),
                            int(srow["byte_end"]), drow["sha256"],
                            receipt["manifest_generation"])
                        result["text"] = win_text
                        result["windowed"] = True
                        result["more_from_this_section"] = {
                            "remaining_bytes": len(data) - len(win),
                            "next_handle": handle,
                            "section_total_bytes": len(data)}
                        receipt["continuations_issued"].append(
                            {"stable_id": srow["stable_id"],
                             "handle_id": hashlib.sha256(
                                 handle.encode()).hexdigest()[:16]})
                    scored.append(result)
            scored.sort(key=lambda r: (-r["fused_total"], r["stable_id"]))
            chosen = scored[:bounded]
            for extra in scored[bounded:]:
                omitted.append({"stable_id": extra["stable_id"],
                                "reason": "over_budget"})
            receipt["chosen"] = [{
                "stable_id": r["stable_id"], "byte_start": r["byte_start"],
                "byte_end": r["byte_end"], "score": r["score"],
                "bm25": r["bm25"], "fused_total": r["fused_total"],
                "why": ("exact phrase (trigram) contact"
                        if r.get("exact_phrase_hit") and not (
                            r["score"]["keyword"] or r["score"]["heading"]
                            or r["score"]["task"])
                        else "contact components > 0")} for r in chosen]
            receipt["omitted"] = omitted
            if query_vector is not None:
                receipt["embeddings"] = "query_vector_supplied"
            receipt["latency_ms"] = round(
                (time.perf_counter() - started) * 1000, 3)
            self._write_receipt(receipt)
            return {"results": chosen, "receipt": receipt}
        finally:
            conn.close()

    # -- P.006d: continuation handles -------------------------------

    def _make_handle(self, document_id: str, stable_id: str,
                     next_offset: int, section_end: int,
                     source_sha256: str, generation: int) -> str:
        payload = {"document_id": document_id, "stable_id": stable_id,
                   "next_byte_offset": next_offset,
                   "section_byte_end": section_end,
                   "source_sha256": source_sha256,
                   "manifest_generation": generation}
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii")

    def _parse_handle(self, handle: str) -> dict[str, Any]:
        try:
            payload = json.loads(base64.urlsafe_b64decode(
                handle.encode("ascii")).decode("utf-8"))
        except Exception as exc:
            raise PersonaIndexError(f"invalid continuation handle: {exc}")
        for key in ("document_id", "stable_id", "next_byte_offset",
                    "section_byte_end", "source_sha256",
                    "manifest_generation"):
            if key not in payload:
                raise PersonaIndexError(
                    f"continuation handle missing field: {key}")
        return payload

    def _section_row(self, conn: sqlite3.Connection,
                     stable_id: str) -> sqlite3.Row | None:
        return conn.execute(
            "SELECT * FROM sections WHERE stable_id = ?", (stable_id,)).fetchone()

    def continue_read(self, handle: str,
                      max_bytes: int | None = None) -> dict[str, Any]:
        """Serve the next window named by a continuation handle.

        Handles are validated, not trusted: the document hash
        and manifest generation are re-checked at serve time.
        A stale handle returns a named ``stale_continuation``
        result carrying the section's current first window --
        it never silently serves bytes from a changed source.
        """
        payload = self._parse_handle(handle)
        limit = int(max_bytes) if max_bytes else self.subspan_target
        manifest = self._manifest()
        record = manifest["documents"].get(payload["document_id"])
        if record is None or record["sha256"] != payload["source_sha256"] \
                or int(manifest["generation"]) != int(payload["manifest_generation"]):
            fresh = None
            if self.db_path.exists():
                try:
                    fresh = self.read_section_page(payload["stable_id"])
                except PersonaIndexError:
                    fresh = None
            return {"status": "stale_continuation",
                    "error": "stale_continuation",
                    "stable_id": payload["stable_id"],
                    "current_first_window": fresh}
        source = self._source_path(record["path"])
        if _hash_file(source) != record["sha256"]:
            return {"status": "stale_continuation",
                    "error": "stale_continuation",
                    "stable_id": payload["stable_id"],
                    "current_first_window": None}
        start = int(payload["next_byte_offset"])
        end = min(start + limit, int(payload["section_byte_end"]))
        data = _slice_bytes(source, start, end)
        # Never split a UTF-8 character across windows.
        while data:
            try:
                text = data.decode("utf-8")
                break
            except UnicodeDecodeError:
                data = data[:-1]
                end -= 1
        else:
            text = ""
        section_end = int(payload["section_byte_end"])
        next_handle = None
        if end < section_end:
            next_handle = self._make_handle(
                payload["document_id"], payload["stable_id"], end,
                section_end, payload["source_sha256"],
                int(payload["manifest_generation"]))
        receipt = self._base_receipt("continuation")
        receipt["chosen"] = [{"stable_id": payload["stable_id"],
                               "byte_start": start, "byte_end": end}]
        if next_handle:
            receipt["continuations_issued"].append(
                {"stable_id": payload["stable_id"],
                 "handle_id": hashlib.sha256(
                     next_handle.encode()).hexdigest()[:16]})
        self._write_receipt(receipt)
        return {"status": "ok", "stable_id": payload["stable_id"],
                "document_id": payload["document_id"], "text": text,
                "byte_start": start, "byte_end": end,
                "next_handle": next_handle,
                "remaining_bytes": section_end - end,
                "section_total_bytes": section_end,
                "complete": end >= section_end, "receipt": receipt}

    # -- P.006e: exact citation --------------------------------------

    def cite(self, stable_id: str) -> dict[str, Any]:
        """Exact citation: slice from source at serve time, verify.

        Falls back to the W03 manifest's own byte ranges when
        the section is not in the FTS index (citation needs the
        manifest, not the index), recording index status
        honestly.
        """
        manifest = self._manifest()
        found: dict[str, Any] | None = None
        if self.db_path.exists():
            conn = self._connect(readonly=True)
            try:
                row = self._section_row(conn, stable_id)
                if row is not None:
                    drow = conn.execute(
                        "SELECT * FROM documents WHERE document_id = ?",
                        (row["document_id"],)).fetchone()
                    found = {"document_id": row["document_id"],
                             "path": drow["path"],
                             "source_sha256": drow["sha256"],
                             "byte_start": int(row["byte_start"]),
                             "byte_end": int(row["byte_end"]),
                             "line_start": int(row["line_start"]),
                             "line_end": int(row["line_end"]),
                             "section_sha256": row["section_sha256"]}
            finally:
                conn.close()
        if found is None:
            for doc_id, record in manifest["documents"].items():
                for span in record.get("sections") or []:
                    if span["stable_id"] == stable_id:
                        source = self._source_path(record["path"])
                        ls, le = _line_span(source, int(span["byte_start"]),
                                            int(span["byte_end"]))
                        found = {"document_id": doc_id,
                                 "path": record["path"],
                                 "source_sha256": record["sha256"],
                                 "byte_start": int(span["byte_start"]),
                                 "byte_end": int(span["byte_end"]),
                                 "line_start": ls, "line_end": le,
                                 "section_sha256": span["sha256"]}
                        break
                if found is not None:
                    break
        if found is None:
            raise CitationError(f"unknown stable_id: {stable_id}")
        record = manifest["documents"][found["document_id"]]
        source = self._source_path(found["path"])
        data = _slice_bytes(source, found["byte_start"], found["byte_end"])
        digest = hashlib.sha256(data).hexdigest()
        if digest != found["section_sha256"]:
            raise CitationError(
                f"citation hash mismatch for {stable_id}: index/manifest "
                f"{found['section_sha256']} vs source slice {digest}")
        status = self.index_status()
        result = {
            "mode": "exact_citation", "persona_id": self.persona_id,
            "document_id": found["document_id"], "role": record["role"],
            "stable_id": stable_id, "path": found["path"],
            "byte_start": found["byte_start"], "byte_end": found["byte_end"],
            "line_start": found["line_start"], "line_end": found["line_end"],
            "source_sha256": found["source_sha256"],
            "section_sha256": digest,
            "manifest_generation": int(manifest["generation"]),
            "index_generation": status.get("index_generation", 0),
            "index_status": status.get("status", "unbuilt"),
            "privacy_class": record.get("privacy_class", ""),
            "trust_class": record.get("trust_class", ""),
            "destinations": record.get("destinations", []),
            "text": data.decode("utf-8"),
        }
        receipt = self._base_receipt("exact_citation")
        receipt["chosen"] = [{"stable_id": stable_id,
                               "byte_start": found["byte_start"],
                               "byte_end": found["byte_end"],
                               "section_sha256": digest}]
        self._write_receipt(receipt)
        result["receipt"] = receipt
        return result

    # -- P.006f: paged full-fidelity read ------------------------------

    def read_page(self, document_id: str, cursor: int = 0,
                  max_bytes: int = DEFAULT_PAGE_BYTES) -> dict[str, Any]:
        """One page of a canonical source, byte-faithful.

        No redaction, no formatting, no dedup. Pages split only
        at UTF-8 character boundaries; concatenating all pages
        reproduces the source byte-for-byte, proven by the
        whole-source hash on the final page.
        """
        manifest = self._manifest()
        record = manifest["documents"].get(document_id)
        if record is None:
            raise PersonaIndexError(f"unknown document: {document_id}")
        source = self._source_path(record["path"])
        total = int(record["byte_length"])
        start = max(0, int(cursor))
        if start > total:
            raise PersonaIndexError(
                f"cursor {start} beyond source length {total}")
        raw = _slice_bytes(source, start, min(start + int(max_bytes), total))
        data = raw
        while data:
            try:
                text = data.decode("utf-8")
                break
            except UnicodeDecodeError:
                data = data[:-1]
        else:
            text = ""
        end = start + len(data)
        complete = end >= total
        result = {"document_id": document_id, "text": text,
                  "byte_start": start, "byte_end": end,
                  "next_cursor": None if complete else end,
                  "page_sha256": hashlib.sha256(data).hexdigest(),
                  "source_sha256": record["sha256"],
                  "source_byte_length": total, "complete": complete}
        receipt = self._base_receipt("paged_read")
        receipt["chosen"] = [{"document_id": document_id,
                               "byte_start": start, "byte_end": end}]
        self._write_receipt(receipt)
        result["receipt"] = receipt
        return result

    def read_section_page(self, stable_id: str, cursor: int | None = None,
                          max_bytes: int = DEFAULT_PAGE_BYTES) -> dict[str, Any]:
        """The paged read bounded to one section's byte range."""
        citation = self.cite(stable_id)
        start = citation["byte_start"] if cursor is None else int(cursor)
        if start < citation["byte_start"] or start > citation["byte_end"]:
            raise PersonaIndexError(
                f"cursor {start} outside section {stable_id}")
        source = self._source_path(citation["path"])
        end_want = min(start + int(max_bytes), citation["byte_end"])
        data = _slice_bytes(source, start, end_want)
        while data:
            try:
                text = data.decode("utf-8")
                break
            except UnicodeDecodeError:
                data = data[:-1]
        else:
            text = ""
        end = start + len(data)
        complete = end >= citation["byte_end"]
        return {"stable_id": stable_id,
                "document_id": citation["document_id"], "text": text,
                "byte_start": start, "byte_end": end,
                "next_cursor": None if complete else end,
                "page_sha256": hashlib.sha256(data).hexdigest(),
                "section_sha256": citation["section_sha256"],
                "section_byte_start": citation["byte_start"],
                "section_byte_end": citation["byte_end"],
                "complete": complete}

    # -- P.007: embeddings consent gate -------------------------------

    def _emb_connect(self) -> sqlite3.Connection:
        self.semantic_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.embeddings_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS consent_records(
          consent_id TEXT PRIMARY KEY, document_id TEXT NOT NULL,
          provider_kind TEXT NOT NULL, provider TEXT NOT NULL,
          model TEXT NOT NULL, version TEXT NOT NULL,
          dimensions INTEGER NOT NULL, granted_by TEXT NOT NULL,
          granted_at TEXT NOT NULL, cloud_override INTEGER NOT NULL,
          active INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS embeddings(
          document_id TEXT NOT NULL, stable_id TEXT NOT NULL,
          provider TEXT NOT NULL, model TEXT NOT NULL,
          version TEXT NOT NULL, dimensions INTEGER NOT NULL,
          source_sha256 TEXT NOT NULL, vector BLOB NOT NULL,
          created_at TEXT NOT NULL,
          PRIMARY KEY(document_id, stable_id, provider, model, version));
        """)
        conn.commit()
        return conn

    def grant_consent(self, document_id: str, provider_kind: str,
                      provider: str, model: str, version: str,
                      dimensions: int, granted_by: str,
                      cloud_override: bool = False) -> dict[str, Any]:
        """Record per-source embedding consent (fail-closed).

        Cloud embedding of a ``private`` source is refused at
        grant time unless the operator records an explicit
        override. A local consent never implies cloud consent:
        the provider kind is part of the record.
        """
        if provider_kind not in ("local", "cloud"):
            raise ConsentError(f"unknown provider_kind: {provider_kind!r}")
        manifest = self._manifest()
        record = manifest["documents"].get(document_id)
        if record is None:
            raise ConsentError(f"unknown document: {document_id}")
        if provider_kind == "cloud" \
                and record.get("privacy_class") == "private" \
                and not cloud_override:
            raise ConsentError(
                f"cloud embedding refused for private source {document_id} "
                "without a recorded operator override")
        consent = {"consent_id": str(uuid.uuid4()),
                   "document_id": document_id,
                   "provider_kind": provider_kind, "provider": provider,
                   "model": model, "version": version,
                   "dimensions": int(dimensions), "granted_by": granted_by,
                   "granted_at": _utc_now(),
                   "cloud_override": bool(cloud_override), "active": True}
        conn = self._emb_connect()
        try:
            conn.execute(
                "INSERT INTO consent_records VALUES (?,?,?,?,?,?,?,?,?,?,1)",
                (consent["consent_id"], document_id, provider_kind, provider,
                 model, version, int(dimensions), granted_by,
                 consent["granted_at"], 1 if cloud_override else 0))
            conn.commit()
        finally:
            conn.close()
        return consent

    def _active_consent(self, conn: sqlite3.Connection, document_id: str,
                        provider: str, model: str,
                        version: str) -> sqlite3.Row | None:
        return conn.execute(
            "SELECT * FROM consent_records WHERE document_id = ? AND "
            "provider = ? AND model = ? AND version = ? AND active = 1",
            (document_id, provider, model, version)).fetchone()

    def revoke_consent(self, consent_id: str) -> dict[str, Any]:
        """Revoke a consent record and delete its vectors atomically."""
        conn = self._emb_connect()
        try:
            row = conn.execute(
                "SELECT * FROM consent_records WHERE consent_id = ?",
                (consent_id,)).fetchone()
            if row is None:
                raise ConsentError(f"unknown consent record: {consent_id}")
            conn.execute(
                "UPDATE consent_records SET active = 0 WHERE consent_id = ?",
                (consent_id,))
            cur = conn.execute(
                "DELETE FROM embeddings WHERE document_id = ? AND "
                "provider = ? AND model = ? AND version = ?",
                (row["document_id"], row["provider"], row["model"],
                 row["version"]))
            deleted = cur.rowcount
            conn.commit()
            return {"consent_id": consent_id, "revoked": True,
                    "vectors_deleted": deleted,
                    "document_id": row["document_id"]}
        finally:
            conn.close()

    def embed_document(self, document_id: str,
                       embed_fn: Callable[[str], list[float]], *,
                       provider: str, model: str, version: str) -> dict[str, Any]:
        """Embed one document's sections under a valid consent.

        ``embed_fn`` is injected: the real provider contract
        lands with W08/E.02; tests use a local fake. A document
        with no matching active consent is never embedded --
        the check runs at embed time, not only at grant time.
        """
        manifest = self._manifest()
        record = manifest["documents"].get(document_id)
        if record is None:
            raise ConsentError(f"unknown document: {document_id}")
        conn = self._emb_connect()
        try:
            consent = self._active_consent(conn, document_id, provider,
                                           model, version)
            if consent is None:
                raise ConsentError(
                    f"no active consent for {document_id} under "
                    f"{provider}/{model}/{version}; not embedded")
            source = self._source_path(record["path"])
            stored = 0
            for span in record.get("sections") or []:
                data = _slice_bytes(source, int(span["byte_start"]),
                                    int(span["byte_end"]))
                if hashlib.sha256(data).hexdigest() != span["sha256"]:
                    raise ConsentError(
                        f"source slice hash mismatch embedding {document_id}")
                vector = [float(v) for v in embed_fn(data.decode("utf-8"))]
                if len(vector) != int(consent["dimensions"]):
                    raise ConsentError(
                        f"embedding dimensions {len(vector)} != consented "
                        f"{consent['dimensions']}")
                blob = struct.pack(f"<{len(vector)}f", *vector)
                conn.execute(
                    "INSERT OR REPLACE INTO embeddings VALUES "
                    "(?,?,?,?,?,?,?,?,?)",
                    (document_id, span["stable_id"], provider, model, version,
                     len(vector), record["sha256"], blob, _utc_now()))
                stored += 1
            conn.commit()
            return {"document_id": document_id, "vectors_stored": stored,
                    "consent_id": consent["consent_id"],
                    "provider_kind": consent["provider_kind"]}
        finally:
            conn.close()

    def _semantic_for(self, document_id: str, stable_id: str,
                      section_sha256: str,
                      query_vector: list[float]) -> float | None:
        """Cosine similarity from a currently-consented vector, or None.

        None (never a stale or faked value) when: no embeddings
        store, no vector, consent revoked or drifted, or the
        source changed since the vector was computed. The
        stored ``source_sha256`` is the whole-document hash, so
        any source change invalidates every vector of that
        document at once.
        """
        if not self.embeddings_path.exists():
            return None
        manifest = self._manifest()
        record = manifest["documents"].get(document_id)
        if record is None:
            return None
        conn = sqlite3.connect(f"file:{self.embeddings_path}?mode=ro",
                               uri=True)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM embeddings WHERE document_id = ? AND "
                "stable_id = ?", (document_id, stable_id)).fetchone()
            if row is None or row["source_sha256"] != record["sha256"]:
                return None
            consent = self._active_consent(conn, document_id, row["provider"],
                                           row["model"], row["version"])
            if consent is None:
                return None
            vec = list(struct.unpack(f"<{row['dimensions']}f", row["vector"]))
        except sqlite3.OperationalError:
            return None
        finally:
            conn.close()
        if len(vec) != len(query_vector):
            return None
        dot = sum(a * b for a, b in zip(vec, query_vector))
        na = math.sqrt(sum(a * a for a in vec))
        nb = math.sqrt(sum(b * b for b in query_vector))
        if na == 0.0 or nb == 0.0:
            return None
        return max(0.0, min(1.0, dot / (na * nb)))

    def vector_count(self, document_id: str | None = None) -> int:
        if not self.embeddings_path.exists():
            return 0
        conn = self._emb_connect()
        try:
            if document_id is None:
                row = conn.execute("SELECT COUNT(*) c FROM embeddings").fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) c FROM embeddings WHERE document_id = ?",
                    (document_id,)).fetchone()
            return int(row["c"])
        finally:
            conn.close()


def fallback_retrieve(entries: list[dict[str, Any]], query: str = "",
                      task_text: str | None = None,
                      limit: int = 5) -> list[dict[str, Any]]:
    """The incumbent in-memory section 13 path (control group).

    With the index deleted, small-corpus queries are answered
    exactly as before P2: this is ``persona_runtime``'s own
    ``retrieve_sections``, not a stub.
    """
    return retrieve_sections(entries, query=query, task_text=task_text,
                             limit=limit)


def measure_tokenizers(samples: list[tuple[str, str]]) -> dict[str, Any]:
    """Tokenizer measurement harness (build step P.006a exit).

    Each sample is ``(text, query)``; both FTS5 tokenizers are
    exercised in-memory and per-sample hits recorded. The W04
    decision (recorded in the implementation record): keep
    BOTH tables -- unicode61 primary, trigram as the exact-
    substring fallback for runes / diacritics / CJK / code.
    """
    report: dict[str, Any] = {"unicode61": [], "trigram": []}
    for text, query in samples:
        norm = normalize_search_text(text)
        for name, ddl, match in (
                ("unicode61",
                 "CREATE VIRTUAL TABLE t USING fts5(x, tokenize="
                 "'unicode61 remove_diacritics 2')",
                 _fts_phrase(query.casefold())),
                ("trigram",
                 "CREATE VIRTUAL TABLE t USING fts5(x, tokenize='trigram')",
                 _fts_phrase(normalize_search_text(query)))):
            conn = sqlite3.connect(":memory:")
            try:
                conn.execute(ddl)
                conn.execute("INSERT INTO t(x) VALUES (?)", (norm,))
                try:
                    hit = conn.execute(
                        "SELECT COUNT(*) FROM t WHERE t MATCH ?",
                        (match,)).fetchone()[0] > 0
                except sqlite3.OperationalError:
                    hit = False
                report[name].append(bool(hit))
            finally:
                conn.close()
    report["unicode61_hits"] = sum(report["unicode61"])
    report["trigram_hits"] = sum(report["trigram"])
    report["samples"] = len(samples)
    return report
