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
    loom.mkdir(parents=True)
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
        assert loaded.enabled and loaded.tools_registered == ["smidja_spec_validate"]
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
