"""Contracts for prompt assembly order + why order matters (Slice 144).

Persona Runtime roadmap §53 (Prompt Assembly Order) and §54
(Why Order Matters): the recommended prompt order is runtime
system rules, Persona Kernel, current Persona State, relevant
persona sections, relevant long-term memory, active project
context, recent conversation context, current user message —
the character appears before transient context, and §53 is
the enforcer the §10 pinning spec designated. §54: if persona
comes after huge conversation history, recent context may
dominate; putting identity near the highest-level instructions
helps keep the model anchored. These are pure surfaces: no
prompt is assembled, nothing is injected, and no order is
reordered live. Tests load through real plugin discovery.
"""

from __future__ import annotations

import hashlib
import importlib
from pathlib import Path

import pytest
import yaml

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)

ENABLED = {"persona_runtime_enabled": True}

CORE_DOC = """# Core Identity

Caducea is a counselor who lives in the longhouse terminal.
Caducea gives advice carefully.
"""

OTHER_CORE_DOC = """# Core Identity

Other is a smith who lives in the far forge.
Other gives advice bluntly.
"""

MEMORY_POLICY_DOC = """# Resolving Memory Conflicts

When memories conflict, the newer verified record wins.
"""

DOCS = {
    "core": ("core.md", CORE_DOC),
    "memory_policy": ("memory_policy.md", MEMORY_POLICY_DOC),
}

ASSEMBLY = [
    {"slot": "runtime_system_rules", "source": "runtime",
     "status": "external"},
    {"slot": "persona_kernel", "source": "compiled_kernel",
     "status": "banked"},
    {"slot": "current_persona_state", "source": "persona_state",
     "status": "banked"},
    {"slot": "relevant_persona_sections",
     "source": "persona_retrieval", "status": "banked"},
    {"slot": "relevant_long_term_memory",
     "source": "memory_subsystem", "status": "external"},
    {"slot": "active_project_context", "source": "project_context",
     "status": "external"},
    {"slot": "recent_conversation_context",
     "source": "conversation_context", "status": "external"},
    {"slot": "current_user_message", "source": "caller_input",
     "status": "external"},
]

SLOT_NAMES = [row["slot"] for row in ASSEMBLY]

REASONS = [
    {"reason": "recent_context_may_dominate",
     "statement": "If persona comes after huge conversation "
                  "history, recent context may dominate."},
    {"reason": "identity_near_highest_instructions_anchors",
     "statement": "Putting identity near the highest-level "
                  "instructions helps keep the model anchored."},
]


class _Ctx:
    def __init__(self, config=None):
        self._config = dict(config or {})

    def get_config(self, key, default=None):
        return self._config.get(key, default)


def _write_profile(home) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [volmarr-core]\n", encoding="utf-8"
    )


def _load_modules():
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    _write_profile(home)
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-core"]
        package = loaded.module.__package__
        return (
            manager,
            importlib.import_module(f"{package}.persona_runtime"),
            importlib.import_module(f"{package}.identity"),
        )
    except Exception:
        manager.unload()
        raise


def _write_persona(home: Path, persona_id: str = "caducea",
                   core_doc: str = CORE_DOC) -> None:
    persona_dir = home / "persona"
    persona_dir.mkdir(parents=True, exist_ok=True)
    docs = dict(DOCS)
    docs["core"] = ("core.md", core_doc)
    for role, (name, text) in docs.items():
        (persona_dir / name).write_text(text, encoding="utf-8")
    persona = {
        "id": persona_id,
        "display_name": "Caducea Hermesdottir",
        "directory": "./persona",
        "version": "1.4.2",
        "documents": {
            role: {"file": name, "required": True}
            for role, (name, _text) in docs.items()
        },
    }
    config_dir = home / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "persona.yaml").write_text(
        yaml.safe_dump({"persona": persona}, sort_keys=False),
        encoding="utf-8")


def _hashes(home: Path) -> dict[str, str]:
    return {
        str(path.relative_to(home)):
            hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(home.rglob("*"))
        if path.is_file() and "entity" not in path.parts
    }


def test_assembly_order_and_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        order = runtime.prompt_assembly_order()
        order[0]["slot"] = "x"
        fresh_order = runtime.prompt_assembly_order()
        slots = runtime.prompt_assembly_slots()
        slots.append("x")
        contract = runtime.prompt_assembly_contract()
    finally:
        mods[0].unload()
    assert fresh_order == ASSEMBLY
    assert runtime.prompt_assembly_slots() == SLOT_NAMES
    assert list(runtime.PROMPT_ASSEMBLY_SLOTS) == SLOT_NAMES
    # §53 enforces the §10 pinning: kernel at position 1,
    # directly under the runtime system rules.
    assert runtime.PINNING_ORDER[1] == "persona_kernel"
    assert contract == {
        "name": "PersonaPromptAssemblyOrder",
        "slots": ASSEMBLY,
        "kernel_position": 1,
        "enforces_pinning": "section_10",
        "character_before_transient_context": True,
        "assembles_prompt": False,
        "injects": False,
        "wired_into_turn_path": False,
    }
    assert list(runtime.CHARACTER_SLOTS) == [
        "persona_kernel", "current_persona_state",
        "relevant_persona_sections"]
    assert list(runtime.TRANSIENT_CONTEXT_SLOTS) == [
        "relevant_long_term_memory", "active_project_context",
        "recent_conversation_context", "current_user_message"]


def test_assembly_plan_full_order():
    mods = _load_modules()
    runtime = mods[1]
    try:
        plan = runtime.prompt_assembly_plan()
    finally:
        mods[0].unload()
    assert plan == {
        "slots": ASSEMBLY,
        "slot_names": SLOT_NAMES,
        "kernel_position": 1,
        "character_before_transient_context": True,
        "assembles": False,
    }


def test_assembly_plan_subsequence():
    mods = _load_modules()
    runtime = mods[1]
    try:
        plan = runtime.prompt_assembly_plan([
            "runtime_system_rules", "persona_kernel",
            "current_user_message"])
        no_kernel = runtime.prompt_assembly_plan([
            "runtime_system_rules", "current_user_message"])
    finally:
        mods[0].unload()
    assert plan["slot_names"] == [
        "runtime_system_rules", "persona_kernel",
        "current_user_message"]
    assert plan["slots"] == [ASSEMBLY[0], ASSEMBLY[1], ASSEMBLY[7]]
    assert plan["kernel_position"] == 1
    assert plan["character_before_transient_context"] is True
    assert no_kernel["kernel_position"] is None
    assert no_kernel["character_before_transient_context"] is False


def test_assembly_plan_malformed_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for bad in ("slots", [], ["unknown_slot"],
                    ["persona_kernel", "persona_kernel"],
                    # Out of canonical order is refused by
                    # the §53 plan (evaluation is §54's job).
                    ["current_user_message", "persona_kernel"],
                    ["persona_kernel", 3], [None]):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.prompt_assembly_plan(bad)
    finally:
        mods[0].unload()


def test_order_matters_reasons_and_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        reasons = runtime.order_matters_reasons()
        reasons[0]["reason"] = "x"
        fresh = runtime.order_matters_reasons()
        contract = runtime.order_matters_contract()
    finally:
        mods[0].unload()
    assert fresh == REASONS
    assert list(runtime.ORDER_MATTERS_REASONS) == [
        (row["reason"], row["statement"]) for row in REASONS]
    assert contract == {
        "name": "PersonaOrderMatters",
        "reasons": REASONS,
        "kernel_must_precede_transient_context": True,
        "anchored_kernel_position": 1,
        "evaluates_only": True,
        "reorders_live_prompt": False,
        "injects": False,
    }


def test_evaluate_canonical_order_is_anchored():
    mods = _load_modules()
    runtime = mods[1]
    try:
        result = runtime.evaluate_prompt_order(list(SLOT_NAMES))
    finally:
        mods[0].unload()
    assert result == {
        "slots": SLOT_NAMES,
        "kernel_position": 1,
        "character_before_transient_context": True,
        "anchored": True,
        "risks": [],
    }


def test_evaluate_dominated_and_buried_orders():
    mods = _load_modules()
    runtime = mods[1]
    try:
        dominated = runtime.evaluate_prompt_order([
            "runtime_system_rules", "recent_conversation_context",
            "persona_kernel", "current_user_message"])
        buried = runtime.evaluate_prompt_order([
            "runtime_system_rules", "relevant_long_term_memory",
            "active_project_context", "persona_kernel"])
    finally:
        mods[0].unload()
    # Persona after huge conversation history: recent
    # context may dominate (§54's first reason).
    assert dominated["kernel_position"] == 2
    assert dominated["character_before_transient_context"] is False
    assert dominated["anchored"] is False
    assert dominated["risks"] == [
        "recent_context_may_dominate",
        "identity_not_near_highest_instructions"]
    # Kernel buried under transient context, though not
    # after the conversation itself: not near the
    # highest-level instructions.
    assert buried["kernel_position"] == 3
    assert buried["character_before_transient_context"] is False
    assert buried["anchored"] is False
    assert buried["risks"] == [
        "identity_not_near_highest_instructions"]


def test_evaluate_missing_kernel_and_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        missing = runtime.evaluate_prompt_order([
            "runtime_system_rules", "current_user_message"])
        for bad in ("order", [], ["unknown_slot"],
                    ["persona_kernel", "persona_kernel"],
                    ["persona_kernel", 3]):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.evaluate_prompt_order(bad)
    finally:
        mods[0].unload()
    assert missing == {
        "slots": ["runtime_system_rules", "current_user_message"],
        "kernel_position": None,
        "character_before_transient_context": False,
        "anchored": False,
        "risks": ["persona_kernel_missing"],
    }


def test_packet_determinism_and_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        home = get_hermes_home()
        _write_persona(home)
        before = _hashes(home)
        plan = runtime.prompt_assembly_plan()
        evaluation = runtime.evaluate_prompt_order(
            runtime.prompt_assembly_slots())
        first = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        second = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        after = _hashes(home)
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            mods[2].IdentityStore(_Ctx()).ensure()
            _write_persona(
                profile_b, persona_id="other",
                core_doc=OTHER_CORE_DOC)
            other_plan = runtime.prompt_assembly_plan()
        finally:
            reset_hermes_home_override(token)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert before == after
    # The pure surfaces are profile-independent: the same
    # canonical plan stands in either profile.
    assert plan == other_plan
    assert evaluation["anchored"] is True
    assert first[0].content == second[0].content == third[0].content
    assert len(first) == 1
    content = first[0].content
    assert "§§3-60" in content
    assert "§53 prompt assembly" in content
    assert "kernel at position 1" in content
    assert "character before transient context" in content
    assert "assembles no prompt" in content
    assert "§54 order matters" in content
    assert "recent context may dominate" in content
    assert "helps keep the model anchored" in content
    # The packet names the contracts only — never canonical
    # persona text.
    assert "longhouse terminal" not in content
