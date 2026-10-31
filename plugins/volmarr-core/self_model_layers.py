"""Five-layer persistent self-model (Self-Aware Agency roadmap §5).

The Emergent Agency Phase 1 store (`self_model.py`) keeps the entity's
durable claims. This module assembles the §5 five-layer view over that
store and its neighbouring ledgers — deterministically, read-only, and
on demand (no new persistent file, no resident process):

- **Objective self** — machine-verifiable facts only: the canonical
  entity id, the home runtime, the continuity heartbeat probe, goal
  and relationship counts, and the capability claims backed by strong
  evidence (explicit user correction, deterministic tool results,
  canonical identity/system state).
- **Narrative self** — the bounded autobiographical layer: the
  highest-confidence identity claim as summary, identity claims as
  milestones. Never raw transcript history.
- **Ideal self** — the developmental target: preference claims as
  traits, commitment claims as principles, limitation keys as the
  capabilities being built. The ideal layer is reported beside the
  objective layer; it never overwrites it.
- **Relational self** — summaries taken verbatim from the
  relationships ledger, which stays the authority for relationship
  state; nothing is invented that the ledger does not carry.
- **Experiential self** — the transient operating state: attention
  (the top active goal), load (blocked share of live goals),
  uncertainty (mean inverse confidence of uncertainty claims), and
  the active goal ids.

Cross-layer disagreement is made explicit rather than smoothed over:
claims carrying recorded contradictions, high-confidence capability
claims while the heartbeat is unhealthy, blocked goals with no next
action, and high experiential uncertainty each surface as a
structured discrepancy. Unreadable source ledgers degrade to an
empty layer plus a ``source_unreadable`` discrepancy — never to
invented content.

This module owns no writes: it never writes raw memories,
relationships, world state, affective state, or autonomy policy, and
it never writes the claims store either. Disabled by default.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .context_packet import ContextItem
from .goals import GoalError, GoalStore
from .heartbeat import probe_heartbeat
from .identity import IdentityError, IdentityStore, _as_bool
from .relationships import RelationshipError, RelationshipStore
from .self_model import SelfModelError, SelfModelStore, evidence_strength

LAYERS_VERSION = 1
LAYER_NAMES = ("objective", "narrative", "ideal", "relational", "experiential")
HOME_RUNTIME = "hermes"

_MAX_MILESTONES = 5
_MAX_RELATIONAL = 10
_MAX_LIMITATIONS = 10
_MAX_ASSUMPTIONS = 10
_MAX_CONTRADICTIONS = 10
_MAX_DISCREPANCIES = 10
_STRONG_CAPABILITY_FLOOR = 0.5
_HIGH_CONFIDENCE = 0.8
_HIGH_UNCERTAINTY = 0.7


class LayeredSelfModelError(RuntimeError):
    """The layered self-model cannot be safely assembled."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _epoch(value: str) -> float:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, OverflowError, OSError):
        return 0.0


class LayeredSelfModelService:
    """Assemble the §5 five-layer snapshot from the existing stores."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)
        self._claims = SelfModelStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("layered_self_model_enabled", False), False
        )

    @staticmethod
    def layers() -> tuple[str, ...]:
        return LAYER_NAMES

    def snapshot(self) -> dict[str, Any]:
        if not self.enabled():
            raise LayeredSelfModelError("layered self-model is disabled")
        owner = self._identity.read().entity_id
        discrepancies: list[dict[str, str]] = []

        records = self._claim_records(discrepancies)
        claims = [record["claim"] for record in records]
        by_domain: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            by_domain.setdefault(record["claim"].domain, []).append(record)

        heartbeat = probe_heartbeat(self._ctx)
        goals, goal_counts = self._goal_view(discrepancies)
        relationships = self._relationship_view(discrepancies)

        verified_capabilities = sorted(
            record["claim"].key
            for record in by_domain.get("capability", [])
            if evidence_strength(record["claim"].source.source_type) == "strong"
            and record["claim"].confidence >= _STRONG_CAPABILITY_FLOOR
        )
        objective = {
            "entity_id": owner,
            "home_runtime": HOME_RUNTIME,
            "heartbeat_status": heartbeat.status,
            "heartbeat_healthy": bool(heartbeat.healthy),
            "current_goal_count": sum(goal_counts.values()),
            "live_goal_count": sum(
                count
                for status, count in goal_counts.items()
                if status in {"planned", "active", "blocked"}
            ),
            "goal_counts": goal_counts,
            "relationship_count": len(relationships),
            "claim_count": len(claims),
            "verified_capabilities": verified_capabilities,
        }

        identity_claims = sorted(
            (record["claim"] for record in by_domain.get("identity", [])),
            key=lambda claim: (-claim.confidence, claim.key, claim.claim_id),
        )
        narrative = {
            "summary": identity_claims[0].statement if identity_claims else "",
            "milestones": [claim.statement for claim in identity_claims[:_MAX_MILESTONES]],
        }

        limitations = sorted(
            (record["claim"] for record in by_domain.get("limitation", [])),
            key=lambda claim: (-claim.confidence, claim.key, claim.claim_id),
        )
        growth_targets = [claim.key for claim in limitations]
        ideal = {
            "traits": [
                claim.statement
                for claim in sorted(
                    (r["claim"] for r in by_domain.get("preference", [])),
                    key=lambda c: (-c.confidence, c.key, c.claim_id),
                )
            ][:_MAX_MILESTONES],
            "capabilities": growth_targets,
            "principles": [
                claim.statement
                for claim in sorted(
                    (r["claim"] for r in by_domain.get("commitment", [])),
                    key=lambda c: (-c.confidence, c.key, c.claim_id),
                )
            ][:_MAX_MILESTONES],
        }

        relational = {"summaries": relationships}

        live_goals = [
            goal for goal in goals if goal["status"] in {"planned", "active", "blocked"}
        ]
        active_goals = sorted(
            (goal for goal in live_goals if goal["status"] == "active"),
            key=lambda goal: (goal["priority"], goal["created_at"], goal["goal_id"]),
        )
        blocked_goals = [goal for goal in live_goals if goal["status"] == "blocked"]
        uncertainty_claims = [r["claim"] for r in by_domain.get("uncertainty", [])]
        uncertainty = (
            round(
                sum(1.0 - claim.confidence for claim in uncertainty_claims)
                / len(uncertainty_claims),
                6,
            )
            if uncertainty_claims
            else 0.0
        )
        experiential = {
            "attention": active_goals[0]["title"] if active_goals else "",
            "load": (
                round(len(blocked_goals) / len(live_goals), 6) if live_goals else 0.0
            ),
            "uncertainty": uncertainty,
            "blocked": bool(blocked_goals),
            "active_goal_ids": [goal["goal_id"] for goal in active_goals],
        }

        known_limitations = [claim.statement for claim in limitations[:_MAX_LIMITATIONS]]
        active_assumptions = [
            {"domain": claim.domain, "key": claim.key, "confidence": claim.confidence}
            for claim in sorted(
                (c for c in claims if c.confidence < 0.5),
                key=lambda c: (c.confidence, c.domain, c.key, c.claim_id),
            )
        ][:_MAX_ASSUMPTIONS]
        unresolved_contradictions = []
        for record in records:
            contradictions = record["contradictions"]
            if not contradictions:
                continue
            claim = record["claim"]
            unresolved_contradictions.append(
                {
                    "domain": claim.domain,
                    "key": claim.key,
                    "statement": contradictions[-1]["statement"],
                    "count": len(contradictions),
                }
            )
            discrepancies.append(
                {
                    "kind": "contradicted_claim",
                    "detail": f"{claim.domain}/{claim.key} carries "
                    f"{len(contradictions)} recorded contradiction(s)",
                }
            )
        unresolved_contradictions = unresolved_contradictions[:_MAX_CONTRADICTIONS]

        if not heartbeat.healthy:
            for record in by_domain.get("capability", []):
                claim = record["claim"]
                if claim.confidence >= _HIGH_CONFIDENCE:
                    discrepancies.append(
                        {
                            "kind": "capability_claim_vs_health",
                            "detail": f"capability/{claim.key} confidence "
                            f"{claim.confidence:.2f} while heartbeat is "
                            f"{heartbeat.status}",
                        }
                    )
        for goal in blocked_goals:
            if not str(goal.get("next_action") or "").strip():
                discrepancies.append(
                    {
                        "kind": "blocked_goal_without_next_action",
                        "detail": f"goal {goal['goal_id']} is blocked with no next action",
                    }
                )
        if uncertainty >= _HIGH_UNCERTAINTY:
            discrepancies.append(
                {
                    "kind": "high_uncertainty",
                    "detail": f"experiential uncertainty is {uncertainty:.2f}",
                }
            )

        return {
            "layers_version": LAYERS_VERSION,
            "owner_entity_id": owner,
            "generated_at": _now(),
            "objective": objective,
            "narrative": narrative,
            "ideal": ideal,
            "relational": relational,
            "experiential": experiential,
            "known_limitations": known_limitations,
            "active_assumptions": active_assumptions,
            "unresolved_contradictions": unresolved_contradictions,
            "growth_targets": growth_targets,
            "discrepancies": discrepancies[:_MAX_DISCREPANCIES],
        }

    # -- source views (read-only; failures degrade, never invent) -------

    def _claim_records(
        self, discrepancies: list[dict[str, str]]
    ) -> list[dict[str, Any]]:
        try:
            return self._claims.records()
        except (IdentityError, SelfModelError, OSError):
            discrepancies.append(
                {"kind": "source_unreadable", "detail": "self-model claims store"}
            )
            return []

    def _goal_view(
        self, discrepancies: list[dict[str, str]]
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        try:
            data = GoalStore(self._ctx).get()
            goals = list(data["goals"].values())
        except (IdentityError, GoalError, OSError):
            discrepancies.append(
                {"kind": "source_unreadable", "detail": "goals ledger"}
            )
            return [], {}
        counts: dict[str, int] = {}
        for goal in goals:
            counts[goal["status"]] = counts.get(goal["status"], 0) + 1
        return goals, counts

    def _relationship_view(
        self, discrepancies: list[dict[str, str]]
    ) -> list[dict[str, Any]]:
        try:
            data = RelationshipStore(self._ctx).get()
            records = list(data["relationships"].values())
        except (IdentityError, RelationshipError, OSError):
            discrepancies.append(
                {"kind": "source_unreadable", "detail": "relationships ledger"}
            )
            return []
        records.sort(key=lambda r: (r["display_name"], r["entity_id"]))
        return [
            {
                "entity_id": record["entity_id"],
                "display_name": record["display_name"],
                "relationship_type": record["relationship_type"],
                "status": record["status"],
                "trust": float(record["trust"]),
            }
            for record in records[:_MAX_RELATIONAL]
        ]


class LayeredSelfModelBridge:
    """Surface one bounded layered-self-model packet item.

    Content-bearing only: disabled, unreadable, or a snapshot with no
    narrative, limitation, or discrepancy content contributes nothing.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._service = LayeredSelfModelService(ctx)

    def hooks(self):
        return ()

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not _as_bool(
            self._ctx.get_config("layered_self_model_enabled", False), False
        ):
            return []
        try:
            snapshot = self._service.snapshot()
        except (IdentityError, LayeredSelfModelError, OSError):
            return []
        parts: list[str] = []
        if snapshot["narrative"]["summary"]:
            parts.append(f"identity: {snapshot['narrative']['summary']}")
        if snapshot["known_limitations"]:
            parts.append(f"limitations: {len(snapshot['known_limitations'])} known")
        if snapshot["discrepancies"]:
            parts.append(f"discrepancies: {len(snapshot['discrepancies'])} unresolved")
        if not parts:
            return []
        return [
            ContextItem(
                section="current_state",
                content="Layered self-model — " + "; ".join(parts) + ".",
                source="self_model_layers",
                record_id=snapshot["owner_entity_id"],
                priority=0.4,
                updated_at=_epoch(snapshot["generated_at"]),
            )
        ]


__all__ = [
    "LAYERS_VERSION",
    "LAYER_NAMES",
    "HOME_RUNTIME",
    "LayeredSelfModelError",
    "LayeredSelfModelService",
    "LayeredSelfModelBridge",
]
