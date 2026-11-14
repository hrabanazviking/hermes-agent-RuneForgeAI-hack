"""Bounded subprocess tools for the official AI Agent Astrology Engine."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo
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


ENGINE_REPO = "hrabanazviking/astrology-engine"
ENGINE_PIN = "bb4ede4fbb326d21df34a5ca0ca6e343f4f49fbe"
ENGINE_VERSION = "4.0.0"
EPHEMERIS_PROVENANCE = (
    "Swiss Ephemeris via pyswisseph 2.10.3.2; when the optional Swiss "
    ".se1 data files are absent the engine falls back to its Moshier "
    "backend and says so in its own provenance block (E09-T3)"
)
# Pinned allowlist: the capability ids the engine's own `capabilities`
# output reported at the E.09 pin, re-measured in X.09 (28 ids).
# Dynamic discovery may only ever surface ids on this list (s.44.6).
CAPABILITY_ALLOWLIST = (
    "chart", "vedic", "vargas", "dashas", "panchanga",
    "relationship", "location", "western", "legacy",
    "advanced-jyotisha", "chinese-tibetan-other", "runic", "wheel",
    "solar-arc", "profection", "watch", "elect", "stars",
    "asteroids", "midpoints", "draconic", "dossier", "forecast",
    "mantras", "yogas", "shadbala", "ashtakavarga", "jaimini",
)
_AYANAMSAS = ("lahiri", "raman", "krishnamurti", "fagan-bradley")
_CACHE: dict[str, str] = {}
_CACHE_MAX = 128


def _iana_zone(value: Any):
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        return None
    try:
        return ZoneInfo(value.strip())
    except (KeyError, ValueError):
        return None


def _local_time_status(raw_date: str, raw_time: str, zone: ZoneInfo) -> str:
    """Classify a wall time in a zone: ok / fold / gap (stdlib only)."""
    naive = datetime.combine(
        date.fromisoformat(raw_date), time.fromisoformat(raw_time))

    def _roundtrips(fold: int) -> bool:
        aware = naive.replace(tzinfo=zone, fold=fold)
        back = aware.astimezone(timezone.utc).astimezone(zone)
        return back.replace(tzinfo=None) == naive

    if _roundtrips(0) and _roundtrips(1):
        off0 = naive.replace(tzinfo=zone, fold=0).utcoffset()
        off1 = naive.replace(tzinfo=zone, fold=1).utcoffset()
        return "fold" if off0 != off1 else "ok"
    return "gap"


def _timezone_arg(args: dict, key: str = "timezone"):
    """Return (name, zone, error); (None, None, None) when absent."""
    raw = args.get(key)
    if raw is None:
        return None, None, None
    zone = _iana_zone(raw)
    if zone is None:
        return None, None, f"{key} must be a valid IANA timezone name"
    return raw.strip(), zone, None


def _dst_error(raw_date, raw_time, zone, tz_name):
    if raw_time is None or zone is None:
        return None
    status = _local_time_status(raw_date, raw_time, zone)
    if status == "fold":
        return (f"local time {raw_time} on {raw_date} is ambiguous in "
                f"{tz_name} (DST fold); supply an unambiguous time")
    if status == "gap":
        return (f"local time {raw_time} on {raw_date} does not exist in "
                f"{tz_name} (DST gap); supply a valid local time")
    return None


def _cache_key(argv: list) -> str:
    canonical = json.dumps(
        {"engine_pin": ENGINE_PIN, "argv": list(argv)}, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

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
            "timezone": {"type": "string", "description": "Optional explicit IANA timezone; with a time, DST fold/gap local times are rejected."},
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
            "timezone": {"type": "string", "description": "Optional explicit IANA timezone; with a time, DST fold/gap local times are rejected."},
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
            "timezone": {"type": "string", "description": "Optional explicit IANA timezone; with a time, DST fold/gap local times are rejected."},
        },
        "required": [
            "natal_date",
            "start_date",
            "end_date",
            "latitude",
            "longitude",
            "natal_time",
        ],
        "additionalProperties": False,
    },
}

ASTROLOGY_SYNASTRY_SCHEMA = {
    "name": "astrology_synastry",
    "description": (
        "Calculate anonymous two-chart synastry cross-aspects locally from explicit dates "
        "and coordinates. Times are optional. Names, city geocoding, interpretation, and "
        "the engine's city-gated house-overlay mode are intentionally excluded."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "date_a": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
            "time_a": {
                "type": "string",
                "pattern": r"^(?:[01]\d|2[0-3]):[0-5]\d$",
            },
            "latitude_a": {
                "type": "number",
                "exclusiveMinimum": -90,
                "exclusiveMaximum": 90,
            },
            "longitude_a": {"type": "number", "minimum": -180, "maximum": 180},
            "date_b": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
            "time_b": {
                "type": "string",
                "pattern": r"^(?:[01]\d|2[0-3]):[0-5]\d$",
            },
            "latitude_b": {
                "type": "number",
                "exclusiveMinimum": -90,
                "exclusiveMaximum": 90,
            },
            "longitude_b": {"type": "number", "minimum": -180, "maximum": 180},
            "timezone_a": {"type": "string"},
            "timezone_b": {"type": "string"},
        },
        "required": [
            "date_a",
            "latitude_a",
            "longitude_a",
            "date_b",
            "latitude_b",
            "longitude_b",
        ],
        "additionalProperties": False,
    },
}

ASTROLOGY_ASTROCARTOGRAPHY_SCHEMA = {
    "name": "astrology_astrocartography",
    "description": (
        "Calculate local MC, IC, ASC, and DSC astrocartography lines from explicit birth "
        "coordinates. Optional query coordinates identify nearby lines. No city geocoding, "
        "identity label, persistence, or interpretation is added."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
            "time": {
                "type": "string",
                "pattern": r"^(?:[01]\d|2[0-3]):[0-5]\d$",
            },
            "latitude": {
                "type": "number",
                "exclusiveMinimum": -90,
                "exclusiveMaximum": 90,
            },
            "longitude": {"type": "number", "minimum": -180, "maximum": 180},
            "query_latitude": {
                "type": "number",
                "exclusiveMinimum": -90,
                "exclusiveMaximum": 90,
            },
            "query_longitude": {"type": "number", "minimum": -180, "maximum": 180},
            "timezone": {"type": "string", "description": "Optional explicit IANA timezone; with a time, DST fold/gap local times are rejected."},
        },
        "required": ["date", "time", "latitude", "longitude"],
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


def _run_cached(ctx, argv, **kwargs):
    """s.44.7: cache keyed on exact inputs + engine revision.

    The key is a sha256 over the pinned engine revision and the
    exact fixed argv; a hit replays the stored report byte-for-byte
    (deterministic replay) and never re-runs the engine. Chart
    contents live only in this process memory - never logged,
    never written to disk, never sent anywhere (s.44.7 privacy).
    """
    key = _cache_key(argv)
    if key in _CACHE:
        return _CACHE[key], None, key, True
    report, error = _run_calculation(ctx, argv, **kwargs)
    if error is None and report is not None:
        if len(_CACHE) >= _CACHE_MAX:
            _CACHE.clear()
        _CACHE[key] = report
    return report, error, key, False


def _envelope(calculation, report, key, hit, *, timezone_name=None,
              time_precision="exact"):
    return {
        "success": True,
        "engine": ENGINE_REPO,
        "engine_pin": ENGINE_PIN,
        "engine_version": ENGINE_VERSION,
        "calculation": calculation,
        "interpretation_included": False,
        "ephemeris": EPHEMERIS_PROVENANCE,
        "timezone": timezone_name,
        "time_precision": time_precision,
        "cache_key": key,
        "cache_hit": hit,
        "report": report,
    }

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
        allowed = {"date", "time", "latitude", "longitude", "timezone"}
        if not {"date", "latitude", "longitude"}.issubset(args) or not set(args) <= allowed:
            return tool_error(
                "date, latitude, and longitude are required; only optional time and timezone are accepted"
            )
        raw_date = _calendar_date(args.get("date"))
        if raw_date is None:
            return tool_error("date must be a real calendar date in YYYY-MM-DD form")
        raw_time = args.get("time")
        if raw_time is not None:
            raw_time = _clock_time(raw_time)
            if raw_time is None:
                return tool_error("time must use 24-hour HH:MM form")
        tz_name, zone, tz_error = _timezone_arg(args)
        if tz_error is not None:
            return tool_error(tz_error)
        dst = _dst_error(raw_date, raw_time, zone, tz_name)
        if dst is not None:
            return tool_error(dst)
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
        if tz_name is not None:
            argv.extend(["--timezone", tz_name])
        report, error = _run_calculation(ctx, argv)
        if error is not None:
            return tool_error(error)
        payload = {
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
        if tz_name is not None:
            payload["timezone"] = tz_name
        return tool_result(payload)

    return handle


def build_transit_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        required = {"natal_date", "transit_date", "latitude", "longitude"}
        allowed = required | {"natal_time", "transit_time", "timezone"}
        if not required.issubset(args) or not set(args) <= allowed:
            return tool_error(
                "natal_date, transit_date, latitude, and longitude are required; "
                "only natal_time, transit_time, and timezone are optional"
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
        tz_name, zone, tz_error = _timezone_arg(args)
        if tz_error is not None:
            return tool_error(tz_error)
        dst = _dst_error(natal_date, natal_time, zone, tz_name)
        if dst is not None:
            return tool_error(dst)
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
        if tz_name is not None:
            argv.extend(["--timezone", tz_name])
        report, error = _run_calculation(ctx, argv)
        if error is not None:
            return tool_error(error)
        payload = {
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
        if tz_name is not None:
            payload["timezone"] = tz_name
        return tool_result(payload)

    return handle


def build_predict_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        required = {
            "natal_date",
            "natal_time",
            "start_date",
            "end_date",
            "latitude",
            "longitude",
        }
        allowed = required | {"timezone"}
        if not required.issubset(args) or not set(args) <= allowed:
            return tool_error(
                "natal_date, natal_time, start_date, end_date, latitude, and "
                "longitude are required (the E.09 engine requires a known "
                "birth time for predict); only timezone is optional"
            )
        natal_date = _calendar_date(args.get("natal_date"))
        start_date = _calendar_date(args.get("start_date"))
        end_date = _calendar_date(args.get("end_date"))
        if natal_date is None or start_date is None or end_date is None:
            return tool_error("all dates must be real calendar dates in YYYY-MM-DD form")
        window_days = (date.fromisoformat(end_date) - date.fromisoformat(start_date)).days
        if not 0 <= window_days <= 366:
            return tool_error("prediction window must be forward-moving and no longer than 366 days")
        natal_time = _clock_time(args.get("natal_time"))
        if natal_time is None:
            return tool_error(
                "natal_time is required: predict requires a known birth "
                "time at the E.09 engine pin (E09-T2)")
        tz_name, zone, tz_error = _timezone_arg(args)
        if tz_error is not None:
            return tool_error(tz_error)
        dst = _dst_error(natal_date, natal_time, zone, tz_name)
        if dst is not None:
            return tool_error(dst)
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
        argv.extend(["--time", natal_time])
        if tz_name is not None:
            argv.extend(["--timezone", tz_name])
        report, error = _run_calculation(ctx, argv)
        if error is not None:
            return tool_error(error)
        payload = {
                "success": True,
                "engine": "hrabanazviking/astrology-engine",
                "calculation": "prediction",
                "interpretation_included": False,
                "natal_date": natal_date,
                "natal_time_known": True,
                "start_date": start_date,
                "end_date": end_date,
                "window_days": window_days,
                "latitude": latitude,
                "longitude": longitude,
                "report": report,
            }
        if tz_name is not None:
            payload["timezone"] = tz_name
        return tool_result(payload)

    return handle


def build_synastry_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        required = {
            "date_a",
            "latitude_a",
            "longitude_a",
            "date_b",
            "latitude_b",
            "longitude_b",
        }
        allowed = required | {"time_a", "time_b", "timezone_a", "timezone_b"}
        if not required.issubset(args) or not set(args) <= allowed:
            return tool_error(
                "both dates and coordinate pairs are required; only time_a, time_b, timezone_a, and timezone_b are optional"
            )
        date_a = _calendar_date(args.get("date_a"))
        date_b = _calendar_date(args.get("date_b"))
        if date_a is None or date_b is None:
            return tool_error("date_a and date_b must be real YYYY-MM-DD dates")
        time_a = args.get("time_a")
        time_b = args.get("time_b")
        if time_a is not None:
            time_a = _clock_time(time_a)
            if time_a is None:
                return tool_error("time_a must use 24-hour HH:MM form")
        if time_b is not None:
            time_b = _clock_time(time_b)
            if time_b is None:
                return tool_error("time_b must use 24-hour HH:MM form")
        tz_a, zone_a, tz_err_a = _timezone_arg(args, "timezone_a")
        if tz_err_a is not None:
            return tool_error(tz_err_a)
        tz_b, zone_b, tz_err_b = _timezone_arg(args, "timezone_b")
        if tz_err_b is not None:
            return tool_error(tz_err_b)
        dst = _dst_error(date_a, time_a, zone_a, tz_a)
        if dst is not None:
            return tool_error(dst)
        dst = _dst_error(date_b, time_b, zone_b, tz_b)
        if dst is not None:
            return tool_error(dst)
        latitude_a = _number(args.get("latitude_a"), minimum=-90.0, maximum=90.0)
        longitude_a = _number(args.get("longitude_a"), minimum=-180.0, maximum=180.0)
        latitude_b = _number(args.get("latitude_b"), minimum=-90.0, maximum=90.0)
        longitude_b = _number(args.get("longitude_b"), minimum=-180.0, maximum=180.0)
        if latitude_a is None or not -90.0 < latitude_a < 90.0:
            return tool_error("latitude_a must be finite and strictly between -90 and 90")
        if latitude_b is None or not -90.0 < latitude_b < 90.0:
            return tool_error("latitude_b must be finite and strictly between -90 and 90")
        if longitude_a is None or longitude_b is None:
            return tool_error("both longitudes must be finite numbers from -180 to 180")
        argv = [
            "synastry",
            "--date1",
            date_a,
            "--lat1",
            _coordinate(latitude_a),
            "--lon1",
            _coordinate(longitude_a),
            "--date2",
            date_b,
            "--lat2",
            _coordinate(latitude_b),
            "--lon2",
            _coordinate(longitude_b),
        ]
        if time_a is not None:
            argv.extend(["--time1", time_a])
        if time_b is not None:
            argv.extend(["--time2", time_b])
        if tz_a is not None:
            argv.extend(["--timezone1", tz_a])
        if tz_b is not None:
            argv.extend(["--timezone2", tz_b])
        report, error = _run_calculation(ctx, argv)
        if error is not None:
            return tool_error(error)
        return tool_result(
            {
                "success": True,
                "engine": "hrabanazviking/astrology-engine",
                "calculation": "synastry",
                "interpretation_included": False,
                "identities_included": False,
                "house_overlays_included": False,
                "date_a": date_a,
                "time_a_known": time_a is not None,
                "date_b": date_b,
                "time_b_known": time_b is not None,
                "report": report,
            }
        )

    return handle


def build_astrocartography_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        required = {"date", "time", "latitude", "longitude"}
        allowed = required | {"timezone", "query_latitude", "query_longitude"}
        if not required.issubset(args) or not set(args) <= allowed:
            return tool_error(
                "date, time, latitude, and longitude are required (the E.09 engine requires a known birth time for geoastrology); only timezone and a query pair are optional"
            )
        has_query_lat = "query_latitude" in args
        has_query_lon = "query_longitude" in args
        if has_query_lat != has_query_lon:
            return tool_error("query_latitude and query_longitude must be supplied together")
        raw_date = _calendar_date(args.get("date"))
        if raw_date is None:
            return tool_error("date must be a real calendar date in YYYY-MM-DD form")
        raw_time = _clock_time(args.get("time"))
        if raw_time is None:
            return tool_error(
                "time is required: geoastrology requires a known birth "
                "time at the E.09 engine pin (E09-T2)")
        tz_name, zone, tz_error = _timezone_arg(args)
        if tz_error is not None:
            return tool_error(tz_error)
        dst = _dst_error(raw_date, raw_time, zone, tz_name)
        if dst is not None:
            return tool_error(dst)
        latitude = _number(args.get("latitude"), minimum=-90.0, maximum=90.0)
        longitude = _number(args.get("longitude"), minimum=-180.0, maximum=180.0)
        if latitude is None or not -90.0 < latitude < 90.0:
            return tool_error("latitude must be a finite number strictly between -90 and 90")
        if longitude is None:
            return tool_error("longitude must be a finite number from -180 to 180")
        query_latitude = None
        query_longitude = None
        if has_query_lat:
            query_latitude = _number(
                args.get("query_latitude"), minimum=-90.0, maximum=90.0
            )
            query_longitude = _number(
                args.get("query_longitude"), minimum=-180.0, maximum=180.0
            )
            if query_latitude is None or not -90.0 < query_latitude < 90.0:
                return tool_error(
                    "query_latitude must be finite and strictly between -90 and 90"
                )
            if query_longitude is None:
                return tool_error("query_longitude must be finite from -180 to 180")
        argv = [
            "geoastrology",
            "--date",
            raw_date,
            "--lat",
            _coordinate(latitude),
            "--lon",
            _coordinate(longitude),
        ]
        argv.extend(["--time", raw_time])
        if tz_name is not None:
            argv.extend(["--timezone", tz_name])
        if query_latitude is not None and query_longitude is not None:
            argv.extend(
                [
                    "--query-lat",
                    _coordinate(query_latitude),
                    "--query-lon",
                    _coordinate(query_longitude),
                ]
            )
        report, error = _run_calculation(ctx, argv)
        if error is not None:
            return tool_error(error)
        return tool_result(
            {
                "success": True,
                "engine": "hrabanazviking/astrology-engine",
                "calculation": "astrocartography",
                "interpretation_included": False,
                "date": raw_date,
                "time_known": True,
                "query_included": query_latitude is not None,
                "latitude": latitude,
                "longitude": longitude,
                "report": report,
            }
        )

    return handle


def _structured_schema(name, description, *, query=False, ayanamsa=True):
    props = {
        "date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
        "time": {"type": "string", "pattern": r"^(?:[01]\d|2[0-3]):[0-5]\d$"},
        "latitude": {"type": "number", "exclusiveMinimum": -90, "exclusiveMaximum": 90},
        "longitude": {"type": "number", "minimum": -180, "maximum": 180},
        "timezone": {"type": "string", "description": "Explicit IANA timezone (required by the engine structured family); DST fold/gap local times are rejected."},
    }
    required = ["date", "time", "latitude", "longitude", "timezone"]
    if ayanamsa:
        props["ayanamsa"] = {"type": "string", "enum": list(_AYANAMSAS)}
    if query:
        props["query_latitude"] = {"type": "number", "exclusiveMinimum": -90, "exclusiveMaximum": 90}
        props["query_longitude"] = {"type": "number", "minimum": -180, "maximum": 180}
        required += ["query_latitude", "query_longitude"]
    return {"name": name, "description": description, "parameters": {
        "type": "object", "properties": props, "required": required,
        "additionalProperties": False}}


ASTROLOGY_VEDIC_SCHEMA = _structured_schema(
    "astrology_vedic",
    "Calculate a Vedic (Jyotisha) D1 chart with nakshatras via the local "
    "Astrology Engine structured family. Explicit IANA timezone and a "
    "known birth time are required; returns the engine's structured "
    "result with its provenance, never an interpretation.")
ASTROLOGY_VARGAS_SCHEMA = _structured_schema(
    "astrology_vargas",
    "Calculate the sixteen classical Vedic divisional charts (vargas) "
    "via the local Astrology Engine. Explicit timezone and known birth "
    "time required; structured engine output only.")
ASTROLOGY_DASHAS_SCHEMA = _structured_schema(
    "astrology_dashas",
    "Calculate the Vimshottari dasha chronology via the local Astrology "
    "Engine. Explicit timezone and known birth time required; the "
    "engine's chronology facts only, no interpretation.")
ASTROLOGY_PANCHANGA_SCHEMA = _structured_schema(
    "astrology_panchanga",
    "Calculate panchanga elements (tithi, nakshatra, yoga, karana) for "
    "an explicit instant via the local Astrology Engine. Explicit "
    "timezone required; structured engine output only.")
ASTROLOGY_RELOCATION_SCHEMA = _structured_schema(
    "astrology_relocation", query=True,
    description="Calculate fixed-instant relocation lines for a query "
    "location via the local Astrology Engine structured `location` "
    "command. Explicit timezone, known birth time, and an explicit "
    "query coordinate pair are required; no geocoding.")


def _legacy_schema(name, description):
    return {"name": name, "description": description, "parameters": {
        "type": "object",
        "properties": {
            "date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
            "time": {"type": "string", "pattern": r"^(?:[01]\d|2[0-3]):[0-5]\d$"},
            "latitude": {"type": "number", "exclusiveMinimum": -90, "exclusiveMaximum": 90},
            "longitude": {"type": "number", "minimum": -180, "maximum": 180},
            "timezone": {"type": "string", "description": "Optional explicit IANA timezone; with a time, DST fold/gap local times are rejected."},
        },
        "required": ["date", "time", "latitude", "longitude"],
        "additionalProperties": False}}


ASTROLOGY_HELLENISTIC_SCHEMA = _legacy_schema(
    "astrology_hellenistic",
    "Calculate Hellenistic analysis (sect, bonification, joys) via the "
    "local Astrology Engine. A known birth time is required (sect is "
    "time-dependent); engine report only, no interpretation.")
ASTROLOGY_DIGNITY_SCHEMA = _legacy_schema(
    "astrology_dignity",
    "Calculate the essential-dignities table with scoring and mutual "
    "receptions via the local Astrology Engine. Known birth time "
    "required; engine report only.")

ASTROLOGY_RUNIC_SCHEMA = {
    "name": "astrology_runic",
    "description": (
        "Calculate Northern runic cycle layers (half-month, hour, tide, "
        "station, weekday) for an explicit ISO datetime and longitude "
        "via the local Astrology Engine (Pennick 2023, a modern "
        "synthesis - the engine labels it as such). Explicit IANA "
        "timezone required; the engine's computation output only - "
        "its interpretive --reading mode is never invoked."),
    "parameters": {
        "type": "object",
        "properties": {
            "datetime": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d$"},
            "longitude": {"type": "number", "minimum": -180, "maximum": 180},
            "timezone": {"type": "string"},
            "age": {"type": "number", "minimum": 0, "maximum": 150},
        },
        "required": ["datetime", "longitude", "timezone"],
        "additionalProperties": False,
    },
}

ASTROLOGY_CAPABILITIES_SCHEMA = {
    "name": "astrology_capabilities",
    "description": (
        "Discover the configured Astrology Engine's capability catalog "
        "dynamically: runs the engine's own `capabilities` and `tools` "
        "commands and intersects the result with the pinned X.09 "
        "allowlist for the E.09-tested engine revision. Anything the "
        "engine reports that is not on the allowlist is named as "
        "unvetted and never exposed as a tool."),
    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
}


def _coords(args, lat_key="latitude", lon_key="longitude"):
    latitude = _number(args.get(lat_key), minimum=-90.0, maximum=90.0)
    longitude = _number(args.get(lon_key), minimum=-180.0, maximum=180.0)
    if latitude is None or not -90.0 < latitude < 90.0:
        return None, None, f"{lat_key} must be a finite number strictly between -90 and 90"
    if longitude is None:
        return None, None, f"{lon_key} must be a finite number from -180 to 180"
    return latitude, longitude, None


def _build_structured_handler(ctx, subcommand, calculation, *, query=False):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        required = {"date", "time", "latitude", "longitude", "timezone"}
        allowed = required | {"ayanamsa"}
        if query:
            required |= {"query_latitude", "query_longitude"}
            allowed |= {"query_latitude", "query_longitude"}
        if not required.issubset(args) or not set(args) <= allowed:
            return tool_error(
                f"{calculation} requires date, time, latitude, longitude, "
                "and an explicit IANA timezone; no other fields are accepted")
        raw_date = _calendar_date(args.get("date"))
        raw_time = _clock_time(args.get("time"))
        if raw_date is None:
            return tool_error("date must be a real calendar date in YYYY-MM-DD form")
        if raw_time is None:
            return tool_error(
                "time is required and must use 24-hour HH:MM form: this "
                "engine family requires a known birth time")
        tz_name, zone, tz_error = _timezone_arg(args)
        if tz_error is not None or tz_name is None:
            return tool_error(tz_error or "timezone must be a valid IANA timezone name")
        dst = _dst_error(raw_date, raw_time, zone, tz_name)
        if dst is not None:
            return tool_error(dst)
        latitude, longitude, coord_error = _coords(args)
        if coord_error is not None:
            return tool_error(coord_error)
        argv = [subcommand, "--date", raw_date, "--time", raw_time,
                "--lat", _coordinate(latitude), "--lon", _coordinate(longitude),
                "--timezone", tz_name]
        ayanamsa = args.get("ayanamsa")
        if ayanamsa is not None:
            if ayanamsa not in _AYANAMSAS:
                return tool_error("ayanamsa must be one of: " + ", ".join(_AYANAMSAS))
            argv.extend(["--ayanamsa", ayanamsa])
        if query:
            q_lat, q_lon, q_error = _coords(args, "query_latitude", "query_longitude")
            if q_error is not None:
                return tool_error(q_error)
            argv.extend(["--query-lat", _coordinate(q_lat), "--query-lon", _coordinate(q_lon)])
        report, error, key, hit = _run_cached(ctx, argv)
        if error is not None:
            return tool_error(error)
        return tool_result(_envelope(calculation, report, key, hit, timezone_name=tz_name))
    return handle


def _build_legacy_handler(ctx, subcommand, calculation):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        required = {"date", "time", "latitude", "longitude"}
        allowed = required | {"timezone"}
        if not required.issubset(args) or not set(args) <= allowed:
            return tool_error(
                f"{calculation} requires date, time, latitude, and "
                "longitude; only timezone is optional")
        raw_date = _calendar_date(args.get("date"))
        raw_time = _clock_time(args.get("time"))
        if raw_date is None:
            return tool_error("date must be a real calendar date in YYYY-MM-DD form")
        if raw_time is None:
            return tool_error(
                "time is required and must use 24-hour HH:MM form: "
                f"{calculation} is birth-time dependent")
        tz_name, zone, tz_error = _timezone_arg(args)
        if tz_error is not None:
            return tool_error(tz_error)
        dst = _dst_error(raw_date, raw_time, zone, tz_name)
        if dst is not None:
            return tool_error(dst)
        latitude, longitude, coord_error = _coords(args)
        if coord_error is not None:
            return tool_error(coord_error)
        argv = [subcommand, "--date", raw_date, "--time", raw_time,
                "--lat", _coordinate(latitude), "--lon", _coordinate(longitude)]
        if tz_name is not None:
            argv.extend(["--timezone", tz_name])
        report, error, key, hit = _run_cached(ctx, argv)
        if error is not None:
            return tool_error(error)
        return tool_result(_envelope(calculation, report, key, hit, timezone_name=tz_name))
    return handle


def build_runic_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        required = {"datetime", "longitude", "timezone"}
        allowed = required | {"age"}
        if not required.issubset(args) or not set(args) <= allowed:
            return tool_error(
                "datetime, longitude, and timezone are required; only age is optional")
        raw_dt = args.get("datetime")
        if not isinstance(raw_dt, str) or not re.fullmatch(
                r"\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d", raw_dt):
            return tool_error("datetime must use YYYY-MM-DDTHH:MM form")
        raw_date, raw_time = raw_dt.split("T", 1)
        if _calendar_date(raw_date) is None or _clock_time(raw_time) is None:
            return tool_error("datetime must be a real calendar date and time")
        tz_name, zone, tz_error = _timezone_arg(args)
        if tz_error is not None or tz_name is None:
            return tool_error(tz_error or "timezone must be a valid IANA timezone name")
        dst = _dst_error(raw_date, raw_time, zone, tz_name)
        if dst is not None:
            return tool_error(dst)
        longitude = _number(args.get("longitude"), minimum=-180.0, maximum=180.0)
        if longitude is None:
            return tool_error("longitude must be a finite number from -180 to 180")
        argv = ["runic", "--datetime", raw_dt, "--lon", _coordinate(longitude),
                "--timezone", tz_name, "--json"]
        age = args.get("age")
        if age is not None:
            age_value = _number(age, minimum=0.0, maximum=150.0)
            if age_value is None:
                return tool_error("age must be a finite number from 0 to 150")
            argv.extend(["--age", format(age_value, ".12g")])
        report, error, key, hit = _run_cached(ctx, argv)
        if error is not None:
            return tool_error(error)
        return tool_result(_envelope("runic", report, key, hit, timezone_name=tz_name))
    return handle


def build_capabilities_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        if args:
            return tool_error("astrology_capabilities does not accept arguments")
        cap_report, cap_error, _k1, _h1 = _run_cached(ctx, ["capabilities"])
        if cap_error is not None:
            return tool_error(cap_error)
        tool_report, tool_error_msg, _k2, _h2 = _run_cached(ctx, ["tools"])
        if tool_error_msg is not None:
            return tool_error(tool_error_msg)
        try:
            cap_doc = json.loads(cap_report)
            tool_doc = json.loads(tool_report)
        except (TypeError, ValueError):
            return tool_error("The local Astrology Engine returned an unparseable capability catalog.")
        allow = set(CAPABILITY_ALLOWLIST)
        capabilities = []
        for entry in cap_doc.get("capabilities") or []:
            if not isinstance(entry, dict):
                continue
            cid = entry.get("id")
            if cid in allow:
                capabilities.append({"id": cid, "status": entry.get("status"),
                                     "scope": entry.get("scope")})
        reported = {c["id"] for c in capabilities}
        engine_tools = []
        for entry in tool_doc.get("tools") or []:
            if isinstance(entry, dict) and entry.get("capability_id") in allow:
                engine_tools.append(entry["capability_id"])
        return tool_result({
            "success": True,
            "engine": ENGINE_REPO,
            "engine_pin": ENGINE_PIN,
            "engine_version": ENGINE_VERSION,
            "calculation": "capabilities",
            "interpretation_included": False,
            "ephemeris": EPHEMERIS_PROVENANCE,
            "allowlist": list(CAPABILITY_ALLOWLIST),
            "capabilities": capabilities,
            "engine_tools": engine_tools,
            "allowlisted_but_unreported": sorted(allow - reported),
            "production_ready": False,
        })
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
        (
            "astrology_synastry",
            ASTROLOGY_SYNASTRY_SCHEMA,
            build_synastry_handler(ctx),
            "⚭",
        ),
        (
            "astrology_astrocartography",
            ASTROLOGY_ASTROCARTOGRAPHY_SCHEMA,
            build_astrocartography_handler(ctx),
            "🗺️",
        ),
        ("astrology_vedic", ASTROLOGY_VEDIC_SCHEMA,
         _build_structured_handler(ctx, "vedic", "vedic"), "🪔"),
        ("astrology_vargas", ASTROLOGY_VARGAS_SCHEMA,
         _build_structured_handler(ctx, "vargas", "vargas"), "🧩"),
        ("astrology_dashas", ASTROLOGY_DASHAS_SCHEMA,
         _build_structured_handler(ctx, "dashas", "dashas"), "⏳"),
        ("astrology_panchanga", ASTROLOGY_PANCHANGA_SCHEMA,
         _build_structured_handler(ctx, "panchanga", "panchanga"), "📅"),
        ("astrology_relocation", ASTROLOGY_RELOCATION_SCHEMA,
         _build_structured_handler(ctx, "location", "relocation", query=True), "🧭"),
        ("astrology_hellenistic", ASTROLOGY_HELLENISTIC_SCHEMA,
         _build_legacy_handler(ctx, "hellenistic", "hellenistic"), "🏛️"),
        ("astrology_dignity", ASTROLOGY_DIGNITY_SCHEMA,
         _build_legacy_handler(ctx, "dignity", "dignity"), "⚖️"),
        ("astrology_runic", ASTROLOGY_RUNIC_SCHEMA,
         build_runic_handler(ctx), "ᚱ"),
        ("astrology_capabilities", ASTROLOGY_CAPABILITIES_SCHEMA,
         build_capabilities_handler(ctx), "📚"),
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
