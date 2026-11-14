"""X.05 Sagnaskemma contracts (roadmap section 40).

These contracts pin the section 40 test gates on the private
adapter: seeded determinism, multi-user seat isolation,
interrupted action rollback, serialization round trip,
source-canon denial, no leakage into public surfaces, and
optional game session continuity (handoff without duplicated
rolls or state). Every fixture here is synthetic and authored
for this test file -- no private canon, scenario, character
or lore content appears anywhere in these tests. The staged
private engine is never imported here; engine-facing proofs
run against an injected runner or a synthetic root."""
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
               for name in ("sagnaskemma", "cli")}
    finally:
        manager.unload()
    return out


class FakeCtx:
    def __init__(self, cfg=None):
        self._cfg = cfg or {}

    def get_config(self, key, default=None):
        return self._cfg.get(key, default)


def _store(mods, tmp_path, name="sessions.db"):
    return mods["sagnaskemma"].TableSessionStore(tmp_path / name)


def _session(mods, tmp_path, seed=42, name="sessions.db"):
    store = _store(mods, tmp_path, name)
    store.create_session("table-one", "gm-seat", seed)
    store.add_seat("table-one", "player-seat", "player")
    store.add_seat("table-one", "watcher", "spectator")
    return store


def test_seeded_determinism(mods):
    s = mods["sagnaskemma"]
    first = s.DiceOwner(42)
    seq_a = [first.roll("2d6+3"), first.roll("1d20"), first.roll("3d4")]
    second = s.DiceOwner(42)
    seq_b = [second.roll("2d6+3"), second.roll("1d20"),
             second.roll("3d4")]
    assert seq_a == seq_b  # same seed, identical recorded outcomes
    assert [r["index"] for r in seq_a] == [0, 1, 2]
    assert all(r["total"] == sum(r["faces"]) + r["modifier"]
               for r in seq_a)
    with pytest.raises(s.SagnaskemmaError) as exc:
        first.roll("d20")
    assert exc.value.name == "dice_malformed"


def test_session_rolls_are_seeded_and_recorded(mods, tmp_path):
    s = mods["sagnaskemma"]
    store = _session(mods, tmp_path)
    r1 = store.apply("table-one", "gm-seat", "txn-1", "roll",
                     {"expression": "2d6+3", "purpose": "synthetic"})
    r2 = store.apply("table-one", "player-seat", "txn-2", "roll",
                     {"expression": "1d20"})
    owner = s.DiceOwner(42)
    assert r1["roll"] == owner.roll("2d6+3", roller="gm-seat",
                                     purpose="synthetic")
    assert r2["roll"]["faces"] == owner.roll("1d20")["faces"]
    state = store.state("table-one")
    assert len(state["dice"]["rolls"]) == 2  # audit ledger
    assert state["dice"]["seed"] == 42


def test_multi_user_seat_isolation(mods, tmp_path):
    s = mods["sagnaskemma"]
    store = _session(mods, tmp_path)
    store.create_session("table-two", "other-gm", 9)
    # a seat in one session holds nothing in the other
    with pytest.raises(s.SagnaskemmaError) as exc:
        store.apply("table-two", "player-seat", "txn-x", "roll",
                    {"expression": "1d6"})
    assert exc.value.name == "seat_not_found"
    # spectator is read-only
    with pytest.raises(s.SagnaskemmaError) as exc:
        store.apply("table-one", "watcher", "txn-y", "roll",
                    {"expression": "1d6"})
    assert exc.value.name == "seat_permission_refused"
    # player may roll and hold inventory but not run combat or undo
    ok = store.apply("table-one", "player-seat", "txn-p", "inventory",
                     {"holder": "player-seat", "item": "torch"})
    assert ok["count"] == 1
    with pytest.raises(s.SagnaskemmaError):
        store.apply("table-one", "player-seat", "txn-q", "combat",
                    {"name": "dummy", "hp": 5})
    with pytest.raises(s.SagnaskemmaError):
        store.undo("table-one", "player-seat", "txn-p")
    roles = {seat["seat_id"]: seat["role"]
             for seat in store.seats("table-one")}
    assert roles == {"gm-seat": "gm", "player-seat": "player",
                     "watcher": "spectator"}


def test_interrupted_action_rollback(mods, tmp_path):
    s = mods["sagnaskemma"]
    store = _session(mods, tmp_path)
    store.apply("table-one", "gm-seat", "txn-1", "roll",
                {"expression": "1d20"})
    before = store.state("table-one")
    # an inventory take the holder cannot satisfy aborts whole
    with pytest.raises(s.SagnaskemmaError) as exc:
        store.apply("table-one", "player-seat", "txn-2", "inventory",
                    {"holder": "player-seat", "item": "torch",
                     "count": -1})
    assert exc.value.name == "inventory_insufficient"
    # a malformed roll after a good one spends no dice either
    with pytest.raises(s.SagnaskemmaError):
        store.apply("table-one", "gm-seat", "txn-3", "roll",
                    {"expression": "banana"})
    after = store.state("table-one")
    assert after == before  # state, dice owner and rolls untouched
    assert store.get_session("table-one")["revision"] == 1
    assert [t["txn_id"] for t in store.transactions("table-one")] == \
        ["txn-1"]
    # the next good roll continues the seeded sequence exactly
    nxt = store.apply("table-one", "gm-seat", "txn-4", "roll",
                      {"expression": "1d20"})
    owner = s.DiceOwner(42)
    owner.roll("1d20")
    assert nxt["roll"]["faces"] == owner.roll("1d20")["faces"]


def test_idempotent_transactions_and_undo(mods, tmp_path):
    s = mods["sagnaskemma"]
    store = _session(mods, tmp_path)
    first = store.apply("table-one", "gm-seat", "txn-1", "roll",
                        {"expression": "2d6"})
    again = store.apply("table-one", "gm-seat", "txn-1", "roll",
                        {"expression": "2d6"})
    assert again["duplicate"] is True
    assert again["roll"] == first["roll"]  # no second roll spent
    assert len(store.state("table-one")["dice"]["rolls"]) == 1
    with pytest.raises(s.SagnaskemmaError) as exc:
        store.apply("table-one", "gm-seat", "txn-1", "roll",
                    {"expression": "3d6"})
    assert exc.value.name == "idempotency_conflict"
    store.apply("table-one", "gm-seat", "txn-2", "combat",
                {"name": "training-dummy", "hp": 10})
    store.apply("table-one", "gm-seat", "txn-3", "combat",
                {"name": "training-dummy", "damage": 4})
    assert store.state("table-one")["combatants"] == \
        {"training-dummy": {"hp": 6, "max_hp": 10}}
    with pytest.raises(s.SagnaskemmaError) as exc:
        store.undo("table-one", "gm-seat", "txn-2")
    assert exc.value.name == "undo_not_latest"  # savepoint stack
    undone = store.undo("table-one", "gm-seat", "txn-3")
    assert undone["status"] == "undone"
    assert store.state("table-one")["combatants"] == \
        {"training-dummy": {"hp": 10, "max_hp": 10}}


def test_serialization_round_trip_and_crash_recovery(mods, tmp_path):
    s = mods["sagnaskemma"]
    store = _session(mods, tmp_path)
    store.apply("table-one", "gm-seat", "txn-1", "roll",
                {"expression": "2d6+1"})
    store.apply("table-one", "gm-seat", "txn-2", "initiative",
                {"entries": [{"name": "b", "initiative": 12},
                             {"name": "a", "initiative": 15}]})
    store.apply("table-one", "player-seat", "txn-3", "describe",
                {"text": "A synthetic hall, authored for this test."})
    exported = store.export_session("table-one")
    blob = json.dumps(exported, sort_keys=True)  # must serialize
    revived = json.loads(blob)
    assert revived == exported
    other = _store(mods, tmp_path, "imported.db")
    imported = other.import_session(revived)
    assert imported["handoff"] == "imported"
    assert other.state("table-one") == store.state("table-one")
    assert other.export_session("table-one") == exported
    # crash recovery: a fresh store object over the same file
    reopened = _store(mods, tmp_path, "sessions.db")
    assert reopened.state("table-one") == store.state("table-one")
    assert reopened.get_session("table-one")["revision"] == 3


def test_handoff_continuity_no_duplicated_rolls(mods, tmp_path):
    s = mods["sagnaskemma"]
    store = _session(mods, tmp_path)
    store.apply("table-one", "gm-seat", "txn-1", "roll",
                {"expression": "1d20"})
    exported = store.export_session("table-one")
    other = _store(mods, tmp_path, "frontend-b.db")
    other.import_session(json.loads(json.dumps(exported)))
    assert other.import_session(exported)["handoff"] == \
        "already_present"  # re-handoff duplicates nothing
    dup = other.apply("table-one", "gm-seat", "txn-1", "roll",
                      {"expression": "1d20"})
    assert dup["duplicate"] is True
    # both frontends continue with the identical next roll
    next_a = store.apply("table-one", "gm-seat", "txn-2", "roll",
                         {"expression": "1d20"})
    next_b = other.apply("table-one", "gm-seat", "txn-2", "roll",
                         {"expression": "1d20"})
    assert next_a["roll"] == next_b["roll"]


def test_source_canon_denial_and_not_configured(mods, tmp_path):
    s = mods["sagnaskemma"]
    bare = FakeCtx()
    # users without source access see not configured, nothing hidden
    with pytest.raises(s.SagnaskemmaError) as exc:
        s.authorize_capability(bare, "dice")
    assert exc.value.name == "not_configured"
    status = s.sagnaskemma_status(bare)
    assert status["configured"] is False
    assert status["availability"] == "not configured"
    assert status["production_ready"] is False
    record = s.service_record(bare)
    assert record["hidden_content_served"] is False
    # canon denial stands even before configuration questions
    with pytest.raises(s.SagnaskemmaError) as exc:
        s.authorize_capability(bare, "lore_retrieval")
    assert exc.value.name == "canon_denied"
    flagged = FakeCtx({"sagnaskemma_canon_access": True})
    with pytest.raises(s.SagnaskemmaError) as exc:
        s.authorize_capability(flagged, "lore_retrieval")
    assert exc.value.name == "canon_store_not_configured"
    with pytest.raises(s.SagnaskemmaError) as exc:
        s.authorize_capability(bare, "flying")
    assert exc.value.name == "unknown_capability"
    # a synthetic staged root configures mechanics, canon stays denied
    root = tmp_path / "engine-root"
    (root / "engine").mkdir(parents=True)
    (root / "engine" / "__init__.py").write_text(
        '__version__ = "0.2.0"\n', encoding="utf-8")
    (root / "engine" / "api.py").write_text("", encoding="utf-8")
    (root / "engine" / "dice.py").write_text("", encoding="utf-8")
    staged = FakeCtx({"sagnaskemma_engine_root": str(root)})
    probe = s.probe_engine(str(root))
    assert probe["configured"] is True
    assert probe["engine_version"] == "0.2.0"
    ok = s.authorize_capability(staged, "combat")
    assert ok["allowed"] is True and ok["kind"] == "mechanics"
    with pytest.raises(s.SagnaskemmaError) as exc:
        s.authorize_capability(staged, "lore_retrieval")
    assert exc.value.name == "canon_denied"
    caps = s.capability_catalog()
    assert caps["mechanics"] == list(s.MECHANICS_CAPABILITIES)
    assert caps["narrative"] == list(s.NARRATIVE_CAPABILITIES)
    assert "content" not in json.dumps(caps)  # no hidden content served


def test_samtal_link_and_wyrd_namespace(mods, tmp_path):
    s = mods["sagnaskemma"]
    store = _session(mods, tmp_path)
    with pytest.raises(s.SagnaskemmaError) as exc:
        store.link_samtal("table-one", "gm-seat", "table-one")
    assert exc.value.name == "room_session_conflated"
    with pytest.raises(s.SagnaskemmaError):
        store.link_samtal("table-one", "player-seat", "room-9")
    link = store.link_samtal("table-one", "gm-seat", "room-9")
    assert link["samtal_room_id"] == "room-9"
    assert {seat["seat_id"] for seat in link["seats"]} == \
        {"gm-seat", "player-seat", "watcher"}
    wyrd = store.wyrd_campaign_record("table-one")
    assert wyrd["namespace"] == "sagnaskemma-table-one"
    assert wyrd["reality"] == "fictional"
    assert wyrd["truth_class"] == "fictional_state"


def test_engine_client_contract(mods):
    s = mods["sagnaskemma"]
    calls = []

    def runner(code, argv):
        calls.append((code, argv))
        if "discover" in code:
            return {"protocol_version": "1.0", "name": "sagnaskemma",
                    "command_count": 243,
                    "transports": list(s.ENGINE_TRANSPORTS),
                    "state_env": "SAGNASKEMMA_STATE_DIR"}
        req = json.loads(argv[0])
        return {"protocol_version": "1.0", "id": req["request_id"],
                "ok": True, "rolls": []}

    client = s.EngineClient("", runner=runner)
    found = client.discover()
    assert found["command_count"] == 243
    assert found["schema"] == s.SERVICE_SCHEMA
    out = client.execute(["roll", "1d6"], request_id="txn-9")
    assert out["id"] == "txn-9"

    def bad_runner(code, argv):
        return {"protocol_version": "2.0"}

    with pytest.raises(s.SagnaskemmaError) as exc:
        s.EngineClient("", runner=bad_runner).discover()
    assert exc.value.name == "version_mismatch"
    with pytest.raises(s.SagnaskemmaError) as exc:
        s.EngineClient("").discover()
    assert exc.value.name == "not_configured"


def _run_cli(mods, argv, ctx):
    cli = mods["cli"]
    parser = argparse.ArgumentParser(prog="hermes")
    sub = parser.add_subparsers(dest="command")
    volmarr_parser = sub.add_parser("volmarr")
    cli.register_cli(volmarr_parser)
    args = parser.parse_args(argv)
    return cli.health_command(args, ctx=ctx)


def test_cli_table_family(mods, capsys):
    s = mods["sagnaskemma"]
    ctx = FakeCtx()
    rc = _run_cli(mods, ["volmarr", "table", "status", "--json"], ctx)
    assert rc == 0
    record = json.loads(capsys.readouterr().out)
    assert record["configured"] is False  # truthful absence
    assert record["availability"] == "not configured"
    assert record["source_head_audited"] == s.SOURCE_HEAD_AUDITED
    assert record["production_ready"] is False
    assert record["hidden_content_served"] is False
    rc = _run_cli(mods, ["volmarr", "table", "capabilities",
                         "--json"], ctx)
    assert rc == 0
    caps = json.loads(capsys.readouterr().out)
    assert caps["capabilities"]["mechanics"][0] == "dice"
    assert "lore_retrieval" in caps["capabilities"]["narrative"]
    rc = _run_cli(mods, ["volmarr", "table"], ctx)
    assert rc == 2
    capsys.readouterr()
