"""Contracts for persona drift defenses + precedence (Slice 129).

Persona Runtime roadmap §23 (Conversation Drift Problem) and
§24 (Do Not Derive Character From Chat History): long
conversations create seven named drift dangers, each with
an explicit defense grounded in the surfaces already banked
(§10 kernel pinning, §7 verbatim, §§15/16 never-evict,
§§17/18 anchors) or standing honestly as a contract rule;
and conversation history may affect current mood, immediate
context, and recent events, but must never redefine
foundational personality — canonical persona outranks
conversational drift under the §24 priority (PERSONA CORE >
RELATIONSHIP MODEL > SERVICE BIBLE > long-term memory >
current conversation > temporary emotional state). These
are pure contract surfaces: no conversation is monitored.
Tests load through real plugin discovery.
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

# Relationship Authority

Volmarr's word outranks Caducea's counsel in his own house.
"""

SERVICE_DOC = """# Shell Policy

Run only the commands the task names.
"""

DOCS = {
    "core": ("core.md", CORE_DOC),
    "service_bible": ("service.md", SERVICE_DOC),
}

DANGERS = [
    "recent_message_dominance",
    "summary_mutation",
    "context_truncation",
    "assistant_self_imitation",
    "memory_contamination",
    "user_mood_overfitting",
    "temporary_roleplay_overriding_identity",
]

TIERS = [
    "persona_core",
    "relationship_model",
    "service_bible",
    "long_term_memory",
    "current_conversation",
    "temporary_emotional_state",
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


def _write_persona(home: Path) -> None:
    persona_dir = home / "persona"
    persona_dir.mkdir(parents=True, exist_ok=True)
    for role, (name, text) in DOCS.items():
        (persona_dir / name).write_text(text, encoding="utf-8")
    persona = {
        "id": "caducea",
        "display_name": "Caducea Hermesdottir",
        "directory": "./persona",
        "documents": {
            role: {"file": name, "required": True}
            for role, (name, _text) in DOCS.items()
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


def test_drift_defenses_seven_in_roadmap_order_grounded():
    mods = _load_modules()
    runtime = mods[1]
    try:
        rows = runtime.drift_defenses()
        # Mutating a returned row must not poison the contract.
        rows[0]["defense"] = "tampered"
        fresh = runtime.drift_defenses()
    finally:
        mods[0].unload()
    assert runtime.drift_dangers() == DANGERS
    assert list(runtime.DRIFT_DANGERS) == DANGERS
    assert [row["danger"] for row in fresh] == DANGERS
    for row in fresh:
        assert row["defense"] and row["defense"] != "tampered"
        assert row["kind"] in (
            "mechanism", "rule", "mechanism_and_rule")
        assert row["grounding"]
        assert row["description"]
    by_danger = {row["danger"]: row for row in fresh}
    # Each defense is grounded in the banked surface that
    # actually does (or states) the work — not invented.
    assert "§10" in by_danger["recent_message_dominance"]["grounding"]
    assert by_danger["recent_message_dominance"]["kind"] == "mechanism"
    assert "§7" in by_danger["summary_mutation"]["grounding"]
    assert "§19" in by_danger["summary_mutation"]["grounding"]
    assert "§16" in by_danger["context_truncation"]["grounding"]
    assert by_danger["context_truncation"]["kind"] == "mechanism"
    # Self-imitation and memory contamination stand as
    # contract rules in this layer, labelled honestly.
    assert by_danger["assistant_self_imitation"]["kind"] == "rule"
    assert by_danger["memory_contamination"]["kind"] == "rule"
    assert "§67" in by_danger["memory_contamination"]["grounding"]
    assert "§24" in by_danger["user_mood_overfitting"]["grounding"]
    assert "§§17/18" in (
        by_danger["temporary_roleplay_overriding_identity"]["grounding"])


def test_precedence_order_exact_with_document_role_mapping():
    mods = _load_modules()
    runtime = mods[1]
    try:
        rows = runtime.precedence_order()
    finally:
        mods[0].unload()
    assert runtime.precedence_tiers() == TIERS
    assert list(runtime.PRECEDENCE_TIERS) == TIERS
    assert rows == [
        {"tier": "persona_core", "rank": 0, "name": "PERSONA CORE",
         "document_role": "core", "canonical": True},
        {"tier": "relationship_model", "rank": 1,
         "name": "RELATIONSHIP MODEL",
         "document_role": "relationship", "canonical": True},
        {"tier": "service_bible", "rank": 2, "name": "SERVICE BIBLE",
         "document_role": "service_bible", "canonical": True},
        {"tier": "long_term_memory", "rank": 3,
         "name": "long-term memory",
         "document_role": None, "canonical": False},
        {"tier": "current_conversation", "rank": 4,
         "name": "current conversation",
         "document_role": None, "canonical": False},
        {"tier": "temporary_emotional_state", "rank": 5,
         "name": "temporary emotional state",
         "document_role": None, "canonical": False},
    ]


def test_conversation_history_may_affect_state_never_personality():
    mods = _load_modules()
    runtime = mods[1]
    try:
        history = runtime.classify_influence("conversation_history")
        by_name = runtime.classify_influence("current conversation")
        summary = runtime.classify_influence("summary")
        temporary = runtime.classify_influence("temporary_roleplay")
    finally:
        mods[0].unload()
    assert runtime.history_may_affect() == [
        "current_mood", "immediate_context", "recent_events"]
    assert runtime.history_must_not_redefine() == [
        "foundational_personality", "identity", "traits"]
    for row in (history, by_name, summary):
        assert row["tier"] == "current_conversation"
        assert row["rank"] == 4
        assert row["document_role"] is None
        assert row["canonical"] is False
        assert row["may_affect"] == [
            "current_mood", "immediate_context", "recent_events"]
        assert row["may_redefine"] == []
        assert row["must_not_redefine"] == [
            "foundational_personality", "identity", "traits"]
        assert row["may_redefine_foundational_personality"] is False
    # A summary is derived from history: it inherits the
    # conversation tier and can never outrank its source.
    assert summary["tier"] == history["tier"]
    assert temporary["tier"] == "temporary_emotional_state"
    assert temporary["rank"] == 5
    assert temporary["may_redefine_foundational_personality"] is False


def test_canonical_tiers_and_memory_classification():
    mods = _load_modules()
    runtime = mods[1]
    try:
        core = runtime.classify_influence("core")
        by_name = runtime.classify_influence("PERSONA CORE")
        relationship = runtime.classify_influence("relationship")
        service = runtime.classify_influence("service_bible")
        memory = runtime.classify_influence("long-term memory")
    finally:
        mods[0].unload()
    assert core == by_name
    assert core["tier"] == "persona_core"
    assert core["rank"] == 0
    assert core["document_role"] == "core"
    assert relationship["tier"] == "relationship_model"
    assert relationship["document_role"] == "relationship"
    assert service["tier"] == "service_bible"
    assert service["document_role"] == "service_bible"
    for row in (core, relationship, service):
        assert row["canonical"] is True
        assert row["may_redefine_foundational_personality"] is True
        assert row["must_not_redefine"] == []
    # Long-term memory is a non-document tier below every
    # canonical document: it informs, it never redefines.
    assert memory["tier"] == "long_term_memory"
    assert memory["rank"] == 3
    assert memory["canonical"] is False
    assert memory["may_redefine_foundational_personality"] is False


def test_influence_allowed_matrix():
    mods = _load_modules()
    runtime = mods[1]
    try:
        allowed = runtime.influence_allowed
        results = {
            "history_mood": allowed("conversation_history", "mood"),
            "history_context": allowed(
                "conversation_history", "immediate_context"),
            "history_recent": allowed(
                "conversation_history", "recent_events"),
            "history_personality": allowed(
                "conversation_history", "foundational_personality"),
            "history_identity": allowed("conversation_history", "identity"),
            "history_traits": allowed("summary", "traits"),
            "memory_personality": allowed("memory", "personality"),
            "temporary_identity": allowed("temporary_roleplay", "identity"),
            "temporary_mood": allowed(
                "temporary_emotional_state", "current_mood"),
            "core_personality": allowed("core", "foundational_personality"),
            "relationship_identity": allowed("relationship", "identity"),
            "service_traits": allowed("service_bible", "traits"),
        }
    finally:
        mods[0].unload()
    assert results == {
        "history_mood": True,
        "history_context": True,
        "history_recent": True,
        "history_personality": False,
        "history_identity": False,
        "history_traits": False,
        "memory_personality": False,
        "temporary_identity": False,
        "temporary_mood": True,
        "core_personality": True,
        "relationship_identity": True,
        "service_traits": True,
    }


def test_precedence_comparison_core_beats_conversation():
    mods = _load_modules()
    runtime = mods[1]
    try:
        checks = (
            runtime.outranks("core", "conversation_history"),
            runtime.outranks("conversation_history", "core"),
            runtime.outranks(
                "current_conversation", "temporary_emotional_state"),
            runtime.outranks(
                "temporary_emotional_state", "current_conversation"),
            # Memory sits below the service bible.
            runtime.outranks("service_bible", "long_term_memory"),
            runtime.outranks("long_term_memory", "service_bible"),
            runtime.outranks("persona_core", "persona_core"),
            runtime.precedence_winner("summary", "core"),
            runtime.precedence_winner(
                "temporary_roleplay", "conversation_history"),
            runtime.precedence_winner("memory", "memory"),
        )
    finally:
        mods[0].unload()
    assert checks == (
        True, False, True, False, True, False, False,
        "persona_core", "current_conversation", "long_term_memory",
    )


def test_invalid_inputs_are_refused():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for bad in ("", "  ", None, 42, "weather", "avatar",
                    "tool_policy", "memory_policy"):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.classify_influence(bad)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.influence_allowed("conversation_history", "weather")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.influence_allowed("weather", "mood")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.precedence_winner("core", "weather")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.outranks("", "core")
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
        first = runtime.classify_influence("conversation_history")
        second = runtime.classify_influence("conversation_history")
        items = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        after = _hashes(home)
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            mods[2].IdentityStore(_Ctx()).ensure()
            compiled_b = runtime.PersonaCompiler(
                _Ctx(ENABLED)).compile()
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert first == second
    assert before == after
    assert compiled_b is None
    assert len(items) == 1
    assert "§§3-64" in items[0].content
    assert "§23 drift defenses" in items[0].content
    assert "§24 precedence" in items[0].content
    assert "never redefine foundational" in items[0].content
    # The packet names the contract only — never canonical
    # persona text.
    assert "longhouse terminal" not in items[0].content
