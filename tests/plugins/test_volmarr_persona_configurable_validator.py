"""Contracts for configurable priorities + validator (Slice 152).

Persona Runtime roadmap §69 (Configurable Priorities) and
§70 (Persona Validator): a ``persona.precedence`` list
may order the six document roles — the shipped safe
default is the roadmap's example (core, relationship,
service_bible, tool_policy, memory_policy, avatar) —
under two non-configurable safety rails (the persona
core first, every branch document below the service
bible), and the compile-time validator catalogue names
the eight §70 issue kinds with the banked surfaces
that detect them at honest levels (compile-time,
partial, or not detected), warns the human, and never
silently invents missing character traits. These are
pure surfaces: no config loader behaviour changes, no
second compiler runs, and no prose is interpreted.
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

DEFAULT_PRECEDENCE = [
    "core", "relationship", "service_bible",
    "tool_policy", "memory_policy", "avatar",
]

CANONICAL_ROLES = [
    "core", "relationship", "service_bible",
    "memory_policy", "tool_policy", "avatar",
]

VALIDATOR_ISSUES = [
    "contradictory_directives",
    "missing_required_files",
    "duplicate_identities",
    "invalid_references",
    "extreme_token_size",
    "broken_markdown",
    "empty_sections",
    "unresolvable_paths",
]

COMPILE_TIME = [
    "missing_required_files",
    "extreme_token_size",
    "unresolvable_paths",
]

PARTIAL = ["duplicate_identities", "invalid_references"]

NOT_DETECTED = [
    "contradictory_directives",
    "broken_markdown",
    "empty_sections",
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


def test_default_precedence_and_example():
    mods = _load_modules()
    runtime = mods[1]
    try:
        default = runtime.default_precedence()
        default.append("x")
        roles = runtime.configurable_precedence_roles()
        roles.append("x")
    finally:
        mods[0].unload()
    assert runtime.default_precedence() == DEFAULT_PRECEDENCE
    assert list(runtime.CONFIGURABLE_PRECEDENCE_DEFAULT) == \
        DEFAULT_PRECEDENCE
    assert runtime.configurable_precedence_roles() == \
        CANONICAL_ROLES
    # The default is exactly the §69 roadmap example, and
    # its roles are the six §67 compiler roles.
    assert runtime.configurable_precedence_example() == {
        "persona": {"precedence": DEFAULT_PRECEDENCE}}
    assert set(DEFAULT_PRECEDENCE) == \
        set(runtime.CORE_ROLES) == set(CANONICAL_ROLES)
    assert runtime.CONFIGURABLE_PRECEDENCE_CONFIG_KEY == \
        "persona.precedence"
    # The default differs from the §67 traversal order
    # only in the branch order: the example puts
    # tool_policy before memory_policy, which §67 leaves
    # tied as siblings.
    canonical = [runtime.canonical_file_role(document)
                 for document in runtime.canonical_file_order()]
    assert canonical == CANONICAL_ROLES
    assert DEFAULT_PRECEDENCE[:3] == canonical[:3]
    assert sorted(DEFAULT_PRECEDENCE[3:]) == \
        sorted(canonical[3:])


def test_validate_precedence_accepts_configurations():
    mods = _load_modules()
    runtime = mods[1]
    try:
        validate = runtime.validate_precedence
        assert validate(DEFAULT_PRECEDENCE) == DEFAULT_PRECEDENCE
        assert validate(tuple(DEFAULT_PRECEDENCE)) == \
            DEFAULT_PRECEDENCE
        # Roadmap document names resolve to roles.
        assert validate([
            "PERSONA_CORE", "RELATIONSHIP_MODEL",
            "SERVICE_BIBLE", "TOOL_POLICY", "MEMORY_POLICY",
            "AVATAR"]) == DEFAULT_PRECEDENCE
        # The branch order is the human's configuration.
        assert validate([
            "core", "relationship", "service_bible",
            "memory_policy", "avatar", "tool_policy"]) == [
            "core", "relationship", "service_bible",
            "memory_policy", "avatar", "tool_policy"]
        # Relationship and service bible may swap below
        # the core.
        assert validate([
            "core", "service_bible", "relationship",
            "avatar", "tool_policy", "memory_policy"]) == [
            "core", "service_bible", "relationship",
            "avatar", "tool_policy", "memory_policy"]
    finally:
        mods[0].unload()


def test_validate_precedence_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        validate = runtime.validate_precedence
        for bad in (
                None, "core", 42, {"core": 1},
                [],
                # Incomplete: a role is missing.
                ["core", "relationship", "service_bible",
                 "tool_policy", "memory_policy"],
                # Duplicated after resolution (document name
                # and role name the same document).
                ["core", "relationship", "service_bible",
                 "tool_policy", "memory_policy", "PERSONA_CORE"],
                # Unknown role.
                ["core", "relationship", "service_bible",
                 "tool_policy", "memory_policy", "unknown"],
                # A bare memory names no document (§67).
                ["core", "relationship", "service_bible",
                 "tool_policy", "memory", "avatar"],
                # Rail: the core must stand first.
                ["relationship", "core", "service_bible",
                 "tool_policy", "memory_policy", "avatar"],
                # Rail: a branch document above its parent,
                # the service bible.
                ["core", "relationship", "tool_policy",
                 "service_bible", "memory_policy", "avatar"],
                ["core", "avatar", "relationship",
                 "service_bible", "tool_policy",
                 "memory_policy"],
                [None, "relationship", "service_bible",
                 "tool_policy", "memory_policy", "avatar"],
        ):
            with pytest.raises(runtime.PersonaRuntimeError):
                validate(bad)
    finally:
        mods[0].unload()


def test_resolve_rank_winner_and_outranks():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.resolve_precedence() == DEFAULT_PRECEDENCE
        assert runtime.resolve_precedence(None) == \
            DEFAULT_PRECEDENCE
        custom = ["core", "relationship", "service_bible",
                  "memory_policy", "avatar", "tool_policy"]
        assert runtime.resolve_precedence(custom) == custom
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.resolve_precedence(["core"])
        assert runtime.configurable_precedence_rank("core") == 0
        assert runtime.configurable_precedence_rank(
            "PERSONA_CORE") == 0
        assert runtime.configurable_precedence_rank("avatar") == 5
        # Under the default the example's branch order
        # holds: tool_policy outranks memory_policy,
        # reversing their §67 sibling tie.
        assert runtime.configurable_precedence_outranks(
            "tool_policy", "memory_policy")
        assert not runtime.configurable_precedence_outranks(
            "memory_policy", "tool_policy")
        assert not runtime.canonical_file_outranks(
            "tool_policy", "memory_policy")
        # Under a custom list the branch order follows
        # the human's configuration.
        assert runtime.configurable_precedence_outranks(
            "memory_policy", "tool_policy", precedence=custom)
        assert runtime.configurable_precedence_winner(
            "avatar", "tool_policy") == "tool_policy"
        assert runtime.configurable_precedence_winner(
            "avatar", "tool_policy",
            precedence=custom) == "avatar"
        assert runtime.configurable_precedence_winner(
            "core", "core") == "core"
        assert runtime.configurable_precedence_rank(
            "tool_policy", precedence=custom) == 5
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.configurable_precedence_rank("memory")
    finally:
        mods[0].unload()


def test_configurable_priorities_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.configurable_priorities_contract()
    finally:
        mods[0].unload()
    assert contract == {
        "name": "ConfigurablePriorities",
        "config_key": "persona.precedence",
        "default": DEFAULT_PRECEDENCE,
        "roles": CANONICAL_ROLES,
        "example": {"persona": {"precedence": DEFAULT_PRECEDENCE}},
        "safe_defaults": True,
        "core_first": True,
        "branches_below_service_bible": True,
        "canonical_basis": "§67 canonical file priority",
        "changes_config_loader": False,
    }


def test_precedence_surfaces_coexist_with_section24():
    mods = _load_modules()
    runtime = mods[1]
    try:
        # Regression guard: the §69 role tuple must not
        # shadow the §24 precedence-tier role map —
        # classify_influence reads it by tier name.
        classified = runtime.classify_influence("core")
        order = runtime.precedence_order()
    finally:
        mods[0].unload()
    assert classified["document_role"] == "core"
    assert classified["tier"] == "persona_core"
    assert [row["document_role"] for row in order[:3]] == [
        "core", "relationship", "service_bible"]


def test_validator_issues_and_catalogue():
    mods = _load_modules()
    runtime = mods[1]
    try:
        issues = runtime.validator_issues()
        issues.append("x")
        catalogue = runtime.persona_validator_catalogue()
        catalogue[0]["issue"] = "x"
    finally:
        mods[0].unload()
    assert runtime.validator_issues() == VALIDATOR_ISSUES
    assert list(runtime.VALIDATOR_ISSUES) == VALIDATOR_ISSUES
    rows = runtime.persona_validator_catalogue()
    assert [row["issue"] for row in rows] == VALIDATOR_ISSUES
    assert [row["name"] for row in rows] == [
        "contradictory directives", "missing required files",
        "duplicate identities", "invalid references",
        "extreme token size", "broken Markdown",
        "empty sections", "unresolvable paths"]
    assert all(row["warn_human"] for row in rows)
    assert {row["detection"] for row in rows} == {
        "compile_time", "partial", "not_detected"}
    by_issue = {row["issue"]: row for row in rows}
    assert by_issue["missing_required_files"]["detector"] == \
        "PersonaCompiler.compile (§6)"
    assert by_issue["unresolvable_paths"]["detector"] == \
        "PersonaConfigStore.document_path (§3)"
    assert by_issue["contradictory_directives"]["detector"] == \
        "none"
    assert by_issue["broken_markdown"]["detector"] == "none"
    assert by_issue["empty_sections"]["detector"] == "none"


def test_validator_issue_resolution_and_detection():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.persona_validator_detection(
            "missing_required_files") == "compile_time"
        assert runtime.persona_validator_detection(
            "Missing Required Files") == "compile_time"
        assert runtime.persona_validator_detection(
            "extreme_token_size") == "compile_time"
        assert runtime.persona_validator_detection(
            "unresolvable_paths") == "compile_time"
        assert runtime.persona_validator_detection(
            "duplicate_identities") == "partial"
        assert runtime.persona_validator_detection(
            "invalid_references") == "partial"
        assert runtime.persona_validator_detection(
            "contradictory_directives") == "not_detected"
        assert runtime.persona_validator_detection(
            "broken_markdown") == "not_detected"
        assert runtime.persona_validator_detection(
            "empty_sections") == "not_detected"
        row = runtime.persona_validator_issue(
            "extreme token size")
        assert row["issue"] == "extreme_token_size"
        assert row == runtime.persona_validator_catalogue()[4]
        for bad in ("", "   ", None, 7, ["core"],
                    "missing_files", "unknown_issue"):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.persona_validator_issue(bad)
    finally:
        mods[0].unload()


def test_validator_detection_matches_banked_surfaces():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        compiled = runtime.PersonaCompiler(_Ctx()).compile()
        assert compiled is not None
        assert compiled["missing_optional"] == []
        # Compile-time detection is real: deleting a
        # required document fails the compile closed —
        # the §70 missing-required-files detector.
        (home / "persona" / "memory_policy.md").unlink()
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.PersonaCompiler(_Ctx()).compile()
        # The detector named for unresolvable paths is
        # the config store's own document_path check.
        _write_persona(home)
        config = runtime.PersonaConfigStore(_Ctx()).read()
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.PersonaConfigStore(_Ctx()).document_path(
                config, {"role": "core", "file": "../escape.md",
                         "required": True, "extension": False})
    finally:
        mods[0].unload()


def test_persona_validator_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.persona_validator_contract()
    finally:
        mods[0].unload()
    assert contract == {
        "name": "PersonaValidator",
        "issues": VALIDATOR_ISSUES,
        "compile_time_detected": COMPILE_TIME,
        "partially_detected": PARTIAL,
        "not_detected": NOT_DETECTED,
        "warns_human": True,
        "invents_missing_traits": False,
        "second_compiler": False,
        "interprets_prose": False,
    }
    # The three detection lists partition the catalogue.
    assert sorted(COMPILE_TIME + PARTIAL + NOT_DETECTED) == \
        sorted(VALIDATOR_ISSUES)


def test_packet_determinism_and_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        home = get_hermes_home()
        _write_persona(home)
        before = _hashes(home)
        contract = runtime.persona_validator_contract()
        first = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        second = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        after = _hashes(home)
        token = set_hermes_home_override(str(profile_b))
        try:
            _write_profile(profile_b)
            mods[2].IdentityStore(_Ctx()).ensure()
            _write_persona(
                profile_b, persona_id="other",
                core_doc=OTHER_CORE_DOC)
            other_contract = runtime.persona_validator_contract()
        finally:
            reset_hermes_home_override(token)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert before == after
    assert contract == other_contract
    assert first[0].content == second[0].content == third[0].content
    assert len(first) == 1
    content = first[0].content
    assert "§§3-90" in content
    assert "§69 configurable priorities" in content
    assert "safe" in content
    assert "§70 persona validator" in content
    assert "never silently invented" in content
    # The packet names the contracts only — never canonical
    # persona text.
    assert "longhouse terminal" not in content
