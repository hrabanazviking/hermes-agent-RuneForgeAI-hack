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
    (package / "forms.py").write_text(
        '''class Form:
    def __init__(self, key, old_norse): self.key, self.old_norse = key, old_norse
    def name(self): return self.key
    def name_on(self): return self.old_norse
    def syllable_range(self): return (4, 6)
    def describe(self): return f"Official structure for {self.old_norse}"
    def validate_stanza(self, lines): return len(lines) == 4

class Line:
    def __init__(self, text, syllables, alliteration_group):
        self.text = text
        self.syllables = syllables
        self.alliteration_group = alliteration_group

FORMS = {
    "fornyrthislag": Form("fornyrthislag", "fornyrðislag"),
    "fornyrdislag": Form("fornyrthislag", "fornyrðislag"),
    "ljodhattr": Form("ljodhattr", "ljóðaháttr"),
    "drottkvaett": Form("drottkvaett", "dróttkvætt"),
    "malahattr": Form("malahattr", "málaháttr"),
}

def get_form(key): return FORMS[key]
''',
        encoding="utf-8",
    )
    (package / "lexicon.py").write_text(
        '''class Kenning:
    base = "sea"
    expression = "whale-road"
    components = ["whale", "road"]
    domain = "vanaheim"
    syllable_count = 2

def count_syllables_approx(word): return 1
def alliteration_group(word): return word[0].lower() if word else ""

class Lexicon:
    def __init__(self, seed=None):
        self.seed = seed
        self.kennings = [Kenning()]
''',
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


def test_forms_catalog_uses_official_registry_and_removes_aliases(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home = get_hermes_home()
    root = tmp_path / "seidr-engine"
    _fake_engine(root, "unused")
    _write_profile(home, root)
    manager = PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-seidr"]
        assert set(loaded.tools_registered) == {
            "seidr_compose",
            "seidr_forms",
            "seidr_kennings",
            "seidr_validate_meter",
        }
        result = json.loads(
            registry.dispatch("seidr_forms", {}, scope=manager.scope_key)
        )
    finally:
        manager.unload()
    keys = [item["key"] for item in result["forms"]]
    assert keys == ["fornyrthislag", "ljodhattr", "drottkvaett", "malahattr"]
    assert "fornyrdislag" not in keys
    assert result["forms"][0]["syllables_per_line"] == {"minimum": 4, "maximum": 6}


def test_kennings_catalog_comes_from_official_lexicon(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home = get_hermes_home()
    root = tmp_path / "seidr-engine"
    _fake_engine(root, "unused")
    _write_profile(home, root)
    manager = PluginManager()
    manager.discover_and_load()
    try:
        result = json.loads(
            registry.dispatch("seidr_kennings", {}, scope=manager.scope_key)
        )
    finally:
        manager.unload()
    assert result["kennings"] == [
        {
            "base": "sea",
            "expression": "whale-road",
            "components": ["whale", "road"],
            "domain": "vanaheim",
            "syllables": 2,
        }
    ]


def test_meter_validation_uses_official_form_and_line_metrics(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home = get_hermes_home()
    root = tmp_path / "seidr-engine"
    _fake_engine(root, "unused")
    _write_profile(home, root)
    lines = ["Wyrd wakes", "Wolves wander", "Runes rise", "Ravens return"]
    manager = PluginManager()
    manager.discover_and_load()
    try:
        result = json.loads(
            registry.dispatch(
                "seidr_validate_meter",
                {"form": "fornyrthislag", "lines": lines},
                scope=manager.scope_key,
            )
        )
    finally:
        manager.unload()
    validation = result["validation"]
    assert validation["valid"] is True
    assert [line["syllables"] for line in validation["lines"]] == [2, 2, 2, 2]
    assert [line["alliteration_group"] for line in validation["lines"]] == [
        "w",
        "w",
        "r",
        "r",
    ]


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
