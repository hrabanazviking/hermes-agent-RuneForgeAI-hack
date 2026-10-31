"""Profile-bound binding for Volmarr's ravens: muninn + huginn (Slice 90).

The ravens are Volmarr's own standalone packages (``~/workspace/ravens``:
muninn 1.0.0, huginn 1.0.0), built to the Bifröst contract. The Slice 90
Gate 0 re-audit (see ``PERSISTENT_ENTITY_ACCEPTANCE_AUDIT.md``) measured
the bridge-mediated paths against the real packages and found:

- Muninn through Bifröst IS profile-bound (Bifröst passes the configured
  ``muninn_db_path`` into ``MuninnConfig``) and its write semantics are
  exactly the audited ones.
- Huginn through Bifröst is NOT profile-bound: Bifröst constructs
  ``HuginnMemory(config=None)``, whose local store defaults to
  ``~/.hermes/memory/huginn_local.db`` — the default home, shared by
  every profile. Bridge-mediated Huginn therefore stays NO-GO.
- Every Bifröst bridge *method* (``health`` included) lazily constructs
  both ravens and opens/creates their stores: bridge methods are
  write-side operations and are never used by read-only probes here.

This module is the Hermes-side binding the audit cleared:

- ``probe_ravens`` attests the installed packages import-only — it
  constructs no memory object and opens no store.
- ``build_muninn_memory`` / ``build_huginn_memory`` construct the real
  ravens pinned to the ACTIVE profile's configured store paths. Huginn
  is constructed directly (never through the bridge) with
  ``backend="local"`` so its store is the profile's own file and no
  Qdrant probe or network touch occurs. These builders are write-side:
  constructing a raven opens (and if needed creates/heals) its store.
  Callers must treat them as such; no read-only path in this plugin
  calls them.
"""

from __future__ import annotations

import importlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .memory_fabric import (
    DEFAULT_MUNINN_DB_PATH,
    MemoryFabricConfigurationError,
    _profile_path,
)


DEFAULT_HUGINN_DB_PATH = Path("memory") / "huginn_local.db"

MUNINN_REQUIRED_SYMBOLS = ("HebbianMemory",)
HUGINN_REQUIRED_SYMBOLS = ("HuginnMemory",)


class RavensConfigurationError(ValueError):
    """A ravens path or package violates the binding contract."""


@dataclass(frozen=True)
class RavensSettings:
    muninn_db_path: Path
    huginn_db_path: Path

    @classmethod
    def from_plugin_context(cls, ctx) -> "RavensSettings":
        return cls(
            muninn_db_path=_profile_path(
                ctx.get_config("bifrost_muninn_db_path", str(DEFAULT_MUNINN_DB_PATH)),
                DEFAULT_MUNINN_DB_PATH,
            ),
            huginn_db_path=_profile_path(
                ctx.get_config("bifrost_huginn_db_path", str(DEFAULT_HUGINN_DB_PATH)),
                DEFAULT_HUGINN_DB_PATH,
            ),
        )


@dataclass(frozen=True)
class RavensHealth:
    healthy: bool
    status: str
    muninn_db_path: str
    huginn_db_path: str
    muninn_version: str | None = None
    huginn_version: str | None = None
    error_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_raven(name: str, required_symbols: tuple[str, ...], config_module: str):
    package = importlib.import_module(name)
    for symbol in required_symbols:
        if not hasattr(package, symbol):
            raise RavensConfigurationError(
                f"installed {name} package does not expose {symbol}"
            )
    config = importlib.import_module(config_module)
    return package, config


def probe_ravens(ctx) -> RavensHealth:
    """Attest the installed ravens import-only: no construction, no store I/O."""
    try:
        settings = RavensSettings.from_plugin_context(ctx)
    except Exception as exc:
        return RavensHealth(
            False,
            "configuration_error",
            str(ctx.get_config("bifrost_muninn_db_path", str(DEFAULT_MUNINN_DB_PATH))),
            str(ctx.get_config("bifrost_huginn_db_path", str(DEFAULT_HUGINN_DB_PATH))),
            error_type=type(exc).__name__,
        )
    versions: dict[str, str | None] = {}
    for name, symbols, config_module, config_class in (
        ("muninn", MUNINN_REQUIRED_SYMBOLS, "muninn.config", "MuninnConfig"),
        ("huginn", HUGINN_REQUIRED_SYMBOLS, "huginn.config", "HuginnConfig"),
    ):
        try:
            package, config = _load_raven(name, symbols, config_module)
            if not hasattr(config, config_class):
                raise RavensConfigurationError(
                    f"installed {name} package does not expose {config_class}"
                )
        except ModuleNotFoundError as exc:
            return RavensHealth(
                False,
                "package_missing",
                str(settings.muninn_db_path),
                str(settings.huginn_db_path),
                error_type=type(exc).__name__,
            )
        except Exception as exc:
            return RavensHealth(
                False,
                "contract_mismatch",
                str(settings.muninn_db_path),
                str(settings.huginn_db_path),
                error_type=type(exc).__name__,
            )
        version = getattr(package, "__version__", None)
        versions[name] = version if isinstance(version, str) else None
    return RavensHealth(
        True,
        "healthy",
        str(settings.muninn_db_path),
        str(settings.huginn_db_path),
        muninn_version=versions["muninn"],
        huginn_version=versions["huginn"],
    )


def build_muninn_memory(ctx):
    """Construct the profile's Muninn (write-side: opens/creates its store)."""
    settings = RavensSettings.from_plugin_context(ctx)
    try:
        package, config_module = _load_raven(
            "muninn", MUNINN_REQUIRED_SYMBOLS, "muninn.config"
        )
        config = config_module.MuninnConfig(db_path=str(settings.muninn_db_path))
        return package.HebbianMemory(config)
    except RavensConfigurationError:
        raise
    except Exception as exc:
        raise RavensConfigurationError(
            "installed muninn package could not construct the profile memory"
        ) from exc


def build_huginn_memory(ctx):
    """Construct the profile's Huginn directly, local backend, profile store.

    Never routed through Bifröst: the bridge constructs Huginn with
    default paths in the default home (Slice 90 Gate 0 re-audit), which
    breaks profile isolation. ``backend="local"`` keeps construction
    deterministic — no Qdrant probe, no network.
    """
    settings = RavensSettings.from_plugin_context(ctx)
    try:
        package, config_module = _load_raven(
            "huginn", HUGINN_REQUIRED_SYMBOLS, "huginn.config"
        )
        config = config_module.HuginnConfig(
            local_db_path=str(settings.huginn_db_path),
            backend="local",
        )
        return package.HuginnMemory(config)
    except RavensConfigurationError:
        raise
    except Exception as exc:
        raise RavensConfigurationError(
            "installed huginn package could not construct the profile memory"
        ) from exc


__all__ = [
    "DEFAULT_HUGINN_DB_PATH",
    "RavensConfigurationError",
    "RavensHealth",
    "RavensSettings",
    "build_huginn_memory",
    "build_muninn_memory",
    "probe_ravens",
]
