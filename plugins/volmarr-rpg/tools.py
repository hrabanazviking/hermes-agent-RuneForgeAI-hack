"""Bounded deterministic tabletop mechanics."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from tools.registry import tool_error, tool_result


_MAX_SEED = 2**31 - 1
_MAX_SRD_FILE_BYTES = 64 * 1024
_ORACLE_YES_CHANCES = {
    "impossible": 0,
    "no_way": 5,
    "very_unlikely": 15,
    "unlikely": 30,
    "fifty_fifty": 50,
    "likely": 70,
    "very_likely": 85,
    "near_certain": 95,
    "certain": 100,
}

DICE_ROLL_SCHEMA = {
    "name": "dice_roll",
    "description": (
        "Roll a bounded number of identical dice with an explicit reproducibility seed "
        "and optional flat modifier. Returns every die and the arithmetic evidence."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "count": {"type": "integer", "minimum": 1, "maximum": 100},
            "sides": {"type": "integer", "minimum": 2, "maximum": 1000},
            "modifier": {"type": "integer", "minimum": -10000, "maximum": 10000},
            "seed": {"type": "integer", "minimum": 0, "maximum": _MAX_SEED},
        },
        "required": ["count", "sides", "seed"],
        "additionalProperties": False,
    },
}

RPG_SKILL_CHECK_SCHEMA = {
    "name": "rpg_skill_check",
    "description": (
        "Resolve a replayable d20 ability or skill check against a DC, with normal, "
        "advantage, or disadvantage selection and an explicit total modifier."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "modifier": {"type": "integer", "minimum": -30, "maximum": 30},
            "difficulty_class": {"type": "integer", "minimum": 0, "maximum": 50},
            "mode": {
                "type": "string",
                "enum": ["normal", "advantage", "disadvantage"],
                "default": "normal",
            },
            "seed": {"type": "integer", "minimum": 0, "maximum": _MAX_SEED},
        },
        "required": ["modifier", "difficulty_class", "seed"],
        "additionalProperties": False,
    },
}

RPG_ORACLE_SCHEMA = {
    "name": "rpg_oracle",
    "description": (
        "Resolve a replayable binary RPG oracle from an explicit likelihood, chaos "
        "factor, and seed. Chaos widens only the exceptional-result band."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "likelihood": {
                "type": "string",
                "enum": list(_ORACLE_YES_CHANCES),
            },
            "chaos_factor": {"type": "integer", "minimum": 1, "maximum": 9},
            "seed": {"type": "integer", "minimum": 0, "maximum": _MAX_SEED},
        },
        "required": ["likelihood", "chaos_factor", "seed"],
        "additionalProperties": False,
    },
}

RPG_RANDOM_TABLE_SCHEMA = {
    "name": "rpg_random_table",
    "description": (
        "Select one entry from a caller-supplied bounded random table with an explicit "
        "reproducibility seed. Returns the dN-style roll and selected entry."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "entries": {
                "type": "array",
                "minItems": 1,
                "maxItems": 100,
                "items": {"type": "string", "minLength": 1, "maxLength": 200},
            },
            "seed": {"type": "integer", "minimum": 0, "maximum": _MAX_SEED},
        },
        "required": ["entries", "seed"],
        "additionalProperties": False,
    },
}

RPG_CONDITION_LOOKUP_SCHEMA = {
    "name": "rpg_condition_lookup",
    "description": (
        "Look up one condition in a configured external SRD 5 checkout. Returns the "
        "source definition and license provenance without bundling SRD content in Hermes."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "condition": {"type": "string", "minLength": 1, "maxLength": 60},
        },
        "required": ["condition"],
        "additionalProperties": False,
    },
}


def _integer(value: Any, *, minimum: int, maximum: int) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if minimum <= value <= maximum else None


def _configured_conditions_file(value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        return None
    candidate = Path(value.strip()).expanduser()
    if not candidate.is_absolute():
        return None
    try:
        root = candidate.resolve()
        conditions_file = root / "json" / "12 conditions.json"
        size = conditions_file.stat().st_size
    except OSError:
        return None
    if not root.is_dir() or not conditions_file.is_file():
        return None
    if not 1 <= size <= _MAX_SRD_FILE_BYTES:
        return None
    return conditions_file


def _load_conditions(ctx) -> dict[str, Any] | None:
    conditions_file = _configured_conditions_file(ctx.get_config("srd_root", ""))
    if conditions_file is None:
        return None
    try:
        payload = json.loads(conditions_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or len(payload) != 1:
        return None
    section = next(iter(payload.values()))
    if not isinstance(section, dict):
        return None
    conditions = {
        name: definition
        for name, definition in section.items()
        if name != "content"
        and isinstance(name, str)
        and name.strip()
        and isinstance(definition, (list, dict))
    }
    return conditions or None


def build_dice_roll_handler():
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        required = {"count", "sides", "seed"}
        if not required.issubset(args) or not set(args) <= required | {"modifier"}:
            return tool_error(
                "count, sides, and seed are required; only modifier is optional"
            )
        count = _integer(args.get("count"), minimum=1, maximum=100)
        sides = _integer(args.get("sides"), minimum=2, maximum=1000)
        modifier = _integer(args.get("modifier", 0), minimum=-10000, maximum=10000)
        seed = _integer(args.get("seed"), minimum=0, maximum=_MAX_SEED)
        if count is None:
            return tool_error("count must be an integer from 1 to 100")
        if sides is None:
            return tool_error("sides must be an integer from 2 to 1000")
        if modifier is None:
            return tool_error("modifier must be an integer from -10000 to 10000")
        if seed is None:
            return tool_error(f"seed must be an integer from 0 to {_MAX_SEED}")
        rng = random.Random(seed)
        rolls = [rng.randint(1, sides) for _ in range(count)]
        subtotal = sum(rolls)
        return tool_result(
            {
                "success": True,
                "calculation": "dice_roll",
                "notation": f"{count}d{sides}{modifier:+d}" if modifier else f"{count}d{sides}",
                "seed": seed,
                "count": count,
                "sides": sides,
                "modifier": modifier,
                "rolls": rolls,
                "subtotal": subtotal,
                "total": subtotal + modifier,
            }
        )

    return handle


def build_skill_check_handler():
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        required = {"modifier", "difficulty_class", "seed"}
        if not required.issubset(args) or not set(args) <= required | {"mode"}:
            return tool_error(
                "modifier, difficulty_class, and seed are required; only mode is optional"
            )
        modifier = _integer(args.get("modifier"), minimum=-30, maximum=30)
        difficulty_class = _integer(
            args.get("difficulty_class"), minimum=0, maximum=50
        )
        seed = _integer(args.get("seed"), minimum=0, maximum=_MAX_SEED)
        mode = args.get("mode", "normal")
        if modifier is None:
            return tool_error("modifier must be an integer from -30 to 30")
        if difficulty_class is None:
            return tool_error("difficulty_class must be an integer from 0 to 50")
        if seed is None:
            return tool_error(f"seed must be an integer from 0 to {_MAX_SEED}")
        if mode not in {"normal", "advantage", "disadvantage"}:
            return tool_error("mode must be normal, advantage, or disadvantage")
        rng = random.Random(seed)
        natural_rolls = [rng.randint(1, 20) for _ in range(1 if mode == "normal" else 2)]
        if mode == "advantage":
            kept = max(natural_rolls)
        elif mode == "disadvantage":
            kept = min(natural_rolls)
        else:
            kept = natural_rolls[0]
        total = kept + modifier
        return tool_result(
            {
                "success": True,
                "calculation": "rpg_skill_check",
                "seed": seed,
                "mode": mode,
                "natural_rolls": natural_rolls,
                "kept_roll": kept,
                "modifier": modifier,
                "total": total,
                "difficulty_class": difficulty_class,
                "check_succeeds": total >= difficulty_class,
                "natural_d20_automatic": False,
            }
        )

    return handle


def build_oracle_handler():
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        required = {"likelihood", "chaos_factor", "seed"}
        if set(args) != required:
            return tool_error("likelihood, chaos_factor, and seed are required")
        likelihood = args.get("likelihood")
        chaos_factor = _integer(args.get("chaos_factor"), minimum=1, maximum=9)
        seed = _integer(args.get("seed"), minimum=0, maximum=_MAX_SEED)
        if likelihood not in _ORACLE_YES_CHANCES:
            return tool_error(
                "likelihood must be one of: " + ", ".join(_ORACLE_YES_CHANCES)
            )
        if chaos_factor is None:
            return tool_error("chaos_factor must be an integer from 1 to 9")
        if seed is None:
            return tool_error(f"seed must be an integer from 0 to {_MAX_SEED}")

        yes_chance = _ORACLE_YES_CHANCES[likelihood]
        roll = random.Random(seed).randint(1, 100)
        yes = roll <= yes_chance
        exceptional_band = chaos_factor
        if yes and roll <= exceptional_band:
            outcome = "exceptional_yes"
        elif not yes and roll > 100 - exceptional_band:
            outcome = "exceptional_no"
        else:
            outcome = "yes" if yes else "no"
        return tool_result(
            {
                "success": True,
                "calculation": "rpg_oracle",
                "seed": seed,
                "likelihood": likelihood,
                "yes_chance_percent": yes_chance,
                "chaos_factor": chaos_factor,
                "exceptional_band_percent": exceptional_band,
                "roll": roll,
                "yes": yes,
                "outcome": outcome,
            }
        )

    return handle


def build_random_table_handler():
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        if set(args) != {"entries", "seed"}:
            return tool_error("entries and seed are required")
        entries = args.get("entries")
        seed = _integer(args.get("seed"), minimum=0, maximum=_MAX_SEED)
        if not isinstance(entries, list) or not 1 <= len(entries) <= 100:
            return tool_error("entries must be an array containing 1 to 100 strings")
        if any(
            not isinstance(entry, str)
            or not entry.strip()
            or len(entry) > 200
            for entry in entries
        ):
            return tool_error("each entry must be a non-blank string of at most 200 characters")
        if seed is None:
            return tool_error(f"seed must be an integer from 0 to {_MAX_SEED}")

        normalized_entries = [entry.strip() for entry in entries]
        roll = random.Random(seed).randint(1, len(normalized_entries))
        return tool_result(
            {
                "success": True,
                "calculation": "rpg_random_table",
                "seed": seed,
                "notation": f"1d{len(normalized_entries)}",
                "entry_count": len(normalized_entries),
                "roll": roll,
                "selected_entry": normalized_entries[roll - 1],
            }
        )

    return handle


def build_condition_lookup_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        if set(args) != {"condition"}:
            return tool_error("condition is required")
        query = args.get("condition")
        if not isinstance(query, str) or not query.strip() or len(query) > 60:
            return tool_error("condition must be a non-blank string of at most 60 characters")
        conditions = _load_conditions(ctx)
        if conditions is None:
            return tool_error(
                "Configure volmarr-rpg srd_root as an absolute path to the official SRD checkout."
            )
        by_normalized_name = {name.casefold(): name for name in conditions}
        canonical_name = by_normalized_name.get(query.strip().casefold())
        if canonical_name is None:
            return tool_error("condition was not found in the configured SRD checkout")
        definition = conditions[canonical_name]
        try:
            encoded_definition = json.dumps(definition, ensure_ascii=False)
        except (TypeError, ValueError):
            return tool_error("the configured SRD condition has an invalid structure")
        if len(encoded_definition.encode("utf-8")) > 16 * 1024:
            return tool_error("the configured SRD condition is too large")
        return tool_result(
            {
                "success": True,
                "calculation": "rpg_condition_lookup",
                "condition": canonical_name,
                "definition": definition,
                "source": {
                    "corpus": "System Reference Document 5.0",
                    "file": "json/12 conditions.json",
                    "license": "OGL-1.0a",
                },
            }
        )

    return handle


def register_tools(ctx) -> None:
    for name, schema, handler, emoji in (
        ("dice_roll", DICE_ROLL_SCHEMA, build_dice_roll_handler(), "🎲"),
        (
            "rpg_skill_check",
            RPG_SKILL_CHECK_SCHEMA,
            build_skill_check_handler(),
            "🛡️",
        ),
        ("rpg_oracle", RPG_ORACLE_SCHEMA, build_oracle_handler(), "🔮"),
        (
            "rpg_random_table",
            RPG_RANDOM_TABLE_SCHEMA,
            build_random_table_handler(),
            "📜",
        ),
        (
            "rpg_condition_lookup",
            RPG_CONDITION_LOOKUP_SCHEMA,
            build_condition_lookup_handler(ctx),
            "📖",
        ),
    ):
        ctx.register_tool(
            name=name,
            toolset="volmarr_rpg",
            schema=schema,
            handler=handler,
            description=schema["description"],
            emoji=emoji,
        )
