"""X.01 Yggdrasil local-host contracts (roadmap section 36).

These contracts pin: versioned envelopes with source identity +
privacy zone, read-only local discovery where unprobed capability
stays "unknown" (never guessed), pure placement with wrong-owner
refusal, budget enforcement, token-limit and memory checks, and
no accidental cloud egress (any non-local destination refused by
name). No mesh is claimed: status reports live_peers 0 and
mesh_claimed False until host-to-host live proof exists
(section 36 deliverable 10). CLI tests drive the real
``hermes volmarr yggdrasil`` family.
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
               for name in ("yggdrasil_local", "cli")}
    finally:
        manager.unload()
    return out


def _cap(mods, **probes):
    yg = mods["yggdrasil_local"]
    base = {"models": ["m1"], "context_lengths": {"m1": 8192},
            "accelerator": "gpu-test", "node_id": "node-a"}
    base.update(probes)
    return yg.discover_local_node(probes=base, recorded_at="t0")


def _req(mods, **kw):
    yg = mods["yggdrasil_local"]
    base = dict(request_id="r1", owner="alice", model="m1",
                est_tokens=100, est_seconds=5, budget_tokens=1000,
                budget_seconds=60, recorded_at="t0")
    base.update(kw)
    return yg.build_task_request(**base)


def test_discovery_unknown_stays_unknown(mods):
    yg = mods["yggdrasil_local"]
    cap = yg.discover_local_node(recorded_at="t0")
    assert cap["schema"] == yg.CAPABILITY_SCHEMA
    assert cap["source_project"] == yg.SOURCE_PROJECT
    assert cap["accelerator"] == "unknown"
    assert cap["models"] == "unknown"
    assert cap["context_lengths"] == "unknown"
    assert cap["network_topology"]["peers"] == "unknown"
    assert cap["mesh_claimed"] is False
    assert cap["live_peers"] == 0
    assert isinstance(cap["ram_total_bytes"], int)


def test_discovery_probe_values_are_used_verbatim(mods):
    cap = _cap(mods)
    assert cap["models"] == ["m1"]
    assert cap["accelerator"] == "gpu-test"
    assert cap["node_id"] == "node-a"


def test_placement_happy_path_local(mods):
    yg = mods["yggdrasil_local"]
    dec = yg.place_task(_cap(mods), _req(mods), caller="alice")
    assert dec["schema"] == yg.PLACEMENT_SCHEMA
    assert dec["decision"] == "place_local"
    assert dec["reasons"] == []
    assert dec["scheduler_owner"] == "hermes-cron-gateway"


def test_placement_wrong_owner_refused(mods):
    yg = mods["yggdrasil_local"]
    with pytest.raises(yg.YggdrasilLocalError) as exc:
        yg.place_task(_cap(mods), _req(mods), caller="mallory")
    assert exc.value.name == "wrong_owner"


def test_placement_budget_enforced(mods):
    yg = mods["yggdrasil_local"]
    dec = yg.place_task(_cap(mods), _req(mods, est_tokens=5000,
                                         budget_tokens=100), caller="alice")
    assert dec["decision"] == "refuse"
    assert any("budget_exceeded" in r for r in dec["reasons"])


def test_placement_no_cloud_egress(mods):
    yg = mods["yggdrasil_local"]
    dec = yg.place_task(_cap(mods), _req(mods, destination="cloud:example"),
                        caller="alice")
    assert dec["decision"] == "refuse"
    assert any("egress_not_authorized" in r for r in dec["reasons"])
    assert any("cloud_egress_refused" in r for r in dec["reasons"])


def test_placement_unknown_capability_never_guessed(mods):
    yg = mods["yggdrasil_local"]
    cap = yg.discover_local_node(recorded_at="t0")
    dec = yg.place_task(cap, _req(mods), caller="alice")
    assert dec["decision"] == "refuse"
    assert any("capability_unknown" in r for r in dec["reasons"])


def test_placement_token_limit_and_memory(mods):
    yg = mods["yggdrasil_local"]
    dec = yg.place_task(_cap(mods), _req(mods, est_tokens=9000,
                                         budget_tokens=99999), caller="alice")
    assert any("token_limit_exceeded" in r for r in dec["reasons"])
    dec2 = yg.place_task(_cap(mods), _req(mods, required_ram_bytes=10**15),
                         caller="alice")
    assert any("insufficient_memory" in r for r in dec2["reasons"])


def test_lease_outcome_receipt_chain_and_wrong_owner(mods):
    yg = mods["yggdrasil_local"]
    dec = yg.place_task(_cap(mods), _req(mods), caller="alice")
    lease = yg.issue_lease(dec, caller="alice", lease_id="l1")
    assert lease["schema"] == yg.LEASE_SCHEMA
    with pytest.raises(yg.YggdrasilLocalError) as exc:
        yg.issue_lease(dec, caller="mallory", lease_id="l2")
    assert exc.value.name == "wrong_owner"
    outcome, receipt = yg.complete_task(
        lease, caller="alice", status="succeeded", detail="done")
    assert outcome["schema"] == yg.OUTCOME_SCHEMA
    assert receipt["schema"] == yg.RECEIPT_SCHEMA
    assert len(receipt["evidence_sha256"]) == 64
    assert receipt["live_mesh_proof"] is False
    refused = yg.place_task(_cap(mods), _req(mods, destination="cloud:x"),
                            caller="alice")
    with pytest.raises(yg.YggdrasilLocalError) as exc2:
        yg.issue_lease(refused, caller="alice", lease_id="l3")
    assert exc2.value.name == "lease_refused"


def test_malformed_envelopes_refused_by_name(mods):
    yg = mods["yggdrasil_local"]
    with pytest.raises(yg.YggdrasilLocalError):
        yg.build_task_request(request_id="", owner="a", model="m",
                              est_tokens=1, est_seconds=1,
                              budget_tokens=1, budget_seconds=1)
    with pytest.raises(yg.YggdrasilLocalError):
        yg.validate_task_request({"schema": "bogus"})
    with pytest.raises(yg.YggdrasilLocalError):
        _req(mods, privacy_zone="secret-zone")


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


def test_cli_yggdrasil_status_and_discover(mods, capsys):
    assert _run_cli(mods, ["volmarr", "yggdrasil", "status", "--json"]) == 0
    record = json.loads(capsys.readouterr().out)
    assert record["mesh_claimed"] is False
    assert record["live_peers"] == 0
    assert record["source_head_audited"].startswith("1af750f1")
    assert _run_cli(mods, ["volmarr", "yggdrasil", "discover", "--json"]) == 0
    cap = json.loads(capsys.readouterr().out)
    assert cap["accelerator"] == "unknown"
    assert cap["scope"] == "local-host-only"


def test_cli_yggdrasil_place_refuses_egress(mods, capsys, tmp_path):
    req_file = tmp_path / "req.json"
    req_file.write_text(json.dumps({
        "request_id": "cli-r1", "owner": "alice", "model": "m1",
        "est_tokens": 10, "est_seconds": 1, "budget_tokens": 100,
        "budget_seconds": 10, "destination": "cloud:example"}),
        encoding="utf-8")
    rc = _run_cli(mods, ["volmarr", "yggdrasil", "place", "--request",
                         str(req_file), "--caller", "alice", "--json"])
    assert rc == 0
    dec = json.loads(capsys.readouterr().out)
    assert dec["decision"] == "refuse"
    assert any("egress" in r for r in dec["reasons"])
    rc2 = _run_cli(mods, ["volmarr", "yggdrasil", "place", "--request",
                          str(req_file), "--caller", "mallory", "--json"])
    assert rc2 == 1
