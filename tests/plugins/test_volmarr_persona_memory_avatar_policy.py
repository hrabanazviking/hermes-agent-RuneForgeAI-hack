"""Contracts for memory + avatar policy usage (Slice 140).

Persona Runtime roadmap §45 (Memory Policy Usage) and §46
(Avatar Policy Usage): the model normally does not need
the entire Memory Policy in context — the memory
subsystem itself implements it, and policy text is
retrieved only when resolving memory conflicts, deciding
promotion, performing reflection, or explaining memory
decisions — and the Avatar file rarely belongs in
ordinary text inference, retrieved only when generating
images, controlling the avatar, describing the persona,
selecting expressions, or in VR interaction, with the
avatar controller consuming structured AvatarIR
directly. These are pure contract surfaces: nothing is
injected and no subsystem or controller is owned here.
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
"""

MEMORY_POLICY_DOC = """# Resolving Memory Conflicts

When memories conflict, the newer verified record wins.

# Deciding Promotion

Deciding promotion weighs repetition and source trust.

# Performing Reflection

Performing reflection reviews what the day taught.

# Explaining Memory Decisions

Explaining memory decisions names the policy that applied.

# Memory Retention

Retention keeps what serves the work and lets the rest fade.
"""

AVATAR_DOC = """# Generating Images

Generating images follows the canonical appearance record.

# Controlling the Avatar

Controlling the avatar moves only on explicit direction.

# Describing Caducea

Describing Caducea uses the canonical appearance record.

# Selecting Expressions

Selecting expressions matches the moment's tone.

# VR Interaction

VR interaction keeps presence calm and bounded.

# Ordinary Text Inference

Ordinary text inference proceeds without embodiment detail.
"""

DOCS = {
    "core": ("core.md", CORE_DOC),
    "memory_policy": ("memory_policy.md", MEMORY_POLICY_DOC),
    "avatar": ("avatar.md", AVATAR_DOC),
}

MEMORY_OCCASIONS = [
    "resolving_memory_conflicts", "deciding_promotion",
    "performing_reflection", "explaining_memory_decisions",
]

AVATAR_OCCASIONS = [
    "generating_images", "controlling_avatar",
    "describing_persona", "selecting_expressions",
    "vr_interaction",
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


def test_memory_policy_contract_and_occasions():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.memory_policy_usage_contract()
        occasions = runtime.memory_policy_occasions()
        occasions.append("tampered")
        fresh = runtime.memory_policy_occasions()
    finally:
        mods[0].unload()
    assert fresh == MEMORY_OCCASIONS
    assert list(runtime.MEMORY_POLICY_OCCASIONS) == MEMORY_OCCASIONS
    assert contract == {
        "name": "MemoryPolicyUsage",
        "role": "memory_policy",
        "occasions": MEMORY_OCCASIONS,
        "normally_needed_in_context": False,
        "implemented_by": "memory_subsystem",
        "retrieve_only_on_occasion": True,
        "behavior_in_code_where_practical": True,
        "continuously_injected": False,
        "retrieval": "explicit_only",
        "injects": False,
    }


def test_classify_memory_policy_occasions():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.classify_memory_policy_occasions(
            "resolve this memory conflict") == [
                "resolving_memory_conflicts"]
        assert runtime.classify_memory_policy_occasions(
            "decide the promotion question") == [
                "deciding_promotion"]
        assert runtime.classify_memory_policy_occasions(
            "a moment of reflection") == ["performing_reflection"]
        assert runtime.classify_memory_policy_occasions(
            "explain that memory decision") == [
                "explaining_memory_decisions"]
        assert runtime.classify_memory_policy_occasions(
            "wizardry and tea") == []
        for bad in (None, 42, ["reflection"]):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.classify_memory_policy_occasions(bad)
    finally:
        mods[0].unload()


def test_memory_policy_occasions_for_section():
    mods = _load_modules()
    runtime = mods[1]
    try:
        cases = {
            ("Resolving Memory Conflicts",
             "resolving_memory_conflicts"):
                ["resolving_memory_conflicts"],
            ("Deciding Promotion", "deciding_promotion"):
                ["deciding_promotion"],
            ("Performing Reflection", "performing_reflection"):
                ["performing_reflection"],
            ("Explaining Memory Decisions",
             "explaining_memory_decisions"):
                ["explaining_memory_decisions"],
            ("Memory Retention", "memory_retention"): [],
        }
        for (heading, section_id), expected in cases.items():
            assert runtime.memory_policy_occasions_for_section({
                "heading": heading, "section_id": section_id,
            }) == expected
    finally:
        mods[0].unload()


def test_memory_policy_retrieval_need_modes():
    mods = _load_modules()
    runtime = mods[1]
    try:
        occasion = runtime.memory_policy_retrieval_need(
            "resolve the conflicting memories")
        ordinary = runtime.memory_policy_retrieval_need(
            "write python code and run the tests")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.memory_policy_retrieval_need(None)
    finally:
        mods[0].unload()
    assert occasion == {
        "occasions": ["resolving_memory_conflicts"],
        "mode": "selective_retrieval",
        "dynamic_retrieval": True,
        "subsystem_only": False,
    }
    # §45: normally the subsystem implements the policy —
    # no policy text is needed in context.
    assert ordinary == {
        "occasions": [],
        "mode": "subsystem_only",
        "dynamic_retrieval": False,
        "subsystem_only": True,
    }


def test_retrieve_memory_policy_signalled_only():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        conflict = runtime.retrieve_memory_policy(
            compiled["index"],
            query="resolve this memory conflict")
        ordinary = runtime.retrieve_memory_policy(
            compiled["index"], query="write python code")
        nothing = runtime.retrieve_memory_policy(compiled["index"])
    finally:
        mods[0].unload()
    assert [row["stable_id"] for row in conflict] == [
        "memory_policy.resolving_memory_conflicts"]
    assert conflict[0]["occasions"] == [
        "resolving_memory_conflicts"]
    assert conflict[0]["role"] == "memory_policy"
    assert ordinary == []
    assert nothing == []


def test_retrieve_memory_policy_explicit_occasion():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        promotion = runtime.retrieve_memory_policy(
            compiled["index"], occasion="deciding_promotion")
        reflection = runtime.retrieve_memory_policy(
            compiled["index"], occasion="Performing Reflection")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.retrieve_memory_policy(
                compiled["index"], occasion="wizardry")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.retrieve_memory_policy(
                compiled["index"], occasion=42)
    finally:
        mods[0].unload()
    assert [row["stable_id"] for row in promotion] == [
        "memory_policy.deciding_promotion"]
    assert [row["stable_id"] for row in reflection] == [
        "memory_policy.performing_reflection"]


def test_avatar_policy_contract_and_occasions():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.avatar_policy_usage_contract()
        occasions = runtime.avatar_policy_occasions()
        occasions.append("tampered")
        fresh = runtime.avatar_policy_occasions()
    finally:
        mods[0].unload()
    assert fresh == AVATAR_OCCASIONS
    assert list(runtime.AVATAR_POLICY_OCCASIONS) == AVATAR_OCCASIONS
    assert contract == {
        "name": "AvatarPolicyUsage",
        "role": "avatar",
        "occasions": AVATAR_OCCASIONS,
        "rarely_in_ordinary_text_inference": True,
        "retrieve_only_on_occasion": True,
        "avatar_controller_consumes": "AvatarIR",
        "avatar_controller_direct_ir": True,
        "continuously_injected": False,
        "retrieval": "explicit_only",
        "injects": False,
    }


def test_classify_avatar_occasions():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.classify_avatar_occasions(
            "generate an image of the hall") == ["generating_images"]
        assert runtime.classify_avatar_occasions(
            "control the avatar pose") == ["controlling_avatar"]
        assert runtime.classify_avatar_occasions(
            "describe her appearance") == ["describing_persona"]
        assert runtime.classify_avatar_occasions(
            "selecting expressions for the scene") == [
                "selecting_expressions"]
        assert runtime.classify_avatar_occasions(
            "a vr interaction in the headset") == ["vr_interaction"]
        assert runtime.classify_avatar_occasions(
            "wizardry and tea") == []
        for bad in (None, 42, ["vr_interaction"]):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.classify_avatar_occasions(bad)
    finally:
        mods[0].unload()


def test_avatar_occasions_for_section_and_need():
    mods = _load_modules()
    runtime = mods[1]
    try:
        cases = {
            ("Generating Images", "generating_images"):
                ["generating_images"],
            ("Controlling the Avatar", "controlling_the_avatar"):
                ["controlling_avatar"],
            ("Describing Caducea", "describing_caducea"):
                ["describing_persona"],
            ("Selecting Expressions", "selecting_expressions"):
                ["selecting_expressions"],
            ("VR Interaction", "vr_interaction"): ["vr_interaction"],
            ("Ordinary Text Inference", "ordinary_text_inference"):
                [],
        }
        for (heading, section_id), expected in cases.items():
            assert runtime.avatar_occasions_for_section({
                "heading": heading, "section_id": section_id,
            }) == expected
        occasion = runtime.avatar_retrieval_need(
            "generate an image")
        ordinary = runtime.avatar_retrieval_need(
            "write python code and run the tests")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.avatar_retrieval_need(None)
    finally:
        mods[0].unload()
    assert occasion == {
        "occasions": ["generating_images"],
        "mode": "selective_retrieval",
        "dynamic_retrieval": True,
        "ordinary_text_inference": False,
    }
    # §46: the Avatar file rarely belongs in ordinary text
    # inference.
    assert ordinary == {
        "occasions": [],
        "mode": "not_in_ordinary_inference",
        "dynamic_retrieval": False,
        "ordinary_text_inference": True,
    }


def test_retrieve_avatar_policy_signalled_only():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        images = runtime.retrieve_avatar_policy(
            compiled["index"], query="generate an image")
        vr = runtime.retrieve_avatar_policy(
            compiled["index"], occasion="vr_interaction")
        ordinary = runtime.retrieve_avatar_policy(
            compiled["index"], query="write python code")
        nothing = runtime.retrieve_avatar_policy(compiled["index"])
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.retrieve_avatar_policy(
                compiled["index"], occasion="wizardry")
    finally:
        mods[0].unload()
    assert [row["stable_id"] for row in images] == [
        "avatar.generating_images"]
    assert images[0]["occasions"] == ["generating_images"]
    assert images[0]["role"] == "avatar"
    assert [row["stable_id"] for row in vr] == [
        "avatar.vr_interaction"]
    assert ordinary == []
    assert nothing == []


def test_retrievers_role_restricted():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        memory_rows = runtime.retrieve_memory_policy(
            compiled["index"], query="reflection on the conflict")
        avatar_rows = runtime.retrieve_avatar_policy(
            compiled["index"], query="describe her appearance")
    finally:
        mods[0].unload()
    assert memory_rows
    assert {row["role"] for row in memory_rows} == {"memory_policy"}
    assert avatar_rows
    assert {row["role"] for row in avatar_rows} == {"avatar"}


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
        first = runtime.retrieve_memory_policy(
            compiled["index"], occasion="deciding_promotion")
        second = runtime.retrieve_memory_policy(
            compiled["index"], occasion="deciding_promotion")
        via_memory = runtime.PersonaMemoryPolicyRetriever(
            _Ctx(ENABLED)).retrieve(occasion="deciding_promotion")
        via_avatar = runtime.PersonaAvatarPolicyRetriever(
            _Ctx(ENABLED)).retrieve(occasion="vr_interaction")
        items = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        after = _hashes(home)
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            mods[2].IdentityStore(_Ctx()).ensure()
            empty_memory = runtime.PersonaMemoryPolicyRetriever(
                _Ctx(ENABLED)).retrieve(occasion="deciding_promotion")
            empty_avatar = runtime.PersonaAvatarPolicyRetriever(
                _Ctx(ENABLED)).retrieve(occasion="vr_interaction")
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert first == second == via_memory
    assert [row["stable_id"] for row in first] == [
        "memory_policy.deciding_promotion"]
    assert [row["stable_id"] for row in via_avatar] == [
        "avatar.vr_interaction"]
    assert before == after
    assert empty_memory == []
    assert empty_avatar == []
    assert len(items) == 1
    assert "§§3-90" in items[0].content
    assert "§45 memory policy" in items[0].content
    assert "memory subsystem" in items[0].content
    assert "§46 avatar policy" in items[0].content
    assert "AvatarIR" in items[0].content
    # The packet names the contracts only — never canonical
    # persona text or authored anchor prose.
    assert "longhouse terminal" not in items[0].content
    assert "does not command" not in items[0].content
