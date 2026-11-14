"""X.07 Huginn-and-Muninn-Ravens contracts (roadmap section 42).

These contracts pin the section 42 test gates on the authority
adapter: verified first-party source (the dedicated repo +
independent per-package pins recorded in the lock), independent
package import (neither raven needs the other), exact API smoke,
no package confusion (PyPI fallback blocked, truthful
package_missing), deterministic reads/writes, and export/restore
via a disposable store close/reopen.

The ravens are external packages, not Hermes dependencies: the
stock test tree has neither installed (the Slice 90 / E.04
record), so -- exactly like tests/plugins/test_volmarr_ravens.py
-- these contracts inject faithful stub packages whose surface
mirrors the real pinned APIs (same classes, methods, and
observable behaviour, SQLite-backed so close/reopen restore is
real). The REAL pinned packages are proven separately in a
staged sibling tree (E.04 proof pattern); see
docs/modernization/X07_RAVENS_WORKSTREAM.md.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path

import pytest

_MUNINN_STUB = '''
import sqlite3

__version__ = "1.0.0"


class MuninnConfig:
    def __init__(self, db_path="muninn.db"):
        self.db_path = db_path


class _Node:
    def __init__(self, row):
        self.id, self.content = row


class HebbianMemory:
    def __init__(self, config=None):
        self.config = config or MuninnConfig()
        self._db = sqlite3.connect(self.config.db_path)
        self._db.execute("CREATE TABLE IF NOT EXISTS nodes "
                         "(id INTEGER PRIMARY KEY, content TEXT, "
                         "category TEXT, importance INT, "
                         "UNIQUE(content, category))")
        self._db.execute("CREATE TABLE IF NOT EXISTS conns "
                         "(a INT, b INT, strength REAL, "
                         "PRIMARY KEY(a, b))")
        self._db.commit()

    def remember(self, content, category="general", importance=5,
                 tags=None, emotional_valence=0.0, path="",
                 metadata=None):
        cur = self._db.execute(
            "INSERT OR IGNORE INTO nodes (content, category, importance) "
            "VALUES (?, ?, ?)", (str(content), category, importance))
        self._db.commit()
        if cur.rowcount:
            return int(cur.lastrowid)
        row = self._db.execute(
            "SELECT id FROM nodes WHERE content=? AND category=?",
            (str(content), category)).fetchone()
        return int(row[0])

    def associate(self, a, b, strength=None, delta=None):
        value = 0.5 if strength is None else float(strength)
        for x, y in ((a, b), (b, a)):
            self._db.execute(
                "INSERT OR REPLACE INTO conns (a, b, strength) "
                "VALUES (?, ?, ?)", (x, y, value))
        self._db.commit()
        return value

    def activate_batch(self, ids, emotional_valence=0.0):
        return {"activated": list(ids)}

    def get_associations(self, memory_id, min_strength=0.0, limit=100):
        rows = self._db.execute(
            "SELECT b, strength FROM conns WHERE a=? AND strength>=? "
            "ORDER BY strength DESC", (memory_id, min_strength)).fetchall()
        return [{"memory_id": int(b), "strength": float(s),
                 "co_activation_count": 1, "consolidated": False,
                 "last_coactivated_at": None} for b, s in rows]

    def decay(self, days=1.0):
        return {"days": float(days), "decayed": 0}

    def consolidate(self, threshold=None):
        return {"consolidated": 0}

    def health(self):
        return {"status": "healthy"}

    def dump(self, limit=50):
        rows = self._db.execute(
            "SELECT id, content FROM nodes LIMIT ?", (limit,)).fetchall()
        return {"stats": {}, "nodes": [
            {"id": i, "content": c} for i, c in rows]}

    def get_node(self, memory_id):
        row = self._db.execute(
            "SELECT id, content FROM nodes WHERE id=?",
            (memory_id,)).fetchone()
        return _Node(row) if row else None

    def close(self):
        self._db.close()
'''

_HUGINN_STUB = '''
import sqlite3

__version__ = "1.0.0"


class HuginnConfig:
    def __init__(self, local_db_path="huginn.db", backend="local"):
        self.local_db_path = local_db_path
        self.backend = backend


class RetrievalResult:
    def __init__(self, query, results):
        self.query = query
        self.results = results
        self.relevance_scores = [float(r["score"]) for r in results]
        self.error = None


class HuginnMemory:
    def __init__(self, config=None):
        self.config = config or HuginnConfig()
        self._db = sqlite3.connect(self.config.local_db_path)
        self._db.execute("CREATE TABLE IF NOT EXISTS memories "
                         "(id INTEGER PRIMARY KEY, content TEXT, "
                         "category TEXT, importance INT, "
                         "UNIQUE(content, category))")
        self._db.commit()

    def upsert_memory(self, content, category="general", importance=5,
                      tags=None, emotional_valence=0.0, memory_id=None):
        cur = self._db.execute(
            "INSERT OR IGNORE INTO memories (content, category, "
            "importance) VALUES (?, ?, ?)",
            (content, category, importance))
        self._db.commit()
        if cur.rowcount:
            return int(cur.lastrowid)
        row = self._db.execute(
            "SELECT id FROM memories WHERE content=? AND category=?",
            (content, category)).fetchone()
        return int(row[0])

    def search(self, query_text, limit=10, category=None,
               min_importance=1):
        terms = set(query_text.lower().split())
        rows = self._db.execute(
            "SELECT id, content, category, importance FROM memories"
        ).fetchall()
        scored = []
        for mid, content, cat, imp in rows:
            words = set(content.lower().split())
            score = len(terms & words) / max(1, len(terms))
            if score > 0:
                scored.append({"id": mid, "content": content,
                               "category": cat, "importance": imp,
                               "tags": [], "emotional_valence": 0.0,
                               "score": score})
        scored.sort(key=lambda r: (-r["score"], r["id"]))
        return scored[:limit]

    def fly(self, query, max_results=5, compress=True):
        return RetrievalResult(query, self.search(query, limit=max_results))

    def multi_hop_retrieve(self, query, hops=2, limit=10):
        return self.search(query, limit=limit)

    def get(self, memory_id):
        row = self._db.execute(
            "SELECT id, content FROM memories WHERE id=?",
            (memory_id,)).fetchone()
        return {"id": row[0], "content": row[1]} if row else None

    def health(self):
        return {"status": "healthy", "backend_configured": "local"}

    def close(self):
        self._db.close()
'''


@pytest.fixture(scope="module")
def stubsrc(tmp_path_factory):
    root = tmp_path_factory.mktemp("ravens-stubs")
    for package, source in (("muninn", _MUNINN_STUB),
                            ("huginn", _HUGINN_STUB)):
        pkg_dir = root / package
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text(source, encoding="utf-8")
    sys.path.insert(0, str(root))
    os.environ["PYTHONPATH"] = (
        str(root) + os.pathsep + os.environ.get("PYTHONPATH", ""))
    for name in ("muninn", "huginn"):
        sys.modules.pop(name, None)
    return root


@pytest.fixture(scope="module")
def mods(stubsrc):
    from hermes_cli import plugins as plugins_mod
    from hermes_constants import get_hermes_home

    home = get_hermes_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [volmarr-core]\n", encoding="utf-8")
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-core"]
        pkg = loaded.module.__package__
        out = {name: importlib.import_module(f"{pkg}.{name}")
               for name in ("ravens_authority", "cli")}
    finally:
        manager.unload()
    return out


class FakeCtx:
    def __init__(self, cfg=None):
        self._cfg = cfg or {}

    def get_config(self, key, default=None):
        return self._cfg.get(key, default)


def _lock_path() -> Path:
    return (Path(__file__).resolve().parents[2]
            / "docs" / "modernization" / "integration-lock.json")


def test_authority_record_names_the_dedicated_repo(mods):
    ra = mods["ravens_authority"]
    record = ra.ravens_authority_status(FakeCtx(), recorded_at="t")
    assert record["schema"] == "runeforge.ravens.authority.v1"
    assert record["service"] == "volmarr-ravens"
    assert record["canonical_repo"] == "hrabanazviking/Huginn-and-Muninn-Ravens"
    assert record["tree_head_pinned"] == ra.RAVENS_TREE_HEAD
    assert record["license"] == "MIT"
    # Truthful by default: the authority surface is default-off and
    # production_ready is never claimed by an audit slice.
    assert record["enabled"] is False
    assert record["production_ready"] is False
    assert record["qdrant_enabled"] is False
    assert "blocked" in record["pypi_fallback"]


def test_independent_package_pins_are_recorded_in_the_lock(mods):
    ra = mods["ravens_authority"]
    lock = json.loads(_lock_path().read_text(encoding="utf-8"))
    rows = {r["name"]: r for r in lock["engines"]}
    muninn, huginn = rows["Muninn"], rows["Huginn"]
    # The shared tree pin stays (ledger guard semantics) ...
    assert muninn["pinned"] == huginn["pinned"] == ra.RAVENS_TREE_HEAD
    # ... and each raven now carries its OWN reviewed package pin.
    assert muninn["package_pin"] == ra.MUNINN_PACKAGE_PIN
    assert huginn["package_pin"] == ra.HUGINN_PACKAGE_PIN
    assert muninn["package_pin"] != huginn["package_pin"]
    # The originating repository is recorded for both rows.
    assert muninn["repo"] == huginn["repo"] == ra.CANONICAL_REPO
    assert "X.07" in muninn["verdict"] and "X.07" in huginn["verdict"]
    # The authority adapter is a registered adapter path for both.
    for row in (muninn, huginn):
        assert "plugins/volmarr-core/ravens_authority.py" in row["adapter"]["paths"]


def test_role_catalog_matches_section_42_item_5(mods):
    ra = mods["ravens_authority"]
    catalog = ra.role_catalog()
    by_package = {p["package"]: p for p in catalog["packages"]}
    assert by_package["muninn"]["role"] == ra.MUNINN_ROLE
    assert "association" in by_package["muninn"]["role"]
    assert "consolidation" in by_package["muninn"]["role"]
    assert by_package["huginn"]["role"] == ra.HUGINN_ROLE
    assert "retrieval" in by_package["huginn"]["role"]
    assert "ranking" in by_package["huginn"]["role"]
    assert catalog["imports_independent"] is True
    assert catalog["second_memory_store_created"] is False


def test_packages_present_with_complete_real_apis(mods):
    ra = mods["ravens_authority"]
    record = ra.ravens_authority_status(FakeCtx(), recorded_at="t")
    assert record["all_packages_present"] is True
    for package in record["packages"]:
        assert package["version"] == "1.0.0"
        assert package["api_complete"] is True, package
        assert package["api_missing"] == []


def test_packages_import_independently(mods):
    ra = mods["ravens_authority"]
    proof = ra.probe_import_independence()
    assert proof["independent"] is True, proof
    assert proof["directions"]["muninn_without_huginn"]["ok"] is True
    assert proof["directions"]["huginn_without_muninn"]["ok"] is True


def test_exact_api_smoke_is_deterministic_and_restores(mods, tmp_path):
    ra = mods["ravens_authority"]
    record = ra.run_ravens_smoke(tmp_path / "smoke")
    assert record["status"] == "ok", record
    assert record["ok"] is True
    assert record["muninn"]["role"] == ra.MUNINN_ROLE
    assert record["huginn"]["role"] == ra.HUGINN_ROLE
    assert record["huginn"]["backend"] == "local"
    assert record["independence"]["independent"] is True


def test_smoke_stays_inside_the_given_root(mods, tmp_path):
    ra = mods["ravens_authority"]
    root = tmp_path / "only_here"
    record = ra.run_ravens_smoke(root)
    assert record["ok"] is True
    created = {p.name for p in root.iterdir()}
    assert created == {"muninn_smoke.db", "huginn_smoke.db"}, created


def _run_cli(mods, argv, ctx):
    cli = mods["cli"]
    parser = argparse.ArgumentParser(prog="hermes")
    sub = parser.add_subparsers(dest="command")
    volmarr_parser = sub.add_parser("volmarr")
    cli.register_cli(volmarr_parser)
    args = parser.parse_args(argv)
    return cli.health_command(args, ctx=ctx)


def test_cli_ravens_family(mods, capsys):
    ctx = FakeCtx()
    rc = _run_cli(mods, ["volmarr", "ravens", "status", "--json"], ctx)
    assert rc == 0
    record = json.loads(capsys.readouterr().out)
    assert record["service"] == "volmarr-ravens"
    assert record["all_packages_present"] is True
    assert record["enabled"] is False  # default-off, reported truthfully
    rc = _run_cli(mods, ["volmarr", "ravens", "roles", "--json"], ctx)
    assert rc == 0
    catalog = json.loads(capsys.readouterr().out)
    assert [p["package"] for p in catalog["packages"]] == ["muninn", "huginn"]
    rc = _run_cli(mods, ["volmarr", "ravens", "smoke", "--json"], ctx)
    assert rc == 0
    smoke = json.loads(capsys.readouterr().out)
    assert smoke["ok"] is True, smoke
    rc = _run_cli(mods, ["volmarr", "ravens"], ctx)
    assert rc == 2
    capsys.readouterr()
