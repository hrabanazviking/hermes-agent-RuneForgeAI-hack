"""Isolated read-only bridge to Seidr-Smidja's public Loom API."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))


def main() -> int:
    if len(sys.argv) != 3:
        return 2
    engine_root = Path(sys.argv[1]).resolve()
    spec_path = Path(sys.argv[2]).resolve()
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


if __name__ == "__main__":
    raise SystemExit(main())
