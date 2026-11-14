"""X.08 Samkoma contracts (roadmap section 43).

These contracts pin the section 43 test gates on the proposal-only
adapter: unsupported claim stays unsupported (citation integrity),
no automatic calendar publishing (no publish path exists and an
approval converts nothing), duplicate submission idempotence
(one receipt per candidate), wrong-account refusal, and the
registry duty (a Samkoma lock entry + matrix row, no pin taken).
"""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def mods():
    from hermes_cli import plugins as plugins_mod
    from hermes_constants import get_hermes_home

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
               for name in ("samkoma", "cli")}
    finally:
        manager.unload()
    return out


class FakeCtx:
    def __init__(self, cfg=None):
        self._cfg = cfg or {}

    def get_config(self, key, default=None):
        return self._cfg.get(key, default)


def _lock_path() -> Path:
    return (Path(__file__).resolve().parents[2]
            / "docs" / "modernization" / "integration-lock.json")


SOURCE = {"id": "src-1", "kind": "chat-export", "title": "Chat",
          "text": "Anna: Table session this Saturday at 18:00, "
                  "bring the character sheets. Ben: At the hall."}


def _candidate(mods):
    sk = mods["samkoma"]
    return sk.build_candidate(SOURCE, [
        {"name": "title", "value": "Table session",
         "quote": "Table session this Saturday"},
        {"name": "place", "value": "The longhouse hall",
         "quote": "in the longhouse hall"},
    ], kind="event", title="Table session", created_by="seat-1")


def test_status_unconfigured_is_truthful(mods):
    sk = mods["samkoma"]
    record = sk.samkoma_status(FakeCtx(), recorded_at="t")
    assert record["schema"] == "runeforge.samkoma.status.v1"
    assert record["canonical_repo"] == "hrabanazviking/RuneForgeAI-Samkoma"
    assert record["audited_head"] == sk.AUDITED_HEAD
    assert record["license"] == "GPL-3.0-only"
    assert record["enabled"] is False
    assert record["configured"] is False
    assert record["tree"]["status"] == "not_configured"
    assert record["publishes_anything"] is False
    assert record["production_ready"] is False
    assert record["connector_sync_performed"] is False


def test_status_measures_a_staged_tree(mods, tmp_path):
    sk = mods["samkoma"]
    root = tmp_path / "samkoma"
    (root / ".git" / "refs" / "heads").mkdir(parents=True)
    (root / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    (root / ".git" / "refs" / "heads" / "main").write_text(sk.AUDITED_HEAD + "\n")
    (root / "OPENAPI.json").write_text(json.dumps(
        {"paths": {"/a": {}, "/b": {}},
         "components": {"schemas": {"A": {}, "B": {}, "C": {}}}}))
    (root / "LICENSE").write_text("not the real license")
    record = sk.samkoma_status(FakeCtx({"samkoma_root": str(root)}))
    tree = record["tree"]
    assert record["configured"] is True
    assert tree["head"] == sk.AUDITED_HEAD
    assert tree["head_matches_audited"] is True
    assert tree["openapi_paths"] == 2 and tree["openapi_schemas"] == 3
    assert tree["license_matches_audited"] is False  # honest mismatch


def test_lock_records_samkoma_without_a_pin(mods):
    sk = mods["samkoma"]
    lock = json.loads(_lock_path().read_text(encoding="utf-8"))
    rows = {r["name"]: r for r in lock["engines"]}
    assert len(lock["engines"]) == 30
    row = rows["Samkoma"]
    assert row["repo"] == sk.CANONICAL_REPO
    assert row["pinned"] is None
    assert row["current_head"] == sk.AUDITED_HEAD
    assert "plugins/volmarr-core/samkoma.py" in row["adapter"]["paths"]
    assert "X.08" in row["verdict"]


def test_catalog_refuses_publish_verbs(mods):
    sk = mods["samkoma"]
    catalog = sk.operations_catalog()
    modes = {o["name"]: o["mode"] for o in catalog["operations"]}
    assert modes["candidate.preview"] == "read-only"
    assert "proposal-only" in modes["candidate.extract"]
    assert catalog["publishes_anything"] is False
    for verb in ("event.publish", "calendar.create", "task.create"):
        assert verb in catalog["publish_verbs_refused"]


def test_supported_field_needs_a_verbatim_quote(mods):
    cand = _candidate(mods)
    by_name = {f["name"]: f for f in cand["fields"]}
    assert by_name["title"]["supported"] is True
    assert by_name["place"]["supported"] is False
    assert by_name["place"]["unsupported_reasons"] == ["quote_not_in_source"]
    assert cand["is_fact"] is False and cand["published"] is False


def test_no_quote_and_missing_timezone_stay_unsupported(mods):
    sk = mods["samkoma"]
    cand = sk.build_candidate(SOURCE, [
        {"name": "host", "value": "Anna", "quote": ""},
        {"name": "starts_at", "value": "2026-11-21T18:00:00",
         "quote": "this Saturday at 18:00"},
        {"name": "ends_at", "value": "2026-11-21T21:00:00+01:00",
         "quote": "this Saturday at 18:00"},
    ])
    by_name = {f["name"]: f for f in cand["fields"]}
    assert by_name["host"]["supported"] is False
    assert "no_quote" in by_name["host"]["unsupported_reasons"]
    assert by_name["starts_at"]["supported"] is False
    assert "timezone_missing" in by_name["starts_at"]["unsupported_reasons"]
    assert by_name["ends_at"]["supported"] is True


def test_preview_flags_duplicates_and_publishes_nothing(mods):
    sk = mods["samkoma"]
    cand = _candidate(mods)
    other = dict(cand, source_id="src-2")
    preview = sk.preview_candidate(cand, existing=[other])
    assert "possible_duplicate" in preview["flags"]
    assert preview["unsupported_fields"] == ["place"]
    assert preview["is_fact"] is False and preview["published"] is False
    assert preview["status"] == "pending"


def test_review_gate_refusals_and_no_conversion(mods):
    sk = mods["samkoma"]
    cand = _candidate(mods)
    wrong = sk.evaluate_review(cand, approver_id="anna", approver_role="owner",
                               account_id="other-acct", expected_account="group-acct")
    assert wrong["approved"] is False and wrong["refusals"] == ["wrong_account"]
    role = sk.evaluate_review(cand, approver_id="anna", approver_role="guest",
                              account_id="group-acct", expected_account="group-acct")
    assert role["approved"] is False and role["refusals"] == ["role_not_authorized"]
    seat = sk.evaluate_review(cand, approver_id="seat-1", approver_role="owner",
                              account_id="group-acct", expected_account="group-acct",
                              seat_ids=("seat-1",))
    assert seat["approved"] is False
    assert seat["refusals"] == ["seat_cannot_approve_own_draft"]
    ok = sk.evaluate_review(cand, approver_id="anna", approver_role="owner",
                            account_id="group-acct", expected_account="group-acct")
    assert ok["approved"] is True and ok["refusals"] == []
    # Even a clean approval converts and publishes NOTHING here,
    # and the unsupported field stays unsupported in the record.
    assert ok["conversion_performed"] is False and ok["published"] is False
    assert ok["unsupported_fields"] == ["place"]


def test_proposal_draft_is_idempotent(mods, tmp_path):
    sk = mods["samkoma"]
    cand = _candidate(mods)
    store = tmp_path / "proposals"
    first = sk.draft_proposal(store, cand)
    second = sk.draft_proposal(store, cand)
    assert first["duplicate"] is False and second["duplicate"] is True
    assert first["idempotency_key"] == second["idempotency_key"]
    assert len(list(store.glob("*.json"))) == 1
    assert first["published"] is False and first["synced"] is False


def test_source_deletion_removes_its_proposals(mods, tmp_path):
    sk = mods["samkoma"]
    store = tmp_path / "proposals"
    sk.draft_proposal(store, _candidate(mods))
    other = sk.build_candidate({"id": "src-9", "text": "x y"}, [], title="Other")
    sk.draft_proposal(store, other)
    result = sk.respect_source_deletion(store, "src-1")
    assert result["removed"] == 1
    assert len(list(store.glob("*.json"))) == 1


def test_search_sources_is_read_only(mods):
    sk = mods["samkoma"]
    hits = sk.search_sources([SOURCE, {"id": "s2", "text": "nothing"}], "table session")
    assert [h["source_id"] for h in hits] == ["src-1"]
    assert sk.search_sources([SOURCE], "") == []


def _run_cli(mods, argv, ctx):
    cli = mods["cli"]
    parser = argparse.ArgumentParser(prog="hermes")
    sub = parser.add_subparsers(dest="command")
    volmarr_parser = sub.add_parser("volmarr")
    cli.register_cli(volmarr_parser)
    args = parser.parse_args(argv)
    return cli.health_command(args, ctx=ctx)


def test_cli_samkoma_family(mods, capsys):
    ctx = FakeCtx()
    rc = _run_cli(mods, ["volmarr", "samkoma", "status", "--json"], ctx)
    assert rc == 0
    record = json.loads(capsys.readouterr().out)
    assert record["service"] == "volmarr-samkoma"
    assert record["enabled"] is False and record["production_ready"] is False
    rc = _run_cli(mods, ["volmarr", "samkoma", "catalog", "--json"], ctx)
    assert rc == 0
    catalog = json.loads(capsys.readouterr().out)
    assert catalog["publishes_anything"] is False
    rc = _run_cli(mods, ["volmarr", "samkoma", "preview", "--json"], ctx)
    assert rc == 0
    preview = json.loads(capsys.readouterr().out)
    assert preview["published"] is False and preview["is_fact"] is False
    assert preview["unsupported_fields"] == ["place"]
    assert "synthetic" in preview["source_label"]
    rc = _run_cli(mods, ["volmarr", "samkoma"], ctx)
    assert rc == 2
    capsys.readouterr()
