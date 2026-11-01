"""Contracts for model metrics + kernel distillation (Slice 149).

Persona Runtime roadmap §63 (Persona Adherence Score) and
§64 (Distill Persona For Small Models): maintain per-model
metrics (reasoning, latency, persona_adherence, tool_use,
cost) the router can choose between by task; compile
multiple kernels (full ~1500, medium ~750, micro ~250
tokens) from the same canonical source for small models.
These are pure surfaces: no live model is measured, no
model is routed, and no kernel is built. Tests load
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

METRIC_NAMES = [
    "reasoning", "latency", "persona_adherence",
    "tool_use", "cost",
]

METRICS_EXAMPLE = {"model": {
    "reasoning": 0.82, "latency": 0.95,
    "persona_adherence": 0.93, "tool_use": 0.76,
    "cost": 0.99,
}}

MODEL_TASKS = [
    "reasoning", "companionship", "tool_work",
    "fast_response", "low_cost", "balanced",
]

TASK_PRIMARY = {
    "reasoning": "reasoning",
    "companionship": "persona_adherence",
    "tool_work": "tool_use",
    "fast_response": "latency",
    "low_cost": "cost",
    "balanced": "mean",
}

MODELS = {
    "router example": dict(METRICS_EXAMPLE["model"]),
    "deep thinker": {
        "reasoning": 0.99, "latency": 0.40,
        "persona_adherence": 0.50, "tool_use": 0.90,
        "cost": 0.30},
    "tool hand": {
        "reasoning": 0.60, "latency": 0.70,
        "persona_adherence": 0.60, "tool_use": 0.98,
        "cost": 0.50},
}

KERNEL_TIERS = ["kernel_full", "kernel_medium", "kernel_micro"]

KERNEL_TARGETS = {
    "kernel_full": 1500, "kernel_medium": 750,
    "kernel_micro": 250}

KERNEL_HASH = "a" * 64


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


def test_metric_names_and_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        names = runtime.model_metric_names()
        names.append("x")
        contract = runtime.model_metrics_contract()
    finally:
        mods[0].unload()
    assert runtime.model_metric_names() == METRIC_NAMES
    assert list(runtime.MODEL_METRIC_NAMES) == METRIC_NAMES
    assert contract == {
        "name": "PersonaAdherenceScore",
        "metrics": METRIC_NAMES,
        "example": METRICS_EXAMPLE,
        "tasks": MODEL_TASKS,
        "task_primary_metrics": TASK_PRIMARY,
        "adherence_basis": "persona_adherence (§62)",
        "router_chooses_by_task": True,
        "routes_live_models": False,
        "measures_live_models": False,
    }


def test_metrics_example_verbatim_and_round_trip():
    mods = _load_modules()
    runtime = mods[1]
    try:
        example = runtime.model_metrics_example()
        validated = runtime.validate_model_metrics(
            {"model": dict(METRICS_EXAMPLE["model"])})
        adherence = runtime.persona_adherence(0.07)
    finally:
        mods[0].unload()
    assert example == METRICS_EXAMPLE
    assert validated == METRICS_EXAMPLE
    # The example's persona_adherence metric is exactly the
    # §62 adherence derived from an 0.07 average drift.
    assert adherence == 0.93
    assert example["model"]["persona_adherence"] == adherence


def test_metrics_builder_order_and_isolation():
    mods = _load_modules()
    runtime = mods[1]
    try:
        shuffled = {
            "cost": 1, "tool_use": 0.5, "reasoning": 0,
            "persona_adherence": 0.25, "latency": 0.75}
        built = runtime.model_metrics(shuffled)
        built["model"]["cost"] = 0.0
        fresh = runtime.model_metrics(shuffled)
    finally:
        mods[0].unload()
    # Supplied out of order, returned in roadmap order;
    # int values normalise to float; mutation is isolated.
    assert list(fresh["model"]) == METRIC_NAMES
    assert fresh == {"model": {
        "reasoning": 0.0, "latency": 0.75,
        "persona_adherence": 0.25, "tool_use": 0.5,
        "cost": 1.0}}


def test_metrics_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        full = dict(METRICS_EXAMPLE["model"])
        missing = dict(full)
        del missing["cost"]
        for bad in (missing, dict(full, speed=0.5),
                    dict(full, cost=1.01), dict(full, cost=-0.1),
                    dict(full, cost=True), dict(full, cost="cheap"),
                    {}, "metrics", None, [("cost", 0.5)]):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.model_metrics(bad)
    finally:
        mods[0].unload()


def test_validate_metrics_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        good = dict(METRICS_EXAMPLE["model"])
        reordered = {"model": dict(reversed(list(good.items())))}
        bad_records = [
            {"model": dict(good), "extra": 1},
            {"metrics": dict(good)},
            {"model": {k: v for k, v in good.items()
                       if k != "latency"}},
            {"model": dict(good, reasoning=2.0)},
            reordered,
            "not a record",
            None,
        ]
        for bad in bad_records:
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.validate_model_metrics(bad)
    finally:
        mods[0].unload()


def test_task_selection_by_primary_metric():
    mods = _load_modules()
    runtime = mods[1]
    try:
        primaries = {
            task: runtime.task_primary_metric(task)
            for task in MODEL_TASKS}
        chosen = {
            task: runtime.select_model_for_task(task, MODELS)
            for task in MODEL_TASKS}
        table = runtime.model_selection_table(
            "companionship", MODELS)
    finally:
        mods[0].unload()
    assert primaries == TASK_PRIMARY
    assert chosen["reasoning"] == "deep_thinker"
    assert chosen["companionship"] == "router_example"
    assert chosen["tool_work"] == "tool_hand"
    assert chosen["fast_response"] == "router_example"
    assert chosen["low_cost"] == "router_example"
    # Balanced scores the mean: the example model leads.
    assert chosen["balanced"] == "router_example"
    assert [row["model"] for row in table] == [
        "router_example", "tool_hand", "deep_thinker"]
    assert table[0]["score"] == 0.93
    assert table[0]["primary_metric"] == "persona_adherence"
    assert table[0]["metrics"] == METRICS_EXAMPLE["model"]


def test_task_selection_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for bad_task in ("everything", "", None, 3):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.task_primary_metric(bad_task)
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.select_model_for_task(bad_task, MODELS)
        for bad_models in ({}, {"qwen": {"reasoning": 0.5}},
                           {"Qwen": dict(METRICS_EXAMPLE["model"]),
                            "qwen": dict(METRICS_EXAMPLE["model"])},
                           "models", None):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.model_selection_table(
                    "reasoning", bad_models)
    finally:
        mods[0].unload()


def test_kernel_tiers_targets_and_budget():
    mods = _load_modules()
    runtime = mods[1]
    try:
        tiers = runtime.kernel_tiers()
        tiers.append("x")
        targets = runtime.kernel_tier_targets()
        targets["kernel_micro"] = 1
        budgets = {
            value: runtime.kernel_tier_for_budget(value)
            for value in (2000, 1500, 1499, 750, 749, 250)}
    finally:
        mods[0].unload()
    assert runtime.kernel_tiers() == KERNEL_TIERS
    assert list(runtime.KERNEL_TIERS) == KERNEL_TIERS
    assert runtime.kernel_tier_targets() == KERNEL_TARGETS
    assert dict(runtime.KERNEL_TIER_TARGETS) == KERNEL_TARGETS
    # The full target is the §5 kernel ceiling.
    assert runtime.kernel_tier_target("kernel_full") == \
        runtime.KERNEL_TOKEN_MAX == 1500
    assert budgets == {
        2000: "kernel_full", 1500: "kernel_full",
        1499: "kernel_medium", 750: "kernel_medium",
        749: "kernel_micro", 250: "kernel_micro"}


def test_kernel_tier_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for bad in ("kernel_tiny", "", None, 250):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.kernel_tier_target(bad)
        for bad_budget in (249, 0, -1, True, 750.0, "750", None):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.kernel_tier_for_budget(bad_budget)
    finally:
        mods[0].unload()


def test_distilled_record_plan_and_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        record = runtime.distilled_kernel_record(
            "kernel_micro", KERNEL_HASH, 240)
        validated = runtime.validate_distilled_kernel_record(
            {"distilled_kernel": dict(record["distilled_kernel"])})
        over = runtime.distilled_kernel_record(
            "kernel_micro", KERNEL_HASH, 300)
        plan = runtime.kernel_distillation_plan({"kernel": {
            "sha256": KERNEL_HASH, "estimated_tokens": 1400}})
        contract = runtime.kernel_distillation_contract()
    finally:
        mods[0].unload()
    assert validated == record == {"distilled_kernel": {
        "tier": "kernel_micro", "target_tokens": 250,
        "kernel_hash": KERNEL_HASH, "estimated_tokens": 240,
        "within_target": True,
        "source": "canonical_persona_kernel"}}
    assert over["distilled_kernel"]["within_target"] is False
    # A 1400-token source kernel fits only the full tier
    # undistilled; every tier derives from the same source.
    assert plan == {
        "source": "canonical_persona_kernel",
        "kernel_hash": KERNEL_HASH,
        "source_estimated_tokens": 1400,
        "tiers": [
            {"tier": "kernel_full", "target_tokens": 1500,
             "fits_source_kernel": True},
            {"tier": "kernel_medium", "target_tokens": 750,
             "fits_source_kernel": False},
            {"tier": "kernel_micro", "target_tokens": 250,
             "fits_source_kernel": False},
        ],
        "same_canonical_source": True,
        "builds_kernels": False,
    }
    assert contract == {
        "name": "PersonaKernelDistillation",
        "tiers": KERNEL_TIERS,
        "target_tokens": KERNEL_TARGETS,
        "same_canonical_source": True,
        "micro_below_section_5_band": True,
        "micro_kernel_section": 65,
        "builds_kernels": False,
    }


def test_distilled_record_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        good = runtime.distilled_kernel_record(
            "kernel_full", KERNEL_HASH, 1400)["distilled_kernel"]
        reordered = {"distilled_kernel": dict(reversed(
            list(good.items())))}
        bad_records = [
            {"distilled_kernel": dict(good), "extra": 1},
            {"kernel": dict(good)},
            {"distilled_kernel": dict(good, target_tokens=999)},
            {"distilled_kernel": dict(good, within_target=False)},
            {"distilled_kernel": dict(good, source="other")},
            reordered,
            "not a record",
            None,
        ]
        for bad in bad_records:
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.validate_distilled_kernel_record(bad)
        for args in (("kernel_tiny", KERNEL_HASH, 100),
                     ("kernel_micro", "", 100),
                     ("kernel_micro", KERNEL_HASH, 0),
                     ("kernel_micro", KERNEL_HASH, True),
                     ("kernel_micro", KERNEL_HASH, 12.5)):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.distilled_kernel_record(*args)
        for bad_plan in (None, {}, {"kernel": {}},
                         {"kernel": {"sha256": KERNEL_HASH}},
                         {"kernel": {"sha256": KERNEL_HASH,
                                     "estimated_tokens": "many"}}):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.kernel_distillation_plan(bad_plan)
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
        example = runtime.model_metrics_example()
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
            other_example = runtime.model_metrics_example()
        finally:
            reset_hermes_home_override(token)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert before == after
    assert example == other_example
    assert first[0].content == second[0].content == third[0].content
    assert len(first) == 1
    content = first[0].content
    assert "§§3-76" in content
    assert "§63 model metrics" in content
    assert "persona adherence" in content
    assert "§64 kernel distillation" in content
    assert "same canonical" in content
    # The packet names the contracts only — never canonical
    # persona text.
    assert "longhouse terminal" not in content
