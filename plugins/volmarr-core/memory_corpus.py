"""Unbounded memory corpus: the P.014 bridge foundation (W06 / P5).

Design: docs/modernization/P5_DESIGN_DRAFT.md sections 4.1-4.2,
4.4, 4.9; slices M1 (corpus foundation) and M2 (index wiring).

Three named things, never blurred (draft section 4.1):

1. **Full store** -- the profile's ``memories/MEMORY.md`` and
   ``memories/USER.md`` as complete authored documents, ingested
   into a W03 ``CanonicalLibrary`` rooted at the profile. The
   files on disk remain the canonical bytes; the manifest and
   index are generated, deletable, rebuildable artefacts.
2. **Hot digest** -- a derived, bounded, source-linked digest
   (``memory_digest.py``). It never writes back over the source.
3. **Stock snapshot** -- the stock curated store's bounded view
   (2,200 / 1,375 chars). Untouched and still owned by the stock
   ``MemoryStore``; this module only *reports* its size honestly.

Namespace ruling (draft section 4.1): the corpus is rooted in the
profile/user namespace. The W03 library is keyed by that profile
namespace id; a persona id appears only as a consumer label on
receipts -- memory is not owned by the persona that reads it.

No new store and no second index are built here: storage is the
W03 canonical library, retrieval is the W04 persona index rooted
at the same library. Plugin-side only; no core file is touched.
With ``memory_corpus_enabled`` false (the default) nothing in
this module is constructed on a turn path and stock behaviour is
byte-identical.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .canonical_library import (
    CanonicalLibrary,
    CanonicalLibraryError,
    StreamingIngester,
    default_role_for_filename,
    migration_dry_run,
    mint_document_id,
)
from .persona_index import PersonaIndex

__all__ = [
    "ENTRY_DELIMITER", "HOT_CAPS", "MEMORY_TARGETS",
    "MemoryCorpus", "MemoryCorpusError", "ObservationOverwriteRefused",
    "corpus_from_plugin_context", "parse_entries",
]

#: Stock entry delimiter (tools/memory_tool_store.py) -- the
#: adapter's entry model must parse exactly what the stock tool
#: parses, so the constant is mirrored here, never re-derived.
ENTRY_DELIMITER = "\n\u00a7\n"

#: Stock curated caps, REPORTED ONLY. They bound the hot view the
#: stock tool serves; they never bound this corpus (draft 4.1).
HOT_CAPS = {"memory": 2200, "user": 1375}

#: target -> (profile-relative path, canonical role)
MEMORY_TARGETS = {
    "memory": ("memories/MEMORY.md", "memory"),
    "user": ("memories/USER.md", "user"),
}

_BACKUP_KIND = "volmarr-memory-corpus-backup"
_BACKUP_VERSION = 1


class MemoryCorpusError(Exception):
    """A memory-corpus refusal or failure (named, never silent)."""


class ObservationOverwriteRefused(MemoryCorpusError):
    """Section 41 guard: an agent observation may not overwrite
    authored canon (draft 4.3 / P.015)."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_entries(text: str) -> list[str]:
    """Stock-identical entry parsing (strip, drop empties)."""
    return [e for e in (x.strip() for x in text.split(ENTRY_DELIMITER)) if e]


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class MemoryCorpus:
    """One profile's unbounded MEMORY.md / USER.md corpus."""

    def __init__(self, profile_root: Path, *,
                 namespace_id: str = "profile:default",
                 consumer_persona_id: str | None = None) -> None:
        self.root = Path(profile_root)
        self.namespace_id = namespace_id
        self.consumer_persona_id = consumer_persona_id
        self.library = CanonicalLibrary(self.root, namespace_id)
        self.index = PersonaIndex(self.root, namespace_id)
        self._ingester = StreamingIngester()

    # -- paths ----------------------------------------------------

    @property
    def memories_dir(self) -> Path:
        return self.root / "memories"

    def target_path(self, target: str) -> Path:
        if target not in MEMORY_TARGETS:
            raise MemoryCorpusError(f"unknown memory target: {target}")
        return self.root / MEMORY_TARGETS[target][0]

    def document_id(self, target: str) -> str:
        return mint_document_id(
            self.namespace_id, MEMORY_TARGETS[target][0])

    def _record(self, target: str) -> dict[str, Any] | None:
        manifest = self.library.store.load()
        return manifest["documents"].get(self.document_id(target))

    # -- M1: inventory + import (draft 4.2) ------------------------

    def inventory(self) -> dict[str, Any]:
        """Files, sizes, streaming hashes, proposed roles.

        Anything in ``memories/`` that is not MEMORY.md / USER.md
        is reported ``unmapped`` -- never guessed, never ingested.
        """
        files: list[dict[str, Any]] = []
        if self.memories_dir.is_dir():
            for path in sorted(self.memories_dir.iterdir()):
                if not path.is_file():
                    continue
                digest, length = self._ingester.hash_file(path)
                role = default_role_for_filename(path.name)
                files.append({
                    "name": path.name,
                    "path": f"memories/{path.name}",
                    "sha256": digest, "byte_length": length,
                    "role": role,
                    "status": "mapped" if role in ("memory", "user")
                    else "unmapped"})
        return {"kind": "memory-corpus-inventory",
                "namespace_id": self.namespace_id,
                "profile_root": str(self.root), "files": files}

    def dry_run_import(self) -> dict[str, Any]:
        """P.003-style verify-only import simulation.

        Proves per file that nothing moved (``unchanged_after``)
        and commits nothing anywhere.
        """
        sources = [self.target_path(t) for t in ("memory", "user")
                   if self.target_path(t).exists()]
        report = migration_dry_run(sources, self.namespace_id)
        report["kind"] = "memory-corpus-import-dry-run"
        return report

    def import_corpus(self, *, confirm: bool = False) -> dict[str, Any]:
        """Import the profile's memory files into the library.

        Without ``confirm`` this is the dry-run and nothing is
        ingested. With ``confirm`` the mapped files are ingested
        verbatim as ONE manifest transaction; sources are read in
        place, never copied, rewritten or re-encoded. The empty
        profile is an honest no-op receipt, not an error, and no
        stub files are created.
        """
        if not confirm:
            return self.dry_run_import()
        present = [t for t in ("memory", "user")
                   if self.target_path(t).exists()]
        if not present:
            return {"kind": "memory-corpus-import", "status": "empty",
                    "namespace_id": self.namespace_id, "documents": [],
                    "generation": self.library.store.load()["generation"]}
        relpaths = [MEMORY_TARGETS[t][0] for t in present]
        roles = {MEMORY_TARGETS[t][0]: MEMORY_TARGETS[t][1]
                 for t in present}
        records = self.library.ingest_tree(
            relpaths, lambda rel: roles.get(rel))
        for record in records:
            if record.status != "indexed":
                raise MemoryCorpusError(
                    f"import refused for {record.path}: "
                    f"status {record.status}")
        return {"kind": "memory-corpus-import", "status": "imported",
                "namespace_id": self.namespace_id,
                "documents": [r.to_dict() for r in records],
                "generation": self.library.store.load()["generation"]}

    # -- M2: index wiring (draft 5, M2) ----------------------------

    def sync_index(self) -> dict[str, Any]:
        return self.index.sync()

    def index_status(self) -> dict[str, Any]:
        return self.index.index_status()

    def repair_index(self) -> dict[str, Any]:
        """Delete ONLY the derived index and rebuild it.

        The manifest, journal and canonical files are not index
        artefacts and are never touched here. Returns the status
        before and after so the rebuild is auditable.
        """
        before = self.index.index_status()
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(str(self.index.db_path) + suffix)
            if candidate.exists():
                candidate.unlink()
        after = self.index.sync(force=True)
        return {"kind": "memory-corpus-index-repair",
                "before": before, "after": after}

    # -- reads: retrieval / citation / paging ----------------------

    def retrieve(self, query: str, *, limit: int = 5,
                 destination: str = "local") -> dict[str, Any]:
        """W04 retrieval over the corpus, with the P.018 filter.

        ``destination="cloud"`` refuses private-classified
        results BEFORE egress: they are removed from the result
        set and named on the returned receipt, so the filter is
        evidence, not a promise. Local retrieval is unfiltered.
        """
        out = self.index.retrieve(query, limit=limit)
        if destination == "cloud":
            kept, refused = [], []
            for row in out["results"]:
                if row.get("privacy_class") == "private":
                    refused.append({"stable_id": row["stable_id"],
                                    "reason": "private_source_cloud_refused"})
                else:
                    kept.append(row)
            out = dict(out, results=kept)
            receipt = dict(out["receipt"])
            receipt["cloud_egress"] = len(kept)
            receipt["privacy_refused"] = refused
            out["receipt"] = receipt
        elif destination != "local":
            raise MemoryCorpusError(
                f"unknown retrieval destination: {destination}")
        return out

    def cite(self, stable_id: str, *, destination: str = "local") -> dict[str, Any]:
        result = self.index.cite(stable_id)
        if destination == "cloud" \
                and result.get("privacy_class") == "private":
            raise MemoryCorpusError(
                f"private source refused for cloud egress: {stable_id}")
        if destination not in ("local", "cloud"):
            raise MemoryCorpusError(
                f"unknown citation destination: {destination}")
        return result

    def read_page(self, document_id: str, cursor: int = 0,
                  max_bytes: int | None = None) -> dict[str, Any]:
        if max_bytes is None:
            return self.index.read_page(document_id, cursor)
        return self.index.read_page(document_id, cursor, max_bytes)

    # -- status: the truthful three-store report (draft 4.5) -------

    def status(self) -> dict[str, Any]:
        manifest = self.library.store.load()
        targets: dict[str, Any] = {}
        for target in ("memory", "user"):
            path = self.target_path(target)
            record = self._record(target)
            entry: dict[str, Any] = {
                "path": MEMORY_TARGETS[target][0],
                "exists": path.exists(),
                "full_store_bytes": path.stat().st_size
                if path.exists() else 0,
                "hot_cap_chars": HOT_CAPS[target],
                "document_id": self.document_id(target),
                "ingested": record is not None}
            if path.exists():
                text = path.read_bytes().decode("utf-8")
                entries = parse_entries(text)
                hot_chars = len(ENTRY_DELIMITER.join(entries))
                entry["snapshot_chars"] = hot_chars
                entry["snapshot_over_cap"] = hot_chars > HOT_CAPS[target]
            if record is not None:
                entry.update({
                    "sha256": record["sha256"],
                    "byte_length": record["byte_length"],
                    "revision": record["revision"],
                    "sections": len(record.get("sections") or []),
                    "trust_class": record.get("trust_class"),
                    "privacy_class": record.get("privacy_class")})
            targets[target] = entry
        return {"kind": "memory-corpus-status",
                "namespace_id": self.namespace_id,
                "consumer_persona_id": self.consumer_persona_id,
                "profile_root": str(self.root),
                "generation": manifest["generation"],
                "index": self.index_status(),
                "targets": targets}

    def status_block(self) -> dict[str, Any]:
        """The compact adapter-facing status block (draft 4.5)."""
        full = self.status()
        return {
            "full_store_bytes": {
                t: full["targets"][t]["full_store_bytes"]
                for t in ("memory", "user")},
            "snapshot_chars": {
                t: full["targets"][t].get("snapshot_chars", 0)
                for t in ("memory", "user")},
            "snapshot_caps": dict(HOT_CAPS),
            "snapshot_over_cap": {
                t: bool(full["targets"][t].get("snapshot_over_cap"))
                for t in ("memory", "user")},
            "corpus_generation": full["generation"],
            "index_status": full["index"]["status"]}

    # -- writes: transactional, scoped, audited (draft 4.4) --------

    def _after_source_write(self, target: str) -> dict[str, Any]:
        record = self.library.ingest(
            MEMORY_TARGETS[target][0], MEMORY_TARGETS[target][1])
        self.index.sync()
        return {"document_id": record.document_id,
                "sha256": record.sha256, "revision": record.revision,
                "generation": self.library.store.load()["generation"]}

    def append_entry(self, target: str, content: str, *,
                     provenance: str = "authored") -> dict[str, Any]:
        """Append-only full-store write; prior bytes are preserved
        exactly (the new bytes are a pure suffix). Journaled by
        re-ingestion through the W03 manifest transaction."""
        text = (content or "").strip()
        if not text:
            raise MemoryCorpusError("append content cannot be empty")
        path = self.target_path(target)
        prior = path.read_bytes() if path.exists() else b""
        addition = text.encode("utf-8")
        if prior and not prior.endswith(b"\n"):
            addition = b"\n" + addition
        if prior:
            addition = b"\n" + addition
        _atomic_write_bytes(path, prior + addition)
        info = self._after_source_write(target)
        return {"kind": "memory-corpus-append", "target": target,
                "provenance": provenance,
                "appended_bytes": len(addition), **info}

    def replace_section_text(self, stable_id: str, new_text: str, *,
                             expected_section_sha256: str,
                             provenance: str = "authored") -> dict[str, Any]:
        """Section-scoped write through the citation byte range.

        The section 41 guard (P.015) is enforced HERE, at the one
        write door: a non-authored provenance may never replace
        authored canon. ``expected_section_sha256`` is the pinned
        approval semantics of draft 4.5: if the section changed
        since it was read, the write is refused as stale.
        """
        if provenance != "authored":
            raise ObservationOverwriteRefused(
                "agent-observed content may not overwrite authored "
                f"memory (section 41 guard): {stable_id}")
        citation = self.index.cite(stable_id)
        if citation["section_sha256"] != expected_section_sha256:
            raise MemoryCorpusError(
                f"stale section: {stable_id} changed since read "
                "(pinned-entry approval refused the write)")
        target = "user" if citation["role"] == "user" else "memory"
        path = self.target_path(target)
        data = path.read_bytes()
        start, end = citation["byte_start"], citation["byte_end"]
        if hashlib.sha256(data[start:end]).hexdigest() \
                != expected_section_sha256:
            raise MemoryCorpusError(
                f"section bytes drifted for {stable_id}; refusing")
        new_section = new_text.encode("utf-8")
        _atomic_write_bytes(path, data[:start] + new_section + data[end:])
        info = self._after_source_write(target)
        return {"kind": "memory-corpus-section-replace",
                "stable_id": stable_id, "target": target, **info}

    # -- observations: derived, typed, never canon (draft 4.3) -----

    @property
    def observations_path(self) -> Path:
        return self.root / "generated" / "observations.jsonl"

    def record_observation(self, target: str, content: str, *,
                           source: str = "agent") -> dict[str, Any]:
        """Store an agent observation as a DERIVED record only.

        Observations never enter the authored files. Promotion
        into canon is possible only through an authored write
        (``append_entry`` / ``replace_section_text`` with
        provenance ``authored``) -- a human-visible door.
        """
        if target not in MEMORY_TARGETS:
            raise MemoryCorpusError(f"unknown memory target: {target}")
        text = (content or "").strip()
        if not text:
            raise MemoryCorpusError("observation content cannot be empty")
        record = {"kind": "memory-observation", "target": target,
                  "provenance": "agent-observed", "source": source,
                  "recorded_at": _utc_now(), "content": text,
                  "corpus_generation":
                  self.library.store.load()["generation"]}
        path = self.observations_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return record

    def list_observations(self) -> list[dict[str, Any]]:
        path = self.observations_path
        if not path.exists():
            return []
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out

    # -- backup / restore (draft 4.9, P.019 memory half) -----------

    def backup(self, dest_dir: Path) -> dict[str, Any]:
        """Corpus backup = canonical files + manifest + journal.

        The index is EXCLUDED on purpose: it is rebuildable, and
        restore must prove that by rebuilding it. Encryption
        inherits the open W00.03-ENC question: backups are
        unencrypted-local, named as such, never silently.
        """
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        files: list[dict[str, Any]] = []
        for target in ("memory", "user"):
            src = self.target_path(target)
            if not src.exists():
                continue
            out = dest / MEMORY_TARGETS[target][0]
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, out)
            digest, length = self._ingester.hash_file(out)
            files.append({"target": target,
                          "path": MEMORY_TARGETS[target][0],
                          "sha256": digest, "byte_length": length})
        generated = self.root / "generated"
        for name in ("manifest.json", "manifest.journal.jsonl"):
            src = generated / name
            if src.exists():
                shutil.copyfile(src, dest / name)
        manifest = {"kind": _BACKUP_KIND, "version": _BACKUP_VERSION,
                    "namespace_id": self.namespace_id,
                    "created_at": _utc_now(),
                    "generation": self.library.store.load()["generation"],
                    "encryption": "none-unencrypted-local",
                    "index_included": False, "files": files}
        (dest / "backup-manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        return manifest

    @classmethod
    def restore(cls, backup_dir: Path, dest_root: Path, *,
                  namespace_id: str = "profile:default") -> dict[str, Any]:
        """Restore a backup into a fresh profile root and REBUILD
        the index from the restored manifest + sources (the index
        is never copied). Retrieval is the caller's proof step."""
        src = Path(backup_dir)
        manifest_path = src / "backup-manifest.json"
        if not manifest_path.exists():
            raise MemoryCorpusError(f"not a corpus backup: {src}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("kind") != _BACKUP_KIND:
            raise MemoryCorpusError(f"not a corpus backup: {src}")
        dest = Path(dest_root)
        for entry in manifest["files"]:
            out = dest / entry["path"]
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src / entry["path"], out)
            digest, _ = StreamingIngester().hash_file(out)
            if digest != entry["sha256"]:
                raise MemoryCorpusError(
                    f"restore hash mismatch for {entry['path']}")
        gen_dir = dest / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        for name in ("manifest.json", "manifest.journal.jsonl"):
            if (src / name).exists():
                shutil.copyfile(src / name, gen_dir / name)
        corpus = cls(dest, namespace_id=namespace_id)
        repair = corpus.repair_index()
        return {"kind": "memory-corpus-restore",
                "namespace_id": namespace_id,
                "files": manifest["files"], "repair": repair,
                "status": corpus.status()}


def corpus_from_plugin_context(ctx, *,
                               consumer_persona_id: str | None = None
                               ) -> MemoryCorpus:
    """Resolve the corpus for the active profile (draft 4.8).

    ``memory_corpus_root`` is profile-relative by default; a
    relative path that escapes the profile home is refused with
    the ``memory_fabric._profile_path`` discipline. The namespace
    id is the profile's own name -- memory belongs to the
    profile/user namespace, not to a persona (draft 4.1).
    """
    from hermes_constants import get_hermes_home

    home = get_hermes_home().resolve()
    configured = str(ctx.get_config("memory_corpus_root", "") or "")
    if not configured:
        root = home
    else:
        candidate = Path(configured)
        if candidate.is_absolute():
            root = candidate.resolve()
        else:
            root = (home / candidate).resolve()
            if not root.is_relative_to(home):
                raise MemoryCorpusError(
                    "memory_corpus_root escapes the active profile")
    return MemoryCorpus(
        root, namespace_id=f"profile:{home.name}",
        consumer_persona_id=consumer_persona_id)
