"""SELF STATE context integration (Self-Aware Agency roadmap §13).

The central context packet carried five sections at schema v1.
§13 upgrades it to v2 with an explicit, bounded ``SELF STATE``
section between CURRENT STATE and RELEVANT EPISODES — the packet
builder now owns that section (``self_state``, limit 7, one item
per §13 field). What §13 does not want is a full self-model dump
in every prompt, so this module assembles only the seven compact,
high-value fields §13 names, deterministically and read-only,
from the stores that already own them:

- identity summary — the layered self-model's narrative summary
  (Slice 103), falling back to the objective entity id;
- current attention — the layered experiential attention target;
- active self-originated goal — the top-ranked live intrinsic
  goal under the Phase 9 arbitration (Slice 99), when the
  intrinsic-goal surface is enabled;
- major discrepancy — the first structured discrepancy of the
  layered snapshot, when one exists;
- confidence/uncertainty — the layered experiential uncertainty
  and its complement, as numbers, never as invented prose;
- relevant known limitation — the first known limitation of the
  layered snapshot, when one exists;
- current curiosity target — the top Phase 4 frontier question,
  when the curiosity surface is enabled and its frontier is
  non-empty.

Assembly is a pure function of the source stores: this module
writes nothing, owns no persistent file, and degrades per-field —
an unreadable optional source omits its field rather than
inventing content. The layered fields require the layered
self-model (Slice 103) to be enabled; without it assembly is
refused, because a SELF STATE section built from partial sources
would misrepresent itself as the §5 view.

Disabled by default.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .context_packet import ContextItem
from .curiosity import CuriosityError, CuriosityStore
from .identity import IdentityError, IdentityStore, _as_bool
from .intrinsic_goals import IntrinsicGoalError, IntrinsicGoalService
from .self_model_layers import LayeredSelfModelError, LayeredSelfModelService

MAX_FIELD_CHARS = 240

# The seven §13 fields, in the order they appear in the section.
SELF_STATE_FIELDS = (
    "identity_summary",
    "current_attention",
    "active_self_originated_goal",
    "major_discrepancy",
    "confidence_uncertainty",
    "known_limitation",
    "curiosity_target",
)

_FIELD_LABELS = {
    "identity_summary": "Identity",
    "current_attention": "Current focus",
    "active_self_originated_goal": "Active self-originated goal",
    "major_discrepancy": "Active discrepancy",
    "confidence_uncertainty": "Confidence",
    "known_limitation": "Known limitation",
    "curiosity_target": "Current curiosity",
}


class SelfStateError(RuntimeError):
    """The SELF STATE section cannot be safely assembled."""


def _epoch(value: str) -> float:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, OverflowError, OSError):
        return 0.0


def _bounded(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = " ".join(value.split()).strip()
    return text[:MAX_FIELD_CHARS]


class SelfStateService:
    """Assemble the compact §13 SELF STATE fields from existing stores."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("self_state_enabled", False), False
        )

    def assemble(self) -> dict[str, Any]:
        """The §13 fields present on this profile, in field order.

        Pure read: no source store is written. Optional fields are
        omitted when their source is disabled, empty, or unreadable.
        """
        if not self.enabled():
            raise SelfStateError("self state is disabled")
        layered = LayeredSelfModelService(self._ctx)
        if not layered.enabled():
            raise SelfStateError(
                "self state requires the layered self-model to be enabled")
        snapshot = layered.snapshot()
        fields: dict[str, str] = {}

        narrative = snapshot.get("narrative") or {}
        objective = snapshot.get("objective") or {}
        summary = _bounded(narrative.get("summary"))
        if not summary:
            summary = _bounded(
                f"persistent entity {objective.get('entity_id', '')} "
                f"on {objective.get('home_runtime', 'hermes')}")
        if summary:
            fields["identity_summary"] = summary

        experiential = snapshot.get("experiential") or {}
        attention = _bounded(experiential.get("attention"))
        if attention:
            fields["current_attention"] = attention

        intrinsic_title = self._intrinsic_goal_title()
        if intrinsic_title:
            fields["active_self_originated_goal"] = intrinsic_title

        discrepancies = snapshot.get("discrepancies") or []
        if discrepancies and isinstance(discrepancies[0], dict):
            detail = _bounded(discrepancies[0].get("detail"))
            if detail:
                fields["major_discrepancy"] = detail

        uncertainty = experiential.get("uncertainty")
        if isinstance(uncertainty, (int, float)) \
                and not isinstance(uncertainty, bool):
            value = min(1.0, max(0.0, float(uncertainty)))
            fields["confidence_uncertainty"] = (
                f"uncertainty {value:.2f}; confidence {1.0 - value:.2f}")

        limitations = snapshot.get("known_limitations") or []
        if limitations:
            limitation = _bounded(limitations[0])
            if limitation:
                fields["known_limitation"] = limitation

        curiosity = self._curiosity_target()
        if curiosity:
            fields["curiosity_target"] = curiosity

        return {
            "fields": fields,
            "generated_at": str(snapshot.get("generated_at") or ""),
            "owner_entity_id": str(snapshot.get("owner_entity_id") or ""),
        }

    # -- optional sources (disabled/empty/unreadable -> omitted) --------
    def _intrinsic_goal_title(self) -> str:
        try:
            service = IntrinsicGoalService(self._ctx)
            if not service.enabled():
                return ""
            for row in service.arbitrate():
                if row.get("origin") == "intrinsic":
                    return _bounded(row.get("title"))
        except (IdentityError, IntrinsicGoalError, OSError):
            return ""
        return ""

    def _curiosity_target(self) -> str:
        try:
            store = CuriosityStore(self._ctx)
            if not store.enabled():
                return ""
            frontier = store.frontier()
        except (IdentityError, CuriosityError, OSError):
            return ""
        if frontier:
            return _bounded(frontier[0].get("question"))
        return ""


class SelfStateBridge:
    """Surface the §13 fields as SELF STATE packet items.

    One item per present field, in §13 field order, never more
    than the seven the section allows. No hooks: assembly happens
    only when the packet builder asks.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._service = SelfStateService(ctx)

    def hooks(self):
        return ()

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not _as_bool(self._ctx.get_config("self_state_enabled", False), False):
            return []
        try:
            assembled = self._service.assemble()
        except (IdentityError, SelfStateError, LayeredSelfModelError, OSError):
            return []
        fields = assembled["fields"]
        updated_at = _epoch(assembled["generated_at"])
        items: list[ContextItem] = []
        for index, name in enumerate(SELF_STATE_FIELDS):
            value = fields.get(name)
            if not value:
                continue
            items.append(ContextItem(
                section="self_state",
                content=f"{_FIELD_LABELS[name]}: {value}",
                source="self_state",
                record_id=name,
                priority=1.0 - index * 0.05,
                updated_at=updated_at,
            ))
        return items


__all__ = [
    "SELF_STATE_FIELDS",
    "MAX_FIELD_CHARS",
    "SelfStateError",
    "SelfStateService",
    "SelfStateBridge",
]
