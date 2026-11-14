"""X.07 ravens authority: the dedicated repo as audited memory-package authority.

Roadmap section 42 names ``hrabanazviking/Huginn-and-Muninn-Ravens``
the candidate canonical source of truth for Volmarr's two ravens,
subject to version/hash/ownership verification. E.04 (2026-11-13)
proved distribution: the repo exists (created by Volmarr
2026-10-31), the published 1.0.0 packages are byte-identical to
this fork's pinned local tree, and the new-machine sibling-clone
route resolves without ever reaching PyPI for these names.

This module is the X.07 Hermes-side authority surface. It is
original volmarr-core code; no ravens source is copied or vendored.

What it records and proves:

- The originating repository and the audited tree pin
  (``fc761f020b39...``, the local ``~/ravens`` HEAD the fork's
  ``[tool.uv.sources]`` sibling binding resolves).
- INDEPENDENT per-package pins: the reviewed commit that
  introduced each package inside that tree -- Muninn at
  ``4eafc310...`` (``muninn 1.0.0``) and Huginn at ``54dd839c...``
  (``huginn 1.0.0``). The shared tree pin stays in the lock as
  ``pinned`` (the ledger guard asserts it); the package pins are
  recorded additively so each raven can move independently in a
  future update.
- Role separation per the packages' REAL APIs (section 42 item 5):
  Muninn is the association / reinforcement / decay /
  consolidation backend (``HebbianMemory``); Huginn is the
  retrieval / ingestion / ranking backend (``HuginnMemory``).
- Import independence (section 42 item 5): neither package needs
  the other to import -- proven live by ``probe_import_independence``
  (a subprocess that hard-blocks the sibling, then imports).
- An exact API smoke (``run_ravens_smoke``) against DISPOSABLE
  stores under a caller-provided directory: deterministic
  Muninn association/decay/consolidation and Huginn
  ingestion/search ranking, plus a close/reopen restore. It never
  touches a profile store.
- Bifröst remains the optional coordination layer (item 6); this
  module creates no second agent memory store -- its smoke stores
  are throwaway proof fixtures, deleted by the caller.

Truth discipline: when a package is absent the status reports
``package_missing`` by name; nothing here ever installs, downloads
or falls back to the unrelated PyPI ``muninn``/``huginn`` projects
(section 42 item 4 / roadmap line 169 name-collision rule).
Qdrant stays off: Huginn is constructed with ``backend="local"``
only, and optional vector operation would need verified
availability plus an explicit privacy agreement (item 9), which
the default-off ``ravens_qdrant_agreed`` key records as NOT given.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path
from typing import Any

CANONICAL_REPO = "hrabanazviking/Huginn-and-Muninn-Ravens"
CANONICAL_REPO_URL = "https://github.com/hrabanazviking/Huginn-and-Muninn-Ravens"
RAVENS_TREE_HEAD = "fc761f020b39f9be875310d271aac7423239d5f8"
MUNINN_PACKAGE_PIN = "4eafc3101e5ea6805cb2f0c11784c6524b30ec6f"
HUGINN_PACKAGE_PIN = "54dd839c931f0856366fecff120fc30ad7443e1d"
PACKAGE_VERSION = "1.0.0"
PACKAGE_LICENSE = "MIT"
REPO_HEAD_AUDITED = "17d6bd8b7d8a9bc7b9446f1cdf20b8d0bff6f94c"
REPO_LICENSE_SHA256 = (
    "c006b7010fa0c6dc396e405025475c03352effe1495e67e0f9d9a11f427b0383"
)

MUNINN_ROLE = "association/reinforcement/decay/consolidation backend"
HUGINN_ROLE = "retrieval/ingestion/ranking backend"

# Real API surface, read from the pinned packages' core classes
# (muninn/core.py HebbianMemory, huginn/core.py HuginnMemory).
MUNINN_API = (
    "remember",
    "associate",
    "activate_batch",
    "get_associations",
    "decay",
    "consolidate",
    "health",
)
HUGINN_API = (
    "upsert_memory",
    "search",
    "fly",
    "multi_hop_retrieve",
    "get",
    "health",
)

_PACKAGES = {
    "muninn": {
        "lock_name": "Muninn",
        "package_pin": MUNINN_PACKAGE_PIN,
        "role": MUNINN_ROLE,
        "memory_class": "HebbianMemory",
        "api": MUNINN_API,
    },
    "huginn": {
        "lock_name": "Huginn",
        "package_pin": HUGINN_PACKAGE_PIN,
        "role": HUGINN_ROLE,
        "memory_class": "HuginnMemory",
        "api": HUGINN_API,
    },
}


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if value is None:
        return default
    return bool(value)


def role_catalog() -> dict[str, Any]:
    """The section 42 item 5 role split, as data (no imports)."""
    return {
        "schema": "runeforge.ravens.roles.v1",
        "service": "volmarr-ravens",
        "canonical_repo": CANONICAL_REPO,
        "tree_head_pinned": RAVENS_TREE_HEAD,
        "packages": [
            {
                "package": name,
                "lock_name": spec["lock_name"],
                "package_pin": spec["package_pin"],
                "version": PACKAGE_VERSION,
                "license": PACKAGE_LICENSE,
                "role": spec["role"],
                "memory_class": spec["memory_class"],
                "api": list(spec["api"]),
            }
            for name, spec in _PACKAGES.items()
        ],
        "imports_independent": True,
        "coordination_layer": "bifrost (optional, preserved)",
        "second_memory_store_created": False,
    }


def _probe_package(name: str) -> dict[str, Any]:
    """Import-only attestation of one raven: constructs nothing."""
    spec = _PACKAGES[name]
    record: dict[str, Any] = {
        "package": name,
        "lock_name": spec["lock_name"],
        "package_pin": spec["package_pin"],
        "expected_version": PACKAGE_VERSION,
        "role": spec["role"],
        "present": False,
        "version": None,
        "api_missing": [],
    }
    try:
        package = importlib.import_module(name)
    except Exception as exc:  # absent or broken install: report, never hide
        record["status"] = "package_missing"
        record["error_type"] = type(exc).__name__
        return record
    record["present"] = True
    record["status"] = "present"
    version = getattr(package, "__version__", None)
    if version is None:
        try:
            from importlib.metadata import version as _meta_version

            version = _meta_version(name)
        except Exception:
            version = None
    record["version"] = version
    memory_cls = getattr(package, spec["memory_class"], None)
    if memory_cls is None:
        record["api_missing"] = [spec["memory_class"]]
    else:
        record["api_missing"] = [
            symbol for symbol in spec["api"] if not hasattr(memory_cls, symbol)
        ]
    record["api_complete"] = not record["api_missing"]
    return record


def ravens_authority_status(ctx, recorded_at: str | None = None) -> dict[str, Any]:
    """Truthful authority status: pins, repo, roles, package presence.

    Import-only: constructs no memory object and opens no store.
    """
    enabled = _as_bool(ctx.get_config("ravens_authority_enabled", False))
    qdrant_agreed = _as_bool(ctx.get_config("ravens_qdrant_agreed", False))
    packages = [_probe_package(name) for name in ("muninn", "huginn")]
    return {
        "schema": "runeforge.ravens.authority.v1",
        "service": "volmarr-ravens",
        "recorded_at": recorded_at,
        "enabled": enabled,
        "canonical_repo": CANONICAL_REPO,
        "canonical_repo_url": CANONICAL_REPO_URL,
        "repo_head_audited": REPO_HEAD_AUDITED,
        "tree_head_pinned": RAVENS_TREE_HEAD,
        "license": PACKAGE_LICENSE,
        "repo_license_sha256": REPO_LICENSE_SHA256,
        "packages": packages,
        "all_packages_present": all(p["present"] for p in packages),
        "imports_independent": True,
        "huginn_backend": "local",
        "qdrant_enabled": False,
        "qdrant_privacy_agreed": qdrant_agreed,
        "pypi_fallback": "blocked ([tool.uv.sources] sibling path binding)",
        "coordination_layer": "bifrost (optional, preserved)",
        "production_ready": False,
    }


_BLOCKER_SCRIPT = """
import importlib.abc
import sys

blocked, target = sys.argv[1], sys.argv[2]


class _Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target_module=None):
        if fullname == blocked or fullname.startswith(blocked + "."):
            raise ImportError(f"blocked for independence proof: {blocked}")
        return None


sys.meta_path.insert(0, _Blocker())
module = importlib.import_module(target)
assert blocked not in sys.modules, f"{target} pulled in {blocked}"
print(f"INDEPENDENT {target} {getattr(module, '__version__', 'unknown')}")
"""


def probe_import_independence(timeout: float = 60.0) -> dict[str, Any]:
    """Prove each raven imports with the other hard-blocked.

    Runs one subprocess per direction so a leaked import cannot be
    masked by interpreter state. A missing package reports
    ``package_missing`` truthfully instead of passing.
    """
    results: dict[str, Any] = {}
    ok = True
    for blocked, target in (("huginn", "muninn"), ("muninn", "huginn")):
        key = f"{target}_without_{blocked}"
        try:
            proc = subprocess.run(
                [sys.executable, "-c", _BLOCKER_SCRIPT, blocked, target],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            results[key] = {"ok": False, "status": "timeout"}
            ok = False
            continue
        out = (proc.stdout or "").strip()
        if proc.returncode == 0 and out.startswith("INDEPENDENT"):
            results[key] = {"ok": True, "status": "independent", "detail": out}
        elif "blocked for independence proof" in (proc.stderr or ""):
            results[key] = {"ok": False, "status": "depends_on_sibling"}
            ok = False
        elif "No module named" in (proc.stderr or "") or "ModuleNotFoundError" in (
            proc.stderr or ""
        ):
            results[key] = {"ok": False, "status": "package_missing"}
            ok = False
        else:
            results[key] = {
                "ok": False,
                "status": "probe_error",
                "detail": (proc.stderr or "").strip()[-300:],
            }
            ok = False
    return {"independent": ok, "directions": results}


def _smoke_muninn(root: Path) -> dict[str, Any]:
    """Exact Muninn API smoke on a disposable store (WRITE, throwaway)."""
    from muninn import HebbianMemory, MuninnConfig

    db_path = root / "muninn_smoke.db"
    memory = HebbianMemory(MuninnConfig(db_path=str(db_path)))
    try:
        first = memory.remember(
            "the river remembers the stone bridge",
            category="smoke",
            importance=7,
            tags=["river", "bridge"],
        )
        second = memory.remember(
            "the stone bridge crosses the cold river",
            category="smoke",
            importance=6,
            tags=["bridge", "river"],
        )
        assert first != second
        # Idempotent store: the same content returns the same id.
        assert memory.remember(
            "the river remembers the stone bridge",
            category="smoke",
            importance=7,
            tags=["river", "bridge"],
        ) == first
        strength = memory.associate(first, second, strength=0.9)
        assert 0.0 < strength <= 1.0
        memory.activate_batch([first], emotional_valence=0.5)
        associations = memory.get_associations(first)
        associated_ids = {int(row["memory_id"]) for row in associations}
        assert second in associated_ids, associations
        decay_report = memory.decay(days=0.0)
        assert isinstance(decay_report, dict)
        consolidate_report = memory.consolidate()
        assert isinstance(consolidate_report, dict)
        health = memory.health()
        assert isinstance(health, dict)
        exported = memory.dump(limit=50)
        assert isinstance(exported, dict)
    finally:
        memory.close()
    # Restore: reopen the same disposable store and read the node back.
    reopened = HebbianMemory(MuninnConfig(db_path=str(db_path)))
    try:
        node = reopened.get_node(first)
        assert node is not None
        content = node.content if hasattr(node, "content") else node["content"]
        assert "river remembers" in str(content)
        again = reopened.get_associations(first)
        again_ids = {int(row["memory_id"]) for row in again}
        assert second in again_ids
    finally:
        reopened.close()
    return {
        "package": "muninn",
        "role": MUNINN_ROLE,
        "steps": [
            "remember x2 (distinct ids)",
            "remember idempotent (same id)",
            "associate strength=0.9",
            "activate_batch (reinforcement)",
            "get_associations contains the wired peer",
            "decay(days=0) report",
            "consolidate() report",
            "health() report",
            "dump() export",
            "close/reopen restore: node + association intact",
        ],
        "ok": True,
    }


def _smoke_huginn(root: Path) -> dict[str, Any]:
    """Exact Huginn API smoke on a disposable local store."""
    from huginn import HuginnConfig, HuginnMemory

    db_path = root / "huginn_smoke.db"
    memory = HuginnMemory(
        HuginnConfig(local_db_path=str(db_path), backend="local")
    )
    try:
        first = memory.upsert_memory(
            "the river remembers the stone bridge",
            category="smoke",
            importance=7,
            tags=["river", "bridge"],
        )
        second = memory.upsert_memory(
            "a kettle sings on the winter stove",
            category="smoke",
            importance=5,
            tags=["kettle", "stove"],
        )
        assert first != second
        results = memory.search("river bridge", limit=5)
        assert results, "search returned nothing for an ingested term"
        assert int(results[0]["id"]) == first, results
        scores = [float(r["score"]) for r in results]
        assert scores == sorted(scores, reverse=True), scores
        # Deterministic reads: the same query repeats exactly.
        repeat = memory.search("river bridge", limit=5)
        assert [int(r["id"]) for r in repeat] == [int(r["id"]) for r in results]
        assert [float(r["score"]) for r in repeat] == scores
        flight = memory.fly("river bridge", max_results=5)
        assert flight.results, "fly() returned no results"
        assert int(flight.results[0]["id"]) == first
        got = memory.get(first)
        assert got is not None and "river remembers" in str(got["content"])
        health = memory.health()
        assert isinstance(health, dict)
    finally:
        memory.close()
    return {
        "package": "huginn",
        "role": HUGINN_ROLE,
        "backend": "local",
        "steps": [
            "upsert_memory x2 (distinct ids)",
            "search ranks the matching memory first",
            "scores are best-first (descending)",
            "search is deterministic across repeats",
            "fly() agrees with search",
            "get() round-trips the ingested content",
            "health() report",
        ],
        "ok": True,
    }


def run_ravens_smoke(root: Path) -> dict[str, Any]:
    """Full section 42 smoke: roles + independence, disposable stores only.

    ``root`` must be a throwaway directory chosen by the caller; the
    smoke creates its two stores there and nowhere else.
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "schema": "runeforge.ravens.smoke.v1",
        "service": "volmarr-ravens",
        "store_root": str(root),
        "ok": False,
    }
    for name in ("muninn", "huginn"):
        try:
            importlib.import_module(name)
        except Exception as exc:
            record["status"] = "package_missing"
            record["missing_package"] = name
            record["error_type"] = type(exc).__name__
            return record
    try:
        record["muninn"] = _smoke_muninn(root)
        record["huginn"] = _smoke_huginn(root)
    except Exception as exc:
        record["status"] = "smoke_failed"
        record["error_type"] = type(exc).__name__
        record["error"] = str(exc)[:300]
        return record
    independence = probe_import_independence()
    record["independence"] = independence
    record["ok"] = bool(
        record["muninn"]["ok"]
        and record["huginn"]["ok"]
        and independence["independent"]
    )
    record["status"] = "ok" if record["ok"] else "independence_failed"
    return record


__all__ = [
    "CANONICAL_REPO",
    "CANONICAL_REPO_URL",
    "HUGINN_API",
    "HUGINN_PACKAGE_PIN",
    "HUGINN_ROLE",
    "MUNINN_API",
    "MUNINN_PACKAGE_PIN",
    "MUNINN_ROLE",
    "PACKAGE_LICENSE",
    "PACKAGE_VERSION",
    "RAVENS_TREE_HEAD",
    "REPO_HEAD_AUDITED",
    "REPO_LICENSE_SHA256",
    "probe_import_independence",
    "ravens_authority_status",
    "role_catalog",
    "run_ravens_smoke",
]
