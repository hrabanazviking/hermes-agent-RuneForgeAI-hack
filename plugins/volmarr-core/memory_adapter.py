"""Old-tool adapter for the unbounded memory corpus (W06 / M4).

Design: docs/modernization/P5_DESIGN_DRAFT.md section 4.5, ticket
P.014 core. The adapter is interposed at the TOOL-RESULT level:
it never patches ``tools/memory_tool.py`` (core stays
upstream-clean, ground rule 3) and it never changes stock
semantics for a write that fits the hot caps.

Semantics, stated plainly so no surface can blur them:

- The **full store** is the profile's MEMORY.md / USER.md, held
  complete by ``memory_corpus.MemoryCorpus``. It has no cap.
- The **hot view** is the stock curated view of the same files:
  entries parsed exactly as the stock store parses them
  (``ENTRY_DELIMITER``-joined, stock ``_char_count`` rule),
  measured against the stock caps (2,200 / 1,375 chars). The
  caps bound this VIEW; they never bound the full store.
- A stock-shaped write that fits the hot caps behaves exactly
  as today and lands in both stores (they are the same bytes).
- A write that would overflow the hot caps SUCCEEDS in the full
  store, is journaled through the corpus, and the result says
  plainly ``landed_in: "full_store"`` with
  ``in_hot_view: false`` and the reason -- replacing the stock
  silent-truncation / hard-refusal cliff with an honest
  two-store answer. The adapter never reports the hot view as
  containing what it does not.
- Pinned-entry approval is preserved (stock ``_locate`` rule):
  a staged write carrying ``matched_entry`` applies only if
  that exact entry is still present; otherwise the write is
  refused as ``stale_entry`` and nothing is applied.
- Entry edits (replace / patch / remove, and entry-model adds)
  rewrite the file as the stock store itself would
  (delimiter-joined entries) -- but ONLY when the file already
  round-trips through the stock entry model byte-exactly AND is
  entry-shaped (it carries the stock delimiter, or it carries
  no heading structure at all). A free-form authored document
  (headed Markdown sections, no delimiter) is a document, not
  an entry list, and the adapter refuses entry edits against it
  with a named error pointing at the section-scoped corpus
  write door, rather than silently normalising authored bytes.
  ``add`` is exempt: it is append-only and preserves every
  prior byte exactly.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from .memory_corpus import (
    ENTRY_DELIMITER,
    HOT_CAPS,
    MEMORY_TARGETS,
    MemoryCorpus,
    parse_entries,
)

__all__ = ["MemoryAdapter"]


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    data = text.encode("utf-8")
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


class MemoryAdapter:
    """Stock-shaped memory operations over the unbounded corpus."""

    def __init__(self, corpus: MemoryCorpus) -> None:
        self.corpus = corpus

    # -- file model -------------------------------------------------

    def _read(self, target: str) -> tuple[str, list[str], bool]:
        path = self.corpus.target_path(target)
        text = path.read_bytes().decode("utf-8") if path.exists() else ""
        entries = parse_entries(text)
        round_trips = ENTRY_DELIMITER.join(entries) == text.strip() \
            if text.strip() else text == ""
        # A file of headed Markdown sections with no stock entry
        # delimiter is a free-form authored DOCUMENT, not an entry
        # list: it trivially "round-trips" as one giant entry, and
        # treating it as one would let an entry edit rewrite the
        # whole document. Entry-model files either carry the
        # delimiter or carry no heading structure at all.
        has_headings = any(
            line.startswith(("# ", "## ", "### "))
            for line in text.splitlines())
        entry_model = round_trips and (
            ENTRY_DELIMITER in text or not has_headings)
        return text, entries, entry_model

    def _hot_chars(self, entries: list[str]) -> int:
        return len(ENTRY_DELIMITER.join(entries))

    def _status_block(self, target: str, entries: list[str]) -> dict[str, Any]:
        block = self.corpus.status_block()
        block = dict(block)
        block["target"] = target
        block["hot_chars"] = self._hot_chars(entries)
        block["hot_cap_chars"] = HOT_CAPS[target]
        return block

    def _reingest(self, target: str) -> None:
        self.corpus.library.ingest(MEMORY_TARGETS[target][0],
                                   MEMORY_TARGETS[target][1])
        self.corpus.index.sync()

    def _persist_entries(self, target: str, entries: list[str]) -> None:
        path = self.corpus.target_path(target)
        _atomic_write_text(path, ENTRY_DELIMITER.join(entries))
        self._reingest(target)

    def _require_entry_model(self, target: str, text: str,
                             round_trips: bool) -> dict[str, Any] | None:
        if round_trips:
            return None
        return {"success": False, "error": (
            f"{target} is a free-form authored document and does "
            "not round-trip through the stock entry model; an "
            "entry edit would silently normalise authored bytes. "
            "Use the section-scoped corpus write "
            "(replace_section_text) instead."),
            "failure_class": "not_entry_model",
            "memory_status": self.corpus.status_block()}

    def _locate(self, entries: list[str], old_text: str,
                matched_entry: str | None) -> int | dict[str, Any]:
        if matched_entry is not None:
            if matched_entry in entries:
                return entries.index(matched_entry)
            return {"success": False, "error": (
                "stale_entry: the entry this write was staged "
                "against is no longer present; nothing applied."),
                "failure_class": "stale_entry"}
        needle = (old_text or "").strip()
        matches = [i for i, e in enumerate(entries) if needle in e]
        exact = [i for i, e in enumerate(entries) if e == needle]
        if exact:
            return exact[0]
        if len(matches) > 1:
            return {"success": False, "error": (
                f"Multiple entries matched '{needle}'. "
                "Be more specific."), "failure_class": "ambiguous"}
        if not matches:
            return {"success": False, "error": (
                f"No entry matched '{needle}'."),
                "failure_class": "no_match"}
        return matches[0]

    def _result(self, target: str, entries: list[str], *,
                landed_in: str, message: str,
                extra: dict[str, Any] | None = None) -> dict[str, Any]:
        hot = self._hot_chars(entries)
        out: dict[str, Any] = {
            "success": True, "target": target, "message": message,
            "landed_in": landed_in,
            "in_full_store": True,
            "in_hot_view": hot <= HOT_CAPS[target],
            "memory_status": self._status_block(target, entries)}
        if extra:
            out.update(extra)
        return out

    # -- stock-shaped operations ------------------------------------

    def add(self, target: str, content: str) -> dict[str, Any]:
        text = (content or "").strip()
        if not text:
            return {"success": False,
                    "error": "Content cannot be empty.",
                    "failure_class": "missing_content"}
        _raw, entries, round_trips = self._read(target)
        if text in entries:
            return self._result(target, entries, landed_in="hot_and_full",
                                message="Entry already exists "
                                        "(no duplicate added).")
        prospective = entries + [text]
        if self._hot_chars(prospective) <= HOT_CAPS[target] \
                and round_trips:
            self._persist_entries(target, prospective)
            return self._result(target, prospective,
                                landed_in="hot_and_full",
                                message="Entry added.")
        # Overflow (or a free-form authored file): the write
        # succeeds in the FULL store, append-only, prior bytes
        # preserved exactly, and the result says so plainly.
        info = self.corpus.append_entry(target, text)
        _raw2, entries2, _rt2 = self._read(target)
        reason = ("hot view cap would be exceeded" if round_trips
                  else "target is a free-form authored document")
        return self._result(
            target, entries2, landed_in="full_store",
            message=(
                f"Entry saved to the full store only: {reason} "
                f"({self._hot_chars(prospective):,} chars against "
                f"the {HOT_CAPS[target]:,}-char hot cap). It is "
                "complete and exactly recallable from the full "
                "store; it is NOT in the hot view."),
            extra={"full_store": info})

    def replace(self, target: str, old_text: str, new_content: str,
                matched_entry: str | None = None) -> dict[str, Any]:
        new_text = (new_content or "").strip()
        if not (old_text or "").strip():
            return {"success": False,
                    "error": "old_text cannot be empty.",
                    "failure_class": "missing_old_text"}
        if not new_text:
            return {"success": False, "error": (
                "new_content cannot be empty. Use 'remove' to "
                "delete entries."), "failure_class": "missing_content"}
        raw, entries, round_trips = self._read(target)
        refusal = self._require_entry_model(target, raw, round_trips)
        if refusal is not None:
            return refusal
        located = self._locate(entries, old_text, matched_entry)
        if isinstance(located, dict):
            located["memory_status"] = self._status_block(target, entries)
            return located
        replaced = entries[:located] + [new_text] + entries[located + 1:]
        self._persist_entries(target, replaced)
        landed = "hot_and_full" if self._hot_chars(replaced) \
            <= HOT_CAPS[target] else "full_store"
        return self._result(
            target, replaced, landed_in=landed,
            message="Entry replaced.",
            extra={"replaced_entry": entries[located]})

    def patch(self, target: str, old_text: str, new_text: str,
              matched_entry: str | None = None) -> dict[str, Any]:
        if not (old_text or "").strip():
            return {"success": False,
                    "error": "old_text cannot be empty.",
                    "failure_class": "missing_old_text"}
        if new_text is None or not str(new_text).strip():
            return {"success": False, "error": (
                "new_text cannot be empty. Use remove/replace "
                "to drop text."), "failure_class": "missing_content"}
        raw, entries, round_trips = self._read(target)
        refusal = self._require_entry_model(target, raw, round_trips)
        if refusal is not None:
            return refusal
        located = self._locate(entries, old_text, matched_entry)
        if isinstance(located, dict):
            located["memory_status"] = self._status_block(target, entries)
            return located
        before = entries[located]
        if before.count(old_text) != 1:
            return {"success": False, "error": (
                "patch span must occur exactly once in the matched "
                "entry."), "failure_class": "ambiguous_span",
                "memory_status": self._status_block(target, entries)}
        after = before.replace(old_text, str(new_text), 1)
        patched = entries[:located] + [after] + entries[located + 1:]
        self._persist_entries(target, patched)
        landed = "hot_and_full" if self._hot_chars(patched) \
            <= HOT_CAPS[target] else "full_store"
        return self._result(
            target, patched, landed_in=landed,
            message="Entry patched.",
            extra={"patched_entry_before": before,
                   "patched_entry_after": after})

    def remove(self, target: str, old_text: str,
               matched_entry: str | None = None) -> dict[str, Any]:
        if not (old_text or "").strip():
            return {"success": False,
                    "error": "old_text cannot be empty.",
                    "failure_class": "missing_old_text"}
        raw, entries, round_trips = self._read(target)
        refusal = self._require_entry_model(target, raw, round_trips)
        if refusal is not None:
            return refusal
        located = self._locate(entries, old_text, matched_entry)
        if isinstance(located, dict):
            located["memory_status"] = self._status_block(target, entries)
            return located
        removed = entries[located]
        remaining = entries[:located] + entries[located + 1:]
        self._persist_entries(target, remaining)
        return self._result(
            target, remaining, landed_in="hot_and_full",
            message="Entry removed.", extra={"removed_entry": removed})

    # -- truthful status (the adapter's standing report) ------------

    def status(self, target: str | None = None) -> dict[str, Any]:
        block = self.corpus.status_block()
        if target is not None:
            _raw, entries, _rt = self._read(target)
            return self._status_block(target, entries)
        return block

    def source_sha256(self, target: str) -> str:
        path = self.corpus.target_path(target)
        if not path.exists():
            return hashlib.sha256(b"").hexdigest()
        return hashlib.sha256(path.read_bytes()).hexdigest()
