"""Autonomy policy engine (Emergent Agency Phase 5, roadmap §12).

A deterministic gate between wanting something and doing something —
the roadmap's most important safety and sovereignty boundary. Two
durable files under the stable entity identity:

- ``entity/autonomy_policy.yaml`` — the human-authoritative policy.
  The runtime reads it and, after create-once seeding, *never writes
  it*: no method in this module alters an existing policy file, and
  policy changes arrive only by direct human edit (or a later
  explicit operator CLI). The capability registry lives here, so a
  risk class is never inferred from a tool/action name at runtime —
  an action with no registry entry is denied as unknown.
- ``entity/autonomy_state.json`` — runtime state the autonomy
  service may update: cycle counters, budget consumption, the last
  autonomous action, consecutive failures, and circuit-breaker state.

Decisions are pure functions of (proposal, policy, state): the LLM
never generates a :class:`PolicyDecision`. The circuit breaker can
only reduce authority — once tripped it stays tripped until a human
edits the state file; no code path here untrips it, and a success
never clears a trip (it only resets the consecutive-failure count
while the breaker is untripped).
"""

from __future__ import annotations

import json
import os
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from hermes_constants import get_hermes_home, mkdir_under_hermes_home
from utils import atomic_json_write, atomic_yaml_write

from .agency_contracts import (
    ActionProposal,
    ActionResult,
    AgencyContractError,
    PolicyDecision,
)
from .context_packet import ContextItem
from .identity import IdentityError, IdentityStore, _as_bool

AUTONOMY_POLICY_VERSION = 1
AUTONOMY_STATE_VERSION = 1
DEFAULT_POLICY_PATH = Path("entity") / "autonomy_policy.yaml"
DEFAULT_STATE_PATH = Path("entity") / "autonomy_state.json"
MAX_POLICY_BYTES = 1024 * 1024
MAX_STATE_BYTES = 1024 * 1024
MAX_CAPABILITIES = 200
MAX_ALLOWLIST = 100

AUTONOMY_MODES = frozenset({"off", "observe", "propose", "local", "bounded"})
COST_UNITS = {"none": 0, "low": 1, "medium": 3, "high": 8}
_SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

# Create-once seed capabilities (roadmap §12 registry examples). The
# human may edit this registry in the policy file at any time; the
# runtime never does.
_DEFAULT_CAPABILITIES: dict[str, dict[str, Any]] = {
    "world_get": {"class": 0, "network": "loopback", "reversible": True},
    "goal_update": {"class": 2, "domain": "entity", "reversible": True},
    "github_push": {"class": 3, "domain": "external", "reversible": False},
}

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


class AutonomyError(RuntimeError):
    """The autonomy policy/state cannot be safely read or changed."""


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _timestamp_ok(value: Any, *, empty: bool = False) -> bool:
    if empty and value == "":
        return True
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


class AutonomyStore:
    """Human-authoritative policy (read-only) + runtime state store."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("autonomy_enabled", True), True
        )

    def _resolve(self, key: str, default: Path) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(key, str(default))))
        if configured.is_absolute():
            configured = default
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / default
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise AutonomyError("autonomy path resolves outside the active profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    def policy_path(self) -> Path:
        return self._resolve("autonomy_policy_path", DEFAULT_POLICY_PATH)

    def state_path(self) -> Path:
        return self._resolve("autonomy_state_path", DEFAULT_STATE_PATH)

    # -- lifecycle ------------------------------------------------------
    def ensure(self) -> dict[str, Any]:
        """Seed policy (create-once) and state; return the state.

        Seeding is the only policy write this module ever performs,
        and only when no policy file exists yet. An existing policy
        file is validated and left byte-for-byte untouched.
        """
        owner = self._identity.ensure().entity_id
        policy_path = self.policy_path()
        with self._lock(policy_path):
            if policy_path.exists():
                self._read_policy_unlocked(policy_path, owner)
            else:
                self._write_policy(policy_path, self._default_policy(owner))
        state_path = self.state_path()
        with self._lock(state_path):
            if state_path.exists():
                return self._read_state_unlocked(state_path, owner)
            data = self._default_state(owner)
            self._write_state(state_path, data)
            return data

    @staticmethod
    def _default_policy(owner: str) -> dict[str, Any]:
        return {
            "autonomy_version": AUTONOMY_POLICY_VERSION,
            "owner_entity_id": owner,
            "policy_version": 1,
            "mode": "observe",
            "capabilities": {k: dict(v) for k, v in _DEFAULT_CAPABILITIES.items()},
            "bounded_allowlist": [],
            "max_autonomous_actions": 20,
            "cost_budget": 20,
            "failure_threshold": 3,
        }

    @staticmethod
    def _default_state(owner: str) -> dict[str, Any]:
        return {
            "autonomy_state_version": AUTONOMY_STATE_VERSION,
            "owner_entity_id": owner,
            "updated_at": _fmt(_now_dt()),
            "proposals_considered": 0,
            "decisions_allow": 0,
            "decisions_confirmation": 0,
            "decisions_deny": 0,
            "actions_executed": 0,
            "actions_failed": 0,
            "cost_spent": 0,
            "consecutive_failures": 0,
            "circuit_breaker_tripped": False,
            "paused": False,
            "pause_reason": "",
            "last_action": None,
        }

    def policy(self) -> dict[str, Any]:
        owner = self._identity.read().entity_id
        path = self.policy_path()
        with self._lock(path):
            return self._read_policy_unlocked(path, owner)

    def state(self) -> dict[str, Any]:
        owner = self._identity.read().entity_id
        path = self.state_path()
        with self._lock(path):
            return self._read_state_unlocked(path, owner)

    # -- the deterministic gate -------------------------------------------
    def evaluate(
        self, proposal: ActionProposal, *, now: datetime | None = None
    ) -> PolicyDecision:
        """Decide one proposal deterministically. Writes nothing."""
        if not isinstance(proposal, ActionProposal):
            raise AutonomyError("proposal must be an ActionProposal contract record")
        owner = self._identity.read().entity_id
        if proposal.owner_entity_id != owner:
            raise AutonomyError("proposal owner does not match entity identity")
        moment = now or _now_dt()
        policy = self.policy()
        state = self.state()
        cost = COST_UNITS[proposal.estimated_cost]
        budget_remaining = (
            int(state["actions_executed"]) < int(policy["max_autonomous_actions"])
            and int(state["cost_spent"]) + cost <= int(policy["cost_budget"])
        )

        def decide(decision: str, reason: str, risk: int) -> PolicyDecision:
            return PolicyDecision(
                proposal_id=proposal.proposal_id,
                owner_entity_id=owner,
                decision=decision,
                reason_code=reason,
                risk_class=risk,
                budget_remaining=budget_remaining,
                policy_version=int(policy["policy_version"]),
                decided_at=_fmt(moment),
            )

        if state["paused"] or state["circuit_breaker_tripped"]:
            return decide("deny", "circuit_breaker_paused", proposal.risk_class)
        if proposal.expires_at and _parse(proposal.expires_at) <= moment:
            return decide("deny", "expired_proposal", proposal.risk_class)
        capability = policy["capabilities"].get(proposal.action)
        if capability is None:
            return decide("deny", "unknown_capability", proposal.risk_class)
        risk = int(capability["class"])
        mode = str(policy["mode"])
        if mode == "off":
            return decide("deny", "autonomy_off", risk)
        if mode == "observe":
            return decide("deny", "mode_observe_no_execution", risk)
        if mode == "propose":
            return decide("require_confirmation", "mode_propose_requires_confirmation", risk)
        # local / bounded: classes 4-5 never auto-run (roadmap §12).
        if risk >= 4:
            return decide("deny", "risk_class_never_auto", risk)
        if risk >= 2:
            allowlisted = (
                mode == "bounded" and proposal.action in policy["bounded_allowlist"]
            )
            if not allowlisted:
                reason = (
                    "persistent_local_requires_confirmation"
                    if risk == 2
                    else "external_requires_confirmation"
                )
                return decide("require_confirmation", reason, risk)
        if not budget_remaining:
            return decide("deny", "budget_exhausted", risk)
        reason = "allowed_bounded_allowlist" if (
            mode == "bounded" and risk >= 2
        ) else "allowed_local_action"
        return decide("allow", reason, risk)

    # -- runtime state recording (never policy) ---------------------------
    def record_decision(self, decision: PolicyDecision) -> dict[str, Any]:
        if not isinstance(decision, PolicyDecision):
            raise AutonomyError("decision must be a PolicyDecision contract record")
        owner = self._identity.read().entity_id
        if decision.owner_entity_id != owner:
            raise AutonomyError("decision owner does not match entity identity")
        path = self.state_path()
        with self._lock(path):
            data = self._read_state_unlocked(path, owner)
            data["proposals_considered"] = int(data["proposals_considered"]) + 1
            key = {
                "allow": "decisions_allow",
                "require_confirmation": "decisions_confirmation",
                "deny": "decisions_deny",
            }[decision.decision]
            data[key] = int(data[key]) + 1
            data["updated_at"] = _fmt(_now_dt())
            self._write_state(path, data)
            return data

    def record_result(
        self, result: ActionResult, *, estimated_cost: str = "none"
    ) -> dict[str, Any]:
        """Fold one action outcome into state; may trip the breaker.

        Success (breaker untripped) resets consecutive failures and
        consumes budget. Failure increments the failure streak; at
        the policy's failure threshold the circuit breaker trips and
        autonomy pauses. A trip is never cleared here.
        """
        if not isinstance(result, ActionResult):
            raise AutonomyError("result must be an ActionResult contract record")
        if estimated_cost not in COST_UNITS:
            raise AutonomyError("estimated_cost is invalid")
        owner = self._identity.read().entity_id
        if result.owner_entity_id != owner:
            raise AutonomyError("result owner does not match entity identity")
        policy = self.policy()
        path = self.state_path()
        with self._lock(path):
            data = self._read_state_unlocked(path, owner)
            data["last_action"] = {
                "proposal_id": result.proposal_id,
                "status": result.status,
                "completed_at": result.completed_at,
            }
            if result.status == "succeeded":
                data["actions_executed"] = int(data["actions_executed"]) + 1
                data["cost_spent"] = int(data["cost_spent"]) + COST_UNITS[estimated_cost]
                if not data["circuit_breaker_tripped"]:
                    data["consecutive_failures"] = 0
            elif result.status == "failed":
                data["actions_failed"] = int(data["actions_failed"]) + 1
                data["consecutive_failures"] = int(data["consecutive_failures"]) + 1
                if (
                    not data["circuit_breaker_tripped"]
                    and int(data["consecutive_failures"]) >= int(policy["failure_threshold"])
                ):
                    data["circuit_breaker_tripped"] = True
                    data["paused"] = True
                    data["pause_reason"] = "circuit_breaker_consecutive_failures"
            data["updated_at"] = _fmt(_now_dt())
            self._write_state(path, data)
            return data

    def trip_circuit_breaker(self, reason: str) -> dict[str, Any]:
        """Pause autonomy now (operator/service call). Never untrips."""
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 200:
            raise AutonomyError("pause reason is invalid")
        owner = self._identity.read().entity_id
        path = self.state_path()
        with self._lock(path):
            data = self._read_state_unlocked(path, owner)
            data["circuit_breaker_tripped"] = True
            data["paused"] = True
            data["pause_reason"] = reason.strip()
            data["updated_at"] = _fmt(_now_dt())
            self._write_state(path, data)
            return data

    # -- reading / validation ---------------------------------------------
    def _read_policy_unlocked(self, path: Path, owner: str) -> dict[str, Any]:
        if path.is_symlink():
            raise AutonomyError("autonomy policy must not be a symbolic link")
        if not path.is_file():
            raise AutonomyError("autonomy policy file is missing")
        try:
            if path.stat().st_size > MAX_POLICY_BYTES:
                raise AutonomyError("autonomy policy exceeds its size limit")
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise AutonomyError("autonomy policy is unreadable or malformed") from exc
        if not isinstance(payload, dict):
            raise AutonomyError("autonomy policy document must be a mapping")
        allowed = {
            "autonomy_version", "owner_entity_id", "policy_version", "mode",
            "capabilities", "bounded_allowlist", "max_autonomous_actions",
            "cost_budget", "failure_threshold",
        }
        if set(payload) != allowed:
            raise AutonomyError("autonomy policy fields are invalid")
        version = payload.get("autonomy_version")
        if isinstance(version, bool) or version != AUTONOMY_POLICY_VERSION:
            raise AutonomyError("autonomy policy version is unsupported")
        if payload.get("owner_entity_id") != owner:
            raise AutonomyError("autonomy policy owner does not match entity identity")
        pv = payload.get("policy_version")
        if not _is_int(pv) or pv < 1:
            raise AutonomyError("autonomy policy_version is invalid")
        if payload.get("mode") not in AUTONOMY_MODES:
            raise AutonomyError("autonomy mode is invalid")
        capabilities = payload.get("capabilities")
        if not isinstance(capabilities, dict) or len(capabilities) > MAX_CAPABILITIES:
            raise AutonomyError("autonomy capabilities mapping is invalid")
        for action, entry in capabilities.items():
            if not isinstance(action, str) or not _SLUG.match(action):
                raise AutonomyError("autonomy capability name is invalid")
            if not isinstance(entry, dict) or "class" not in entry or not set(entry) <= {
                "class", "network", "domain", "reversible",
            }:
                raise AutonomyError("autonomy capability entry is invalid")
            if not _is_int(entry["class"]) or not 0 <= entry["class"] <= 5:
                raise AutonomyError("autonomy capability class is invalid")
            if "reversible" in entry and not isinstance(entry["reversible"], bool):
                raise AutonomyError("autonomy capability reversible is invalid")
            for text_key in ("network", "domain"):
                if text_key in entry and (
                    not isinstance(entry[text_key], str) or len(entry[text_key]) > 100
                ):
                    raise AutonomyError("autonomy capability entry is invalid")
        allowlist = payload.get("bounded_allowlist")
        if (
            not isinstance(allowlist, list)
            or len(allowlist) > MAX_ALLOWLIST
            or any(not isinstance(a, str) or a not in capabilities for a in allowlist)
        ):
            raise AutonomyError("autonomy bounded_allowlist is invalid")
        for field, low, high in (
            ("max_autonomous_actions", 0, 10000),
            ("cost_budget", 0, 100000),
            ("failure_threshold", 1, 20),
        ):
            value = payload.get(field)
            if not _is_int(value) or not low <= value <= high:
                raise AutonomyError(f"autonomy policy {field} is invalid")
        return payload

    def _read_state_unlocked(self, path: Path, owner: str) -> dict[str, Any]:
        if path.is_symlink():
            raise AutonomyError("autonomy state must not be a symbolic link")
        if not path.is_file():
            raise AutonomyError("autonomy state file is missing")
        try:
            if path.stat().st_size > MAX_STATE_BYTES:
                raise AutonomyError("autonomy state exceeds its size limit")
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as exc:
            raise AutonomyError("autonomy state is unreadable or malformed") from exc
        if not isinstance(payload, dict):
            raise AutonomyError("autonomy state document must be a mapping")
        allowed = {
            "autonomy_state_version", "owner_entity_id", "updated_at",
            "proposals_considered", "decisions_allow", "decisions_confirmation",
            "decisions_deny", "actions_executed", "actions_failed", "cost_spent",
            "consecutive_failures", "circuit_breaker_tripped", "paused",
            "pause_reason", "last_action",
        }
        if set(payload) != allowed:
            raise AutonomyError("autonomy state fields are invalid")
        version = payload.get("autonomy_state_version")
        if isinstance(version, bool) or version != AUTONOMY_STATE_VERSION:
            raise AutonomyError("autonomy state version is unsupported")
        if payload.get("owner_entity_id") != owner:
            raise AutonomyError("autonomy state owner does not match entity identity")
        if not _timestamp_ok(payload.get("updated_at")):
            raise AutonomyError("autonomy state updated_at is invalid")
        for field in (
            "proposals_considered", "decisions_allow", "decisions_confirmation",
            "decisions_deny", "actions_executed", "actions_failed", "cost_spent",
            "consecutive_failures",
        ):
            value = payload.get(field)
            if not _is_int(value) or value < 0:
                raise AutonomyError(f"autonomy state {field} is invalid")
        for field in ("circuit_breaker_tripped", "paused"):
            if not isinstance(payload.get(field), bool):
                raise AutonomyError(f"autonomy state {field} is invalid")
        if payload["paused"] and not payload["circuit_breaker_tripped"]:
            # Pausing only ever comes from the breaker in this slice.
            if payload.get("pause_reason") == "":
                raise AutonomyError("autonomy state pause_reason is invalid")
        reason = payload.get("pause_reason")
        if not isinstance(reason, str) or len(reason) > 200:
            raise AutonomyError("autonomy state pause_reason is invalid")
        last = payload.get("last_action")
        if last is not None:
            if not isinstance(last, dict) or set(last) != {
                "proposal_id", "status", "completed_at",
            }:
                raise AutonomyError("autonomy state last_action is invalid")
            if last["status"] not in ("succeeded", "failed", "denied", "skipped"):
                raise AutonomyError("autonomy state last_action is invalid")
            if not _timestamp_ok(last["completed_at"]):
                raise AutonomyError("autonomy state last_action is invalid")
        return payload

    @staticmethod
    def _write_policy(path: Path, data: dict[str, Any]) -> None:
        atomic_yaml_write(path, data, sort_keys=False, create_mode=0o600)

    @staticmethod
    def _write_state(path: Path, data: dict[str, Any]) -> None:
        atomic_json_write(path, data, mode=0o600)

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


class AutonomyBridge:
    """Seed autonomy policy/state at session start; offer its packet.

    The bridge never executes an action and never edits policy; it
    only surfaces the current gate status, failing open throughout.
    """

    def __init__(self, ctx) -> None:
        self._store = AutonomyStore(ctx)

    def hooks(self):
        return (("on_session_start", self.on_session_start),)

    def on_session_start(self, **_: Any) -> None:
        if not self._store.enabled():
            return
        try:
            self._store.ensure()
        except (IdentityError, AutonomyError, OSError):
            return

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not self._store.enabled():
            return []
        try:
            policy = self._store.policy()
            state = self._store.state()
        except (IdentityError, AutonomyError, OSError):
            return []
        # Content-bearing only (the packet contract every prior slice
        # keeps: a fresh, execution-incapable profile contributes
        # nothing). The gate status matters when autonomy can execute
        # (local/bounded) or when the breaker has reduced authority.
        if not (
            state["circuit_breaker_tripped"]
            or state["paused"]
            or policy["mode"] in ("local", "bounded")
        ):
            return []
        remaining = max(
            0, int(policy["max_autonomous_actions"]) - int(state["actions_executed"])
        )
        breaker = "tripped" if state["circuit_breaker_tripped"] else "clear"
        return [ContextItem(
            section="current_state",
            content=(
                f"Autonomy: mode {policy['mode']} (policy v{policy['policy_version']}); "
                f"circuit breaker {breaker}; {remaining} autonomous actions remaining"
            ),
            source="autonomy",
            record_id=str(policy["policy_version"]),
            priority=0.5,
            updated_at=_parse(state["updated_at"]).timestamp(),
        )]


__all__ = [
    "AUTONOMY_POLICY_VERSION", "AUTONOMY_STATE_VERSION",
    "DEFAULT_POLICY_PATH", "DEFAULT_STATE_PATH", "AUTONOMY_MODES", "COST_UNITS",
    "AutonomyError", "AutonomyStore", "AutonomyBridge",
]
