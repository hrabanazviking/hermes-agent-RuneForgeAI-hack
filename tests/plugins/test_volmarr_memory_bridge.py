"""Contracts for the memory packet bridge (W06 / M5, P.017/P.018).

Invariants: the bridge is a PresentState packet SOURCE only (no
hooks of its own; PresentState remains sole prompt owner); it is
fully gated by memory_corpus_enabled (default false -> no items,
no corpus construction); enabled retrieval serves verbatim cited
sections as durable_knowledge items naming stable id + source
hash + captured corpus generation; the digest path requires its
own second opt-in; cloud egress is double-gated (operator flag
AND cloud-bound turn) and private sources never cross it.
"""

from __future__ import annotations

import importlib
import shutil
from pathlib import Path

import pytest
import yaml

from hermes_constants import get_hermes_home

NS = "profile:w06-bridge"

MEMORY_DOC = (
    "# Long-Term Memory\n\n"
    "## Travel\n\nThe ferry leaves at dawn; needle amber lantern quay.\n\n"
    "## Garden\n\nWild berries and herbal teas.\n"
).encode("utf-8")

USER_DOC = b"# User Profile\n\n## Preferences\n\nPlain words first.\n"


@pytest.fixture(scope="module")
def mods():
    from hermes_cli import plugins as plugins_mod

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
               for name in ("memory_corpus", "memory_bridge", "cli")}
        out["pkg"] = pkg
    finally:
        manager.unload()
    return out


class _Ctx:
    def __init__(self, config=None):
        self._config = dict(config or {})

    def get_config(self, key, default=None):
        return self._config.get(key, default)


@pytest.fixture()
def profile(mods, tmp_path):
    root = Path.home() / f".hermes-w06-bridge-{tmp_path.name}"
    shutil.rmtree(root, ignore_errors=True)
    (root / "memories").mkdir(parents=True)
    (root / "memories/MEMORY.md").write_bytes(MEMORY_DOC)
    (root / "memories/USER.md").write_bytes(USER_DOC)
    corpus = mods["memory_corpus"].MemoryCorpus(root, namespace_id=NS)
    corpus.import_corpus(confirm=True)
    corpus.sync_index()
    yield root, corpus
    shutil.rmtree(root, ignore_errors=True)


def _bridge(mods, corpus, config):
    return mods["memory_bridge"].MemoryBridge(
        _Ctx(config), corpus_factory=lambda ctx: corpus)


def test_bridge_has_no_hooks_and_is_default_off(mods, profile):
    _root, corpus = profile
    bridge = _bridge(mods, corpus, {})
    assert bridge.hooks() == ()
    assert bridge.enabled() is False
    assert bridge.packet_items("s1", "amber lantern") == []
    assert bridge.last_receipt is None  # disabled: zero work done


def test_enabled_retrieval_items_are_provenanced(mods, profile):
    _root, corpus = profile
    bridge = _bridge(mods, corpus, {"memory_corpus_enabled": True})
    items = bridge.packet_items("s1", "amber lantern quay")
    assert items, "retrieval must serve the buried section"
    item = items[0]
    assert item.section == "durable_knowledge"
    assert item.source == "volmarr-memory/full-store"
    assert "amber lantern quay" in item.content
    assert "source_sha256=" in item.content
    assert "corpus_generation=" in item.content
    assert bridge.last_receipt["outcome"] == "served"
    assert bridge.last_receipt["cloud_egress"] == 0
    assert bridge.last_receipt["generation"] == \
        corpus.library.store.load()["generation"]


def test_no_query_without_digest_optin_serves_nothing(mods, profile):
    _root, corpus = profile
    bridge = _bridge(mods, corpus, {"memory_corpus_enabled": True})
    assert bridge.packet_items("s1", "") == []
    assert bridge.last_receipt["outcome"] == "no_items"


def test_digest_path_requires_second_optin(mods, profile):
    _root, corpus = profile
    bridge = _bridge(mods, corpus, {
        "memory_corpus_enabled": True,
        "memory_corpus_digest_enabled": True})
    items = bridge.packet_items("s1", "")
    assert items, "digest-enabled empty query must serve digest items"
    assert all(i.source == "volmarr-memory/hot-digest" for i in items)
    assert all(i.section == "durable_knowledge" for i in items)


def test_cloud_egress_double_gate_and_private_refusal(mods, profile):
    _root, corpus = profile
    # Cloud-bound turn but operator egress flag OFF: local path.
    bridge = _bridge(mods, corpus, {"memory_corpus_enabled": True})
    items = bridge.packet_items("s1", "amber lantern",
                                destination="cloud")
    assert items  # served locally, nothing egressed
    assert bridge.last_receipt["destination"] == "local"
    # Egress ON + cloud-bound: private corpus serves nothing and
    # the receipt names the refusal.
    bridge2 = _bridge(mods, corpus, {
        "memory_corpus_enabled": True,
        "memory_corpus_cloud_egress_enabled": True})
    items2 = bridge2.packet_items("s1", "amber lantern",
                                  destination="cloud")
    assert items2 == []
    assert bridge2.last_receipt["destination"] == "cloud"
    assert bridge2.last_receipt["privacy_refused"]


def test_empty_corpus_serves_nothing(mods, tmp_path):
    root = Path.home() / f".hermes-w06-bridge-empty-{tmp_path.name}"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    try:
        corpus = mods["memory_corpus"].MemoryCorpus(root, namespace_id=NS)
        bridge = _bridge(mods, corpus, {"memory_corpus_enabled": True})
        assert bridge.packet_items("s1", "anything") == []
        assert bridge.last_receipt["outcome"] == "empty_corpus"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_plugin_yaml_declares_all_w06_flags():
    home = get_hermes_home()
    # plugin.yaml ships with the plugin package in the repo tree.
    candidates = list(Path.cwd().glob("plugins/volmarr-core/plugin.yaml"))
    assert candidates, "plugin.yaml must be findable from repo root"
    data = yaml.safe_load(candidates[0].read_text(encoding="utf-8"))
    schema = data["config_schema"]
    for key in ("memory_corpus_enabled", "memory_corpus_digest_enabled",
                "memory_corpus_root", "memory_corpus_cloud_egress_enabled",
                "mempalace_retrieval_enabled",
                "openviking_retrieval_enabled"):
        assert key in schema, f"{key} must be declared (draft 4.8)"
        assert schema[key]["default"] in (False, "")
    assert home  # fixture sanity


def test_cli_corpus_status_reports_honestly(mods, profile, capsys):
    import argparse
    import json as _json

    from hermes_constants import (
        reset_hermes_home_override,
        set_hermes_home_override,
    )

    root, _corpus = profile
    # The CLI constructs the corpus with the profile-derived
    # namespace (draft 4.1: memory belongs to the profile), so
    # import under that same namespace before asking it.
    cli_corpus = mods["memory_corpus"].MemoryCorpus(
        root, namespace_id=f"profile:{root.name}")
    cli_corpus.import_corpus(confirm=True)
    cli_corpus.sync_index()
    token = set_hermes_home_override(str(root))
    try:
        args = argparse.Namespace(
            volmarr_action="memory", memory_action="corpus",
            corpus_action="status", json_output=True)
        rc = mods["cli"].health_command(args, ctx=_Ctx({}))
    finally:
        reset_hermes_home_override(token)
    assert rc == 0
    status = _json.loads(capsys.readouterr().out)
    assert status["kind"] == "memory-corpus-status"
    assert status["targets"]["memory"]["full_store_bytes"] == len(MEMORY_DOC)
    assert status["targets"]["memory"]["ingested"] is True
    assert status["digest"]["state"] == "absent"
