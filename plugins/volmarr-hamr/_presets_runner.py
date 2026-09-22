"""Isolated read-only bridge to Hamr's published preset catalogs."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        return 2
    engine_root = Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(engine_root / "src"))
    try:
        from hamr.core.constants import BODY_PRESETS
        from hamr.core.presets import CHARACTER_PRESETS

        body = [
            {
                "name": name,
                "proportions": {
                    str(key): float(value) for key, value in sorted(proportions.items())
                },
            }
            for name, proportions in sorted(BODY_PRESETS.items())
        ]
        character = [
            {
                "name": name,
                "display_name": str(preset["display_name"])[:200],
                "description": str(preset["description"])[:500],
            }
            for name, preset in sorted(CHARACTER_PRESETS.items())
        ]
    except Exception:
        return 2
    sys.stdout.write(json.dumps({"body": body, "character": character}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
