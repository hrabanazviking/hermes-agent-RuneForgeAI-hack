"""Live persona wiring: kernel + per-turn pipeline (W05, P3/P4).

Implements roadmap tickets P.008, P.009, P.010, P.011 and the
P.017 live substrate per docs/modernization/P3P4_DESIGN_DRAFT.md.
Plugin-side only: no Hermes core file is touched.

Two channels, one owner (draft section 3):

- Channel S (stable, per-session): exactly one system-prompt
  section, id ``volmarr.persona.kernel`` at the only legal
  position ``after_memory``, rendered from the compiled kernel
  of the ACTIVE generation. Frozen-per-session semantics are
  the core's own; a new generation refreshes this channel at
  the core's rebuild boundaries, never mid-turn.
- Channel T (per-turn, dynamic): ``PresentStateBridge`` stays
  the sole ``pre_llm_call`` persona assembler. This module's
  ``packet_items`` replaces the old descriptive
  ``PersonaRuntimeBridge.packet_items`` as the persona source
  in the composition tuple: instead of a prose description of
  the contract system it emits REAL content — a bounded kernel
  echo, routed + retrieved persona sections verbatim (stable-id
  named, source-hash provenanced, P.008), and a section 37
  persona-state line — produced by giving the banked pure
  surfaces their first live callers: the section 20 reloader,
  the section 14 router, the section 13 retriever and the
  section 15 budgeter, all over ONE immutable per-turn
  generation snapshot (draft section 5).

Everything is opt-in per profile via ``persona_live_owner``
(default off = stock Hermes behaviour, byte-for-byte, including
the legacy SOUL path). P.010: while persona-live owns the
prompt, a still-loaded legacy SOUL.md would double-inject the
persona, so ownership REFUSES (fail loud, stock fallback)
unless the operator attests the supported core suppression
was applied (``persona_live_legacy_soul_disabled``); the spike
behind that choice is recorded in the W05 implementation
record. Delegated child sessions receive fragments only
(section 36, draft section 7). Per-turn receipts (P.011) are
operator-only and never enter tool results or messages.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from hermes_constants import get_hermes_home
from utils import atomic_json_write

from .context_packet import ContextItem
from .persona_runtime import (
    PersonaCompiler,
    PersonaReloader,
    PersonaRuntimeError,
    anchor_block,
    budget_items,
    context_classes,
    kernel_tier_target,
    kernel_tiers,
    persona_state,
    retrieve_sections,
    route_mode,
    route_sections,
)

try:
    import fcntl
except ImportError:  # pragma: no cover - platform branch
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover - platform branch
    msvcrt = None


logger = logging.getLogger(__name__)

SECTION_ID = "volmarr.persona.kernel"
SECTION_POSITION = "after_memory"
SECTION_MAX_CHARS = 4_000
# Core wraps a rendered section in a ``## Plugin Context: <id>``
# heading; keep the body inside the per-section cap with margin.
SECTION_BODY_BUDGET = 3_900

RECEIPT_SCHEMA = "runeforge.persona-live-receipt"
RECEIPT_VERSION = 1
RECEIPT_STORE_VERSION = 1
DEFAULT_RECEIPT_PATH = Path("memory") / "persona_live_receipts.json"
MAX_RECEIPTS = 256

KERNEL_SOURCE = "persona_live/kernel"
RETRIEVAL_SOURCE = "persona_live/retrieval"
STATE_SOURCE = "persona_live/state"
FRAGMENT_SOURCE = "persona_live/fragment"

# Channel T kernel-echo tier per section 15 context class: the
# frozen Channel S section carries the fullest kernel the cap
# allows; the per-turn echo is packet-scale by design.
_ECHO_TIER_BY_CLASS = {
    "small_local": "kernel_micro",
    "standard": "kernel_medium",
    "large": "kernel_full",
}

_AUTHORITY_CEILINGS = ("read_only", "task_bounded", "full")


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off", ""}:
            return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    return default


@dataclass(frozen=True)
class PersonaGeneration:
    """One immutable published generation (draft section 5).

    The compiled artefact is stored privately and handed out
    only as a deep copy, so no caller can mutate the snapshot
    a turn captured.
    """

    number: int
    kernel_hash: str
    persona_hash: str
    persona_id: str
    activated_at: float
    _compiled: dict[str, Any] = field(repr=False, compare=False)

    def compiled(self) -> dict[str, Any]:
        return copy.deepcopy(self._compiled)


class PersonaLiveState:
    """Active-generation holder with atomic next-turn activation.

    Reload checks (section 20, first live caller) run at turn
    start BEFORE the turn captures its generation reference; a
    validated new compile is published by a single reference
    swap under a lock, so it takes effect from the NEXT
    admitted turn — never mid-turn. A failed validation keeps
    the last known-good generation and records the error.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._compiler = PersonaCompiler(ctx)
        self._reloader = PersonaReloader(ctx)
        self._lock = threading.RLock()
        self._generation: PersonaGeneration | None = None
        self._next_number = 1
        self.last_error: str | None = None

    def current(self) -> PersonaGeneration | None:
        with self._lock:
            return self._generation

    def ensure(self) -> PersonaGeneration | None:
        """Build the first generation if none is published."""
        with self._lock:
            if self._generation is not None:
                return self._generation
            try:
                compiled = self._compiler.compile()
            except (PersonaRuntimeError, OSError) as exc:
                self.last_error = f"{type(exc).__name__}: compile refused"
                logger.warning("persona_live: initial compile failed (%s)",
                               type(exc).__name__)
                return None
            if compiled is None:
                return None
            return self._publish(compiled)

    def refresh(self) -> PersonaGeneration | None:
        """Turn-start reload check; publish on validated change."""
        with self._lock:
            current = self._generation
            if current is None:
                return self.ensure()
            try:
                result = self._reloader.check(current._compiled)
            except (PersonaRuntimeError, OSError) as exc:
                # Last known-good is retained (draft section 5).
                self.last_error = f"{type(exc).__name__}: reload refused"
                logger.warning(
                    "persona_live: reload check failed, keeping "
                    "generation %d (%s)", current.number,
                    type(exc).__name__)
                return current
            if not result.get("changed"):
                return current
            fresh = result.get("compiled")
            if fresh is None:
                # Persona config removed: ownership lapses to
                # stock behaviour rather than serving a ghost.
                self._generation = None
                self.last_error = None
                return None
            return self._publish(fresh)

    def _publish(self, compiled: dict[str, Any]) -> PersonaGeneration:
        kernel = compiled.get("kernel") or {}
        generation = PersonaGeneration(
            number=self._next_number,
            kernel_hash=str(kernel.get("sha256") or ""),
            persona_hash=str(compiled.get("persona_hash") or ""),
            persona_id=str(compiled.get("persona_id") or ""),
            activated_at=time.time(),
            _compiled=copy.deepcopy(compiled),
        )
        self._next_number += 1
        self._generation = generation
        self.last_error = None
        return generation


class _ReceiptStore:
    """Bounded operator-only receipt log beside the turn capture.

    Same path discipline as PresentStateStore: the path is
    resolved on every operation and may not escape the active
    profile home. Receipts carry hashes, ids and budget numbers
    only — never persona text.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx

    def _path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(
            "persona_live_receipt_path", str(DEFAULT_RECEIPT_PATH))))
        if configured.is_absolute():
            return configured.resolve()
        resolved = (home / configured).resolve()
        if not resolved.is_relative_to(home):
            return home / DEFAULT_RECEIPT_PATH
        return resolved

    @contextmanager
    def _locked(self, *, write: bool):
        path = self._path()
        lock_path = path.with_suffix(path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+b") as lock:
            lock.seek(0, os.SEEK_END)
            if lock.tell() == 0:
                lock.write(b"\0")
                lock.flush()
            lock.seek(0)
            if fcntl is not None:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            elif msvcrt is not None:
                msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield path
            finally:
                lock.seek(0)
                if fcntl is not None:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                elif msvcrt is not None:
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)

    def _read_unlocked(self, path: Path) -> dict[str, Any]:
        if not path.is_file() or path.is_symlink():
            return {"schema_version": RECEIPT_STORE_VERSION, "receipts": []}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {"schema_version": RECEIPT_STORE_VERSION, "receipts": []}
        if not isinstance(data, dict) \
                or data.get("schema_version") != RECEIPT_STORE_VERSION \
                or not isinstance(data.get("receipts"), list):
            return {"schema_version": RECEIPT_STORE_VERSION, "receipts": []}
        return data

    def append(self, receipt: dict[str, Any]) -> None:
        with self._locked(write=True) as path:
            data = self._read_unlocked(path)
            receipts = data["receipts"]
            receipts.append(receipt)
            data["receipts"] = receipts[-MAX_RECEIPTS:]
            atomic_json_write(
                path, data, indent=2, sort_keys=True,
                ensure_ascii=False, mode=0o600)

    def read_all(self) -> list[dict[str, Any]]:
        with self._locked(write=False) as path:
            return list(self._read_unlocked(path)["receipts"])


def _index_by_stable_id(compiled: Mapping[str, Any]) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for entry in compiled.get("index") or []:
        if isinstance(entry, dict) and entry.get("stable_id"):
            rows[str(entry["stable_id"])] = entry
    return rows


def _document_hashes(compiled: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(doc.get("role")): str(doc.get("sha256") or "")
        for doc in compiled.get("documents") or []
        if isinstance(doc, dict) and doc.get("role")
    }


def kernel_text_for_tier(
    compiled: Mapping[str, Any], tier: str
) -> tuple[str, list[str], list[str]]:
    """Whole-section kernel text for one section 64 tier.

    Returns ``(text, included_stable_ids, excluded_stable_ids)``.
    The anchor block stands first, verbatim, and is never
    evicted; sections are taken whole, in kernel order, under
    the tier's token target. Sections are taken in kernel
    order (section 16's protection is honoured by that order:
    the kernel compiler emits P0 first, so P0 sections are the
    last a tier ever drops, and section 16's never-evict rule
    governs the packet budgeter, which expires retrieved
    context before ever touching the kernel category). A tier
    target is nevertheless a hard bound for the tier's text:
    sections that do not fit are excluded whole and reported
    through the excluded list, never silently dropped.
    Nothing is ever head/tail-truncated.
    """
    kernel = compiled.get("kernel") or {}
    if tier == "kernel_full":
        return (
            str(kernel.get("text") or ""),
            [str(sid) for sid in kernel.get("stable_ids") or []],
            [],
        )
    target = kernel_tier_target(tier)
    by_id = _index_by_stable_id(compiled)
    anchor_text = anchor_block(
        list(kernel.get("anchors") or []),
        list(kernel.get("anti_anchors") or []))
    total = 0
    if anchor_text:
        # The compiler counts anchors inside the kernel total;
        # approximate their share from the full text delta is
        # unreliable, so count the block's own words the same
        # way section estimates are carried: via index-free
        # character estimate below in the caller-visible ids.
        total = max(1, len(anchor_text) // 4)
    included: list[str] = []
    excluded: list[str] = []
    blocks: list[str] = [anchor_text] if anchor_text else []
    for stable_id in [str(s) for s in kernel.get("stable_ids") or []]:
        entry = by_id.get(stable_id)
        if entry is None:
            excluded.append(stable_id)
            continue
        tokens = entry.get("estimated_tokens")
        tokens = int(tokens) if isinstance(tokens, int) else 0
        if included and total + tokens > target:
            excluded.append(stable_id)
            continue
        included.append(stable_id)
        blocks.append(str(entry.get("text") or ""))
        total += tokens
    return "\n\n".join(block for block in blocks if block), included, excluded


class PersonaLiveBridge:
    """The W05 live persona owner: Channel S + Channel T source."""

    def __init__(self, ctx, *, turn_signals: dict | None = None) -> None:
        self._ctx = ctx
        self._state = PersonaLiveState(ctx)
        self._receipts = _ReceiptStore(ctx)
        # Shared mutable holder PresentStateBridge fills with the
        # current turn's hook kwargs before sources run (P.009:
        # PresentState remains the assembler; this is its signal
        # channel to the persona source it owns).
        self._turn_signals = turn_signals if turn_signals is not None else {}
        self._fragments: dict[str, dict[str, Any]] = {}
        self._fragment_lock = threading.Lock()
        self.last_receipt: dict[str, Any] | None = None
        self.registration_problem: str | None = None

    # -- configuration -------------------------------------------------

    def enabled(self) -> bool:
        return _as_bool(
            self._ctx.get_config("persona_live_owner", False), False)

    def _context_class(self) -> str:
        value = self._ctx.get_config("persona_live_context_class", "standard")
        return value if value in context_classes() else "standard"

    def _configured_tier(self) -> str | None:
        value = self._ctx.get_config("persona_live_kernel_tier", "auto")
        return value if value in kernel_tiers() else None

    def legacy_soul_present(self) -> bool:
        try:
            return (get_hermes_home() / "SOUL.md").is_file()
        except OSError:
            return False

    def _soul_suppression_attested(self) -> bool:
        return _as_bool(self._ctx.get_config(
            "persona_live_legacy_soul_disabled", False), False)

    def ownership_problem(self) -> str | None:
        """P.010 fail-loud check (draft section 4, option 2).

        Persona-live ownership with the legacy SOUL block still
        loaded would inject the persona twice. Until the
        operator applies a supported core suppression and
        attests it, ownership is refused and every channel
        falls back to stock Hermes behaviour.
        """
        if not self.enabled():
            return None
        if self.legacy_soul_present() \
                and not self._soul_suppression_attested():
            return (
                "persona_live_owner is set but the legacy SOUL.md "
                "block is still loaded for this profile and no "
                "supported suppression is attested "
                "(persona_live_legacy_soul_disabled); refusing "
                "persona-live ownership rather than double-"
                "injecting the persona (P.010)")
        return None

    # -- Channel S ------------------------------------------------------

    def register(self, ctx) -> None:
        """Register the one Channel S section (fail-open)."""
        if not self.enabled():
            return
        problem = self.ownership_problem()
        if problem is not None:
            self.registration_problem = problem
            logger.warning("persona_live: %s", problem)
            return
        try:
            ctx.register_system_prompt_section(
                SECTION_ID,
                self.render_kernel_section,
                position=SECTION_POSITION,
                max_chars=SECTION_MAX_CHARS,
            )
        except Exception as exc:  # plugin load must never break
            self.registration_problem = (
                f"channel S registration failed: {type(exc).__name__}")
            logger.warning("persona_live: %s", self.registration_problem)

    def render_kernel_section(self, session_info: Any = None) -> str:
        """Channel S body: the active generation's kernel.

        Rendered once per session and frozen by core. Returns
        an empty string (section skipped by core) whenever the
        plugin does not own this profile's prompt.
        """
        if not self.enabled() or self.ownership_problem() is not None:
            return ""
        generation = self._state.ensure()
        if generation is None:
            return ""
        compiled = generation.compiled()
        text, _included, _excluded, _tier = self._channel_s_text(compiled)
        return text

    def _channel_s_text(
        self, compiled: Mapping[str, Any]
    ) -> tuple[str, list[str], list[str], str]:
        configured = self._configured_tier()
        if configured is not None:
            text, included, excluded = kernel_text_for_tier(
                compiled, configured)
            return text, included, excluded, configured
        for tier in kernel_tiers():
            text, included, excluded = kernel_text_for_tier(compiled, tier)
            if len(text) <= SECTION_BODY_BUDGET:
                return text, included, excluded, tier
        text, included, excluded = kernel_text_for_tier(
            compiled, "kernel_micro")
        return text, included, excluded, "kernel_micro"

    # -- Channel T ------------------------------------------------------

    def packet_items(
        self, session_id: str, user_message: Any = ""
    ) -> list[ContextItem]:
        """The persona source for PresentState's per-turn packet.

        Replaces the retired descriptive PersonaRuntimeBridge
        item (draft section 3.3): no turn ever receives both.
        """
        if not self.enabled():
            return []
        message = user_message if isinstance(user_message, str) else ""
        signals = dict(self._turn_signals)
        problem = self.ownership_problem()
        if problem is not None:
            self._record_receipt(
                session_id=session_id, signals=signals, generation=None,
                kind="refused", problem=problem, included=[], excluded=[],
                budget=None, tier=None)
            return []
        generation = self._state.refresh()
        if generation is None:
            self._record_receipt(
                session_id=session_id, signals=signals, generation=None,
                kind="no_persona", problem=self._state.last_error,
                included=[], excluded=[], budget=None, tier=None)
            return []
        parent_session_id = str(signals.get("parent_session_id") or "")
        if parent_session_id:
            return self._delegate_items(
                session_id, generation, signals)
        return self._pipeline_items(session_id, message, generation, signals)

    def _pipeline_items(
        self,
        session_id: str,
        message: str,
        generation: PersonaGeneration,
        signals: dict[str, Any],
    ) -> list[ContextItem]:
        compiled = generation.compiled()
        by_id = _index_by_stable_id(compiled)
        doc_hashes = _document_hashes(compiled)
        context_class = self._context_class()
        kernel = compiled.get("kernel") or {}

        # Stage 2 (section 14 router — first live caller).
        route = route_sections(
            compiled.get("index") or [], user_message=message)
        # Stage 3 (section 13 retriever — first live caller).
        retrieved = retrieve_sections(
            compiled.get("index") or [], query=message, limit=5)

        # Kernel echo at packet scale (Channel S carries the
        # frozen fullest form; see module docstring).
        echo_tier = self._configured_tier() or _ECHO_TIER_BY_CLASS[
            context_class]
        echo_text, echo_included, echo_excluded = kernel_text_for_tier(
            compiled, echo_tier)
        kernel_level = "P0" if any(
            (by_id.get(sid) or {}).get("priority_level") == "P0"
            for sid in kernel.get("stable_ids") or []) else "P1"

        # Stage 4 (section 15 budgeter — first live caller).
        budget_input: list[dict[str, Any]] = [{
            "id": "persona_kernel",
            "category": "persona_kernel",
            "estimated_tokens": int(kernel.get("estimated_tokens") or 0),
            "priority": 0.90, "score": 0.90,
            "priority_level": kernel_level,
        }]
        seen_ids = {"persona_kernel"}
        for row in retrieved:
            stable_id = str(row.get("stable_id") or "")
            entry = by_id.get(stable_id)
            if entry is None or stable_id in seen_ids:
                continue
            seen_ids.add(stable_id)
            score = row.get("score")
            budget_input.append({
                "id": stable_id,
                "category": "persona_retrieval",
                "estimated_tokens": int(entry.get("estimated_tokens") or 0),
                "priority": float(entry.get("priority") or 0.0),
                "score": float(score.get("total", 0.0))
                if isinstance(score, dict) else 0.0,
                "priority_level": entry.get("priority_level"),
            })
        try:
            budget = budget_items(budget_input, context_class=context_class)
        except PersonaRuntimeError:
            budget = None
        if budget is not None:
            included_ids = {
                str(row["id"]) for row in budget.get("included") or []}
            excluded_rows = [
                {"id": str(row.get("id")), "reason": str(row.get("reason"))}
                for row in budget.get("excluded") or []]
        else:
            included_ids = seen_ids
            excluded_rows = []

        items: list[ContextItem] = []
        emitted: list[str] = []
        if "persona_kernel" in included_ids and echo_text:
            items.append(ContextItem(
                section="current_state",
                content=(
                    f"Persona kernel (generation {generation.number}, "
                    f"tier {echo_tier}, sha256 {generation.kernel_hash}): "
                    f"{echo_text}"),
                source=KERNEL_SOURCE,
                record_id=f"kernel:{generation.kernel_hash[:16]}",
                priority=0.95,
            ))
            emitted.append("persona_kernel")
        for row in retrieved:
            stable_id = str(row.get("stable_id") or "")
            if stable_id not in included_ids:
                continue
            entry = by_id.get(stable_id) or {}
            role = str(entry.get("role") or row.get("role") or "")
            items.append(ContextItem(
                section="current_state",
                content=(
                    f"[{stable_id} | role={role} | "
                    f"source_sha256={doc_hashes.get(role, '')}] "
                    f"{entry.get('text') or row.get('text') or ''}"),
                source=RETRIEVAL_SOURCE,
                record_id=stable_id,
                priority=float(entry.get("priority") or 0.0),
            ))
            emitted.append(stable_id)
        state_item = self._state_item(compiled, route, generation)
        if state_item is not None:
            items.append(state_item)
        self._record_receipt(
            session_id=session_id, signals=signals, generation=generation,
            kind="turn", problem=None,
            included=emitted + echo_included,
            excluded=excluded_rows + [
                {"id": sid, "reason": "over_tier_target"}
                for sid in echo_excluded],
            budget=budget, tier=echo_tier, route=route)
        return items

    def _state_item(
        self,
        compiled: Mapping[str, Any],
        route: Mapping[str, Any],
        generation: PersonaGeneration,
    ) -> ContextItem | None:
        """The section 37 state line (first live caller)."""
        task = str(route.get("task") or "general")
        try:
            mode = route_mode(task)["initial_mode"]
        except (PersonaRuntimeError, KeyError, TypeError):
            try:
                mode = route_mode("general")["initial_mode"]
            except (PersonaRuntimeError, KeyError, TypeError):
                mode = "companion"
        try:
            state = persona_state(
                compiled, mode,
                {"warmth": 0.5, "playfulness": 0.5, "focus": 0.5},
                {"trust": 0.5},
                "hermes", task or "general")["persona_state"]
        except (PersonaRuntimeError, KeyError, TypeError):
            return None
        content = (
            f"Persona state: {state['id']} v{state['version']}, "
            f"mode {state['active_mode']} (routed from this turn's "
            f"task signal), generation {generation.number}, kernel "
            f"sha256 {generation.kernel_hash[:12]}. Scored state "
            f"fields are neutral defaults — no live affect signal "
            f"is consumed by this layer.")
        return ContextItem(
            section="self_state",
            content=content,
            source=STATE_SOURCE,
            record_id=f"state:{generation.persona_id}:{generation.number}",
            priority=0.6,
        )

    # -- Delegate fragments (section 36) --------------------------------

    def delegate_fragment(
        self,
        persona_id: str,
        stable_ids: Any,
        authority_ceiling: str = "read_only",
    ) -> dict[str, Any]:
        """Build a bounded fragment packet for a child session.

        Named sections verbatim; the anchor block is never
        included wholesale, memory-role sections (private
        memory) and unknown ids are excluded with reasons, and
        no credentials exist in this layer to leak. The child's
        own identity stays primary — the fragment is delivered
        only through the child's own turn (see _delegate_items).
        """
        if authority_ceiling not in _AUTHORITY_CEILINGS:
            raise PersonaRuntimeError("authority ceiling is invalid")
        generation = self._state.ensure()
        if generation is None:
            raise PersonaRuntimeError("no active persona generation")
        if persona_id != generation.persona_id:
            raise PersonaRuntimeError("persona id does not match the "
                                      "active generation")
        compiled = generation.compiled()
        by_id = _index_by_stable_id(compiled)
        doc_hashes = _document_hashes(compiled)
        sections: list[dict[str, Any]] = []
        excluded: list[dict[str, str]] = []
        for raw in list(stable_ids or []):
            stable_id = str(raw)
            entry = by_id.get(stable_id)
            if entry is None:
                excluded.append({"id": stable_id, "reason": "not_found"})
                continue
            role = str(entry.get("role") or "")
            if role == "memory":
                excluded.append(
                    {"id": stable_id, "reason": "private_memory_role"})
                continue
            sections.append({
                "stable_id": stable_id,
                "role": role,
                "source_sha256": doc_hashes.get(role, ""),
                "text": str(entry.get("text") or ""),
            })
        return {
            "fragment_id": uuid4().hex[:16],
            "persona_id": generation.persona_id,
            "generation": generation.number,
            "kernel_hash": generation.kernel_hash,
            "authority_ceiling": authority_ceiling,
            "sections": sections,
            "excluded": excluded,
        }

    def attach_delegate(self, session_id: str, fragment: Mapping[str, Any]) -> None:
        with self._fragment_lock:
            self._fragments[str(session_id)] = copy.deepcopy(dict(fragment))

    def _delegate_items(
        self,
        session_id: str,
        generation: PersonaGeneration,
        signals: dict[str, Any],
    ) -> list[ContextItem]:
        with self._fragment_lock:
            fragment = self._fragments.get(str(session_id))
        if fragment is None:
            # A child with no fragment gets NO persona content:
            # its own identity is primary (section 36).
            self._record_receipt(
                session_id=session_id, signals=signals,
                generation=generation, kind="delegate_without_fragment",
                problem=None, included=[], excluded=[], budget=None,
                tier=None)
            return []
        items = [
            ContextItem(
                section="current_state",
                content=(
                    f"[{row['stable_id']} | role={row['role']} | "
                    f"source_sha256={row['source_sha256']}] {row['text']}"),
                source=FRAGMENT_SOURCE,
                record_id=str(row["stable_id"]),
                priority=0.5,
            )
            for row in fragment.get("sections") or []
        ]
        self._record_receipt(
            session_id=session_id, signals=signals, generation=generation,
            kind="delegate_fragment", problem=None,
            included=[str(r["stable_id"]) for r in fragment.get("sections") or []],
            excluded=list(fragment.get("excluded") or []),
            budget=None, tier=None)
        return items

    # -- Receipts (P.011) -------------------------------------------------

    def _record_receipt(
        self,
        *,
        session_id: str,
        signals: Mapping[str, Any],
        generation: PersonaGeneration | None,
        kind: str,
        problem: str | None,
        included: list,
        excluded: list,
        budget: Mapping[str, Any] | None,
        tier: str | None,
        route: Mapping[str, Any] | None = None,
    ) -> None:
        receipt: dict[str, Any] = {
            "schema": RECEIPT_SCHEMA,
            "version": RECEIPT_VERSION,
            "kind": kind,
            "recorded_at": time.time(),
            "session_id": str(session_id or ""),
            "turn_id": str(signals.get("turn_id") or ""),
            "generation": generation.number if generation else None,
            "persona_id": generation.persona_id if generation else None,
            "kernel_sha256": generation.kernel_hash if generation else None,
            "persona_hash": generation.persona_hash if generation else None,
            "model": str(signals.get("model") or ""),
            "platform": str(signals.get("platform") or ""),
            "context_class": self._context_class(),
            "channel_s_tier": tier,
            "legacy_soul_present": self.legacy_soul_present(),
            "problem": problem,
            "route_task": str(route.get("task") or "") if route else None,
            "route_tags": list(route.get("task_tags") or []) if route else [],
            "included": included,
            "excluded": excluded,
            "budget": (budget.get("categories") if budget else None),
        }
        receipt["receipt_id"] = hashlib.sha256(
            json.dumps(receipt, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
        self.last_receipt = receipt
        try:
            self._receipts.append(receipt)
        except Exception:  # receipts never break a turn
            logger.warning("persona_live: receipt write failed",
                           exc_info=True)

    def receipts(self) -> list[dict[str, Any]]:
        return self._receipts.read_all()


__all__ = [
    "KERNEL_SOURCE",
    "RECEIPT_SCHEMA",
    "RETRIEVAL_SOURCE",
    "SECTION_ID",
    "STATE_SOURCE",
    "FRAGMENT_SOURCE",
    "PersonaGeneration",
    "PersonaLiveBridge",
    "PersonaLiveState",
    "kernel_text_for_tier",
]
