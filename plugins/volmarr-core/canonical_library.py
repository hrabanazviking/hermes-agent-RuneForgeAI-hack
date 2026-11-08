"""Unbounded canonical source library (W03 / Phases P0+P1).

Implements roadmap tickets P.001-P.005 per
docs/modernization/P0P1_DESIGN_DRAFT.md:

- P.001 source roles / trust / privacy policy + the manifest
  field contract, with the no-cap clause enforced mechanically:
  no document record may carry a key matching ``^max_`` or
  ``_limit$`` (``max_chars`` and kin are named errors).
- P.002 streaming, byte-exact ingestion: chunked reads with an
  incremental SHA-256 over the original bytes, incremental
  UTF-8 validation, and Markdown section extraction carrying
  exact byte ranges. Peak memory is a function of the work
  unit (an *operations* quota, never a document property),
  never of the file size. Canonical bytes are read in place;
  ingestion never copies, rewrites, normalises or re-encodes
  them. Export reproduces the original byte stream.
- P.004 transactional manifest updates: tmp-file + fsync +
  atomic rename + directory fsync, a monotonic generation, a
  per-commit journal, a single-writer advisory lock, and
  quarantine-and-rebuild recovery.
- P.003 migration dry-run: inventory, role proposals,
  verify-only simulated ingestion, a provenance report, an
  idempotence check and a rollback rehearsal -- always
  against a caller-supplied library root (a disposable
  profile in tests), never the dormant deployment.
- P.005 stable section identity reusing the persona
  compiler's ``stable_section_id`` and slug rules
  (``persona_runtime``); no second identity scheme.

The stock prompt path in ``agent/prompt_builder.py`` is not
touched: with this module unused, upstream behaviour is
byte-for-byte intact. Bounded retrieval packets remain the
business of ``context_packet.py``; nothing here bounds the
storage, import, export, edit, hash, backup or indexing of a
canonical authored document.
"""

from __future__ import annotations

import codecs
import fcntl
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Callable, Iterable, Iterator

from .persona_runtime import _slugify, display_heading, stable_section_id

__all__ = [
    "CORE_ROLES", "DOCUMENT_RECORD_FIELDS", "FORBIDDEN_KEY_NAMES",
    "CanonicalLibrary", "CanonicalLibraryError", "Checkpoint",
    "DocumentRecord", "IngestResult", "LockTimeoutError",
    "ManifestStore", "SectionSpan", "StreamingIngester",
    "default_role_for_filename", "find_forbidden_keys",
    "migration_dry_run", "mint_document_id", "validate_record",
]

# ----------------------------------------------------------------
# P.001 -- policy: roles, trust, privacy, priorities, statuses
# ----------------------------------------------------------------

#: Core role vocabulary (roadmap 7.1). The vocabulary is open:
#: a new role needs metadata, never a code edit, so validation
#: accepts any well-formed role token; this set names the core.
CORE_ROLES = (
    "soul", "identity", "service_bible", "relationships",
    "memory_policy", "tool_policy", "avatar", "worldview",
    "memory", "user",
)
TRUST_CLASSES = (
    "authored-canon", "operator", "imported-trusted",
    "imported-untrusted",
)
PRIVACY_CLASSES = ("private", "shared", "public")
PRIORITIES = ("P0", "P1", "P2", "P3", "P4")
STATUSES = (
    "complete", "unindexed", "indexing", "indexed", "outdated",
    "unreadable", "corrupt",
)
CONFLICT_POLICIES = ("hash-is-authority",)
DOCUMENT_STATES = ("active", "archived")
SOURCE_KINDS = ("local-file", "local-tree", "git-checkout", "connector")

_ROLE_TOKEN = re.compile(r"^[a-z0-9][a-z0-9_/-]*$")
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")

#: The no-cap clause (design draft section 2): these key names,
#: and any key matching ``^max_`` or ``_limit$``, are forbidden
#: on a document record and rejected with a named error.
FORBIDDEN_KEY_NAMES = frozenset({
    "max_chars", "max_tokens", "max_bytes", "char_limit",
    "token_limit", "byte_limit",
})
_FORBIDDEN_KEY_RE = re.compile(r"^max_|_limit$")

#: The complete document-record field contract (draft section 2).
#: ``additionalProperties: false`` made structural: a record may
#: carry exactly these keys, no others.
DOCUMENT_RECORD_FIELDS = frozenset({
    "document_id", "role", "path", "namespace", "sha256",
    "byte_length", "revision", "external_revision", "label",
    "locale", "dialect", "tags", "category", "priority",
    "trust_class", "privacy_class", "destinations", "persona_id",
    "shared", "anchors", "include_rules", "status",
    "conflict_policy", "state", "first_seen_at",
    "last_verified_at", "last_compiled_at", "provenance",
    "sections",
})
_REQUIRED_FIELDS = (
    "document_id", "role", "path", "namespace", "sha256",
    "byte_length", "revision", "priority", "trust_class",
    "privacy_class", "persona_id", "status", "conflict_policy",
    "state", "provenance",
)

#: Filename -> proposed role for the P.003 dry-run. Unmapped
#: files are reported unmapped; the dry-run never guesses.
_FILENAME_ROLES = {
    "SOUL.md": "soul",
    "IDENTITY.md": "identity",
    "USER.md": "user",
    "MEMORY.md": "memory",
    "AGENTS.md": "service_bible",
    "HERMES.md": "service_bible",
    ".hermes.md": "service_bible",
}


class CanonicalLibraryError(Exception):
    """A canonical-library validation or ingestion failure."""


class LockTimeoutError(CanonicalLibraryError):
    """The manifest single-writer lock was not acquired in time."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_forbidden_keys(obj: Any, prefix: str = "") -> list[str]:
    """Every forbidden key path in *obj*, recursively.

    A key is forbidden when it is one of FORBIDDEN_KEY_NAMES or
    matches ``^max_`` / ``_limit$``. Operational quotas live in
    a separate operations config, never on document records,
    so any hit here is a contract violation.
    """
    hits: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(key, str) and (
                key in FORBIDDEN_KEY_NAMES or _FORBIDDEN_KEY_RE.search(key)
            ):
                hits.append(path)
            hits.extend(find_forbidden_keys(value, path))
    elif isinstance(obj, (list, tuple)):
        for idx, value in enumerate(obj):
            hits.extend(find_forbidden_keys(value, f"{prefix}[{idx}]"))
    return hits


def mint_document_id(persona_id: str, relpath: str) -> str:
    """Stable, path-independent-once-minted document id.

    Minted at first ingestion from the canonical relpath and
    persona id; recorded forever after, so a rename keeps the
    id and only updates ``path`` (draft section 2).
    """
    digest = hashlib.sha256(
        f"{persona_id}\x00{relpath}".encode("utf-8")).hexdigest()
    return f"doc_{digest[:16]}"


def default_role_for_filename(name: str) -> str | None:
    """Proposed role for a well-known filename, else None."""
    return _FILENAME_ROLES.get(name)


@dataclass
class DocumentRecord:
    """One manifest document record (draft section 2)."""

    document_id: str
    role: str
    path: str
    namespace: str
    sha256: str
    byte_length: int
    revision: int = 1
    priority: str = "P2"
    trust_class: str = "authored-canon"
    privacy_class: str = "private"
    persona_id: str = ""
    status: str = "unindexed"
    conflict_policy: str = "hash-is-authority"
    state: str = "active"
    provenance: dict[str, Any] = field(
        default_factory=lambda: {"kind": "local-file"})
    external_revision: str | None = None
    label: str = ""
    locale: str = ""
    dialect: str = ""
    tags: list[str] = field(default_factory=list)
    category: str = ""
    destinations: list[str] = field(default_factory=list)
    shared: bool = False
    anchors: list[str] = field(default_factory=list)
    include_rules: list[str] = field(default_factory=list)
    first_seen_at: str = ""
    last_verified_at: str = ""
    last_compiled_at: str = ""
    sections: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "document_id": self.document_id, "role": self.role,
            "path": self.path, "namespace": self.namespace,
            "sha256": self.sha256, "byte_length": self.byte_length,
            "revision": self.revision,
            "external_revision": self.external_revision,
            "label": self.label, "locale": self.locale,
            "dialect": self.dialect, "tags": list(self.tags),
            "category": self.category, "priority": self.priority,
            "trust_class": self.trust_class,
            "privacy_class": self.privacy_class,
            "destinations": list(self.destinations),
            "persona_id": self.persona_id, "shared": self.shared,
            "anchors": list(self.anchors),
            "include_rules": list(self.include_rules),
            "status": self.status,
            "conflict_policy": self.conflict_policy,
            "state": self.state,
            "first_seen_at": self.first_seen_at,
            "last_verified_at": self.last_verified_at,
            "last_compiled_at": self.last_compiled_at,
            "provenance": dict(self.provenance),
            "sections": [dict(s) for s in self.sections],
        }
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DocumentRecord":
        validate_record(data)
        return cls(
            document_id=data["document_id"], role=data["role"],
            path=data["path"], namespace=data["namespace"],
            sha256=data["sha256"], byte_length=data["byte_length"],
            revision=data.get("revision", 1),
            priority=data.get("priority", "P2"),
            trust_class=data.get("trust_class", "authored-canon"),
            privacy_class=data.get("privacy_class", "private"),
            persona_id=data.get("persona_id", ""),
            status=data.get("status", "unindexed"),
            conflict_policy=data.get(
                "conflict_policy", "hash-is-authority"),
            state=data.get("state", "active"),
            provenance=dict(data.get("provenance") or {"kind": "local-file"}),
            external_revision=data.get("external_revision"),
            label=data.get("label", ""), locale=data.get("locale", ""),
            dialect=data.get("dialect", ""),
            tags=list(data.get("tags") or []),
            category=data.get("category", ""),
            destinations=list(data.get("destinations") or []),
            shared=bool(data.get("shared", False)),
            anchors=list(data.get("anchors") or []),
            include_rules=list(data.get("include_rules") or []),
            first_seen_at=data.get("first_seen_at", ""),
            last_verified_at=data.get("last_verified_at", ""),
            last_compiled_at=data.get("last_compiled_at", ""),
            sections=[dict(s) for s in (data.get("sections") or [])],
        )


def validate_record(data: Any) -> dict[str, Any]:
    """Validate one document record against the P.001 contract.

    Raises CanonicalLibraryError naming the violation: a
    forbidden no-cap key, an unknown field (the schema is
    ``additionalProperties: false``), a missing required field,
    an out-of-vocabulary enum, an absolute or escaping path, or
    a malformed hash. Returns the record unchanged on success.
    """
    if not isinstance(data, dict):
        raise CanonicalLibraryError("document record is not an object")
    forbidden = find_forbidden_keys(data)
    if forbidden:
        raise CanonicalLibraryError(
            "forbidden no-cap key on document record: "
            + ", ".join(sorted(forbidden)))
    unknown = sorted(set(data) - DOCUMENT_RECORD_FIELDS)
    if unknown:
        raise CanonicalLibraryError(
            "unknown field on document record: " + ", ".join(unknown))
    for name in _REQUIRED_FIELDS:
        if name not in data:
            raise CanonicalLibraryError(
                f"document record missing required field: {name}")
    if not _ROLE_TOKEN.match(str(data["role"])):
        raise CanonicalLibraryError(
            f"invalid role token: {data['role']!r}")
    if data["priority"] not in PRIORITIES:
        raise CanonicalLibraryError(
            f"invalid priority: {data['priority']!r}")
    if data["trust_class"] not in TRUST_CLASSES:
        raise CanonicalLibraryError(
            f"invalid trust_class: {data['trust_class']!r}")
    if data["privacy_class"] not in PRIVACY_CLASSES:
        raise CanonicalLibraryError(
            f"invalid privacy_class: {data['privacy_class']!r}")
    if data["status"] not in STATUSES:
        raise CanonicalLibraryError(f"invalid status: {data['status']!r}")
    if data["conflict_policy"] not in CONFLICT_POLICIES:
        raise CanonicalLibraryError(
            f"invalid conflict_policy: {data['conflict_policy']!r}")
    if data["state"] not in DOCUMENT_STATES:
        raise CanonicalLibraryError(f"invalid state: {data['state']!r}")
    if not _SHA256_HEX.match(str(data["sha256"])):
        raise CanonicalLibraryError("sha256 is not 64 lowercase hex chars")
    if not isinstance(data["byte_length"], int) or data["byte_length"] < 0:
        raise CanonicalLibraryError("byte_length must be a non-negative int")
    path = str(data["path"])
    if os.path.isabs(path) or path.startswith("/"):
        raise CanonicalLibraryError(
            "document path must be relative to the library root")
    parts = Path(path).parts
    if ".." in parts:
        raise CanonicalLibraryError(
            "document path escapes the library root")
    prov = data.get("provenance") or {}
    if prov.get("kind", "local-file") not in SOURCE_KINDS:
        raise CanonicalLibraryError(
            f"invalid provenance kind: {prov.get('kind')!r}")
    return data


# ----------------------------------------------------------------
# P.002 + P.005 -- streaming byte-exact ingestion, section spans
# ----------------------------------------------------------------

#: Default ingestion work unit: 1 MiB. An *operations* quota
#: (import pacing / parser work-unit size), tunable per
#: ingester -- it never appears on a document record and never
#: limits what may be ingested.
DEFAULT_WORK_UNIT = 1024 * 1024

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_SETEXT_RE = re.compile(r"^(=+|-+)\s*$")
_FENCE_RE = re.compile(r"^\s*(```+|~~~+)")


@dataclass
class SectionSpan:
    """One Markdown section as an exact byte range (P.005)."""

    section_id: str
    stable_id: str
    heading: str
    level: int
    byte_start: int
    byte_end: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id, "stable_id": self.stable_id,
            "heading": self.heading, "level": self.level,
            "byte_start": self.byte_start, "byte_end": self.byte_end,
            "sha256": self.sha256,
        }


@dataclass
class Checkpoint:
    """A resume checkpoint: byte offset + prefix hash state.

    Checkpoints carry serialised hash state, never partial
    text (draft section 3 step 7). Resume re-streams the
    prefix to rebuild decoder/section state and verifies the
    prefix digest before continuing.
    """

    byte_offset: int
    sha256_prefix: str

    def to_dict(self) -> dict[str, Any]:
        return {"byte_offset": self.byte_offset,
                "sha256_prefix": self.sha256_prefix}


@dataclass
class IngestResult:
    path: str
    sha256: str
    byte_length: int
    status: str
    sections: list[SectionSpan] = field(default_factory=list)
    error: str = ""
    error_offset: int | None = None
    resumed_from: int = 0


class StreamingIngester:
    """Chunked, byte-exact ingestion front door (P.002)."""

    def __init__(self, work_unit: int = DEFAULT_WORK_UNIT) -> None:
        if work_unit <= 0:
            raise CanonicalLibraryError("work_unit must be positive")
        self.work_unit = work_unit

    # -- low-level streaming primitives --------------------------

    def hash_file(self, path: Path) -> tuple[str, int]:
        """Streaming SHA-256 + byte length of a file's raw bytes."""
        hasher = hashlib.sha256()
        total = 0
        with open(path, "rb") as fh:
            while True:
                chunk = fh.read(self.work_unit)
                if not chunk:
                    break
                hasher.update(chunk)
                total += len(chunk)
        return hasher.hexdigest(), total

    def verify_file(self, path: Path, expected_sha256: str) -> bool:
        digest, _ = self.hash_file(path)
        return digest == expected_sha256

    def export_file(self, src: Path, dst: Path) -> str:
        """Stream-copy *src* to *dst*; return the copied digest.

        Export reproduces the original byte stream, never a
        re-serialisation; the digest is computed over the bytes
        as copied and fsynced before return.
        """
        hasher = hashlib.sha256()
        dst.parent.mkdir(parents=True, exist_ok=True)
        with open(src, "rb") as fin, open(dst, "wb") as fout:
            while True:
                chunk = fin.read(self.work_unit)
                if not chunk:
                    break
                hasher.update(chunk)
                fout.write(chunk)
            fout.flush()
            os.fsync(fout.fileno())
        return hasher.hexdigest()

    def iter_section_bytes(
        self, path: Path, span: SectionSpan
    ) -> Iterator[bytes]:
        """Yield a section's exact bytes, streaming."""
        remaining = span.byte_end - span.byte_start
        with open(path, "rb") as fh:
            fh.seek(span.byte_start)
            while remaining > 0:
                chunk = fh.read(min(self.work_unit, remaining))
                if not chunk:
                    break
                yield chunk
                remaining -= len(chunk)

    def section_digest(self, path: Path, span: SectionSpan) -> str:
        hasher = hashlib.sha256()
        for chunk in self.iter_section_bytes(path, span):
            hasher.update(chunk)
        return hasher.hexdigest()

    # -- the ingestion pipeline ----------------------------------

    def ingest_file(
        self,
        path: Path,
        role: str,
        document_id: str = "",
        checkpoint_sink: Callable[[Checkpoint], None] | None = None,
        resume_from: Checkpoint | None = None,
    ) -> IngestResult:
        """Ingest one file: hash, UTF-8 validation, sections.

        Never raises for content problems: an I/O error or an
        invalid UTF-8 sequence produces an ``unreadable``
        result carrying the failure offset/reason (failure
        honesty, draft section 3); the caller's manifest
        transaction decides what commits.
        """
        path = Path(path)
        hasher = hashlib.sha256()
        decoder = codecs.getincrementaldecoder("utf-8")()
        total = 0
        sections: list[dict[str, Any]] = []
        hashers: list[Any] = []
        in_fence = False
        fence_char = ""
        # YAML front matter at the very start of a document is
        # preamble content (draft section 4): its closing fence
        # must never promote the last front-matter line to a
        # Setext heading.
        in_front_matter = False
        seen_any_line = False
        # One-line delay so a Setext underline can promote the
        # pending line to a heading (draft section 4).
        pending: dict[str, Any] | None = None
        error = ""
        error_offset: int | None = None
        fast_forward = resume_from.byte_offset if resume_from else 0
        resumed = 0

        def start_section(heading: str, level: int, start: int,
                          slug_base: str) -> None:
            sections.append({
                "heading": heading, "level": level,
                "byte_start": start, "slug_base": slug_base,
            })
            hashers.append(hashlib.sha256())

        def assign(line: dict[str, Any]) -> None:
            nonlocal in_fence, fence_char
            raw: bytes = line["raw"]
            text: str = line["text"]
            stripped = text.strip()
            fence = _FENCE_RE.match(text)
            if fence:
                marker = fence.group(1)
                if not in_fence:
                    in_fence, fence_char = True, marker[0]
                elif marker[0] == fence_char:
                    in_fence = False
            heading_match = None
            if not in_fence and not fence and not line.get("plain"):
                heading_match = _HEADING_RE.match(text.rstrip("\r\n"))
            if heading_match:
                if sections:
                    sections[-1]["byte_end"] = line["start"]
                raw_heading = heading_match.group(2)
                semantic = display_heading(raw_heading)
                start_section(semantic, len(heading_match.group(1)),
                              line["start"], _slugify(semantic))
            elif not sections:
                start_section("preamble", 0, line["start"], "_preamble")
            hashers[-1].update(raw)

        def feed_line(raw: bytes, start: int) -> None:
            nonlocal pending, error, error_offset
            nonlocal in_front_matter, seen_any_line
            try:
                text = decoder.decode(raw)
            except UnicodeDecodeError as exc:
                error = f"invalid UTF-8: {exc.reason}"
                error_offset = start + exc.start
                raise
            line = {"raw": raw, "text": text, "start": start,
                    "end": start + len(raw)}
            stripped = text.strip()
            if not seen_any_line:
                seen_any_line = True
                if stripped == "---":
                    in_front_matter = True
            elif in_front_matter and pending is not None and \
                    pending.get("plain") and \
                    pending["text"].strip() in ("---", "...") and \
                    pending["start"] != 0:
                in_front_matter = False
            if in_front_matter:
                line["plain"] = True
            if pending is not None:
                setext = _SETEXT_RE.match(line["text"].strip())
                prev_text = pending["text"].strip()
                if (setext and prev_text and not in_fence
                        and pending.get("kind") == "text"):
                    if sections:
                        sections[-1]["byte_end"] = pending["start"]
                    semantic = display_heading(prev_text)
                    level = 1 if setext.group(1).startswith("=") else 2
                    start_section(semantic, level, pending["start"],
                                  _slugify(semantic))
                    hashers[-1].update(pending["raw"])
                    hashers[-1].update(raw)
                    pending = None
                    return
                assign(pending)
            line["kind"] = (
                "text" if line["text"].strip() and not line.get("plain")
                and not _HEADING_RE.match(line["text"].rstrip("\r\n"))
                and not _FENCE_RE.match(line["text"]) else "other")
            pending = line

        if resume_from is not None:
            prefix_hasher = hashlib.sha256()
            remaining = resume_from.byte_offset
            with open(path, "rb") as fh:
                while remaining > 0:
                    part = fh.read(min(self.work_unit, remaining))
                    if not part:
                        break
                    prefix_hasher.update(part)
                    remaining -= len(part)
            if prefix_hasher.hexdigest() != resume_from.sha256_prefix:
                raise CanonicalLibraryError(
                    "resume checkpoint prefix hash mismatch: "
                    "the source changed since the checkpoint")
        try:
            with open(path, "rb") as fh:
                buffer = b""
                while True:
                    chunk = fh.read(self.work_unit)
                    if not chunk:
                        break
                    hasher.update(chunk)
                    total += len(chunk)
                    if total <= fast_forward:
                        # Rebuilding state for a resume: the
                        # prefix digest is verified by the
                        # caller-visible check below; lines are
                        # still fed so section state is exact.
                        resumed = total
                    buffer += chunk
                    lines = buffer.split(b"\n")
                    buffer = lines.pop()
                    # Lines are fed with a running byte cursor
                    # so every section range is an exact offset
                    # into the original bytes (CRLF-safe).
                    cursor = self._line_cursor
                    for part in lines:
                        raw_line = part + b"\n"
                        feed_line(raw_line, cursor)
                        cursor += len(raw_line)
                    self._line_cursor = cursor
                    self._pending_buffer = buffer
                    if checkpoint_sink is not None:
                        checkpoint_sink(Checkpoint(
                            byte_offset=total,
                            sha256_prefix=hasher.copy().hexdigest()))
                    if error:
                        break
                if not error and (buffer or pending is not None
                                  or self._pending_buffer):
                    tail = buffer
                    if tail:
                        feed_line(tail, self._line_cursor)
                        self._line_cursor += len(tail)
                if pending is not None:
                    assign(pending)
                    pending = None
                # Final decoder flush: a truncated multibyte
                # sequence at EOF is an error, never a
                # replacement character.
                try:
                    decoder.decode(b"", final=True)
                except UnicodeDecodeError as exc:
                    error = f"invalid UTF-8 at EOF: {exc.reason}"
                    error_offset = total - max(1, exc.start)
        except (OSError, UnicodeDecodeError) as exc:
            if isinstance(exc, UnicodeDecodeError) and not error:
                error = f"invalid UTF-8: {exc.reason}"
        finally:
            self._line_cursor = 0
            self._pending_buffer = b""
        if resume_from is not None:
            resumed = resume_from.byte_offset
        if sections:
            sections[-1]["byte_end"] = total
        spans: list[SectionSpan] = []
        if not error:
            seen: dict[str, int] = {}
            had_heading = any(s["level"] > 0 for s in sections)
            for meta, sec_hasher in zip(sections, hashers):
                base = meta["slug_base"]
                seen[base] = seen.get(base, 0) + 1
                slug = base if seen[base] == 1 else f"{base}_{seen[base]}"
                spans.append(SectionSpan(
                    section_id=slug,
                    stable_id=stable_section_id(role, slug),
                    heading=meta["heading"], level=meta["level"],
                    byte_start=meta["byte_start"],
                    byte_end=meta["byte_end"],
                    sha256=sec_hasher.hexdigest()))
            if len(spans) == 1 and not had_heading and document_id:
                # No-heading file: one root section whose
                # identity is the document id itself.
                spans[0].section_id = document_id
                spans[0].stable_id = document_id
        status = "unreadable" if error else "complete"
        return IngestResult(
            path=str(path), sha256=hasher.hexdigest(),
            byte_length=total, status=status, sections=spans,
            error=error, error_offset=error_offset,
            resumed_from=resumed)

    _line_cursor: int = 0
    _pending_buffer: bytes = b""


# ----------------------------------------------------------------
# P.004 -- transactional manifest store
# ----------------------------------------------------------------

MANIFEST_SCHEMA_VERSION = 1


class ManifestStore:
    """The derived, rebuildable manifest of one persona library.

    Layout under the library root: ``generated/manifest.json``,
    ``generated/manifest.journal.jsonl``,
    ``generated/.manifest.lock``. Canonical bytes never live in
    the manifest; deleting it and re-ingesting reproduces it.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.generated = self.root / "generated"
        self.manifest_path = self.generated / "manifest.json"
        self.journal_path = self.generated / "manifest.journal.jsonl"
        self.lock_path = self.generated / ".manifest.lock"

    # -- reading --------------------------------------------------

    def _empty(self, persona_id: str = "") -> dict[str, Any]:
        return {"schema_version": MANIFEST_SCHEMA_VERSION,
                "generation": 0, "persona_id": persona_id,
                "documents": {}}

    def _journal_tail_generation(self) -> int:
        if not self.journal_path.exists():
            return 0
        tail = 0
        with open(self.journal_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    tail = int(json.loads(line)["generation"])
        return tail

    def _replay_journal(self, upto: int | None = None) -> dict[str, Any]:
        manifest = self._empty()
        if not self.journal_path.exists():
            return manifest
        with open(self.journal_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if upto is not None and entry["generation"] > upto:
                    break
                for change in entry["changes"]:
                    record = change.get("record")
                    if record is not None:
                        manifest["documents"][record["document_id"]] = record
                    elif change.get("change_kind") == "remove":
                        manifest["documents"].pop(change["document_id"], None)
                manifest["generation"] = entry["generation"]
                manifest["persona_id"] = entry.get(
                    "persona_id", manifest["persona_id"])
        return manifest

    def load(self) -> dict[str, Any]:
        """Load the manifest, recovering honestly if torn.

        A manifest whose JSON fails validation or whose
        generation disagrees with the journal tail is
        quarantined and rebuilt from the journal; sources are
        never touched by recovery.
        """
        if not self.manifest_path.exists():
            return self._replay_journal() if self.journal_path.exists() \
                else self._empty()
        try:
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or "documents" not in data:
                raise CanonicalLibraryError("manifest shape invalid")
            for record in data["documents"].values():
                validate_record(record)
            tail = self._journal_tail_generation()
            if tail and data.get("generation") != tail:
                raise CanonicalLibraryError(
                    "manifest generation disagrees with journal tail")
            return data
        except (ValueError, CanonicalLibraryError):
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            quarantine = self.generated / f"manifest.corrupt-{stamp}.json"
            os.replace(self.manifest_path, quarantine)
            return self._replay_journal()

    # -- writing ----------------------------------------------------

    def _acquire_lock(self, timeout_s: float) -> int:
        self.generated.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return fd
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    os.close(fd)
                    raise LockTimeoutError(
                        f"manifest lock not acquired within {timeout_s}s")
                time.sleep(0.05)

    @staticmethod
    def _fsync_dir(path: Path) -> None:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def _write_manifest_atomic(self, manifest: dict[str, Any]) -> None:
        tmp = self.generated / f"manifest.json.tmp-{manifest['generation']}"
        payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.manifest_path)
        self._fsync_dir(self.generated)

    def commit(self, records: list[DocumentRecord],
               persona_id: str = "", timeout_s: float = 10.0,
               change_kind: str = "upsert") -> dict[str, Any]:
        """Commit document changes as one transaction.

        Generation increments exactly once per committed
        transaction, however many documents it carries. The
        journal line is the audit spine: generation, timestamp,
        and per-doc old/new hash + revision + the full record.
        """
        for record in records:
            validate_record(record.to_dict())
        fd = self._acquire_lock(timeout_s)
        try:
            manifest = self.load()
            if persona_id:
                manifest["persona_id"] = persona_id
            changes: list[dict[str, Any]] = []
            for record in records:
                data = record.to_dict()
                old = manifest["documents"].get(record.document_id)
                changes.append({
                    "document_id": record.document_id,
                    "old_sha256": old["sha256"] if old else None,
                    "new_sha256": data["sha256"],
                    "old_revision": old["revision"] if old else 0,
                    "new_revision": data["revision"],
                    "change_kind": change_kind,
                    "record": data,
                })
                manifest["documents"][record.document_id] = data
            manifest["generation"] += 1
            self._write_manifest_atomic(manifest)
            entry = {"generation": manifest["generation"],
                     "timestamp": _utc_now(),
                     "persona_id": manifest["persona_id"],
                     "changes": changes}
            with open(self.journal_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            return manifest
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def rollback_to_generation(self, generation: int,
                               timeout_s: float = 10.0) -> dict[str, Any]:
        """Rewind derived state to a journal generation.

        Rollback only rewinds the manifest (derived state); it
        never edits sources -- migration itself never edits
        sources, so there is nothing else to undo. The rewind
        is itself committed as a new generation so the journal
        stays append-only and auditable.
        """
        target = self._replay_journal(upto=generation)
        fd = self._acquire_lock(timeout_s)
        try:
            current = self.load()
            target["generation"] = current["generation"] + 1
            self._write_manifest_atomic(target)
            entry = {"generation": target["generation"],
                     "timestamp": _utc_now(),
                     "persona_id": target["persona_id"],
                     "changes": [{
                         "document_id": doc_id,
                         "old_sha256": None,
                         "new_sha256": record["sha256"],
                         "old_revision": 0,
                         "new_revision": record["revision"],
                         "change_kind": "rollback",
                         "record": record,
                     } for doc_id, record in target["documents"].items()]}
            # Documents present now but absent at the target are
            # removed by the rewind; record the removals too.
            for doc_id, record in current["documents"].items():
                if doc_id not in target["documents"]:
                    entry["changes"].append({
                        "document_id": doc_id,
                        "old_sha256": record["sha256"],
                        "new_sha256": None, "old_revision": record["revision"],
                        "new_revision": 0, "change_kind": "remove",
                        "record": None})
            with open(self.journal_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            return target
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)


# ----------------------------------------------------------------
# Facade + P.003 migration dry-run
# ----------------------------------------------------------------


class CanonicalLibrary:
    """One persona's canonical source library.

    Sources live in place under ``root`` (their ``path`` is
    relative to it); derived state lives under
    ``root/generated``. Ingestion reads sources; it never
    copies, rewrites or re-encodes them.
    """

    def __init__(self, root: Path, persona_id: str,
                 work_unit: int = DEFAULT_WORK_UNIT) -> None:
        self.root = Path(root)
        self.persona_id = persona_id
        self.ingester = StreamingIngester(work_unit)
        self.store = ManifestStore(self.root)

    def _source_path(self, relpath: str) -> Path:
        candidate = (self.root / relpath).resolve()
        root_resolved = self.root.resolve()
        if candidate != root_resolved and \
                root_resolved not in candidate.parents:
            raise CanonicalLibraryError(
                f"path escapes the library root: {relpath}")
        return candidate

    def ingest(self, relpath: str, role: str, *,
               trust_class: str = "authored-canon",
               privacy_class: str = "private", priority: str = "P2",
               namespace: str = "default",
               provenance: dict[str, Any] | None = None,
               include_rules: Iterable[str] = (),
               commit: bool = True) -> DocumentRecord:
        """Ingest one source and (by default) commit its record.

        Revision discipline: a first ingestion is revision 1;
        a re-ingestion whose hash changed bumps the revision;
        an unchanged re-ingestion keeps it. An unreadable
        source records status ``unreadable`` with its last
        known hash retained -- absence/failure is a state,
        never a silent deletion.
        """
        source = self._source_path(relpath)
        document_id = mint_document_id(self.persona_id, relpath)
        existing = self.store.load()["documents"].get(document_id)
        now = _utc_now()
        if not source.exists():
            if existing is None:
                raise CanonicalLibraryError(
                    f"source does not exist: {relpath}")
            record = DocumentRecord.from_dict(existing)
            record.status = "unreadable"
            if commit:
                self.store.commit([record], persona_id=self.persona_id)
            return record
        result = self.ingester.ingest_file(source, role, document_id)
        if result.status != "complete":
            if existing is not None:
                record = DocumentRecord.from_dict(existing)
                record.status = "unreadable"
                if commit:
                    self.store.commit([record], persona_id=self.persona_id)
                return record
            raise CanonicalLibraryError(
                f"ingestion failed for {relpath}: {result.error} "
                f"at byte {result.error_offset}")
        revision = 1
        first_seen = now
        if existing is not None:
            first_seen = existing.get("first_seen_at") or now
            revision = existing["revision"] + (
                1 if existing["sha256"] != result.sha256 else 0)
        record = DocumentRecord(
            document_id=document_id, role=role, path=relpath,
            namespace=namespace, sha256=result.sha256,
            byte_length=result.byte_length, revision=revision,
            priority=priority, trust_class=trust_class,
            privacy_class=privacy_class, persona_id=self.persona_id,
            status="indexed",
            provenance=provenance or {"kind": "local-file",
                                       "origin": relpath},
            include_rules=list(include_rules),
            first_seen_at=first_seen, last_verified_at=now,
            last_compiled_at=now,
            sections=[s.to_dict() for s in result.sections])
        if commit:
            self.store.commit([record], persona_id=self.persona_id)
        return record

    def ingest_tree(self, relpaths: Iterable[str],
                    role_for: Callable[[str], str | None], *,
                    include_rule: str = "") -> list[DocumentRecord]:
        """Ingest many sources as ONE manifest transaction.

        Files whose role cannot be determined are skipped and
        reported by omission from the result -- callers diff
        the input set against the result to list unmapped
        files; nothing is silently assigned a role.
        """
        records: list[DocumentRecord] = []
        for relpath in relpaths:
            role = role_for(relpath)
            if role is None:
                continue
            record = self.ingest(
                relpath, role, commit=False,
                include_rules=[include_rule] if include_rule else [])
            records.append(record)
        if records:
            self.store.commit(records, persona_id=self.persona_id)
        return records

    def verify(self, document_id: str) -> bool:
        """Re-hash a source and compare with its record."""
        manifest = self.store.load()
        data = manifest["documents"].get(document_id)
        if data is None:
            raise CanonicalLibraryError(f"unknown document: {document_id}")
        source = self._source_path(data["path"])
        if not source.exists():
            return False
        return self.ingester.verify_file(source, data["sha256"])

    def export(self, document_id: str, dst: Path) -> str:
        """Export a source byte-exactly; return the digest."""
        manifest = self.store.load()
        data = manifest["documents"].get(document_id)
        if data is None:
            raise CanonicalLibraryError(f"unknown document: {document_id}")
        digest = self.ingester.export_file(
            self._source_path(data["path"]), Path(dst))
        if digest != data["sha256"]:
            raise CanonicalLibraryError(
                f"export digest mismatch for {document_id}")
        return digest

    def list_documents(self) -> list[dict[str, Any]]:
        manifest = self.store.load()
        return [manifest["documents"][key]
                for key in sorted(manifest["documents"])]


def migration_dry_run(sources: Iterable[Path], persona_id: str,
                      work_unit: int = DEFAULT_WORK_UNIT) -> dict[str, Any]:
    """P.003 dry-run over a candidate source set (draft section 6).

    Verify-only: hashes and section previews are computed by
    streaming, no manifest is committed anywhere, and every
    source is re-hashed afterwards so the report itself proves
    the dry-run moved nothing. The report carries no wall-clock
    timestamps in its comparable body, so two runs over the
    same set produce identical ``comparable`` payloads (the
    idempotence gate).
    """
    ingester = StreamingIngester(work_unit)
    files: list[dict[str, Any]] = []
    warnings: list[str] = []
    seen_roles: dict[str, str] = {}
    for source in sources:
        source = Path(source)
        entry: dict[str, Any] = {"name": source.name,
                                 "path": str(source)}
        if source.is_symlink():
            warnings.append(f"symlink source (reviewed, not followed "
                            f"blindly): {source}")
        if not source.exists():
            entry.update({"status": "unreadable",
                          "error": "source does not exist"})
            files.append(entry)
            continue
        digest, length = ingester.hash_file(source)
        role = default_role_for_filename(source.name)
        entry.update({"sha256": digest, "byte_length": length,
                      "role": role})
        if role is None:
            entry["status"] = "unmapped"
        else:
            if role in seen_roles:
                warnings.append(
                    f"duplicate role {role}: {seen_roles[role]} and "
                    f"{source.name}")
            seen_roles[role] = source.name
            result = ingester.ingest_file(
                source, role, mint_document_id(persona_id, source.name))
            entry["status"] = ("simulated" if result.status == "complete"
                                else "unreadable")
            entry["sections"] = [s.to_dict() for s in result.sections]
            if result.error:
                entry["error"] = result.error
                entry["error_offset"] = result.error_offset
        after, _ = ingester.hash_file(source)
        entry["unchanged_after"] = (after == digest)
        files.append(entry)
    comparable = {"persona_id": persona_id, "files": files,
                  "warnings": warnings}
    return {"kind": "migration-dry-run", "persona_id": persona_id,
            "files": files, "warnings": warnings,
            "comparable": comparable}
