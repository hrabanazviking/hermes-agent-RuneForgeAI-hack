"""Contracts for the local official Seiðr Engine boundary."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from hermes_constants import get_hermes_home, reset_hermes_home_override, set_hermes_home_override


def _write_profile(home: Path, engine_root: Path) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-seidr]\n"
        "  entries:\n"
        "    volmarr-seidr:\n"
        "      settings:\n"
        f"        engine_root: {json.dumps(str(engine_root))}\n"
        f"        python_path: {json.dumps(sys.executable)}\n",
        encoding="utf-8",
    )


def _fake_engine(root: Path, verse: str, record: Path | None = None) -> None:
    package = root / "seidr"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "forms.py").write_text("", encoding="utf-8")
    (package / "lexicon.py").write_text(
        "class Lexicon:\n    def __init__(self, seed=None): self.seed = seed\n",
        encoding="utf-8",
    )
    record_code = ""
    if record is not None:
        record_code = (
            "        import json, os, sys\n"
            "        from pathlib import Path\n"
            f"        Path({str(record)!r}).write_text(json.dumps({{'seed': config.seed, "
            "'form': config.form, 'domain': config.domain, 'stanzas': config.num_stanzas, "
            "'kennings': config.use_kennings, 'stdin_closed': sys.stdin.read(1) == '', "
            "'secret_present': os.environ.get('OPENROUTER_API_KEY') is not None, "
            "'hermes_home_present': os.environ.get('HERMES_HOME') is not None}))\n"
        )
    poet = f'''class PoemConfig:
    def __init__(self, form, domain, num_stanzas, use_kennings, seed):
        self.form = form
        self.domain = domain
        self.num_stanzas = num_stanzas
        self.use_kennings = use_kennings
        self.seed = seed

class Line:
    text = {verse!r}
    syllables = 4
    alliteration_group = "w"
    domain = "asgard"

class Stanza:
    def __init__(self, form, domain):
        self.form = form
        self.domain = domain
        self.lines = [Line()]

class Poem:
    def __init__(self, config):
        self.stanzas = [Stanza(config.form, config.domain) for _ in range(config.num_stanzas)]
    def format(self):
        return {verse!r}

class Skald:
    def __init__(self, lexicon=None, seed=None): pass
    def compose_poem(self, config):
{record_code}        return Poem(config)
'''
    (package / "poet.py").write_text(poet, encoding="utf-8")


def test_real_discovery_composes_seeded_verse_without_credentials(tmp_path, monkeypatch):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home = get_hermes_home()
    root = tmp_path / "seidr-engine"
    record = tmp_path / "compose.json"
    _fake_engine(root, "Wyrd wakes", record)
    _write_profile(home, root)
    monkeypatch.setenv("OPENROUTER_API_KEY", "must-not-reach-seidr")
    manager = PluginManager()
    manager.discover_and_load()
    try:
        result = json.loads(
            registry.dispatch(
                "seidr_compose",
                {"form": "fornyrthislag", "domain": "asgard", "stanzas": 2, "seed": 1},
                scope=manager.scope_key,
            )
        )
    finally:
        manager.unload()
    assert "error" not in result, result
    assert result["ai_generated"] is False
    assert result["poem"]["verse"] == "Wyrd wakes"
    assert len(result["poem"]["stanzas"]) == 2
    assert json.loads(record.read_text(encoding="utf-8")) == {
        "seed": 1,
        "form": "fornyrthislag",
        "domain": "asgard",
        "stanzas": 2,
        "kennings": True,
        "stdin_closed": True,
        "secret_present": False,
        "hermes_home_present": False,
    }


def test_compose_resolves_active_profile_a_b_a(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home_a = get_hermes_home()
    home_b = tmp_path / "profile-b"
    root_a = tmp_path / "seidr-a"
    root_b = tmp_path / "seidr-b"
    _fake_engine(root_a, "Verse A")
    _fake_engine(root_b, "Verse B")
    _write_profile(home_a, root_a)
    _write_profile(home_b, root_b)
    manager = PluginManager()
    manager.discover_and_load()
    try:
        verses = []
        for home in (home_a, home_b, home_a):
            token = set_hermes_home_override(home)
            try:
                result = json.loads(
                    registry.dispatch(
                        "seidr_compose",
                        {"form": "ljodhattr", "seed": 9},
                        scope=manager.scope_key,
                    )
                )
                verses.append(result["poem"]["verse"])
            finally:
                reset_hermes_home_override(token)
    finally:
        manager.unload()
    assert verses == ["Verse A", "Verse B", "Verse A"]


def test_compose_rejects_invalid_arguments_before_engine(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home = get_hermes_home()
    root = tmp_path / "seidr-engine"
    marker = tmp_path / "should-not-exist"
    _fake_engine(root, "Never composed", marker)
    _write_profile(home, root)
    manager = PluginManager()
    manager.discover_and_load()
    try:
        invalid = json.loads(
            registry.dispatch(
                "seidr_compose",
                {"form": "free_verse", "seed": 1},
                scope=manager.scope_key,
            )
        )
        extra = json.loads(
            registry.dispatch(
                "seidr_compose",
                {"form": "fornyrthislag", "seed": 1, "topic": "private topic"},
                scope=manager.scope_key,
            )
        )
        zero_seed = json.loads(
            registry.dispatch(
                "seidr_compose",
                {"form": "fornyrthislag", "seed": 0},
                scope=manager.scope_key,
            )
        )
    finally:
        manager.unload()
    assert "error" in invalid
    assert "error" in extra
    assert "error" in zero_seed
    assert not marker.exists()
