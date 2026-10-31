"""Opt-in bounded episodic retrieval from the attached OpenViking server.

Gate 0 audit (2026-10-30, catalog-pinned official source — see
``PERSISTENT_ENTITY_ACCEPTANCE_AUDIT.md`` / campaign Slice 84): verdict
CONDITIONAL PASS for ``POST /api/v1/search/find`` only. That route is
session-free (no session load, no intent analysis) and its call chain
contains no corpus writes; ``/search`` and the deprecated ``/recall``
are stateful and are never used here. Two disclosed conditions bind
this bridge:

- The server's own usage-audit store records search calls by default.
  That is server-owned accounting (the same the official provider's
  prefetch already triggers), not a corpus mutation — but it is a real
  server-side write, so the bridge stays opt-in, default off.
- Credential-free retrieval exists only when the server's ``/health``
  reports ``auth_mode == "dev"``; api_key/trusted modes require a key
  even on localhost, and this attachment never carries credentials.
  The bridge therefore fails closed unless health attests dev mode.

The server also embeds the query with its own configured embedder,
whose locality health cannot attest; opt-in enablement is the
operator's attestation. Only the current user message (capped) is
sent — never history, never a session id.
"""

from __future__ import annotations

import hashlib
import json
import math
import urllib.error
import urllib.request
from typing import Any

from .context_packet import ContextItem
from .openviking import _bounded_timeout, _open_local, probe_openviking


_MAX_QUERY_CHARS = 2_000
_MAX_CONTENT_CHARS = 800
_MAX_RESULTS = 5
_MAX_RESPONSE_BYTES = 1024 * 1024


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


class OpenVikingRetrievalBridge:
    """Produce ``relevant_episodes`` packet items from OpenViking memories."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx

    def packet_items(
        self,
        session_id: str,
        user_message: Any = "",
    ) -> list[ContextItem]:
        if not _as_bool(
            self._ctx.get_config("openviking_retrieval_enabled", False), False
        ):
            return []
        query = user_message.strip() if isinstance(user_message, str) else ""
        if not query:
            return []
        query = query[:_MAX_QUERY_CHARS]
        health = probe_openviking(self._ctx)
        if not health.healthy:
            return []
        # Credential-free retrieval exists only in dev auth mode; fail
        # closed (and never send the query) in every other mode.
        if health.auth_mode != "dev":
            return []
        timeout = _bounded_timeout(
            self._ctx.get_config("openviking_probe_timeout_ms", 2_000)
        )
        payload = self._find(health.base_url, query=query, timeout=timeout)
        if not isinstance(payload, dict):
            return []
        if payload.get("status") not in (None, "ok"):
            return []
        result = payload.get("result")
        if not isinstance(result, dict):
            return []
        memories = result.get("memories")
        if not isinstance(memories, list):
            return []
        items: list[ContextItem] = []
        for hit in memories[:_MAX_RESULTS]:
            if not isinstance(hit, dict):
                continue
            content_raw = hit.get("content")
            if not (isinstance(content_raw, str) and content_raw.strip()):
                content_raw = hit.get("abstract")
            if not isinstance(content_raw, str) or not content_raw.strip():
                continue
            content = content_raw.strip()
            if len(content) > _MAX_CONTENT_CHARS:
                content = content[: _MAX_CONTENT_CHARS - 1].rstrip() + "…"
            uri = hit.get("uri")
            if isinstance(uri, str) and uri.strip():
                record_id = uri.strip()
            else:
                record_id = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
            score = hit.get("score")
            if (
                isinstance(score, (int, float))
                and not isinstance(score, bool)
                and math.isfinite(score)
                and 0.0 <= score <= 1.0
            ):
                priority = float(score)
            else:
                priority = 0.5
            items.append(
                ContextItem(
                    section="relevant_episodes",
                    content=content,
                    source="openviking/memories",
                    record_id=record_id,
                    priority=priority,
                )
            )
        return items

    @staticmethod
    def _find(base_url: str, *, query: str, timeout: float):
        """POST the audited ``/find`` body; fail open on any failure."""
        body = json.dumps(
            {
                "query": query,
                "limit": _MAX_RESULTS,
                "context_type": "memory",
                "read_content": True,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{base_url}/api/v1/search/find",
            data=body,
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "runeforgeai-hermes-openviking-retrieval/1",
            },
        )
        try:
            with _open_local(request, timeout) as response:
                if response.status != 200:
                    return None
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
            if len(raw) > _MAX_RESPONSE_BYTES:
                return None
            payload = json.loads(raw.decode("utf-8"))
        except (urllib.error.URLError, OSError, UnicodeDecodeError, ValueError):
            return None
        except Exception:
            return None
        return payload if isinstance(payload, dict) else None
