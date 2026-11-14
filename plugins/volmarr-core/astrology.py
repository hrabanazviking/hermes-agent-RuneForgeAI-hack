"""X.09 Astrology Engine: richer capability catalog (roadmap s.44).

The Astrology Engine (``hrabanazviking/astrology-engine``) is
pinned at ``bb4ede4fbb32`` (package 4.0.0, Apache-2.0) by E.09.
Its own outputs at the pin, re-measured in X.09: 57 CLI
subcommands, a `capabilities` document naming 28 capability ids
(schema_version 1.0), and a `tools` document naming 26 agent
tools with JSON input schemas. The README's "47 subcommands" is
superseded by measurement.

This module is the Hermes-side X.09 record + operator surface.
It is original volmarr-core code; no engine source is copied or
vendored. The calculation tools themselves live in the
``volmarr-astrology`` plugin (0.8.0), which X.09 upgraded from
the E.09 narrow adapter: the seven deterministic tools retained
(now with explicit timezone + DST fold/gap rejection, and a
known birth time required for predict and geoastrology per
E09-T2), plus engine-verified structured tools (vedic, vargas,
dashas, panchanga, relocation), Hellenistic/dignity reports,
runic cycles, and allowlist-bounded dynamic capability
discovery.

Scope law for this slice (section 44): astronomical calculation
stays separate from interpretation - no result here or in the
plugin invents a position, and the engine's interpretive modes
(reading, dossier, forecast's symbolic keys, tarot, lenormand,
cartomancy, numerology, mantras) are NOT exposed (ticket
X09-T2). Personal chart data is private profile data: results
are computed by a local bounded subprocess, cached only in
process memory keyed by exact inputs + engine pin, and never
logged, persisted, or sent anywhere by this adapter.
``production_ready`` is False.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

CANONICAL_REPO = "hrabanazviking/astrology-engine"
CANONICAL_REPO_URL = "https://github.com/hrabanazviking/astrology-engine"
ENGINE_PIN = "bb4ede4fbb326d21df34a5ca0ca6e343f4f49fbe"
ENGINE_VERSION = "4.0.0"
PROJECT_LICENSE = "Apache-2.0"
LICENSE_SHA256 = "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"
PLUGIN_VERSION = "0.8.0"
CLI_SUBCOMMAND_COUNT = 57
CAPABILITY_COUNT = 28
ENGINE_TOOL_COUNT = 26
BATCH_MAX_ITEMS = 32
BATCH_PER_ITEM_TIMEOUT_SECONDS = 20.0
BATCH_TOTAL_BUDGET_SECONDS = 300.0

# Hermes tool -> engine capability/subcommand, as built in X.09.
EXPOSED_TOOLS = (
    {"tool": "astrology_lunar", "engine": "lunar", "mode": "deterministic"},
    {"tool": "astrology_planetary_hours", "engine": "planet-hours", "mode": "deterministic"},
    {"tool": "astrology_natal", "engine": "natal", "mode": "deterministic"},
    {"tool": "astrology_transit", "engine": "transit", "mode": "deterministic"},
    {"tool": "astrology_predict", "engine": "predict", "mode": "deterministic"},
    {"tool": "astrology_synastry", "engine": "synastry", "mode": "deterministic"},
    {"tool": "astrology_astrocartography", "engine": "geoastrology", "mode": "deterministic"},
    {"tool": "astrology_vedic", "engine": "vedic", "mode": "structured"},
    {"tool": "astrology_vargas", "engine": "vargas", "mode": "structured"},
    {"tool": "astrology_dashas", "engine": "dashas", "mode": "structured"},
    {"tool": "astrology_panchanga", "engine": "panchanga", "mode": "structured"},
    {"tool": "astrology_relocation", "engine": "location", "mode": "structured"},
    {"tool": "astrology_hellenistic", "engine": "hellenistic", "mode": "report"},
    {"tool": "astrology_dignity", "engine": "dignity", "mode": "report"},
    {"tool": "astrology_runic", "engine": "runic", "mode": "structured"},
    {"tool": "astrology_capabilities", "engine": "capabilities+tools", "mode": "discovery"},
)
# Engine-verified but deliberately NOT exposed in X.09, with the
# reason recorded (never silently dropped):
NOT_EXPOSED = (
    {"engine": "reading/dossier/forecast", "reason": "interpretive output; s.44.5 keeps calculation separate from interpretation (X09-T2)"},
    {"engine": "tarot/lenormand/cartomancy/numerology/iching/runecast/ogham", "reason": "divination draws, not astronomical calculation (X09-T2)"},
    {"engine": "charts/chart/chart-show/chart-delete", "reason": "engine chart library persists personal chart data; the adapter keeps chart data in process memory only (X09-T3)"},
    {"engine": "solar-return/progressions/composite/synergy/antiscia/lots/aspect-grid", "reason": "verified CLI surface, not yet adapted; incremental follow-up (X09-T4)"},
    {"engine": "yogas/shadbala/ashtakavarga/jaimini/draconic/asteroids/midpoints/stars/elect/watch/profection/solar-arc/wheel/western/relationship/synergy-json/bazi/chinese/tibetan/mantras", "reason": "verified capability surface, not yet adapted; incremental follow-up (X09-T4)"},
)
OFFLINE_RECIPE = (
    "git clone https://github.com/hrabanazviking/astrology-engine and check out the pin bb4ede4fbb326d21df34a5ca0ca6e343f4f49fbe",
    "python3 -m venv .venv && .venv/bin/pip install -e .[geo]  (geo extra carries timezonefinder + geopy; without it timed charts fail closed - E09-T1)",
    "point the volmarr-astrology plugin's engine_path at astrology_engine.py and python_path at the venv interpreter; no network is used at calculation time",
    "ephemeris provenance: pyswisseph 2.10.3.2 (Swiss Ephemeris 2.10.03); the engine requests the Swiss backend and falls back to its bundled Moshier backend when the optional .se1 data files are absent, naming the actual backend per body in its provenance block; asteroid bodies need seas_18.se1, absent in a plain install (E09-T3)",
)


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if value is None:
        return default
    return bool(value)


def capability_catalog() -> dict[str, Any]:
    """The X.09 catalog: measured engine surface vs Hermes exposure."""
    return {
        "schema": "runeforge.astrology.catalog.v1",
        "service": "volmarr-astrology",
        "canonical_repo": CANONICAL_REPO,
        "engine_pin": ENGINE_PIN,
        "engine_version": ENGINE_VERSION,
        "plugin_version": PLUGIN_VERSION,
        "measured": {
            "cli_subcommands": CLI_SUBCOMMAND_COUNT,
            "capabilities": CAPABILITY_COUNT,
            "engine_tools": ENGINE_TOOL_COUNT,
        },
        "exposed_tools": [dict(row) for row in EXPOSED_TOOLS],
        "not_exposed": [dict(row) for row in NOT_EXPOSED],
        "offline_recipe": list(OFFLINE_RECIPE),
        "interpretation_included": False,
        "production_ready": False,
    }


def _measure_tree(root: Path) -> dict[str, Any]:
    """Measure a staged engine checkout truthfully (no git call)."""
    record: dict[str, Any] = {"root": str(root), "present": root.is_dir()}
    if not root.is_dir():
        record["status"] = "tree_missing"
        return record
    head = None
    head_file = root / ".git" / "HEAD"
    if head_file.is_file():
        ref = head_file.read_text(encoding="utf-8").strip()
        if ref.startswith("ref:"):
            ref_path = root / ".git" / ref[4:].strip()
            if ref_path.is_file():
                head = ref_path.read_text(encoding="utf-8").strip()
            else:
                packed = root / ".git" / "packed-refs"
                if packed.is_file():
                    for line in packed.read_text(encoding="utf-8").splitlines():
                        parts = line.split(" ", 1)
                        if len(parts) == 2 and parts[1].strip() == ref[4:].strip():
                            head = parts[0].strip()
        elif ref:
            head = ref
    record["head"] = head
    record["head_matches_pin"] = head == ENGINE_PIN
    lic = root / "LICENSE"
    if lic.is_file():
        record["license_sha256"] = hashlib.sha256(lic.read_bytes()).hexdigest()
        record["license_matches_audited"] = record["license_sha256"] == LICENSE_SHA256
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        match = re.search(r'^version\s*=\s*"([^"]+)"',
                          pyproject.read_text(encoding="utf-8"), re.M)
        if match:
            record["package_version"] = match.group(1)
    record["status"] = "measured" if head else "tree_partial"
    return record


def astrology_status(ctx, recorded_at: str | None = None) -> dict[str, Any]:
    """Truthful adapter status: config, staged tree, hard limits."""
    enabled = _as_bool(ctx.get_config("astrology_enabled", False))
    root_value = str(ctx.get_config("astrology_root", "") or "").strip()
    tree = _measure_tree(Path(root_value).expanduser()) if root_value else {
        "root": "", "present": False, "status": "not_configured"}
    return {
        "schema": "runeforge.astrology.status.v1",
        "service": "volmarr-astrology",
        "recorded_at": recorded_at,
        "enabled": enabled,
        "configured": bool(root_value),
        "canonical_repo": CANONICAL_REPO,
        "canonical_repo_url": CANONICAL_REPO_URL,
        "engine_pin": ENGINE_PIN,
        "engine_version": ENGINE_VERSION,
        "plugin_version": PLUGIN_VERSION,
        "license": PROJECT_LICENSE,
        "license_sha256": LICENSE_SHA256,
        "tree": tree,
        "mode": "deterministic local calculation; interpretation excluded",
        "chart_data_handling": "private profile data: process-memory cache only, never logged or persisted",
        "production_ready": False,
    }


def local_time_status(raw_date: str, raw_time: str, tz_name: str) -> str:
    """Classify a wall time: ok / fold / gap / invalid_zone / invalid."""
    try:
        zone = ZoneInfo(tz_name)
    except (KeyError, ValueError):
        return "invalid_zone"
    try:
        naive = datetime.combine(date.fromisoformat(raw_date),
                                 time.fromisoformat(raw_time))
    except ValueError:
        return "invalid"

    def _roundtrips(fold: int) -> bool:
        aware = naive.replace(tzinfo=zone, fold=fold)
        back = aware.astimezone(timezone.utc).astimezone(zone)
        return back.replace(tzinfo=None) == naive

    if _roundtrips(0) and _roundtrips(1):
        off0 = naive.replace(tzinfo=zone, fold=0).utcoffset()
        off1 = naive.replace(tzinfo=zone, fold=1).utcoffset()
        return "fold" if off0 != off1 else "ok"
    return "gap"


def cache_key_for(argv: list) -> str:
    """The plugin cache key: exact inputs + engine pin (s.44.7)."""
    canonical = json.dumps({"engine_pin": ENGINE_PIN, "argv": list(argv)},
                           sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_batch_plan(items: list[dict], *, max_items: int = BATCH_MAX_ITEMS,
                     per_item_timeout: float = BATCH_PER_ITEM_TIMEOUT_SECONDS,
                     total_budget: float = BATCH_TOTAL_BUDGET_SECONDS) -> dict[str, Any]:
    """s.44.8 batch plan for time-series / location comparisons.

    A plan is a pure, deterministic function of its items: each
    item names a calculation and its exact inputs; the plan
    validates every item (unknown calculation, bad date/time,
    missing timezone, DST fold/gap and unknown birth time are
    refused BY NAME per item), assigns the s.44.7 cache key the
    plugin would use, and enforces the latency caps (item count,
    per-item timeout, total budget). The replay key is a sha256
    over the canonical plan body: the same items always produce
    the same plan and the same replay key, so a batch can be
    replayed deterministically and cancelled between items (the
    plan carries a cancellation checkpoint per item index).
    This function PLANS only; it runs no engine and reads no
    chart store.
    """
    known = {row["tool"]: row["engine"] for row in EXPOSED_TOOLS}
    refused: list[dict[str, Any]] = []
    planned: list[dict[str, Any]] = []
    for index, item in enumerate(items or []):
        tool = str(item.get("tool") or "")
        if tool not in known:
            refused.append({"index": index, "tool": tool,
                            "reason": "unknown_calculation"})
            continue
        raw_date = str(item.get("date") or "")
        raw_time = item.get("time")
        tz_name = str(item.get("timezone") or "")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date):
            refused.append({"index": index, "tool": tool, "reason": "invalid_date"})
            continue
        needs_time = known[tool] in {"predict", "geoastrology", "vedic",
                                     "vargas", "dashas", "panchanga",
                                     "location", "hellenistic", "dignity"}
        if needs_time and not raw_time:
            refused.append({"index": index, "tool": tool,
                            "reason": "unknown_birth_time"})
            continue
        if raw_time and tz_name:
            status = local_time_status(raw_date, str(raw_time), tz_name)
            if status != "ok":
                refused.append({"index": index, "tool": tool,
                                "reason": f"local_time_{status}"})
                continue
        argv = [known[tool], "--date", raw_date]
        if raw_time:
            argv += ["--time", str(raw_time)]
        if tz_name:
            argv += ["--timezone", tz_name]
        planned.append({"index": index, "tool": tool, "engine": known[tool],
                        "cache_key": cache_key_for(argv),
                        "timeout_seconds": per_item_timeout,
                        "cancel_checkpoint": index})
    effective_cap = min(max_items, int(total_budget // per_item_timeout))
    if len(planned) > effective_cap:
        refused.extend({"index": row["index"], "tool": row["tool"],
                        "reason": "batch_item_cap"} for row in planned[effective_cap:])
        planned = planned[:effective_cap]
    body = {"items": planned, "refused": refused,
            "per_item_timeout": per_item_timeout, "total_budget": total_budget}
    replay_key = hashlib.sha256(
        json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "schema": "runeforge.astrology.batch.v1",
        "service": "volmarr-astrology",
        "items": planned,
        "refused": refused,
        "item_count": len(planned),
        "refused_count": len(refused),
        "caps": {"max_items": effective_cap, "requested_max_items": max_items,
                 "per_item_timeout_seconds": per_item_timeout,
                 "total_budget_seconds": total_budget},
        "estimated_worst_case_seconds": len(planned) * per_item_timeout,
        "cancellation": "between items, at each cancel_checkpoint",
        "replay_key": replay_key,
        "deterministic_replay": True,
        "runs_engine": False,
        "production_ready": False,
    }


# A labelled synthetic batch for the CLI batch verb: two dates x
# the same explicit location, proving the plan machinery without
# claiming any real chart data.
SYNTHETIC_BATCH = [
    {"tool": "astrology_natal", "date": "2000-01-01", "time": "12:00",
     "timezone": "Europe/Stockholm"},
    {"tool": "astrology_natal", "date": "2000-01-02", "time": "12:00",
     "timezone": "Europe/Stockholm"},
    {"tool": "astrology_predict", "date": "2000-01-01",
     "timezone": "Europe/Stockholm"},
]

__all__ = [
    "BATCH_MAX_ITEMS", "CANONICAL_REPO", "CANONICAL_REPO_URL",
    "CAPABILITY_COUNT", "CLI_SUBCOMMAND_COUNT", "ENGINE_PIN",
    "ENGINE_TOOL_COUNT", "ENGINE_VERSION", "EXPOSED_TOOLS",
    "LICENSE_SHA256", "NOT_EXPOSED", "OFFLINE_RECIPE",
    "PLUGIN_VERSION", "PROJECT_LICENSE", "SYNTHETIC_BATCH",
    "astrology_status", "build_batch_plan", "cache_key_for",
    "capability_catalog", "local_time_status",
]
