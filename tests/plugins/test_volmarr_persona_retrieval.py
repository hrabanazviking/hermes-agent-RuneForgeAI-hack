"""Contracts for hybrid persona retrieval (Slice 122).

Persona Runtime roadmap §13 (hybrid persona retrieval: do
not rely only on embeddings — semantic similarity + keyword
matching + document role + section tags + current task
classification + priority; results named by §12 stable ids,
e.g. a coding/git task loading
``service_bible.coding_preferences`` +
``tool_policy.git_policy``). The semantic component is
honestly unavailable here: this plugin owns no embedding
surface, so every score records ``semantic: None`` and the
component table names it unavailable — never a faked
similarity. Everything else is deterministic and pure.
Tests load through real plugin discovery.
"""

from __future__ import annotations

import hashlib
import importlib
from pathlib import Path

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

Speak warmly and plainly.
"""

SERVICE_DOC = """# Coding Preferences

Write coding work carefully: refactor code in small steps,
run tests, and keep git history clean.

# Opensource Values

Share code openly.
"""

TOOL_DOC = """# Git Policy

Use git branches for work; never force push a branch.

# Remote Git Operations

Remote git push operations need care and reversibility.

# Reversibility

Prefer reversible changes; every remote push should be
reversible.
"""

REL_DOC = """# When Caducea Disagrees

Offer counsel once, then accept the decision.
"""

AVATAR_DOC = """# Visual Identity

Raven hair, pale eyes.
"""

DOCS = {
    "core": ("core.md", CORE_DOC),
    "service_bible": ("bible.md", SERVICE_DOC),
    "tool_policy": ("tools.md", TOOL_DOC),
    "relationship": ("rel.md", REL_DOC),
    "avatar": ("avatar.md", AVATAR_DOC),
}

GIT_QUERY = "Refactor my Hermes Git branch files and push it"


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


def _write_persona(home: Path, docs=None) -> None:
    persona_dir = home / "persona"
    persona_dir.mkdir(parents=True, exist_ok=True)
    chosen = docs or DOCS
    for role, (name, text) in chosen.items():
        (persona_dir / name).write_text(text, encoding="utf-8")
    documents = {
        role: {"file": chosen[role][0], "required": True}
        for role in chosen
    }
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


def _hashes(home: Path) -> dict[str, str]:
    return {
        str(path.relative_to(home)):
            hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(home.rglob("*"))
        if path.is_file() and "entity" not in path.parts
    }


def _compile(runtime):
    return runtime.PersonaCompiler(_Ctx(ENABLED)).compile()


def test_classify_task_matches_the_roadmap_example():
    mods = _load_modules()
    runtime = mods[1]
    try:
        tags = runtime.classify_task(
            "Refactor my Hermes Git branch and push it")
        assert "coding" in tags
        assert "git" in tags
        assert "external_mutation" in tags
        assert runtime.classify_task(
            "Refactor my files and push it").count("filesystem") == 1
        assert runtime.classify_task("hello there") == []
        assert runtime.classify_task("") == []
        # Lexicon order is deterministic.
        assert tags == [t for t in runtime.task_tags() if t in tags]
    finally:
        mods[0].unload()


def test_hybrid_components_name_semantic_unavailable():
    mods = _load_modules()
    runtime = mods[1]
    try:
        components = {
            row["name"]: row for row in runtime.hybrid_components()}
        assert components["semantic_similarity"]["available"] is False
        assert "embedding" in components[
            "semantic_similarity"]["reason"]
        for name in ("keyword_matching", "document_role",
                     "section_tags", "task_classification", "priority"):
            assert components[name]["available"] is True
    finally:
        mods[0].unload()


def test_section_tags_and_score_are_pure_and_explainable():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        compiled = _compile(runtime)
        entry = next(
            row for row in compiled["index"]
            if row["stable_id"] == "tool_policy.git_policy")
        tags = runtime.section_tags(entry)
        assert "tool_policy" in tags and "git" in tags
        assert "tools" in tags  # the §8 category
        score = runtime.retrieval_score(
            entry, query="git branch", task_tags_=["git"])
        assert score["semantic"] is None
        assert score["keyword"] > 0 and score["task"] > 0
        assert score["role"] == 1.0
        assert score["priority"] == entry["priority"]
        assert 0.0 < score["total"] <= 1.0
        # Pure: same inputs, same outputs; an unrelated
        # section scores no task contact.
        assert score == runtime.retrieval_score(
            entry, query="git branch", task_tags_=["git"])
        other = next(
            row for row in compiled["index"]
            if row["stable_id"] == "avatar.visual_identity")
        assert runtime.retrieval_score(
            other, query="git branch", task_tags_=["git"])["task"] == 0.0
    finally:
        mods[0].unload()


def test_retrieval_loads_the_roadmap_example_sections():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        compiled = _compile(runtime)
        results = runtime.retrieve_sections(
            compiled["index"], query=GIT_QUERY, limit=5)
    finally:
        mods[0].unload()
    ids = [row["stable_id"] for row in results]
    # The §13 example's load set for a coding/git task.
    assert "service_bible.coding_preferences" in ids
    assert "tool_policy.git_policy" in ids
    assert "tool_policy.remote_git_operations" in ids
    assert "tool_policy.reversibility" in ids
    # Unrelated persona material is not retrieved.
    assert "avatar.visual_identity" not in ids
    assert "relationship.when_caducea_disagrees" not in ids
    # Explainable and deterministic: descending scores,
    # stable-id tiebreak, full component breakdown, and
    # the task classification is carried on every result.
    scores = [row["score"]["total"] for row in results]
    assert scores == sorted(scores, reverse=True)
    for row in results:
        assert row["score"]["semantic"] is None
        assert set(row["task_tags"]) >= {
            "coding", "git", "filesystem", "external_mutation"}
        assert row["text"]  # verbatim text (§7)


def test_retrieval_bounds_and_empty_signals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        compiled = _compile(runtime)
        index = compiled["index"]
        assert runtime.retrieve_sections(index, query="") == []
        assert runtime.retrieve_sections(
            index, query="zzzqqq unknownword") == []
        one = runtime.retrieve_sections(
            index, query=GIT_QUERY, limit=1)
        assert len(one) == 1
        clamped = runtime.retrieve_sections(
            index, query=GIT_QUERY, limit=999)
        assert len(clamped) <= 20
        # Deterministic across calls.
        assert [r["stable_id"] for r in clamped] == [
            r["stable_id"] for r in runtime.retrieve_sections(
                index, query=GIT_QUERY, limit=999)]
        # An explicit task text classifies independently
        # of the query wording.
        by_task = runtime.retrieve_sections(
            index, query="branch", task_text="push the git branch")
        assert by_task and by_task[0]["task_tags"] == runtime.classify_task(
            "push the git branch")
    finally:
        mods[0].unload()


def test_retriever_service_deterministic_writes_nothing():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        home = get_hermes_home()
        _write_persona(home)
        before = _hashes(home)
        retriever = runtime.PersonaRetriever(_Ctx(ENABLED))
        first = retriever.retrieve(query=GIT_QUERY)
        second = retriever.retrieve(query=GIT_QUERY)
        items = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        after = _hashes(home)
    finally:
        mods[0].unload()
    assert [r["stable_id"] for r in first] == \
        [r["stable_id"] for r in second]
    assert before == after
    assert len(items) == 1
    assert "§13 hybrid retrieval" in items[0].content
    assert "persistent Hermes entity" not in items[0].content


def test_retriever_without_persona_config_returns_empty():
    mods = _load_modules()
    runtime = mods[1]
    try:
        # No persona config in this fresh profile: compile
        # is None and retrieval is empty, not an error.
        empty = runtime.PersonaRetriever(_Ctx(ENABLED)).retrieve(
            query=GIT_QUERY)
    finally:
        mods[0].unload()
    assert empty == []


def test_profile_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        assert runtime.PersonaRetriever(
            _Ctx(ENABLED)).retrieve(query=GIT_QUERY)
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
