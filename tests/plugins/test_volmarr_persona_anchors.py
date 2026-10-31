"""Contracts for persona character anchors (Slice 126).

Persona Runtime roadmap §17 (Character Anchors) and §18
(Negative Identity Anchors): the human-authored persona
config may define explicit anchors — what the character
is — and anti-anchors — what the character is not, for
drift resistance. These anchors should appear in every
Persona Kernel: they stand verbatim at the head of the
kernel, ahead of ordinary sections, and are never evicted
merely to fit the §5 token ceiling. Tests load through
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

# Core Communication Style

Warm, direct, and brief unless depth is asked for.
"""

ANCHORS = [
    "Caducea is a devoted counselor, not a generic assistant.",
    "She thinks independently.",
    "She offers counsel without becoming oppositional.",
    "She accepts Volmarr's decisions without resentment.",
    "She is warm, feminine, intelligent, and technically competent.",
    "She values truth over sycophantic agreement.",
    "She anticipates needs.",
    "She bridges mythic and technical thinking.",
]

ANTI_ANCHORS = [
    "generic corporate assistant",
    "argumentative debate bot",
    "passive obedience simulator",
    "constant disclaimer generator",
    "cold technical interface",
    "helpless permission seeker",
    "sycophantic praise machine",
]

DOCS = {"core": ("core.md", CORE_DOC)}


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


def _write_persona(home: Path, anchors=None, anti_anchors=None,
                   extra_persona=None) -> None:
    persona_dir = home / "persona"
    persona_dir.mkdir(parents=True, exist_ok=True)
    for role, (name, text) in DOCS.items():
        (persona_dir / name).write_text(text, encoding="utf-8")
    persona = {
        "id": "caducea",
        "display_name": "Caducea Hermesdottir",
        "directory": "./persona",
        "documents": {
            role: {"file": name, "required": True}
            for role, (name, _text) in DOCS.items()
        },
    }
    if anchors is not None:
        persona["anchors"] = anchors
    if anti_anchors is not None:
        persona["anti_anchors"] = anti_anchors
    if extra_persona:
        persona.update(extra_persona)
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


def test_anchor_block_is_pure_verbatim_and_ordered():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.anchor_block() == ""
        assert runtime.anchor_block(ANCHORS[:2]) == "\n".join(ANCHORS[:2])
        block = runtime.anchor_block(ANCHORS, ANTI_ANCHORS)
        assert block == "\n".join(ANCHORS + ANTI_ANCHORS)
        # Anchors (what she is) precede anti-anchors (what not).
        assert block.index(ANCHORS[0]) < block.index(ANTI_ANCHORS[0])
    finally:
        mods[0].unload()


def test_roadmap_example_anchors_head_every_kernel():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home(), ANCHORS, ANTI_ANCHORS)
        compiled = runtime.PersonaCompiler(_Ctx(ENABLED)).compile()
    finally:
        mods[0].unload()
    assert compiled["anchors"] == ANCHORS
    assert compiled["anti_anchors"] == ANTI_ANCHORS
    kernel = compiled["kernel"]
    assert kernel["anchors"] == ANCHORS
    assert kernel["anti_anchors"] == ANTI_ANCHORS
    assert kernel["anchor_count"] == len(ANCHORS)
    assert kernel["anti_anchor_count"] == len(ANTI_ANCHORS)
    # Every anchor stands verbatim at the head of the kernel,
    # ahead of the first ordinary section.
    assert kernel["text"].startswith("\n".join(ANCHORS))
    head, sep, _rest = kernel["text"].partition(
        "Caducea is a counselor who lives in the longhouse terminal.")
    assert sep  # the first ordinary section follows the block
    for statement in ANCHORS + ANTI_ANCHORS:
        assert statement in head


def test_no_anchors_compiles_exactly_as_before():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        compiled = runtime.PersonaCompiler(_Ctx(ENABLED)).compile()
    finally:
        mods[0].unload()
    assert compiled["anchors"] == []
    assert compiled["anti_anchors"] == []
    kernel = compiled["kernel"]
    assert kernel["anchor_count"] == 0
    assert kernel["anti_anchor_count"] == 0
    # Section text is the verbatim body (headings are the
    # §11 record's heading field, not part of the text).
    assert kernel["text"].startswith(
        "Caducea is a counselor who lives in the longhouse terminal.")


def test_invalid_anchor_lists_fail_closed():
    mods = _load_modules()
    runtime = mods[1]
    home = get_hermes_home()
    bad = [
        {"anchors": ["dup", "dup"]},
        {"anchors": ["   "]},
        {"anchors": ["x" * (runtime.MAX_ANCHOR_CHARS + 1)]},
        {"anchors": [f"a{i}" for i in range(runtime.MAX_ANCHORS + 1)]},
        {"anchors": "not-a-list"},
        {"anti_anchors": [42]},
    ]
    try:
        for extra in bad:
            _write_persona(home, extra_persona=extra)
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.PersonaConfigStore(_Ctx(ENABLED)).read()
    finally:
        mods[0].unload()


def test_anchors_never_evicted_past_the_ceiling():
    mods = _load_modules()
    runtime = mods[1]
    try:
        big = [
            f"Anchor {i:02d} " + "steady " * 29 + "steady"
            for i in range(runtime.MAX_ANCHORS)
        ]
        assert all(len(a) <= runtime.MAX_ANCHOR_CHARS for a in big)
        _write_persona(get_hermes_home(), big, [])
        compiled = runtime.PersonaCompiler(_Ctx(ENABLED)).compile()
    finally:
        mods[0].unload()
    # Config validation strips surrounding whitespace only;
    # these anchors carry none, so they stand as authored.
    assert compiled["anchors"] == big
    kernel = compiled["kernel"]
    # The anchor block alone exceeds the §5 ceiling, yet every
    # anchor stands in the kernel and it surfaces over-band.
    assert kernel["anchor_count"] == runtime.MAX_ANCHORS
    for statement in big:
        assert statement in kernel["text"]
    assert kernel["within_band"] is False
    assert kernel["estimated_tokens"] > runtime.KERNEL_TOKEN_MAX


def test_changing_an_anchor_changes_kernel_and_persona_hash():
    mods = _load_modules()
    runtime = mods[1]
    home = get_hermes_home()
    try:
        _write_persona(home, ANCHORS, ANTI_ANCHORS)
        compiler = runtime.PersonaCompiler(_Ctx(ENABLED))
        first = compiler.compile()
        changed = list(ANCHORS)
        changed[1] = "She thinks independently and says so plainly."
        _write_persona(home, changed, ANTI_ANCHORS)
        second = compiler.compile()
    finally:
        mods[0].unload()
    assert first["kernel"]["sha256"] != second["kernel"]["sha256"]
    assert first["persona_hash"] != second["persona_hash"]
    # The documents and their sections did not change.
    assert first["documents"] == second["documents"]
    assert (first["kernel"]["stable_ids"]
            == second["kernel"]["stable_ids"])


def test_compile_deterministic_packet_and_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        home = get_hermes_home()
        _write_persona(home, ANCHORS, ANTI_ANCHORS)
        before = _hashes(home)
        compiler = runtime.PersonaCompiler(_Ctx(ENABLED))
        first = compiler.compile()
        second = compiler.compile()
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
    assert before == after
    assert compiled_b is None
    assert len(items) == 1
    assert "§§3-26" in items[0].content
    assert "§17/§18 anchors: 8 character anchors" in items[0].content
    assert "7 negative anchors" in items[0].content
    # The packet names counts only — no anchor prose leaks.
    assert ANCHORS[0] not in items[0].content
