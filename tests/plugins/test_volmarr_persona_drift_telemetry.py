"""Contracts for drift telemetry + model quality (Slice 148).

Persona Runtime roadmap §61 (Character Drift Telemetry) and
§62 (Model Router + Persona Quality): locally record drift
score, kernel version, model used, mode, and retrieved
persona sections so models can be compared; model selection
considers persona adherence alongside intelligence. These
are pure surfaces: no record is persisted, no live telemetry
is recorded, no model is routed. Tests load through real
plugin discovery.
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

TELEMETRY_FIELDS = [
    "drift_score", "kernel_version", "model", "mode",
    "retrieved_sections",
]

EXAMPLE_AVERAGES = {
    "gemma_4_e2b": 0.18, "qwen": 0.11, "remote_model": 0.06}

SECTIONS = ["core.execution", "service_bible.coding_preferences"]


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


def _record(runtime, score, model, mode="architect",
            sections=SECTIONS):
    return runtime.drift_telemetry_record(
        score, "1.4.2", model, mode, list(sections))


def test_telemetry_fields_and_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        fields = runtime.telemetry_fields()
        fields.append("x")
        contract = runtime.telemetry_contract()
    finally:
        mods[0].unload()
    assert runtime.telemetry_fields() == TELEMETRY_FIELDS
    assert list(runtime.TELEMETRY_FIELDS) == TELEMETRY_FIELDS
    assert contract == {
        "name": "PersonaDriftTelemetry",
        "fields": TELEMETRY_FIELDS,
        "example_averages": EXAMPLE_AVERAGES,
        "recorded_locally": True,
        "compares_models": True,
        "persists_records": False,
        "records_live_telemetry": False,
    }


def test_record_build_normalises_and_round_trips():
    mods = _load_modules()
    runtime = mods[1]
    try:
        built = _record(runtime, 0.18, "Gemma 4 E2B")
        built["telemetry"]["drift_score"] = 0.5
        fresh = _record(runtime, 0.18, "Gemma 4 E2B")
        validated = runtime.validate_drift_telemetry_record(
            {"telemetry": dict(fresh["telemetry"])})
    finally:
        mods[0].unload()
    # The model name is slugified, the mode validated, the
    # sections carried by stable id; mutation is isolated.
    assert fresh == {"telemetry": {
        "drift_score": 0.18, "kernel_version": "1.4.2",
        "model": "gemma_4_e2b", "mode": "architect",
        "retrieved_sections": SECTIONS}}
    assert list(fresh["telemetry"]) == TELEMETRY_FIELDS
    assert validated == fresh


def test_record_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        bad_calls = [
            (1.01, "1.4.2", "qwen", "architect", []),
            (-0.1, "1.4.2", "qwen", "architect", []),
            (True, "1.4.2", "qwen", "architect", []),
            ("low", "1.4.2", "qwen", "architect", []),
            (0.1, "1.4", "qwen", "architect", []),
            (0.1, "v1.4.2", "qwen", "architect", []),
            (0.1, "1.4.2", "", "architect", []),
            (0.1, "1.4.2", "qwen", "wizard", []),
            (0.1, "1.4.2", "qwen", "architect", ["no_dot"]),
            (0.1, "1.4.2", "qwen", "architect",
             ["core.execution", "core.execution"]),
            (0.1, "1.4.2", "qwen", "architect", "core.execution"),
        ]
        for args in bad_calls:
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.drift_telemetry_record(*args)
    finally:
        mods[0].unload()


def test_validate_record_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        good = _record(runtime, 0.11, "qwen")["telemetry"]
        reordered = {"telemetry": dict(reversed(
            list(good.items())))}
        bad_records = [
            {"telemetry": dict(good), "extra": 1},
            {"record": dict(good)},
            {"telemetry": {k: v for k, v in good.items()
                           if k != "mode"}},
            {"telemetry": dict(good, drift_score=2.0)},
            {"telemetry": dict(good, model="Qwen")},
            reordered,
            "not a record",
            None,
        ]
        for bad in bad_records:
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.validate_drift_telemetry_record(bad)
    finally:
        mods[0].unload()


def test_model_drift_averages_reproduce_example():
    mods = _load_modules()
    runtime = mods[1]
    try:
        records = [
            _record(runtime, 0.16, "Gemma 4 E2B"),
            _record(runtime, 0.20, "Gemma 4 E2B"),
            _record(runtime, 0.11, "Qwen"),
            _record(runtime, 0.04, "remote model"),
            _record(runtime, 0.08, "remote model"),
        ]
        averages = runtime.model_drift_averages(records)
        example = runtime.telemetry_example_averages()
        example["qwen"] = 0.5
    finally:
        mods[0].unload()
    # The roadmap's example averages are reproduced exactly,
    # in first-appearance order; the example is isolated.
    assert averages == EXAMPLE_AVERAGES
    assert list(averages) == [
        "gemma_4_e2b", "qwen", "remote_model"]
    assert runtime.telemetry_example_averages() == EXAMPLE_AVERAGES
    assert dict(runtime.TELEMETRY_EXAMPLE_AVERAGES) == EXAMPLE_AVERAGES


def test_model_drift_averages_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for bad in ([], (), "records", None,
                    [{"telemetry": {"drift_score": 0.1}}]):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.model_drift_averages(bad)
    finally:
        mods[0].unload()


def test_persona_adherence_and_quality_table():
    mods = _load_modules()
    runtime = mods[1]
    try:
        table = runtime.model_quality_table(dict(EXAMPLE_AVERAGES))
        adherence = runtime.persona_adherence(0.18)
    finally:
        mods[0].unload()
    assert adherence == 0.82
    # Ordered by adherence descending: the remote model
    # holds the personality best, Gemma worst.
    assert table == [
        {"model": "remote_model", "average_drift": 0.06,
         "persona_adherence": 0.94},
        {"model": "qwen", "average_drift": 0.11,
         "persona_adherence": 0.89},
        {"model": "gemma_4_e2b", "average_drift": 0.18,
         "persona_adherence": 0.82},
    ]


def test_preferred_companionship_model_and_router_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        considerations = runtime.model_selection_considerations()
        considerations.append("x")
        preferred = runtime.preferred_companionship_model(
            dict(EXAMPLE_AVERAGES))
        contract = runtime.model_router_contract()
    finally:
        mods[0].unload()
    assert runtime.model_selection_considerations() == [
        "intelligence", "persona_adherence"]
    assert list(runtime.MODEL_SELECTION_CONSIDERATIONS) == [
        "intelligence", "persona_adherence"]
    # The lowest-drift model is preferred for companionship
    # even though no intelligence score is carried here.
    assert preferred == "remote_model"
    assert contract == {
        "name": "PersonaAwareModelRouter",
        "considerations": ["intelligence", "persona_adherence"],
        "adherence_basis": "character_drift_telemetry",
        "example_averages": EXAMPLE_AVERAGES,
        "example_preferred_model": "remote_model",
        "routes_live_models": False,
        "per_model_metrics_section": 63,
    }


def test_quality_table_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for bad in ({}, {"qwen": 1.5}, {"qwen": True},
                    {"": 0.1}, "averages", None):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.model_quality_table(bad)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.persona_adherence(1.5)
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
        averages = runtime.telemetry_example_averages()
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
            other_averages = runtime.telemetry_example_averages()
        finally:
            reset_hermes_home_override(token)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert before == after
    assert averages == other_averages
    assert first[0].content == second[0].content == third[0].content
    assert len(first) == 1
    content = first[0].content
    assert "§§3-92" in content
    assert "§61 drift telemetry" in content
    assert "§62 model router" in content
    assert "persona adherence" in content
    # The packet names the contracts only — never canonical
    # persona text.
    assert "longhouse terminal" not in content
