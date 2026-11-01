"""Contracts for history compression + long-term design (Slice 145).

Persona Runtime roadmap §55 (Conversation History Compression)
and §56 (Long-Term Conversation Design): do not endlessly
append messages — a conversation is carried as a recent
verbatim window (the roadmap's example: the last 8–20
messages) plus structured conversation state plus episodic
summaries plus retrieved older memories, which makes
conversations effectively unlimited. §56: the model should
never need the entire conversation history to remain itself —
identity lives in persona, history lives in memory, task
state lives in project/context, and the conversation window
handles immediacy. These are pure surfaces: no live history
is compressed, nothing is summarised, and no memory is
retrieved. Tests load through real plugin discovery.
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

COMPONENTS = [
    {"component": "recent_verbatim_window",
     "owner": "conversation_context", "status": "external"},
    {"component": "structured_conversation_state",
     "owner": "trait_state_separation", "status": "banked"},
    {"component": "episodic_summaries",
     "owner": "summary_claim_classification", "status": "banked"},
    {"component": "retrieved_older_memories",
     "owner": "memory_subsystem", "status": "external"},
]

COMPONENT_NAMES = [row["component"] for row in COMPONENTS]

PLACEMENTS = [
    {"concern": "identity", "lives_in": "persona",
     "owner": "persona_documents", "status": "banked"},
    {"concern": "history", "lives_in": "memory",
     "owner": "memory_subsystem", "status": "external"},
    {"concern": "task_state", "lives_in": "project_context",
     "owner": "project_context", "status": "external"},
    {"concern": "immediacy", "lives_in": "conversation_window",
     "owner": "conversation_context", "status": "external"},
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


def test_components_and_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        components = runtime.compression_components()
        components[0]["component"] = "x"
        fresh = runtime.compression_components()
        contract = runtime.compression_contract()
    finally:
        mods[0].unload()
    assert fresh == COMPONENTS
    assert list(runtime.COMPRESSION_COMPONENT_NAMES) == COMPONENT_NAMES
    assert runtime.RECENT_WINDOW_MIN == 8
    assert runtime.RECENT_WINDOW_MAX == 20
    assert contract == {
        "name": "PersonaHistoryCompression",
        "components": COMPONENTS,
        "recent_window_min": 8,
        "recent_window_max": 20,
        "endless_appending": False,
        "effectively_unlimited": True,
        "summary_guard": "section_25",
        "state_separation": "section_26",
        "feeds_prompt_slot": "recent_conversation_context",
        "compresses_live_history": False,
        "summarizes": False,
        "retrieves_memories": False,
    }
    # The compressed recent window is exactly what the §53
    # prompt order carries as recent conversation context.
    assert "recent_conversation_context" in runtime.PROMPT_ASSEMBLY_SLOTS


def test_compression_plan_default_window():
    mods = _load_modules()
    runtime = mods[1]
    try:
        plan = runtime.compression_plan(100)
    finally:
        mods[0].unload()
    assert plan == {
        "total_messages": 100,
        "window_capacity": 20,
        "verbatim_messages": 20,
        "compressed_messages": 80,
        "components": COMPONENTS,
        "appends_endlessly": False,
        "compresses": False,
    }


def test_compression_plan_custom_window_and_short_conversation():
    mods = _load_modules()
    runtime = mods[1]
    try:
        custom = runtime.compression_plan(30, 8)
        short = runtime.compression_plan(5, 8)
        band_edges = runtime.compression_plan(20, 20)
    finally:
        mods[0].unload()
    assert custom["verbatim_messages"] == 8
    assert custom["compressed_messages"] == 22
    # A conversation shorter than the window stays fully
    # verbatim; nothing needs carrying yet.
    assert short["verbatim_messages"] == 5
    assert short["compressed_messages"] == 0
    assert band_edges["verbatim_messages"] == 20
    assert band_edges["compressed_messages"] == 0


def test_compression_plan_zero_messages():
    mods = _load_modules()
    runtime = mods[1]
    try:
        plan = runtime.compression_plan(0)
    finally:
        mods[0].unload()
    assert plan["total_messages"] == 0
    assert plan["verbatim_messages"] == 0
    assert plan["compressed_messages"] == 0


def test_compression_plan_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for bad_total in (-1, "100", 2.5, True, None):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.compression_plan(bad_total)
        for bad_window in (7, 21, 0, "20", 8.0, False):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.compression_plan(30, bad_window)
    finally:
        mods[0].unload()


def test_long_term_design_and_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        design = runtime.long_term_design()
        design[0]["concern"] = "x"
        fresh = runtime.long_term_design()
        contract = runtime.long_term_design_contract()
    finally:
        mods[0].unload()
    assert fresh == PLACEMENTS
    assert list(runtime.LONG_TERM_CONCERNS) == [
        row["concern"] for row in PLACEMENTS]
    assert contract == {
        "name": "PersonaLongTermConversationDesign",
        "placements": PLACEMENTS,
        "needs_entire_history_to_remain_itself": False,
        "compression": "section_55",
        "stores_identity": False,
        "stores_history": False,
        "stores_task_state": False,
        "injects": False,
    }


def test_placement_for_each_concern():
    mods = _load_modules()
    runtime = mods[1]
    try:
        found = [runtime.placement_for(row["concern"])
                 for row in PLACEMENTS]
    finally:
        mods[0].unload()
    assert found == PLACEMENTS


def test_placement_for_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for bad in ("persona", "unknown", "", None, 3, ["identity"]):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.placement_for(bad)
    finally:
        mods[0].unload()


def test_packet_determinism_and_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        home = get_hermes_home()
        _write_persona(home)
        before = _hashes(home)
        plan = runtime.compression_plan(100)
        placement = runtime.placement_for("identity")
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
            other_plan = runtime.compression_plan(100)
            other_placement = runtime.placement_for("identity")
        finally:
            reset_hermes_home_override(token)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert before == after
    # The pure surfaces are profile-independent: the same
    # plan and placement stand in either profile.
    assert plan == other_plan
    assert placement == other_placement
    assert first[0].content == second[0].content == third[0].content
    assert len(first) == 1
    content = first[0].content
    assert "§§3-84" in content
    assert "§55 history compression" in content
    assert "never endlessly" in content
    assert "§56" in content
    assert "long-term design: identity lives in" in content
    assert "never needs the entire" in content
    # The packet names the contracts only — never canonical
    # persona text.
    assert "longhouse terminal" not in content
