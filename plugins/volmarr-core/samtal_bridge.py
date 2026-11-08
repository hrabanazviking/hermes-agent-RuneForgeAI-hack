"""N3 Samtal bridge contract + Samkoma candidate flow (W10).

Roadmap section 22 (Phase N3) defines a Samtal-native bridge:
agents join a hall AS AGENTS with individual identities distinct
from the human account owner, send/receive with cursors, recover
missed messages after disconnect, and never leak closed-room
content outward; Samkoma joins as reviewable extraction -- input
receipt, candidate, evidence, operator approval, published event
(section 43: never auto-publish an unapproved event). Acceptance
(section 22): impersonation, duplicate delivery, missing-cursor
recovery, private-to-public leak prevention and unapproved
planning proposals are all covered by tests.

This slice is CONTRACT LEVEL with an injected transport, built on
the W09 capability bus policy. Honest stage, stated plainly:

- NO live Samtal connection is attempted or claimed: no
  credentials exist for this slice, Samtal's own auth/encryption
  stays the security boundary, and the transport here is an
  interface plus an in-memory fake used by the tests. Wiring a
  real Samtal transport is a recorded remainder.
- Sending resolves through the capability policy (the send
  action needs explicit approval; privacy travel rules refuse a
  private-class payload addressed to a public room BY NAME).
- Samkoma publishing is a guarded state machine on records: an
  unapproved candidate can never reach the published state, and
  publishing is idempotent, so a retried agent cannot post the
  same event twice (section 43).
"""

from __future__ import annotations

from typing import Any, Protocol

from .capability_bus import authorize

SCHEMA = "runeforge.samtal-bridge.v1"
SAMKOMA_SCHEMA = "runeforge.samkoma-flow.v1"

SAMTAL_DESCRIPTOR = {
    "schema": "runeforge.capability.v1",
    "service": "volmarr-samtal-bridge",
    "version": "0.26.0",
    "owner": "volmarr",
    "actions": ["read", "send"],
    "transport": "authenticated-remote",
    "auth": "scoped",
    "side_effects": True,
    "privacy_classes": ["public", "shared", "local-private"],
    "availability": "contract-implemented",
    "timeout_ms": 2000,
}

SAMKOMA_DESCRIPTOR = {
    "schema": "runeforge.capability.v1",
    "service": "volmarr-samkoma",
    "version": "0.26.0",
    "owner": "volmarr",
    "actions": ["read", "propose", "publish"],
    "transport": "in-process",
    "auth": "scoped",
    "side_effects": True,
    "privacy_classes": ["public", "shared", "local-private"],
    "availability": "contract-implemented",
    "timeout_ms": 2000,
}

# Room scope -> capability-bus destination vocabulary.
ROOM_DESTINATIONS = {"public": "public", "private": "shared", "local": "local"}


class SamtalError(Exception):
    """Named, honest bridge / Samkoma failure."""

    def __init__(self, name: str, detail: str) -> None:
        super().__init__(detail)
        self.name = name
        self.detail = detail


class Transport(Protocol):
    """Injected Samtal transport. A real adapter implements this
    against Samtal's own authenticated API; nothing in this module
    opens a network connection itself."""

    def send(self, envelope: dict[str, Any]) -> None: ...

    def fetch(self, after_cursor: int) -> list[dict[str, Any]]: ...


class InMemoryTransport:
    """Fake transport for contract tests (NOT a Samtal client).

    ``deliver`` plays the server: it stamps the next cursor onto
    an incoming-room envelope. ``inject`` places an envelope with
    an explicit cursor, for gap and redelivery scenarios.
    """

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self._room: list[dict[str, Any]] = []
        self._next_cursor = 1

    def send(self, envelope: dict[str, Any]) -> None:
        self.sent.append(dict(envelope))

    def deliver(self, envelope: dict[str, Any]) -> dict[str, Any]:
        stamped = dict(envelope)
        stamped["cursor"] = self._next_cursor
        self._next_cursor += 1
        self._room.append(stamped)
        return stamped

    def inject(self, envelope: dict[str, Any]) -> dict[str, Any]:
        stamped = dict(envelope)
        self._room.append(stamped)
        cursor = stamped.get("cursor")
        if isinstance(cursor, int) and cursor >= self._next_cursor:
            self._next_cursor = cursor + 1
        return stamped

    def fetch(self, after_cursor: int) -> list[dict[str, Any]]:
        rows = [dict(e) for e in self._room
                if isinstance(e.get("cursor"), int)
                and e["cursor"] > after_cursor]
        return sorted(rows, key=lambda e: e["cursor"])


def validate_identity(identity: Any) -> dict[str, Any]:
    """An agent identity must exist and differ from its human
    owner: an agent is a participant, never the account owner."""
    if not isinstance(identity, dict):
        raise SamtalError("validation_failure", "identity_not_an_object")
    agent_id = identity.get("agent_id")
    human_id = identity.get("human_owner_id")
    if not isinstance(agent_id, str) or not agent_id.strip():
        raise SamtalError("validation_failure", "agent_id_empty")
    if not isinstance(human_id, str) or not human_id.strip():
        raise SamtalError("validation_failure", "human_owner_id_empty")
    if agent_id == human_id:
        raise SamtalError(
            "validation_failure", "identity_agent_equals_human_owner")
    return identity


class SamtalBridge:
    """One agent's bridge seat: identity, cursors, dedupe."""

    def __init__(self, identity: dict[str, Any], transport: Transport) -> None:
        self.identity = validate_identity(identity)
        self.transport = transport
        self._cursor = 0
        self._seen: set[str] = set()
        self.inbox: list[dict[str, Any]] = []
        self.duplicates_suppressed = 0
        self.refusals: list[str] = []

    @property
    def cursor(self) -> int:
        return self._cursor

    @property
    def agent_id(self) -> str:
        return self.identity["agent_id"]

    def send_message(
        self,
        *,
        message_id: str,
        room_id: str,
        room_scope: str,
        body: str,
        privacy_class: str = "public",
        sender_id: str | None = None,
        approved: bool = False,
        sent_at: str = "",
    ) -> dict[str, Any]:
        sender = sender_id if sender_id is not None else self.agent_id
        if sender == self.identity["human_owner_id"]:
            raise SamtalError(
                "unauthorized",
                "impersonation_refused:human_owner_identity",
            )
        if sender != self.agent_id:
            raise SamtalError(
                "unauthorized",
                f"impersonation_refused:sender_not_agent_identity:{sender}",
            )
        if room_scope not in ROOM_DESTINATIONS:
            raise SamtalError(
                "validation_failure", f"room_scope_unknown:{room_scope}")
        if not message_id or not str(message_id).strip():
            raise SamtalError("validation_failure", "message_id_required")
        decision = authorize(
            SAMTAL_DESCRIPTOR,
            caller=self.agent_id,
            action="send",
            data_owner=self.agent_id,
            data_class=privacy_class,
            destination=ROOM_DESTINATIONS[room_scope],
            approved=approved,
        )
        if not decision["allowed"]:
            raise SamtalError("unauthorized", "; ".join(decision["reasons"]))
        envelope = {
            "schema": SCHEMA,
            "message_id": message_id,
            "room_id": room_id,
            "room_scope": room_scope,
            "sender_id": sender,
            "sender_kind": "agent",
            "body": body,
            "privacy_class": privacy_class,
            "sent_at": sent_at,
            "provenance": {
                "service": SAMTAL_DESCRIPTOR["service"],
                "agent_id": self.agent_id,
                "human_owner_id": self.identity["human_owner_id"],
            },
        }
        self.transport.send(envelope)
        return envelope

    def poll(self) -> list[dict[str, Any]]:
        """Accept new room messages after the current cursor.

        Duplicates (same message_id) are suppressed, never
        delivered twice; a cursor gap refuses by name and leaves
        the cursor at the last good message, so a later poll can
        recover the missing range -- no gaps, no dupes.
        """
        accepted: list[dict[str, Any]] = []
        for envelope in self.transport.fetch(self._cursor):
            cursor = envelope.get("cursor")
            if not isinstance(cursor, int) or isinstance(cursor, bool):
                self.refusals.append("envelope_cursor_missing")
                continue
            if cursor <= self._cursor:
                continue
            if cursor > self._cursor + 1:
                raise SamtalError(
                    "unavailable",
                    f"cursor_gap:expected {self._cursor + 1} got {cursor}",
                )
            message_id = envelope.get("message_id")
            if not message_id:
                self.refusals.append("envelope_message_id_missing")
                self._cursor = cursor
                continue
            if message_id in self._seen:
                self.duplicates_suppressed += 1
                self._cursor = cursor
                continue
            if (
                envelope.get("sender_kind") == "agent"
                and envelope.get("sender_id")
                == self.identity["human_owner_id"]
            ):
                self.refusals.append(
                    "impersonation_refused:incoming_agent_claims_human_id:"
                    f"{message_id}")
                self._seen.add(message_id)
                self._cursor = cursor
                continue
            self._seen.add(message_id)
            self.inbox.append(envelope)
            accepted.append(envelope)
            self._cursor = cursor
        return accepted

    def recover(self) -> dict[str, Any]:
        """Missing-cursor recovery: replay from the start of the
        room through the transport and rebuild the inbox. Replay
        passes through the same message-id dedupe, so recovery
        yields exactly the room's messages -- no gaps, no dupes.
        """
        self._cursor = 0
        self._seen = set()
        self.inbox = []
        self.duplicates_suppressed = 0
        accepted = self.poll()
        return {
            "schema": SCHEMA,
            "recovered": len(accepted),
            "cursor": self._cursor,
            "duplicates_suppressed": self.duplicates_suppressed,
        }

    def status(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "service": SAMTAL_DESCRIPTOR["service"],
            "availability": SAMTAL_DESCRIPTOR["availability"],
            "agent_id": self.agent_id,
            "human_owner_id": self.identity["human_owner_id"],
            "cursor": self._cursor,
            "inbox_count": len(self.inbox),
            "duplicates_suppressed": self.duplicates_suppressed,
            "refusals": list(self.refusals),
        }


class SamkomaPipeline:
    """Samkoma flow: receipt, candidate, evidence, operator
    approval, published event -- guarded at every transition.

    An unapproved candidate can NEVER reach the published state:
    publish is only reachable from the approved state, approval
    is only reachable with evidence attached, and publishing is
    idempotent per candidate (one candidate, one event).
    """

    FLOW = ("received", "candidate", "evidence", "approved", "published")

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}
        self._events: dict[str, dict[str, Any]] = {}

    def create_receipt(
        self, *, candidate_id: str, source_ref: str, summary: str,
        recorded_at: str,
    ) -> dict[str, Any]:
        if not candidate_id or not candidate_id.strip():
            raise SamtalError("validation_failure", "candidate_id_required")
        if not source_ref or not source_ref.strip():
            raise SamtalError("validation_failure", "source_ref_required")
        existing = self._records.get(candidate_id)
        if existing is not None:
            return existing
        record = {
            "schema": SAMKOMA_SCHEMA,
            "candidate_id": candidate_id,
            "status": "received",
            "receipt": {
                "source_ref": source_ref,
                "summary": summary,
                "recorded_at": recorded_at,
            },
            "candidate": None,
            "evidence": [],
            "approval": None,
        }
        self._records[candidate_id] = record
        return record

    def _require(self, candidate_id: str) -> dict[str, Any]:
        record = self._records.get(candidate_id)
        if record is None:
            raise SamtalError("unavailable", f"candidate_unknown:{candidate_id}")
        return record

    def _guard(self, record: dict[str, Any], allowed: tuple[str, ...],
               target: str) -> None:
        if record["status"] not in allowed:
            raise SamtalError(
                "validation_failure",
                f"transition_refused:{record['status']}->{target}",
            )

    def draft_candidate(
        self, candidate_id: str, *, title: str, detail: str = "",
    ) -> dict[str, Any]:
        record = self._require(candidate_id)
        self._guard(record, ("received",), "candidate")
        if not title or not title.strip():
            raise SamtalError("validation_failure", "candidate_title_required")
        record["candidate"] = {"title": title, "detail": detail}
        record["status"] = "candidate"
        return record

    def attach_evidence(
        self, candidate_id: str, *, evidence_ref: str, recorded_at: str,
    ) -> dict[str, Any]:
        record = self._require(candidate_id)
        self._guard(record, ("candidate", "evidence"), "evidence")
        if not evidence_ref or not evidence_ref.strip():
            raise SamtalError("validation_failure", "evidence_ref_required")
        record["evidence"].append(
            {"ref": evidence_ref, "recorded_at": recorded_at})
        record["status"] = "evidence"
        return record

    def approve(
        self, candidate_id: str, *, operator: str, approved: bool,
        recorded_at: str,
    ) -> dict[str, Any]:
        record = self._require(candidate_id)
        self._guard(record, ("evidence",), "approved")
        if not operator or not operator.strip():
            raise SamtalError("validation_failure", "operator_required")
        if not approved:
            raise SamtalError("unauthorized", "approval_not_granted")
        record["approval"] = {
            "operator": operator, "approved": True,
            "recorded_at": recorded_at,
        }
        record["status"] = "approved"
        return record

    def publish(
        self, candidate_id: str, *, recorded_at: str,
    ) -> dict[str, Any]:
        record = self._require(candidate_id)
        existing = self._events.get(candidate_id)
        if existing is not None:
            return existing
        if record["status"] != "approved":
            raise SamtalError(
                "validation_failure",
                "transition_refused:unapproved_cannot_publish:"
                f"{record['status']}->published",
            )
        event = {
            "schema": SAMKOMA_SCHEMA,
            "event_id": f"event-{candidate_id}",
            "candidate_id": candidate_id,
            "title": record["candidate"]["title"],
            "evidence": list(record["evidence"]),
            "approval": dict(record["approval"]),
            "receipt": dict(record["receipt"]),
            "published_at": recorded_at,
        }
        self._events[candidate_id] = event
        record["status"] = "published"
        return event

    def get(self, candidate_id: str) -> dict[str, Any] | None:
        return self._records.get(candidate_id)

    def status(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for record in self._records.values():
            counts[record["status"]] = counts.get(record["status"], 0) + 1
        return {
            "schema": SAMKOMA_SCHEMA,
            "service": SAMKOMA_DESCRIPTOR["service"],
            "availability": SAMKOMA_DESCRIPTOR["availability"],
            "flow": list(self.FLOW),
            "counts": counts,
            "published_events": len(self._events),
        }
