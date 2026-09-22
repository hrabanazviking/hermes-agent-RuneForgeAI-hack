"""Contracts for the read-only Seidr-Smidja Loom boundary."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)


def _profile(home: Path, engine: Path, specs: Path) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [volmarr-smidja]\n  entries:\n    volmarr-smidja:\n"
        "      settings:\n"
        f"        engine_root: {json.dumps(str(engine))}\n"
        f"        spec_root: {json.dumps(str(specs))}\n"
        f"        python_path: {json.dumps(sys.executable)}\n",
        encoding="utf-8",
    )


def _engine(root: Path) -> None:
    loom = root / "src" / "seidr_smidja" / "loom"
    hoard = root / "src" / "seidr_smidja" / "hoard"
    loom.mkdir(parents=True)
    hoard.mkdir()
    (root / "src" / "seidr_smidja" / "__init__.py").write_text("", encoding="utf-8")
    (loom / "loader.py").write_text("", encoding="utf-8")
    (loom / "__init__.py").write_text(
        "from pathlib import Path\nfrom types import SimpleNamespace\n"
        "class Failure:\n"
        "    def __init__(self, field_path, reason): self.field_path=field_path; self.reason=reason\n"
        "class LoomValidationError(Exception):\n"
        "    def __init__(self, failures): self.failures=failures\n"
        "def load_and_validate(path):\n"
        "    value=Path(path).read_text(encoding='utf-8').strip()\n"
        "    if value.startswith('INVALID:'): raise LoomValidationError([Failure('avatar_id', value[8:].strip())])\n"
        "    return SimpleNamespace(spec_version='1.0', avatar_id=value, display_name=value, "
        "base_asset_id='vroid/test', metadata=SimpleNamespace(license='CC0-1.0'))\n",
        encoding="utf-8",
    )
    (hoard / "__init__.py").write_text("", encoding="utf-8")
    (hoard / "port.py").write_text(
        "from dataclasses import dataclass\n"
        "@dataclass\n"
        "class AssetFilter:\n"
        "    asset_type: str | None = None\n"
        "    tags: list[str] | None = None\n",
        encoding="utf-8",
    )
    (hoard / "local.py").write_text(
        "import json\nfrom types import SimpleNamespace\n"
        "class LocalHoardAdapter:\n"
        "    def __init__(self, catalog_path, bases_dir): self.catalog_path=catalog_path; self.bases_dir=bases_dir\n"
        "    def list_assets(self, filter):\n"
        "        values=json.loads(self.catalog_path.read_text(encoding='utf-8'))\n"
        "        return [SimpleNamespace(**item) for item in values "
        "if (not filter.asset_type or item['asset_type']==filter.asset_type) "
        "and all(tag in item['tags'] for tag in (filter.tags or []))]\n",
        encoding="utf-8",
    )
    catalog = root / "data" / "hoard" / "catalog.yaml"
    bases = root / "data" / "hoard" / "bases"
    bases.mkdir(parents=True)
    catalog.write_text(
        json.dumps(
            [
                {
                    "asset_id": "vroid/sample_a",
                    "display_name": "Sample A",
                    "asset_type": "vrm_base",
                    "tags": ["feminine", "sample"],
                    "vrm_version": "1.0",
                    "file_size_bytes": 128,
                    "cached": True,
                },
                {
                    "asset_id": "vroid/sample_b",
                    "display_name": "Sample B",
                    "asset_type": "vrm_base",
                    "tags": ["masculine", "sample"],
                    "vrm_version": "0.0",
                    "file_size_bytes": None,
                    "cached": False,
                },
            ]
        ),
        encoding="utf-8",
    )


def test_real_discovery_validates_and_reports_failures_without_forge(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    engine = tmp_path / "smidja"
    specs = tmp_path / "specs"
    _engine(engine)
    specs.mkdir()
    (specs / "valid.yaml").write_text("avatar_a", encoding="utf-8")
    (specs / "invalid.yaml").write_text("INVALID: required value missing", encoding="utf-8")
    _profile(get_hermes_home(), engine, specs)
    manager = PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-smidja"]
        assert loaded.enabled and loaded.tools_registered == [
            "smidja_spec_validate",
            "smidja_assets",
        ]
        valid = json.loads(registry.dispatch("smidja_spec_validate", {"spec_path": "valid.yaml"}, scope=manager.scope_key))
        invalid = json.loads(registry.dispatch("smidja_spec_validate", {"spec_path": "invalid.yaml"}, scope=manager.scope_key))
    finally:
        manager.unload()

    assert valid["valid"] is True and valid["summary"]["avatar_id"] == "avatar_a"
    assert invalid["valid"] is False
    assert invalid["failures"] == [{"field_path": "avatar_id", "reason": "required value missing"}]
    assert valid["forge_dispatched"] is False
    assert valid["blender_launched"] is False
    assert valid["output_created"] is False
    assert valid["source"]["license_metadata"].startswith("CONFLICT:")


def test_validation_rejects_escape_absolute_extra_and_oversized_inputs(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    engine = tmp_path / "smidja"
    specs = tmp_path / "specs"
    _engine(engine)
    specs.mkdir()
    outside = tmp_path / "outside.yaml"
    outside.write_text("outside", encoding="utf-8")
    (specs / "huge.yaml").write_text("x" * (64 * 1024 + 1), encoding="utf-8")
    _profile(get_hermes_home(), engine, specs)
    manager = PluginManager()
    manager.discover_and_load()
    try:
        rejected = [
            json.loads(registry.dispatch("smidja_spec_validate", args, scope=manager.scope_key))
            for args in (
                {"spec_path": "../outside.yaml"},
                {"spec_path": str(outside.resolve())},
                {"spec_path": "huge.yaml"},
                {"spec_path": "missing.yaml", "dispatch": True},
            )
        ]
    finally:
        manager.unload()
    assert all("error" in item for item in rejected)


def test_validation_resolves_active_profile_a_b_a(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home_a = get_hermes_home()
    home_b = tmp_path / "home-b"
    engine_a = tmp_path / "smidja-a"
    engine_b = tmp_path / "smidja-b"
    specs_a = tmp_path / "specs-a"
    specs_b = tmp_path / "specs-b"
    _engine(engine_a)
    _engine(engine_b)
    specs_a.mkdir()
    specs_b.mkdir()
    (specs_a / "avatar.yaml").write_text("avatar_a", encoding="utf-8")
    (specs_b / "avatar.yaml").write_text("avatar_b", encoding="utf-8")
    _profile(home_a, engine_a, specs_a)
    _profile(home_b, engine_b, specs_b)

    manager = PluginManager()
    manager.discover_and_load()
    try:
        avatar_ids = []
        for home in (home_a, home_b, home_a):
            token = set_hermes_home_override(home)
            try:
                result = json.loads(
                    registry.dispatch(
                        "smidja_spec_validate",
                        {"spec_path": "avatar.yaml"},
                        scope=manager.scope_key,
                    )
                )
                avatar_ids.append(result["summary"]["avatar_id"])
            finally:
                reset_hermes_home_override(token)
    finally:
        manager.unload()

    assert avatar_ids == ["avatar_a", "avatar_b", "avatar_a"]


def test_asset_discovery_filters_metadata_without_resolving_or_bootstrapping(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    engine = tmp_path / "smidja"
    specs = tmp_path / "specs"
    _engine(engine)
    specs.mkdir()
    _profile(get_hermes_home(), engine, specs)
    manager = PluginManager()
    manager.discover_and_load()
    try:
        result = json.loads(
            registry.dispatch(
                "smidja_assets",
                {"asset_type": "vrm_base", "tags": ["feminine"]},
                scope=manager.scope_key,
            )
        )
        rejected = json.loads(
            registry.dispatch(
                "smidja_assets",
                {"tags": ["x"] * 9},
                scope=manager.scope_key,
            )
        )
    finally:
        manager.unload()

    assert result["count"] == 1
    assert result["assets"][0]["asset_id"] == "vroid/sample_a"
    assert result["assets"][0]["cached"] is True
    assert result["asset_resolved"] is False
    assert result["asset_fetched"] is False
    assert result["hoard_bootstrapped"] is False
    assert "error" in rejected


def test_asset_discovery_resolves_active_profile_a_b_a(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home_a = get_hermes_home()
    home_b = tmp_path / "home-b-assets"
    engine_a = tmp_path / "smidja-assets-a"
    engine_b = tmp_path / "smidja-assets-b"
    specs_a = tmp_path / "specs-assets-a"
    specs_b = tmp_path / "specs-assets-b"
    _engine(engine_a)
    _engine(engine_b)
    specs_a.mkdir()
    specs_b.mkdir()
    catalog_b = engine_b / "data" / "hoard" / "catalog.yaml"
    values_b = json.loads(catalog_b.read_text(encoding="utf-8"))
    values_b[0]["asset_id"] = "profile_b/sample"
    catalog_b.write_text(json.dumps(values_b), encoding="utf-8")
    _profile(home_a, engine_a, specs_a)
    _profile(home_b, engine_b, specs_b)

    manager = PluginManager()
    manager.discover_and_load()
    try:
        first_ids = []
        for home in (home_a, home_b, home_a):
            token = set_hermes_home_override(home)
            try:
                result = json.loads(
                    registry.dispatch("smidja_assets", {}, scope=manager.scope_key)
                )
                first_ids.append(result["assets"][0]["asset_id"])
            finally:
                reset_hermes_home_override(token)
    finally:
        manager.unload()

    assert first_ids == ["vroid/sample_a", "profile_b/sample", "vroid/sample_a"]
