"""N2 task handoffs + publish guard, shared with Mythic Eng. (W10).

Roadmap section 21 (Phase N2) imports Mythic Engineering as an
explicit workflow -- natural-language intent, invariants, small
executable tasks, code/test/verify, evidence and ledger -- and
section 49 asks Hermes and the Mythic Agent Coder CLI to share a
versioned workflow schema and task handoffs while keeping one
write authority per repository checkout. The W10 gate (section
30) is "permissioned, replay-safe workflows".

This module is that shared handoff record as data + validation,
plugin-side, built on the W09 capability bus:

- a handoff is intent, invariants, tasks, evidence and a ledger,
  validated strictly: malformed records are refused by name,
  never repaired silently;
- a valid handoff travels in a capability-bus result envelope, so
  provenance (service, version, source, time, confidentiality)
  is mandatory, exactly as section 20 requires;
- publishing resolves through the capability policy: a publish
  action with no explicit approval flag is REFUSED by name
  (write actions and side-effect services always need approval),
  and privacy travel rules still apply on top of approval -- a
  local-private payload cannot be approved into a public
  destination. No publish is performed here; the guard only
  decides, and a refusal is a tested contract.
"""

from __future__ import annotations

from typing import Any

from .capability_bus import authorize, result_envelope

SCHEMA = "runeforge.task-handoff.v1"

DESCRIPTOR = {
    "schema": "runeforge.capability.v1",
    "service": "volmarr-task-handoff",
    "version": "0.26.0",
    "owner": "volmarr",
    "actions": ["read", "propose", "publish"],
    "transport": "in-process",
    "auth": "scoped",
    "side_effects": True,
    "privacy_classes": ["public", "shared", "local-private"],
    "availability": "contract-implemented",
    "timeout_ms": 2000,
}

TASK_STATUSES = frozenset({"planned", "running", "done", "blocked"})
REQUIRED_FIELDS = (
    "schema", "handoff_id", "repo", "intent",
    "invariants", "tasks", "evidence", "ledger",
)


class HandoffError(Exception):
    """Named, honest handoff / publish-guard failure."""

    def __init__(self, name: str, detail: str) -> None:
        super().__init__(detail)
        self.name = name
        self.detail = detail


def _nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_handoff(record: Any) -> list[str]:
    """Return the named problems with a handoff ([] = valid)."""
    problems: list[str] = []
    if not isinstance(record, dict):
        return ["handoff_not_an_object"]
    for field in REQUIRED_FIELDS:
        if field not in record:
            problems.append(f"missing_field:{field}")
    if problems:
        return problems
    if record["schema"] != SCHEMA:
        problems.append(f"schema_mismatch:{record['schema']}")
    if not _nonempty_str(record["handoff_id"]):
        problems.append("handoff_id_empty")
    if not _nonempty_str(record["repo"]):
        problems.append("repo_empty")
    if not _nonempty_str(record["intent"]):
        problems.append("intent_empty")
    invariants = record["invariants"]
    if (
        not isinstance(invariants, list)
        or not invariants
        or not all(_nonempty_str(item) for item in invariants)
    ):
        problems.append("invariants_invalid")
    tasks = record["tasks"]
    if not isinstance(tasks, list) or not tasks:
        problems.append("tasks_invalid")
    else:
        seen_ids: set[str] = set()
        for task in tasks:
            if not isinstance(task, dict):
                problems.append("task_not_an_object")
                continue
            task_id = task.get("id")
            if not _nonempty_str(task_id):
                problems.append("task_id_empty")
            elif task_id in seen_ids:
                problems.append(f"task_id_duplicated:{task_id}")
            else:
                seen_ids.add(task_id)
            if not _nonempty_str(task.get("title")):
                problems.append(f"task_title_empty:{task_id}")
            if task.get("status") not in TASK_STATUSES:
                problems.append(
                    f"task_status_unknown:{task_id}:{task.get('status')}")
    evidence = record["evidence"]
    if not isinstance(evidence, list):
        problems.append("evidence_invalid")
    else:
        for item in evidence:
            if not isinstance(item, dict) or not _nonempty_str(item.get("kind")):
                problems.append("evidence_kind_empty")
            elif not _nonempty_str(item.get("ref")):
                problems.append(f"evidence_ref_required:{item.get('kind')}")
    ledger = record["ledger"]
    if not isinstance(ledger, list):
        problems.append("ledger_invalid")
    else:
        for item in ledger:
            if not isinstance(item, dict) or not _nonempty_str(item.get("entry")):
                problems.append("ledger_entry_empty")
    return problems


def require_handoff(record: Any) -> dict:
    problems = validate_handoff(record)
    if problems:
        raise HandoffError("validation_failure", "; ".join(problems))
    return record


def new_handoff(
    *,
    handoff_id: str,
    repo: str,
    intent: str,
    invariants: list[str],
    tasks: list[dict[str, Any]],
    evidence: list[dict[str, Any]] | None = None,
    ledger: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build and validate one handoff record (Mythic Eng. flow:
    intent, invariants, tasks, evidence, ledger)."""
    record = {
        "schema": SCHEMA,
        "handoff_id": handoff_id,
        "repo": repo,
        "intent": intent,
        "invariants": list(invariants),
        "tasks": [dict(task) for task in tasks],
        "evidence": [dict(item) for item in (evidence or [])],
        "ledger": [dict(item) for item in (ledger or [])],
    }
    return require_handoff(record)


def handoff_envelope(record: dict, *, recorded_at: str) -> dict[str, Any]:
    """Wrap a valid handoff in a capability-bus result envelope;
    provenance is mandatory, an anonymous handoff cannot travel."""
    require_handoff(record)
    return result_envelope(
        DESCRIPTOR,
        outputs=record,
        source_ref=f"handoff:{record['handoff_id']}",
        recorded_at=recorded_at,
        confidentiality="local-private",
    )


def guard_publish(
    *,
    caller: str,
    data_owner: str,
    data_class: str = "local-private",
    destination: str = "local",
    approved: bool = False,
    device: str | None = None,
) -> dict[str, Any]:
    """Resolve a publish/push action through the capability
    policy. Without the explicit approval flag the decision is a
    refusal naming write_action_requires_approval; approval does
    not override the privacy travel rules."""
    return authorize(
        DESCRIPTOR,
        caller=caller,
        action="publish",
        data_owner=data_owner,
        data_class=data_class,
        destination=destination,
        device=device,
        approved=approved,
    )


def require_publish(**kwargs: Any) -> dict[str, Any]:
    decision = guard_publish(**kwargs)
    if not decision["allowed"]:
        raise HandoffError("unauthorized", "; ".join(decision["reasons"]))
    return decision
