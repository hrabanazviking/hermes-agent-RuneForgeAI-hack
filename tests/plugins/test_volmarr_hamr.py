"""Contracts for the read-only official Hamr validation boundary."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)


def _write_profile(home: Path, engine_root: Path, spec_root: Path) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-hamr]\n"
        "  entries:\n"
        "    volmarr-hamr:\n"
        "      settings:\n"
        f"        engine_root: {json.dumps(str(engine_root))}\n"
        f"        spec_root: {json.dumps(str(spec_root))}\n"
        f"        python_path: {json.dumps(sys.executable)}\n",
        encoding="utf-8",
    )


def _fake_engine(root: Path, record: Path | None = None) -> None:
    package = root / "src" / "hamr" / "core"
    package.mkdir(parents=True)
    (root / "src" / "hamr" / "__init__.py").write_text("", encoding="utf-8")
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "errors.py").write_text(
        "class SpecValidationError(Exception):\n"
        "    def __init__(self, errors):\n"
        "        self.errors = errors\n",
        encoding="utf-8",
    )
    record_code = ""
    if record is not None:
        record_code = (
            "        import json, os\n"
            f"        Path({str(record)!r}).write_text(json.dumps({{\n"
            "            'stdin_closed': sys.stdin.read(1) == '',\n"
            "            'secret_present': os.environ.get('OPENROUTER_API_KEY') is not None,\n"
            "            'hermes_home_present': os.environ.get('HERMES_HOME') is not None,\n"
            "        }), encoding='utf-8')\n"
        )
    (package / "spec.py").write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "from types import SimpleNamespace\n"
        "from hamr.core.errors import SpecValidationError\n\n"
        "class Spec:\n"
        "    @classmethod\n"
        "    def from_yaml(cls, path):\n"
        f"{record_code}"
        "        value = Path(path).read_text(encoding='utf-8').strip()\n"
        "        if value.startswith('INVALID:'):\n"
        "            raise SpecValidationError([value.removeprefix('INVALID:').strip()])\n"
        "        return SimpleNamespace(character=SimpleNamespace(\n"
        "            name=value, version='1.0', export=SimpleNamespace(format='vrm1')\n"
        "        ))\n",
        encoding="utf-8",
    )
    (package / "constants.py").write_text(
        "BODY_PRESETS = {'average': {'waist': 0.5, 'height': 0.6}}\n",
        encoding="utf-8",
    )
    (package / "presets.py").write_text(
        "CHARACTER_PRESETS = {\n"
        "    'starter': {\n"
        "        'display_name': 'Starter Avatar',\n"
        "        'description': 'A bounded test preset.',\n"
        "    },\n"
        "}\n",
        encoding="utf-8",
    )


def test_real_discovery_validates_without_credentials_blender_or_output(tmp_path, monkeypatch):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    engine = tmp_path / "hamr"
    specs = tmp_path / "specs"
    record = tmp_path / "record.json"
    _fake_engine(engine, record)
    specs.mkdir()
    (specs / "avatar.yaml").write_text("Read-Only Avatar", encoding="utf-8")
    _write_profile(get_hermes_home(), engine, specs)
    monkeypatch.setenv("OPENROUTER_API_KEY", "must-not-reach-hamr")

    manager = PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-hamr"]
        assert loaded.enabled
        assert set(loaded.tools_registered) == {"hamr_spec_validate", "hamr_presets"}
        result = json.loads(
            registry.dispatch(
                "hamr_spec_validate",
                {"spec_path": "avatar.yaml"},
                scope=manager.scope_key,
            )
        )
    finally:
        manager.unload()

    assert result["valid"] is True
    assert result["summary"] == {
        "name": "Read-Only Avatar",
        "version": "1.0",
        "export_format": "vrm1",
    }
    assert result["blender_launched"] is False
    assert result["output_created"] is False
    assert json.loads(record.read_text(encoding="utf-8")) == {
        "stdin_closed": True,
        "secret_present": False,
        "hermes_home_present": False,
    }
    assert sorted(path.name for path in specs.iterdir()) == ["avatar.yaml"]


def test_presets_returns_official_catalog_structure_without_spec_content(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    engine = tmp_path / "hamr"
    specs = tmp_path / "specs"
    _fake_engine(engine)
    specs.mkdir()
    _write_profile(get_hermes_home(), engine, specs)

    manager = PluginManager()
    manager.discover_and_load()
    try:
        result = json.loads(
            registry.dispatch("hamr_presets", {}, scope=manager.scope_key)
        )
        rejected = json.loads(
            registry.dispatch(
                "hamr_presets", {"include_full_specs": True}, scope=manager.scope_key
            )
        )
    finally:
        manager.unload()

    assert result["body_count"] == 1
    assert result["character_count"] == 1
    assert result["body"] == [
        {"name": "average", "proportions": {"height": 0.6, "waist": 0.5}}
    ]
    assert result["character"] == [
        {
            "name": "starter",
            "display_name": "Starter Avatar",
            "description": "A bounded test preset.",
        }
    ]
    assert result["blender_launched"] is False
    assert "error" in rejected


def test_validation_resolves_active_profile_a_b_a(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home_a = get_hermes_home()
    home_b = tmp_path / "home-b"
    engine_a = tmp_path / "hamr-a"
    engine_b = tmp_path / "hamr-b"
    specs_a = tmp_path / "specs-a"
    specs_b = tmp_path / "specs-b"
    _fake_engine(engine_a)
    _fake_engine(engine_b)
    specs_a.mkdir()
    specs_b.mkdir()
    (specs_a / "avatar.yaml").write_text("Avatar A", encoding="utf-8")
    (specs_b / "avatar.yaml").write_text("Avatar B", encoding="utf-8")
    _write_profile(home_a, engine_a, specs_a)
    _write_profile(home_b, engine_b, specs_b)

    manager = PluginManager()
    manager.discover_and_load()
    try:
        names = []
        for home in (home_a, home_b, home_a):
            token = set_hermes_home_override(home)
            try:
                result = json.loads(
                    registry.dispatch(
                        "hamr_spec_validate",
                        {"spec_path": "avatar.yaml"},
                        scope=manager.scope_key,
                    )
                )
                names.append(result["summary"]["name"])
            finally:
                reset_hermes_home_override(token)
    finally:
        manager.unload()

    assert names == ["Avatar A", "Avatar B", "Avatar A"]


def test_validation_reports_official_errors_and_rejects_path_escape(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    engine = tmp_path / "hamr"
    specs = tmp_path / "specs"
    _fake_engine(engine)
    specs.mkdir()
    (specs / "invalid.yaml").write_text("INVALID: height outside range", encoding="utf-8")
    (tmp_path / "outside.yaml").write_text("Outside", encoding="utf-8")
    _write_profile(get_hermes_home(), engine, specs)

    manager = PluginManager()
    manager.discover_and_load()
    try:
        invalid = json.loads(
            registry.dispatch(
                "hamr_spec_validate",
                {"spec_path": "invalid.yaml"},
                scope=manager.scope_key,
            )
        )
        rejected = []
        for args in (
            {"spec_path": "../outside.yaml"},
            {"spec_path": str((tmp_path / "outside.yaml").resolve())},
            {"spec_path": "avatar.json"},
            {"spec_path": "invalid.yaml", "build": True},
        ):
            rejected.append(
                json.loads(
                    registry.dispatch(
                        "hamr_spec_validate", args, scope=manager.scope_key
                    )
                )
            )
    finally:
        manager.unload()

    assert invalid["valid"] is False
    assert invalid["errors"] == ["height outside range"]
    assert all("error" in result for result in rejected)
