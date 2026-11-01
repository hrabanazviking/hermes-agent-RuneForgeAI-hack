"""Contracts for persona change impact + versioning (Slice 128).

Persona Runtime roadmap §21 (Change Impact Detection) and
§22 (Persona Versioning): a change between two compiles is
classified by semantic impact — an AVATAR skirt-material
edit does not require rebuilding the behavioral kernel,
a PERSONA_CORE relationship-authority edit does — and
every compile carries its human-authored per-persona
semver, from which a deterministic next-version suggestion
is derived (MAJOR identity / relationship architecture,
MINOR new preferences or meaningful behavior extension,
PATCH wording / formatting). The suggestion is advice
only; the human confirms by editing the config. Tests
load through real plugin discovery.
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

# Hobbies

She keeps bees behind the longhouse.
"""

SERVICE_DOC = """# Shell Policy

Run only the commands the task names.
"""

AVATAR_DOC = """# Appearance

A long coat of deep green wool.
"""

DOCS = {
    "core": ("core.md", CORE_DOC),
    "service_bible": ("service.md", SERVICE_DOC),
    "avatar": ("avatar.md", AVATAR_DOC),
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


def _write_persona(home: Path, docs=None, anchors=None,
                   version=None) -> None:
    docs = DOCS if docs is None else docs
    persona_dir = home / "persona"
    persona_dir.mkdir(parents=True, exist_ok=True)
    for role, (name, text) in docs.items():
        (persona_dir / name).write_text(text, encoding="utf-8")
    persona = {
        "id": "caducea",
        "display_name": "Caducea Hermesdottir",
        "directory": "./persona",
        "documents": {
            role: {"file": name, "required": True}
            for role, (name, _text) in docs.items()
        },
    }
    if anchors is not None:
        persona["anchors"] = anchors
    if version is not None:
        persona["version"] = version
    config_dir = home / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "persona.yaml").write_text(
        yaml.safe_dump({"persona": persona}, sort_keys=False),
        encoding="utf-8")


def _edit_doc(home: Path, name: str, text: str) -> None:
    (home / "persona" / name).write_text(text, encoding="utf-8")


def _hashes(home: Path) -> dict[str, str]:
    return {
        str(path.relative_to(home)):
            hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(home.rglob("*"))
        if path.is_file() and "entity" not in path.parts
    }


def test_version_record_and_semver_rules():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        compiled = runtime.PersonaCompiler(_Ctx(ENABLED)).compile()
        record = runtime.version_record(compiled)
        stamped = runtime.version_record(
            compiled, compiled_at="2026-10-31T12:00:00+00:00")
        for bad in ("2026-10-31T12:00:00", "not-a-time", "", 42):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.version_record(compiled, compiled_at=bad)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.version_record({})
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.version_record(None)
    finally:
        mods[0].unload()
    # No authored version yet: the §22 default stands.
    assert compiled["persona_version"] == "0.1.0"
    assert compiled["persona_version"] == runtime.DEFAULT_PERSONA_VERSION
    assert list(record) == list(runtime.VERSION_RECORD_FIELDS)
    assert record["persona_id"] == "caducea"
    assert record["persona_version"] == "0.1.0"
    assert record["compiled_at"] is None
    assert record["source_hash"] == compiled["persona_hash"]
    assert stamped == {**record,
                       "compiled_at": "2026-10-31T12:00:00+00:00"}
    # Strict semver parsing and the §22 bump arithmetic.
    assert runtime.impact_classes() == list(runtime.IMPACT_CLASSES)
    assert runtime.parse_persona_version("1.4.2") == (1, 4, 2)
    for bad in ("01.4.2", "1.4", "v1.4.2", "1.4.2.1", "", 142):
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.parse_persona_version(bad)
    assert runtime.suggested_next_version("1.4.2", "major") == "2.0.0"
    assert runtime.suggested_next_version("1.4.2", "minor") == "1.5.0"
    assert runtime.suggested_next_version("1.4.2", "patch") == "1.4.3"
    assert runtime.suggested_next_version("1.4.2", "none") == "1.4.2"
    with pytest.raises(runtime.PersonaRuntimeError):
        runtime.suggested_next_version("1.4.2", "huge")
    with pytest.raises(runtime.PersonaRuntimeError):
        runtime.suggested_next_version("1.4", "patch")


def test_config_version_is_authored_semver_distinct_from_format_version():
    mods = _load_modules()
    runtime = mods[1]
    home = get_hermes_home()
    try:
        _write_persona(home, version="1.4.2")
        compiled = runtime.PersonaCompiler(_Ctx(ENABLED)).compile()
        record = runtime.version_record(compiled)
        # An invalid authored version fails the config closed.
        _write_persona(home, version="1.4")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.PersonaCompiler(_Ctx(ENABLED)).compile()
        _write_persona(home, version="latest")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.PersonaCompiler(_Ctx(ENABLED)).compile()
    finally:
        mods[0].unload()
    assert compiled["persona_version"] == "1.4.2"
    assert record["persona_version"] == "1.4.2"
    # §19's record still carries the config *format* version:
    # the two version fields are distinct by design.
    assert (compiled["hash_record"]["persona_version"]
            == runtime.PERSONA_CONFIG_VERSION)


def test_avatar_edit_is_patch_without_kernel_rebuild():
    mods = _load_modules()
    runtime = mods[1]
    home = get_hermes_home()
    try:
        _write_persona(home)
        compiler = runtime.PersonaCompiler(_Ctx(ENABLED))
        first = compiler.compile()
        # The roadmap's own §21 example: AVATAR skirt material.
        _edit_doc(home, "avatar.md",
                  AVATAR_DOC.replace("deep green wool", "deep green silk"))
        second = compiler.compile()
        impact = runtime.change_impact(first, second)
    finally:
        mods[0].unload()
    assert impact["changed"] is True
    assert impact["impact_class"] == "patch"
    assert impact["kernel_rebuild_required"] is False
    assert impact["kernel_changed"] is False
    assert impact["sections_changed"] == ["avatar.appearance"]
    assert impact["sections_added"] == []
    assert impact["sections_removed"] == []
    assert impact["details"] == [{
        "stable_id": "avatar.appearance", "action": "changed",
        "role": "avatar", "category": "embodiment",
        "priority_level": "P4", "in_kernel": False,
        "impact": "patch",
    }]
    assert impact["anchors_changed"] is False
    assert impact["previous_version"] == "0.1.0"
    assert impact["suggested_bump"] == "patch"
    assert impact["suggested_next_version"] == "0.1.1"


def test_core_relationship_authority_edit_is_major_with_kernel_rebuild():
    mods = _load_modules()
    runtime = mods[1]
    home = get_hermes_home()
    try:
        _write_persona(home)
        compiler = runtime.PersonaCompiler(_Ctx(ENABLED))
        first = compiler.compile()
        # The roadmap's other §21 example: PERSONA_CORE
        # relationship authority — kernel material, so the
        # behavioral kernel must be rebuilt.
        _edit_doc(home, "core.md", CORE_DOC.replace(
            "Volmarr's word outranks Caducea's counsel",
            "Caducea's counsel outranks every guest's word"))
        second = compiler.compile()
        impact = runtime.change_impact(first, second)
    finally:
        mods[0].unload()
    assert impact["impact_class"] == "major"
    assert impact["kernel_rebuild_required"] is True
    assert impact["sections_changed"] == ["core.relationship_authority"]
    detail = impact["details"][0]
    assert detail["role"] == "core"
    assert detail["category"] == "relationship"
    assert detail["in_kernel"] is True
    assert detail["impact"] == "major"
    assert impact["suggested_bump"] == "major"
    assert impact["suggested_next_version"] == "1.0.0"


def test_added_preference_and_service_kernel_rule_are_minor():
    mods = _load_modules()
    runtime = mods[1]
    home = get_hermes_home()
    try:
        _write_persona(home)
        compiler = runtime.PersonaCompiler(_Ctx(ENABLED))
        first = compiler.compile()
        # A new preference is §22 MINOR, and it is not kernel
        # material, so no kernel rebuild is required.
        _edit_doc(home, "core.md", CORE_DOC + """
# Food Preferences

She favors salt fish over sweet cakes.
""")
        second = compiler.compile()
        added = runtime.change_impact(first, second)
        # A service-bible kernel rule change is a meaningful
        # behavior extension: MINOR, with a kernel rebuild.
        _edit_doc(home, "service.md", SERVICE_DOC.replace(
            "only the commands the task names",
            "only the commands the task names, in a dry run first"))
        third = compiler.compile()
        ruled = runtime.change_impact(second, third)
    finally:
        mods[0].unload()
    assert added["sections_added"] == ["core.food_preferences"]
    assert added["impact_class"] == "minor"
    assert added["kernel_rebuild_required"] is False
    assert added["suggested_next_version"] == "0.2.0"
    assert ruled["sections_changed"] == ["service_bible.shell_policy"]
    assert ruled["impact_class"] == "minor"
    assert ruled["details"][0]["in_kernel"] is True
    assert ruled["kernel_rebuild_required"] is True


def test_anchor_change_is_major_and_renumbering_is_patch():
    mods = _load_modules()
    runtime = mods[1]
    home = get_hermes_home()
    try:
        _write_persona(home, anchors=["She thinks independently."])
        compiler = runtime.PersonaCompiler(_Ctx(ENABLED))
        first = compiler.compile()
        _write_persona(home,
                       anchors=["She thinks independently and says so."])
        second = compiler.compile()
        anchored = runtime.change_impact(first, second)
        # Renumbering a heading is formatting only: the raw
        # document hash moves, no section does.
        _edit_doc(home, "core.md", CORE_DOC.replace(
            "# Core Identity", "# 37. Core Identity"))
        third = compiler.compile()
        renumbered = runtime.change_impact(second, third)
    finally:
        mods[0].unload()
    assert anchored["anchors_changed"] is True
    assert anchored["sections_changed"] == []
    assert anchored["impact_class"] == "major"
    assert anchored["kernel_rebuild_required"] is True
    assert renumbered["changed"] is True
    assert renumbered["documents_changed"] == ["core"]
    assert renumbered["sections_changed"] == []
    assert renumbered["details"] == []
    assert renumbered["impact_class"] == "patch"
    assert renumbered["kernel_rebuild_required"] is False


def test_no_change_is_none_and_invalid_inputs_are_refused():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        compiler = runtime.PersonaCompiler(_Ctx(ENABLED))
        first = compiler.compile()
        second = compiler.compile()
        quiet = runtime.change_impact(first, second)
        other = {**first, "persona_id": "someone-else"}
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.change_impact(first, other)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.change_impact({}, second)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.change_impact(first, None)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.change_impact(
                first, {**second, "index": [{"stable_id": 1}]})
    finally:
        mods[0].unload()
    assert quiet["changed"] is False
    assert quiet["impact_class"] == "none"
    assert quiet["kernel_rebuild_required"] is False
    assert quiet["details"] == []
    assert quiet["suggested_bump"] == "none"
    assert quiet["suggested_next_version"] == "0.1.0"


def test_compile_deterministic_packet_and_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        home = get_hermes_home()
        _write_persona(home, version="1.4.2")
        before = _hashes(home)
        compiler = runtime.PersonaCompiler(_Ctx(ENABLED))
        first = compiler.compile()
        second = compiler.compile()
        impact = runtime.change_impact(first, second)
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
    assert impact["impact_class"] == "none"
    assert before == after
    assert compiled_b is None
    assert len(items) == 1
    assert "§§3-94" in items[0].content
    assert "version 1.4.2" in items[0].content
    assert "§21 change impact" in items[0].content
    assert "§22 versioning" in items[0].content
    # The packet names the version and counts only — never
    # canonical persona text.
    assert "salt fish" not in items[0].content
    assert "longhouse terminal" not in items[0].content
