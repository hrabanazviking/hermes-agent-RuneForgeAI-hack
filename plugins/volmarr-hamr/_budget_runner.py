"""Isolated read-only bridge to Hamr's pure-Python performance estimator."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        return 2
    engine_root = Path(sys.argv[1]).resolve()
    spec_path = Path(sys.argv[2]).resolve()
    tier = sys.argv[3]
    sys.path.insert(0, str(engine_root / "src"))
    try:
        from hamr.core.perf import MEMORY_TIERS, check_budget
        from hamr.core.spec import Spec

        budget = MEMORY_TIERS[tier]
        spec = Spec.from_yaml(spec_path)
        report = check_budget(spec.character, budget)
        payload = {
            "within_budget": bool(report.within_budget),
            "estimates": {
                "build_time_seconds": float(report.build_time_seconds),
                "peak_memory_mb": float(report.peak_memory_mb),
                "total_triangles": int(report.total_triangles),
                "max_texture_resolution": int(report.max_texture_resolution),
            },
            "limits": {
                "max_build_time_seconds": float(budget.max_build_time_seconds),
                "max_memory_mb": float(budget.max_memory_mb),
                "max_triangles": int(budget.max_triangles),
                "max_texture_resolution": int(budget.max_texture_resolution),
                "blender_timeout_seconds": float(budget.blender_timeout_seconds),
                "target_fps": float(budget.target_fps),
            },
            "warnings": [str(item)[:500] for item in report.warnings[:100]],
        }
    except Exception:
        return 2
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
