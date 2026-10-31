"""Durable intrinsic goals (Emergent Agency Phase 9, roadmap §16).

The motivation system's intent proposals (Phase 2) may now be
*promoted* into durable goals in the schema-v2 goal ledger — but only
through this service, and only within hard bounds:

- promotion is one explicit call (no hook, no turn-path caller);
- an intrinsic-goal quota caps how many live intrinsic goals exist;
- goal origin is preserved by the ledger itself (Phase 9 migration in
  ``goals.py``): promoted goals are ``origin="intrinsic"`` forever,
  with the proposing drive recorded as ``origin_ref``;
- priority arbitration is one deterministic function over tiers —
  explicit urgent user goals, explicit normal user goals, safety /
  continuity maintenance, approved intrinsic goals, then unapproved
  intrinsic goals — and the tier order is configurable
  (``intrinsic_goal_tier_order``, comma-separated tier names);
- a user may approve, archive, or reject an intrinsic goal (never a
  user goal through this surface). Rejection archives the goal and
  records its fingerprint in the ledger with a cooldown; while the
  cooldown runs, the same fingerprint — and any near-duplicate title
  (token Jaccard >= 0.8 against the rejected title) — is refused, so
  rejection cannot be evaded by rewording. An exact duplicate of an
  existing non-archived intrinsic goal returns that goal instead of
  creating a second record.

Nothing here executes actions, sends messages, or calls tools.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from .context_packet import ContextItem
from .goals import GoalError, GoalStore
from .identity import IdentityError, _as_bool

DEFAULT_QUOTA = 5
MAX_QUOTA = 50
DEFAULT_REJECTION_COOLDOWN_HOURS = 168.0  # one week
MAX_REJECTION_COOLDOWN_HOURS = 8760.0
NEAR_DUPLICATE_THRESHOLD = 0.8
LIVE_STATUSES = frozenset({"planned", "active", "blocked"})

TIER_USER_URGENT = "explicit_urgent_user"
TIER_USER_NORMAL = "explicit_normal_user"
TIER_MAINTENANCE = "safety_continuity"
TIER_INTRINSIC_APPROVED = "approved_intrinsic"
TIER_INTRINSIC_NEW = "new_intrinsic"
DEFAULT_TIER_ORDER = (
    TIER_USER_URGENT,
    TIER_USER_NORMAL,
    TIER_MAINTENANCE,
    TIER_INTRINSIC_APPROVED,
    TIER_INTRINSIC_NEW,
)


class IntrinsicGoalError(RuntimeError):
    """An intrinsic-goal promotion or user action was refused."""


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def normalize_goal_text(text: str) -> str:
    """Canonical text for fingerprints (case/space/punct-insensitive)."""
    folded = re.sub(r"\s+", " ", str(text).strip().casefold())
    return folded.strip(" .!?;:")


def goal_fingerprint(title: str, description: str = "") -> str:
    """Stable fingerprint of a goal's normalised title + description."""
    material = f"{normalize_goal_text(title)}\n{normalize_goal_text(description)}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def title_similarity(first: str, second: str) -> float:
    """Token-set Jaccard similarity of two normalised titles."""
    first_tokens = set(normalize_goal_text(first).split())
    second_tokens = set(normalize_goal_text(second).split())
    if not first_tokens or not second_tokens:
        return 0.0
    return len(first_tokens & second_tokens) / len(first_tokens | second_tokens)


def tier_of(goal: dict[str, Any]) -> str:
    origin = goal.get("origin", "user")
    if origin == "maintenance":
        return TIER_MAINTENANCE
    if origin == "intrinsic":
        return TIER_INTRINSIC_APPROVED if goal.get("approved") else TIER_INTRINSIC_NEW
    return TIER_USER_URGENT if goal.get("urgency") == "urgent" else TIER_USER_NORMAL


class IntrinsicGoalService:
    """Promotion, arbitration, and user control of intrinsic goals."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._goals = GoalStore(ctx)

    def enabled(self) -> bool:
        return self._goals.enabled() and _as_bool(
            self._ctx.get_config("intrinsic_goals_enabled", True), True
        )

    def _quota(self) -> int:
        try:
            value = int(self._ctx.get_config("intrinsic_goal_quota", DEFAULT_QUOTA))
        except (TypeError, ValueError):
            value = DEFAULT_QUOTA
        return min(MAX_QUOTA, max(0, value))

    def _cooldown_hours(self) -> float:
        try:
            value = float(
                self._ctx.get_config(
                    "intrinsic_goal_rejection_cooldown_hours",
                    DEFAULT_REJECTION_COOLDOWN_HOURS,
                )
            )
        except (TypeError, ValueError):
            value = DEFAULT_REJECTION_COOLDOWN_HOURS
        return min(MAX_REJECTION_COOLDOWN_HOURS, max(0.0, value))

    def tier_order(self) -> list[str]:
        """Configured tier order; unknown names dropped, missing appended."""
        raw = self._ctx.get_config("intrinsic_goal_tier_order", "")
        order: list[str] = []
        if isinstance(raw, str):
            for name in raw.split(","):
                name = name.strip()
                if name in DEFAULT_TIER_ORDER and name not in order:
                    order.append(name)
        elif isinstance(raw, (list, tuple)):
            for name in raw:
                if name in DEFAULT_TIER_ORDER and name not in order:
                    order.append(name)
        for name in DEFAULT_TIER_ORDER:
            if name not in order:
                order.append(name)
        return order

    # -- promotion ------------------------------------------------------
    def promote(
        self, proposal: dict[str, Any], *, now: datetime | None = None
    ) -> dict[str, Any]:
        """Promote one intent proposal into a durable intrinsic goal.

        Returns the created goal, or the existing intrinsic goal when
        the proposal is an exact duplicate of one. Raises
        ``IntrinsicGoalError`` for a rejected fingerprint still in
        cooldown, a near-duplicate of a rejected goal, a full quota,
        or a malformed proposal.
        """
        if not self.enabled():
            raise IntrinsicGoalError("intrinsic goals are disabled")
        if not isinstance(proposal, dict):
            raise IntrinsicGoalError("proposal must be a mapping")
        moment = now or _now_dt()
        title = proposal.get("title") or proposal.get("proposal") or ""
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > 200:
            raise IntrinsicGoalError("proposal title is missing or oversized")
        title = title.strip()
        description = proposal.get("description", "")
        if not isinstance(description, str) or len(description) > 4000:
            raise IntrinsicGoalError("proposal description is invalid")
        origin_ref = proposal.get("drive") or proposal.get("origin_ref") or ""
        if not isinstance(origin_ref, str) or len(origin_ref) > 200:
            raise IntrinsicGoalError("proposal origin reference is invalid")
        try:
            expected_value = float(proposal.get("expected_value", 0.5))
        except (TypeError, ValueError):
            expected_value = 0.5
        expected_value = min(1.0, max(0.0, expected_value))

        fingerprint = goal_fingerprint(title, description)
        rejected = self._goals.rejected_fingerprints()
        entry = rejected.get(fingerprint)
        if entry is not None and _parse(entry["cooldown_until"]) > moment:
            raise IntrinsicGoalError("goal fingerprint is in rejection cooldown")
        for other_fp, other in rejected.items():
            if other_fp == fingerprint:
                continue
            if _parse(other["cooldown_until"]) <= moment:
                continue
            if title_similarity(title, other["title"]) >= NEAR_DUPLICATE_THRESHOLD:
                raise IntrinsicGoalError(
                    "proposal is a near-duplicate of a rejected goal"
                )

        data = self._goals.get()
        live_intrinsic = 0
        for goal in data["goals"].values():
            if goal.get("origin") != "intrinsic":
                continue
            # Archived records do not block: rejection is governed by
            # its fingerprint cooldown, and an archived goal whose
            # cooldown has run out may be proposed again as a new goal.
            if (
                goal["status"] != "archived"
                and goal_fingerprint(goal["title"], goal.get("description", "")) == fingerprint
            ):
                return goal
            if goal["status"] in LIVE_STATUSES:
                live_intrinsic += 1
        if live_intrinsic >= self._quota():
            raise IntrinsicGoalError("intrinsic goal quota is full")

        # Intrinsic priorities stay in the lower half of the scale so
        # user goals normally outrank them even before tiers apply.
        priority = int(round(expected_value * 50))
        return self._goals.create(
            title=title,
            description=description,
            priority=priority,
            next_action="",
            origin="intrinsic",
            origin_ref=origin_ref,
            urgency="normal",
            approved=False,
        )

    # -- user control -----------------------------------------------------
    def _intrinsic_goal(self, goal_id: str) -> dict[str, Any]:
        goal = self._goals.get(goal_id)
        if goal.get("origin") != "intrinsic":
            raise IntrinsicGoalError("goal is not an intrinsic goal")
        return goal

    def approve(self, goal_id: str) -> dict[str, Any]:
        if not self.enabled():
            raise IntrinsicGoalError("intrinsic goals are disabled")
        self._intrinsic_goal(goal_id)
        return self._goals.update(
            goal_id, {"approved": True}, "Intrinsic goal approved by the user."
        )

    def archive(self, goal_id: str) -> dict[str, Any]:
        if not self.enabled():
            raise IntrinsicGoalError("intrinsic goals are disabled")
        self._intrinsic_goal(goal_id)
        return self._goals.update(
            goal_id, {"status": "archived"}, "Intrinsic goal archived by the user."
        )

    def reject(self, goal_id: str, *, now: datetime | None = None) -> dict[str, Any]:
        """Archive an intrinsic goal and cool its fingerprint down (§16)."""
        if not self.enabled():
            raise IntrinsicGoalError("intrinsic goals are disabled")
        moment = now or _now_dt()
        goal = self._intrinsic_goal(goal_id)
        fingerprint = goal_fingerprint(goal["title"], goal.get("description", ""))
        self._goals.note_rejection(
            fingerprint,
            title=goal["title"],
            rejected_at=_fmt(moment),
            cooldown_until=_fmt(moment + timedelta(hours=self._cooldown_hours())),
        )
        return self._goals.update(
            goal_id,
            {"status": "archived"},
            "Intrinsic goal rejected by the user; fingerprint in cooldown.",
        )

    # -- arbitration ------------------------------------------------------
    def arbitrate(self) -> list[dict[str, Any]]:
        """Live goals in deterministic priority order (§16).

        Tier first (configurable order), then priority descending,
        then creation time, then goal id — identical inputs always
        produce the identical ordering.
        """
        order = self.tier_order()
        rank = {name: index for index, name in enumerate(order)}
        data = self._goals.get()
        rows = []
        for goal in data["goals"].values():
            if goal["status"] not in LIVE_STATUSES:
                continue
            tier = tier_of(goal)
            rows.append({
                "goal_id": goal["goal_id"],
                "title": goal["title"],
                "status": goal["status"],
                "priority": goal["priority"],
                "origin": goal.get("origin", "user"),
                "urgency": goal.get("urgency", "normal"),
                "approved": bool(goal.get("approved", False)),
                "created_at": goal["created_at"],
                "tier": tier,
                "_sort": (rank[tier], -goal["priority"], goal["created_at"], goal["goal_id"]),
            })
        rows.sort(key=lambda row: row["_sort"])
        for row in rows:
            row.pop("_sort", None)
        return rows


class IntrinsicGoalBridge:
    """Ensure the v2 ledger at session start; offer its top intrinsic goal."""

    def __init__(self, ctx) -> None:
        self._service = IntrinsicGoalService(ctx)

    def hooks(self):
        return (("on_session_start", self.on_session_start),)

    def on_session_start(self, **_: Any) -> None:
        if not self._service.enabled():
            return
        try:
            self._service._goals.ensure()
        except (IdentityError, GoalError, OSError):
            return

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not self._service.enabled():
            return []
        try:
            rows = self._service.arbitrate()
        except (IdentityError, GoalError, OSError):
            return []
        for row in rows:
            if row["origin"] != "intrinsic":
                continue
            return [ContextItem(
                section="current_state",
                content=(
                    f"Intrinsic goal: {row['title']} "
                    f"(tier {row['tier']}; priority {row['priority']})"
                ),
                source="intrinsic_goals",
                record_id=row["goal_id"],
                priority=0.4,
                updated_at=_parse(row["created_at"]).timestamp(),
            )]
        return []


__all__ = [
    "DEFAULT_TIER_ORDER", "NEAR_DUPLICATE_THRESHOLD",
    "TIER_INTRINSIC_APPROVED", "TIER_INTRINSIC_NEW", "TIER_MAINTENANCE",
    "TIER_USER_NORMAL", "TIER_USER_URGENT",
    "IntrinsicGoalError", "IntrinsicGoalService", "IntrinsicGoalBridge",
    "goal_fingerprint", "normalize_goal_text", "title_similarity", "tier_of",
]
