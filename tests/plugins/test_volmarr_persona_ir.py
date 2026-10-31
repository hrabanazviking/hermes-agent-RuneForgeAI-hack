"""Contracts for PersonaIR and no-blind-summary (Slice 119).

Persona Runtime roadmap §7 (do not summarize blindly: kernel,
index, and IR carry section text verbatim — structured
representation is deterministic classification of whole
sections, never generated summaries or paraphrase) and §8
(PersonaIR: the compiler's explicit intermediate artefact with
the thirteen named categories; the Markdown documents remain
canonical and the IR is generated runtime data humans are
never required to edit). Tests load through real discovery.
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

EXPECTED_CATEGORIES = [
    "identity", "motivations", "values", "relationship",
    "communication", "behavioral_rules", "preferences",
    "boundaries", "tools", "memory", "embodiment", "quirks",
    "projects",
]

CORE_DOC = """# Core Identity

I am Caducea, a persistent Hermes entity.

# Primary Motivation

Help Volmarr translate vision into reality.

# Communication Style

Plain words first, warmth always.

# Counsel Behavior

Caducea offers counsel freely but genuinely accepts Volmarr's
final decision. She never resents being overruled.

# Hard Boundaries

Never force-push. Never share secrets.

# Character Quirks

She names her tools after ships.
"""

SERVICE_DOC = """# Coding Preferences

Test everything twice.
"""

RELATIONSHIP_DOC = """# Relationship Model

Chosen devotion and independent intelligence coexist.
"""

MEMORY_DOC = """# Memory Policy

Continuity is sacred; summaries never define the persona.
"""

TOOL_DOC = """# Tool Policy

Prefer local tools; ask before anything irreversible.
"""

AVATAR_DOC = """# Avatar Appearance

Raven hair, gold coin chains.
"""


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


def _write_persona(home: Path, *, extra_role=False) -> dict:
    persona_dir = home / "persona"
    persona_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "core": ("core.md", CORE_DOC),
        "service_bible": ("bible.md", SERVICE_DOC),
        "relationship": ("rel.md", RELATIONSHIP_DOC),
        "memory_policy": ("mem.md", MEMORY_DOC),
        "tool_policy": ("tools.md", TOOL_DOC),
        "avatar": ("avatar.md", AVATAR_DOC),
    }
    documents = {}
    for role, (name, text) in files.items():
        (persona_dir / name).write_text(text, encoding="utf-8")
        documents[role] = {"file": name, "required": True}
    if extra_role:
        (persona_dir / "spirit.md").write_text(
            "# Spiritual Model\n\nFrith above all.\n",
            encoding="utf-8")
        documents["spirituality"] = {"file": "spirit.md"}
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
    return config


def _hashes(home: Path) -> dict[str, str]:
    return {
        str(path.relative_to(home)):
            hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(home.rglob("*"))
        if path.is_file() and "entity" not in path.parts
    }


def _compile(runtime):
    return runtime.PersonaCompiler(_Ctx(ENABLED)).compile()


def test_ir_has_all_thirteen_categories_in_roadmap_order():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        compiled = _compile(runtime)
    finally:
        mods[0].unload()
    ir = compiled["ir"]
    assert runtime.ir_categories() == EXPECTED_CATEGORIES
    assert list(ir["categories"]) == EXPECTED_CATEGORIES
    assert list(ir["category_counts"]) == EXPECTED_CATEGORIES
    assert ir["generated"] is True
    assert ir["human_editable"] is False
    assert ir["persona_id"] == "caducea"
    assert ir["total_sections"] == len(compiled["index"])
    assert sum(ir["category_counts"].values()) == ir["total_sections"]
    # No section classifies as a project in this persona.
    assert ir["categories"]["projects"] == []
    assert ir["categories"]["values"] == []


def test_ir_classification_maps_sections_deterministically():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        compiled = _compile(runtime)
    finally:
        mods[0].unload()
    by_section = {}
    for category, rows in compiled["ir"]["categories"].items():
        for row in rows:
            by_section[(row["role"], row["section_id"])] = category
    assert by_section[("core", "core_identity")] == "identity"
    assert by_section[("core", "primary_motivation")] == "motivations"
    assert by_section[("core", "communication_style")] == "communication"
    assert by_section[("core", "counsel_behavior")] == "behavioral_rules"
    assert by_section[("core", "hard_boundaries")] == "boundaries"
    assert by_section[("core", "character_quirks")] == "quirks"
    assert by_section[("service_bible", "coding_preferences")] == \
        "preferences"
    assert by_section[("relationship", "relationship_model")] == \
        "relationship"
    assert by_section[("memory_policy", "memory_policy")] == "memory"
    assert by_section[("tool_policy", "tool_policy")] == "tools"
    assert by_section[("avatar", "avatar_appearance")] == "embodiment"
    # The pure classifier agrees with the compiled artefact.
    assert runtime.classify_section("core", "Hard Boundaries") == \
        "boundaries"
    assert runtime.classify_section("avatar", "Anything") == "embodiment"


def test_section_text_is_verbatim_everywhere_no_summaries():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        compiled = _compile(runtime)
        sources = {
            role: (home / "persona" / name).read_text(encoding="utf-8")
            for role, name in {
                "core": "core.md", "service_bible": "bible.md",
                "relationship": "rel.md", "memory_policy": "mem.md",
                "tool_policy": "tools.md", "avatar": "avatar.md",
            }.items()
        }
    finally:
        mods[0].unload()
    # §7: every indexed section text appears verbatim in its
    # source document (whitespace normalisation aside, these
    # fixtures need none) — nothing was summarised or reworded.
    for row in compiled["index"]:
        assert row["text"] in sources[row["role"]]
    # The kernel is whole verbatim sections only.
    kernel_ids = set(compiled["kernel"]["section_ids"])
    for row in compiled["index"]:
        if row["section_id"] in kernel_ids and row["role"] == "core":
            assert row["text"] in compiled["kernel"]["text"]
    # The IR carries exactly the index texts — the §7 counsel
    # example sentence survives word-for-word, structured by
    # classification rather than rewritten into a summary.
    index_texts = {
        (r["role"], r["section_id"]): r["text"]
        for r in compiled["index"]}
    for rows in compiled["ir"]["categories"].values():
        for row in rows:
            assert row["text"] == index_texts[
                (row["role"], row["section_id"])]
    counsel = compiled["ir"]["categories"]["behavioral_rules"]
    assert any(
        "genuinely accepts Volmarr's\nfinal decision. "
        "She never resents being overruled." in row["text"]
        for row in counsel)


def test_ir_is_deterministic_and_compile_writes_nothing():
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
    assert first["ir"] == second["ir"]
    assert len(first["ir"]["ir_hash"]) == 64
    # Generated runtime data is returned, never persisted:
    # no IR file (or any other file) appears in the profile.
    assert before == after


def test_ir_hash_changes_when_a_document_changes():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        compiler = runtime.PersonaCompiler(_Ctx(ENABLED))
        first = compiler.compile()
        (home / "persona" / "core.md").write_text(
            CORE_DOC + "\n# Projects\n\nHermes, Samtal.\n",
            encoding="utf-8")
        second = compiler.compile()
    finally:
        mods[0].unload()
    assert first["ir"]["ir_hash"] != second["ir"]["ir_hash"]
    assert second["ir"]["categories"]["projects"]
    assert second["ir"]["categories"]["projects"][0]["section_id"] == \
        "projects"


def test_extension_role_sections_classify_without_code_change():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home(), extra_role=True)
        compiled = _compile(runtime)
    finally:
        mods[0].unload()
    values = compiled["ir"]["categories"]["values"]
    assert [(r["role"], r["section_id"]) for r in values] == [
        ("spirituality", "spiritual_model")]


def test_packet_names_ir_hash_and_counts_only():
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
    assert "PersonaIR hash" in items[0].content
    assert "categories populated" in items[0].content
    assert "persistent Hermes entity" not in items[0].content
    assert "Raven hair" not in items[0].content


def test_profile_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        assert _compile(runtime)["ir"]["total_sections"] > 0
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
