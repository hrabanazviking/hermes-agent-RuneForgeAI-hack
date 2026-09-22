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
        assert set(loaded.tools_registered) == {
            "dice_roll",
            "rpg_skill_check",
            "rpg_oracle",
        }
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


def test_oracle_is_replayable_and_separates_likelihood_from_chaos():
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    _enable_plugin()
    manager = PluginManager()
    manager.discover_and_load()
    try:
        baseline_args = {
            "likelihood": "likely",
            "chaos_factor": 1,
            "seed": 7,
        }
        first = json.loads(
            registry.dispatch("rpg_oracle", baseline_args, scope=manager.scope_key)
        )
        replay = json.loads(
            registry.dispatch("rpg_oracle", baseline_args, scope=manager.scope_key)
        )
        high_chaos = json.loads(
            registry.dispatch(
                "rpg_oracle",
                {**baseline_args, "chaos_factor": 9},
                scope=manager.scope_key,
            )
        )
        impossible = json.loads(
            registry.dispatch(
                "rpg_oracle",
                {**baseline_args, "likelihood": "impossible"},
                scope=manager.scope_key,
            )
        )
        certain = json.loads(
            registry.dispatch(
                "rpg_oracle",
                {**baseline_args, "likelihood": "certain"},
                scope=manager.scope_key,
            )
        )
    finally:
        manager.unload()

    assert first == replay
    assert 1 <= first["roll"] <= 100
    assert first["yes"] is (first["roll"] <= first["yes_chance_percent"])
    assert high_chaos["roll"] == first["roll"]
    assert high_chaos["yes_chance_percent"] == first["yes_chance_percent"]
    assert high_chaos["exceptional_band_percent"] > first["exceptional_band_percent"]
    assert impossible["yes"] is False
    assert certain["yes"] is True


def test_oracle_rejects_boolean_chaos_and_narrative_fields():
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    _enable_plugin()
    manager = PluginManager()
    manager.discover_and_load()
    try:
        invalid = []
        for args in (
            {"likelihood": "likely", "chaos_factor": True, "seed": 1},
            {"likelihood": "unknown", "chaos_factor": 5, "seed": 1},
            {
                "likelihood": "likely",
                "chaos_factor": 5,
                "seed": 1,
                "question": "Will the hidden door open?",
            },
        ):
            invalid.append(
                json.loads(registry.dispatch("rpg_oracle", args, scope=manager.scope_key))
            )
    finally:
        manager.unload()

    assert all("error" in result for result in invalid)
