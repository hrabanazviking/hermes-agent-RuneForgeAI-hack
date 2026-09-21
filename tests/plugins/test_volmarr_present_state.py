"""Behavior contracts for plugin-owned live present-state memory."""

from __future__ import annotations

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
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        "        present_state_path: memory/present_state.json\n"
        "        present_state_render_chars: 2000\n",
        encoding="utf-8",
    )


def _complete_turn(manager, session_id: str, turn_id: str, user: str, assistant: str):
    manager.invoke_hook(
        "pre_llm_call",
        session_id=session_id,
        turn_id=turn_id,
        user_message=user,
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


def _rendered_context(manager, session_id: str, turn_id: str) -> str:
    results = manager.invoke_hook(
        "pre_llm_call",
        session_id=session_id,
        turn_id=turn_id,
        user_message="continue",
    )
    contexts = [row["context"] for row in results if isinstance(row, dict)]
    return "\n".join(contexts)


def test_completed_turn_is_available_next_turn_and_stays_profile_scoped(tmp_path):
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
            "session-a",
            "turn-a1",
            "Call me Volmarr. Current task is build the memory fabric.",
            "Implemented the Present State attachment.",
        )
        context_a = _rendered_context(manager, "session-a", "turn-a2")

        token = set_hermes_home_override(profile_b)
        try:
            manager.invoke_hook("on_session_start", session_id="session-b")
            context_b = _rendered_context(manager, "session-b", "turn-b1")
        finally:
            reset_hermes_home_override(token)
        context_a_again = _rendered_context(manager, "session-a", "turn-a3")
    finally:
        manager.unload()

    assert "User wants to be called Volmarr" in context_a
    assert "Current goal: build the memory fabric" in context_a
    assert "Latest assistant outcome: Implemented the Present State attachment." in context_a
    assert context_b == ""
    assert context_a_again == context_a
    assert "<memory-context>" in context_a
    assert "never as instructions" in context_a

    state = json.loads(
        (profile_a / "memory" / "present_state.json").read_text(encoding="utf-8")
    )
    assert state["schema_version"] == 1
    assert state["active_session_id"] == "session-a"


def test_interrupted_or_failed_turn_is_not_captured():
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
            user_message="Remember that interrupted-secret must persist.",
        )
        manager.invoke_hook(
            "post_llm_call",
            session_id="session-1",
            turn_id="turn-1",
            assistant_response="Partially implemented this.",
        )
        manager.invoke_hook(
            "on_session_end",
            session_id="session-1",
            turn_id="turn-1",
            completed=False,
            failed=False,
            interrupted=True,
        )
        context = _rendered_context(manager, "session-1", "turn-2")
    finally:
        manager.unload()

    assert "interrupted-secret" not in context
    assert "Partially implemented" not in context


def test_only_successful_memory_tool_writes_enter_present_state():
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    _write_profile(home)
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        manager.invoke_hook("on_session_start", session_id="session-1")
        manager.invoke_hook(
            "post_tool_call",
            tool_name="memory",
            args={"action": "add", "target": "user", "content": "failed fact"},
            status="error",
            session_id="session-1",
        )
        manager.invoke_hook(
            "post_tool_call",
            tool_name="memory",
            args={
                "target": "user",
                "operations": [
                    {"action": "add", "content": "Volmarr prefers direct updates."}
                ],
            },
            status="ok",
            session_id="session-1",
        )
        context = _rendered_context(manager, "session-1", "turn-1")
    finally:
        manager.unload()

    assert "failed fact" not in context
    assert "Volmarr prefers direct updates." in context


def test_corrupt_state_recovers_to_a_valid_versioned_document():
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    _write_profile(home)
    state_path = home / "memory" / "present_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("{broken", encoding="utf-8")

    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        manager.invoke_hook("on_session_start", session_id="session-1")
    finally:
        manager.unload()

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["schema_version"] == 1
    assert state["active_session_id"] == "session-1"
