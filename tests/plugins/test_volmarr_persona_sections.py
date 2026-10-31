"""Contracts for the section-aware parser + stable ids (Slice 121).

Persona Runtime roadmap §11 (section-aware Markdown parser:
parse semantically, respect conceptual boundaries, never
chunk at arbitrary token counts; a section record carries
document / section / heading / content / priority) and §12
(stable section ids: a persistent role-prefixed identifier
per section, e.g. ``relationship.when_disagreeing``, making
retrieval explainable). Priority here is derived by the pure
``section_priority`` function — §16's authored P0-P4
metadata is a later section. Tests load through real plugin
discovery.
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

CORE_DOC = """# Overview

Core overview text.

# Core Identity

I am Caducea, a persistent Hermes entity.

# Overview

Second overview text.
"""

REL_DOC = """# 37. WHEN CADUCEA DISAGREES

Offer counsel once. Accept the final decision without resentment.

# Settled Decisions

Decisions stand once made.
"""

SERVICE_DOC = """# Overview

Service overview text.

# Coding Preferences

Test everything twice.
"""

DOCS = {
    "core": ("core.md", CORE_DOC),
    "relationship": ("rel.md", REL_DOC),
    "service_bible": ("bible.md", SERVICE_DOC),
}


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
        for role in chosen
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


def _row(compiled, role, section_id):
    return next(
        row for row in compiled["index"]
        if row["role"] == role and row["section_id"] == section_id)


def test_section11_example_record_shape():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        compiled = _compile(runtime)
    finally:
        mods[0].unload()
    # The roadmap's own §11/§12 example, in compiled form:
    # "# 37. WHEN CADUCEA DISAGREES" in the relationship
    # document becomes a record whose section slug and
    # stable id carry no enumeration number.
    row = _row(compiled, "relationship", "when_caducea_disagrees")
    assert row["document"] == "relationship"
    assert row["section"] == "when_caducea_disagrees"
    assert row["heading"] == "WHEN CADUCEA DISAGREES"
    assert row["content"] == row["text"]
    assert "Accept the final decision" in row["content"]
    assert row["stable_id"] == "relationship.when_caducea_disagrees"
    assert _row(compiled, "relationship", "settled_decisions")[
        "stable_id"] == "relationship.settled_decisions"
    # Priority is present, in range, and exactly the pure
    # derivation (the §11 example's 0.87 is illustrative;
    # §16 authored metadata is a later section).
    assert 0.0 <= row["priority"] <= 1.0
    assert row["priority"] == runtime.section_priority(
        "relationship", "WHEN CADUCEA DISAGREES", in_kernel=False)


def test_display_heading_and_stable_id_are_pure_functions():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.display_heading(
            "37. WHEN CADUCEA DISAGREES") == "WHEN CADUCEA DISAGREES"
        assert runtime.display_heading("11.2) Detail") == "Detail"
        assert runtime.display_heading("Core Identity") == \
            "Core Identity"
        # No enumeration punctuation: not an enumeration.
        assert runtime.display_heading("3D Models") == "3D Models"
        assert runtime.stable_section_id(
            "relationship", "when_disagreeing") == \
            "relationship.when_disagreeing"
        assert runtime.stable_section_id(
            "tool_policy", "git_policy") == "tool_policy.git_policy"
    finally:
        mods[0].unload()


def test_renumbering_never_changes_stable_ids():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        compiler = runtime.PersonaCompiler(_Ctx(ENABLED))
        first = compiler.compile()
        (home / "persona" / "rel.md").write_text(
            REL_DOC.replace("# 37.", "# 41."), encoding="utf-8")
        second = compiler.compile()
    finally:
        mods[0].unload()
    ids = lambda c: [row["stable_id"] for row in c["index"]]
    assert ids(first) == ids(second)
    assert [row["section_id"] for row in first["index"]] == \
        [row["section_id"] for row in second["index"]]
    # Section text is unchanged, so the kernel is unchanged;
    # only the document hash (the heading line itself) moved.
    assert first["kernel"]["sha256"] == second["kernel"]["sha256"]
    assert first["persona_hash"] != second["persona_hash"]


def test_duplicate_headings_get_distinct_stable_ids():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        compiled = _compile(runtime)
        again = _compile(runtime)
    finally:
        mods[0].unload()
    first = _row(compiled, "core", "overview")
    second = _row(compiled, "core", "overview_2")
    assert first["stable_id"] == "core.overview"
    assert second["stable_id"] == "core.overview_2"
    assert first["text"] != second["text"]
    # Disambiguation is deterministic across compiles.
    assert [r["stable_id"] for r in compiled["index"]] == \
        [r["stable_id"] for r in again["index"]]


def test_stable_ids_are_unique_across_documents():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        compiled = _compile(runtime)
    finally:
        mods[0].unload()
    stable = [row["stable_id"] for row in compiled["index"]]
    assert len(stable) == len(set(stable))
    # The same bare slug in two documents is two sections.
    assert _row(compiled, "core", "overview")["stable_id"] == \
        "core.overview"
    assert _row(compiled, "service_bible", "overview")[
        "stable_id"] == "service_bible.overview"


def test_parser_respects_conceptual_boundaries_only():
    mods = _load_modules()
    runtime = mods[1]
    try:
        big = "# Big Section\n\n" + ("lore line\n" * 2000)
        sections = runtime.parse_sections(big)
        assert len(sections) == 1
        assert sections[0]["section_id"] == "big_section"
        assert sections[0]["text"].count("lore line") == 2000
        doc = "intro words\n\n# First\n\na\n\n## Sub Part\n\nb\n"
        parsed = runtime.parse_sections(doc)
        assert [s["heading"] for s in parsed] == [
            "preamble", "First", "Sub Part"]
        assert parsed[0]["text"] == "intro words"
    finally:
        mods[0].unload()


def test_section_priority_bands_are_deterministic():
    mods = _load_modules()
    runtime = mods[1]
    try:
        priority = runtime.section_priority
        assert priority("core", "Core Identity", in_kernel=True) == 0.90
        # Kernel-marked (§9) but not selected.
        assert priority("tool_policy", "Critical Boundaries") == 0.80
        assert priority("core", "Core Identity") == 0.80
        # Persona-defining category, unmarked heading.
        assert priority("relationship", "Relationship Model") == 0.60
        # Preference / embodiment material, and the preamble.
        assert priority("service_bible", "Coding Preferences") == 0.40
        assert priority("avatar", "Avatar Appearance") == 0.40
        assert priority("core", "preamble") == 0.40
        # Compiled rows agree: the kernel row is top band.
        _write_persona(get_hermes_home())
        compiled = _compile(runtime)
    finally:
        mods[0].unload()
    assert _row(compiled, "core", "core_identity")["priority"] == 0.90
    for row in compiled["index"]:
        assert row["priority"] in (0.40, 0.60, 0.80, 0.90)


def test_kernel_and_ir_carry_stable_ids():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        compiled = _compile(runtime)
    finally:
        mods[0].unload()
    kernel = compiled["kernel"]
    assert kernel["stable_ids"] == [
        runtime.stable_section_id(row["role"], row["section_id"])
        for row in kernel["sources"]]
    assert "core.core_identity" in kernel["stable_ids"]
    by_stable = {row["stable_id"]: row for row in compiled["index"]}
    for rows in compiled["ir"]["categories"].values():
        for row in rows:
            assert row["stable_id"] == by_stable[
                row["stable_id"]]["stable_id"]
            assert row["stable_id"] == runtime.stable_section_id(
                row["role"], row["section_id"])


def test_compile_is_deterministic_writes_nothing_packet_counts_only():
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
        items = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        after = _hashes(home)
    finally:
        mods[0].unload()
    assert [r["stable_id"] for r in first["index"]] == \
        [r["stable_id"] for r in second["index"]]
    assert first["kernel"]["stable_ids"] == \
        second["kernel"]["stable_ids"]
    assert before == after
    assert len(items) == 1
    assert "stable id" in items[0].content
    assert "persistent Hermes entity" not in items[0].content


def test_profile_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        assert _compile(runtime)["index"]
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
