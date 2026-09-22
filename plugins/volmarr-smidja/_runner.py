"""Isolated read-only bridge to Seidr-Smidja's public Loom API."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))


def _validate(engine_root: Path, spec_path: Path) -> int:
    sys.path.insert(0, str(engine_root / "src"))
    try:
        from seidr_smidja.loom import LoomValidationError, load_and_validate

        spec = load_and_validate(spec_path)
    except LoomValidationError as exc:
        _emit(
            {
                "valid": False,
                "failures": [
                    {
                        "field_path": str(item.field_path)[:200],
                        "reason": str(item.reason)[:500],
                    }
                    for item in exc.failures[:100]
                ],
            }
        )
        return 0
    except Exception:
        return 2
    _emit(
        {
            "valid": True,
            "failures": [],
            "summary": {
                "spec_version": str(spec.spec_version)[:40],
                "avatar_id": str(spec.avatar_id)[:200],
                "display_name": str(spec.display_name)[:200],
                "base_asset_id": str(spec.base_asset_id)[:200],
                "license": str(spec.metadata.license)[:100],
            },
        }
    )
    return 0


def _assets(engine_root: Path, asset_type: str, tags_json: str) -> int:
    sys.path.insert(0, str(engine_root / "src"))
    try:
        tags = json.loads(tags_json)
        if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
            return 2
        from seidr_smidja.hoard.local import LocalHoardAdapter
        from seidr_smidja.hoard.port import AssetFilter

        adapter = LocalHoardAdapter(
            catalog_path=engine_root / "data" / "hoard" / "catalog.yaml",
            bases_dir=engine_root / "data" / "hoard" / "bases",
        )
        assets = adapter.list_assets(
            AssetFilter(asset_type=asset_type or None, tags=tags)
        )
    except Exception:
        return 2
    _emit(
        {
            "assets": [
                {
                    "asset_id": item.asset_id,
                    "display_name": item.display_name,
                    "asset_type": item.asset_type,
                    "tags": item.tags,
                    "vrm_version": item.vrm_version,
                    "file_size_bytes": item.file_size_bytes,
                    "cached": item.cached,
                }
                for item in assets[:101]
            ]
        }
    )
    return 0


def _gate_rules(engine_root: Path, target_name: str) -> int:
    sys.path.insert(0, str(engine_root / "src"))
    try:
        from seidr_smidja.gate import ComplianceTarget, list_rules

        target = ComplianceTarget(target_name)
        rules = list_rules(target, rules_dir=engine_root / "data" / "gate")
    except Exception:
        return 2
    _emit(
        {
            "rules": [
                {
                    "rule_id": rule.rule_id,
                    "display_name": rule.display_name,
                    "severity": rule.severity.value,
                    "description": rule.description,
                }
                for rule in rules[:101]
            ]
        }
    )
    return 0


def _render_views(engine_root: Path) -> int:
    sys.path.insert(0, str(engine_root / "src"))
    try:
        from seidr_smidja.oracle_eye import list_standard_views

        views = list_standard_views()
    except Exception:
        return 2
    _emit({"views": [view.value for view in views[:33]]})
    return 0


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "validate":
        return _validate(Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve())
    if len(sys.argv) == 5 and sys.argv[1] == "assets":
        return _assets(Path(sys.argv[2]).resolve(), sys.argv[3], sys.argv[4])
    if len(sys.argv) == 4 and sys.argv[1] == "gate-rules":
        return _gate_rules(Path(sys.argv[2]).resolve(), sys.argv[3])
    if len(sys.argv) == 3 and sys.argv[1] == "render-views":
        return _render_views(Path(sys.argv[2]).resolve())
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
