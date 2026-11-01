"""Contracts for generated directory + manifest (Slice 142).

Persona Runtime roadmap §49 (Generated Directory) and §50
(Manifest): the recommended layout is ``persona/source/``
holding the six authored Caducea documents and
``persona/.compiled/`` holding the generated artefacts,
regenerable at any time; the manifest names the persona
id, its version, the compile stamp, the documents by
role with each document's file and hash, and the kernel
hash. These are pure surfaces: no directory is created,
no manifest is written, and nothing is injected. Tests
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

SOURCE_DOCUMENTS = [
    {"role": "core", "file": "CADUCEA_PERSONA_CORE.md",
     "path": "source/CADUCEA_PERSONA_CORE.md"},
    {"role": "service_bible",
     "file": "CADUCEA_SERVICE_BIBLE.md",
     "path": "source/CADUCEA_SERVICE_BIBLE.md"},
    {"role": "memory_policy",
     "file": "CADUCEA_MEMORY_POLICY.md",
     "path": "source/CADUCEA_MEMORY_POLICY.md"},
    {"role": "tool_policy", "file": "CADUCEA_TOOL_POLICY.md",
     "path": "source/CADUCEA_TOOL_POLICY.md"},
    {"role": "relationship",
     "file": "CADUCEA_RELATIONSHIP_MODEL.md",
     "path": "source/CADUCEA_RELATIONSHIP_MODEL.md"},
    {"role": "avatar", "file": "CADUCEA_AVATAR.md",
     "path": "source/CADUCEA_AVATAR.md"},
]

COMPILED_ARTIFACTS = [
    {"file": "persona_ir.json", "kind": "ir",
     "path": ".compiled/persona_ir.json", "generated": True},
    {"file": "persona_kernel.txt", "kind": "kernel",
     "path": ".compiled/persona_kernel.txt", "generated": True},
    {"file": "sections.jsonl", "kind": "sections",
     "path": ".compiled/sections.jsonl", "generated": True},
    {"file": "embeddings.db", "kind": "embeddings",
     "path": ".compiled/embeddings.db", "generated": True},
    {"file": "manifest.json", "kind": "manifest",
     "path": ".compiled/manifest.json", "generated": True},
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


def test_generated_source_documents_and_layout():
    mods = _load_modules()
    runtime = mods[1]
    try:
        docs = runtime.generated_source_documents()
        docs.append({"role": "x", "file": "x", "path": "x"})
        fresh = runtime.generated_source_documents()
        layout = runtime.generated_directory_layout()
    finally:
        mods[0].unload()
    assert fresh == SOURCE_DOCUMENTS
    assert [tuple(pair) for pair in
            runtime.GENERATED_SOURCE_DOCUMENTS] == [
                (row["role"], row["file"]) for row in SOURCE_DOCUMENTS]
    # The §49 source roles are exactly the six §3 core
    # roles, in roadmap order.
    assert [row["role"] for row in fresh] == list(runtime.CORE_ROLES)
    assert layout == {
        "root": "persona",
        "source_directory": "source",
        "compiled_directory": ".compiled",
        "source_documents": SOURCE_DOCUMENTS,
        "compiled_artifacts": COMPILED_ARTIFACTS,
        "compiled_regenerable": True,
    }


def test_generated_compiled_artifacts_differ_from_cache_names():
    mods = _load_modules()
    runtime = mods[1]
    try:
        artifacts = runtime.generated_compiled_artifacts()
        artifacts[0]["generated"] = False
        fresh = runtime.generated_compiled_artifacts()
    finally:
        mods[0].unload()
    assert fresh == COMPILED_ARTIFACTS
    assert [tuple(pair) for pair in
            runtime.GENERATED_COMPILED_ARTIFACTS] == [
                (row["file"], row["kind"]) for row in COMPILED_ARTIFACTS]
    # Honest naming gap, recorded in the module: §49's
    # compiled names differ from §48's cache names for
    # the sections and manifest artefacts.
    cache_files = {file for file, _kind in runtime.CACHE_ARTIFACTS}
    assert "persona_sections.jsonl" in cache_files
    assert "persona_manifest.json" in cache_files
    generated_files = {row["file"] for row in fresh}
    assert "sections.jsonl" in generated_files
    assert "manifest.json" in generated_files


def test_generated_directory_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.generated_directory_contract()
    finally:
        mods[0].unload()
    assert contract == {
        "name": "PersonaGeneratedDirectory",
        "root": "persona",
        "source_directory": "source",
        "compiled_directory": ".compiled",
        "source_documents": SOURCE_DOCUMENTS,
        "compiled_artifacts": COMPILED_ARTIFACTS,
        "compiled_regenerable": True,
        "creates_directory": False,
        "writes_files": False,
        "injects": False,
    }


def test_manifest_shape_and_determinism():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        built = runtime.manifest(compiled)
        again = runtime.manifest(_compiled(runtime))
        record = runtime.hash_record(compiled)
        valid = runtime.validate_manifest(built, compiled)
        stale = runtime.manifest_staleness(built, compiled)
    finally:
        mods[0].unload()
    assert built == again
    assert list(built) == list(runtime.MANIFEST_FIELDS)
    assert built["persona_id"] == "caducea"
    # §50's version is the §22 per-persona semver the
    # compile carries, not the §19 config format version.
    assert built["version"] == "1.4.2"
    assert built["compiled_at"] is None
    assert built["kernel_hash"] == record["kernel_hash"]
    assert built["kernel_hash"] == compiled["kernel"]["sha256"]
    # The §50 gap over §48: every document stands by role
    # with its file AND its hash, in document order.
    assert list(built["documents"]) == [
        doc["role"] for doc in compiled["documents"]]
    for doc in compiled["documents"]:
        assert built["documents"][doc["role"]] == {
            "file": doc["file"], "hash": doc["sha256"]}
    assert valid is True
    assert stale == {"valid": True, "changed": [], "missing": []}


def test_manifest_document_entries_carry_file_and_hash_only():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        built = runtime.manifest(_compiled(runtime))
    finally:
        mods[0].unload()
    assert list(runtime.MANIFEST_DOCUMENT_FIELDS) == ["file", "hash"]
    for entry in built["documents"].values():
        assert list(entry) == ["file", "hash"]


def test_generated_layout_paths_are_rooted_in_the_layout():
    mods = _load_modules()
    runtime = mods[1]
    try:
        layout = runtime.generated_directory_layout()
    finally:
        mods[0].unload()
    assert runtime.GENERATED_ROOT == "persona"
    assert runtime.GENERATED_SOURCE_DIR == "source"
    assert runtime.GENERATED_COMPILED_DIR == ".compiled"
    for row in layout["source_documents"]:
        assert row["path"] == f"source/{row['file']}"
    for row in layout["compiled_artifacts"]:
        assert row["path"] == f".compiled/{row['file']}"
        assert row["generated"] is True


def test_manifest_stamp_alone_is_not_a_change():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        stamped = runtime.manifest(
            compiled, compiled_at="2026-10-31T00:00:00+00:00")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.manifest(compiled, compiled_at="soon")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.manifest(
                compiled, compiled_at="2026-10-31T00:00:00")
        stale = runtime.manifest_staleness(stamped, compiled)
        valid = runtime.validate_manifest(stamped, compiled)
    finally:
        mods[0].unload()
    assert stamped["compiled_at"] == "2026-10-31T00:00:00+00:00"
    assert stale == {"valid": True, "changed": [], "missing": []}
    assert valid is True


def test_manifest_staleness_changed_document():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        built = runtime.manifest(compiled)
        tampered = copy.deepcopy(built)
        tampered["documents"]["core"]["hash"] = "0" * 64
        renamed = copy.deepcopy(built)
        renamed["documents"]["avatar"]["file"] = "other.md"
        altered = copy.deepcopy(compiled)
        altered["documents"][0]["sha256"] = "f" * 64
        altered["documents"][0]["file"] = "core.md"
        tampered_stale = runtime.manifest_staleness(tampered, compiled)
        renamed_stale = runtime.manifest_staleness(renamed, compiled)
        altered_stale = runtime.manifest_staleness(built, altered)
    finally:
        mods[0].unload()
    assert tampered_stale == {
        "valid": False, "changed": ["core"], "missing": []}
    assert renamed_stale == {
        "valid": False, "changed": ["avatar"], "missing": []}
    # A compile-side document hash change is refused by
    # the §19 record consistency inside hash_record only
    # when the record itself is rebuilt — here the direct
    # documents list drives the manifest, so the change
    # names the role.
    assert altered_stale["valid"] is False
    assert altered_stale["changed"] == ["core"]


def test_manifest_staleness_missing_document():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        built = runtime.manifest(compiled)
        missing = copy.deepcopy(built)
        del missing["documents"]["avatar"]
        stale = runtime.manifest_staleness(missing, compiled)
        valid = runtime.validate_manifest(missing, compiled)
    finally:
        mods[0].unload()
    assert stale == {
        "valid": False, "changed": [], "missing": ["avatar"]}
    assert valid is False


def test_manifest_staleness_kernel_and_version():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        built = runtime.manifest(compiled)
        kernel = copy.deepcopy(built)
        kernel["kernel_hash"] = "0" * 64
        version = copy.deepcopy(built)
        version["version"] = "1.4.3"
        kernel_stale = runtime.manifest_staleness(kernel, compiled)
        version_stale = runtime.manifest_staleness(version, compiled)
        kernel_valid = runtime.validate_manifest(kernel, compiled)
    finally:
        mods[0].unload()
    assert kernel_stale == {
        "valid": False, "changed": ["kernel_hash"], "missing": []}
    assert version_stale == {
        "valid": False, "changed": ["version"], "missing": []}
    assert kernel_valid is False


def test_manifest_malformed_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        built = runtime.manifest(compiled)
        for bad_compiled in (None, {}, {"persona_id": "x"}):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.manifest(bad_compiled)
        no_file = copy.deepcopy(compiled)
        del no_file["documents"][0]["file"]
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.manifest(no_file)
        for bad_manifest in (None, "manifest", {}):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.validate_manifest(bad_manifest, compiled)
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.manifest_staleness(bad_manifest, compiled)
        broken = copy.deepcopy(built)
        del broken["documents"]
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.validate_manifest(broken, compiled)
        bad_version = copy.deepcopy(built)
        bad_version["version"] = "1.4"
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.validate_manifest(bad_version, compiled)
        no_hash = copy.deepcopy(built)
        del no_hash["documents"]["core"]["hash"]
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.validate_manifest(no_hash, compiled)
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
        built = runtime.manifest(compiled)
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
            cross = runtime.manifest_staleness(built, other)
        finally:
            reset_hermes_home_override(token)
        back = _compiled(runtime)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        valid_back = runtime.validate_manifest(built, back)
        valid_other = runtime.validate_manifest(built, other)
    finally:
        mods[0].unload()
    assert before == after
    assert first[0].content == second[0].content == third[0].content
    assert back["persona_hash"] == compiled["persona_hash"]
    assert valid_back is True
    # A manifest for one persona never validates against
    # another persona's compile.
    assert cross["valid"] is False
    assert "persona_id" in cross["changed"]
    assert valid_other is False
    assert len(first) == 1
    content = first[0].content
    assert "§§3-82" in content
    assert "§49 generated directory" in content
    assert "persona/source/" in content
    assert "persona/.compiled/" in content
    assert "creates no directory" in content
    assert "§50 manifest" in content
    assert "documents by role with" in content
    assert "writes no manifest" in content
    # The packet names the contracts only — never canonical
    # persona text or authored anchor prose.
    assert "longhouse terminal" not in content
    assert "does not command" not in content
