"""N1 capability bus: versioned descriptors, registry, policy (W09).

Roadmap section 20 (Phase N1) asks for a shared capability bus rather
than a monolith: a versioned ``runeforge.capability.v1`` descriptor for
every native tool/service, a central registry that discovers actions
lazily, caches descriptors and expires them when services change, a
runtime permission policy that answers who may call which action on
whose data, on which device, with what human approval, and where the
outputs may travel, uniform error categories, provenance on every
result, and separately tracked long-running jobs with receipts and
idempotency keys. Each service keeps its own deployment, lock,
database and lifecycle; Hermes is the coordination shell.

This module is the first, contract-level slice of that bus, built
plugin-side in volmarr-core (ground rule: personal code in plugins,
not core). It is deliberately honest about its evidence stage:

- descriptors are validated strictly and malformed contracts are
  refused by name -- never repaired silently, never defaulted;
- the registry is in-memory plus lazy discovery from a directory of
  JSON descriptor files; expiry is enforced on every read;
- the permission policy is pure and fail-closed: anything it does not
  positively allow, it refuses with a named reason;
- result and error envelopes REQUIRE provenance (service, reviewed
  version, source reference, timestamp, confidentiality class) -- an
  anonymous magical tool result cannot be constructed through them;
- jobs are tracked records with idempotency keys; creating the same
  job twice returns the same record, never a duplicate;
- the three built-in seed descriptors describe tools that already
  exist in this fork (volmarr-astrology, volmarr-tarot,
  volmarr-seidr) at their plugin.yaml versions, availability
  ``contract-implemented`` -- NOT ``proven-by-live-probe``. No seed
  claims a live service, no descriptor here dispatches a call, and
  the section 20 acceptance gate (three real heterogeneous apps
  participating live) is NOT claimed by this slice; it is recorded
  as a remainder in the W09 implementation record.

No network, no subprocess, no mutation outside the caller's own
registry instance.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA = "runeforge.capability.v1"

TRANSPORTS = frozenset(
    {"loopback-http", "unix-socket", "in-process", "subprocess", "authenticated-remote"}
)
AUTH_MODES = frozenset({"none", "scoped", "owner-only"})
PRIVACY_CLASSES = frozenset({"public", "shared", "local-private"})
AVAILABILITY_STATES = frozenset(
    {"proven-by-live-probe", "contract-implemented", "design-only", "unknown"}
)

# Uniform error categories, roadmap section 20, verbatim.
ERROR_CATEGORIES = (
    "unavailable",
    "unauthorized",
    "validation_failure",
    "version_mismatch",
    "resource_exhausted",
    "timeout",
    "partial_result",
    "completed",
)

# Actions that change the world; they always need human approval.
WRITE_ACTIONS = frozenset({"write", "execute", "publish", "send", "delete"})

# Where output may travel, least to most exposed.
DESTINATIONS = frozenset({"local", "shared", "cloud", "public"})

_PRIVACY_TRAVEL = {
    "public": DESTINATIONS,
    "shared": frozenset({"local", "shared"}),
    "local-private": frozenset({"local"}),
}

DEFAULT_TTL_S = 3600
MAX_TIMEOUT_MS = 600_000

REQUIRED_FIELDS = (
    "schema",
    "service",
    "version",
    "owner",
    "actions",
    "transport",
    "auth",
    "side_effects",
    "privacy_classes",
    "availability",
    "timeout_ms",
)


class CapabilityError(Exception):
    """Named, honest capability-bus failure."""

    def __init__(self, name: str, detail: str) -> None:
        super().__init__(detail)
        self.name = name
        self.detail = detail


def validate_descriptor(descriptor: Any) -> list[str]:
    """Return the named problems with a descriptor ([] = valid)."""
    problems: list[str] = []
    if not isinstance(descriptor, dict):
        return ["descriptor_not_an_object"]
    for field in REQUIRED_FIELDS:
        if field not in descriptor:
            problems.append(f"missing_field:{field}")
    if problems:
        return problems
    if descriptor["schema"] != SCHEMA:
        problems.append(f"schema_mismatch:{descriptor['schema']}")
    if not isinstance(descriptor["service"], str) or not descriptor["service"].strip():
        problems.append("service_empty")
    if not isinstance(descriptor["version"], str) or not descriptor["version"].strip():
        problems.append("version_empty")
    if not isinstance(descriptor["owner"], str) or not descriptor["owner"].strip():
        problems.append("owner_empty")
    actions = descriptor["actions"]
    if (
        not isinstance(actions, list)
        or not actions
        or not all(isinstance(a, str) and a.strip() for a in actions)
    ):
        problems.append("actions_invalid")
    elif len(set(actions)) != len(actions):
        problems.append("actions_duplicated")
    if descriptor["transport"] not in TRANSPORTS:
        problems.append(f"transport_unknown:{descriptor['transport']}")
    if descriptor["auth"] not in AUTH_MODES:
        problems.append(f"auth_unknown:{descriptor['auth']}")
    if not isinstance(descriptor["side_effects"], bool):
        problems.append("side_effects_not_bool")
    classes = descriptor["privacy_classes"]
    if (
        not isinstance(classes, list)
        or not classes
        or not all(c in PRIVACY_CLASSES for c in classes)
    ):
        problems.append("privacy_classes_invalid")
    if descriptor["availability"] not in AVAILABILITY_STATES:
        problems.append(f"availability_unknown:{descriptor['availability']}")
    timeout = descriptor["timeout_ms"]
    if (
        not isinstance(timeout, int)
        or isinstance(timeout, bool)
        or timeout <= 0
        or timeout > MAX_TIMEOUT_MS
    ):
        problems.append("timeout_ms_out_of_range")
    devices = descriptor.get("devices")
    if devices is not None and (
        not isinstance(devices, list)
        or not all(isinstance(d, str) and d.strip() for d in devices)
    ):
        problems.append("devices_invalid")
    ttl = descriptor.get("ttl_s")
    if ttl is not None and (
        not isinstance(ttl, int) or isinstance(ttl, bool) or ttl <= 0
    ):
        problems.append("ttl_s_invalid")
    return problems


def require_valid(descriptor: Any) -> dict:
    problems = validate_descriptor(descriptor)
    if problems:
        raise CapabilityError("validation_failure", "; ".join(problems))
    return descriptor


class CapabilityRegistry:
    """In-memory descriptor registry with enforced expiry."""

    def __init__(self) -> None:
        self._entries: dict[str, dict[str, Any]] = {}

    def register(self, descriptor: dict, *, now: float) -> dict:
        require_valid(descriptor)
        ttl = descriptor.get("ttl_s", DEFAULT_TTL_S)
        entry = {
            "descriptor": dict(descriptor),
            "registered_at": now,
            "expires_at": now + ttl,
        }
        self._entries[descriptor["service"]] = entry
        return entry

    def get(self, service: str, *, now: float) -> dict | None:
        entry = self._entries.get(service)
        if entry is None:
            return None
        if now >= entry["expires_at"]:
            del self._entries[service]
            return None
        return entry["descriptor"]

    def services(self, *, now: float) -> list[str]:
        return sorted(s for s in list(self._entries) if self.get(s, now=now) is not None)

    def discover(self, directory: str | Path, *, now: float) -> dict[str, Any]:
        """Lazily load *.json descriptors; malformed files are refused
        by name in the returned problems, never silently skipped."""
        root = Path(directory)
        record: dict[str, Any] = {"loaded": [], "problems": []}
        if not root.is_dir():
            record["problems"].append(f"descriptor_directory_missing:{root}")
            return record
        for path in sorted(root.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                record["problems"].append(f"{path.name}:unreadable:{exc}")
                continue
            problems = validate_descriptor(payload)
            if problems:
                record["problems"].append(f"{path.name}:" + ";".join(problems))
                continue
            self.register(payload, now=now)
            record["loaded"].append(payload["service"])
        return record


def authorize(
    descriptor: dict | None,
    *,
    caller: str,
    action: str,
    data_owner: str,
    data_class: str,
    destination: str,
    device: str | None = None,
    approved: bool = False,
) -> dict[str, Any]:
    """The section 20 permission policy, pure and fail-closed.

    Answers: who (caller) may call which action on whose data
    (data_owner), on which device, with what human approval, and
    where outputs may travel (destination). Every refusal names its
    reason; an absent descriptor or unknown value is a refusal.
    """
    reasons: list[str] = []
    if descriptor is None:
        return {"allowed": False, "reasons": ["service_unavailable"]}
    if action not in descriptor["actions"]:
        reasons.append(f"action_not_offered:{action}")
    if data_class not in PRIVACY_CLASSES:
        reasons.append(f"data_class_unknown:{data_class}")
    elif data_class not in descriptor["privacy_classes"]:
        reasons.append(f"data_class_not_declared:{data_class}")
    if destination not in DESTINATIONS:
        reasons.append(f"destination_unknown:{destination}")
    elif data_class in _PRIVACY_TRAVEL and destination not in _PRIVACY_TRAVEL[data_class]:
        reasons.append(f"privacy_travel_refused:{data_class}->{destination}")
    if descriptor["auth"] == "owner-only" and caller != descriptor["owner"]:
        reasons.append("owner_only_service")
    if data_owner != caller and descriptor["auth"] != "scoped":
        reasons.append("cross_owner_requires_scoped_auth")
    if data_owner != caller and descriptor["auth"] == "scoped" and not approved:
        reasons.append("cross_owner_requires_approval")
    if action in WRITE_ACTIONS and not approved:
        reasons.append("write_action_requires_approval")
    if descriptor["side_effects"] and action not in ("read", "propose") and not approved:
        reasons.append("side_effect_service_requires_approval")
    devices = descriptor.get("devices")
    if devices is not None and device not in devices:
        reasons.append(f"device_not_allowed:{device}")
    return {"allowed": not reasons, "reasons": reasons}


def result_envelope(
    descriptor: dict,
    *,
    outputs: Any,
    source_ref: str,
    recorded_at: str,
    confidentiality: str,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """A result with mandatory provenance; anonymous results refused."""
    require_valid(descriptor)
    if not source_ref or not str(source_ref).strip():
        raise CapabilityError("validation_failure", "source_ref_required")
    if not recorded_at or not str(recorded_at).strip():
        raise CapabilityError("validation_failure", "recorded_at_required")
    if confidentiality not in PRIVACY_CLASSES:
        raise CapabilityError(
            "validation_failure", f"confidentiality_unknown:{confidentiality}"
        )
    if confidentiality not in descriptor["privacy_classes"]:
        raise CapabilityError(
            "validation_failure", f"confidentiality_not_declared:{confidentiality}"
        )
    return {
        "schema": SCHEMA,
        "status": "completed",
        "service": descriptor["service"],
        "version": descriptor["version"],
        "outputs": outputs,
        "warnings": list(warnings or []),
        "provenance": {
            "service": descriptor["service"],
            "version": descriptor["version"],
            "owner": descriptor["owner"],
            "source_ref": source_ref,
            "recorded_at": recorded_at,
            "confidentiality": confidentiality,
        },
    }


def error_envelope(
    descriptor: dict | None,
    *,
    category: str,
    detail: str,
    recorded_at: str,
) -> dict[str, Any]:
    if category not in ERROR_CATEGORIES:
        raise CapabilityError("validation_failure", f"error_category_unknown:{category}")
    return {
        "schema": SCHEMA,
        "status": category,
        "service": descriptor["service"] if descriptor else None,
        "version": descriptor["version"] if descriptor else None,
        "detail": detail,
        "provenance": {
            "recorded_at": recorded_at,
            "confidentiality": "local-private",
        },
    }


class JobBook:
    """Long-running work: tracked jobs with idempotency keys."""

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._by_key: dict[str, str] = {}
        self._seq = 0

    def create(
        self, descriptor: dict, *, action: str, idempotency_key: str, now: float
    ) -> dict[str, Any]:
        require_valid(descriptor)
        if action not in descriptor["actions"]:
            raise CapabilityError("validation_failure", f"action_not_offered:{action}")
        if not idempotency_key or not idempotency_key.strip():
            raise CapabilityError("validation_failure", "idempotency_key_required")
        existing = self._by_key.get(idempotency_key)
        if existing is not None:
            return self._jobs[existing]
        self._seq += 1
        job = {
            "job_id": f"job-{self._seq:04d}",
            "service": descriptor["service"],
            "action": action,
            "idempotency_key": idempotency_key,
            "status": "created",
            "created_at": now,
            "receipt": {
                "service": descriptor["service"],
                "version": descriptor["version"],
                "idempotency_key": idempotency_key,
            },
        }
        self._jobs[job["job_id"]] = job
        self._by_key[idempotency_key] = job["job_id"]
        return job

    def transition(self, job_id: str, status: str) -> dict[str, Any]:
        job = self._jobs.get(job_id)
        if job is None:
            raise CapabilityError("unavailable", f"job_unknown:{job_id}")
        allowed = {
            "created": {"running", "cancelled"},
            "running": {"completed", "failed", "cancelled"},
            "completed": set(),
            "failed": set(),
            "cancelled": set(),
        }
        if status not in allowed[job["status"]]:
            raise CapabilityError(
                "validation_failure",
                f"job_transition_refused:{job['status']}->{status}",
            )
        job["status"] = status
        return job

    def get(self, job_id: str) -> dict[str, Any] | None:
        return self._jobs.get(job_id)


# Built-in seed descriptors: tools that already exist in this fork.
# Versions are the plugin.yaml versions at W09 (2026-11-08); adapter
# paths are stat-checked by builtin_status(). Availability is
# contract-implemented, honestly -- the engines behind them are local
# checkouts resolved per profile, so no live probe is claimed here.
BUILTIN_DESCRIPTORS: tuple[dict, ...] = (
    {
        "schema": SCHEMA,
        "service": "volmarr-astrology",
        "version": "0.7.0",
        "owner": "volmarr",
        "actions": ["calculate_astrology"],
        "transport": "subprocess",
        "auth": "scoped",
        "side_effects": False,
        "privacy_classes": ["public", "shared", "local-private"],
        "availability": "contract-implemented",
        "timeout_ms": 30000,
        "adapter_path": "plugins/volmarr-astrology/plugin.yaml",
    },
    {
        "schema": SCHEMA,
        "service": "volmarr-tarot",
        "version": "0.3.0",
        "owner": "volmarr",
        "actions": ["draw_tarot"],
        "transport": "subprocess",
        "auth": "scoped",
        "side_effects": False,
        "privacy_classes": ["public", "shared", "local-private"],
        "availability": "contract-implemented",
        "timeout_ms": 30000,
        "adapter_path": "plugins/volmarr-tarot/plugin.yaml",
    },
    {
        "schema": SCHEMA,
        "service": "volmarr-seidr",
        "version": "0.4.0",
        "owner": "volmarr",
        "actions": ["compose_seidr"],
        "transport": "subprocess",
        "auth": "scoped",
        "side_effects": False,
        "privacy_classes": ["public", "shared", "local-private"],
        "availability": "contract-implemented",
        "timeout_ms": 30000,
        "adapter_path": "plugins/volmarr-seidr/plugin.yaml",
    },
)


def repo_root(module_file: str | Path | None = None) -> Path:
    """Repository root for this plugin (plugins/volmarr-core -> root)."""
    return Path(module_file or __file__).resolve().parents[2]


def builtin_status(root: Path | None = None) -> dict[str, Any]:
    """Validate the seed descriptors and stat-check their adapters."""
    base = root or repo_root()
    problems: list[str] = []
    rows: list[dict[str, Any]] = []
    for descriptor in BUILTIN_DESCRIPTORS:
        found = validate_descriptor(descriptor)
        adapter = descriptor.get("adapter_path")
        if adapter and not (base / adapter).is_file():
            found.append(f"adapter_missing:{adapter}")
        problems.extend(f"{descriptor['service']}:{p}" for p in found)
        rows.append(
            {
                "service": descriptor["service"],
                "version": descriptor["version"],
                "actions": list(descriptor["actions"]),
                "availability": descriptor["availability"],
                "adapter_present": bool(adapter) and (base / adapter).is_file(),
                "problems": found,
            }
        )
    return {
        "schema": SCHEMA,
        "status": "ok" if not problems else "problems",
        "service_count": len(rows),
        "services": rows,
        "problems": problems,
    }
