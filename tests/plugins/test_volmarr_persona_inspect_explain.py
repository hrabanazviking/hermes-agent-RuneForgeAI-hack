"""Contracts for persona inspect + explain (Slice 153).

Persona Runtime roadmap §71 (Persona Inspect Command)
and §72 (Persona Explain Command): the inspect display
(persona name, version, document count, kernel tokens,
indexed sections, source hash, status VALID) stands as
a pure record and render over a supplied compile — the
roadmap's ``hermes persona`` spelling registers no new
core command, because this plugin's CLI surface is
``hermes volmarr`` — and the explain display ("Why did
Caducea respond this way?" answered with the relevant
persona sections by §12 stable id) stands as a pure
record and render over caller-supplied section ids,
verified against a supplied compile's index when one
is given. This layer compiles nothing, generates no
responses, and explains no live response. Tests load
through real plugin discovery.
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

INSPECT_FIELDS = [
    "persona", "version", "documents", "kernel_tokens",
    "indexed_sections", "source_hash", "status",
]

EXAMPLE_SECTIONS = [
    "relationship.settled_decisions",
    "service_bible.advice_style",
    "core.graceful_deference",
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


def test_inspect_example_matches_roadmap():
    mods = _load_modules()
    runtime = mods[1]
    try:
        example = runtime.persona_inspect_example()
        fields = runtime.persona_inspect_contract()["fields"]
        fields.append("x")
    finally:
        mods[0].unload()
    assert list(runtime.INSPECT_FIELDS) == INSPECT_FIELDS
    assert example == {
        "persona": "Caducea Hermesdottir",
        "version": "1.4.2",
        "documents": 6,
        "kernel_tokens": 934,
        "indexed_sections": 271,
        "source_hash": "0" * 64,
        "status": "VALID",
    }
    assert list(example) == INSPECT_FIELDS
    assert runtime.INSPECT_COMMAND == "hermes persona inspect"
    assert runtime.INSPECT_STATUS_VALID == "VALID"


def test_inspect_record_from_real_compile():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        compiled = runtime.PersonaCompiler(_Ctx()).compile()
        record = runtime.persona_inspect(compiled)
    finally:
        mods[0].unload()
    assert record == {
        "persona": "Caducea Hermesdottir",
        "version": "1.4.2",
        "documents": len(compiled["documents"]),
        "kernel_tokens": compiled["kernel"]["estimated_tokens"],
        "indexed_sections": len(compiled["index"]),
        "source_hash": compiled["persona_hash"],
        "status": "VALID",
    }
    # The inspect counts are the compile's own counts.
    assert record["documents"] == 2
    assert record["indexed_sections"] > 0
    assert record["kernel_tokens"] > 0
    # The source hash is the §22 version record's hash.
    assert runtime.version_record(compiled)["source_hash"] == \
        record["source_hash"]


def test_inspect_render_is_roadmap_display():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        compiled = runtime.PersonaCompiler(_Ctx()).compile()
        rendered = runtime.render_persona_inspect(compiled)
    finally:
        mods[0].unload()
    assert rendered == "\n".join((
        "Persona: Caducea Hermesdottir",
        "Version: 1.4.2",
        f"Documents: {len(compiled['documents'])}",
        f"Kernel tokens: {compiled['kernel']['estimated_tokens']}",
        f"Indexed sections: {len(compiled['index'])}",
        f"Source hash: {compiled['persona_hash']}",
        "Status: VALID",
    ))
    assert not rendered.endswith("\n")


def test_inspect_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        compiled = runtime.PersonaCompiler(_Ctx()).compile()
        bad_compiles = [None, "compile", [], {}]
        for key in ("display_name", "persona_id",
                    "persona_version", "documents", "index",
                    "kernel", "persona_hash"):
            broken = dict(compiled)
            broken.pop(key)
            bad_compiles.append(broken)
        for key, value in (
                ("display_name", "  "), ("persona_version", 7),
                ("documents", {}), ("index", "sections"),
                ("kernel", []), ("persona_hash", "")):
            broken = dict(compiled)
            broken[key] = value
            bad_compiles.append(broken)
        for tokens in (True, -1, "934", None):
            broken = dict(compiled)
            broken["kernel"] = {"estimated_tokens": tokens}
            bad_compiles.append(broken)
        for bad in bad_compiles:
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.persona_inspect(bad)
    finally:
        mods[0].unload()


def test_inspect_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.persona_inspect_contract()
    finally:
        mods[0].unload()
    assert contract == {
        "name": "PersonaInspect",
        "command": "hermes persona inspect",
        "plugin_cli_surface": "hermes volmarr",
        "fields": INSPECT_FIELDS,
        "example": runtime.persona_inspect_example(),
        "status": "VALID",
        "status_basis": "§70 compile-time detections (§6)",
        "new_core_command": False,
        "compiles_persona": False,
    }


def test_explain_example_and_render():
    mods = _load_modules()
    runtime = mods[1]
    try:
        example = runtime.persona_explain_example()
        rendered = runtime.render_persona_explain(EXAMPLE_SECTIONS)
        sections = runtime.persona_explain_contract()[
            "example_sections"]
        sections.append("x")
    finally:
        mods[0].unload()
    assert list(runtime.EXPLAIN_EXAMPLE_SECTIONS) == \
        EXAMPLE_SECTIONS
    assert runtime.EXPLAIN_QUESTION == \
        "Why did Caducea respond this way?"
    assert runtime.EXPLAIN_COMMAND == "hermes persona explain"
    assert example == {
        "question": "Why did Caducea respond this way?",
        "persona_id": None,
        "relevant_sections": EXAMPLE_SECTIONS,
        "sections_verified": False,
        "explains_live_response": False,
    }
    assert rendered == (
        "Why did Caducea respond this way?\n\n\n"
        "Relevant persona sections:\n"
        "- relationship.settled_decisions\n"
        "- service_bible.advice_style\n"
        "- core.graceful_deference")
    assert not rendered.endswith("\n")


def test_explain_verified_against_compile():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        compiled = runtime.PersonaCompiler(_Ctx()).compile()
        stable_ids = [row["stable_id"] for row in compiled["index"]]
        assert "core.graceful_deference" in stable_ids
        record = runtime.persona_explain(
            ["core.graceful_deference"], compiled)
        # A section the compile never indexed is refused,
        # never explained as if it stood in the persona.
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.persona_explain(
                ["relationship.settled_decisions"], compiled)
    finally:
        mods[0].unload()
    assert record == {
        "question": "Why did Caducea respond this way?",
        "persona_id": "caducea",
        "relevant_sections": ["core.graceful_deference"],
        "sections_verified": True,
        "explains_live_response": False,
    }


def test_explain_refusals_and_order():
    mods = _load_modules()
    runtime = mods[1]
    try:
        # Supplied order is preserved, never sorted.
        record = runtime.persona_explain([
            "service_bible.advice_style", "core.identity"])
        for bad in (
                None, "core.identity", [], 7,
                ["core.identity", "core.identity"],
                ["Core Identity"], ["core"], ["core."],
                [".identity"], ["core.identity", None],
                ["core.identity"] * 1
                + [f"core.section_{n}" for n in range(32)],
        ):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.persona_explain(bad)
    finally:
        mods[0].unload()
    assert record["relevant_sections"] == [
        "service_bible.advice_style", "core.identity"]


def test_explain_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.persona_explain_contract()
    finally:
        mods[0].unload()
    assert contract == {
        "name": "PersonaExplain",
        "command": "hermes persona explain",
        "plugin_cli_surface": "hermes volmarr",
        "question": "Why did Caducea respond this way?",
        "example_sections": EXAMPLE_SECTIONS,
        "sections_named_by": "stable_id",
        "max_sections": 32,
        "new_core_command": False,
        "explains_live_response": False,
    }
    assert runtime.MAX_EXPLAIN_SECTIONS == 32


def test_packet_determinism_and_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        home = get_hermes_home()
        _write_persona(home)
        before = _hashes(home)
        contract = runtime.persona_inspect_contract()
        explain = runtime.persona_explain_contract()
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
            other_contract = runtime.persona_inspect_contract()
            other_explain = runtime.persona_explain_contract()
        finally:
            reset_hermes_home_override(token)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert before == after
    assert contract == other_contract
    assert explain == other_explain
    assert first[0].content == second[0].content == third[0].content
    assert len(first) == 1
    content = first[0].content
    assert "§§3-72" in content
    assert "§71 persona inspect" in content
    assert "status VALID" in content
    assert "§72 persona explain" in content
    assert "explains no live" in content
    # The packet names the contracts only — never canonical
    # persona text.
    assert "longhouse terminal" not in content
