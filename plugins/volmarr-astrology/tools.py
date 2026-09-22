"""Bounded subprocess tools for the official AI Agent Astrology Engine."""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

from tools.registry import tool_error, tool_result


_MAX_OUTPUT_BYTES = 64 * 1024
_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
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

ASTROLOGY_LUNAR_SCHEMA = {
    "name": "astrology_lunar",
    "description": (
        "Calculate the current lunar phase, illumination, void-of-course status, "
        "next lunations, and Moon aspects locally with the configured official "
        "Astrology Engine. Returns calculations only, not an LLM interpretation."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
}

ASTROLOGY_PLANETARY_HOURS_SCHEMA = {
    "name": "astrology_planetary_hours",
    "description": (
        "Calculate the Chaldean planetary-hour rulers for one explicit date and "
        "latitude/longitude with the configured local Astrology Engine. Coordinates "
        "are required so the engine never performs online geocoding."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "date": {
                "type": "string",
                "description": "Calendar date in YYYY-MM-DD form.",
                "pattern": r"^\d{4}-\d{2}-\d{2}$",
            },
            "latitude": {
                "type": "number",
                "exclusiveMinimum": -90,
                "exclusiveMaximum": 90,
            },
            "longitude": {
                "type": "number",
                "minimum": -180,
                "maximum": 180,
            },
        },
        "required": ["date", "latitude", "longitude"],
        "additionalProperties": False,
    },
}

ASTROLOGY_NATAL_SCHEMA = {
    "name": "astrology_natal",
    "description": (
        "Calculate a local natal chart from an explicit birth date and coordinates. "
        "Birth time is optional; when omitted, the engine marks houses and angles as "
        "approximate. The plugin does not geocode, create extra state, or interpret the chart."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "date": {
                "type": "string",
                "description": "Birth date in YYYY-MM-DD form.",
                "pattern": r"^\d{4}-\d{2}-\d{2}$",
            },
            "time": {
                "type": "string",
                "description": "Optional local birth time in 24-hour HH:MM form.",
                "pattern": r"^(?:[01]\d|2[0-3]):[0-5]\d$",
            },
            "latitude": {
                "type": "number",
                "exclusiveMinimum": -90,
                "exclusiveMaximum": 90,
            },
            "longitude": {
                "type": "number",
                "minimum": -180,
                "maximum": 180,
            },
        },
        "required": ["date", "latitude", "longitude"],
        "additionalProperties": False,
    },
}

ASTROLOGY_TRANSIT_SCHEMA = {
    "name": "astrology_transit",
    "description": (
        "Calculate an explicit-date transit chart against a natal chart locally. "
        "Coordinates are required and the sky date may not default to now. Natal and "
        "sky times are optional; the tool calculates but does not interpret."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "natal_date": {
                "type": "string",
                "pattern": r"^\d{4}-\d{2}-\d{2}$",
            },
            "natal_time": {
                "type": "string",
                "pattern": r"^(?:[01]\d|2[0-3]):[0-5]\d$",
            },
            "transit_date": {
                "type": "string",
                "pattern": r"^\d{4}-\d{2}-\d{2}$",
            },
            "transit_time": {
                "type": "string",
                "description": "Optional explicit UTC sky time in HH:MM form.",
                "pattern": r"^(?:[01]\d|2[0-3]):[0-5]\d$",
            },
            "latitude": {
                "type": "number",
                "exclusiveMinimum": -90,
                "exclusiveMaximum": 90,
            },
            "longitude": {
                "type": "number",
                "minimum": -180,
                "maximum": 180,
            },
        },
        "required": ["natal_date", "transit_date", "latitude", "longitude"],
        "additionalProperties": False,
    },
}

ASTROLOGY_PREDICT_SCHEMA = {
    "name": "astrology_predict",
    "description": (
        "Calculate exact transit-to-natal events, stations, ingresses, and eclipses "
        "for an explicit window of at most 366 days using the local Astrology Engine. "
        "Uses the engine's documented planet sets and returns facts without interpretation."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "natal_date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
            "natal_time": {
                "type": "string",
                "pattern": r"^(?:[01]\d|2[0-3]):[0-5]\d$",
            },
            "start_date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
            "end_date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
            "latitude": {
                "type": "number",
                "exclusiveMinimum": -90,
                "exclusiveMaximum": 90,
            },
            "longitude": {"type": "number", "minimum": -180, "maximum": 180},
        },
        "required": [
            "natal_date",
            "start_date",
            "end_date",
            "latitude",
            "longitude",
        ],
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
    if not resolved.is_file():
        return None
    if executable and not os.access(resolved, os.X_OK):
        return None
    return resolved


def _runtime(ctx) -> tuple[Path, Path] | None:
    engine = _configured_file(ctx.get_config("engine_path", ""))
    python_value = ctx.get_config("python_path", "")
    python = _configured_file(python_value or sys.executable, executable=True)
    if engine is None or engine.suffix.lower() != ".py" or python is None:
        return None
    return python, engine


def _timeout(ctx) -> float:
    try:
        value = float(ctx.get_config("timeout_seconds", 20))
    except (TypeError, ValueError):
        value = 20.0
    if not math.isfinite(value):
        value = 20.0
    return min(60.0, max(1.0, value))


def _child_env() -> dict[str, str]:
    env = {key: os.environ[key] for key in _BASE_ENV if key in os.environ}
    env.update({"NO_COLOR": "1", "PYTHONUTF8": "1"})
    return env


def _run_calculation(
    ctx,
    argv: list[str],
    *,
    zero_exit_failure_markers: tuple[str, ...] = (),
) -> tuple[str | None, str | None]:
    runtime = _runtime(ctx)
    if runtime is None:
        return None, (
            "Configure volmarr-astrology engine_path and a Python interpreter "
            "with pyswisseph installed."
        )
    python, engine = runtime
    timeout = _timeout(ctx)
    try:
        completed = subprocess.run(
            [str(python), str(engine), *argv],
            env=_child_env(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None, "The local astrology calculation timed out."
    except OSError:
        return None, "The local Astrology Engine could not be started."

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    if (
        len(stdout.encode("utf-8", errors="replace")) > _MAX_OUTPUT_BYTES
        or len(stderr.encode("utf-8", errors="replace")) > _MAX_OUTPUT_BYTES
    ):
        return None, "The local Astrology Engine returned an oversized response."
    if completed.returncode != 0:
        return None, "The local Astrology Engine failed to calculate lunar state."
    report = _ANSI_RE.sub("", stdout).strip()
    combined = f"{report}\n{stderr}".lower()
    if "pyswisseph required" in combined:
        return None, (
            "The configured Astrology Engine Python environment does not have "
            "pyswisseph installed."
        )
    if any(marker in combined for marker in zero_exit_failure_markers):
        return None, "The local Astrology Engine could not complete the calculation."
    if not report:
        return None, "The local Astrology Engine returned no calculation output."
    return report, None


def _run_lunar(ctx) -> tuple[str | None, str | None]:
    return _run_calculation(ctx, ["lunar"])


def _number(value: Any, *, minimum: float, maximum: float) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(parsed) or not minimum <= parsed <= maximum:
        return None
    return parsed


def _coordinate(value: float) -> str:
    return format(value, ".12g")


def _calendar_date(value: Any) -> str | None:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _clock_time(value: Any) -> str | None:
    if not isinstance(value, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
        return None
    return value


def build_lunar_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        if args:
            return tool_error("astrology_lunar does not accept arguments")
        report, error = _run_lunar(ctx)
        if error is not None:
            return tool_error(error)
        return tool_result(
            {
                "success": True,
                "engine": "hrabanazviking/astrology-engine",
                "calculation": "lunar",
                "interpretation_included": False,
                "report": report,
            }
        )

    return handle


def build_planetary_hours_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        if set(args) != {"date", "latitude", "longitude"}:
            return tool_error(
                "date, latitude, and longitude are required; no other fields are accepted"
            )
        raw_date = _calendar_date(args.get("date"))
        if raw_date is None:
            return tool_error("date must be a real calendar date in YYYY-MM-DD form")
        latitude = _number(args.get("latitude"), minimum=-90.0, maximum=90.0)
        longitude = _number(args.get("longitude"), minimum=-180.0, maximum=180.0)
        if latitude is None or not -90.0 < latitude < 90.0:
            return tool_error("latitude must be a finite number strictly between -90 and 90")
        if longitude is None:
            return tool_error("longitude must be a finite number from -180 to 180")
        report, error = _run_calculation(
            ctx,
            [
                "planet-hours",
                "--date",
                raw_date,
                "--lat",
                _coordinate(latitude),
                "--lon",
                _coordinate(longitude),
            ],
            zero_exit_failure_markers=("error calculating planetary hours:",),
        )
        if error is not None:
            return tool_error(error)
        return tool_result(
            {
                "success": True,
                "engine": "hrabanazviking/astrology-engine",
                "calculation": "planetary_hours",
                "interpretation_included": False,
                "date": raw_date,
                "latitude": latitude,
                "longitude": longitude,
                "report": report,
            }
        )

    return handle


def build_natal_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        allowed = {"date", "time", "latitude", "longitude"}
        if not {"date", "latitude", "longitude"}.issubset(args) or not set(args) <= allowed:
            return tool_error(
                "date, latitude, and longitude are required; only optional time is accepted"
            )
        raw_date = _calendar_date(args.get("date"))
        if raw_date is None:
            return tool_error("date must be a real calendar date in YYYY-MM-DD form")
        raw_time = args.get("time")
        if raw_time is not None:
            raw_time = _clock_time(raw_time)
            if raw_time is None:
                return tool_error("time must use 24-hour HH:MM form")
        latitude = _number(args.get("latitude"), minimum=-90.0, maximum=90.0)
        longitude = _number(args.get("longitude"), minimum=-180.0, maximum=180.0)
        if latitude is None or not -90.0 < latitude < 90.0:
            return tool_error("latitude must be a finite number strictly between -90 and 90")
        if longitude is None:
            return tool_error("longitude must be a finite number from -180 to 180")
        argv = [
            "natal",
            "--date",
            raw_date,
            "--lat",
            _coordinate(latitude),
            "--lon",
            _coordinate(longitude),
        ]
        if raw_time is not None:
            argv.extend(["--time", raw_time])
        report, error = _run_calculation(ctx, argv)
        if error is not None:
            return tool_error(error)
        return tool_result(
            {
                "success": True,
                "engine": "hrabanazviking/astrology-engine",
                "calculation": "natal",
                "interpretation_included": False,
                "date": raw_date,
                "time_known": raw_time is not None,
                "latitude": latitude,
                "longitude": longitude,
                "report": report,
            }
        )

    return handle


def build_transit_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        required = {"natal_date", "transit_date", "latitude", "longitude"}
        allowed = required | {"natal_time", "transit_time"}
        if not required.issubset(args) or not set(args) <= allowed:
            return tool_error(
                "natal_date, transit_date, latitude, and longitude are required; "
                "only natal_time and transit_time are optional"
            )
        natal_date = _calendar_date(args.get("natal_date"))
        transit_date = _calendar_date(args.get("transit_date"))
        if natal_date is None or transit_date is None:
            return tool_error("natal_date and transit_date must be real YYYY-MM-DD dates")
        natal_time = args.get("natal_time")
        transit_time = args.get("transit_time")
        if natal_time is not None:
            natal_time = _clock_time(natal_time)
            if natal_time is None:
                return tool_error("natal_time must use 24-hour HH:MM form")
        if transit_time is not None:
            transit_time = _clock_time(transit_time)
            if transit_time is None:
                return tool_error("transit_time must use 24-hour HH:MM form")
        latitude = _number(args.get("latitude"), minimum=-90.0, maximum=90.0)
        longitude = _number(args.get("longitude"), minimum=-180.0, maximum=180.0)
        if latitude is None or not -90.0 < latitude < 90.0:
            return tool_error("latitude must be a finite number strictly between -90 and 90")
        if longitude is None:
            return tool_error("longitude must be a finite number from -180 to 180")
        argv = [
            "transit",
            "--date",
            natal_date,
            "--transit-date",
            transit_date,
            "--lat",
            _coordinate(latitude),
            "--lon",
            _coordinate(longitude),
        ]
        if natal_time is not None:
            argv.extend(["--time", natal_time])
        if transit_time is not None:
            argv.extend(["--transit-time", transit_time])
        report, error = _run_calculation(ctx, argv)
        if error is not None:
            return tool_error(error)
        return tool_result(
            {
                "success": True,
                "engine": "hrabanazviking/astrology-engine",
                "calculation": "transit",
                "interpretation_included": False,
                "natal_date": natal_date,
                "natal_time_known": natal_time is not None,
                "transit_date": transit_date,
                "transit_time_explicit": transit_time is not None,
                "latitude": latitude,
                "longitude": longitude,
                "report": report,
            }
        )

    return handle


def build_predict_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        required = {
            "natal_date",
            "start_date",
            "end_date",
            "latitude",
            "longitude",
        }
        allowed = required | {"natal_time"}
        if not required.issubset(args) or not set(args) <= allowed:
            return tool_error(
                "natal_date, start_date, end_date, latitude, and longitude are required; "
                "only natal_time is optional"
            )
        natal_date = _calendar_date(args.get("natal_date"))
        start_date = _calendar_date(args.get("start_date"))
        end_date = _calendar_date(args.get("end_date"))
        if natal_date is None or start_date is None or end_date is None:
            return tool_error("all dates must be real calendar dates in YYYY-MM-DD form")
        window_days = (date.fromisoformat(end_date) - date.fromisoformat(start_date)).days
        if not 0 <= window_days <= 366:
            return tool_error("prediction window must be forward-moving and no longer than 366 days")
        natal_time = args.get("natal_time")
        if natal_time is not None:
            natal_time = _clock_time(natal_time)
            if natal_time is None:
                return tool_error("natal_time must use 24-hour HH:MM form")
        latitude = _number(args.get("latitude"), minimum=-90.0, maximum=90.0)
        longitude = _number(args.get("longitude"), minimum=-180.0, maximum=180.0)
        if latitude is None or not -90.0 < latitude < 90.0:
            return tool_error("latitude must be a finite number strictly between -90 and 90")
        if longitude is None:
            return tool_error("longitude must be a finite number from -180 to 180")
        argv = [
            "predict",
            "--date",
            natal_date,
            "--start",
            start_date,
            "--end",
            end_date,
            "--lat",
            _coordinate(latitude),
            "--lon",
            _coordinate(longitude),
        ]
        if natal_time is not None:
            argv.extend(["--time", natal_time])
        report, error = _run_calculation(ctx, argv)
        if error is not None:
            return tool_error(error)
        return tool_result(
            {
                "success": True,
                "engine": "hrabanazviking/astrology-engine",
                "calculation": "prediction",
                "interpretation_included": False,
                "natal_date": natal_date,
                "natal_time_known": natal_time is not None,
                "start_date": start_date,
                "end_date": end_date,
                "window_days": window_days,
                "latitude": latitude,
                "longitude": longitude,
                "report": report,
            }
        )

    return handle


def register_tools(ctx) -> None:
    for name, schema, handler, emoji in (
        (
            "astrology_lunar",
            ASTROLOGY_LUNAR_SCHEMA,
            build_lunar_handler(ctx),
            "🌙",
        ),
        (
            "astrology_planetary_hours",
            ASTROLOGY_PLANETARY_HOURS_SCHEMA,
            build_planetary_hours_handler(ctx),
            "🕰️",
        ),
        (
            "astrology_natal",
            ASTROLOGY_NATAL_SCHEMA,
            build_natal_handler(ctx),
            "✨",
        ),
        (
            "astrology_transit",
            ASTROLOGY_TRANSIT_SCHEMA,
            build_transit_handler(ctx),
            "🪐",
        ),
        (
            "astrology_predict",
            ASTROLOGY_PREDICT_SCHEMA,
            build_predict_handler(ctx),
            "🔭",
        ),
    ):
        ctx.register_tool(
            name=name,
            toolset="volmarr_astrology",
            schema=schema,
            handler=handler,
            check_fn=lambda: _runtime(ctx) is not None,
            description=schema["description"],
            emoji=emoji,
        )
