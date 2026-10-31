"""Explicit, opt-in write operations on the profile-bound ravens (Slice 92).

Slice 90's Gate 0 re-audit cleared exactly these paths, and only in
their explicit form: Muninn reinforcement and decay/consolidation
(explicit calls against the profile's own store) and Huginn ingestion
(direct construction, local backend, profile store — never through
Bifröst, whose Huginn is default-home-bound and stays NO-GO). This
module is that enablement, under the campaign's attachment law:

- **Each write has its own default-off flag** —
  ``bifrost_reinforcement_enabled``, ``bifrost_decay_enabled``,
  ``bifrost_consolidation_enabled``, ``bifrost_ingestion_enabled``.
  A disabled operation refuses before any package is imported.
- **No hidden writes on reads.** This module registers no hook and no
  packet producer, and no read path in this plugin imports it. Writes
  happen only when an operator invokes one of the named operations
  (``hermes volmarr memory ravens {reinforce|decay|consolidate|ingest}``).
- **Lazy, separate construction.** Importing this module constructs
  nothing; each operation builds only its own backend through the
  Slice 90 profile-bound builders in :mod:`.ravens` and closes it
  before returning. Reinforcement/decay/consolidation never construct
  Huginn; ingestion never constructs Muninn.
- **Auditable semantics.** All mutation semantics live in the raven
  packages themselves (``muninn``/``huginn`` 1.0.0, their
  ``INTERFACE.md`` files and suites); this module validates inputs,
  gates on flags, and reports the packages' own result dicts verbatim.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import asdict, dataclass, field
from typing import Any

from .memory_fabric import MemoryFabricConfigurationError
from .ravens import RavensConfigurationError, build_huginn_memory, build_muninn_memory


_MAX_INGEST_CONTENT_CHARS = 20_000
_MAX_REINFORCE_IDS = 256
_MAX_DECAY_DAYS = 3_650.0


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "yes", "on", "1"}:
            return True
        if normalized in {"false", "no", "off", "0", ""}:
            return False
    return default


@dataclass(frozen=True)
class RavensWriteResult:
    """Outcome of one explicitly invoked ravens write operation."""

    healthy: bool
    status: str
    operation: str
    detail: dict[str, Any] = field(default_factory=dict)
    error_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _refused(operation: str, status: str, **detail: Any) -> RavensWriteResult:
    return RavensWriteResult(False, status, operation, detail=dict(detail))


def _package_present(name: str) -> bool:
    # A module already in sys.modules counts as present even without a
    # findable spec (the same convention as pm's extras anchors).
    if sys.modules.get(name) is not None:
        return True
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def _build(operation: str, builder, package_name: str):
    """Run one profile-bound builder, mapping failures to statuses."""
    if not _package_present(package_name):
        return None, RavensWriteResult(
            False, "package_missing", operation, error_type="ModuleNotFoundError"
        )
    try:
        return builder(), None
    except (RavensConfigurationError, MemoryFabricConfigurationError) as exc:
        return None, RavensWriteResult(
            False, "configuration_error", operation, error_type=type(exc).__name__
        )
    except Exception as exc:
        return None, RavensWriteResult(
            False, "operation_error", operation, error_type=type(exc).__name__
        )


def _flag(ctx, key: str) -> bool:
    return _as_bool(ctx.get_config(key, False), False)


def reinforce_memories(
    ctx,
    memory_ids: Any,
    emotional_valence: Any = 0.0,
) -> RavensWriteResult:
    """Muninn reinforcement: activate + wire the given memories (WRITE).

    Named write: each id is logged as an activation and every pair is
    wired Hebbian-style by the ``muninn`` package. Gated by
    ``bifrost_reinforcement_enabled`` (default off).
    """
    operation = "reinforce"
    if not _flag(ctx, "bifrost_reinforcement_enabled"):
        return _refused(operation, "disabled")
    if isinstance(memory_ids, (str, bytes)) or not isinstance(memory_ids, (list, tuple)):
        return _refused(operation, "validation_error", reason="ids_not_a_list")
    ids = list(memory_ids)
    if not ids or len(ids) > _MAX_REINFORCE_IDS:
        return _refused(operation, "validation_error", reason="ids_out_of_bounds")
    if any(
        isinstance(item, bool) or not isinstance(item, int) or item <= 0
        for item in ids
    ):
        return _refused(
            operation, "validation_error", reason="ids_not_positive_ints"
        )
    try:
        valence = float(emotional_valence)
    except (TypeError, ValueError):
        return _refused(operation, "validation_error", reason="valence_not_numeric")
    if not -1.0 <= valence <= 1.0:
        return _refused(
            operation, "validation_error", reason="valence_out_of_range"
        )
    memory, error = _build(operation, lambda: build_muninn_memory(ctx), "muninn")
    if error is not None:
        return error
    try:
        memory.activate_batch(ids, emotional_valence=valence)
        return RavensWriteResult(
            True, "ok", operation, detail={"activated": len(ids), "memory_ids": ids}
        )
    except Exception as exc:
        return RavensWriteResult(
            False, "operation_error", operation, error_type=type(exc).__name__
        )
    finally:
        memory.close()


def decay_memories(ctx, days: Any = 1.0) -> RavensWriteResult:
    """Muninn decay: fade strengths/confidences and prune (WRITE).

    Gated by ``bifrost_decay_enabled`` (default off). Half-lives, prune
    threshold, and the returned counts are the ``muninn`` package's own
    semantics, per its ``INTERFACE.md``.
    """
    operation = "decay"
    if not _flag(ctx, "bifrost_decay_enabled"):
        return _refused(operation, "disabled")
    try:
        parsed_days = float(days)
    except (TypeError, ValueError):
        return _refused(operation, "validation_error", reason="days_not_numeric")
    if not 0.0 < parsed_days <= _MAX_DECAY_DAYS:
        return _refused(operation, "validation_error", reason="days_out_of_bounds")
    memory, error = _build(operation, lambda: build_muninn_memory(ctx), "muninn")
    if error is not None:
        return error
    try:
        report = memory.decay(days=parsed_days)
        return RavensWriteResult(
            True, "ok", operation, detail={"days": parsed_days, "report": report}
        )
    except Exception as exc:
        return RavensWriteResult(
            False, "operation_error", operation, error_type=type(exc).__name__
        )
    finally:
        memory.close()


def consolidate_memories(ctx) -> RavensWriteResult:
    """Muninn consolidation: mark strong edges consolidated (WRITE).

    Gated by ``bifrost_consolidation_enabled`` (default off). This is
    the association-store maintenance Bifröst delegates to Muninn —
    not the entity consolidation checkpoint (Phase 7), which never
    rewrites memory.
    """
    operation = "consolidate"
    if not _flag(ctx, "bifrost_consolidation_enabled"):
        return _refused(operation, "disabled")
    memory, error = _build(operation, lambda: build_muninn_memory(ctx), "muninn")
    if error is not None:
        return error
    try:
        report = memory.consolidate()
        return RavensWriteResult(True, "ok", operation, detail={"report": report})
    except Exception as exc:
        return RavensWriteResult(
            False, "operation_error", operation, error_type=type(exc).__name__
        )
    finally:
        memory.close()


def ingest_memory(
    ctx,
    content: Any,
    category: Any = "general",
    importance: Any = 5,
    tags: Any = (),
    emotional_valence: Any = 0.0,
) -> RavensWriteResult:
    """Huginn ingestion: upsert one memory into the semantic store (WRITE).

    Gated by ``bifrost_ingestion_enabled`` (default off). The store is
    the profile's own Huginn local store via the Slice 90 direct
    builder — never Bifröst's default-home Huginn.
    """
    operation = "ingest"
    if not _flag(ctx, "bifrost_ingestion_enabled"):
        return _refused(operation, "disabled")
    if not isinstance(content, str) or not content.strip():
        return _refused(operation, "validation_error", reason="content_empty")
    if len(content) > _MAX_INGEST_CONTENT_CHARS:
        return _refused(operation, "validation_error", reason="content_too_large")
    if not isinstance(category, str) or not category.strip():
        return _refused(operation, "validation_error", reason="category_empty")
    if isinstance(importance, bool):
        return _refused(operation, "validation_error", reason="importance_not_int")
    try:
        parsed_importance = int(importance)
    except (TypeError, ValueError):
        return _refused(operation, "validation_error", reason="importance_not_int")
    if not 1 <= parsed_importance <= 10:
        return _refused(
            operation, "validation_error", reason="importance_out_of_range"
        )
    if isinstance(tags, (str, bytes)) or not isinstance(tags, (list, tuple)):
        return _refused(operation, "validation_error", reason="tags_not_a_list")
    tag_list = [str(tag) for tag in tags]
    try:
        valence = float(emotional_valence)
    except (TypeError, ValueError):
        return _refused(operation, "validation_error", reason="valence_not_numeric")
    if not -1.0 <= valence <= 1.0:
        return _refused(
            operation, "validation_error", reason="valence_out_of_range"
        )
    memory, error = _build(operation, lambda: build_huginn_memory(ctx), "huginn")
    if error is not None:
        return error
    try:
        memory_id = memory.upsert_memory(
            content=content,
            category=category,
            importance=parsed_importance,
            tags=tag_list,
            emotional_valence=valence,
        )
        return RavensWriteResult(
            True, "ok", operation, detail={"memory_id": int(memory_id)}
        )
    except Exception as exc:
        return RavensWriteResult(
            False, "operation_error", operation, error_type=type(exc).__name__
        )
    finally:
        memory.close()


__all__ = [
    "RavensWriteResult",
    "consolidate_memories",
    "decay_memories",
    "ingest_memory",
    "reinforce_memories",
]
