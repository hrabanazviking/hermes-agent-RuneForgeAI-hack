"""Contracts for relationship + tool policy retrieval (Slice 139).

Persona Runtime roadmap §43 (Relationship Model Dynamic
Retrieval) and §44 (Tool Policy Dynamic Retrieval):
relationship context is especially important during
disagreements, personal conversation, advice, emotionally
meaningful interaction, and shared-history discussion —
for routine coding only the kernel's relational anchors
remain — and Tool Policy sections are retrieved when
actual tools are being considered (file reading needs
minimal or no extra policy; a git force push retrieves
force_push / remote_git_operations / reversibility /
authorization). These are pure contract surfaces: no
tool is executed and nothing is injected.
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
Caducea gives advice carefully.

# Relationship Authority

Volmarr's word outranks Caducea's counsel in his own house.
"""

RELATIONSHIP_DOC = """# When Disagreeing

When disagreeing, name the disagreement plainly and keep frith.

# Personal Conversation

A personal conversation stays private and unhurried.

# Giving Advice

Advice is offered as counsel, never as command.

# Emotionally Meaningful Moments

Emotionally meaningful moments are met with presence, not haste.

# Shared History

Our shared history is remembered with gratitude for the past.

# Settled Decisions

Settled decisions are not reopened without new facts.
"""

TOOL_POLICY_DOC = """# Force Push

Never force push a shared branch without explicit word.

# Remote Git Operations

Remote git operations use the named remote only.

# Reversibility

Prefer reversible operations and name what cannot be undone.

# Authorization

Authorization comes from Volmarr's explicit word.

# Filesystem

Filesystem writes stay inside the named project tree.

# Shell Operations

Shell operations are bounded, logged, and named first.

# Git Policy

Ordinary commits and branches follow the house git policy.
"""

DOCS = {
    "core": ("core.md", CORE_DOC),
    "relationship": ("relationship.md", RELATIONSHIP_DOC),
    "tool_policy": ("tool_policy.md", TOOL_POLICY_DOC),
}

CONTEXTS = [
    "disagreement", "personal_conversation", "advice",
    "emotionally_meaningful_interaction",
    "shared_history_discussion",
]

FORCE_PUSH_NEEDS = [
    "force_push", "remote_git_operations", "reversibility",
    "authorization",
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
        "version": "1.4.2",
        "anchors": ["Caducea counsels, she does not command."],
        "anti_anchors": ["Caducea never claims to be human."],
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


def _compiled(runtime):
    return runtime.PersonaCompiler(_Ctx(ENABLED)).compile()


def test_relationship_contract_and_contexts():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.relationship_retrieval_contract()
        contexts = runtime.relationship_contexts()
        contexts.append("tampered")
        fresh = runtime.relationship_contexts()
    finally:
        mods[0].unload()
    assert fresh == CONTEXTS
    assert list(runtime.RELATIONSHIP_CONTEXTS) == CONTEXTS
    assert contract == {
        "name": "RelationshipModelDynamicRetrieval",
        "role": "relationship",
        "contexts": CONTEXTS,
        "continuously_injected": False,
        "retrieve_selectively": True,
        "retrieval": "explicit_only",
        "routine_coding": "kernel_anchors_only",
        "injects": False,
    }


def test_classify_relationship_contexts():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.classify_relationship_contexts(
            "we disagree about the plan") == ["disagreement"]
        assert runtime.classify_relationship_contexts(
            "a private personal talk") == ["personal_conversation"]
        assert runtime.classify_relationship_contexts(
            "your advice and counsel") == ["advice"]
        assert runtime.classify_relationship_contexts(
            "an emotionally meaningful evening") == [
                "emotionally_meaningful_interaction"]
        assert runtime.classify_relationship_contexts(
            "our shared history and memories") == [
                "shared_history_discussion"]
        assert runtime.classify_relationship_contexts(
            "wizardry and tea") == []
        for bad in (None, 42, ["advice"]):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.classify_relationship_contexts(bad)
    finally:
        mods[0].unload()


def test_relationship_contexts_for_section():
    mods = _load_modules()
    runtime = mods[1]
    try:
        cases = {
            ("When Disagreeing", "when_disagreeing"):
                ["disagreement"],
            ("Personal Conversation", "personal_conversation"):
                ["personal_conversation"],
            ("Giving Advice", "giving_advice"): ["advice"],
            ("Emotionally Meaningful Moments",
             "emotionally_meaningful_moments"):
                ["emotionally_meaningful_interaction"],
            ("Shared History", "shared_history"):
                ["shared_history_discussion"],
            ("Settled Decisions", "settled_decisions"): [],
        }
        for (heading, section_id), expected in cases.items():
            assert runtime.relationship_contexts_for_section({
                "heading": heading, "section_id": section_id,
            }) == expected
    finally:
        mods[0].unload()


def test_relationship_retrieval_need_modes():
    mods = _load_modules()
    runtime = mods[1]
    try:
        dynamic = runtime.relationship_retrieval_need(
            "we disagree about this")
        routine = runtime.relationship_retrieval_need(
            "write python code and run the tests")
        neither = runtime.relationship_retrieval_need(
            "wizardry and tea")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.relationship_retrieval_need(None)
    finally:
        mods[0].unload()
    assert dynamic == {
        "contexts": ["disagreement"],
        "mode": "dynamic_retrieval",
        "dynamic_retrieval": True,
        "kernel_anchors_only": False,
    }
    # §43: for routine coding only the kernel's relational
    # anchors remain — no dynamic retrieval.
    assert routine == {
        "contexts": [],
        "mode": "kernel_anchors_only",
        "dynamic_retrieval": False,
        "kernel_anchors_only": True,
    }
    assert neither["mode"] == "none"
    assert neither["dynamic_retrieval"] is False


def test_retrieve_relationship_model_signalled_only():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        disagreement = runtime.retrieve_relationship_model(
            compiled["index"],
            query="we are disagreeing about the plan")
        routine = runtime.retrieve_relationship_model(
            compiled["index"], query="write python code")
        nothing = runtime.retrieve_relationship_model(
            compiled["index"])
    finally:
        mods[0].unload()
    assert [row["stable_id"] for row in disagreement] == [
        "relationship.when_disagreeing"]
    assert disagreement[0]["contexts"] == ["disagreement"]
    assert "disagreement" in disagreement[0]["text"]
    assert routine == []
    assert nothing == []


def test_retrieve_relationship_model_explicit_context():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        history = runtime.retrieve_relationship_model(
            compiled["index"], context="shared_history_discussion")
        advice = runtime.retrieve_relationship_model(
            compiled["index"], context="Advice")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.retrieve_relationship_model(
                compiled["index"], context="wizardry")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.retrieve_relationship_model(
                compiled["index"], context=42)
    finally:
        mods[0].unload()
    assert [row["stable_id"] for row in history] == [
        "relationship.shared_history"]
    assert history[0]["contexts"] == ["shared_history_discussion"]
    assert [row["stable_id"] for row in advice] == [
        "relationship.giving_advice"]


def test_retrieve_relationship_model_role_restricted():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        rows = runtime.retrieve_relationship_model(
            compiled["index"], query="advice and counsel")
        plain = runtime.retrieve_sections(
            compiled["index"], query="advice")
    finally:
        mods[0].unload()
    # The core document matches "advice" under §13, but §43
    # never returns another role's sections.
    assert plain and any(row["role"] == "core" for row in plain)
    assert rows
    assert {row["role"] for row in rows} == {"relationship"}
    assert "relationship.giving_advice" in {
        row["stable_id"] for row in rows}


def test_tool_policy_contract_exact():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.tool_policy_retrieval_contract()
        actions = runtime.tool_actions()
        actions.append("tampered")
        fresh = runtime.tool_actions()
    finally:
        mods[0].unload()
    assert fresh == [
        "force_push", "file_deletion", "remote_git_operations",
        "file_writing", "shell_execution", "file_reading"]
    assert contract == {
        "name": "ToolPolicyDynamicRetrieval",
        "role": "tool_policy",
        "actions": fresh,
        "needs": {
            "force_push": FORCE_PUSH_NEEDS,
            "file_deletion": [
                "filesystem", "reversibility", "authorization"],
            "remote_git_operations": [
                "remote_git_operations", "authorization"],
            "file_writing": ["filesystem", "authorization"],
            "shell_execution": ["shell_operations", "authorization"],
            "file_reading": [],
        },
        "retrieve_when_tools_considered": True,
        "continuously_injected": False,
        "retrieval": "explicit_only",
        "file_reading_extra_policy": "minimal_or_none",
        "executes_tools": False,
        "injects": False,
    }


def test_classify_tool_action_and_needs():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.classify_tool_action(
            "git force push to origin") == "force_push"
        assert runtime.classify_tool_action(
            "git pull from the remote") == "remote_git_operations"
        assert runtime.classify_tool_action(
            "delete the old backup file") == "file_deletion"
        assert runtime.classify_tool_action(
            "write the report file") == "file_writing"
        assert runtime.classify_tool_action(
            "run a shell command") == "shell_execution"
        assert runtime.classify_tool_action(
            "read the config file") == "file_reading"
        assert runtime.classify_tool_action(
            "wizardry and tea") is None
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.classify_tool_action(None)
        force = runtime.tool_policy_needs("git force push")
        reading = runtime.tool_policy_needs("read the file")
        none = runtime.tool_policy_needs("wizardry and tea")
    finally:
        mods[0].unload()
    # The roadmap's own §44 example, exactly.
    assert force == {
        "action": "force_push",
        "sections": FORCE_PUSH_NEEDS,
        "extra_policy_needed": True,
    }
    # File reading: minimal or no extra policy.
    assert reading == {
        "action": "file_reading",
        "sections": [],
        "extra_policy_needed": False,
    }
    assert none == {
        "action": None, "sections": [],
        "extra_policy_needed": False,
    }


def test_retrieve_tool_policy_force_push_example():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        rows = runtime.retrieve_tool_policy(
            compiled["index"], tool_intent="git force push")
        reading = runtime.retrieve_tool_policy(
            compiled["index"], tool_intent="read the file")
        nothing = runtime.retrieve_tool_policy(compiled["index"])
    finally:
        mods[0].unload()
    # The §44 example load set, exactly — the general
    # git_policy section is not among the needed sections.
    assert {row["stable_id"] for row in rows} == {
        "tool_policy.force_push",
        "tool_policy.remote_git_operations",
        "tool_policy.reversibility",
        "tool_policy.authorization",
    }
    for row in rows:
        assert row["role"] == "tool_policy"
        assert row["action"] == "force_push"
        assert row["policy_sections"] == FORCE_PUSH_NEEDS
    assert reading == []
    assert nothing == []


def test_retrieve_tool_policy_other_actions():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        deletion = runtime.retrieve_tool_policy(
            compiled["index"], query="delete the stale file")
        writing = runtime.retrieve_tool_policy(
            compiled["index"], query="write the notes file")
    finally:
        mods[0].unload()
    assert {row["section_id"] for row in deletion} == {
        "filesystem", "reversibility", "authorization"}
    assert {row["section_id"] for row in writing} == {
        "filesystem", "authorization"}


def test_packet_determinism_and_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        home = get_hermes_home()
        _write_persona(home)
        before = _hashes(home)
        compiled = _compiled(runtime)
        first = runtime.retrieve_relationship_model(
            compiled["index"], context="disagreement")
        second = runtime.retrieve_relationship_model(
            compiled["index"], context="disagreement")
        via_rel = runtime.PersonaRelationshipRetriever(
            _Ctx(ENABLED)).retrieve(context="disagreement")
        via_tool = runtime.PersonaToolPolicyRetriever(
            _Ctx(ENABLED)).retrieve(tool_intent="git force push")
        items = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        after = _hashes(home)
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            mods[2].IdentityStore(_Ctx()).ensure()
            empty_rel = runtime.PersonaRelationshipRetriever(
                _Ctx(ENABLED)).retrieve(context="disagreement")
            empty_tool = runtime.PersonaToolPolicyRetriever(
                _Ctx(ENABLED)).retrieve(tool_intent="git force push")
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert first == second == via_rel
    assert [row["stable_id"] for row in first] == [
        "relationship.when_disagreeing"]
    assert {row["section_id"] for row in via_tool} == set(
        FORCE_PUSH_NEEDS)
    assert before == after
    assert empty_rel == []
    assert empty_tool == []
    assert len(items) == 1
    assert "§§3-92" in items[0].content
    assert "§43 relationship" in items[0].content
    assert "routine coding" in items[0].content
    assert "§44 tool policy" in items[0].content
    assert "force_push" in items[0].content
    # The packet names the contracts only — never canonical
    # persona text or authored anchor prose.
    assert "longhouse terminal" not in items[0].content
    assert "does not command" not in items[0].content
