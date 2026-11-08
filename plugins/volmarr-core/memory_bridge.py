"""Live packet integration for the memory corpus (W06 / M5).

Design: docs/modernization/P5_DESIGN_DRAFT.md sections 3.3, 4.5
and 5 (slice M5), tickets P.014 (turn-path half), P.017 (memory
continuity across turns) and P.018 (private/public filter before
cloud inference).

``PresentStateBridge`` remains the sole prompt owner and sole
``pre_llm_call`` assembler (the W05 ruling, consumed here exactly
as the draft orders): this bridge is ONE more packet source in
its tuple, never a second owner. It registers no hooks of its
own (``hooks()`` returns ``()``).

Behaviour:

- Fully opt-in: ``memory_corpus_enabled`` (default false) gates
  everything; a disabled profile gets ``[]`` and zero filesystem
  work on the turn path, so stock behaviour is byte-identical.
- With a user message, the source is W04 retrieval over the
  corpus, served as verbatim cited section text under the
  PresentState packet's own budget (the packet builder bounds
  the turn; storage is never bounded). Each item names its
  stable id and source hash -- provenance travels with content.
- With no user message, and only when the digest is separately
  enabled (``memory_corpus_digest_enabled``), the source is the
  derived hot digest (verbatim entries, generation-checked: a
  stale digest is rebuilt before it is served, never served
  stale under a current label).
- Generation-snapshot discipline (draft 3.3, mirroring W05): the
  corpus generation is captured BEFORE any read for the turn;
  every item of the turn names that generation, and a mid-turn
  write activates on the NEXT turn, never mid-turn.
- P.018 egress: local by default and receipts record
  ``cloud_egress: 0``. Only when the operator enables
  ``memory_corpus_cloud_egress_enabled`` AND the turn is marked
  cloud-bound (``destination="cloud"``) does retrieval take the
  corpus's cloud path, which refuses private-classified sources
  before egress and names the refusals on the receipt.
- Fail-open, never turn-blocking: any corpus/index problem
  yields ``[]`` for the turn and is recorded on ``last_receipt``;
  the one live turn path is never destabilised by memory.
"""

from __future__ import annotations

import logging
from typing import Any

from .context_packet import ContextItem

logger = logging.getLogger(__name__)

__all__ = ["MemoryBridge"]

_MAX_ITEMS = 5
_MAX_ITEM_CHARS = 4000


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().casefold()
        if lowered in {"true", "yes", "on", "1"}:
            return True
        if lowered in {"false", "no", "off", "0", ""}:
            return False
    return default


class MemoryBridge:
    """PresentState packet source for the unbounded memory corpus."""

    def __init__(self, ctx, *, corpus_factory=None) -> None:
        self._ctx = ctx
        self._corpus_factory = corpus_factory
        self._corpus = None
        self.last_receipt: dict[str, Any] | None = None

    def hooks(self):
        return ()

    # -- configuration -------------------------------------------------

    def enabled(self) -> bool:
        return _as_bool(
            self._ctx.get_config("memory_corpus_enabled", False), False)

    def _digest_enabled(self) -> bool:
        return _as_bool(self._ctx.get_config(
            "memory_corpus_digest_enabled", False), False)

    def _cloud_egress_enabled(self) -> bool:
        return _as_bool(self._ctx.get_config(
            "memory_corpus_cloud_egress_enabled", False), False)

    def _get_corpus(self):
        if self._corpus is None:
            if self._corpus_factory is not None:
                self._corpus = self._corpus_factory(self._ctx)
            else:
                from .memory_corpus import corpus_from_plugin_context
                self._corpus = corpus_from_plugin_context(self._ctx)
        return self._corpus

    # -- packet source ---------------------------------------------------

    def packet_items(self, session_id: str,
                     user_message: Any = "",
                     destination: str = "local") -> list[ContextItem]:
        if not self.enabled():
            return []
        message = user_message.strip() \
            if isinstance(user_message, str) else ""
        try:
            corpus = self._get_corpus()
            # Generation snapshot captured before any read (M5).
            generation = corpus.library.store.load()["generation"]
            if generation == 0:
                self.last_receipt = {
                    "kind": "memory_bridge", "session_id": session_id,
                    "outcome": "empty_corpus", "generation": 0,
                    "cloud_egress": 0, "items": []}
                return []
            cloud = destination == "cloud" \
                and self._cloud_egress_enabled()
            if message:
                items, detail = self._retrieval_items(
                    corpus, message, generation,
                    "cloud" if cloud else "local")
            elif self._digest_enabled():
                items, detail = self._digest_items(corpus, generation)
            else:
                items, detail = [], {"mode": "no_query_no_digest"}
            self.last_receipt = {
                "kind": "memory_bridge", "session_id": session_id,
                "outcome": "served" if items else "no_items",
                "generation": generation,
                "destination": "cloud" if cloud else "local",
                "cloud_egress": detail.get("cloud_egress", 0),
                "privacy_refused": detail.get("privacy_refused", []),
                "items": [item.record_id for item in items]}
            return items
        except Exception as exc:  # fail open; never block the turn
            logger.warning("memory_bridge: %s", type(exc).__name__)
            self.last_receipt = {
                "kind": "memory_bridge", "session_id": session_id,
                "outcome": "error", "error_type": type(exc).__name__,
                "cloud_egress": 0, "items": []}
            return []

    def _retrieval_items(self, corpus, message: str, generation: int,
                         destination: str):
        status = corpus.index_status()
        if status["status"] == "outdated" or status["status"] == "unbuilt":
            corpus.sync_index()
        found = corpus.retrieve(message, limit=_MAX_ITEMS,
                                destination=destination)
        items: list[ContextItem] = []
        for row in found["results"][:_MAX_ITEMS]:
            text = str(row.get("text") or "")
            if not text.strip():
                continue
            content = (
                f"[{row['stable_id']} | role={row.get('role', '')} | "
                f"source_sha256={row.get('source_sha256', '')} | "
                f"corpus_generation={generation}] {text}")
            if len(content) > _MAX_ITEM_CHARS:
                # Packet-scale bounding only: the item names its
                # continuation through the corpus read path; the
                # full store itself is never truncated.
                content = content[:_MAX_ITEM_CHARS]
            score = row.get("score") or {}
            total = score.get("total") if isinstance(score, dict) else None
            priority = float(total) if isinstance(total, (int, float)) \
                else float(row.get("priority") or 0.5)
            items.append(ContextItem(
                section="durable_knowledge", content=content,
                source="volmarr-memory/full-store",
                record_id=str(row["stable_id"]), priority=priority))
        receipt = found.get("receipt") or {}
        detail = {"mode": "retrieval",
                  "cloud_egress": receipt.get("cloud_egress", 0),
                  "privacy_refused": receipt.get("privacy_refused", [])}
        return items, detail

    def _digest_items(self, corpus, generation: int):
        from . import memory_digest

        digest = memory_digest.load_digest(corpus)
        state = memory_digest.digest_status(corpus, digest)
        if digest is None or state["state"] == "stale":
            digest = memory_digest.build_digest(corpus)
            memory_digest.save_digest(corpus, digest)
        items: list[ContextItem] = []
        for entry in (digest.get("entries") or [])[:_MAX_ITEMS]:
            text = str(entry.get("text") or "")
            if not text.strip():
                continue
            content = (
                f"[{entry['stable_id']} | role={entry.get('role', '')} | "
                f"source_sha256={entry.get('source_sha256', '')} | "
                f"digest_of_generation={generation}] {text}")
            if len(content) > _MAX_ITEM_CHARS:
                content = content[:_MAX_ITEM_CHARS]
            items.append(ContextItem(
                section="durable_knowledge", content=content,
                source="volmarr-memory/hot-digest",
                record_id=str(entry["stable_id"]), priority=0.6))
        return items, {"mode": "digest", "cloud_egress": 0}
