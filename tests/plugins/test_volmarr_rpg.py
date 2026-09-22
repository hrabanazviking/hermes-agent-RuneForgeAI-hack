"""Behavior contracts for deterministic personal RPG mechanics."""

from __future__ import annotations

import json

from hermes_constants import get_hermes_home


def _enable_plugin() -> None:
    home = get_hermes_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [volmarr-rpg]\n",
        encoding="utf-8",
    )


def test_real_discovery_roll_is_replayable_and_exposes_arithmetic():
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    _enable_plugin()
    manager = PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-rpg"]
        assert loaded.enabled
        assert set(loaded.tools_registered) == {"dice_roll", "rpg_skill_check"}
        args = {"count": 4, "sides": 6, "modifier": 3, "seed": 0}
        first = json.loads(registry.dispatch("dice_roll", args, scope=manager.scope_key))
        second = json.loads(registry.dispatch("dice_roll", args, scope=manager.scope_key))
    finally:
        manager.unload()

    assert first == second
    assert len(first["rolls"]) == first["count"] == 4
    assert all(1 <= die <= first["sides"] for die in first["rolls"])
    assert first["subtotal"] == sum(first["rolls"])
    assert first["total"] == first["subtotal"] + first["modifier"]
    assert first["notation"] == "4d6+3"


def test_roll_rejects_boolean_and_unbounded_inputs():
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    _enable_plugin()
    manager = PluginManager()
    manager.discover_and_load()
    try:
        boolean = json.loads(
            registry.dispatch(
                "dice_roll",
                {"count": True, "sides": 20, "seed": 1},
                scope=manager.scope_key,
            )
        )
        oversized = json.loads(
            registry.dispatch(
                "dice_roll",
                {"count": 101, "sides": 20, "seed": 1},
                scope=manager.scope_key,
            )
        )
        extra = json.loads(
            registry.dispatch(
                "dice_roll",
                {"count": 1, "sides": 20, "seed": 1, "label": "private"},
                scope=manager.scope_key,
            )
        )
    finally:
        manager.unload()

    assert "error" in boolean
    assert "error" in oversized
    assert "error" in extra


def test_skill_check_applies_advantage_disadvantage_and_dc_arithmetic():
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    _enable_plugin()
    manager = PluginManager()
    manager.discover_and_load()
    try:
        results = {}
        for mode in ("normal", "advantage", "disadvantage"):
            results[mode] = json.loads(
                registry.dispatch(
                    "rpg_skill_check",
                    {
                        "modifier": 5,
                        "difficulty_class": 15,
                        "mode": mode,
                        "seed": 17,
                    },
                    scope=manager.scope_key,
                )
            )
    finally:
        manager.unload()

    assert len(results["normal"]["natural_rolls"]) == 1
    assert results["advantage"]["kept_roll"] == max(results["advantage"]["natural_rolls"])
    assert results["disadvantage"]["kept_roll"] == min(
        results["disadvantage"]["natural_rolls"]
    )
    for result in results.values():
        assert result["total"] == result["kept_roll"] + result["modifier"]
        assert result["check_succeeds"] is (
            result["total"] >= result["difficulty_class"]
        )
        assert result["natural_d20_automatic"] is False
