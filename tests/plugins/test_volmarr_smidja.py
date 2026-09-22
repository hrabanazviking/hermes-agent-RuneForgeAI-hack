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


def _profile(home: Path, engine: Path, specs: Path, artifacts: Path | None = None) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [volmarr-smidja]\n  entries:\n    volmarr-smidja:\n"
        "      settings:\n"
        f"        engine_root: {json.dumps(str(engine))}\n"
        f"        spec_root: {json.dumps(str(specs))}\n"
        f"        artifact_root: {json.dumps(str(artifacts or specs))}\n"
        f"        python_path: {json.dumps(sys.executable)}\n",
        encoding="utf-8",
    )


def _engine(root: Path) -> None:
    loom = root / "src" / "seidr_smidja" / "loom"
    hoard = root / "src" / "seidr_smidja" / "hoard"
    gate = root / "src" / "seidr_smidja" / "gate"
    oracle = root / "src" / "seidr_smidja" / "oracle_eye"
    loom.mkdir(parents=True)
    hoard.mkdir()
    gate.mkdir()
    oracle.mkdir()
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
    (gate / "gate.py").write_text("", encoding="utf-8")
    (gate / "__init__.py").write_text(
        "import json\nfrom enum import Enum\nfrom types import SimpleNamespace\n"
        "class ComplianceTarget(str, Enum):\n"
        "    VRCHAT='VRCHAT'\n"
        "    VTUBE_STUDIO='VTUBE_STUDIO'\n"
        "def list_rules(target, rules_dir):\n"
        "    values=json.loads((rules_dir / (target.value + '.json')).read_text(encoding='utf-8'))\n"
        "    return [SimpleNamespace(**{k:v for k,v in item.items() if k!='severity'}, "
        "severity=SimpleNamespace(value=item['severity'])) for item in values]\n"
        "def check(vrm_path, targets, rules_dir, vrchat_tier):\n"
        "    invalid=vrm_path.read_text(encoding='utf-8').startswith('INVALID')\n"
        "    enums=[ComplianceTarget(item) for item in targets]\n"
        "    results={}\n"
        "    for target in enums:\n"
        "        violations=[]\n"
        "        if invalid: violations.append(SimpleNamespace(rule_id='fixture.invalid', "
        "severity=SimpleNamespace(value='ERROR'), field_path='humanoid.bones', "
        "description='Required structure is missing.'))\n"
        "        elif target is ComplianceTarget.VRCHAT: violations.append(SimpleNamespace("
        "rule_id='vrchat.polycount', severity=SimpleNamespace(value='WARNING'), "
        "field_path='mesh.polycount', description='Rule not evaluated in structural mode.'))\n"
        "        results[target.value]=SimpleNamespace(passed=not invalid, violations=violations)\n"
        "    return SimpleNamespace(passed=not invalid, targets_checked=enums, results=results)\n",
        encoding="utf-8",
    )
    rules_dir = root / "data" / "gate"
    rules_dir.mkdir()
    for target in ("VRCHAT", "VTUBE_STUDIO"):
        (rules_dir / f"{target}.json").write_text(
            json.dumps(
                [
                    {
                        "rule_id": f"{target.casefold()}.required",
                        "display_name": f"{target} Required Rule",
                        "severity": "ERROR",
                        "description": "Required by the target.",
                    }
                ]
            ),
            encoding="utf-8",
        )
    (oracle / "eye.py").write_text("", encoding="utf-8")
    (oracle / "__init__.py").write_text(
        "import json\nfrom pathlib import Path\nfrom types import SimpleNamespace\n"
        "def list_standard_views():\n"
        "    values=json.loads((Path(__file__).parents[3] / 'data' / 'views.json').read_text(encoding='utf-8'))\n"
        "    return [SimpleNamespace(value=value) for value in values]\n",
        encoding="utf-8",
    )
    (root / "data" / "views.json").write_text(
        json.dumps(["front", "side", "face_closeup"]), encoding="utf-8"
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
            "smidja_gate_rules",
            "smidja_render_views",
            "smidja_gate_check",
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


def test_gate_check_is_bounded_honest_and_profile_scoped(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home_a = get_hermes_home()
    home_b = tmp_path / "home-b-check"
    engine_a = tmp_path / "smidja-check-a"
    engine_b = tmp_path / "smidja-check-b"
    specs_a = tmp_path / "specs-check-a"
    specs_b = tmp_path / "specs-check-b"
    artifacts_a = tmp_path / "artifacts-a"
    artifacts_b = tmp_path / "artifacts-b"
    _engine(engine_a)
    _engine(engine_b)
    specs_a.mkdir()
    specs_b.mkdir()
    artifacts_a.mkdir()
    artifacts_b.mkdir()
    (artifacts_a / "avatar.vrm").write_text("VALID A", encoding="utf-8")
    (artifacts_b / "avatar.vrm").write_text("INVALID B", encoding="utf-8")
    _profile(home_a, engine_a, specs_a, artifacts_a)
    _profile(home_b, engine_b, specs_b, artifacts_b)

    manager = PluginManager()
    manager.discover_and_load()
    try:
        reports = []
        for home in (home_a, home_b, home_a):
            token = set_hermes_home_override(home)
            try:
                reports.append(
                    json.loads(
                        registry.dispatch(
                            "smidja_gate_check",
                            {"artifact_path": "avatar.vrm", "targets": ["VRCHAT"]},
                            scope=manager.scope_key,
                        )
                    )
                )
            finally:
                reset_hermes_home_override(token)
    finally:
        manager.unload()

    assert [report["official_gate_passed"] for report in reports] == [True, False, True]
    assert reports[0]["unevaluated_rule_ids"] == ["vrchat.polycount"]
    assert reports[1]["results"]["VRCHAT"]["violations"][0]["severity"] == "ERROR"
    assert all(report["certification_complete"] is False for report in reports)
    assert all(report["blender_launched"] is False for report in reports)
    assert all(report["output_created"] is False for report in reports)


def test_gate_check_rejects_unbounded_or_escaping_artifacts(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    engine = tmp_path / "smidja-check"
    specs = tmp_path / "specs-check"
    artifacts = tmp_path / "artifacts"
    _engine(engine)
    specs.mkdir()
    artifacts.mkdir()
    outside = tmp_path / "outside.vrm"
    outside.write_text("outside", encoding="utf-8")
    huge = artifacts / "huge.vrm"
    with huge.open("wb") as stream:
        stream.seek(128 * 1024 * 1024)
        stream.write(b"x")
    _profile(get_hermes_home(), engine, specs, artifacts)
    manager = PluginManager()
    manager.discover_and_load()
    try:
        rejected = [
            json.loads(
                registry.dispatch("smidja_gate_check", args, scope=manager.scope_key)
            )
            for args in (
                {"artifact_path": "../outside.vrm"},
                {"artifact_path": str(outside.resolve())},
                {"artifact_path": "huge.vrm"},
                {"artifact_path": "avatar.glb"},
                {"artifact_path": "missing.vrm", "write": True},
                {"artifact_path": "missing.vrm", "targets": [["VRCHAT"]]},
            )
        ]
    finally:
        manager.unload()

    assert all("error" in item for item in rejected)


def test_render_view_discovery_is_non_rendering_and_profile_scoped(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home_a = get_hermes_home()
    home_b = tmp_path / "home-b-views"
    engine_a = tmp_path / "smidja-views-a"
    engine_b = tmp_path / "smidja-views-b"
    specs_a = tmp_path / "specs-views-a"
    specs_b = tmp_path / "specs-views-b"
    _engine(engine_a)
    _engine(engine_b)
    specs_a.mkdir()
    specs_b.mkdir()
    (engine_b / "data" / "views.json").write_text(
        json.dumps(["profile_b_view"]), encoding="utf-8"
    )
    _profile(home_a, engine_a, specs_a)
    _profile(home_b, engine_b, specs_b)

    manager = PluginManager()
    manager.discover_and_load()
    try:
        discovered = []
        for home in (home_a, home_b, home_a):
            token = set_hermes_home_override(home)
            try:
                result = json.loads(
                    registry.dispatch("smidja_render_views", {}, scope=manager.scope_key)
                )
                discovered.append(result)
            finally:
                reset_hermes_home_override(token)
    finally:
        manager.unload()

    assert [item["views"] for item in discovered] == [
        ["front", "side", "face_closeup"],
        ["profile_b_view"],
        ["front", "side", "face_closeup"],
    ]
    assert all(item["blender_launched"] is False for item in discovered)
    assert all(item["images_created"] is False for item in discovered)


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


def test_gate_rule_discovery_is_metadata_only_and_profile_scoped(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home_a = get_hermes_home()
    home_b = tmp_path / "home-b-gate"
    engine_a = tmp_path / "smidja-gate-a"
    engine_b = tmp_path / "smidja-gate-b"
    specs_a = tmp_path / "specs-gate-a"
    specs_b = tmp_path / "specs-gate-b"
    _engine(engine_a)
    _engine(engine_b)
    specs_a.mkdir()
    specs_b.mkdir()
    path_b = engine_b / "data" / "gate" / "VRCHAT.json"
    values_b = json.loads(path_b.read_text(encoding="utf-8"))
    values_b[0]["rule_id"] = "profile_b.required"
    path_b.write_text(json.dumps(values_b), encoding="utf-8")
    _profile(home_a, engine_a, specs_a)
    _profile(home_b, engine_b, specs_b)

    manager = PluginManager()
    manager.discover_and_load()
    try:
        rule_ids = []
        results = []
        for home in (home_a, home_b, home_a):
            token = set_hermes_home_override(home)
            try:
                result = json.loads(
                    registry.dispatch(
                        "smidja_gate_rules",
                        {"target": "VRCHAT"},
                        scope=manager.scope_key,
                    )
                )
                results.append(result)
                rule_ids.append(result["rules"][0]["rule_id"])
            finally:
                reset_hermes_home_override(token)
        rejected = json.loads(
            registry.dispatch(
                "smidja_gate_rules",
                {"target": "ALL"},
                scope=manager.scope_key,
            )
        )
    finally:
        manager.unload()

    assert rule_ids == ["vrchat.required", "profile_b.required", "vrchat.required"]
    assert all(result["artifact_inspected"] is False for result in results)
    assert all(result["compliance_performed"] is False for result in results)
    assert "error" in rejected
