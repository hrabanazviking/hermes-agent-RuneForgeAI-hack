"""Stable, profile-local identity metadata independent of any model provider."""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

import yaml

from hermes_constants import get_hermes_home, mkdir_under_hermes_home
from utils import atomic_yaml_write


IDENTITY_VERSION = 1
DEFAULT_IDENTITY_PATH = Path("entity") / "entity.yaml"

logger = logging.getLogger(__name__)

try:
    import fcntl
except ImportError:  # pragma: no cover - platform branch
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover - platform branch
    msvcrt = None


class IdentityError(RuntimeError):
    """The persisted identity cannot be safely created or accepted."""


@dataclass(frozen=True)
class EntityIdentity:
    entity_id: str
    name: str
    created_at: str
    identity_version: int
    persona_pack: str
    home_runtime: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IdentityHealth:
    healthy: bool
    status: str
    identity_path: str
    identity_version: int | None = None
    entity_id: str | None = None
    name: str | None = None
    home_runtime: str | None = None
    error_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


class IdentityStore:
    """Create once and validate thereafter; never silently replace identity."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx

    def enabled(self) -> bool:
        return _as_bool(self._ctx.get_config("identity_enabled", True), True)

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(
            str(self._ctx.get_config("identity_path", str(DEFAULT_IDENTITY_PATH)))
        )
        if configured.is_absolute():
            configured = DEFAULT_IDENTITY_PATH
        candidate = (home / configured).resolve()
        if not candidate.is_relative_to(home):
            candidate = (home / DEFAULT_IDENTITY_PATH).resolve()
        if not candidate.is_relative_to(home):
            raise IdentityError("identity path resolves outside the active profile")
        return candidate

    def ensure(self) -> EntityIdentity:
        path = self.path()
        with self._lock(path):
            if path.exists():
                return self._read(path)
            identity = EntityIdentity(
                entity_id=str(uuid.uuid4()),
                name="undecided",
                created_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                identity_version=IDENTITY_VERSION,
                persona_pack="",
                home_runtime="hermes",
            )
            atomic_yaml_write(
                path,
                identity.as_dict(),
                sort_keys=False,
                create_mode=0o600,
            )
            return identity

    def read(self) -> EntityIdentity:
        return self._read(self.path())

    def _read(self, path: Path) -> EntityIdentity:
        if path.is_symlink():
            raise IdentityError("identity file must not be a symbolic link")
        if not path.is_file():
            raise IdentityError("identity file is missing")
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise IdentityError("identity file is unreadable or malformed") from exc
        if not isinstance(payload, dict):
            raise IdentityError("identity document must be a mapping")

        version = payload.get("identity_version")
        if isinstance(version, bool) or version != IDENTITY_VERSION:
            raise IdentityError("identity version is unsupported")
        entity_id = payload.get("entity_id")
        try:
            parsed_id = uuid.UUID(entity_id) if isinstance(entity_id, str) else None
        except (ValueError, AttributeError) as exc:
            raise IdentityError("entity_id is not a UUID") from exc
        if parsed_id is None or str(parsed_id) != entity_id.lower():
            raise IdentityError("entity_id is not a canonical UUID")

        name = payload.get("name")
        created_at = payload.get("created_at")
        persona_pack = payload.get("persona_pack")
        runtime = payload.get("home_runtime")
        if not isinstance(name, str) or not name.strip() or len(name) > 128:
            raise IdentityError("identity name is invalid")
        if not isinstance(created_at, str) or not self._valid_timestamp(created_at):
            raise IdentityError("identity creation timestamp is invalid")
        if not isinstance(persona_pack, str) or len(persona_pack) > 256:
            raise IdentityError("identity persona_pack is invalid")
        if runtime != "hermes":
            raise IdentityError("identity home_runtime must be hermes")
        return EntityIdentity(
            entity_id=entity_id,
            name=name,
            created_at=created_at,
            identity_version=version,
            persona_pack=persona_pack,
            home_runtime=runtime,
        )

    @staticmethod
    def _valid_timestamp(value: str) -> bool:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False
        return parsed.tzinfo is not None

    @contextmanager
    def _lock(self, path: Path):
        lock_path = path.with_suffix(path.suffix + ".lock")
        mkdir_under_hermes_home(lock_path.parent)
        with lock_path.open("a+b") as lock:
            lock.seek(0, os.SEEK_END)
            if lock.tell() == 0:
                lock.write(b"\0")
                lock.flush()
            lock.seek(0)
            if fcntl is not None:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            elif msvcrt is not None:
                msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock.seek(0)
                if fcntl is not None:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                elif msvcrt is not None:
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


class IdentityBridge:
    """Establish identity at session start without owning persona text."""

    def __init__(self, ctx) -> None:
        self._store = IdentityStore(ctx)

    def hooks(self) -> Iterable[tuple[str, Callable[..., None]]]:
        return (("on_session_start", self.on_session_start),)

    def on_session_start(self, **_: Any) -> None:
        if not self._store.enabled():
            return
        try:
            self._store.ensure()
        except (IdentityError, OSError) as exc:
            logger.warning("Volmarr identity was not initialized: %s", exc)


def probe_identity(ctx) -> IdentityHealth:
    store = IdentityStore(ctx)
    try:
        path = store.path()
    except IdentityError as exc:
        return IdentityHealth(False, "unsafe_path", "", error_type=type(exc).__name__)
    if not store.enabled():
        return IdentityHealth(False, "disabled", str(path))
    try:
        identity = store.read()
    except IdentityError as exc:
        status = "missing" if not path.exists() else "invalid"
        return IdentityHealth(
            False,
            status,
            str(path),
            error_type=type(exc).__name__,
        )
    except OSError as exc:
        return IdentityHealth(
            False,
            "unreadable",
            str(path),
            error_type=type(exc).__name__,
        )
    return IdentityHealth(
        True,
        "healthy",
        str(path),
        identity_version=identity.identity_version,
        entity_id=identity.entity_id,
        name=identity.name,
        home_runtime=identity.home_runtime,
    )
