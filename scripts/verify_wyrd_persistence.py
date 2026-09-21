#!/usr/bin/env python3
"""Verify official WYRD fact persistence using an isolated disposable database."""

from __future__ import annotations

import gc
import json
import tempfile
from pathlib import Path
from uuid import uuid4


MINIMUM_VERSION = (1, 0, 0)


def _version_tuple(value: str) -> tuple[int, int, int]:
    core = value.strip().lstrip("v").split("-", 1)[0].split("+", 1)[0]
    parts = core.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise ValueError("wyrdforge has no valid semantic version")
    return int(parts[0]), int(parts[1]), int(parts[2])


def main() -> int:
    try:
        import wyrdforge
        from wyrdforge.bridges.python_rpg import BridgeConfig, PythonRPGBridge
    except (ImportError, ModuleNotFoundError) as exc:
        print(
            json.dumps(
                {
                    "healthy": False,
                    "status": "dependency_missing",
                    "error_type": type(exc).__name__,
                },
                sort_keys=True,
            )
        )
        return 2

    version = getattr(wyrdforge, "__version__", "")
    try:
        if _version_tuple(version) < MINIMUM_VERSION:
            raise ValueError("wyrdforge is older than 1.0.0")
    except ValueError as exc:
        print(
            json.dumps(
                {
                    "healthy": False,
                    "status": "unsupported_version",
                    "package_version": version or None,
                    "error": str(exc),
                },
                sort_keys=True,
            )
        )
        return 1

    subject_id = "runeforge_acceptance"
    fact_key = "restart_probe"
    fact_value = f"verified-{uuid4().hex}"
    try:
        with tempfile.TemporaryDirectory(prefix="runeforge-wyrd-acceptance-") as tmp:
            db_path = Path(tmp) / "wyrd-acceptance.db"
            config = BridgeConfig(
                world_id="runeforge_acceptance",
                db_path=str(db_path),
                use_bond_service=False,
            )
            writer = PythonRPGBridge.from_config(config)
            try:
                writer.push_event(
                    "fact",
                    {
                        "subject_id": subject_id,
                        "key": fact_key,
                        "value": fact_value,
                        "confidence": 1.0,
                        "domain": "acceptance",
                    },
                )
            finally:
                writer.teardown()
            del writer
            gc.collect()
            if not db_path.is_file():
                raise RuntimeError("WYRD did not create its disposable database")

            reader = PythonRPGBridge.from_config(config)
            try:
                facts = reader.oracle.get_facts(subject_id)
                matches = [
                    fact
                    for fact in facts
                    if fact.content.structured_payload.fact_key == fact_key
                    and fact.content.structured_payload.fact_value == fact_value
                ]
            finally:
                reader.teardown()
            match_count = len(matches)
            del facts, matches, reader
            gc.collect()
            if match_count != 1:
                raise RuntimeError("fact was not recovered exactly once after restart")
    except Exception as exc:
        print(
            json.dumps(
                {
                    "healthy": False,
                    "status": "persistence_failed",
                    "package_version": version,
                    "error_type": type(exc).__name__,
                    "detail": str(exc)[:500],
                },
                sort_keys=True,
            )
        )
        return 1

    print(
        json.dumps(
            {
                "healthy": True,
                "status": "restart_persistence_verified",
                "package_version": version,
                "records_recovered": 1,
                "storage": "disposable_sqlite",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
