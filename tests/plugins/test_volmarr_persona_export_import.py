"""Contracts for persona export + import (Slice 155).

Persona Runtime roadmap §75 (Persona Export) and §76
(Persona Import): a compiled persona stands as a pure
portable bundle record (``<persona_id>.persona``) built
on the §50 manifest and the §22 version record —
manifest, source Markdown by file and hash, compiled
IR, kernel, version metadata, and optional avatar
metadata — for sharing between Hermes installations,
and an import plan over a validated bundle never
overwrites an existing persona without explicit
handling (a collision refuses by default; only the
explicit ``replace`` handling plans an overwrite).
The roadmap's ``hermes persona`` spelling registers no
new core command, because this plugin's CLI surface is
``hermes volmarr``. This layer writes and reads no
bundle file, imports and installs nothing, and embeds
no source text it does not retain. Tests load through
real plugin discovery.
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

# Graceful Deference

Caducea defers gracefully when Volmarr decides.
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

CONTENTS = [
    "manifest", "source_markdown", "compiled_ir",
    "kernel", "version_metadata", "avatar_metadata",
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


def test_export_contents_and_filename():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contents = runtime.export_contents()
        contents.append("x")
    finally:
        mods[0].unload()
    assert list(runtime.EXPORT_CONTENTS) == CONTENTS
    assert runtime.EXPORT_BUNDLE_EXTENSION == ".persona"
    assert runtime.export_filename("caducea") == "caducea.persona"
    assert runtime.persona_export_example() == {
        "filename": "caducea.persona",
        "persona_id": "caducea",
        "contents": CONTENTS,
        "avatar_metadata_optional": True,
    }
    with pytest.raises(runtime.PersonaRuntimeError):
        runtime.export_filename("Not A Slug")
    with pytest.raises(runtime.PersonaRuntimeError):
        runtime.export_filename(None)


def test_export_from_real_compile():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        compiled = runtime.PersonaCompiler(_Ctx()).compile()
        bundle = runtime.persona_export(compiled)
    finally:
        mods[0].unload()
    assert bundle["filename"] == "caducea.persona"
    assert bundle["persona_id"] == "caducea"
    assert bundle["version"] == "1.4.2"
    assert bundle["contents"] == CONTENTS
    assert bundle["avatar_present"] is False
    assert bundle["avatar_metadata"] is None
    assert bundle["manifest"] == runtime.manifest(compiled)
    assert bundle["version_metadata"] == \
        runtime.version_record(compiled)
    assert bundle["source_documents"] == [
        {"role": doc["role"], "file": doc["file"],
         "hash": doc["sha256"]}
        for doc in compiled["documents"]]
    assert bundle["kernel"] == {
        "sha256": compiled["kernel"]["sha256"],
        "estimated_tokens": compiled["kernel"]["estimated_tokens"],
    }
    assert bundle["compiled_ir"]["ir_hash"] == \
        compiled["ir"]["ir_hash"]
    assert bundle["compiled_ir"]["total_sections"] == \
        compiled["ir"]["total_sections"]
    assert bundle["compiled_ir"]["generated"] is True
    assert bundle["compiled_ir"]["human_editable"] is False
    # The bundle names the source Markdown by file and
    # hash (§50) — it embeds no document text this layer
    # does not retain as a document (§5 Layer C).
    assert "longhouse terminal" not in str(bundle)


def test_export_avatar_metadata_optional():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        compiled = runtime.PersonaCompiler(_Ctx()).compile()
        bundle = runtime.persona_export(
            compiled, avatar_metadata={"style": "pale witch"})
        plain = runtime.persona_export(compiled)
        for bad in ("pale witch", {"style": 7}, {"": "x"},
                    {"style": ""}, {str(i): "x" for i in range(17)}):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.persona_export(compiled, avatar_metadata=bad)
    finally:
        mods[0].unload()
    assert bundle["avatar_present"] is True
    assert bundle["avatar_metadata"] == {"style": "pale witch"}
    assert runtime.validate_persona_export(bundle) == bundle
    assert plain["avatar_metadata"] is None


def test_validate_export_round_trip_and_tamper():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        compiled = runtime.PersonaCompiler(_Ctx()).compile()
        bundle = runtime.persona_export(compiled)
        checked = runtime.validate_persona_export(bundle)
        tampered = []
        bad = dict(bundle); bad["filename"] = "other.persona"
        tampered.append(bad)
        bad = dict(bundle); bad["version"] = "9.9.9"
        tampered.append(bad)
        bad = dict(bundle); bad["contents"] = ["manifest"]
        tampered.append(bad)
        bad = dict(bundle); bad["avatar_present"] = True
        tampered.append(bad)
        bad = dict(bundle)
        bad["kernel"] = {"sha256": "0" * 64, "estimated_tokens": 1}
        tampered.append(bad)
        bad = dict(bundle)
        bad["source_documents"] = []
        tampered.append(bad)
        bad = dict(bundle)
        bad["compiled_ir"] = dict(bundle["compiled_ir"])
        bad["compiled_ir"]["total_sections"] = 999
        tampered.append(bad)
        bad = dict(bundle); bad["extra"] = True
        tampered.append(bad)
        bad = dict(bundle); del bad["manifest"]
        tampered.append(bad)
        for record in tampered + [None, "bundle", []]:
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.validate_persona_export(record)
    finally:
        mods[0].unload()
    assert checked == bundle
    assert checked is not bundle


def test_import_plan_no_collision():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        compiled = runtime.PersonaCompiler(_Ctx()).compile()
        bundle = runtime.persona_export(compiled)
        fresh = runtime.persona_import_plan(bundle)
        other = runtime.persona_import_plan(
            bundle, existing_persona_id="runa")
    finally:
        mods[0].unload()
    assert fresh == {
        "command": "hermes persona import",
        "filename": "caducea.persona",
        "persona_id": "caducea",
        "version": "1.4.2",
        "existing_persona_id": None,
        "collision": False,
        "handling": "refuse",
        "action": "import",
        "would_overwrite": False,
        "explicit_handling_required": False,
        "performs_import": False,
    }
    assert other["collision"] is False
    assert other["action"] == "import"


def test_import_plan_collision_needs_explicit_handling():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        compiled = runtime.PersonaCompiler(_Ctx()).compile()
        bundle = runtime.persona_export(compiled)
        refused = runtime.persona_import_plan(
            bundle, existing_persona_id="caducea")
        replaced = runtime.persona_import_plan(
            bundle, existing_persona_id="caducea",
            handling="replace")
        handlings = runtime.import_handlings()
        handlings.append("x")
    finally:
        mods[0].unload()
    assert list(runtime.IMPORT_HANDLINGS) == ["refuse", "replace"]
    assert runtime.IMPORT_DEFAULT_HANDLING == "refuse"
    assert refused["collision"] is True
    assert refused["action"] == "refuse"
    assert refused["would_overwrite"] is False
    assert refused["explicit_handling_required"] is True
    assert replaced["action"] == "replace"
    assert replaced["would_overwrite"] is True
    assert replaced["performs_import"] is False


def test_import_plan_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        compiled = runtime.PersonaCompiler(_Ctx()).compile()
        bundle = runtime.persona_export(compiled)
        bad_bundle = dict(bundle); bad_bundle["version"] = "9.9.9"
        for args, kwargs in (
                ((bad_bundle,), {}),
                ((bundle,), {"handling": "overwrite"}),
                ((bundle,), {"handling": None}),
                ((bundle,), {"existing_persona_id": "Not A Slug"}),
                ((bundle,), {"existing_persona_id": 7}),
                ((None,), {}),
        ):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.persona_import_plan(*args, **kwargs)
    finally:
        mods[0].unload()


def test_export_import_contracts():
    mods = _load_modules()
    runtime = mods[1]
    try:
        export_contract = runtime.persona_export_contract()
        import_contract = runtime.persona_import_contract()
    finally:
        mods[0].unload()
    assert export_contract == {
        "name": "PersonaExport",
        "bundle_extension": ".persona",
        "example": runtime.persona_export_example(),
        "contents": CONTENTS,
        "basis": "§50 manifest + §22 version record",
        "avatar_metadata_optional": True,
        "writes_bundle": False,
        "shares_between_installations": True,
    }
    assert import_contract == {
        "name": "PersonaImport",
        "command": "hermes persona import",
        "plugin_cli_surface": "hermes volmarr",
        "example_command": "hermes persona import caducea.persona",
        "handlings": ["refuse", "replace"],
        "default_handling": "refuse",
        "overwrites_without_explicit_handling": False,
        "new_core_command": False,
        "performs_import": False,
        "basis": "§75 persona bundle",
    }
    assert runtime.IMPORT_COMMAND == "hermes persona import"


def test_packet_determinism_and_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        home = get_hermes_home()
        _write_persona(home)
        before = _hashes(home)
        contract = runtime.persona_export_contract()
        compiled = runtime.PersonaCompiler(_Ctx()).compile()
        bundle = runtime.persona_export(compiled)
        plan = runtime.persona_import_plan(
            bundle, existing_persona_id="caducea")
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
            other_contract = runtime.persona_export_contract()
        finally:
            reset_hermes_home_override(token)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert before == after
    assert contract == other_contract
    assert plan["action"] == "refuse"
    assert first[0].content == second[0].content == third[0].content
    assert len(first) == 1
    content = first[0].content
    assert "§§3-80" in content
    assert "§75 persona export" in content
    assert "portable bundle" in content
    assert "§76 persona import" in content
    assert "never overwrites" in content
    # The packet names the contracts only — never canonical
    # persona text.
    assert "longhouse terminal" not in content
