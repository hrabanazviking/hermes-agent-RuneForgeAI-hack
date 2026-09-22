"""Behavior contracts for deterministic personal RPG mechanics."""

from __future__ import annotations

import json
from pathlib import Path

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)


def _enable_plugin(*, home: Path | None = None, srd_root: Path | None = None) -> None:
    home = home or get_hermes_home()
    home.mkdir(parents=True, exist_ok=True)
    config = "plugins:\n  enabled: [volmarr-rpg]\n"
    if srd_root is not None:
        config += (
            "  entries:\n"
            "    volmarr-rpg:\n"
            "      settings:\n"
            f"        srd_root: {json.dumps(str(srd_root))}\n"
        )
    (home / "config.yaml").write_text(config, encoding="utf-8")


def _fake_srd(root: Path, condition_name: str, rule: str) -> None:
    data_dir = root / "json"
    data_dir.mkdir(parents=True)
    (data_dir / "12 conditions.json").write_text(
        json.dumps(
            {
                "Appendix PH-A: Conditions": {
                    "content": ["Condition introduction."],
                    condition_name: [rule],
                }
            }
        ),
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
            "rpg_random_table",
            "rpg_condition_lookup",
            "rpg_random_character",
            "rpg_encounter_initiative",
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


def test_random_table_replays_a_bounded_dn_selection():
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    _enable_plugin()
    manager = PluginManager()
    manager.discover_and_load()
    try:
        args = {
            "entries": ["  distant bells  ", "broken bridge", "friendly raven"],
            "seed": 23,
        }
        first = json.loads(
            registry.dispatch("rpg_random_table", args, scope=manager.scope_key)
        )
        replay = json.loads(
            registry.dispatch("rpg_random_table", args, scope=manager.scope_key)
        )
    finally:
        manager.unload()

    assert first == replay
    assert first["notation"] == "1d3"
    assert first["entry_count"] == 3
    assert 1 <= first["roll"] <= first["entry_count"]
    assert first["selected_entry"] == args["entries"][first["roll"] - 1].strip()


def test_random_table_rejects_empty_oversized_and_extra_inputs():
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    _enable_plugin()
    manager = PluginManager()
    manager.discover_and_load()
    try:
        invalid = []
        for args in (
            {"entries": [], "seed": 1},
            {"entries": ["   "], "seed": 1},
            {"entries": ["x" * 201], "seed": 1},
            {"entries": ["one"], "seed": True},
            {"entries": ["one"], "seed": 1, "weights": [1]},
        ):
            invalid.append(
                json.loads(
                    registry.dispatch("rpg_random_table", args, scope=manager.scope_key)
                )
            )
    finally:
        manager.unload()

    assert all("error" in result for result in invalid)


def test_condition_lookup_reads_configured_external_srd_with_provenance(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    srd_root = tmp_path / "srd"
    _fake_srd(srd_root, "Blinded", "Sight-based checks fail.")
    _enable_plugin(srd_root=srd_root)
    manager = PluginManager()
    manager.discover_and_load()
    try:
        result = json.loads(
            registry.dispatch(
                "rpg_condition_lookup",
                {"condition": " blinded "},
                scope=manager.scope_key,
            )
        )
    finally:
        manager.unload()

    assert result["condition"] == "Blinded"
    assert result["definition"] == ["Sight-based checks fail."]
    assert result["source"] == {
        "corpus": "System Reference Document 5.0",
        "file": "json/12 conditions.json",
        "license": "OGL-1.0a",
    }


def test_condition_lookup_resolves_active_profile_a_b_a(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home_a = get_hermes_home()
    home_b = tmp_path / "home-b"
    srd_a = tmp_path / "srd-a"
    srd_b = tmp_path / "srd-b"
    _fake_srd(srd_a, "Prone", "Rule from profile A.")
    _fake_srd(srd_b, "Prone", "Rule from profile B.")
    _enable_plugin(home=home_a, srd_root=srd_a)
    _enable_plugin(home=home_b, srd_root=srd_b)

    manager = PluginManager()
    manager.discover_and_load()
    try:
        definitions = []
        for home in (home_a, home_b, home_a):
            token = set_hermes_home_override(home)
            try:
                result = json.loads(
                    registry.dispatch(
                        "rpg_condition_lookup",
                        {"condition": "Prone"},
                        scope=manager.scope_key,
                    )
                )
                definitions.append(result["definition"][0])
            finally:
                reset_hermes_home_override(token)
    finally:
        manager.unload()

    assert definitions == [
        "Rule from profile A.",
        "Rule from profile B.",
        "Rule from profile A.",
    ]


def test_condition_lookup_rejects_missing_source_unknown_and_extra_fields(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    missing_root = tmp_path / "missing"
    _enable_plugin(srd_root=missing_root)
    manager = PluginManager()
    manager.discover_and_load()
    try:
        invalid = []
        for args in (
            {"condition": "Blinded"},
            {"condition": ""},
            {"condition": "Blinded", "character": "private"},
        ):
            invalid.append(
                json.loads(
                    registry.dispatch(
                        "rpg_condition_lookup", args, scope=manager.scope_key
                    )
                )
            )
    finally:
        manager.unload()

    assert all("error" in result for result in invalid)


def test_random_character_replays_six_auditable_ability_scores():
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    _enable_plugin()
    manager = PluginManager()
    manager.discover_and_load()
    try:
        args = {"seed": 0}
        first = json.loads(
            registry.dispatch("rpg_random_character", args, scope=manager.scope_key)
        )
        replay = json.loads(
            registry.dispatch("rpg_random_character", args, scope=manager.scope_key)
        )
    finally:
        manager.unload()

    assert first == replay
    assert first["generation_method"] == "4d6_drop_lowest"
    assert first["character_complete"] is False
    assert list(first["abilities"]) == [
        "strength",
        "dexterity",
        "constitution",
        "intelligence",
        "wisdom",
        "charisma",
    ]
    for ability in first["abilities"].values():
        assert len(ability["rolls"]) == 4
        assert all(1 <= roll <= 6 for roll in ability["rolls"])
        dropped_index = ability["dropped_index"]
        assert ability["dropped_roll"] == ability["rolls"][dropped_index]
        assert ability["dropped_roll"] == min(ability["rolls"])
        kept = [
            roll for index, roll in enumerate(ability["rolls"]) if index != dropped_index
        ]
        assert ability["score"] == sum(kept)
        assert ability["modifier"] == (ability["score"] - 10) // 2


def test_random_character_rejects_boolean_seed_and_character_content():
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    _enable_plugin()
    manager = PluginManager()
    manager.discover_and_load()
    try:
        invalid = []
        for args in (
            {"seed": True},
            {"seed": -1},
            {"seed": 1, "name": "private"},
        ):
            invalid.append(
                json.loads(
                    registry.dispatch(
                        "rpg_random_character", args, scope=manager.scope_key
                    )
                )
            )
    finally:
        manager.unload()

    assert all("error" in result for result in invalid)


def test_encounter_initiative_replays_rolls_arithmetic_and_total_order():
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    _enable_plugin()
    manager = PluginManager()
    manager.discover_and_load()
    try:
        args = {
            "participants": [
                {"id": "hero", "modifier": 3},
                {"id": "rival", "modifier": 5},
                {"id": "wolf", "modifier": 2},
            ],
            "seed": 41,
        }
        first = json.loads(
            registry.dispatch("rpg_encounter_initiative", args, scope=manager.scope_key)
        )
        replay = json.loads(
            registry.dispatch("rpg_encounter_initiative", args, scope=manager.scope_key)
        )
    finally:
        manager.unload()

    assert first == replay
    assert first["participant_count"] == 3
    assert first["natural_d20_automatic"] is False
    assert [item["position"] for item in first["order"]] == [1, 2, 3]
    for item in first["order"]:
        assert 1 <= item["natural_roll"] <= 20
        assert item["total"] == item["natural_roll"] + item["modifier"]
    ordering_keys = [
        (-item["total"], -item["modifier"], item["id"].casefold(), item["input_index"])
        for item in first["order"]
    ]
    assert ordering_keys == sorted(ordering_keys)


def test_encounter_initiative_rejects_duplicate_ids_boolean_and_extra_fields():
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    _enable_plugin()
    manager = PluginManager()
    manager.discover_and_load()
    try:
        invalid = []
        for args in (
            {
                "participants": [
                    {"id": "Hero", "modifier": 1},
                    {"id": "hero", "modifier": 2},
                ],
                "seed": 1,
            },
            {"participants": [{"id": "hero", "modifier": True}], "seed": 1},
            {
                "participants": [{"id": "hero", "modifier": 1, "hp": 10}],
                "seed": 1,
            },
        ):
            invalid.append(
                json.loads(
                    registry.dispatch(
                        "rpg_encounter_initiative", args, scope=manager.scope_key
                    )
                )
            )
    finally:
        manager.unload()

    assert all("error" in result for result in invalid)
