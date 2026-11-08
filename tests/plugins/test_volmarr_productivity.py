"""W10/N2 productivity: project packets, handoffs, publish guard.

Roadmap section 21 asks for external project context packets
retrieved live from a repo's current README/ROADMAP/CAMPAIGN_STATE
rather than stale hardcoded facts, one write authority per
checkout (a patch may be prepared only OUTSIDE the target repo),
a task-handoff schema shared with the Mythic Engineering flow,
and no publication without the permitted workflow. These
contracts pin that slice: packets are measured from disk (paths,
sizes, SHA-256, HEAD from .git), missing files are named never
invented, patch output inside the target repo is refused, the
handoff schema validates by name, and publish without an
explicit approval flag is refused through the capability policy.
CLI tests drive the real ``hermes volmarr productivity`` family.
"""

from __future__ import annotations

import argparse
import hashlib
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
               for name in ("project_context", "task_handoff", "cli")}
    finally:
        manager.unload()
    return out


NOW = "2026-11-08T05:10:00-05:00"
HEAD_SHA = "a" * 40


def _repo(tmp_path: Path, *, head_mode: str = "loose") -> Path:
    repo = tmp_path / "proj"
    (repo / ".git" / "refs" / "heads").mkdir(parents=True)
    (repo / "README.md").write_text("# Proj\n", encoding="utf-8")
    (repo / "ROADMAP_X.md").write_text("road\n", encoding="utf-8")
    (repo / "CAMPAIGN_STATE.md").write_text("state\n", encoding="utf-8")
    if head_mode == "loose":
        (repo / ".git" / "HEAD").write_text(
            "ref: refs/heads/main\n", encoding="utf-8")
        (repo / ".git" / "refs" / "heads" / "main").write_text(
            HEAD_SHA + "\n", encoding="utf-8")
    elif head_mode == "packed":
        (repo / ".git" / "HEAD").write_text(
            "ref: refs/heads/main\n", encoding="utf-8")
        (repo / ".git" / "packed-refs").write_text(
            f"{HEAD_SHA} refs/heads/main\n", encoding="utf-8")
    elif head_mode == "detached":
        (repo / ".git" / "HEAD").write_text(
            HEAD_SHA + "\n", encoding="utf-8")
    return repo


def test_packet_measures_live_files_and_head(mods, tmp_path):
    pc = mods["project_context"]
    repo = _repo(tmp_path)
    packet = pc.build_project_packet(repo, recorded_at=NOW)
    assert packet["schema"] == "runeforge.project-context.v1"
    assert packet["head"] == HEAD_SHA
    assert packet["missing"] == []
    by_kind = {row["kind"]: row for row in packet["sources"]}
    assert set(by_kind) == {"readme", "roadmap", "campaign_state"}
    readme = repo / "README.md"
    assert by_kind["readme"]["path"] == "README.md"
    assert by_kind["readme"]["size_bytes"] == readme.stat().st_size
    assert by_kind["readme"]["sha256"] == hashlib.sha256(
        readme.read_bytes()).hexdigest()
    assert packet["provenance"]["recorded_at"] == NOW


def test_packet_head_from_packed_refs_and_detached(mods, tmp_path):
    pc = mods["project_context"]
    repo_p = tmp_path / "packed"
    repo_p.mkdir()
    made = _repo(repo_p, head_mode="packed")
    assert pc.build_project_packet(made, recorded_at=NOW)["head"] == HEAD_SHA
    repo_d = tmp_path / "detached"
    repo_d.mkdir()
    made_d = _repo(repo_d, head_mode="detached")
    assert pc.build_project_packet(made_d, recorded_at=NOW)["head"] == HEAD_SHA


def test_packet_names_missing_files_never_invents(mods, tmp_path):
    pc = mods["project_context"]
    repo = tmp_path / "bare"
    (repo / ".git").mkdir(parents=True)
    (repo / ".git" / "HEAD").write_text(HEAD_SHA + "\n", encoding="utf-8")
    (repo / "README.md").write_text("only\n", encoding="utf-8")
    packet = pc.build_project_packet(repo, recorded_at=NOW)
    assert [row["kind"] for row in packet["sources"]] == ["readme"]
    assert packet["missing"] == ["roadmap", "campaign_state"]


def test_packet_refuses_missing_repo(mods, tmp_path):
    pc = mods["project_context"]
    with pytest.raises(pc.ProjectContextError) as exc:
        pc.build_project_packet(tmp_path / "nope", recorded_at=NOW)
    assert exc.value.name == "unavailable"
    target = tmp_path / "afile"
    target.write_text("x", encoding="utf-8")
    with pytest.raises(pc.ProjectContextError):
        pc.build_project_packet(target, recorded_at=NOW)


def test_patch_output_inside_target_repo_refused(mods, tmp_path):
    pc = mods["project_context"]
    repo = _repo(tmp_path)
    inside = repo / "prep" / "patch.diff"
    with pytest.raises(pc.ProjectContextError) as exc:
        pc.write_patch_preparation(
            repo, inside, content="diff", recorded_at=NOW)
    assert "patch_output_inside_target_repo" in exc.value.detail
    assert not inside.exists()
    assert not (repo / "prep").exists()
    with pytest.raises(pc.ProjectContextError):
        pc.resolve_patch_output(repo, repo)


def test_patch_output_outside_writes_receipt_only(mods, tmp_path):
    pc = mods["project_context"]
    repo = _repo(tmp_path)
    before = pc.build_project_packet(repo, recorded_at=NOW)
    outside = tmp_path / "prep-out" / "patch.diff"
    receipt = pc.write_patch_preparation(
        repo, outside, content="diff-body", recorded_at=NOW)
    assert outside.read_text(encoding="utf-8") == "diff-body"
    assert receipt["sha256"] == hashlib.sha256(b"diff-body").hexdigest()
    assert receipt["target_head"] == HEAD_SHA
    after = pc.build_project_packet(repo, recorded_at=NOW)
    assert after["sources"] == before["sources"]
    assert after["head"] == before["head"]


def _handoff(th):
    return th.new_handoff(
        handoff_id="h-1", repo="proj",
        intent="Ship the slice",
        invariants=["README untouched", "one writer per checkout"],
        tasks=[{"id": "t-1", "title": "Build", "status": "done"},
               {"id": "t-2", "title": "Verify", "status": "planned"}],
        evidence=[{"kind": "test-log", "ref": "~/team02-w10.log"}],
        ledger=[{"entry": "W10 slice prepared"}],
    )


def test_handoff_valid_and_envelope_provenance(mods):
    th = mods["task_handoff"]
    record = _handoff(th)
    assert th.validate_handoff(record) == []
    envelope = th.handoff_envelope(record, recorded_at=NOW)
    assert envelope["status"] == "completed"
    assert envelope["provenance"]["source_ref"] == "handoff:h-1"
    assert envelope["outputs"]["intent"] == "Ship the slice"


def test_handoff_validation_refuses_by_name(mods):
    th = mods["task_handoff"]
    record = _handoff(th)
    bad = dict(record, intent="  ")
    assert "intent_empty" in th.validate_handoff(bad)
    bad = dict(record, invariants=[])
    assert "invariants_invalid" in th.validate_handoff(bad)
    bad = json.loads(json.dumps(record))
    bad["tasks"][0]["status"] = "shipped"
    assert any(p.startswith("task_status_unknown:t-1")
               for p in th.validate_handoff(bad))
    bad = json.loads(json.dumps(record))
    bad["evidence"] = [{"kind": "test-log"}]
    assert "evidence_ref_required:test-log" in th.validate_handoff(bad)
    bad = json.loads(json.dumps(record))
    del bad["ledger"]
    assert th.validate_handoff(bad) == ["missing_field:ledger"]
    with pytest.raises(th.HandoffError):
        th.require_handoff({"schema": "nope"})


def test_publish_guard_refuses_without_approval(mods):
    th = mods["task_handoff"]
    decision = th.guard_publish(caller="yrsa", data_owner="yrsa")
    assert not decision["allowed"]
    assert "write_action_requires_approval" in decision["reasons"]
    assert "side_effect_service_requires_approval" in decision["reasons"]
    with pytest.raises(th.HandoffError) as exc:
        th.require_publish(caller="yrsa", data_owner="yrsa")
    assert exc.value.name == "unauthorized"


def test_publish_guard_approved_local_allowed_public_private_refused(mods):
    th = mods["task_handoff"]
    ok = th.guard_publish(
        caller="yrsa", data_owner="yrsa", approved=True)
    assert ok["allowed"], ok["reasons"]
    leak = th.guard_publish(
        caller="yrsa", data_owner="yrsa", approved=True,
        data_class="local-private", destination="public")
    assert not leak["allowed"]
    assert "privacy_travel_refused:local-private->public" in leak["reasons"]
    cross = th.guard_publish(
        caller="yrsa", data_owner="volmarr", approved=False)
    assert not cross["allowed"]


class _Ctx:
    def __init__(self, config=None):
        self._config = dict(config or {})

    def get_config(self, key, default=None):
        return self._config.get(key, default)


def _run_cli(mods, argv):
    cli = mods["cli"]
    parser = argparse.ArgumentParser(prog="hermes")
    sub = parser.add_subparsers(dest="command")
    volmarr_parser = sub.add_parser("volmarr")
    cli.register_cli(volmarr_parser)
    args = parser.parse_args(argv)
    return cli.health_command(args, ctx=_Ctx())


def test_cli_productivity_packet_and_publish_check(mods, tmp_path, capsys):
    repo = _repo(tmp_path)
    rc = _run_cli(mods, ["volmarr", "productivity", "packet",
                         "--repo", str(repo), "--json"])
    assert rc == 0
    packet = json.loads(capsys.readouterr().out)
    assert packet["head"] == HEAD_SHA
    assert packet["missing"] == []
    rc = _run_cli(mods, ["volmarr", "productivity", "publish-check",
                         "--caller", "yrsa", "--data-owner", "yrsa"])
    assert rc == 1
    decision = json.loads(capsys.readouterr().out)
    assert not decision["allowed"]
    rc = _run_cli(mods, ["volmarr", "productivity", "publish-check",
                         "--caller", "yrsa", "--data-owner", "yrsa",
                         "--approved"])
    assert rc == 0
    capsys.readouterr()


def test_cli_productivity_bridge_status_honest(mods, capsys):
    rc = _run_cli(mods, ["volmarr", "productivity", "bridge-status",
                         "--json"])
    assert rc == 0
    record = json.loads(capsys.readouterr().out)
    assert record["samtal"]["service"] == "volmarr-samtal-bridge"
    assert record["samtal"]["availability"] == "contract-implemented"
    assert record["live_connection"] == "not-claimed"
