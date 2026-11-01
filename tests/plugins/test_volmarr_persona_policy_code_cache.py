"""Contracts for policy-to-code migration + compilation cache (Slice 141).

Persona Runtime roadmap §47 (Policy → Code Migration) and
§48 (Persona Compilation Cache): over time, deterministic
rules move out of prompts into code — prompt instructions
primarily govern personality, judgment, relational
behavior, and nuanced cognition, while code governs
expiration, permissions, limits, routing, formatting,
and deterministic constraints — and the persona compiles
once, caching generated artefacts (persona_kernel.txt,
persona_ir.json, persona_sections.jsonl,
persona_embeddings.db, persona_manifest.json) while
humans edit only Markdown + YAML configuration. These
are pure contract surfaces: no live prompt is migrated,
no cache is persisted, and nothing is injected. Tests
load through real plugin discovery.
"""

from __future__ import annotations

import copy
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

# Memory Retention

Retention keeps what serves the work and lets the rest fade.
"""

AVATAR_DOC = """# Generating Images

Generating images follows the canonical appearance record.

# Ordinary Text Inference

Ordinary text inference proceeds without embodiment detail.
"""

DOCS = {
    "core": ("core.md", CORE_DOC),
    "memory_policy": ("memory_policy.md", MEMORY_POLICY_DOC),
    "avatar": ("avatar.md", AVATAR_DOC),
}

PROMPT_KINDS = [
    "personality", "judgment", "relational_behavior",
    "nuanced_cognition",
]

CODE_KINDS = [
    "expiration", "permissions", "limits", "routing",
    "formatting", "deterministic_constraints",
]

CACHE_FILES = [
    {"file": "persona_kernel.txt", "kind": "kernel",
     "generated": True},
    {"file": "persona_ir.json", "kind": "ir",
     "generated": True},
    {"file": "persona_sections.jsonl", "kind": "sections",
     "generated": True},
    {"file": "persona_embeddings.db", "kind": "embeddings",
     "generated": True},
    {"file": "persona_manifest.json", "kind": "manifest",
     "generated": True},
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
        "anchors": ["Caducea counsels, she does not command."],
        "anti_anchors": ["Caducea never claims to be human."],
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


def _compiled(runtime):
    return runtime.PersonaCompiler(_Ctx(ENABLED)).compile()


def test_policy_code_contract_and_lists():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.policy_to_code_contract()
        prompt = runtime.policy_governs()
        prompt.append("tampered")
        code = runtime.code_governs()
        code.append("tampered")
        fresh_prompt = runtime.policy_governs()
        fresh_code = runtime.code_governs()
    finally:
        mods[0].unload()
    assert fresh_prompt == PROMPT_KINDS
    assert fresh_code == CODE_KINDS
    assert list(runtime.PROMPT_GOVERNS) == PROMPT_KINDS
    assert list(runtime.CODE_GOVERNS) == CODE_KINDS
    assert contract == {
        "name": "PolicyToCodeMigration",
        "prompt_governs": PROMPT_KINDS,
        "code_governs": CODE_KINDS,
        "migration_direction": "prompt_to_code",
        "migrates": "deterministic_rules",
        "example": {
            "prompt_instruction":
                "Never include expired memories.",
            "code_rule": "if memory.expired: exclude()",
        },
        "migrates_live_prompts": False,
        "owns_prompts": False,
        "injects": False,
    }


def test_classify_rule_kinds_prompt_and_code():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.classify_rule_kinds(
            "personality, judgment, relational behavior, "
            "and nuanced cognition") == PROMPT_KINDS
        assert runtime.classify_rule_kinds(
            "expiration, permissions, limits, routing, "
            "formatting, and deterministic constraints"
        ) == CODE_KINDS
        # Prompt kinds always stand ahead of code kinds,
        # each in roadmap order, whatever the text order.
        assert runtime.classify_rule_kinds(
            "routing limits personality") == [
                "personality", "limits", "routing"]
    finally:
        mods[0].unload()


def test_classify_rule_kinds_empty_and_malformed():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.classify_rule_kinds("") == []
        assert runtime.classify_rule_kinds(
            "wizardry and tea") == []
        for bad in (None, 42, ["expiration"]):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.classify_rule_kinds(bad)
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.migration_assessment(bad)
    finally:
        mods[0].unload()


def test_roadmap_example_is_a_code_migration_candidate():
    mods = _load_modules()
    runtime = mods[1]
    try:
        # §47's own example: the prompt instruction
        # "Never include expired memories." is a
        # deterministic expiration rule standing in
        # prompt form — code should govern it.
        assessment = runtime.migration_assessment(
            "Never include expired memories")
    finally:
        mods[0].unload()
    assert assessment == {
        "kinds": ["expiration"],
        "prompt_governed_kinds": [],
        "code_governed_kinds": ["expiration"],
        "migration_candidate": True,
        "governed_by": "code",
    }


def test_governance_for_kind():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.governance_for_kind(
            "personality") == "prompt"
        assert runtime.governance_for_kind(
            "expiration") == "code"
        # Slugified and case-insensitive, like the
        # neighbouring explicit-name validators.
        assert runtime.governance_for_kind(
            "Relational Behavior") == "prompt"
        assert runtime.governance_for_kind(
            "Deterministic Constraints") == "code"
        assert runtime.governance_for_kind(
            "FORMATTING") == "code"
        for bad in ("wizardry", "", None, 42):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.governance_for_kind(bad)
    finally:
        mods[0].unload()


def test_migration_assessment_mixed_and_prompt_only():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mixed = runtime.migration_assessment(
            "nuanced judgment about routing and formatting")
        prompt_only = runtime.migration_assessment(
            "personality and nuanced cognition")
        unclassified = runtime.migration_assessment(
            "wizardry and tea")
    finally:
        mods[0].unload()
    assert mixed == {
        "kinds": [
            "judgment", "nuanced_cognition", "routing",
            "formatting"],
        "prompt_governed_kinds": [
            "judgment", "nuanced_cognition"],
        "code_governed_kinds": ["routing", "formatting"],
        "migration_candidate": True,
        "governed_by": "mixed",
    }
    assert prompt_only == {
        "kinds": ["personality", "nuanced_cognition"],
        "prompt_governed_kinds": [
            "personality", "nuanced_cognition"],
        "code_governed_kinds": [],
        "migration_candidate": False,
        "governed_by": "prompt",
    }
    assert unclassified == {
        "kinds": [],
        "prompt_governed_kinds": [],
        "code_governed_kinds": [],
        "migration_candidate": False,
        "governed_by": "unclassified",
    }


def test_compilation_cache_artifacts_and_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.compilation_cache_contract()
        artifacts = runtime.compilation_cache_artifacts()
        artifacts[0]["generated"] = False
        artifacts.append({"file": "x", "kind": "x",
                          "generated": True})
        fresh = runtime.compilation_cache_artifacts()
    finally:
        mods[0].unload()
    assert fresh == CACHE_FILES
    assert [tuple(pair) for pair in runtime.CACHE_ARTIFACTS] == [
        (row["file"], row["kind"]) for row in CACHE_FILES]
    assert contract == {
        "name": "PersonaCompilationCache",
        "artifacts": CACHE_FILES,
        "compile_once": True,
        "artifacts_are_generated": True,
        "humans_edit": ["markdown", "yaml_configuration"],
        "persists_cache": False,
        "writes_cache": False,
        "injects": False,
    }


def test_cache_manifest_shape_and_determinism():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        manifest = runtime.cache_manifest(compiled)
        again = runtime.cache_manifest(_compiled(runtime))
        record = runtime.hash_record(compiled)
        valid = runtime.validate_cache_manifest(manifest, compiled)
        stale = runtime.cache_staleness(manifest, compiled)
    finally:
        mods[0].unload()
    assert manifest == again
    assert manifest["persona_id"] == "caducea"
    assert manifest["persona_version"] == record["persona_version"]
    assert manifest["compiled_at"] is None
    assert manifest["embeddings_note"] == runtime.EMBEDDINGS_HASH_NOTE
    by_kind = {row["kind"]: row for row in manifest["artifacts"]}
    assert [row["kind"] for row in manifest["artifacts"]] == [
        "kernel", "ir", "sections", "embeddings", "manifest"]
    assert by_kind["kernel"]["sha256"] == compiled["kernel"]["sha256"]
    assert by_kind["kernel"]["file"] == "persona_kernel.txt"
    assert by_kind["ir"]["sha256"] == compiled["ir"]["ir_hash"]
    assert by_kind["manifest"]["sha256"] == compiled["persona_hash"]
    sections_hash = by_kind["sections"]["sha256"]
    assert isinstance(sections_hash, str)
    assert len(sections_hash) == 64
    # §48 honesty (§13): no embedding surface is owned,
    # so the embeddings hash is None, never faked.
    assert by_kind["embeddings"]["sha256"] is None
    assert all(row["generated"] is True
               for row in manifest["artifacts"])
    assert valid is True
    assert stale == {"valid": True, "changed": [], "missing": []}


def test_cache_manifest_stamp_alone_is_not_a_change():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        stamped = runtime.cache_manifest(
            compiled, compiled_at="2026-10-31T00:00:00+00:00")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.cache_manifest(compiled, compiled_at="soon")
        with pytest.raises(runtime.PersonaRuntimeError):
            # A naive stamp is refused (§19 handling).
            runtime.cache_manifest(
                compiled, compiled_at="2026-10-31T00:00:00")
        stale = runtime.cache_staleness(stamped, compiled)
        valid = runtime.validate_cache_manifest(stamped, compiled)
    finally:
        mods[0].unload()
    assert stamped["compiled_at"] == "2026-10-31T00:00:00+00:00"
    # §19: the stamp is a caller stamp, not persona
    # material — validity survives a stamp difference.
    assert stale == {"valid": True, "changed": [], "missing": []}
    assert valid is True


def test_cache_staleness_tampered_changed_and_missing():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        manifest = runtime.cache_manifest(compiled)
        tampered = copy.deepcopy(manifest)
        for row in tampered["artifacts"]:
            if row["kind"] == "kernel":
                row["sha256"] = "0" * 64
        altered = copy.deepcopy(compiled)
        altered["index"][0]["text"] += "\nAn extra line."
        missing = copy.deepcopy(manifest)
        missing["artifacts"] = [
            row for row in missing["artifacts"]
            if row["kind"] != "sections"]
        tampered_stale = runtime.cache_staleness(tampered, compiled)
        altered_stale = runtime.cache_staleness(manifest, altered)
        missing_stale = runtime.cache_staleness(missing, compiled)
        tampered_valid = runtime.validate_cache_manifest(
            tampered, compiled)
        altered_valid = runtime.validate_cache_manifest(
            manifest, altered)
        missing_valid = runtime.validate_cache_manifest(
            missing, compiled)
    finally:
        mods[0].unload()
    assert tampered_stale == {
        "valid": False, "changed": ["kernel"], "missing": []}
    assert tampered_valid is False
    assert altered_stale == {
        "valid": False, "changed": ["sections"], "missing": []}
    assert altered_valid is False
    assert missing_stale == {
        "valid": False, "changed": [], "missing": ["sections"]}
    assert missing_valid is False


def test_cache_manifest_malformed_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        manifest = runtime.cache_manifest(compiled)
        for bad_compiled in (None, {}, {"persona_id": "x"}):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.cache_manifest(bad_compiled)
        no_ir = copy.deepcopy(compiled)
        del no_ir["ir"]
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.cache_manifest(no_ir)
        for bad_manifest in (None, "manifest", {}):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.validate_cache_manifest(
                    bad_manifest, compiled)
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.cache_staleness(bad_manifest, compiled)
        broken = copy.deepcopy(manifest)
        del broken["artifacts"]
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.validate_cache_manifest(broken, compiled)
        faked = copy.deepcopy(manifest)
        for row in faked["artifacts"]:
            if row["kind"] == "embeddings":
                row["sha256"] = "f" * 64
        with pytest.raises(runtime.PersonaRuntimeError):
            # An embeddings hash this layer cannot own is
            # a malformed manifest, not a stale one.
            runtime.validate_cache_manifest(faked, compiled)
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
        compiled = _compiled(runtime)
        manifest = runtime.cache_manifest(compiled)
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
            other = _compiled(runtime)
            cross = runtime.cache_staleness(manifest, other)
        finally:
            reset_hermes_home_override(token)
        back = _compiled(runtime)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        valid_back = runtime.validate_cache_manifest(manifest, back)
        valid_other = runtime.validate_cache_manifest(
            manifest, other)
    finally:
        mods[0].unload()
    assert before == after
    assert first[0].content == second[0].content == third[0].content
    assert back["persona_hash"] == compiled["persona_hash"]
    assert valid_back is True
    # A manifest for one persona never validates against
    # another persona's compile.
    assert cross["valid"] is False
    assert "manifest" in cross["changed"]
    assert valid_other is False
    assert len(first) == 1
    content = first[0].content
    assert "§§3-76" in content
    assert "§47 policy to code" in content
    assert "personality, judgment" in content
    assert "deterministic constraints" in content
    assert "§48 compilation cache" in content
    assert "Markdown and" in content
    assert "persists" in content and "no cache" in content
    # The packet names the contracts only — never canonical
    # persona text or authored anchor prose.
    assert "longhouse terminal" not in content
    assert "does not command" not in content
