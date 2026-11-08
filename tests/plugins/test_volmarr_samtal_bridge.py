"""W10/N3 Samtal bridge contract + Samkoma candidate flow.

Roadmap section 22 acceptance names five topics: agent identity
impersonation, duplicate delivery, missing-cursor recovery,
private-to-public leak prevention and unapproved planning
proposals. These contracts pin them against an injected fake
transport -- NO live Samtal connection exists in this slice and
none is claimed: the agent identity is distinct from the human
owner, sends resolve through the capability policy (approval +
privacy travel), receives are deduplicated by message id,
recovery replays from the last cursor with no gaps or dupes, and
the Samkoma pipeline (receipt, candidate, evidence, operator
approval, published event) refuses every unapproved path to the
published state and publishes idempotently.
"""

from __future__ import annotations

import importlib

import pytest

from hermes_constants import get_hermes_home


@pytest.fixture(scope="module")
def mods():
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [volmarr-core]\n", encoding="utf-8")
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-core"]
        pkg = loaded.module.__package__
        out = {name: importlib.import_module(f"{pkg}.{name}")
               for name in ("samtal_bridge",)}
    finally:
        manager.unload()
    return out


NOW = "2026-11-08T05:20:00-05:00"
IDENTITY = {
    "agent_id": "yrsa-agent",
    "human_owner_id": "volmarr-human",
    "display_name": "Yrsa (agent)",
}


def _bridge(sb):
    transport = sb.InMemoryTransport()
    return sb.SamtalBridge(dict(IDENTITY), transport), transport


def _msg(message_id, sender="other-agent", kind="agent", body="hi"):
    return {
        "message_id": message_id, "room_id": "hall",
        "sender_id": sender, "sender_kind": kind, "body": body,
        "privacy_class": "public",
    }


def test_identity_must_differ_from_human_owner(mods):
    sb = mods["samtal_bridge"]
    with pytest.raises(sb.SamtalError) as exc:
        sb.SamtalBridge(
            {"agent_id": "same", "human_owner_id": "same"},
            sb.InMemoryTransport())
    assert "identity_agent_equals_human_owner" in exc.value.detail
    bridge, _ = _bridge(sb)
    assert bridge.status()["agent_id"] == "yrsa-agent"
    assert bridge.status()["availability"] == "contract-implemented"


def test_send_happy_path_as_agent(mods):
    sb = mods["samtal_bridge"]
    bridge, transport = _bridge(sb)
    envelope = bridge.send_message(
        message_id="m-1", room_id="hall", room_scope="public",
        body="hail", approved=True, sent_at=NOW)
    assert envelope["sender_id"] == "yrsa-agent"
    assert envelope["sender_kind"] == "agent"
    assert envelope["provenance"]["human_owner_id"] == "volmarr-human"
    assert transport.sent[0]["message_id"] == "m-1"


def test_impersonation_refused_by_name(mods):
    sb = mods["samtal_bridge"]
    bridge, transport = _bridge(sb)
    with pytest.raises(sb.SamtalError) as exc:
        bridge.send_message(
            message_id="m-x", room_id="hall", room_scope="public",
            body="i am the owner", sender_id="volmarr-human",
            approved=True)
    assert "impersonation_refused:human_owner_identity" in exc.value.detail
    with pytest.raises(sb.SamtalError) as exc:
        bridge.send_message(
            message_id="m-y", room_id="hall", room_scope="public",
            body="hi", sender_id="other-agent", approved=True)
    assert "impersonation_refused:sender_not_agent_identity" in exc.value.detail
    assert transport.sent == []


def test_send_requires_approval(mods):
    sb = mods["samtal_bridge"]
    bridge, transport = _bridge(sb)
    with pytest.raises(sb.SamtalError) as exc:
        bridge.send_message(
            message_id="m-2", room_id="hall", room_scope="public",
            body="unapproved")
    assert "write_action_requires_approval" in exc.value.detail
    assert transport.sent == []


def test_private_to_public_leak_refused_by_name(mods):
    sb = mods["samtal_bridge"]
    bridge, transport = _bridge(sb)
    with pytest.raises(sb.SamtalError) as exc:
        bridge.send_message(
            message_id="m-3", room_id="hall", room_scope="public",
            body="secret", privacy_class="local-private", approved=True)
    assert "privacy_travel_refused:local-private->public" in exc.value.detail
    with pytest.raises(sb.SamtalError) as exc:
        bridge.send_message(
            message_id="m-4", room_id="hall", room_scope="public",
            body="room only", privacy_class="shared", approved=True)
    assert "privacy_travel_refused:shared->public" in exc.value.detail
    ok = bridge.send_message(
        message_id="m-5", room_id="dm", room_scope="local",
        body="secret", privacy_class="local-private", approved=True)
    assert ok["privacy_class"] == "local-private"
    assert len(transport.sent) == 1


def test_duplicate_delivery_suppressed_by_message_id(mods):
    sb = mods["samtal_bridge"]
    bridge, transport = _bridge(sb)
    transport.deliver(_msg("m-1"))
    transport.deliver(_msg("m-1"))  # redelivery, new cursor
    transport.deliver(_msg("m-2"))
    accepted = bridge.poll()
    assert [m["message_id"] for m in accepted] == ["m-1", "m-2"]
    assert bridge.duplicates_suppressed == 1
    assert bridge.cursor == 3
    assert bridge.poll() == []


def test_cursor_recovery_after_disconnect_no_gaps_no_dupes(mods):
    sb = mods["samtal_bridge"]
    bridge, transport = _bridge(sb)
    for idx in range(1, 6):
        transport.deliver(_msg(f"m-{idx}"))
    first = bridge.poll()
    assert len(first) == 5 and bridge.cursor == 5
    # Disconnect: a fresh bridge seat has lost its cursor entirely.
    rejoined = sb.SamtalBridge(dict(IDENTITY), transport)
    assert rejoined.cursor == 0
    record = rejoined.recover()
    assert record["recovered"] == 5
    assert record["cursor"] == 5
    assert [m["message_id"] for m in rejoined.inbox] == [
        "m-1", "m-2", "m-3", "m-4", "m-5"]
    # A redelivery after recovery is still suppressed.
    transport.deliver(_msg("m-3"))
    assert rejoined.poll() == []
    assert rejoined.duplicates_suppressed == 1


def test_cursor_gap_refused_then_recovers(mods):
    sb = mods["samtal_bridge"]
    bridge, transport = _bridge(sb)
    transport.deliver(_msg("m-1"))
    transport.inject({**_msg("m-3"), "cursor": 3})
    with pytest.raises(sb.SamtalError) as exc:
        bridge.poll()
    assert "cursor_gap:expected 2 got 3" in exc.value.detail
    assert bridge.cursor == 1
    transport.inject({**_msg("m-2"), "cursor": 2})
    accepted = bridge.poll()
    assert [m["message_id"] for m in accepted] == ["m-2", "m-3"]
    assert bridge.cursor == 3


def test_incoming_agent_claiming_human_id_refused(mods):
    sb = mods["samtal_bridge"]
    bridge, transport = _bridge(sb)
    transport.deliver(_msg("m-bad", sender="volmarr-human", kind="agent"))
    transport.deliver(_msg("m-good", sender="volmarr-human", kind="human"))
    accepted = bridge.poll()
    assert [m["message_id"] for m in accepted] == ["m-good"]
    assert any(r.startswith("impersonation_refused:incoming")
               for r in bridge.refusals)
    assert bridge.cursor == 2


def _pipeline(sb):
    pipe = sb.SamkomaPipeline()
    pipe.create_receipt(
        candidate_id="c-1", source_ref="samtal:hall/msg-9",
        summary="Plan the blot", recorded_at=NOW)
    return pipe


def test_samkoma_full_flow_publishes_once(mods):
    sb = mods["samtal_bridge"]
    pipe = _pipeline(sb)
    assert pipe.get("c-1")["status"] == "received"
    pipe.draft_candidate("c-1", title="Winter blot", detail="hall")
    assert pipe.get("c-1")["status"] == "candidate"
    pipe.attach_evidence("c-1", evidence_ref="samtal:hall/msg-9",
                         recorded_at=NOW)
    pipe.attach_evidence("c-1", evidence_ref="samtal:hall/msg-11",
                         recorded_at=NOW)
    assert pipe.get("c-1")["status"] == "evidence"
    pipe.approve("c-1", operator="volmarr", approved=True,
                 recorded_at=NOW)
    assert pipe.get("c-1")["status"] == "approved"
    event = pipe.publish("c-1", recorded_at=NOW)
    assert event["event_id"] == "event-c-1"
    assert event["title"] == "Winter blot"
    assert len(event["evidence"]) == 2
    assert event["approval"]["operator"] == "volmarr"
    assert pipe.get("c-1")["status"] == "published"
    again = pipe.publish("c-1", recorded_at=NOW)
    assert again["event_id"] == event["event_id"]
    assert pipe.status()["published_events"] == 1


def test_samkoma_unapproved_candidate_can_never_publish(mods):
    sb = mods["samtal_bridge"]
    pipe = _pipeline(sb)
    with pytest.raises(sb.SamtalError) as exc:
        pipe.publish("c-1", recorded_at=NOW)
    assert "unapproved_cannot_publish:received->published" in exc.value.detail
    pipe.draft_candidate("c-1", title="Winter blot")
    with pytest.raises(sb.SamtalError) as exc:
        pipe.publish("c-1", recorded_at=NOW)
    assert "unapproved_cannot_publish:candidate->published" in exc.value.detail
    pipe.attach_evidence("c-1", evidence_ref="samtal:hall/msg-9",
                         recorded_at=NOW)
    with pytest.raises(sb.SamtalError) as exc:
        pipe.publish("c-1", recorded_at=NOW)
    assert "unapproved_cannot_publish:evidence->published" in exc.value.detail
    assert pipe.status()["published_events"] == 0


def test_samkoma_approval_requires_evidence_and_grant(mods):
    sb = mods["samtal_bridge"]
    pipe = _pipeline(sb)
    pipe.draft_candidate("c-1", title="Winter blot")
    with pytest.raises(sb.SamtalError) as exc:
        pipe.approve("c-1", operator="volmarr", approved=True,
                     recorded_at=NOW)
    assert "transition_refused:candidate->approved" in exc.value.detail
    pipe.attach_evidence("c-1", evidence_ref="samtal:hall/msg-9",
                         recorded_at=NOW)
    with pytest.raises(sb.SamtalError) as exc:
        pipe.approve("c-1", operator="volmarr", approved=False,
                     recorded_at=NOW)
    assert "approval_not_granted" in exc.value.detail
    assert pipe.get("c-1")["status"] == "evidence"
    with pytest.raises(sb.SamtalError):
        pipe.attach_evidence("c-1", evidence_ref="  ", recorded_at=NOW)


def test_samkoma_receipt_is_idempotent(mods):
    sb = mods["samtal_bridge"]
    pipe = _pipeline(sb)
    again = pipe.create_receipt(
        candidate_id="c-1", source_ref="samtal:hall/msg-9",
        summary="Plan the blot", recorded_at=NOW)
    assert again["status"] == "received"
    assert pipe.status()["counts"] == {"received": 1}
    with pytest.raises(sb.SamtalError):
        pipe.draft_candidate("c-unknown", title="Nope")
