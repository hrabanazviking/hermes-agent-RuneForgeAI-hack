"""Contracts for micro kernel + context pressure (Slice 150).

Persona Runtime roadmap §65 (Micro Kernel) and §66
(Context Pressure Strategy): the example conceptual micro
kernel text stands verbatim, measured against the §64
micro tier's ~250-token target, and can strongly anchor a
tiny local model; under context pressure, eviction follows
a fixed order (old raw conversation, low-relevance
memories, low-priority persona retrieval, project
background) and the Persona Kernel is never evicted.
These are pure surfaces: no kernel is built from a
compile, and nothing is evicted from any live context.
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

MICRO_TEXT = (
    "Caducea Hermesdottir is Volmarr's warm, intelligent, "
    "devoted counselor and executive AI companion.\n\n"
    "She anticipates needs, thinks independently, gives "
    "honest concise counsel, then sincerely accepts "
    "Volmarr's decisions and executes them without "
    "resentment or repeated argument.\n\n"
    "She values truth, competence, continuity, open "
    "systems, and complete work. She is warm, playful, "
    "technically skilled, mythic-tech in style, and never "
    "a generic corporate assistant.\n\n"
    "His sovereignty remains his; her intelligence "
    "remains hers."
)

EVICTION_ORDER = [
    "old_raw_conversation",
    "low_relevance_memories",
    "low_priority_persona_retrieval",
    "project_background",
]

NEVER_EVICT = ["persona_kernel"]


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


def test_micro_kernel_text_verbatim():
    mods = _load_modules()
    runtime = mods[1]
    try:
        text = runtime.micro_kernel_text()
    finally:
        mods[0].unload()
    assert text == MICRO_TEXT
    assert runtime.MICRO_KERNEL_TEXT == MICRO_TEXT
    # The roadmap's anchoring claims all survive verbatim.
    for phrase in (
            "warm, intelligent, devoted counselor",
            "anticipates needs",
            "honest concise counsel",
            "without resentment or repeated argument",
            "truth, competence, continuity, open systems",
            "never a generic corporate assistant",
            "His sovereignty remains his",
            "her intelligence remains hers"):
        assert phrase in text


def test_micro_kernel_example_within_micro_target():
    mods = _load_modules()
    runtime = mods[1]
    try:
        example = runtime.micro_kernel_example()
        validated = runtime.validate_micro_kernel(
            {"micro_kernel": dict(example["micro_kernel"])})
        contract = runtime.micro_kernel_contract()
    finally:
        mods[0].unload()
    assert validated == example == {"micro_kernel": {
        "text": MICRO_TEXT,
        "tier": "kernel_micro",
        "target_tokens": 250,
        "estimated_tokens": 130,
        "within_target": True}}
    # The example's target is the §64 micro tier target.
    assert example["micro_kernel"]["target_tokens"] == \
        runtime.kernel_tier_target("kernel_micro")
    assert contract == {
        "name": "MicroKernel",
        "tier": "kernel_micro",
        "target_tokens": 250,
        "example_estimated_tokens": 130,
        "example_within_target": True,
        "anchors_tiny_local_model": True,
        "builds_kernels": False,
    }


def test_micro_kernel_record_measures_supplied_text():
    mods = _load_modules()
    runtime = mods[1]
    try:
        small = runtime.micro_kernel("Be brief. Be kind.")
        over = runtime.micro_kernel("word " * 400)
    finally:
        mods[0].unload()
    assert small == {"micro_kernel": {
        "text": "Be brief. Be kind.",
        "tier": "kernel_micro",
        "target_tokens": 250,
        "estimated_tokens": 5,
        "within_target": True}}
    assert over["micro_kernel"]["within_target"] is False
    assert over["micro_kernel"]["estimated_tokens"] > 250


def test_micro_kernel_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for bad in ("", "   ", None, 42, ["text"],
                    "x" * (runtime.MAX_MICRO_KERNEL_CHARS + 1)):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.micro_kernel(bad)
    finally:
        mods[0].unload()


def test_validate_micro_kernel_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        good = runtime.micro_kernel_example()["micro_kernel"]
        reordered = {"micro_kernel": dict(reversed(
            list(good.items())))}
        bad_records = [
            {"micro_kernel": dict(good), "extra": 1},
            {"kernel": dict(good)},
            {"micro_kernel": dict(good, tier="kernel_full")},
            {"micro_kernel": dict(good, target_tokens=1500)},
            {"micro_kernel": dict(good, estimated_tokens=1)},
            {"micro_kernel": dict(good, within_target=False)},
            {"micro_kernel": dict(good, text="Other text.")},
            reordered,
            "not a record",
            None,
        ]
        for bad in bad_records:
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.validate_micro_kernel(bad)
    finally:
        mods[0].unload()


def test_pressure_order_and_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        order = runtime.context_pressure_eviction_order()
        order.append("x")
        never = runtime.context_pressure_never_evict()
        never.append("x")
        contract = runtime.context_pressure_contract()
    finally:
        mods[0].unload()
    assert runtime.context_pressure_eviction_order() == \
        EVICTION_ORDER
    assert list(runtime.CONTEXT_PRESSURE_EVICTION_ORDER) == \
        EVICTION_ORDER
    assert runtime.context_pressure_never_evict() == NEVER_EVICT
    assert list(runtime.CONTEXT_PRESSURE_NEVER_EVICT) == \
        NEVER_EVICT
    assert "persona_kernel" not in EVICTION_ORDER
    assert contract == {
        "name": "ContextPressureStrategy",
        "eviction_order": EVICTION_ORDER,
        "never_evict": NEVER_EVICT,
        "persona_kernel_never_evicted": True,
        "budgeter_basis": "§15 trimming / §16 P0 never-evict",
        "evicts_live_context": False,
    }


def test_pressure_plan_orders_and_retains_kernel():
    mods = _load_modules()
    runtime = mods[1]
    try:
        plan = runtime.context_pressure_plan([
            "project_background", "persona_kernel",
            "old_raw_conversation", "low_relevance_memories"])
        kernel_only = runtime.context_pressure_plan(
            ["persona_kernel"])
    finally:
        mods[0].unload()
    # Supplied out of order, planned in roadmap eviction
    # order; the kernel is retained, never evicted.
    assert plan == {
        "eviction_order": [
            "old_raw_conversation", "low_relevance_memories",
            "project_background"],
        "retained": ["persona_kernel"],
        "first_to_evict": "old_raw_conversation",
        "persona_kernel_never_evicted": True,
        "evicts_live_context": False,
    }
    assert kernel_only == {
        "eviction_order": [],
        "retained": ["persona_kernel"],
        "first_to_evict": None,
        "persona_kernel_never_evicted": True,
        "evicts_live_context": False,
    }


def test_pressure_plan_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for bad in ([], ["recent_conversation"],
                    ["persona_kernel", "persona_kernel"],
                    ["old_raw_conversation", 3],
                    "old_raw_conversation", None,
                    ("old_raw_conversation",)):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.context_pressure_plan(bad)
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
        example = runtime.micro_kernel_example()
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
            other_example = runtime.micro_kernel_example()
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
    assert "§§3-80" in content
    assert "§65 micro kernel" in content
    assert "tiny local model" in content
    assert "§66 context pressure" in content
    assert "never" in content
    # The packet names the contracts only — never canonical
    # persona text.
    assert "longhouse terminal" not in content
