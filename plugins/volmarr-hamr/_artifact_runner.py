"""Isolated bridge to Hamr's current public artifact inspection API."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 3:
        return 2
    engine_root = Path(sys.argv[1]).resolve()
    artifact_path = Path(sys.argv[2]).resolve()
    targets = sys.argv[3:]
    sys.path.insert(0, str(engine_root / "src"))
    try:
        from hamr.core.builder import inspect

        report = inspect(artifact_path, targets=targets)
        checks = report.get("checks", [])
        payload = {
            "exists": bool(report.get("exists", False)),
            "size_mb": float(report.get("size_mb", 0.0)),
            "targets": [str(item) for item in report.get("targets", [])],
            "checks": checks if isinstance(checks, list) else [],
        }
    except Exception:
        return 2
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
