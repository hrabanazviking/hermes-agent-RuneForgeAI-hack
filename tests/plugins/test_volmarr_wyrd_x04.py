"""X.04 WYRD Protocol contracts (roadmap section 39).

These contracts pin the section 39 test gates on the upgraded
single WYRD adapter: version mismatch fails truthfully, the
fact/observation/evidence/fiction distinction holds by
construction, journaled writes persist across restart, event
replay is idempotent, stale writes are rejected before any
traffic, journals are profile-isolated, Verðandi is signalled
only after WYRD confirms a write, and prompt packets are
bounded with provenance on every item. All server traffic here
runs against a capturing fake transport -- no socket is opened
except the CLI status/capabilities verbs, which probe a
dead port and must report the absence truthfully.
"""
from __future__ import annotations

import argparse
import importlib
import json

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
               for name in ("wyrd", "cli", "world_telemetry")}
    finally:
        manager.unload()
    return out


PROV = {"source": "test-harness", "source_ref": "test://source-1",
        "observed_at": "2026-11-14T10:00:00+00:00"}


class FakeCtx:
    def __init__(self, cfg=None):
        self._cfg = cfg or {}

    def get_config(self, key, default=None):
        return self._cfg.get(key, default)


class FakeServer:
    """Capturing fake WYRD server over the verified contract."""

    def __init__(self):
        self.calls = []
        self.event_ok = True
        self.world = {
            "world_id": "probe_world",
            "formatted_for_llm": "WORLD STATE\nworld: probe_world",
            "present_entities": ["sigrid"],
            "canonical_facts": {"sigrid.location": "hall"},
            "query_timestamp": "2026-11-14T10:00:00Z",
        }

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        if path == "/health":
            return {"status": "ok", "version": "1.5.0"}
        if path == "/world":
            return dict(self.world)
        if path.startswith("/facts"):
            return {"facts": [{"record_id": "fact-1",
                               "key": "location", "value": "hall"}]}
        if path == "/query":
            assert body["use_turn_loop"] is False
            return {"response": "Sigrid is in the hall."}
        if path == "/event":
            return {"ok": self.event_ok}
        raise AssertionError(f"unexpected path {path}")


class FakeTelemetry:
    def __init__(self):
        self.writes = []

    def record_write(self, ctx, change_kind, *, revision=None):
        self.writes.append((change_kind, revision))
        return True

    def record(self, ctx, change_kind, **metadata):
        self.writes.append((change_kind, metadata.get("revision")))
        return True


def test_capability_negotiation_and_version_mismatch(mods):
    w = mods["wyrd"]
    caps = w.negotiate_capabilities(
        {"healthy": True, "status": "healthy"}, server_version="1.5.0")
    assert caps["compatible"] is True
    assert caps["mismatches"] == []
    assert caps["source_pin"] == w.SOURCE_PIN
    assert set(caps["methods"]) == set(w.ADAPTER_METHODS)
    assert w.require_compatible(caps) is caps
    old = w.negotiate_capabilities(
        {"healthy": True, "status": "healthy"}, server_version="0.9.0")
    assert old["compatible"] is False
    with pytest.raises(w.WyrdError) as exc:
        w.require_compatible(old)
    assert exc.value.name == "version_mismatch"
    api2 = w.negotiate_capabilities(
        {"healthy": True, "status": "healthy"}, api_version=2)
    assert api2["compatible"] is False
    absent = w.negotiate_capabilities({"healthy": False,
                                       "status": "unreachable"})
    assert absent["compatible"] is None  # unknown, never dressed up


def test_record_schema_mismatch_fails_truthfully(mods):
    w = mods["wyrd"]
    assert w.check_record_schema_version("1.0.0") == "1.0.0"
    assert w.check_record_schema_version("1.7.2") == "1.7.2"
    with pytest.raises(w.WyrdError) as exc:
        w.check_record_schema_version("2.0.0")
    assert exc.value.name == "version_mismatch"
    assert "not silently migrated" in exc.value.detail


def test_truth_class_distinction(mods):
    w = mods["wyrd"]
    fact = w.build_world_record(
        namespace="probe_world", entity_id="sigrid",
        truth_class="canonical_fact", key="location", value="hall",
        confidence=0.9, provenance=PROV)
    assert fact["durable"] is True
    assert w.validate_world_record(fact) is fact
    obs = w.build_world_record(
        namespace="probe_world", entity_id="sigrid",
        truth_class="tentative_observation", key="location",
        title="Seen", summary="Sigrid seemed to be in the hall",
        provenance=PROV)
    assert obs["durable"] is False
    assert w.validate_world_record(obs) is obs
    evidence = w.build_world_record(
        namespace="probe_world", entity_id="sigrid",
        truth_class="quoted_evidence", summary='the hall, at dusk (quoted)',
        provenance=PROV)
    assert evidence["durable"] is False
    fiction = w.build_world_record(
        namespace="sagnaskemma-campaign", entity_id="hero_1",
        truth_class="fictional_state", key="hp", value="12",
        reality="fictional", provenance=PROV)
    assert fiction["reality"] == "fictional"
    assert w.validate_world_record(fiction) is fiction
    # an observation can never present itself as durable canon
    tampered = json.loads(json.dumps(obs))
    tampered["durable"] = True
    with pytest.raises(w.WyrdError):
        w.validate_world_record(tampered)
    # fictional state can never validate as a canonical fact
    dressed = json.loads(json.dumps(fiction))
    dressed["truth_class"] = "canonical_fact"
    dressed["durable"] = True
    with pytest.raises(w.WyrdError):
        w.validate_world_record(dressed)
    # quoted evidence without a named source is refused
    with pytest.raises(w.WyrdError):
        w.build_world_record(
            namespace="probe_world", entity_id="sigrid",
            truth_class="quoted_evidence", summary="words",
            provenance={"source": "test-harness"})
    # a canonical fact without a durable source ref is refused
    with pytest.raises(w.WyrdError):
        w.build_world_record(
            namespace="probe_world", entity_id="sigrid",
            truth_class="canonical_fact", key="location",
            value="hall", provenance={"source": "test-harness"})


def test_private_memory_stays_outside_wyrd(mods):
    w = mods["wyrd"]
    with pytest.raises(w.WyrdError) as exc:
        w.build_world_record(
            namespace="probe_world", entity_id="sigrid",
            truth_class="canonical_fact", key="relationship.status",
            value="close", provenance=PROV)
    assert exc.value.name == "private_memory_refused"
    with pytest.raises(w.WyrdError) as exc:
        w.build_world_record(
            namespace="probe_world", entity_id="sigrid",
            truth_class="tentative_observation", kind="identity",
            title="who", summary="identity claim", provenance=PROV)
    assert exc.value.name == "private_memory_refused"


def test_refs_round_trip(mods):
    w = mods["wyrd"]
    ref = w.make_ref("probe_world", "sigrid", "location")
    assert ref == "wyrd://probe_world/sigrid#location"
    assert w.parse_ref(ref) == {"namespace": "probe_world",
                                "entity_id": "sigrid",
                                "component": "location"}
    with pytest.raises(w.WyrdError):
        w.make_ref("Bad Namespace", "sigrid")
    with pytest.raises(w.WyrdError):
        w.parse_ref("https://example.com/sigrid")


def _entry(**over):
    entry = {"namespace": "probe_world", "entity_id": "sigrid",
             "key": "location", "value": "hall",
             "truth_class": "canonical_fact", "title": "",
             "summary": "", "record_id": "wr-test",
             "ref": "wyrd://probe_world/sigrid#location",
             "provenance": PROV, "idempotency_key": "k-1",
             "expected_revision": None}
    entry.update(over)
    return entry


def test_journal_persistence_and_idempotent_replay(mods, tmp_path):
    w = mods["wyrd"]
    path = tmp_path / "journal.db"
    sent = []
    journal = w.WyrdJournal(path)
    result = journal.commit(
        _entry(), sender=lambda e: sent.append(e) or True)
    assert result["status"] == "committed"
    assert result["revision"] == 1
    state1 = journal.replay()
    assert state1["probe_world/sigrid/location"]["value"] == "hall"
    assert state1["probe_world/sigrid/location"]["revision"] == 1
    # replay is idempotent: folding again changes nothing
    assert journal.replay() == state1
    # persistence across restart: a fresh object over the same
    # file replays the identical state
    restarted = w.WyrdJournal(path)
    assert restarted.replay() == state1
    assert restarted.current_revision(
        "probe_world", "sigrid", "location") == 1
    assert len(sent) == 1


def test_journal_idempotency_and_conflict(mods, tmp_path):
    w = mods["wyrd"]
    journal = w.WyrdJournal(tmp_path / "j.db")
    calls = []
    sender = lambda e: calls.append(e) or True  # noqa: E731
    first = journal.commit(_entry(), sender=sender)
    dupe = journal.commit(_entry(), sender=sender)
    assert first["status"] == "committed"
    assert dupe["status"] == "duplicate"
    assert dupe["sender_called"] is False
    assert len(calls) == 1  # the server was written exactly once
    with pytest.raises(w.WyrdError) as exc:
        journal.commit(_entry(value="garden"), sender=sender)
    assert exc.value.name == "idempotency_conflict"
    assert len(calls) == 1


def test_journal_stale_write_rejected_before_traffic(mods, tmp_path):
    w = mods["wyrd"]
    journal = w.WyrdJournal(tmp_path / "j.db")
    calls = []
    sender = lambda e: calls.append(e) or True  # noqa: E731
    journal.commit(_entry(), sender=sender)
    with pytest.raises(w.WyrdError) as exc:
        journal.commit(
            _entry(idempotency_key="k-2", value="garden",
                   expected_revision=0),
            sender=sender)
    assert exc.value.name == "stale_write_rejected"
    assert len(calls) == 1  # rejected before any traffic
    ok = journal.commit(
        _entry(idempotency_key="k-2", value="garden",
               expected_revision=1),
        sender=sender)
    assert ok["status"] == "committed" and ok["revision"] == 2


def test_journal_unconfirmed_write_leaves_no_trace(mods, tmp_path):
    w = mods["wyrd"]
    journal = w.WyrdJournal(tmp_path / "j.db")
    result = journal.commit(_entry(), sender=lambda e: False)
    assert result["status"] == "unconfirmed"
    assert journal.replay() == {}
    assert journal.current_revision(
        "probe_world", "sigrid", "location") == 0


def test_profile_isolation_journals(mods, tmp_path):
    w = mods["wyrd"]
    journal_a = w.WyrdJournal(tmp_path / "profile-a" / "j.db")
    journal_b = w.WyrdJournal(tmp_path / "profile-b" / "j.db")
    journal_a.commit(_entry(), sender=lambda e: True)
    assert journal_a.replay() != {}
    assert journal_b.replay() == {}
    assert journal_b.current_revision(
        "probe_world", "sigrid", "location") == 0


def test_adapter_distinct_methods_fake_transport(mods):
    w = mods["wyrd"]
    server = FakeServer()
    adapter = w.WyrdAdapter(FakeCtx(), transport=server)
    health = adapter.liveness()
    assert health["healthy"] is True
    caps = adapter.capabilities()
    assert caps["compatible"] is True
    snap = adapter.snapshot()
    assert snap["world_id"] == "probe_world"
    assert snap["references"] == ["wyrd://probe_world/sigrid"]
    with pytest.raises(w.WyrdError) as exc:
        adapter.snapshot(namespace="other_world")
    assert exc.value.name == "namespace_mismatch"
    facts = adapter.facts("sigrid", namespace="probe_world")
    assert facts["facts"][0]["record_id"] == "fact-1"
    assert facts["references"][0]["ref"] == \
        "wyrd://probe_world/sigrid"
    answer = adapter.query("sigrid", "Where is Sigrid?")
    assert answer["writeback"] is False
    assert answer["provenance"]["source"] == "wyrd/passive_oracle"
    assert [c[1].split("?")[0] for c in server.calls] == \
        ["/health", "/health", "/world", "/world", "/facts", "/query"]


def test_adapter_write_signals_only_after_confirmation(mods, tmp_path):
    w = mods["wyrd"]
    server = FakeServer()
    telemetry = FakeTelemetry()
    journal = w.WyrdJournal(tmp_path / "j.db")
    adapter = w.WyrdAdapter(FakeCtx(), transport=server,
                            journal=journal, telemetry=telemetry)
    result = adapter.write_fact(
        namespace="probe_world", entity_id="sigrid", key="location",
        value="hall", provenance=PROV, idempotency_key="w-1")
    assert result["status"] == "committed"
    assert result["event_published"] is True
    assert telemetry.writes == [("fact", 1)]
    # duplicate: no second server write, no second signal
    dupe = adapter.write_fact(
        namespace="probe_world", entity_id="sigrid", key="location",
        value="hall", provenance=PROV, idempotency_key="w-1")
    assert dupe["status"] == "duplicate"
    assert telemetry.writes == [("fact", 1)]
    # unconfirmed: journal holds nothing, Verdandi hears nothing
    server.event_ok = False
    failed = adapter.write_fact(
        namespace="probe_world", entity_id="sigrid", key="mood",
        value="calm", provenance=PROV, idempotency_key="w-2")
    assert failed["status"] == "unconfirmed"
    assert failed["event_published"] is False
    assert telemetry.writes == [("fact", 1)]
    assert journal.current_revision("probe_world", "sigrid", "mood") == 0
    serialized = json.dumps(telemetry.writes)
    assert "hall" not in serialized and "sigrid" not in serialized


def test_subscriptions_and_streaming(mods):
    w = mods["wyrd"]
    server = FakeServer()
    adapter = w.WyrdAdapter(FakeCtx(), transport=server)
    seen = []
    adapter.subscribe("state", seen.append)
    assert adapter.poll_once() == []  # baseline, no change yet
    server.world["canonical_facts"] = {"sigrid.location": "garden"}
    events = adapter.poll_once()
    assert len(events) == 1
    assert events[0]["type"] == "world_changed"
    assert events[0]["changed_fact_keys"] == ["sigrid.location"]
    assert seen == events
    assert adapter.poll_once() == []  # steady state: no re-emit
    server.world["formatted_for_llm"] = "WORLD STATE\ngarden"
    streamed = list(adapter.stream(max_polls=1))
    assert len(streamed) == 1
    with pytest.raises(w.WyrdError):
        adapter.subscribe("telepathy", seen.append)


def test_conflict_resolution_competing_observations(mods):
    w = mods["wyrd"]
    older = w.build_world_record(
        namespace="probe_world", entity_id="sigrid",
        truth_class="tentative_observation", key="location",
        title="seen", summary="in the hall", confidence=0.6,
        provenance={**PROV, "observed_at": "2026-11-14T09:00:00+00:00"})
    newer = w.build_world_record(
        namespace="probe_world", entity_id="sigrid",
        truth_class="tentative_observation", key="location",
        title="seen", summary="in the garden", confidence=0.6,
        provenance={**PROV, "observed_at": "2026-11-14T10:00:00+00:00",
                    "caused_by": older["record_id"]})
    fact = w.build_world_record(
        namespace="probe_world", entity_id="sigrid",
        truth_class="canonical_fact", key="location", value="hall",
        confidence=0.5, provenance=PROV)
    resolved = w.resolve_conflict([older, newer])
    assert resolved["winner"]["record_id"] == newer["record_id"]
    assert [r["record_id"] for r in resolved["superseded"]] == \
        [older["record_id"]]
    assert len(resolved["causal_provenance"]) == 2  # nothing dropped
    with_fact = w.resolve_conflict([older, newer, fact])
    assert with_fact["winner"]["record_id"] == fact["record_id"]
    assert len(with_fact["superseded"]) == 2


def test_prompt_packet_bounded_with_provenance(mods):
    w = mods["wyrd"]
    items = [{"ref": f"wyrd://probe_world/e{i}", "text": "x" * 100,
              "provenance": {"source": "wyrd/facts"},
              "truth_class": "canonical_fact", "priority": float(i)}
             for i in range(40)]
    packet = w.build_prompt_packet(items, max_chars=1000, max_items=5)
    assert packet["item_count"] == 5
    assert packet["total_chars"] <= 1000
    assert packet["truncated"] is True and packet["omitted"] == 35
    assert all(i["ref"] and i["provenance"]["source"] == "wyrd/facts"
               for i in packet["items"])
    # highest priority first
    assert packet["items"][0]["ref"].endswith("/e39")
    huge = w.build_prompt_packet(
        [{"ref": "wyrd://probe_world/sigrid", "text": "A" * 500,
          "provenance": {"source": "wyrd/passive_oracle"}}],
        max_chars=256, max_items=1)
    assert huge["items"][0]["text"] == "A" * 255 + "\u2026"


def test_consumer_seams(mods):
    w = mods["wyrd"]
    seams = {s["name"] for s in w.consumer_seams()}
    assert seams == {"heimdall", "sagnaskemma", "voice_avatar",
                     "local_sensors"}
    ok = w.authorize_consumer("heimdall", "submit_qualified_observation")
    assert ok["allowed"] is True
    assert ok["truth_class"] == "tentative_observation"
    with pytest.raises(w.WyrdError) as exc:
        w.authorize_consumer("heimdall", "write_canonical_fact")
    assert exc.value.name == "consumer_operation_refused"
    assert w.authorize_consumer(
        "sagnaskemma", "write_fictional_state")["allowed"] is True
    with pytest.raises(w.WyrdError):
        w.authorize_consumer("voice_avatar", "write_observation")
    with pytest.raises(w.WyrdError) as exc:
        w.authorize_consumer("local_sensors",
                             "submit_observation_with_uncertainty")
    assert exc.value.name == "uncertainty_required"
    assert w.authorize_consumer(
        "local_sensors", "submit_observation_with_uncertainty",
        confidence=0.4)["allowed"] is True
    with pytest.raises(w.WyrdError) as exc:
        w.authorize_consumer("stranger", "read_query")
    assert exc.value.name == "unknown_consumer_refused"


class _DeadCtx:
    def get_config(self, key, default=None):
        return {"wyrd_base_url": "http://127.0.0.1:9",
                "wyrd_probe_timeout_ms": 300}.get(key, default)


def _run_cli(mods, argv, ctx):
    cli = mods["cli"]
    parser = argparse.ArgumentParser(prog="hermes")
    sub = parser.add_subparsers(dest="command")
    volmarr_parser = sub.add_parser("volmarr")
    cli.register_cli(volmarr_parser)
    args = parser.parse_args(argv)
    return cli.health_command(args, ctx=ctx)


def test_cli_world_family(mods, capsys):
    w = mods["wyrd"]
    ctx = _DeadCtx()
    rc = _run_cli(mods, ["volmarr", "world", "status", "--json"], ctx)
    assert rc == 0
    record = json.loads(capsys.readouterr().out)
    assert record["server_present"] is False  # truthful absence
    assert record["live_server_claimed"] is False
    assert record["capabilities"]["compatible"] is None
    assert record["source_pin"] == w.SOURCE_PIN
    assert record["pin_moved_in_x04"] is False
    rc = _run_cli(mods, ["volmarr", "world", "consumers", "--json"], ctx)
    assert rc == 0
    consumers = json.loads(capsys.readouterr().out)
    assert {c["name"] for c in consumers["consumers"]} == \
        {"heimdall", "sagnaskemma", "voice_avatar", "local_sensors"}
    rc = _run_cli(mods, ["volmarr", "world", "capabilities", "--json"], ctx)
    assert rc == 0
    caps = json.loads(capsys.readouterr().out)
    assert caps["compatible"] is None
    rc = _run_cli(mods, ["volmarr", "world", "snapshot", "--json"], ctx)
    assert rc == 1  # absent server fails truthfully, no fabrication
    capsys.readouterr()
    rc = _run_cli(mods, ["volmarr", "world"], ctx)
    assert rc == 2
    capsys.readouterr()
