"""Bounded local tools for the official RuneTarot engine."""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from tools.registry import tool_error, tool_result


_MAX_OUTPUT_BYTES = 64 * 1024
_MAX_SEED = 2**31 - 1
_BASE_ENV = (
    "PATH",
    "HOME",
    "USERPROFILE",
    "SYSTEMROOT",
    "WINDIR",
    "TMPDIR",
    "TEMP",
    "LANG",
    "LC_ALL",
)
_RUNNER = Path(__file__).with_name("_runner.py").resolve()
_MULTI_CARD_SPREADS = (
    "three_card",
    "past_life",
    "opening_of_the_key",
    "relationship",
    "celtic_cross",
    "tree_of_life",
    "zodiac_wheel",
)

TAROT_DRAW_SCHEMA = {
    "name": "tarot_draw",
    "description": (
        "Draw one reproducible card from the official 78-card RuneTarot deck and return "
        "its built-in Golden Dawn correspondences. This local tool does not ask a question, "
        "call an AI provider, save reading history, or synthesize an interpretation."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "seed": {
                "type": "integer",
                "minimum": 0,
                "maximum": _MAX_SEED,
                "description": "Required reproducibility seed.",
            },
            "allow_reversals": {
                "type": "boolean",
                "description": "Whether the official deck may orient the card reversed.",
                "default": True,
            },
        },
        "required": ["seed"],
        "additionalProperties": False,
    },
}

TAROT_SPREAD_SCHEMA = {
    "name": "tarot_spread",
    "description": (
        "Draw one reproducible official RuneTarot multi-card spread and return each card "
        "with its official position and Golden Dawn correspondences. The tool does not "
        "accept a question, synthesize an interpretation, call AI, or save history."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "spread": {
                "type": "string",
                "enum": list(_MULTI_CARD_SPREADS),
            },
            "seed": {"type": "integer", "minimum": 0, "maximum": _MAX_SEED},
            "allow_reversals": {"type": "boolean", "default": True},
        },
        "required": ["spread", "seed"],
        "additionalProperties": False,
    },
}


def _configured_file(value: Any, *, executable: bool = False) -> Path | None:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        return None
    configured = value.strip()
    candidate = Path(configured).expanduser()
    if not candidate.is_absolute() and candidate.parent == Path("."):
        found = shutil.which(configured) if executable else None
        if found is None:
            return None
        candidate = Path(found)
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    if not resolved.is_file() or (executable and not os.access(resolved, os.X_OK)):
        return None
    return resolved


def _configured_engine_root(value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        return None
    candidate = Path(value.strip()).expanduser()
    if not candidate.is_absolute():
        return None
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    if not resolved.is_dir():
        return None
    if not (resolved / "src" / "deck.py").is_file() or not (resolved / "data").is_dir():
        return None
    return resolved


def _runtime(ctx) -> tuple[Path, Path] | None:
    engine_root = _configured_engine_root(ctx.get_config("engine_root", ""))
    python_value = ctx.get_config("python_path", "")
    python = _configured_file(python_value or sys.executable, executable=True)
    if engine_root is None or python is None or not _RUNNER.is_file():
        return None
    return python, engine_root


def _timeout(ctx) -> float:
    try:
        value = float(ctx.get_config("timeout_seconds", 10))
    except (TypeError, ValueError):
        value = 10.0
    if not math.isfinite(value):
        value = 10.0
    return min(30.0, max(1.0, value))


def _child_env() -> dict[str, str]:
    env = {key: os.environ[key] for key in _BASE_ENV if key in os.environ}
    env.update({"NO_COLOR": "1", "PYTHONUTF8": "1", "PYTHONNOUSERSITE": "1"})
    return env


def _seed(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if not 0 <= value <= _MAX_SEED:
        return None
    return value


def _run_draw(
    ctx,
    *,
    seed: int,
    allow_reversals: bool,
    spread: str | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    runtime = _runtime(ctx)
    if runtime is None:
        return None, (
            "Configure volmarr-tarot engine_root and a Python interpreter with "
            "the RuneTarotEngine deck dependencies installed."
        )
    python, engine_root = runtime
    try:
        command = [
                str(python),
                "-I",
                str(_RUNNER),
                str(engine_root),
                str(seed),
                "1" if allow_reversals else "0",
            ]
        if spread is not None:
            command.append(spread)
        completed = subprocess.run(
            command,
            env=_child_env(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_timeout(ctx),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None, "The local RuneTarot draw timed out."
    except OSError:
        return None, "The local RuneTarot engine could not be started."

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    if (
        len(stdout.encode("utf-8", errors="replace")) > _MAX_OUTPUT_BYTES
        or len(stderr.encode("utf-8", errors="replace")) > _MAX_OUTPUT_BYTES
    ):
        return None, "The local RuneTarot engine returned an oversized response."
    if completed.returncode != 0:
        return None, "The local RuneTarot engine could not complete the draw."
    try:
        card = json.loads(stdout)
    except (TypeError, json.JSONDecodeError):
        return None, "The local RuneTarot engine returned an invalid response."
    if not isinstance(card, dict):
        return None, "The local RuneTarot engine returned an invalid response."
    if spread is None:
        if not card.get("card_id") or not card.get("name"):
            return None, "The local RuneTarot engine returned an invalid card."
    elif (
        card.get("key") != spread
        or not isinstance(card.get("card_count"), int)
        or not isinstance(card.get("cards"), list)
        or len(card["cards"]) != card["card_count"]
    ):
        return None, "The local RuneTarot engine returned an invalid spread."
    return card, None


def build_draw_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        if not set(args) <= {"seed", "allow_reversals"} or "seed" not in args:
            return tool_error("seed is required; only allow_reversals is optional")
        seed = _seed(args.get("seed"))
        if seed is None:
            return tool_error(f"seed must be an integer from 0 to {_MAX_SEED}")
        allow_reversals = args.get("allow_reversals", True)
        if not isinstance(allow_reversals, bool):
            return tool_error("allow_reversals must be true or false")
        card, error = _run_draw(
            ctx,
            seed=seed,
            allow_reversals=allow_reversals,
        )
        if error is not None:
            return tool_error(error)
        return tool_result(
            {
                "success": True,
                "engine": "hrabanazviking/RuneTarotEngine",
                "engine_surface": "development/src/deck.py",
                "calculation": "single_card_draw",
                "seed": seed,
                "reversals_enabled": allow_reversals,
                "interpretation_included": False,
                "card": card,
            }
        )

    return handle


def build_spread_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        required = {"spread", "seed"}
        if not required.issubset(args) or not set(args) <= required | {"allow_reversals"}:
            return tool_error(
                "spread and seed are required; only allow_reversals is optional"
            )
        spread = args.get("spread")
        if spread not in _MULTI_CARD_SPREADS:
            return tool_error("spread must be one of the supported official multi-card layouts")
        seed = _seed(args.get("seed"))
        if seed is None:
            return tool_error(f"seed must be an integer from 0 to {_MAX_SEED}")
        allow_reversals = args.get("allow_reversals", True)
        if not isinstance(allow_reversals, bool):
            return tool_error("allow_reversals must be true or false")
        result, error = _run_draw(
            ctx,
            seed=seed,
            allow_reversals=allow_reversals,
            spread=spread,
        )
        if error is not None:
            return tool_error(error)
        return tool_result(
            {
                "success": True,
                "engine": "hrabanazviking/RuneTarotEngine",
                "engine_surface": (
                    "development/src/deck.py+src/spreads.py+src/golden_dawn.py"
                ),
                "calculation": "multi_card_spread",
                "seed": seed,
                "reversals_enabled": allow_reversals,
                "interpretation_included": False,
                "spread": result,
            }
        )

    return handle


def register_tools(ctx) -> None:
    for name, schema, handler, emoji in (
        ("tarot_draw", TAROT_DRAW_SCHEMA, build_draw_handler(ctx), "🃏"),
        ("tarot_spread", TAROT_SPREAD_SCHEMA, build_spread_handler(ctx), "🔮"),
    ):
        ctx.register_tool(
            name=name,
            toolset="volmarr_tarot",
            schema=schema,
            handler=handler,
            check_fn=lambda: _runtime(ctx) is not None,
            description=schema["description"],
            emoji=emoji,
        )
