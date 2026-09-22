"""Contracts for the local official RuneTarot deck boundary."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)


def _write_profile(home: Path, engine_root: Path, *, timeout: object = 10) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-tarot]\n"
        "  entries:\n"
        "    volmarr-tarot:\n"
        "      settings:\n"
        f"        engine_root: {json.dumps(str(engine_root))}\n"
        f"        python_path: {json.dumps(sys.executable)}\n"
        f"        timeout_seconds: {json.dumps(timeout)}\n",
        encoding="utf-8",
    )


def _fake_engine(root: Path, card_name: str, record: Path | None = None) -> None:
    (root / "src").mkdir(parents=True)
    (root / "data").mkdir()
    (root / "src" / "__init__.py").write_text("", encoding="utf-8")
    record_code = ""
    if record is not None:
        record_code = (
            "        payload = {\n"
            "            'count': count, 'allow_reversals': allow_reversals, 'seed': seed,\n"
            "            'stdin_closed': sys.stdin.read(1) == '',\n"
            "            'secret_present': os.environ.get('OPENROUTER_API_KEY') is not None,\n"
            "            'hermes_home_present': os.environ.get('HERMES_HOME') is not None,\n"
            "        }\n"
            f"        Path({str(record)!r}).write_text(json.dumps(payload), encoding='utf-8')\n"
        )
    module = f'''import json, os, sys
from pathlib import Path

class Card:
    card_id = "major_0"
    display_name = {card_name!r}
    suit = "major"
    is_reversed = True
    element = "air"
    keywords = ["beginning", "possibility"]
    current_meanings = ["a clean beginning"]
    gd_title = "The Spirit of Aether"
    gd_meaning = "A leap into possibility"
    hebrew_letter = "Aleph"
    astrological = "Air"
    tree_path = 11
    number = 0

class TarotDeck:
    def load_cards(self):
        return [Card()] * 78

    def count(self):
        return 78

    def draw_full_hand(self, count, allow_reversals, seed):
{record_code}        Card.is_reversed = allow_reversals
        return [Card()]
'''
    (root / "src" / "deck.py").write_text(module, encoding="utf-8")


def test_real_discovery_draws_one_reproducible_card_without_credentials_or_state(
    tmp_path,
    monkeypatch,
):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home = get_hermes_home()
    engine_root = tmp_path / "runetarot"
    record = tmp_path / "draw.json"
    _fake_engine(engine_root, "The Fool", record)
    _write_profile(home, engine_root)
    monkeypatch.setenv("OPENROUTER_API_KEY", "must-not-reach-runetarot")

    manager = PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-tarot"]
        assert loaded.enabled
        assert loaded.tools_registered == ["tarot_draw"]
        result = json.loads(
            registry.dispatch(
                "tarot_draw",
                {"seed": 42, "allow_reversals": False},
                scope=manager.scope_key,
            )
        )
    finally:
        manager.unload()

    assert result["calculation"] == "single_card_draw"
    assert result["seed"] == 42
    assert result["interpretation_included"] is False
    assert result["card"]["name"] == "The Fool"
    assert result["card"]["reversed"] is False
    assert json.loads(record.read_text(encoding="utf-8")) == {
        "count": 1,
        "allow_reversals": False,
        "seed": 42,
        "stdin_closed": True,
        "secret_present": False,
        "hermes_home_present": False,
    }
    assert not (engine_root / "session").exists()
    assert not (engine_root / "exports").exists()


def test_draw_resolves_active_profile_a_b_a(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home_a = get_hermes_home()
    home_b = tmp_path / "profile-b"
    engine_a = tmp_path / "tarot-a"
    engine_b = tmp_path / "tarot-b"
    _fake_engine(engine_a, "Card for Profile A")
    _fake_engine(engine_b, "Card for Profile B")
    _write_profile(home_a, engine_a)
    _write_profile(home_b, engine_b)

    manager = PluginManager()
    manager.discover_and_load()
    try:
        names = []
        for home in (home_a, home_b, home_a):
            token = set_hermes_home_override(home)
            try:
                result = json.loads(
                    registry.dispatch(
                        "tarot_draw",
                        {"seed": 7},
                        scope=manager.scope_key,
                    )
                )
                names.append(result["card"]["name"])
            finally:
                reset_hermes_home_override(token)
    finally:
        manager.unload()

    assert names == ["Card for Profile A", "Card for Profile B", "Card for Profile A"]


def test_draw_rejects_invalid_arguments_before_starting_engine(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home = get_hermes_home()
    engine_root = tmp_path / "runetarot"
    marker = tmp_path / "should-not-exist"
    _fake_engine(engine_root, "Never Drawn", marker)
    _write_profile(home, engine_root)

    manager = PluginManager()
    manager.discover_and_load()
    try:
        missing = json.loads(
            registry.dispatch("tarot_draw", {}, scope=manager.scope_key)
        )
        boolean_seed = json.loads(
            registry.dispatch("tarot_draw", {"seed": True}, scope=manager.scope_key)
        )
        extra = json.loads(
            registry.dispatch(
                "tarot_draw",
                {"seed": 1, "question": "private question"},
                scope=manager.scope_key,
            )
        )
    finally:
        manager.unload()

    assert "error" in missing
    assert "error" in boolean_seed
    assert "error" in extra
    assert not marker.exists()
