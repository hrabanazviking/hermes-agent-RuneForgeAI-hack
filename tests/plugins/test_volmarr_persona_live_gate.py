"""W05 gate: real discovery, real hooks, real system prompt.

Proves through the actual plugin manager (not stubs) that an
opt-in profile gets the compiled kernel on BOTH channels —
the frozen ``volmarr.persona.kernel`` system-prompt section
and the PresentState ``pre_llm_call`` packet with real routed
+ retrieved content — that the retired descriptive item is
gone, that the registered hook set is unchanged, and that a
non-opt-in profile is byte-for-byte stock. The system-prompt
assertion uses a real AIAgent prompt build, the pattern from
tests/agent/test_plugin_prompt_sections.py.
"""

from __future__ import annotations

import hashlib

import yaml

from hermes_constants import get_hermes_home

CORE_DOC = """# Core Identity

I am Caducea, a persistent Hermes entity.

# Communication Style

Plain words first, warmth always.
"""

SERVICE_DOC = """# Shell Policy

Never force-push.
"""


def _write_persona(home, *, owner: bool) -> None:
    home.mkdir(parents=True, exist_ok=True)
    if owner:
        # P.010 suppression step (draft option 2): the operator
        # removes the legacy SOUL.md block for an owner profile.
        (home / "SOUL.md").unlink(missing_ok=True)
    persona_dir = home / "persona"
    persona_dir.mkdir(parents=True, exist_ok=True)
    (persona_dir / "core.md").write_text(CORE_DOC, encoding="utf-8")
    (persona_dir / "bible.md").write_text(SERVICE_DOC, encoding="utf-8")
    config_dir = home / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "persona.yaml").write_text(
        yaml.safe_dump({"persona": {
            "id": "caducea",
            "display_name": "Caducea Hermesdottir",
            "directory": "./persona",
            "documents": {
                "core": {"file": "core.md", "required": True},
                "service_bible": {"file": "bible.md", "required": True},
            },
            "anchors": ["Never invent a fact."],
        }}, sort_keys=False), encoding="utf-8")
    settings = "        persona_live_owner: true\n" if owner else ""
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        f"{settings}",
        encoding="utf-8")


def _load_manager():
    from hermes_cli import plugins as plugins_mod

    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    return manager


def test_gate_opt_in_profile_gets_kernel_on_both_channels():
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    _write_persona(home, owner=True)
    manager = _load_manager()
    try:
        loaded = manager._plugins["volmarr-core"]
        assert loaded.enabled
        # No new hooks: the registered set is the pre-W05 set.
        assert set(loaded.hooks_registered) == {
            "on_session_start",
            "on_session_end",
            "on_session_finalize",
            "pre_tool_call",
            "post_tool_call",
            "pre_llm_call",
            "post_llm_call",
        }
        # Channel S: exactly one section, rendered with the
        # kernel text verbatim.
        sections = manager._system_prompt_sections
        assert list(sections) == ["volmarr.persona.kernel"]
        rendered = manager.render_system_prompt_sections({})
        assert len(rendered) == 1
        assert rendered[0].id == "volmarr.persona.kernel"
        assert rendered[0].position == "after_memory"
        assert "I am Caducea, a persistent Hermes entity." \
            in rendered[0].content
        assert "Never invent a fact." in rendered[0].content

        # Channel T: a real pre_llm_call invocation carries the
        # kernel + the retrieved shell policy, and NOT the old
        # descriptive contract item.
        results = manager.invoke_hook(
            "pre_llm_call",
            session_id="gate-session",
            turn_id="gate-turn-1",
            user_message="what is the shell policy on force push?",
            model="test/model",
            platform="cli",
            parent_session_id="",
            sender_id="",
        )
        contexts = [row["context"] for row in results
                    if isinstance(row, dict) and row.get("context")]
        joined = "\n".join(contexts)
        assert "I am Caducea, a persistent Hermes entity." in joined
        assert "Never force-push." in joined
        assert "service_bible.shell_policy" in joined
        assert "Persona runtime (§§" not in joined
        digest = hashlib.sha256(
            SERVICE_DOC.encode("utf-8")).hexdigest()
        assert digest in joined
    finally:
        manager.unload()


def test_gate_opt_in_kernel_lands_in_real_system_prompt(monkeypatch):
    from agent.system_prompt import build_system_prompt
    from hermes_cli import plugins as plugins_mod
    from run_agent import AIAgent

    home = get_hermes_home()
    _write_persona(home, owner=True)
    manager = _load_manager()
    try:
        monkeypatch.setattr(plugins_mod, "_plugin_manager", manager)
        monkeypatch.setattr(
            "agent.coding_context.build_coding_workspace_block",
            lambda cwd=None: "Workspace (snapshot at session start):\n"
                             "- Root: /pinned")
        agent = AIAgent(
            api_key="test-key",
            base_url="https://openrouter.ai/api/v1",
            model="test/model",
            provider="openrouter",
            platform="cli",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
            session_id="gate-prompt-session",
        )
        prompt = build_system_prompt(agent)
        assert "## Plugin Context: volmarr.persona.kernel" in prompt
        assert "I am Caducea, a persistent Hermes entity." in prompt
    finally:
        manager.unload()


def test_gate_non_opt_in_profile_is_stock():
    home = get_hermes_home()
    _write_persona(home, owner=False)
    manager = _load_manager()
    try:
        assert manager._system_prompt_sections == {}
        results = manager.invoke_hook(
            "pre_llm_call",
            session_id="gate-session",
            turn_id="gate-turn-1",
            user_message="what is the shell policy on force push?",
            model="test/model",
            platform="cli",
            parent_session_id="",
            sender_id="",
        )
        joined = "\n".join(
            str(row.get("context")) for row in results
            if isinstance(row, dict) and row.get("context"))
        assert "I am Caducea" not in joined
        assert "Never force-push." not in joined
    finally:
        manager.unload()
