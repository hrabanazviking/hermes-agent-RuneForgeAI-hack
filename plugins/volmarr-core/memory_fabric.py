"""Profile-safe attachment boundary for the external Bifröst memory bridge."""

from __future__ import annotations

import importlib
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home


DEFAULT_MIMIR_DB_PATH = Path("memory") / "runa_memory.db"
DEFAULT_MUNINN_DB_PATH = Path("memory") / "muninn_hebbian.db"


class MemoryFabricConfigurationError(ValueError):
    """A memory-fabric path or external package violates the bridge contract."""


def _profile_path(value: Any, default: Path) -> Path:
    home = get_hermes_home().resolve()
    configured = Path(str(value or default))
    if configured.is_absolute():
        return configured.resolve()
    resolved = (home / configured).resolve()
    if not resolved.is_relative_to(home):
        raise MemoryFabricConfigurationError(
            "relative Bifröst storage path escapes the active profile"
        )
    return resolved


@dataclass(frozen=True)
class BifrostSettings:
    mimir_db_path: Path
    muninn_db_path: Path

    @classmethod
    def from_plugin_context(cls, ctx) -> "BifrostSettings":
        return cls(
            mimir_db_path=_profile_path(
                ctx.get_config("bifrost_mimir_db_path", str(DEFAULT_MIMIR_DB_PATH)),
                DEFAULT_MIMIR_DB_PATH,
            ),
            muninn_db_path=_profile_path(
                ctx.get_config("bifrost_muninn_db_path", str(DEFAULT_MUNINN_DB_PATH)),
                DEFAULT_MUNINN_DB_PATH,
            ),
        )


def build_bifrost_bridge(ctx):
    """Construct a Mímir-only Bifröst bridge for the active profile without I/O."""
    settings = BifrostSettings.from_plugin_context(ctx)
    package = importlib.import_module("bifrost")
    try:
        config_type = package.BifrostConfig
        bridge_type = package.BifrostBridge
        backend_type = package.MemoryBackend
        mimir_backend = backend_type.MIMIR
    except AttributeError as exc:
        raise MemoryFabricConfigurationError(
            "installed bifrost package does not expose the required bridge API"
        ) from exc
    config = config_type(
        mimir_db_path=str(settings.mimir_db_path),
        muninn_db_path=str(settings.muninn_db_path),
        default_backend=mimir_backend,
        enable_hebbian_reinforcement=False,
        auto_consolidate=False,
        auto_decay=False,
    )
    return bridge_type(config), settings


@dataclass(frozen=True)
class BifrostHealth:
    healthy: bool
    status: str
    mimir_db_path: str
    package_attached: bool = False
    memory_count: int | None = None
    error_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def probe_bifrost(ctx) -> BifrostHealth:
    """Validate Bifröst and its Mímir store without mutating or querying other backends."""
    configured_path = str(
        ctx.get_config("bifrost_mimir_db_path", str(DEFAULT_MIMIR_DB_PATH))
    )
    try:
        _bridge, settings = build_bifrost_bridge(ctx)
    except ModuleNotFoundError as exc:
        return BifrostHealth(
            False,
            "package_missing",
            configured_path,
            error_type=type(exc).__name__,
        )
    except Exception as exc:
        return BifrostHealth(
            False,
            "configuration_error",
            configured_path,
            error_type=type(exc).__name__,
        )

    db_path = settings.mimir_db_path
    if db_path.is_symlink() or not db_path.is_file():
        return BifrostHealth(
            False,
            "storage_missing",
            str(db_path),
            package_attached=True,
        )
    try:
        uri = f"file:{db_path.as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=1.0) as connection:
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'memories'"
            ).fetchone()
            if table is None:
                return BifrostHealth(
                    False,
                    "schema_missing",
                    str(db_path),
                    package_attached=True,
                )
            row = connection.execute("SELECT COUNT(*) FROM memories").fetchone()
        return BifrostHealth(
            True,
            "healthy",
            str(db_path),
            package_attached=True,
            memory_count=int(row[0]),
        )
    except Exception as exc:
        return BifrostHealth(
            False,
            "storage_error",
            str(db_path),
            package_attached=True,
            error_type=type(exc).__name__,
        )
