"""X.09 Astrology Engine contracts (roadmap section 44).

These contracts pin the section 44 test gates on the upgraded
adapter: DST fold/gap rejection, unknown birth-time handling
(E09-T2: predict and geoastrology require a known time),
model-free reproducibility (cache replay is byte-identical and
the engine runs once), provenance present in every new result,
private-data containment (identity/geocode fields refused, no
chart contents in status records), dynamic discovery bounded by
the pinned allowlist, and the batch-plan determinism/caps of
section 44 item 8. The pre-X.09 deterministic tools keep their
exact legacy result shapes when no timezone is supplied.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

import pytest

from hermes_constants import get_hermes_home

PIN = "bb4ede4fbb326d21df34a5ca0ca6e343f4f49fbe"


def _write_profile(home: Path, engine: Path) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-astrology]\n"
        "  entries:\n"
        "    volmarr-astrology:\n"
        "      settings:\n"
        f"        engine_path: {json.dumps(str(engine))}\n"
        f"        python_path: {json.dumps(sys.executable)}\n"
        "        timeout_seconds: 20\n",
        encoding="utf-8",
    )


def _engine(path: Path, record: Path, count: Path) -> None:
    path.write_text(
        "import json, sys\n"
        f"open({str(count)!r}, 'a').write('x')\n"
        f"open({str(record)!r}, 'w').write(json.dumps(sys.argv[1:]))\n"
        "cmd = sys.argv[1] if len(sys.argv) > 1 else ''\n"
        "if cmd == 'capabilities':\n"
        "    print(json.dumps({'schema_version': '1.0', 'capabilities': ["
        "{'id': 'vedic', 'status': 'available', 'scope': 'D1'}, "
        "{'id': 'bogus-new', 'status': 'available', 'scope': 'unvetted'}], "
        "'tools': []}))\n"
        "elif cmd == 'tools':\n"
        "    print(json.dumps({'schema_version': '1.0', 'tools': ["
        "{'capability_id': 'vedic'}, {'capability_id': 'bogus-new'}]}))\n"
        "else:\n"
        "    print('REPORT ' + cmd)\n",
        encoding="utf-8",
    )


@pytest.fixture()
def astro(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home = get_hermes_home()
    engine = tmp_path / "astrology_engine.py"
    record = tmp_path / "argv.json"
    count = tmp_path / "count.txt"
    _engine(engine, record, count)
    _write_profile(home, engine)
    manager = PluginManager()
    manager.discover_and_load()
    try:
        yield manager, registry, record, count
    finally:
        manager.unload()


def _dispatch(astro, name, args):
    manager, registry, _r, _c = astro
    return json.loads(registry.dispatch(name, args, scope=manager.scope_key))


VEDIC = {"date": "2000-01-01", "time": "12:00", "latitude": 59.3293,
         "longitude": 18.0686, "timezone": "Europe/Stockholm"}


def test_vedic_structured_argv_and_provenance_envelope(astro):
    _m, _r, record, _c = astro
    result = _dispatch(astro, "astrology_vedic", dict(VEDIC))
    assert result["success"] is True
    assert result["calculation"] == "vedic"
    assert result["engine_pin"] == PIN
    assert result["engine_version"] == "4.0.0"
    assert result["interpretation_included"] is False
    assert result["timezone"] == "Europe/Stockholm"
    assert result["time_precision"] == "exact"
    assert "pyswisseph" in result["ephemeris"]
    assert len(result["cache_key"]) == 64 and result["cache_hit"] is False
    assert result["report"] == "REPORT vedic"
    assert json.loads(record.read_text(encoding="utf-8")) == [
        "vedic", "--date", "2000-01-01", "--time", "12:00",
        "--lat", "59.3293", "--lon", "18.0686",
        "--timezone", "Europe/Stockholm"]


def test_structured_family_and_legacy_reports_smoke(astro):
    cases = [
        ("astrology_vargas", "vargas", dict(VEDIC, date="2000-01-03")),
        ("astrology_dashas", "dashas", dict(VEDIC, date="2000-01-04")),
        ("astrology_panchanga", "panchanga", dict(VEDIC, date="2000-01-05")),
        ("astrology_relocation", "relocation",
         dict(VEDIC, date="2000-01-06", query_latitude=40.7128,
              query_longitude=-74.006)),
        ("astrology_hellenistic", "hellenistic",
         {"date": "2000-01-07", "time": "12:00", "latitude": 59.3293,
          "longitude": 18.0686}),
        ("astrology_dignity", "dignity",
         {"date": "2000-01-08", "time": "12:00", "latitude": 59.3293,
          "longitude": 18.0686}),
    ]
    for tool, calculation, args in cases:
        result = _dispatch(astro, tool, args)
        assert result["success"] is True, (tool, result)
        assert result["calculation"] == calculation
        assert result["engine_pin"] == PIN
        assert result["interpretation_included"] is False


def test_cache_replay_is_byte_identical_and_runs_engine_once(astro):
    _m, _r, _record, count = astro
    args = dict(VEDIC, date="2000-02-01")
    first = _dispatch(astro, "astrology_vedic", args)
    second = _dispatch(astro, "astrology_vedic", args)
    assert first["cache_hit"] is False and second["cache_hit"] is True
    assert first["report"] == second["report"]
    assert first["cache_key"] == second["cache_key"]
    assert count.read_text(encoding="utf-8") == "x"


def test_dst_fold_and_gap_are_rejected_before_the_engine(astro):
    _m, _r, _record, count = astro
    fold = _dispatch(astro, "astrology_natal", {
        "date": "2026-11-01", "time": "01:30", "latitude": 40.7128,
        "longitude": -74.006, "timezone": "America/New_York"})
    assert "error" in fold and "ambiguous" in fold["error"]
    gap = _dispatch(astro, "astrology_natal", {
        "date": "2026-03-08", "time": "02:30", "latitude": 40.7128,
        "longitude": -74.006, "timezone": "America/New_York"})
    assert "error" in gap and "does not exist" in gap["error"]
    assert not count.exists()


def test_unknown_birth_time_is_explicit_never_guessed(astro):
    _m, _r, _record, count = astro
    predict = _dispatch(astro, "astrology_predict", {
        "natal_date": "2000-01-01", "start_date": "2026-01-01",
        "end_date": "2026-02-01", "latitude": 59.3293, "longitude": 18.0686})
    assert "error" in predict and "known birth time" in predict["error"]
    acg = _dispatch(astro, "astrology_astrocartography", {
        "date": "2000-01-01", "latitude": 59.3293, "longitude": 18.0686})
    assert "error" in acg and "known birth time" in acg["error"]
    vedic = _dispatch(astro, "astrology_vedic", {
        "date": "2000-01-01", "latitude": 59.3293, "longitude": 18.0686,
        "timezone": "Europe/Stockholm"})
    assert "error" in vedic
    assert not count.exists()


def test_invalid_timezone_and_identity_fields_are_refused(astro):
    bad_tz = _dispatch(astro, "astrology_natal", {
        "date": "2000-01-01", "time": "12:00", "latitude": 59.3293,
        "longitude": 18.0686, "timezone": "Mars/Olympus"})
    assert "error" in bad_tz and "IANA" in bad_tz["error"]
    identity = _dispatch(astro, "astrology_vedic",
                         dict(VEDIC, date="2000-03-01", name="Private Person"))
    assert "error" in identity
    geocode = _dispatch(astro, "astrology_vedic",
                        dict(VEDIC, date="2000-03-02", city="Stockholm"))
    assert "error" in geocode


def test_natal_timezone_forwarded_and_legacy_shape_kept_without_it(astro):
    _m, _r, record, _c = astro
    with_tz = _dispatch(astro, "astrology_natal", {
        "date": "2000-04-01", "time": "12:00", "latitude": 59.3293,
        "longitude": 18.0686, "timezone": "Europe/Stockholm"})
    assert with_tz["timezone"] == "Europe/Stockholm"
    argv = json.loads(record.read_text(encoding="utf-8"))
    assert argv[-2:] == ["--timezone", "Europe/Stockholm"]
    without = _dispatch(astro, "astrology_natal", {
        "date": "2000-04-02", "time": "12:00", "latitude": 59.3293,
        "longitude": 18.0686})
    assert "timezone" not in without
    assert without["time_known"] is True


def test_runic_argv_and_fold_rejection(astro):
    _m, _r, record, _c = astro
    result = _dispatch(astro, "astrology_runic", {
        "datetime": "2026-05-16T16:45", "longitude": 18.0686,
        "timezone": "Europe/Stockholm"})
    assert result["success"] is True and result["calculation"] == "runic"
    argv = json.loads(record.read_text(encoding="utf-8"))
    assert argv == ["runic", "--datetime", "2026-05-16T16:45", "--lon",
                    "18.0686", "--timezone", "Europe/Stockholm", "--json"]
    fold = _dispatch(astro, "astrology_runic", {
        "datetime": "2026-11-01T01:30", "longitude": -74.006,
        "timezone": "America/New_York"})
    assert "error" in fold and "ambiguous" in fold["error"]


def test_capabilities_discovery_is_allowlist_bounded(astro):
    result = _dispatch(astro, "astrology_capabilities", {})
    assert result["success"] is True
    ids = [c["id"] for c in result["capabilities"]]
    assert ids == ["vedic"]
    assert result["engine_tools"] == ["vedic"]
    assert "bogus-new" not in ids and "bogus-new" not in result["engine_tools"]
    assert len(result["allowlist"]) == 28
    assert result["production_ready"] is False


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
               for name in ("astrology", "cli")}
    finally:
        manager.unload()
    return out


class FakeCtx:
    def __init__(self, cfg=None):
        self._cfg = cfg or {}

    def get_config(self, key, default=None):
        return self._cfg.get(key, default)


def test_local_time_status_classification(mods):
    a = mods["astrology"]
    assert a.local_time_status("2026-01-15", "12:00", "Europe/Stockholm") == "ok"
    assert a.local_time_status("2026-11-01", "01:30", "America/New_York") == "fold"
    assert a.local_time_status("2026-03-08", "02:30", "America/New_York") == "gap"
    assert a.local_time_status("2026-01-15", "12:00", "Mars/Olympus") == "invalid_zone"


def test_batch_plan_is_deterministic_capped_and_refuses_by_name(mods):
    a = mods["astrology"]
    items = [{"tool": "astrology_natal", "date": "2000-01-01",
              "time": "12:00", "timezone": "Europe/Stockholm"},
             {"tool": "astrology_predict", "date": "2000-01-01",
              "timezone": "Europe/Stockholm"},
             {"tool": "astrology_natal", "date": "2026-11-01",
              "time": "01:30", "timezone": "America/New_York"},
             {"tool": "astrology_bogus", "date": "2000-01-01"}]
    first = a.build_batch_plan(items)
    second = a.build_batch_plan(items)
    assert first == second
    assert first["replay_key"] == second["replay_key"]
    assert first["item_count"] == 1
    reasons = {r["reason"] for r in first["refused"]}
    assert reasons == {"unknown_birth_time", "local_time_fold",
                       "unknown_calculation"}
    assert first["runs_engine"] is False
    many = [{"tool": "astrology_natal", "date": "2000-01-01",
             "time": "12:00", "timezone": "Europe/Stockholm"}] * 40
    capped = a.build_batch_plan(many)
    assert capped["item_count"] == 15
    assert {r["reason"] for r in capped["refused"]} == {"batch_item_cap"}
    assert capped["estimated_worst_case_seconds"] <= capped["caps"]["total_budget_seconds"]


def test_status_is_truthful_and_contains_no_chart_data(mods, tmp_path):
    a = mods["astrology"]
    record = a.astrology_status(FakeCtx())
    assert record["enabled"] is False and record["configured"] is False
    assert record["tree"]["status"] == "not_configured"
    assert record["production_ready"] is False
    assert record["engine_pin"] == PIN
    blob = json.dumps(record)
    assert "positions" not in blob and "report" not in blob
    configured = a.astrology_status(FakeCtx({
        "astrology_enabled": True, "astrology_root": str(tmp_path / "missing-tree")}))
    assert configured["tree"]["status"] == "tree_missing"


def test_catalog_measures_engine_surface_vs_readme_claim(mods):
    a = mods["astrology"]
    catalog = a.capability_catalog()
    assert catalog["measured"] == {"cli_subcommands": 57,
                                   "capabilities": 28, "engine_tools": 26}
    assert len(catalog["exposed_tools"]) == 16
    assert catalog["interpretation_included"] is False
    assert any("tarot" in row["engine"] for row in catalog["not_exposed"])


def _run_cli(mods, argv, ctx):
    cli = mods["cli"]
    parser = argparse.ArgumentParser(prog="hermes")
    sub = parser.add_subparsers(dest="command")
    volmarr_parser = sub.add_parser("volmarr")
    cli.register_cli(volmarr_parser)
    args = parser.parse_args(argv)
    return cli.health_command(args, ctx=ctx)


def test_cli_astrology_family(mods, capsys):
    ctx = FakeCtx()
    rc = _run_cli(mods, ["volmarr", "astrology", "status", "--json"], ctx)
    assert rc == 0
    record = json.loads(capsys.readouterr().out)
    assert record["service"] == "volmarr-astrology"
    assert record["enabled"] is False and record["production_ready"] is False
    rc = _run_cli(mods, ["volmarr", "astrology", "catalog", "--json"], ctx)
    assert rc == 0
    catalog = json.loads(capsys.readouterr().out)
    assert catalog["measured"]["cli_subcommands"] == 57
    rc = _run_cli(mods, ["volmarr", "astrology", "batch", "--json"], ctx)
    assert rc == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["runs_engine"] is False and "synthetic" in plan["source_label"]
    assert plan["refused_count"] == 1
    rc = _run_cli(mods, ["volmarr", "astrology"], ctx)
    assert rc == 2
    capsys.readouterr()
