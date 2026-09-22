"""Bounded local tools for the official Seiðr Engine."""

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
_FORMS = ("fornyrthislag", "ljodhattr", "drottkvaett", "malahattr")
_DOMAINS = (
    "asgard",
    "vanaheim",
    "alfheim",
    "midgard",
    "jotunheim",
    "svartalfheim",
    "niflheim",
    "muspelheim",
    "helheim",
)
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

SEIDR_COMPOSE_SCHEMA = {
    "name": "seidr_compose",
    "description": (
        "Compose reproducible rule-based Old Norse-inspired verse with the official local "
        "Seiðr Engine. Returns verse and metrical metadata without any AI generation."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "form": {"type": "string", "enum": list(_FORMS)},
            "domain": {"type": "string", "enum": list(_DOMAINS)},
            "stanzas": {"type": "integer", "minimum": 1, "maximum": 4},
            "use_kennings": {"type": "boolean", "default": True},
            "seed": {"type": "integer", "minimum": 1, "maximum": _MAX_SEED},
        },
        "required": ["form", "seed"],
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
    required = ("seidr/poet.py", "seidr/lexicon.py", "seidr/forms.py")
    if not resolved.is_dir() or not all((resolved / item).is_file() for item in required):
        return None
    return resolved


def _runtime(ctx) -> tuple[Path, Path] | None:
    root = _configured_engine_root(ctx.get_config("engine_root", ""))
    python_value = ctx.get_config("python_path", "")
    python = _configured_file(python_value or sys.executable, executable=True)
    if root is None or python is None or not _RUNNER.is_file():
        return None
    return python, root


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
    env.update(
        {
            "NO_COLOR": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUTF8": "1",
            "PYTHONNOUSERSITE": "1",
        }
    )
    return env


def _integer(value: Any, *, minimum: int, maximum: int) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if minimum <= value <= maximum else None


def _run_compose(
    ctx,
    *,
    form: str,
    domain: str | None,
    stanzas: int,
    use_kennings: bool,
    seed: int,
) -> tuple[dict[str, Any] | None, str | None]:
    runtime = _runtime(ctx)
    if runtime is None:
        return None, "Configure volmarr-seidr engine_root and a Python interpreter."
    python, engine_root = runtime
    try:
        completed = subprocess.run(
            [
                str(python),
                "-B",
                "-P",
                "-s",
                str(_RUNNER),
                str(engine_root),
                form,
                domain or "-",
                str(stanzas),
                "1" if use_kennings else "0",
                str(seed),
            ],
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
        return None, "The local Seiðr composition timed out."
    except OSError:
        return None, "The local Seiðr Engine could not be started."
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    if (
        len(stdout.encode("utf-8", errors="replace")) > _MAX_OUTPUT_BYTES
        or len(stderr.encode("utf-8", errors="replace")) > _MAX_OUTPUT_BYTES
    ):
        return None, "The local Seiðr Engine returned an oversized response."
    if completed.returncode != 0:
        return None, "The local Seiðr Engine could not compose the verse."
    try:
        poem = json.loads(stdout)
    except (TypeError, json.JSONDecodeError):
        return None, "The local Seiðr Engine returned an invalid response."
    if (
        not isinstance(poem, dict)
        or poem.get("form") != form
        or poem.get("stanza_count") != stanzas
        or not isinstance(poem.get("verse"), str)
        or not isinstance(poem.get("stanzas"), list)
        or len(poem["stanzas"]) != stanzas
    ):
        return None, "The local Seiðr Engine returned an invalid poem."
    return poem, None


def build_compose_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        allowed = {"form", "domain", "stanzas", "use_kennings", "seed"}
        if not {"form", "seed"}.issubset(args) or not set(args) <= allowed:
            return tool_error("form and seed are required; unsupported fields are rejected")
        form = args.get("form")
        domain = args.get("domain")
        if form not in _FORMS:
            return tool_error("form must be one of the four official meters")
        if domain is not None and domain not in _DOMAINS:
            return tool_error("domain must be one of the Nine Worlds")
        stanzas = _integer(args.get("stanzas", 1), minimum=1, maximum=4)
        seed = _integer(args.get("seed"), minimum=1, maximum=_MAX_SEED)
        use_kennings = args.get("use_kennings", True)
        if stanzas is None:
            return tool_error("stanzas must be an integer from 1 to 4")
        if seed is None:
            return tool_error(f"seed must be an integer from 1 to {_MAX_SEED}")
        if not isinstance(use_kennings, bool):
            return tool_error("use_kennings must be true or false")
        poem, error = _run_compose(
            ctx,
            form=form,
            domain=domain,
            stanzas=stanzas,
            use_kennings=use_kennings,
            seed=seed,
        )
        if error is not None:
            return tool_error(error)
        return tool_result(
            {
                "success": True,
                "engine": "hrabanazviking/seidr-engine",
                "calculation": "old_norse_poetry",
                "ai_generated": False,
                "seed": seed,
                "poem": poem,
            }
        )

    return handle


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="seidr_compose",
        toolset="volmarr_seidr",
        schema=SEIDR_COMPOSE_SCHEMA,
        handler=build_compose_handler(ctx),
        check_fn=lambda: _runtime(ctx) is not None,
        description=SEIDR_COMPOSE_SCHEMA["description"],
        emoji="ᛋ",
    )
