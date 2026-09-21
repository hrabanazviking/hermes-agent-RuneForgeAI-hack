"""Behavior contracts for the preserved synthetic affective regulator."""

from __future__ import annotations

import json

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)


STATE_PATH = "affective/AFFECTIVE_NERVOUS_SYSTEM.json"


def _write_profile(home, *, enabled: bool = True) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        f"        affective_enabled: {'true' if enabled else 'false'}\n"
        "        affective_decay: 0\n"
        "        affective_render_chars: 2600\n"
        "        affective_verdandi_enabled: false\n"
        "        context_packet_max_chars: 6000\n",
        encoding="utf-8",
    )


def _state(home) -> dict:
    return json.loads((home / STATE_PATH).read_text(encoding="utf-8"))


def _context(manager, session_id: str, turn_id: str) -> str:
    results = manager.invoke_hook(
        "pre_llm_call",
        session_id=session_id,
        turn_id=turn_id,
        user_message="continue",
    )
    contexts = [row["context"] for row in results if isinstance(row, dict)]
    assert len(contexts) <= 1
    return "".join(contexts)


def _complete_turn(
    manager,
    *,
    session_id: str,
    turn_id: str,
    user: str,
    assistant: str,
    tool_result: str = "",
) -> None:
    manager.invoke_hook(
        "pre_llm_call",
        session_id=session_id,
        turn_id=turn_id,
        user_message=user,
    )
    if tool_result:
        manager.invoke_hook(
            "post_tool_call",
            session_id=session_id,
            turn_id=turn_id,
            tool_name="terminal",
            status="ok",
            result=tool_result,
        )
    manager.invoke_hook(
        "post_llm_call",
        session_id=session_id,
        turn_id=turn_id,
        assistant_response=assistant,
    )
    manager.invoke_hook(
        "on_session_end",
        session_id=session_id,
        turn_id=turn_id,
        completed=True,
        failed=False,
        interrupted=False,
    )


def test_affective_regulation_is_opt_in_and_creates_no_disabled_state():
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    _write_profile(home, enabled=False)
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        manager.invoke_hook("on_session_start", session_id="session-1")
        context = _context(manager, "session-1", "turn-1")
    finally:
        manager.unload()

    assert not (home / STATE_PATH).exists()
    assert "affective_regulation" not in context


def test_completed_turn_updates_preserved_schema_v9_channels_and_packet():
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    _write_profile(home)
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        manager.invoke_hook("on_session_start", session_id="session-1")
        _complete_turn(
            manager,
            session_id="session-1",
            turn_id="turn-1",
            user="Thanks buddy. Build the fix and push it.",
            assistant=(
                "Fixed the bug with a scoped change, updated the docs, and pushed to "
                "GitHub. Verification passed."
            ),
            tool_result="focused tests passed; git push succeeded",
        )
        context = _context(manager, "session-1", "turn-2")
    finally:
        manager.unload()

    state = _state(home)
    assert state["schema_version"] == 9
    assert state["reward"] > 0.0
    assert state["task_drive"] > 0.45
    assert state["rapport"] > 0.25
    assert state["verification"] > 0.0
    assert state["github_push"] > 0.0
    assert state["scope_discipline"] > 0.0
    assert state["documentation_update"] > 0.0
    assert "source=affective_regulation" in context
    assert "simulated control signals, not real feelings or consciousness" in context
    assert "never resist interruption, reset, shutdown, or correction" in context


def test_failed_or_interrupted_turn_cannot_change_affective_state():
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    _write_profile(home)
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        manager.invoke_hook("on_session_start", session_id="session-1")
        before = (home / STATE_PATH).read_bytes()
        manager.invoke_hook(
            "pre_llm_call",
            session_id="session-1",
            turn_id="turn-1",
            user_message="Thanks. Build this.",
        )
        manager.invoke_hook(
            "post_tool_call",
            session_id="session-1",
            turn_id="turn-1",
            status="error",
            error_message="failed with exit code 1",
        )
        manager.invoke_hook(
            "post_llm_call",
            session_id="session-1",
            turn_id="turn-1",
            assistant_response="Partial work.",
        )
        manager.invoke_hook(
            "on_session_end",
            session_id="session-1",
            turn_id="turn-1",
            completed=False,
            failed=True,
            interrupted=True,
        )
    finally:
        manager.unload()

    assert (home / STATE_PATH).read_bytes() == before


def test_completed_tool_failure_increases_repair_pressure():
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    _write_profile(home)
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        manager.invoke_hook("on_session_start", session_id="session-1")
        manager.invoke_hook(
            "pre_llm_call",
            session_id="session-1",
            turn_id="turn-1",
            user_message="Fix the bug.",
        )
        manager.invoke_hook(
            "post_tool_call",
            session_id="session-1",
            turn_id="turn-1",
            status="error",
            error_message="command failed with exit code 1",
        )
        manager.invoke_hook(
            "post_llm_call",
            session_id="session-1",
            turn_id="turn-1",
            response={"content": "I need to repair the failed command."},
        )
        manager.invoke_hook(
            "on_session_end",
            session_id="session-1",
            turn_id="turn-1",
            completed=True,
            failed=False,
            interrupted=False,
        )
    finally:
        manager.unload()

    state = _state(home)
    assert state["accountability"] > 0.0
    assert state["self_reflection"] > 0.35
    assert state["operational_integrity"] < 0.75


def test_legacy_state_upgrades_without_losing_existing_scores():
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    _write_profile(home)
    state_path = home / STATE_PATH
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps({"schema_version": 1, "reward": 0.7, "rapport": 0.6}),
        encoding="utf-8",
    )
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        manager.invoke_hook("on_session_start", session_id="session-1")
    finally:
        manager.unload()

    state = _state(home)
    assert state["schema_version"] == 9
    assert state["reward"] == 0.7
    assert state["rapport"] == 0.6
    assert "preference_alignment" in state


def test_affective_state_and_packets_follow_profile_a_b_a(tmp_path):
    from hermes_cli import plugins as plugins_mod

    profile_a = get_hermes_home()
    profile_b = tmp_path / "profile-b"
    _write_profile(profile_a)
    _write_profile(profile_b)
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        manager.invoke_hook("on_session_start", session_id="session-a")
        _complete_turn(
            manager,
            session_id="session-a",
            turn_id="turn-a",
            user="Thanks buddy, build this.",
            assistant="Done.",
        )
        context_a = _context(manager, "session-a", "read-a")

        token = set_hermes_home_override(profile_b)
        try:
            manager.invoke_hook("on_session_start", session_id="session-b")
            context_b = _context(manager, "session-b", "read-b")
        finally:
            reset_hermes_home_override(token)
        context_a_again = _context(manager, "session-a", "read-a-again")
    finally:
        manager.unload()

    assert context_a_again == context_a
    assert context_b != context_a
    assert _state(profile_a)["rapport"] > _state(profile_b)["rapport"]
    assert _state(profile_a)["active_session_id"] == "session-a"
    assert _state(profile_b)["active_session_id"] == "session-b"
