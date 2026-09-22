"""Contracts for background routines delegated to Hermes cron."""

from __future__ import annotations

import argparse
import json

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)


def _write_profile(home) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n",
        encoding="utf-8",
    )


def _load_manager():
    from hermes_cli import plugins as plugins_mod

    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    return manager


def _command(manager, argv: list[str]):
    command = manager._cli_commands["volmarr"]
    parser = argparse.ArgumentParser()
    command["setup_fn"](parser)
    args = parser.parse_args(argv)
    return command["handler_fn"], args


def _run_json(manager, argv: list[str], capsys) -> tuple[int, dict]:
    handler, args = _command(manager, argv)
    code = handler(args)
    output = capsys.readouterr()
    assert output.err == ""
    return code, json.loads(output.out)


def _stored_jobs(home) -> list[dict]:
    payload = json.loads((home / "cron" / "jobs.json").read_text(encoding="utf-8"))
    return payload["jobs"]


def test_install_is_explicit_paused_and_idempotent(capsys):
    home = get_hermes_home()
    _write_profile(home)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
        assert not (home / "cron" / "jobs.json").exists()
        code, before = _run_json(manager, ["routines", "status", "--json"], capsys)
        assert code == 1
        assert before["status"] == "uninstalled"
        code, installed = _run_json(
            manager,
            ["routines", "install", "--json"],
            capsys,
        )
        assert code == 0
        first_jobs = _stored_jobs(home)
        code, installed_again = _run_json(
            manager,
            ["routines", "install", "--json"],
            capsys,
        )
        assert code == 0
        second_jobs = _stored_jobs(home)
    finally:
        manager.unload()

    assert installed["status"] == "installed_paused"
    assert installed["definition_current"] is True
    assert installed_again["job_id"] == installed["job_id"]
    assert len(first_jobs) == len(second_jobs) == 1
    assert first_jobs[0]["id"] == second_jobs[0]["id"]
    assert first_jobs[0]["enabled"] is False
    assert first_jobs[0]["no_agent"] is True
    assert first_jobs[0]["prompt"] == ""
    assert first_jobs[0]["script"] == "volmarr_frequent_continuity.py"
    assert first_jobs[0]["schedule_display"] == "every 10m"


def test_install_activate_resumes_existing_job(capsys):
    home = get_hermes_home()
    _write_profile(home)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
        _run_json(manager, ["routines", "install", "--json"], capsys)
        code, active = _run_json(
            manager,
            ["routines", "install", "--activate", "--json"],
            capsys,
        )
    finally:
        manager.unload()

    assert code == 0
    assert active["status"] == "installed_active"
    assert _stored_jobs(home)[0]["enabled"] is True


def test_install_repairs_definition_drift_without_activating(capsys):
    home = get_hermes_home()
    _write_profile(home)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
        _run_json(manager, ["routines", "install", "--json"], capsys)
        jobs_path = home / "cron" / "jobs.json"
        payload = json.loads(jobs_path.read_text(encoding="utf-8"))
        payload["jobs"][0]["script"] = "wrong.py"
        jobs_path.write_text(json.dumps(payload), encoding="utf-8")
        code, repaired = _run_json(
            manager,
            ["routines", "install", "--json"],
            capsys,
        )
    finally:
        manager.unload()

    assert code == 0
    assert repaired["status"] == "installed_paused"
    assert _stored_jobs(home)[0]["script"] == "volmarr_frequent_continuity.py"
    assert _stored_jobs(home)[0]["enabled"] is False


def test_frequent_run_pulses_and_counts_pending_goals(capsys):
    home = get_hermes_home()
    _write_profile(home)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="one")
        from tools.registry import registry

        created = json.loads(
            registry.dispatch(
                "goal_create",
                {"title": "Active work", "priority": 80},
                scope=manager.scope_key,
            )
        )
        registry.dispatch(
            "goal_update",
            {"goal_id": created["goal_id"], "status": "active"},
            scope=manager.scope_key,
        )
        registry.dispatch(
            "goal_create",
            {"title": "Planned work", "priority": 40},
            scope=manager.scope_key,
        )
        code, report = _run_json(
            manager,
            ["routines", "run", "--kind", "frequent", "--json"],
            capsys,
        )
    finally:
        manager.unload()

    assert code == 0
    assert report["success"] is True
    assert report["heartbeat_sequence"] == 1
    assert report["active_goals"] == 1
    assert report["planned_goals"] == 1
    assert report["blocked_goals"] == 0


def test_routine_installation_is_profile_scoped(capsys, tmp_path):
    profile_a = get_hermes_home()
    profile_b = tmp_path / "profile-b"
    _write_profile(profile_a)
    _write_profile(profile_b)
    manager = _load_manager()
    try:
        manager.invoke_hook("on_session_start", session_id="a")
        _, installed_a = _run_json(
            manager,
            ["routines", "install", "--json"],
            capsys,
        )
        token = set_hermes_home_override(profile_b)
        try:
            manager.invoke_hook("on_session_start", session_id="b")
            _, before_b = _run_json(
                manager,
                ["routines", "status", "--json"],
                capsys,
            )
            _, installed_b = _run_json(
                manager,
                ["routines", "install", "--json"],
                capsys,
            )
        finally:
            reset_hermes_home_override(token)
        _, restored_a = _run_json(
            manager,
            ["routines", "status", "--json"],
            capsys,
        )
    finally:
        manager.unload()

    assert before_b["status"] == "uninstalled"
    assert installed_a["job_id"] != installed_b["job_id"]
    assert restored_a["job_id"] == installed_a["job_id"]
    assert (profile_a / "scripts" / "volmarr_frequent_continuity.py").is_file()
    assert (profile_b / "scripts" / "volmarr_frequent_continuity.py").is_file()
