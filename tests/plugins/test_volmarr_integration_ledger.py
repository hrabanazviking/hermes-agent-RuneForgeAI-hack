"""W08/E0 integration ledger: the promoted lock, enforced.

The E0 draft lock was a file no code read, and it carried a stale
ravens-absent claim for a day after the tree had landed on this host.
These contracts pin the promotion: the committed lock loads, validates
clean against the committed tree, keeps the seven E0 first pins
byte-exact, refuses a DRAFT lock by name, rejects the superseded
absence claim if it ever creeps back, and reports a genuinely absent
ravens tree honestly instead of hiding it. CLI tests drive the real
``hermes volmarr engines`` family through the plugin's own argparse
registration and dispatcher -- the lock's first live caller.
"""

from __future__ import annotations

import argparse
import copy
import importlib
import json
from pathlib import Path

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
               for name in ("integration_ledger", "cli")}
    finally:
        manager.unload()
    return out


class _Ctx:
    def __init__(self, config=None):
        self._config = dict(config or {})

    def get_config(self, key, default=None):
        return self._config.get(key, default)


def _real_lock(mods) -> dict:
    return mods["integration_ledger"].load_lock()


def _write_lock(tmp_path: Path, payload) -> Path:
    path = tmp_path / "integration-lock.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _fake_ravens_home(tmp_path: Path, head: str) -> Path:
    home = tmp_path / "home"
    git = home / "ravens" / ".git"
    (git / "refs" / "heads").mkdir(parents=True)
    (git / "HEAD").write_text("ref: refs/heads/master\n", encoding="utf-8")
    (git / "refs" / "heads" / "master").write_text(head + "\n", encoding="utf-8")
    return home


# -- the promoted lock itself -------------------------------------------------


def test_promoted_lock_loads_and_validates(mods):
    il = mods["integration_ledger"]
    lock = _real_lock(mods)
    assert lock["schema"] == "runeforge.integration-lock/v1"
    assert not lock["status"].upper().startswith("DRAFT")
    assert il.validate_lock(lock) == []


def test_promoted_lock_covers_every_section13_row(mods):
    names = {row["name"] for row in _real_lock(mods)["engines"]}
    assert len(names) == 26
    for required in (
        "Verdandi", "Project A.E.S.I.R.", "Bifrost", "Muninn", "Huginn",
        "MemPalace", "OpenViking", "WYRD Protocol", "Kista",
        "Astrology Engine", "RuneTarotEngine", "Seidr Engine", "Hamr",
        "Seidr-Smidja", "AIAvatarKit", "OmniVoice", "ChatIndex",
        "Sagnaskemma engine", "Hermes SessionDB",
        "Persistent identity / affect / goals / agency",
    ):
        assert required in names


def test_no_row_claimed_past_its_proof(mods):
    il = mods["integration_ledger"]
    for row in _real_lock(mods)["engines"]:
        assert row["evidence_stage"] in il.EVIDENCE_STAGES
        # W08 promoted a ledger, not engine upgrades: no row may claim
        # end-to-end or production status on the strength of an audit.
        assert row["evidence_stage"] not in {
            "end-to-end working", "production qualified"}


def test_status_ok_against_this_tree(mods):
    il = mods["integration_ledger"]
    # Default home: on purplelongship ~/ravens is present at the pin.
    report = il.integration_status()
    assert report["engine_count"] == 26
    counts = report["verification_counts"]
    assert counts.get("blocked") == 1  # Sagnaskemma, honestly blocked
    assert counts.get("partially_verified", 0) == 0  # none left (E.13 verified the Hamr LICENSE text; E.06/E.07/E.12 verified OpenViking/WYRD/SRD earlier)
    assert counts.get("verified") == 25
    assert report["status"] == "ok", report["problems"]
    assert all(row["adapter_paths_present"] for row in report["engines"])


def test_ravens_rows_carry_the_correction(mods):
    lock = _real_lock(mods)
    for name in ("Muninn", "Huginn"):
        row = next(r for r in lock["engines"] if r["name"] == name)
        assert row["pinned"] == mods["integration_ledger"].RAVENS_TREE_HEAD
        assert row["current_head"] == row["pinned"]
        assert row["verification"]["status"] == "verified"
        assert "absent on purplelongship" not in json.dumps(row).lower()


def test_find_engine_case_insensitive(mods):
    il = mods["integration_ledger"]
    lock = _real_lock(mods)
    assert il.find_engine(lock, "verdandi")["name"] == "Verdandi"
    assert il.find_engine(lock, "WYRD PROTOCOL")["name"] == "WYRD Protocol"
    assert il.find_engine(lock, "no such engine") is None


# -- honesty guards ------------------------------------------------------------


def test_first_pin_drift_is_refused(mods):
    il = mods["integration_ledger"]
    lock = copy.deepcopy(_real_lock(mods))
    for row in lock["engines"]:
        if row["name"] == "Hamr":
            row["pinned"] = "0" * 40
    problems = il.validate_lock(lock)
    assert any("Hamr" in p and "first pin" in p for p in problems)


def test_draft_lock_is_refused_by_name(mods, tmp_path):
    il = mods["integration_ledger"]
    lock = copy.deepcopy(_real_lock(mods))
    lock["status"] = "DRAFT - Phase 0 recon, must verify each row"
    with pytest.raises(il.IntegrationLedgerError) as excinfo:
        il.load_lock(_write_lock(tmp_path, lock))
    assert excinfo.value.name == "lock_still_draft"


def test_missing_and_invalid_lock_refused(mods, tmp_path):
    il = mods["integration_ledger"]
    with pytest.raises(il.IntegrationLedgerError) as missing:
        il.load_lock(tmp_path / "nope.json")
    assert missing.value.name == "lock_missing"
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(il.IntegrationLedgerError) as invalid:
        il.load_lock(bad)
    assert invalid.value.name == "lock_invalid"


def test_superseded_ravens_absence_claim_is_rejected(mods):
    il = mods["integration_ledger"]
    lock = copy.deepcopy(_real_lock(mods))
    for row in lock["engines"]:
        if row["name"] == "Muninn":
            row["verification"] = {
                "status": "unverified",
                "notes": "tree absent on purplelongship",
            }
    problems = il.validate_lock(lock)
    assert any("Muninn" in p and "superseded" in p for p in problems)


def test_unclassified_mode_and_stage_are_refused(mods):
    il = mods["integration_ledger"]
    lock = copy.deepcopy(_real_lock(mods))
    lock["engines"][0]["adapter"]["mode"] = "sort of live"
    lock["engines"][1]["evidence_stage"] = "basically done"
    problems = il.validate_lock(lock)
    assert any("Verdandi" in p and "not classified" in p for p in problems)
    assert any("A.E.S.I.R." in p and "28.3" in p for p in problems)


# -- local tree truth ------------------------------------------------------------


def test_ravens_tree_status_matches_pin(mods, tmp_path):
    il = mods["integration_ledger"]
    home = _fake_ravens_home(tmp_path, il.RAVENS_TREE_HEAD)
    status = il.ravens_tree_status(home)
    assert status["present"] is True
    assert status["head"] == il.RAVENS_TREE_HEAD
    assert status["matches_pin"] is True


def test_ravens_absence_is_reported_not_hidden(mods, tmp_path):
    il = mods["integration_ledger"]
    empty_home = tmp_path / "empty"
    empty_home.mkdir()
    status = il.ravens_tree_status(empty_home)
    assert status["present"] is False
    assert status["matches_pin"] is False
    report = il.integration_status(home=empty_home)
    assert report["status"] == "problems"
    assert any("ravens" in p for p in report["problems"])


def test_missing_adapter_path_is_reported(mods, tmp_path):
    il = mods["integration_ledger"]
    lock = copy.deepcopy(_real_lock(mods))
    for row in lock["engines"]:
        if row["name"] == "Kista":
            row["adapter"]["paths"] = ["plugins/no-such-adapter"]
    path = _write_lock(tmp_path, lock)
    home = _fake_ravens_home(tmp_path, il.RAVENS_TREE_HEAD)
    report = il.integration_status(path, home=home)
    assert report["status"] == "problems"
    assert any("Kista" in p and "missing" in p for p in report["problems"])


# -- the live caller: hermes volmarr engines -------------------------------------


def _run_cli(mods, argv):
    parser = argparse.ArgumentParser(prog="hermes volmarr")
    mods["cli"].register_cli(parser)
    args = parser.parse_args(argv)
    return mods["cli"].health_command(args, ctx=_Ctx())


def test_cli_engines_status_json(mods, capsys):
    assert _run_cli(mods, ["engines", "status", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["engine_count"] == 26
    assert payload["status"] == "ok"
    assert payload["first_pins"]["Hamr"] == (
        "f77aa588601b38a69b6c1fc0a6733ed5e95dffa8")


def test_cli_engines_show_and_unknown(mods, capsys):
    assert _run_cli(mods, ["engines", "show", "Verdandi"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["pinned"] == "2fc9db8bf555546ab96084f74b1d442b8e1c7a63"
    assert _run_cli(mods, ["engines", "show", "Project A.E.S.I.R."]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["pinned"] == "d9f88b9a65531dfaf48b22df167d75d45d43ca50"
    assert _run_cli(mods, ["engines", "show", "Bifrost"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["pinned"] == "99988dbb638d1b4f35f4a07590d61ad08b72ebd8"
    assert _run_cli(mods, ["engines", "show", "MemPalace"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["pinned"] == "0ed1be82dcbe4f59081b87c4eaa0986af0768ff4"
    assert _run_cli(mods, ["engines", "show", "OpenViking"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["pinned"] == "90f4edcede4c6a665fccb747417ebe6c1db56f4d"
    assert _run_cli(mods, ["engines", "show", "WYRD Protocol"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["pinned"] == "89ed09394c7e13b2e63f91e342fbab8ff9890cbc"
    assert _run_cli(mods, ["engines", "show", "Kista"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["pinned"] == "41a6d65863af9ec5d41ca148828a0b6863605b86"
    assert _run_cli(mods, ["engines", "show", "Astrology Engine"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["pinned"] == "bb4ede4fbb326d21df34a5ca0ca6e343f4f49fbe"
    assert _run_cli(mods, ["engines", "show", "RuneTarotEngine"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["pinned"] == "432e461136ba58cb3e507bb9cd86b4bb2faba80b"
    assert _run_cli(mods, ["engines", "show", "Seidr Engine"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["pinned"] == "fdc2b3c85c62982a4550dfe476751287d723519d"
    assert _run_cli(mods, ["engines", "show", "SRD data (dnd-5e-srd)"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["pinned"] == "2e62e0413061c2443e21369cdc074c7a7356a857"
    assert _run_cli(mods, ["engines", "show", "Hamr"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["pinned"] == "f77aa588601b38a69b6c1fc0a6733ed5e95dffa8"
    assert _run_cli(mods, ["engines", "show", "NoSuchEngine"]) == 1
    capsys.readouterr()


def test_cli_engines_validate_and_usage(mods, capsys):
    assert _run_cli(mods, ["engines", "validate", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"problems": [], "status": "ok"}
    assert _run_cli(mods, ["engines"]) == 2
    assert "Usage: hermes volmarr engines" in capsys.readouterr().out
