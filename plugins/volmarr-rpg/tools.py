"""Bounded deterministic tabletop mechanics."""

from __future__ import annotations

import random
from typing import Any

from tools.registry import tool_error, tool_result


_MAX_SEED = 2**31 - 1

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


def _integer(value: Any, *, minimum: int, maximum: int) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if minimum <= value <= maximum else None


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


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="dice_roll",
        toolset="volmarr_rpg",
        schema=DICE_ROLL_SCHEMA,
        handler=build_dice_roll_handler(),
        description=DICE_ROLL_SCHEMA["description"],
        emoji="🎲",
    )
