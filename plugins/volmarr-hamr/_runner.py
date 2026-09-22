"""Isolated read-only bridge to Hamr's public Spec validation API."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))


def main() -> int:
    if len(sys.argv) != 3:
        _emit({"status": "error"})
        return 2
    engine_root = Path(sys.argv[1]).resolve()
    spec_path = Path(sys.argv[2]).resolve()
    sys.path.insert(0, str(engine_root / "src"))
    try:
        from hamr.core.errors import SpecValidationError
        from hamr.core.spec import Spec

        spec = Spec.from_yaml(spec_path)
    except SpecValidationError as exc:
        errors = [str(item)[:500] for item in exc.errors[:100]]
        _emit({"status": "ok", "valid": False, "errors": errors})
        return 0
    except Exception:
        _emit({"status": "error"})
        return 2

    character = spec.character
    export = getattr(character, "export", None)
    _emit(
        {
            "status": "ok",
            "valid": True,
            "errors": [],
            "summary": {
                "name": str(getattr(character, "name", ""))[:200],
                "version": str(getattr(character, "version", ""))[:40],
                "export_format": str(getattr(export, "format", ""))[:40],
            },
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
