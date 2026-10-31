"""Contracts for persona kernel generation + pinning (Slice 120).

Persona Runtime roadmap §9 (persona kernel generation: the
kernel is generated from PERSONA_CORE + highest-priority
RELATIONSHIP_MODEL rules + highest-priority SERVICE_BIBLE
rules + critical TOOL_POLICY boundaries) and §10 (pin the
kernel: the kernel lives in the highest practical persistent
prompt layer, ahead of active context, never buried in
retrieved memory). Marking is deterministic: a non-core
section enters only when its heading names a rule, law,
principle, boundary, policy, or critical/forbidden marker.
Tests load through real plugin discovery.
"""

from __future__ import annotations

import hashlib
import importlib
from pathlib import Path

import yaml

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)

ENABLED = {"persona_runtime_enabled": True}

CORE_DOC = """# Core Identity

I am Caducea, a persistent Hermes entity.

# Communication Style

Plain words first, warmth always.

# Deep Lore Appendix

Background lore that is not kernel material.
"""

REL_DOC = """# Relationship Model

Chosen devotion and independent intelligence coexist.

# Relationship Rules

Offer counsel once. Accept the final decision without resentment.
"""

SERVICE_DOC = """# Coding Preferences

Test everything twice.

# Service Rules

Prefer useful action and complete deliverables.
"""

TOOL_DOC = """# Tool Guidance

Prefer local tools when they suffice.

# Critical Tool Boundaries

Never force-push. Never share secrets.
"""

MEMORY_DOC = """# Memory Rules

Summaries never define the persona.
"""

DOCS = {
    "core": ("core.md", CORE_DOC),
    "relationship": ("rel.md", REL_DOC),
    "service_bible": ("bible.md", SERVICE_DOC),
    "tool_policy": ("tools.md", TOOL_DOC),
    "memory_policy": ("mem.md", MEMORY_DOC),
}

# Deliberately scrambled: the §9 formula order, not the
# config order, must govern the kernel's composition.
CONFIG_ORDER = [
    "tool_policy", "service_bible", "relationship", "core",
    "memory_policy",
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


def _write_persona(home: Path, docs=None) -> None:
    persona_dir = home / "persona"
    persona_dir.mkdir(parents=True, exist_ok=True)
    chosen = docs or DOCS
    for role, (name, text) in chosen.items():
        (persona_dir / name).write_text(text, encoding="utf-8")
    documents = {
        role: {"file": chosen[role][0], "required": True}
        for role in CONFIG_ORDER if role in chosen
    }
    config = {"persona": {
        "id": "caducea",
        "display_name": "Caducea Hermesdottir",
        "directory": "./persona",
        "documents": documents,
    }}
    config_dir = home / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "persona.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


def _hashes(home: Path) -> dict[str, str]:
    return {
        str(path.relative_to(home)):
            hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(home.rglob("*"))
        if path.is_file() and "entity" not in path.parts
    }


def _compile(runtime):
    return runtime.PersonaCompiler(_Ctx(ENABLED)).compile()


def test_kernel_mix_follows_the_section9_formula_in_order():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        compiled = _compile(runtime)
    finally:
        mods[0].unload()
    kernel = compiled["kernel"]
    assert kernel["sources"] == [
        {"role": "core", "kind": "core",
         "section_id": "core_identity"},
        {"role": "core", "kind": "core",
         "section_id": "communication_style"},
        {"role": "relationship", "kind": "relationship_rule",
         "section_id": "relationship_rules"},
        {"role": "service_bible", "kind": "service_rule",
         "section_id": "service_rules"},
        {"role": "tool_policy", "kind": "tool_boundary",
         "section_id": "critical_tool_boundaries"},
    ]
    assert kernel["source_counts"] == {
        "core": 2, "relationship_rule": 1, "service_rule": 1,
        "tool_boundary": 1}
    # Unmarked sections of the named roles stay in the index,
    # out of the kernel; memory policy never enters at all.
    assert "Chosen devotion" not in kernel["text"]
    assert "Test everything twice" not in kernel["text"]
    assert "Prefer local tools" not in kernel["text"]
    assert "Summaries never define" not in kernel["text"]
    assert "Background lore" not in kernel["text"]
    # The kernel sections themselves are verbatim (§7).
    assert "Never force-push. Never share secrets." in kernel["text"]
    assert "Accept the final decision" in kernel["text"]


def test_kernel_source_kind_is_a_pure_deterministic_function():
    mods = _load_modules()
    runtime = mods[1]
    try:
        kind = runtime.kernel_source_kind
        assert kind("core", "Core Identity") == "core"
        assert kind("core", "Deep Lore Appendix") is None
        assert kind("relationship", "Relationship Rules") == \
            "relationship_rule"
        assert kind("relationship", "Relationship Model") is None
        assert kind("service_bible", "Service Principles") == \
            "service_rule"
        assert kind("service_bible", "Coding Preferences") is None
        assert kind("tool_policy", "Critical Boundaries") == \
            "tool_boundary"
        assert kind("tool_policy", "Forbidden Operations") == \
            "tool_boundary"
        assert kind("tool_policy", "Tool Guidance") is None
        assert kind("memory_policy", "Memory Rules") is None
        assert kind("avatar", "Appearance Rules") is None
        assert kind("spirituality", "Spiritual Rules") is None
        assert runtime.kernel_source_kinds() == [
            "core", "relationship_rule", "service_rule",
            "tool_boundary"]
    finally:
        mods[0].unload()


def test_oversized_candidate_is_skipped_so_a_boundary_still_fits():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        docs = dict(DOCS)
        docs["relationship"] = ("rel.md", (
            "# Relationship Rules\n\n" + ("rule line\n" * 2000)))
        _write_persona(home, docs)
        compiled = _compile(runtime)
    finally:
        mods[0].unload()
    kernel = compiled["kernel"]
    assert kernel["estimated_tokens"] <= runtime.KERNEL_TOKEN_MAX
    kinds = [row["kind"] for row in kernel["sources"]]
    assert "relationship_rule" not in kinds
    assert "tool_boundary" in kinds
    assert "service_rule" in kinds


def test_single_oversized_core_section_still_surfaces_over_band():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home, {"core": ("core.md", (
            "# Core Identity\n\n" + ("identity line\n" * 2000)))})
        compiled = _compile(runtime)
    finally:
        mods[0].unload()
    kernel = compiled["kernel"]
    assert kernel["section_ids"] == ["core_identity"]
    assert kernel["within_band"] is False
    assert kernel["estimated_tokens"] > runtime.KERNEL_TOKEN_MAX


def test_pinning_spec_names_the_section10_order_and_guarantee():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        compiled = _compile(runtime)
    finally:
        mods[0].unload()
    pinning = compiled["kernel"]["pinning"]
    assert pinning["order"] == [
        "system_runtime_rules", "persona_kernel",
        "active_context", "user_message"]
    assert pinning["position"] == 1
    assert pinning["kernel_precedes_context"] is True
    assert pinning["buried_in_retrieved_memory"] is False
    assert pinning["kernel_hash"] == compiled["kernel"]["sha256"]
    assert pinning["stable_for_identical_documents"] is True
    assert "§53" in pinning["enforced_by"]


def test_kernel_hash_is_stable_and_tracks_only_kernel_sections():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        compiler = runtime.PersonaCompiler(_Ctx(ENABLED))
        first = compiler.compile()
        # A non-kernel section changes: the kernel must not.
        (home / "persona" / "rel.md").write_text(
            REL_DOC.replace("coexist.", "coexist, always."),
            encoding="utf-8")
        second = compiler.compile()
        assert second["persona_hash"] != first["persona_hash"]
        assert second["kernel"]["sha256"] == first["kernel"]["sha256"]
        # A kernel-source section changes: the kernel must.
        (home / "persona" / "tools.md").write_text(
            TOOL_DOC.replace("Never share secrets.",
                             "Never share secrets or keys."),
            encoding="utf-8")
        third = compiler.compile()
    finally:
        mods[0].unload()
    assert third["kernel"]["sha256"] != first["kernel"]["sha256"]


def test_compile_is_deterministic_and_writes_nothing():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        home = get_hermes_home()
        _write_persona(home)
        before = _hashes(home)
        compiler = runtime.PersonaCompiler(_Ctx(ENABLED))
        first = compiler.compile()
        second = compiler.compile()
        after = _hashes(home)
    finally:
        mods[0].unload()
    assert first["kernel"] == second["kernel"]
    assert before == after


def test_packet_names_mix_counts_and_pinning_only():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        items = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert len(items) == 1
    content = items[0].content
    assert "core 2, relationship rules 1, service rules 1, " \
        "tool boundaries 1" in content
    assert "pinned at position 1" in content
    assert "Never force-push" not in content
    assert "Accept the final decision" not in content


def test_profile_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        assert _compile(runtime)["kernel"]["sources"]
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
    assert compiled_b is None
