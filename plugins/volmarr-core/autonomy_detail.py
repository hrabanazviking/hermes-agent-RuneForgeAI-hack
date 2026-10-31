"""Bounded-autonomy reconciliation (Self-Aware Agency roadmap §11).

Emergent Agency Phase 5 (Slice 95) already built the autonomy
policy engine: a human-authoritative ``entity/autonomy_policy.yaml``
the runtime never writes after create-once seeding, a capability
registry carrying numeric risk classes 0-5, deterministic gate
decisions, budgets, and a circuit breaker. Phase 8 (Slice 98) added
the narrow Class 0/1 local action set. What neither carries is this
roadmap's own §11 layer, which is therefore built here as a
reconciliation, not a second autonomy engine:

- §11.3 taxonomy: the six risk classes are named (observe, think,
  local reversible, external reversible, consequential,
  sensitive/destructive), each with its §11 automatic-execution
  rule, exposed by :func:`class_disposition`;
- §11.4 permissions: the roadmap's named permission block stands
  with its own defaults (five ``allow``, six ``ask``, three
  ``deny``), each permission mapped to its §11.3 risk class.
  :meth:`AutonomyDetailService.permission_decision` resolves a
  permission deterministically: a ``deny`` default can never be
  upgraded by anything in this module (§11.2/§3.6 — the entity may
  not expand its own authority); an ``allow`` default holds only
  within the configured ``default_class_limit`` (roadmap default
  2); an ``ask`` default is lifted only by an active §11.5 grant;
- §11.5 capability grants: short-lived, operation-scoped grants
  (operation, bounded scope, expiry, max actions) recorded in this
  module's own bounded log. A grant may be built only for an
  ``ask`` permission — never for a ``deny`` one — and its lifetime
  is bounded by ``autonomy_detail_max_grant_hours``. Grant status
  (active/expired/exhausted) is a deterministic function of the
  log and an explicit clock. Recording is explicit only: no hook,
  loop, or turn-path caller issues, records, or uses a grant, and
  this module executes nothing — the Phase 5 gate remains the only
  gate that decides proposals;
- registry reconciliation: :meth:`reconcile_registry` compares the
  Phase 5 policy's registry classes against the classes §11.3's
  own examples imply for the seeded actions, read-only. Where they
  differ (``github_push``: registry 3, §11.3 class 4 — modifying a
  shared repository is consequential; ``run_local_tests``,
  ``update_self_model_evidence``, ``organize_curiosity_queue``:
  registry 1, §11.3 class 2), the difference is surfaced, never
  silently fixed: the policy is human-authoritative and only a
  human edit may reclassify an entry.

Disabled by default.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home, mkdir_under_hermes_home

from .context_packet import ContextItem
from .identity import IdentityError, IdentityStore, _as_bool

DETAIL_VERSION = 1
DEFAULT_LOG_PATH = Path("entity") / "autonomy_grants.jsonl"
DEFAULT_LOG_LIMIT = 200
MAX_LOG_BYTES = 4 * 1024 * 1024
MAX_SCOPE_CHARS = 200
DEFAULT_CLASS_LIMIT = 2
DEFAULT_MAX_GRANT_HOURS = 168
MAX_GRANT_ACTIONS = 100

# §11.3 risk classes: name + automatic-execution rule.
RISK_CLASSES = {
    0: ("observe", "may_run_automatically"),
    1: ("think", "may_run_automatically_within_budgets"),
    2: ("local_reversible", "may_run_automatically_when_policy_permits"),
    3: ("external_reversible", "requires_explicit_policy_grants_and_budgets"),
    4: ("consequential", "requires_confirmation_unless_human_allowlisted"),
    5: ("sensitive_destructive", "always_requires_explicit_human_approval"),
}

# §11.4 permission block, with the roadmap's own defaults.
PERMISSIONS = {
    "self_model_update": "allow",
    "reflection_write": "allow",
    "curiosity_create": "allow",
    "intrinsic_goal_create": "allow",
    "local_test_run": "allow",
    "web_research": "ask",
    "git_branch_create": "ask",
    "git_commit": "ask",
    "github_push": "ask",
    "external_message_send": "ask",
    "package_install": "ask",
    "file_delete": "deny",
    "credential_change": "deny",
    "autonomy_policy_change": "deny",
}

# Each §11.4 permission's §11.3 risk class, from the §11.3 examples
# (update its own non-authoritative self-model / write reflection /
# add curiosity question / create an intrinsic goal / run safe tests
# are class 2; web research and creating a Git branch are class 3;
# modifying a shared repository, sending messages as the user, and
# installing software are class 4; deleting important data, changing
# credentials, and expanding autonomy permissions are class 5).
PERMISSION_RISK_CLASS = {
    "self_model_update": 2,
    "reflection_write": 2,
    "curiosity_create": 2,
    "intrinsic_goal_create": 2,
    "local_test_run": 2,
    "web_research": 3,
    "git_branch_create": 3,
    "git_commit": 3,
    "github_push": 4,
    "external_message_send": 4,
    "package_install": 4,
    "file_delete": 5,
    "credential_change": 5,
    "autonomy_policy_change": 5,
}

# The §11.3-implied class for the Phase 5/Phase 8 seeded registry
# actions §11.3 names unambiguously. Actions §11.3 does not name
# (local read-only research, private reports) are unmapped, honestly.
EXPECTED_REGISTRY_CLASS = {
    "world_get": 0,
    "inspect_project_state": 0,
    "check_health": 0,
    "inspect_memory_integrity": 0,
    "goal_update": 2,
    "run_local_tests": 2,
    "update_self_model_evidence": 2,
    "organize_curiosity_queue": 2,
    "prepare_suggested_patch": 1,
    "github_push": 4,
}

_GRANT_FIELDS = {
    "detail_version", "kind", "grant_id", "owner_entity_id",
    "operation", "scope", "issued_at", "expires_at", "max_actions",
}
_USE_FIELDS = {
    "detail_version", "kind", "record_id", "grant_id",
    "owner_entity_id", "recorded_at",
}

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


class AutonomyDetailError(RuntimeError):
    """An autonomy detail record cannot be safely built or read."""


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _timestamp_ok(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _epoch(value: str) -> float:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, OverflowError, OSError):
        return 0.0


def _canonical_uuid(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


def class_disposition(risk_class: int) -> dict[str, Any]:
    """The §11.3 name and automatic-execution rule of a risk class."""
    if isinstance(risk_class, bool) or risk_class not in RISK_CLASSES:
        raise AutonomyDetailError("risk class is not a §11.3 class")
    name, rule = RISK_CLASSES[risk_class]
    return {"risk_class": risk_class, "name": name, "rule": rule}


def grant_status(grant: dict[str, Any], actions_used: int, *,
                 now: datetime) -> str:
    """A grant's status at a moment: active, expired, or exhausted."""
    if _parse(grant["expires_at"]) <= now:
        return "expired"
    if actions_used >= int(grant["max_actions"]):
        return "exhausted"
    return "active"


class AutonomyDetailService:
    """The §11 taxonomy/permissions/grants layer beside the Phase 5 gate."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("autonomy_detail_enabled", False), False
        )

    def _limit(self) -> int:
        try:
            value = int(self._ctx.get_config(
                "autonomy_detail_log_limit", DEFAULT_LOG_LIMIT))
        except (TypeError, ValueError):
            value = DEFAULT_LOG_LIMIT
        return min(500, max(10, value))

    def default_class_limit(self) -> int:
        try:
            value = int(self._ctx.get_config(
                "autonomy_detail_default_class_limit", DEFAULT_CLASS_LIMIT))
        except (TypeError, ValueError):
            value = DEFAULT_CLASS_LIMIT
        return min(5, max(0, value))

    def max_grant_hours(self) -> int:
        try:
            value = int(self._ctx.get_config(
                "autonomy_detail_max_grant_hours", DEFAULT_MAX_GRANT_HOURS))
        except (TypeError, ValueError):
            value = DEFAULT_MAX_GRANT_HOURS
        return min(720, max(1, value))

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(
            "autonomy_detail_log_path", str(DEFAULT_LOG_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_LOG_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_LOG_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise AutonomyDetailError(
                "autonomy detail log path resolves outside the profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    # -- §11.3/§11.4 registry reconciliation (read-only) ---------------------
    @staticmethod
    def reconcile_registry(policy: dict[str, Any]) -> dict[str, Any]:
        """Compare a Phase 5 policy registry against §11.3's classes.

        Pure: reads the policy mapping handed to it, writes nothing,
        and never reclassifies — the policy is human-authoritative.
        """
        if not isinstance(policy, dict) \
                or not isinstance(policy.get("capabilities"), dict):
            raise AutonomyDetailError("policy registry is invalid")
        rows: list[dict[str, Any]] = []
        for action in sorted(policy["capabilities"]):
            entry = policy["capabilities"][action]
            if not isinstance(entry, dict) \
                    or not isinstance(entry.get("class"), int):
                raise AutonomyDetailError("policy registry entry is invalid")
            registry_class = int(entry["class"])
            expected = EXPECTED_REGISTRY_CLASS.get(action)
            rows.append({
                "action": action,
                "registry_class": registry_class,
                "registry_class_name": RISK_CLASSES.get(
                    registry_class, ("unknown", ""))[0],
                "expected_class": expected,
                "agreement": (
                    "unmapped" if expected is None
                    else "agrees" if expected == registry_class else "differs"
                ),
            })
        return {
            "rows": rows,
            "agrees": sum(1 for r in rows if r["agreement"] == "agrees"),
            "differs": [r["action"] for r in rows
                        if r["agreement"] == "differs"],
            "unmapped": [r["action"] for r in rows
                         if r["agreement"] == "unmapped"],
        }

    # -- §11.4 permission decisions -------------------------------------------
    def permission_decision(self, permission: str, *,
                            now: datetime | None = None) -> dict[str, Any]:
        """Resolve one §11.4 permission deterministically.

        ``deny`` defaults are absolute here; ``allow`` defaults hold
        only within the default class limit; ``ask`` defaults are
        lifted only by an active §11.5 grant for that operation.
        """
        if permission not in PERMISSIONS:
            raise AutonomyDetailError("permission is not a §11.4 permission")
        default = PERMISSIONS[permission]
        risk_class = PERMISSION_RISK_CLASS[permission]
        base = {
            "permission": permission,
            "default": default,
            "risk_class": risk_class,
            "risk_class_name": RISK_CLASSES[risk_class][0],
        }
        if default == "deny":
            return {**base, "decision": "deny",
                    "reason": "permission_denied_by_default"}
        if default == "allow":
            if risk_class <= self.default_class_limit():
                return {**base, "decision": "allow",
                        "reason": "allowed_within_default_class_limit"}
            return {**base, "decision": "require_confirmation",
                    "reason": "above_default_class_limit"}
        grant = self.active_grant_for(permission, now=now)
        if grant is not None:
            return {**base, "decision": "allow",
                    "reason": "active_capability_grant",
                    "grant_id": grant["grant_id"]}
        return {**base, "decision": "require_confirmation",
                "reason": "no_active_capability_grant"}

    # -- §11.5 capability grants ------------------------------------------------
    def build_grant(self, operation: str, *, scope: str,
                    expires_at: str, max_actions: int = 1,
                    issued_at: str | None = None) -> dict[str, Any]:
        """Build a §11.5 grant record. Pure; records nothing."""
        if operation not in PERMISSIONS:
            raise AutonomyDetailError("grant operation is not a §11.4 permission")
        if PERMISSIONS[operation] == "deny":
            raise AutonomyDetailError(
                "a capability grant can never lift a deny permission")
        if PERMISSIONS[operation] != "ask":
            raise AutonomyDetailError(
                "capability grants exist only for ask permissions")
        if not isinstance(scope, str) or not scope.strip() \
                or len(scope.strip()) > MAX_SCOPE_CHARS:
            raise AutonomyDetailError("grant scope is invalid")
        if isinstance(max_actions, bool) or not isinstance(max_actions, int) \
                or not 1 <= max_actions <= MAX_GRANT_ACTIONS:
            raise AutonomyDetailError("grant max_actions is invalid")
        issued = issued_at or _fmt(_now_dt())
        if not _timestamp_ok(issued) or not _timestamp_ok(expires_at):
            raise AutonomyDetailError("grant timestamps are invalid")
        if _parse(expires_at) <= _parse(issued):
            raise AutonomyDetailError("grant expiry must follow its issue")
        grant = {
            "detail_version": DETAIL_VERSION,
            "kind": "grant",
            "grant_id": str(uuid.uuid4()),
            "owner_entity_id": self._identity.read().entity_id,
            "operation": operation,
            "scope": scope.strip(),
            "issued_at": issued,
            "expires_at": expires_at,
            "max_actions": max_actions,
        }
        self._validate(grant, grant["owner_entity_id"])
        return grant

    def record_grant(self, grant: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled():
            raise AutonomyDetailError("autonomy detail is disabled")
        owner = self._identity.read().entity_id
        self._validate(grant, owner)
        if grant.get("kind") != "grant":
            raise AutonomyDetailError("record is not a grant")
        self._append(grant)
        return grant

    def record_use(self, grant_id: str, *,
                   recorded_at: str | None = None) -> dict[str, Any]:
        """Record one use of an active grant. Executes nothing."""
        if not self.enabled():
            raise AutonomyDetailError("autonomy detail is disabled")
        owner = self._identity.read().entity_id
        grant = self._grant_by_id(grant_id)
        if grant is None:
            raise AutonomyDetailError("grant is unknown")
        moment = _parse(recorded_at) if recorded_at else _now_dt()
        if grant_status(grant, self._usage().get(grant_id, 0),
                        now=moment) != "active":
            raise AutonomyDetailError("grant is not active")
        record = {
            "detail_version": DETAIL_VERSION,
            "kind": "use",
            "record_id": str(uuid.uuid4()),
            "grant_id": grant_id,
            "owner_entity_id": owner,
            "recorded_at": recorded_at or _fmt(_now_dt()),
        }
        self._validate(record, owner)
        self._append(record)
        return record

    def records(self, *, limit: int = 500) -> list[dict[str, Any]]:
        owner = self._identity.read().entity_id
        path = self.path()
        if path.is_symlink():
            raise AutonomyDetailError(
                "autonomy detail log must not be a symbolic link")
        if not path.is_file():
            return []
        if path.stat().st_size > MAX_LOG_BYTES:
            raise AutonomyDetailError("autonomy detail log exceeds its size limit")
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except ValueError as exc:
                raise AutonomyDetailError(
                    "autonomy detail log is malformed") from exc
            self._validate(payload, owner)
            out.append(payload)
        return out[-max(1, min(500, limit)):]

    def grants(self) -> list[dict[str, Any]]:
        return [r for r in self.records(limit=500) if r["kind"] == "grant"]

    def _grant_by_id(self, grant_id: str) -> dict[str, Any] | None:
        if not _canonical_uuid(grant_id):
            raise AutonomyDetailError("grant_id is invalid")
        for grant in self.grants():
            if grant["grant_id"] == grant_id:
                return grant
        return None

    def _usage(self) -> dict[str, int]:
        usage: dict[str, int] = {}
        for row in self.records(limit=500):
            if row["kind"] == "use":
                usage[row["grant_id"]] = usage.get(row["grant_id"], 0) + 1
        return usage

    def active_grant_for(self, operation: str, *,
                         now: datetime | None = None) -> dict[str, Any] | None:
        if operation not in PERMISSIONS:
            raise AutonomyDetailError("permission is not a §11.4 permission")
        moment = now or _now_dt()
        usage = self._usage()
        active = None
        for grant in self.grants():
            if grant["operation"] != operation:
                continue
            if grant_status(grant, usage.get(grant["grant_id"], 0),
                            now=moment) == "active":
                active = grant  # the latest recorded active grant wins
        return active

    def _validate(self, payload: Any, owner: str) -> None:
        if not isinstance(payload, dict):
            raise AutonomyDetailError("autonomy detail record is invalid")
        if payload.get("detail_version") != DETAIL_VERSION:
            raise AutonomyDetailError("autonomy detail version is unsupported")
        if payload.get("owner_entity_id") != owner:
            raise AutonomyDetailError(
                "autonomy detail owner does not match entity identity")
        kind = payload.get("kind")
        if kind == "grant":
            if set(payload) != _GRANT_FIELDS:
                raise AutonomyDetailError("autonomy grant fields are invalid")
            if not _canonical_uuid(payload.get("grant_id")):
                raise AutonomyDetailError("autonomy grant id is invalid")
            operation = payload.get("operation")
            if operation not in PERMISSIONS \
                    or PERMISSIONS[operation] != "ask":
                raise AutonomyDetailError(
                    "autonomy grants cover ask permissions only")
            scope = payload.get("scope")
            if not isinstance(scope, str) or not scope.strip() \
                    or len(scope) > MAX_SCOPE_CHARS:
                raise AutonomyDetailError("autonomy grant scope is invalid")
            if not _timestamp_ok(payload.get("issued_at")) \
                    or not _timestamp_ok(payload.get("expires_at")):
                raise AutonomyDetailError("autonomy grant timestamps are invalid")
            issued, expires = _parse(payload["issued_at"]), _parse(payload["expires_at"])
            if expires <= issued:
                raise AutonomyDetailError("autonomy grant expiry is invalid")
            if (expires - issued).total_seconds() \
                    > self.max_grant_hours() * 3600:
                raise AutonomyDetailError(
                    "autonomy grant lifetime exceeds its bound")
            actions = payload.get("max_actions")
            if isinstance(actions, bool) or not isinstance(actions, int) \
                    or not 1 <= actions <= MAX_GRANT_ACTIONS:
                raise AutonomyDetailError("autonomy grant max_actions is invalid")
        elif kind == "use":
            if set(payload) != _USE_FIELDS:
                raise AutonomyDetailError("autonomy use fields are invalid")
            if not _canonical_uuid(payload.get("record_id")) \
                    or not _canonical_uuid(payload.get("grant_id")):
                raise AutonomyDetailError("autonomy use ids are invalid")
            if not _timestamp_ok(payload.get("recorded_at")):
                raise AutonomyDetailError("autonomy use recorded_at is invalid")
        else:
            raise AutonomyDetailError("autonomy detail kind is invalid")

    def _append(self, record: dict[str, Any]) -> None:
        path = self.path()
        if path.is_symlink():
            raise AutonomyDetailError(
                "autonomy detail log must not be a symbolic link")
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
                if path.exists() and path.stat().st_size > MAX_LOG_BYTES:
                    raise AutonomyDetailError(
                        "autonomy detail log exceeds its size limit")
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(
                        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                lines = path.read_text(encoding="utf-8").splitlines()
                limit = self._limit()
                if len(lines) > limit:
                    tmp = path.with_suffix(path.suffix + ".tmp")
                    tmp.write_text("\n".join(lines[-limit:]) + "\n", encoding="utf-8")
                    os.replace(tmp, path)
            finally:
                lock.seek(0)
                if fcntl is not None:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                elif msvcrt is not None:
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


class AutonomyDetailBridge:
    """Surface the latest active §11.5 grant, content-bearing only.

    No session hook — grants and uses are written only by explicit
    calls, and nothing here executes an action.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._service = AutonomyDetailService(ctx)

    def hooks(self):
        return ()

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not _as_bool(
            self._ctx.get_config("autonomy_detail_enabled", False), False
        ):
            return []
        try:
            grants = self._service.grants()
            usage = self._service._usage()
        except (IdentityError, AutonomyDetailError, OSError):
            return []
        moment = _now_dt()
        active = [g for g in grants if grant_status(
            g, usage.get(g["grant_id"], 0), now=moment) == "active"]
        if not active:
            return []
        latest = active[-1]
        remaining = int(latest["max_actions"]) - usage.get(latest["grant_id"], 0)
        return [ContextItem(
            section="current_state",
            content=(
                f"Autonomy (§11 grant): {latest['operation']} allowed by "
                f"capability grant for {latest['scope']} until "
                f"{latest['expires_at']} ({remaining} actions left)"
            ),
            source="autonomy_detail",
            record_id=latest["grant_id"],
            priority=0.5,
            updated_at=_epoch(latest["issued_at"]),
        )]


__all__ = [
    "DETAIL_VERSION",
    "DEFAULT_LOG_PATH",
    "RISK_CLASSES",
    "PERMISSIONS",
    "PERMISSION_RISK_CLASS",
    "EXPECTED_REGISTRY_CLASS",
    "AutonomyDetailError",
    "AutonomyDetailService",
    "AutonomyDetailBridge",
    "class_disposition",
    "grant_status",
]
