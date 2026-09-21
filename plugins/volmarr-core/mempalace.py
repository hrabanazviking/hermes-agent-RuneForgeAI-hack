"""Read-only attachment boundary for the external MemPalace episodic store."""

from __future__ import annotations

import importlib
import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home


DEFAULT_PALACE_PATH = Path("memory") / "mempalace"
DEFAULT_COLLECTION_NAME = "mempalace_drawers"
MINIMUM_PACKAGE_VERSION = "3.10.0"
_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")


class MemPalaceConfigurationError(ValueError):
    """The configured palace would violate the active-profile boundary."""


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = _VERSION_RE.fullmatch(value)
    if not match:
        raise MemPalaceConfigurationError(
            "installed mempalace package has no valid semantic version identity"
        )
    return tuple(int(part) for part in match.groups())


def _palace_path(value: Any) -> Path:
    home = get_hermes_home().resolve()
    configured = Path(str(value or DEFAULT_PALACE_PATH))
    if configured.is_absolute():
        return configured.resolve()
    resolved = (home / configured).resolve()
    if not resolved.is_relative_to(home):
        raise MemPalaceConfigurationError(
            "relative MemPalace path escapes the active profile"
        )
    return resolved


@dataclass(frozen=True)
class MemPalaceHealth:
    healthy: bool
    status: str
    palace_path: str
    package_version: str | None = None
    minimum_package_version: str = MINIMUM_PACKAGE_VERSION
    collection_name: str = DEFAULT_COLLECTION_NAME
    collection_present: bool = False
    database_bytes: int | None = None
    error_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def probe_mempalace(ctx) -> MemPalaceHealth:
    """Verify package identity and palace integrity without opening ChromaDB."""
    configured = ctx.get_config("mempalace_path", str(DEFAULT_PALACE_PATH))
    try:
        path = _palace_path(configured)
    except Exception as exc:
        return MemPalaceHealth(
            False,
            "configuration_error",
            str(configured),
            error_type=type(exc).__name__,
        )
    try:
        package = importlib.import_module("mempalace")
        version = getattr(package, "__version__")
        if not isinstance(version, str) or not version or len(version) > 64:
            raise MemPalaceConfigurationError(
                "installed mempalace package has no valid version identity"
            )
        installed_version = _version_tuple(version)
    except ModuleNotFoundError as exc:
        return MemPalaceHealth(
            False,
            "package_missing",
            str(path),
            error_type=type(exc).__name__,
        )
    except Exception as exc:
        return MemPalaceHealth(
            False,
            "package_error",
            str(path),
            error_type=type(exc).__name__,
        )

    if installed_version < _version_tuple(MINIMUM_PACKAGE_VERSION):
        return MemPalaceHealth(
            False,
            "package_outdated",
            str(path),
            package_version=version,
        )

    database = path / "chroma.sqlite3"
    if path.is_symlink() or database.is_symlink() or not database.is_file():
        return MemPalaceHealth(
            False,
            "storage_missing",
            str(path),
            package_version=version,
        )
    collection_name = str(
        ctx.get_config("mempalace_collection_name", DEFAULT_COLLECTION_NAME)
        or DEFAULT_COLLECTION_NAME
    )
    if not 1 <= len(collection_name) <= 128 or "\x00" in collection_name:
        return MemPalaceHealth(
            False,
            "configuration_error",
            str(path),
            package_version=version,
            error_type="MemPalaceConfigurationError",
        )
    try:
        uri = f"file:{database.as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=1.0) as connection:
            integrity = connection.execute("PRAGMA quick_check").fetchone()
            if not integrity or integrity[0] != "ok":
                return MemPalaceHealth(
                    False,
                    "integrity_error",
                    str(path),
                    package_version=version,
                    collection_name=collection_name,
                    database_bytes=database.stat().st_size,
                )
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'collections'"
            ).fetchone()
            collection_present = bool(
                table
                and connection.execute(
                    "SELECT 1 FROM collections WHERE name = ? LIMIT 1",
                    (collection_name,),
                ).fetchone()
            )
        return MemPalaceHealth(
            collection_present,
            "healthy" if collection_present else "collection_missing",
            str(path),
            package_version=version,
            collection_name=collection_name,
            collection_present=collection_present,
            database_bytes=database.stat().st_size,
        )
    except Exception as exc:
        return MemPalaceHealth(
            False,
            "storage_error",
            str(path),
            package_version=version,
            collection_name=collection_name,
            error_type=type(exc).__name__,
        )
