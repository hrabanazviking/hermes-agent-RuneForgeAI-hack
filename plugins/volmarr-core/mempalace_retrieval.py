"""Opt-in bounded episodic retrieval from the attached MemPalace store.

Gate 0 audit (2026-10-30, official mempalace 3.11.0 — see
``PERSISTENT_ENTITY_ACCEPTANCE_AUDIT.md`` / campaign Slice 83): the
official ``mempalace.searcher.search_memories`` vector path opens the
palace through ChromaDB's ``PersistentClient``, and that open mutates
``chroma.sqlite3`` on every call (measured: bytes changed on consecutive
searches, plus one-time migration marker files). It is therefore NOT
read-only-safe and must never run from a per-turn hook. The same
function's ``vector_disabled=True`` route is the official sqlite-only
BM25 fallback: it reads ``chroma.sqlite3`` directly through a read-only
sqlite connection, never opens a Chroma client, and was measured
byte-for-byte non-mutating on a populated palace while returning the
correct verbatim drawer. This bridge uses only that route. Retrieval is
lexical (exact-word BM25), not semantic — that is the honest scope of
the read-only-safe surface today.
"""

from __future__ import annotations

import hashlib
import importlib
import math
import threading
from typing import Any

from .context_packet import ContextItem
from .mempalace import probe_mempalace


_MAX_QUERY_CHARS = 2_000
_MAX_CONTENT_CHARS = 800
_MAX_RESULTS = 5
_DEFAULT_TIMEOUT_SECONDS = 5


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "yes", "on", "1"}:
            return True
        if normalized in {"false", "no", "off", "0", ""}:
            return False
    return default


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return min(maximum, max(minimum, parsed))


class MemPalaceRetrievalBridge:
    """Produce ``relevant_episodes`` packet items from the local palace."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx

    def packet_items(
        self,
        session_id: str,
        user_message: Any = "",
    ) -> list[ContextItem]:
        if not _as_bool(
            self._ctx.get_config("mempalace_retrieval_enabled", False), False
        ):
            return []
        query = user_message.strip() if isinstance(user_message, str) else ""
        if not query:
            return []
        query = query[:_MAX_QUERY_CHARS]
        health = probe_mempalace(self._ctx)
        if not health.healthy:
            return []
        try:
            searcher = importlib.import_module("mempalace.searcher")
            search_memories = searcher.search_memories
        except Exception:
            return []
        timeout = _bounded_int(
            self._ctx.get_config("mempalace_retrieval_timeout_seconds", _DEFAULT_TIMEOUT_SECONDS),
            _DEFAULT_TIMEOUT_SECONDS,
            1,
            30,
        )
        payload = self._search(
            search_memories,
            query=query,
            palace_path=health.palace_path,
            collection_name=health.collection_name,
            timeout=timeout,
        )
        if not isinstance(payload, dict):
            return []
        results = payload.get("results")
        if not isinstance(results, list):
            return []
        items: list[ContextItem] = []
        for hit in results[:_MAX_RESULTS]:
            if not isinstance(hit, dict):
                continue
            text = hit.get("text")
            if not isinstance(text, str) or not text.strip():
                continue
            content = text.strip()
            if len(content) > _MAX_CONTENT_CHARS:
                content = content[: _MAX_CONTENT_CHARS - 1].rstrip() + "…"
            drawer_id = hit.get("drawer_id")
            if isinstance(drawer_id, str) and drawer_id.strip():
                record_id = drawer_id.strip()
            else:
                record_id = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
            similarity = hit.get("similarity")
            if (
                isinstance(similarity, (int, float))
                and not isinstance(similarity, bool)
                and math.isfinite(similarity)
                and 0.0 <= similarity <= 1.0
            ):
                priority = float(similarity)
            else:
                priority = 0.5
            items.append(
                ContextItem(
                    section="relevant_episodes",
                    content=content,
                    source="mempalace/drawers",
                    record_id=record_id,
                    priority=priority,
                )
            )
        return items

    @staticmethod
    def _search(search_memories, *, query, palace_path, collection_name, timeout):
        """Run the read-only BM25 search under a bounded wait; fail open.

        The query runs on a daemon thread because the official search has
        no timeout parameter; on timeout the turn proceeds without
        episodes and the orphaned read-only query finishes on its own.
        """
        box: dict[str, Any] = {}

        def _run() -> None:
            try:
                box["payload"] = search_memories(
                    query=query,
                    palace_path=palace_path,
                    n_results=_MAX_RESULTS,
                    collection_name=collection_name,
                    vector_disabled=True,
                )
            except Exception:
                box["payload"] = None

        worker = threading.Thread(target=_run, daemon=True)
        worker.start()
        worker.join(timeout)
        if worker.is_alive():
            return None
        return box.get("payload")
