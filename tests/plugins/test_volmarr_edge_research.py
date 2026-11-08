"""W12/N5 edge + research contracts.

Roadmap section 24 acceptance: low-resource failure tests never
corrupt the persona corpus or the Hermes state database, and
proposed self-repair patches never apply automatically. These
contracts pin: the resource meter's unavailable-field honesty
(GPU/NPU/temperatures never invented), private opt-in telemetry
with transmission refused by name, the MimirAlloc evidence gate
refusing promotion until every item is present (and never as a
drop-in replacement), Yggdrasil scheduling over static fixtures
only with live peers refused by name, Lif-thrasir proposals that
can never be applied, and low-resource guarded writes that fail
cleanly by name leaving fixture files byte-identical. Contract
level only: NO live mesh, allocator swap or self-repair exists in
this slice and none is claimed. CLI tests drive the real
``hermes volmarr edge-research`` family.
"""

from __future__ import annotations

import argparse
import hashlib
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
               for name in ("edge_research", "cli")}
    finally:
        manager.unload()
    return out


NOW = "2026-11-08T05:45:00-05:00"
MEMINFO = (
    "MemTotal:       16384000 kB\n"
    "MemFree:         2048000 kB\n"
    "MemAvailable:    8192000 kB\n"
    "Buffers:          512000 kB\n"
    "Cached:          4096000 kB\n"
    "SwapTotal:       4194304 kB\n"
    "SwapFree:        4194304 kB\n"
)
DISK = {"total": 500_000_000_000, "used": 200_000_000_000,
        "free": 300_000_000_000}
FULL_EVIDENCE = {
    "correctness": "evidence://mimiralloc/correctness-2026-11",
    "sanitizer_evidence": "evidence://mimiralloc/asan-tsan-2026-11",
    "fragmentation": "evidence://mimiralloc/fragmentation-2026-11",
    "abi_alignment": "evidence://mimiralloc/abi-2026-11",
    "allocation_failure": "evidence://mimiralloc/alloc-failure-2026-11",
    "thread_safety": "evidence://mimiralloc/threads-2026-11",
    "arm64_proof": "evidence://mimiralloc/arm64-2026-11",
    "oom_recovery": "evidence://mimiralloc/oom-2026-11",
}
NODES = [
    {"node_id": "node-b", "cpu_cores": 4, "memory_bytes": 8 * 1024**3,
     "source": "static-fixture", "arch": "x86_64"},
    {"node_id": "node-a", "cpu_cores": 16, "memory_bytes": 32 * 1024**3,
     "source": "static-fixture", "arch": "aarch64"},
]


def _meter(mods, **kwargs):
    er = mods["edge_research"]
    kwargs.setdefault("meminfo_text", MEMINFO)
    kwargs.setdefault("loadavg", (0.5, 0.25, 0.1))
    kwargs.setdefault("disk_usage", DISK)
    return er.read_resource_meter(recorded_at=NOW, **kwargs)


def test_meter_measures_local_sources_with_provenance(mods):
    env = _meter(mods)
    assert env["provenance"]["service"] == "volmarr-edge-research"
    assert env["provenance"]["confidentiality"] == "local-private"
    meter = env["outputs"]
    assert meter["memory"]["status"] == "measured"
    assert meter["memory"]["total_bytes"] == 16384000 * 1024
    assert meter["memory"]["available_bytes"] == 8192000 * 1024
    assert meter["load"] == {"status": "measured", "load1": 0.5,
                             "load5": 0.25, "load15": 0.1}
    assert meter["disk"]["free_bytes"] == 300_000_000_000


def test_meter_unmeasurable_fields_unavailable_never_invented(mods):
    meter = _meter(mods)["outputs"]
    accel = meter["accelerators_and_thermals"]
    for field_name in ("gpu_util_percent", "gpu_temp_c",
                       "npu_util_percent", "npu_temp_c",
                       "cpu_temp_c", "disk_wear_percent"):
        assert accel[field_name]["status"] == "unavailable"
        assert "value" not in accel[field_name]


def test_meter_probe_values_measured_others_stay_unavailable(mods):
    meter = _meter(mods, probes={"gpu_util_percent": 42.0,
                                 "gpu_temp_c": 61})["outputs"]
    accel = meter["accelerators_and_thermals"]
    assert accel["gpu_util_percent"] == {"status": "measured", "value": 42.0}
    assert accel["gpu_temp_c"] == {"status": "measured", "value": 61}
    assert accel["npu_util_percent"]["status"] == "unavailable"


def test_meter_telemetry_private_and_transmission_none(mods):
    meter = _meter(mods)["outputs"]
    assert meter["telemetry"] == {"privacy": "local-private",
                                  "transmission": "none", "opt_in": False}


def test_telemetry_share_refused_without_opt_in_and_to_cloud(mods):
    er = mods["edge_research"]
    local = er.telemetry_share_decision(destination="local")
    assert local["allowed"] is False
    assert local["reasons"] == ["telemetry_opt_in_required"]
    cloud = er.telemetry_share_decision(destination="cloud", opt_in=True)
    assert cloud["allowed"] is False
    assert cloud["reasons"] == ["telemetry_transmission_refused:cloud"]
    ok = er.telemetry_share_decision(destination="local", opt_in=True)
    assert ok["allowed"] is True


def test_mimiralloc_checklist_empty_evidence_all_missing(mods):
    er = mods["edge_research"]
    checklist = er.mimiralloc_checklist()
    assert checklist["experimental"] is True
    assert checklist["opt_in_only"] is True
    assert checklist["drop_in_replacement"] is False
    assert checklist["present_count"] == 0
    assert checklist["missing"] == list(er.EVIDENCE_ITEMS)


def test_mimiralloc_promotion_refused_by_name_until_complete(mods):
    er = mods["edge_research"]
    partial = dict(FULL_EVIDENCE)
    del partial["arm64_proof"]
    del partial["oom_recovery"]
    decision = er.mimiralloc_promotion(partial)
    assert decision["promoted"] is False
    assert decision["allowed"] is False
    assert "mimiralloc_promotion_refused" in decision["reasons"]
    assert "evidence_missing:arm64_proof" in decision["reasons"]
    assert "evidence_missing:oom_recovery" in decision["reasons"]


def test_mimiralloc_empty_evidence_ref_does_not_count(mods):
    er = mods["edge_research"]
    forged = dict(FULL_EVIDENCE, correctness="   ")
    decision = er.mimiralloc_promotion(forged)
    assert decision["promoted"] is False
    assert "evidence_missing:correctness" in decision["reasons"]


def test_mimiralloc_full_evidence_promotes_experimental_only(mods):
    er = mods["edge_research"]
    decision = er.mimiralloc_promotion(FULL_EVIDENCE)
    assert decision["promoted"] is True
    assert decision["scope"] == "experimental-opt-in-only"
    assert decision["drop_in_replacement"] is False


def test_yggdrasil_inventory_static_fixtures_no_mesh_claimed(mods):
    er = mods["edge_research"]
    env = er.node_inventory(NODES, recorded_at=NOW)
    inv = env["outputs"]
    assert inv["node_count"] == 2
    assert inv["live_peers"] == 0
    assert inv["mesh_claimed"] is False
    assert inv["basis"] == "static-fixtures-only"


def test_yggdrasil_non_fixture_node_refused_by_name(mods):
    er = mods["edge_research"]
    bad = [dict(NODES[0], source="live-peer")]
    with pytest.raises(er.EdgeError) as exc:
        er.node_inventory(bad, recorded_at=NOW)
    assert "node_source_not_static_fixture:live-peer" in exc.value.detail


def test_yggdrasil_schedule_fits_and_no_fit(mods):
    er = mods["edge_research"]
    fit = er.schedule_experiment(
        NODES, {"workload_id": "w1", "cpu_cores": 8,
                "memory_bytes": 16 * 1024**3})
    assert fit["scheduled"] is True
    assert fit["node_id"] == "node-a"
    assert fit["dispatched"] is False
    nofit = er.schedule_experiment(
        NODES, {"workload_id": "w2", "cpu_cores": 64,
                "memory_bytes": 16 * 1024**3})
    assert nofit["scheduled"] is False
    assert nofit["reason"] == "no_static_fixture_fits"


def test_yggdrasil_live_peer_connection_refused_by_name(mods):
    er = mods["edge_research"]
    with pytest.raises(er.EdgeError) as exc:
        er.connect_peer("node-a")
    assert exc.value.name == "live_connection_refused"
    assert "yggdrasil_live_peer_connection_not_claimed:node-a" in exc.value.detail


def test_lifthrasir_proposal_recorded_never_applied(mods):
    er = mods["edge_research"]
    book = er.ProposalBook()
    record = book.propose("Rebuild index nightly", "detail",
                          recorded_at=NOW)
    assert record["status"] == "proposed"
    assert record["applied"] is False
    with pytest.raises(er.EdgeError) as exc:
        er.apply_proposal(book, record["proposal_id"])
    assert exc.value.name == "apply_refused"
    assert f"lifthrasir_apply_refused:{record['proposal_id']}" in exc.value.detail
    assert book.get(record["proposal_id"])["applied"] is False
    report = er.lifthrasir_report(book)
    assert report["mode"] == "observe/report/propose"
    assert report["applied_count"] == 0


def test_guarded_write_low_memory_refused_file_unchanged(mods, tmp_path):
    er = mods["edge_research"]
    target = tmp_path / "corpus.md"
    target.write_bytes(b"original corpus bytes")
    with pytest.raises(er.EdgeError) as exc:
        er.guarded_write(target, b"replacement",
                         mem_available_bytes=1024,
                         disk_free_bytes=10 * 1024**3)
    assert exc.value.name == "resource_exhausted"
    assert "low_memory_refused" in exc.value.detail
    assert target.read_bytes() == b"original corpus bytes"


def test_guarded_write_low_disk_refused_file_unchanged(mods, tmp_path):
    er = mods["edge_research"]
    target = tmp_path / "state.db"
    target.write_bytes(b"state bytes")
    with pytest.raises(er.EdgeError) as exc:
        er.guarded_write(target, b"new state",
                         mem_available_bytes=10 * 1024**3,
                         disk_free_bytes=512)
    assert exc.value.name == "resource_exhausted"
    assert "low_disk_refused" in exc.value.detail
    assert target.read_bytes() == b"state bytes"


def test_guarded_write_with_headroom_writes_byte_exact(mods, tmp_path):
    er = mods["edge_research"]
    target = tmp_path / "out.bin"
    data = b"payload-\x00\x01\x02"
    result = er.guarded_write(target, data,
                              mem_available_bytes=10 * 1024**3,
                              disk_free_bytes=10 * 1024**3)
    assert result["written"] is True
    assert result["sha256"] == hashlib.sha256(data).hexdigest()
    assert target.read_bytes() == data


def test_edge_status_honest_not_claimed(mods):
    er = mods["edge_research"]
    status = er.edge_status(recorded_at=NOW)
    assert status["live_connection"] == "not-claimed"
    assert status["yggdrasil"]["mesh_claimed"] is False
    assert status["lifthrasir"]["auto_apply"] is False
    assert status["mimiralloc"]["drop_in_replacement"] is False


class _Ctx:
    def __init__(self):
        self._config = {}

    def config_get(self, key, default=None):
        return self._config.get(key, default)


def _run_cli(mods, argv):
    cli = mods["cli"]
    parser = argparse.ArgumentParser(prog="hermes")
    sub = parser.add_subparsers(dest="command")
    volmarr_parser = sub.add_parser("volmarr")
    cli.register_cli(volmarr_parser)
    args = parser.parse_args(argv)
    return cli.health_command(args, ctx=_Ctx())


def test_cli_edge_research_status_and_meter(mods, capsys):
    rc = _run_cli(mods, ["volmarr", "edge-research", "status", "--json"])
    assert rc == 0
    record = json.loads(capsys.readouterr().out)
    assert record["live_connection"] == "not-claimed"
    assert record["lifthrasir"]["mode"] == "observe/report/propose"
    rc = _run_cli(mods, ["volmarr", "edge-research", "meter", "--json"])
    assert rc == 0
    env = json.loads(capsys.readouterr().out)
    assert env["outputs"]["telemetry"]["transmission"] == "none"
    assert env["outputs"]["memory"]["status"] in ("measured", "unavailable")


def test_cli_edge_research_propose_records_only(mods, capsys):
    rc = _run_cli(mods, ["volmarr", "edge-research", "propose",
                         "--title", "Tune cache", "--json"])
    assert rc == 0
    record = json.loads(capsys.readouterr().out)
    assert record["status"] == "proposed"
    assert record["applied"] is False
