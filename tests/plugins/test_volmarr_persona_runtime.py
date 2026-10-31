"""Contracts for the persona runtime foundations (Slice 118).

Persona Runtime roadmap §§3-6: human-editable configuration
naming semantic document roles (never filename conventions),
an optional document extension system (extra roles are
first-class, no code change), the three-layer model (kernel /
retrieval index / canonical documents), and a deterministic
persona compiler that runs only when explicitly called and
writes nothing. Tests load through real plugin discovery.
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

I am Caducea, a persistent Hermes entity.

# Communication Style

Plain words first, warmth always.

# Deep Lore Appendix

""" + ("lore line\n" * 400)

SERVICE_DOC = """# Coding Preferences

Test everything twice.

# Shell Policy

Never force-push.
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


def _write_persona(home: Path, *, extra_role=False,
                   omit_optional=False) -> dict:
    persona_dir = home / "persona"
    persona_dir.mkdir(parents=True, exist_ok=True)
    (persona_dir / "whatever_core_name.md").write_text(
        CORE_DOC, encoding="utf-8")
    (persona_dir / "bible.md").write_text(SERVICE_DOC, encoding="utf-8")
    documents = {
        "core": {"file": "whatever_core_name.md", "required": True},
        "service_bible": {"file": "bible.md", "required": True},
        "avatar": {"file": "avatar.md", "required": False},
    }
    if extra_role:
        (persona_dir / "spirit.md").write_text(
            "# Spiritual Model\n\nFrith above all.\n", encoding="utf-8")
        documents["spirituality"] = {"file": "spirit.md"}
    if not omit_optional:
        (persona_dir / "avatar.md").write_text(
            "# Avatar\n\nRaven hair.\n", encoding="utf-8")
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


def test_compile_builds_three_layers_from_roles_not_filenames():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        compiled = runtime.PersonaCompiler(_Ctx(ENABLED)).compile()
    finally:
        mods[0].unload()
    assert compiled["persona_id"] == "caducea"
    assert [doc["role"] for doc in compiled["documents"]] == [
        "core", "service_bible", "avatar"]
    assert compiled["missing_optional"] == []
    # Layer A (§9, Slice 120): the kernel-marked core sections
    # plus the service bible's policy section as a service
    # rule — not the lore, not coding preferences.
    assert compiled["kernel"]["section_ids"] == [
        "core_identity", "communication_style", "shell_policy"]
    assert compiled["kernel"]["sources"][-1] == {
        "role": "service_bible", "kind": "service_rule",
        "section_id": "shell_policy"}
    assert "lore line" not in compiled["kernel"]["text"]
    assert "Test everything twice" not in compiled["kernel"]["text"]
    # Layer B: every section of every document is indexed.
    index_keys = {(row["role"], row["section_id"])
                  for row in compiled["index"]}
    assert ("core", "deep_lore_appendix") in index_keys
    assert ("service_bible", "shell_policy") in index_keys
    # Layer C: hashes are the documents' real sha256 values.
    core_doc = next(d for d in compiled["documents"]
                    if d["role"] == "core")
    assert core_doc["sha256"] == hashlib.sha256(
        CORE_DOC.encode("utf-8")).hexdigest()
    assert len(compiled["persona_hash"]) == 64


def test_extension_role_needs_no_code_change():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home, extra_role=True)
        compiled = runtime.PersonaCompiler(_Ctx(ENABLED)).compile()
    finally:
        mods[0].unload()
    spirit = next(d for d in compiled["documents"]
                  if d["role"] == "spirituality")
    assert spirit["extension"] is True
    assert ("spirituality", "spiritual_model") in {
        (row["role"], row["section_id"]) for row in compiled["index"]}
    core = next(d for d in compiled["documents"] if d["role"] == "core")
    assert core["extension"] is False


def test_missing_required_fails_and_missing_optional_is_named():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home, omit_optional=True)
        compiler = runtime.PersonaCompiler(_Ctx(ENABLED))
        compiled = compiler.compile()
        assert compiled["missing_optional"] == ["avatar"]
        # Remove a required document: the compile fails closed.
        (home / "persona" / "bible.md").unlink()
        with pytest.raises(runtime.PersonaRuntimeError):
            compiler.compile()
    finally:
        mods[0].unload()


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
    assert first["persona_hash"] == second["persona_hash"]
    assert first["kernel"] == second["kernel"]
    assert before == after


def test_no_config_compiles_to_none_and_packet_is_silent():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        assert runtime.PersonaCompiler(_Ctx(ENABLED)).compile() is None
        bridge = runtime.PersonaRuntimeBridge(_Ctx(ENABLED))
        assert bridge.packet_items("s1", "hello") == []
        disabled = runtime.PersonaRuntimeBridge(_Ctx())
        assert disabled.packet_items("s1", "hello") == []
    finally:
        mods[0].unload()


def test_symlinked_document_is_refused():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        target = home / "persona" / "bible.md"
        real = home / "persona" / "bible_real.md"
        target.rename(real)
        target.symlink_to(real)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.PersonaCompiler(_Ctx(ENABLED)).compile()
    finally:
        mods[0].unload()


def test_packet_item_names_counts_and_hash_only():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        home = get_hermes_home()
        _write_persona(home)
        items = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert len(items) == 1
    assert items[0].source == "persona_runtime"
    assert "caducea" in items[0].content
    assert "3 documents" in items[0].content
    # No canonical persona text is injected by this layer.
    assert "persistent Hermes entity" not in items[0].content
    assert "Never force-push" not in items[0].content


def test_profile_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        assert runtime.PersonaCompiler(
            _Ctx(ENABLED)).compile() is not None
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
