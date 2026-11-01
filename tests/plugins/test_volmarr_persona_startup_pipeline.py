"""Contracts for startup sequence + request pipeline (Slice 143).

Persona Runtime roadmap §51 (Startup Sequence) and §52
(Request Pipeline): startup walks load persona.yaml,
resolve the directory, validate required documents,
compare source hashes, then load the compiled persona
if unchanged or compile it if changed, load the Persona
Kernel, initialize the retrieval index, initialize
Persona State, and the persona awakens; each request
walks user message, task classifier, persona router,
persona retrieval, memory retrieval, context budgeter,
prompt assembler, model, persona watchdog, tools /
response. These are pure surfaces: no boot hook is
owned, no pipeline runs, and nothing is injected. Tests
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

STARTUP_STEPS = [
    "load_persona_config", "resolve_persona_directory",
    "validate_required_documents", "compare_source_hashes",
    "load_compiled_persona_or_compile_persona",
    "load_persona_kernel", "initialize_retrieval_index",
    "initialize_persona_state", "awaken",
]

PIPELINE = [
    {"stage": "user_message", "owner": "caller_input",
     "status": "external"},
    {"stage": "task_classifier", "owner": "classify_task",
     "status": "banked"},
    {"stage": "persona_router", "owner": "PersonaRouter",
     "status": "banked"},
    {"stage": "persona_retrieval", "owner": "PersonaRetriever",
     "status": "banked"},
    {"stage": "memory_retrieval", "owner": "memory_subsystem",
     "status": "external"},
    {"stage": "context_budgeter",
     "owner": "PersonaContextBudgeter", "status": "banked"},
    {"stage": "prompt_assembler", "owner": "prompt_assembly_order",
     "status": "banked"},
    {"stage": "model", "owner": "model", "status": "external"},
    {"stage": "persona_watchdog", "owner": "watchdog_contract",
     "status": "banked"},
    {"stage": "tools_or_response", "owner": "caller",
     "status": "external"},
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


def _compiled(runtime):
    return runtime.PersonaCompiler(_Ctx(ENABLED)).compile()


def test_startup_steps_and_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        steps = runtime.startup_steps()
        steps.append("x")
        fresh = runtime.startup_steps()
        contract = runtime.startup_contract()
    finally:
        mods[0].unload()
    assert fresh == STARTUP_STEPS
    assert list(runtime.STARTUP_STEPS) == STARTUP_STEPS
    assert contract == {
        "name": "PersonaStartupSequence",
        "steps": STARTUP_STEPS,
        "branch_decided_by": "source_hash_comparison",
        "loads_compiled_when_unchanged": True,
        "compiles_when_changed_or_absent": True,
        "final_step": "awaken",
        "owns_boot_hook": False,
        "starts_hermes": False,
        "restart_required": False,
        "injects": False,
    }


def test_startup_plan_no_persona_and_removed():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        none_plan = runtime.startup_plan(None, None)
        removed = runtime.startup_plan(compiled, None)
    finally:
        mods[0].unload()
    assert none_plan == {
        "branch": "no_persona", "changed": False, "steps": [],
        "documents_added": [], "documents_removed": [],
        "documents_changed": [], "kernel_changed": False,
        "awakens": False, "restart_required": False,
    }
    assert removed["branch"] == "persona_removed"
    assert removed["changed"] is True
    assert removed["steps"] == STARTUP_STEPS[:4]
    assert removed["documents_removed"] == [
        doc["role"] for doc in compiled["documents"]]
    assert removed["awakens"] is False


def test_startup_plan_first_compile():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        plan = runtime.startup_plan(None, compiled)
    finally:
        mods[0].unload()
    assert plan["branch"] == "compile_persona"
    assert plan["changed"] is True
    assert plan["steps"] == (
        STARTUP_STEPS[:4] + ["compile_persona"] + STARTUP_STEPS[5:])
    assert plan["documents_added"] == [
        doc["role"] for doc in compiled["documents"]]
    assert plan["kernel_changed"] is True
    assert plan["awakens"] is True


def test_startup_plan_unchanged_loads_compiled():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        again = _compiled(runtime)
        plan = runtime.startup_plan(compiled, again)
    finally:
        mods[0].unload()
    assert plan["branch"] == "load_compiled_persona"
    assert plan["changed"] is False
    assert plan["steps"] == (
        STARTUP_STEPS[:4] + ["load_compiled_persona"]
        + STARTUP_STEPS[5:])
    assert plan["documents_changed"] == []
    assert plan["kernel_changed"] is False
    assert plan["awakens"] is True


def test_startup_plan_changed_compiles():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        home = get_hermes_home()
        _write_persona(home)
        compiled = _compiled(runtime)
        _write_persona(home, core_doc=OTHER_CORE_DOC)
        changed = _compiled(runtime)
        plan = runtime.startup_plan(compiled, changed)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.startup_plan(compiled, {"persona_id": "x"})
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.startup_plan(None, "compiled")
    finally:
        mods[0].unload()
    assert plan["branch"] == "compile_persona"
    assert plan["changed"] is True
    assert plan["documents_changed"] == ["core"]
    assert plan["kernel_changed"] is True
    assert plan["awakens"] is True


def test_request_pipeline_stages_and_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        stages = runtime.request_pipeline_stages()
        stages[0]["stage"] = "x"
        fresh = runtime.request_pipeline_stages()
        contract = runtime.request_pipeline_contract()
    finally:
        mods[0].unload()
    assert fresh == PIPELINE
    assert list(runtime.REQUEST_PIPELINE_STAGES) == [
        row["stage"] for row in PIPELINE]
    # Prompt assembly is §53: its owner is the §53 pure
    # order surface (Slice 144), banked here, not a live
    # assembler wired into the turn path.
    assert fresh[6] == {
        "stage": "prompt_assembler",
        "owner": "prompt_assembly_order", "status": "banked"}
    assert contract == {
        "name": "PersonaRequestPipeline",
        "stages": PIPELINE,
        "task_classifier_fields": [
            "task_type", "entities", "project", "tool_intent"],
        "prompt_assembly": "section_53_prompt_assembly_order",
        "runs_pipeline": False,
        "classifies_live_messages": False,
        "injects": False,
    }
    assert runtime.task_classifier_fields() == [
        "task_type", "entities", "project", "tool_intent"]


def test_request_pipeline_plan_classification():
    mods = _load_modules()
    runtime = mods[1]
    try:
        empty = runtime.request_pipeline_plan()
        plan = runtime.request_pipeline_plan({
            "task_type": "Coding Task",
            "entities": ["Hermes", "persona runtime", "Hermes"],
            "project": "Persona Runtime",
            "tool_intent": "File Reading",
        })
    finally:
        mods[0].unload()
    assert empty == {
        "stages": PIPELINE,
        "classification": {
            "task_type": None, "entities": [], "project": None,
            "tool_intent": None},
        "prompt_assembly": "section_53_prompt_assembly_order",
        "executes": False,
    }
    assert plan["classification"] == {
        "task_type": "coding_task",
        "entities": ["hermes", "persona_runtime"],
        "project": "persona_runtime",
        "tool_intent": "file_reading",
    }
    assert plan["executes"] is False


def test_request_pipeline_plan_malformed_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for bad in ("classification", [], {"unknown": "x"},
                    {"task_type": ""}, {"task_type": 3},
                    {"entities": "hermes"}, {"entities": [""]},
                    {"entities": ["x"] * 33},
                    {"project": []}):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.request_pipeline_plan(bad)
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
        plan = runtime.startup_plan(None, compiled)
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
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.startup_plan(compiled, other)
        finally:
            reset_hermes_home_override(token)
        back = _compiled(runtime)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        back_plan = runtime.startup_plan(compiled, back)
    finally:
        mods[0].unload()
    assert before == after
    assert plan["branch"] == "compile_persona"
    assert back_plan["branch"] == "load_compiled_persona"
    assert first[0].content == second[0].content == third[0].content
    assert len(first) == 1
    content = first[0].content
    assert "§§3-76" in content
    assert "§51 startup" in content
    assert "owns no boot hook" in content
    assert "§52 request pipeline" in content
    assert "§53 prompt assembly" in content
    assert "no pipeline runs here" in content
    # The packet names the contracts only — never canonical
    # persona text.
    assert "longhouse terminal" not in content
