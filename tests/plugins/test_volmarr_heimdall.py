"""X.03 Heimdall presence contracts (roadmap section 38).

These contracts pin: an absent or disabled bridge is reported
truthfully (presence is never fabricated), a present bridge's
read-only status reply becomes a QUALIFIED presence/context
observation with provenance (source, location, time) that is
never accepted world truth, every write action is refused by
name in this stage, private IM content can never become an
observation or enter a presence record (section 38 item 9),
and a simulated session is stamped simulated, never passed off
as real. All bridge traffic here runs against fake transports
and fake probes -- no socket is opened and no grid is touched
except the CLI status/presence verbs, which only probe.
"""
from __future__ import annotations

import argparse
import importlib
import json

import pytest

from hermes_constants import get_hermes_home

SEEDED_SECRET = "hunter2-super-secret-value"


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
               for name in ("heimdall", "cli")}
    finally:
        manager.unload()
    return out


def _probe(hd, state):
    return {"state": state, "disabled_by_operator": state == "disabled",
            "command_socket": "/tmp/heimdall.sock",
            "command_socket_present": state in ("present",),
            "event_socket": "/tmp/heimdall.sock.events",
            "event_socket_present": False,
            "api_host": "127.0.0.1", "api_port": 8765,
            "api_listening": state in ("present", "present-api-only"),
            "core_reachable": state == "present"}


def _core_reply(**over):
    result = {"state": "logged_in", "logged_in": True,
              "simulated": False, "core_version": "0.1.0",
              "dotnet_runtime": ".NET 8.0-test",
              "libremetaverse_version": "2.6.4",
              "agent_name": "Test Agent",
              "agent_uuid": "00000000-0000-0000-0000-0000000000aa",
              "region": "Test Region",
              "position": [128.0, 64.0, 25.0], "mode": "attended"}
    result.update(over)
    return {"id": "hermes-heimdall-status", "cmd": "status",
            "status": "ok", "result": result}


class FakeTransport:
    """Records every command it is asked to transmit; serves
    one canned Core status reply."""

    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def __call__(self, cmd, params):
        self.calls.append(cmd)
        return self.reply


def test_absent_bridge_reported_truthfully(mods):
    hd = mods["heimdall"]
    probe = hd.probe_bridge(env={}, exists=lambda p: False,
                            tcp_connectable=lambda h, p: False)
    assert probe["state"] == "absent"
    assert probe["core_reachable"] is False
    record = hd.presence(recorded_at="2026-11-14T12:00:00+00:00",
                         probe=probe)
    assert record["schema"] == hd.PRESENCE_SCHEMA
    assert record["bridge"]["state"] == "absent"
    assert record["session"]["state"] == "unknown"
    assert record["session"]["logged_in"] is None
    assert record["agent"]["name"] is None
    assert record["location"]["region"] is None
    assert "not fabricated" in record["detail"]
    assert hd.validate_presence(record) is record
    status = hd.heimdall_status(
        recorded_at="t0", probe=probe)
    assert status["bridge"]["state"] == "absent"
    assert status["live_grid_session_claimed"] is False
    assert status["login_attempted"] is False
    assert status["source_head_audited"] == hd.SOURCE_HEAD_AUDITED
    assert "yet to be determined" in status["source_license"]


def test_disabled_bridge_reports_disabled(mods):
    hd = mods["heimdall"]
    probe = hd.probe_bridge(
        env={"HEIMDALL_BRIDGE_DISABLED": "1"},
        exists=lambda p: True, tcp_connectable=lambda h, p: True)
    assert probe["state"] == "disabled"
    assert probe["core_reachable"] is False
    record = hd.presence(recorded_at="t0", probe=probe)
    assert record["bridge"]["state"] == "disabled"
    assert record["session"]["logged_in"] is None
    assert "no effect on the rest of the fork" in record["detail"]
    assert hd.validate_presence(record) is record


def test_present_bridge_presence_contract(mods):
    hd = mods["heimdall"]
    transport = FakeTransport(_core_reply())
    record = hd.presence(
        recorded_at="2026-11-14T12:00:00+00:00",
        transport=transport, probe=_probe(hd, "present"))
    # the adapter transmitted exactly one read-only command
    assert transport.calls == ["status"]
    assert record["session"]["state"] == "logged_in"
    assert record["session"]["logged_in"] is True
    assert record["session"]["simulated"] is False
    assert record["agent"]["name"] == "Test Agent"
    assert record["location"]["region"] == "Test Region"
    assert record["location"]["position"] == [128.0, 64.0, 25.0]
    assert record["mode"] == "attended"
    assert record["core"]["libremetaverse_version"] == "2.6.4"
    # qualified observation with provenance, never world truth
    assert record["qualified"] is True
    assert record["accepted_as_world_truth"] is False
    assert record["provenance"]["source"] == "heimdall-core-ipc"
    assert record["provenance"]["location"] == "Test Region"
    assert record["provenance"]["observed_at"] == \
        "2026-11-14T12:00:00+00:00"
    assert record["observation_id"].startswith("obs-")
    assert record["writes_performed"] is False
    assert hd.validate_presence(record) is record


def test_simulated_and_error_states_stay_honest(mods):
    hd = mods["heimdall"]
    sim = hd.presence(
        recorded_at="t0", probe=_probe(hd, "present"),
        transport=FakeTransport(_core_reply(simulated=True)))
    assert sim["session"]["simulated"] is True
    err = hd.presence(
        recorded_at="t0", probe=_probe(hd, "present"),
        transport=FakeTransport(
            {"status": "error", "error": "login_failed: bad"}))
    assert err["session"]["state"] == "error"
    assert err["session"]["logged_in"] is None
    assert "login_failed" in err["detail"]
    assert hd.validate_presence(err) is err
    api_only = hd.presence(recorded_at="t0",
                           probe=_probe(hd, "present-api-only"))
    assert api_only["session"]["state"] == "unknown"
    assert "unverified" in api_only["detail"]


def test_write_actions_refused_by_name(mods):
    hd = mods["heimdall"]
    for action in sorted(hd.WRITE_ACTIONS):
        with pytest.raises(hd.HeimdallError) as exc:
            hd.check_action(action)
        assert exc.value.name == "write_action_refused"
        assert action in exc.value.detail
    with pytest.raises(hd.HeimdallError) as exc:
        hd.check_action("dance")
    assert exc.value.name == "unknown_action_refused"
    for action in sorted(hd.READ_ACTIONS):
        allowed = hd.check_action(action)
        assert allowed["allowed"] is True
        assert allowed["class"] == "read"
    matrix = {row["action"]: row for row in hd.permission_matrix()}
    assert all(not matrix[a]["allowed"] for a in hd.WRITE_ACTIONS)
    assert all(matrix[a]["allowed"] for a in hd.READ_ACTIONS)
    # the transport itself refuses non-read commands by name
    # before any socket is touched
    transport = hd._default_transport("/nonexistent.sock", 0.5)
    with pytest.raises(hd.HeimdallError) as exc:
        transport("say", {"msg": "hello"})
    assert exc.value.name == "write_action_refused"
    with pytest.raises(hd.HeimdallError) as exc:
        transport("im", {"to_uuid": "x", "msg": "hello"})
    assert exc.value.name == "write_action_refused"


def test_presence_tamper_refused(mods):
    hd = mods["heimdall"]
    record = hd.presence(
        recorded_at="t0", probe=_probe(hd, "present"),
        transport=FakeTransport(_core_reply()))
    truth = json.loads(json.dumps(record))
    truth["accepted_as_world_truth"] = True
    with pytest.raises(hd.HeimdallError):
        hd.validate_presence(truth)
    wrote = json.loads(json.dumps(record))
    wrote["writes_performed"] = True
    with pytest.raises(hd.HeimdallError):
        hd.validate_presence(wrote)
    ghost = hd.presence(recorded_at="t0",
                        probe=_probe(hd, "absent"))
    ghost["session"]["logged_in"] = True
    with pytest.raises(hd.HeimdallError):
        hd.validate_presence(ghost)
    leaked = json.loads(json.dumps(record))
    leaked["im_text"] = "private words"
    with pytest.raises(hd.HeimdallError):
        hd.validate_presence(leaked)


def test_observation_privacy_and_redaction(mods):
    hd = mods["heimdall"]
    obs = hd.build_observation(
        kind="chat", source="heimdall-core-ipc",
        location="Test Region", recorded_at="t0",
        summary=f"resident said password={SEEDED_SECRET} aloud")
    assert obs["schema"] == hd.OBSERVATION_SCHEMA
    assert SEEDED_SECRET not in json.dumps(obs)
    assert "<redacted>" in obs["summary"]
    assert obs["qualified"] is True
    assert obs["accepted_as_world_truth"] is False
    assert obs["telemetry_shareable"] is False
    assert obs["provenance"]["location"] == "Test Region"
    assert hd.validate_observation(obs) is obs
    # private IM / relationship content is refused by name,
    # never recorded (section 38 item 9)
    for kind in ("im", "private_im", "relationship"):
        with pytest.raises(hd.HeimdallError) as exc:
            hd.build_observation(kind=kind, summary="x",
                                 source="heimdall-core-ipc")
        assert exc.value.name == "private_content_refused"
    with pytest.raises(hd.HeimdallError):
        hd.build_observation(kind="telepathy", summary="x",
                             source="heimdall-core-ipc")
    shared = json.loads(json.dumps(obs))
    shared["telemetry_shareable"] = True
    with pytest.raises(hd.HeimdallError):
        hd.validate_observation(shared)


class _Ctx:
    pass


def _run_cli(mods, argv):
    cli = mods["cli"]
    parser = argparse.ArgumentParser(prog="hermes")
    sub = parser.add_subparsers(dest="command")
    volmarr_parser = sub.add_parser("volmarr")
    cli.register_cli(volmarr_parser)
    args = parser.parse_args(argv)
    return cli.health_command(args, ctx=_Ctx())


def test_cli_heimdall_family(mods, capsys):
    hd = mods["heimdall"]
    rc = _run_cli(mods, ["volmarr", "heimdall", "status", "--json"])
    assert rc == 0
    record = json.loads(capsys.readouterr().out)
    assert record["service"] == "volmarr-heimdall"
    assert record["bridge"]["state"] in hd.BRIDGE_STATES
    assert record["live_grid_session_claimed"] is False
    assert record["source_head_audited"] == hd.SOURCE_HEAD_AUDITED
    assert set(record["write_actions_refused"]) == \
        set(hd.WRITE_ACTIONS)
    rc = _run_cli(mods, ["volmarr", "heimdall", "presence",
                         "--json"])
    assert rc == 0
    presence_record = json.loads(capsys.readouterr().out)
    assert presence_record["schema"] == hd.PRESENCE_SCHEMA
    assert presence_record["accepted_as_world_truth"] is False
    assert hd.validate_presence(presence_record) is presence_record
    rc = _run_cli(mods, ["volmarr", "heimdall", "permissions",
                         "--json"])
    assert rc == 0
    matrix = json.loads(capsys.readouterr().out)
    by_action = {row["action"]: row for row in matrix["actions"]}
    assert by_action["say"]["allowed"] is False
    assert by_action["im"]["allowed"] is False
    assert by_action["spend"]["allowed"] is False
    assert by_action["presence"]["allowed"] is True
    rc2 = _run_cli(mods, ["volmarr", "heimdall"])
    assert rc2 == 2
    capsys.readouterr()
