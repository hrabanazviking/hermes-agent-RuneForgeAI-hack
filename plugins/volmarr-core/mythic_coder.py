"""X.14 Mythic Agent Coder CLI: the engineering method, shared (s.49).

Mythic Agent Coder CLI (``hrabanazviking/Mythic_Agent_Coder_CLI``,
default branch ``development``, audited at ``e991a526c412``) is
Volmarr's local AI coding harness - the executable home of the
Mythic Engineering method. The audit (from source, not README)
found: package ``mythic-agent`` **0.1.0** (``pyproject.toml``
with hatchling dynamic version from
``mythic_agent/__version__.py``; console scripts ``mythic`` and
``mythic-mcp``); hard dependencies openai / prompt_toolkit /
rich / filelock / pyyaml / httpx, with optional extras for
anthropic / google / the Textual TUI / MCP / tree-sitter code
intelligence / voice; 777 Python files in the tree, 386 under
``mythic_agent/``, 358 test files under ``tests/`` (the README's
6 November audit count of 171 test modules is stale). An import
smoke of the staged tree passes for the package and for
``mythic_agent.workflow.slice_runner`` with the system
interpreter (deeper provider imports need the declared
distribution dependencies, not installed system-wide).

Method (s.49 item 1): the architecture-first workflow lives in
``Mythic-Engineering/Mythic-Engineering_SKILL.md`` - six roles
(Skald, Architect, Forge Worker, Auditor, Cartographer, Scribe),
a five-layer operating model (Vision / Domain / Interface /
Execution / Verification) and an eight-phase daily workflow -
and is executable as data in
``mythic_agent/workflow/slice_runner.py``: a ``SliceDefinition``
(name, description, work order, acceptance gates) whose gates
run sequentially with a durable checkpoint per gate, resumable
after interruption. ``mythic_agent/core/acceptance_gates.py``
pins the acceptance honesty this connector mirrors: held
evidence (runner output, compile log, ledger row) is evidence;
bare claims (feeling, memory, assertion, summary) are not, and
a slice banks only green. The CLI (``mythic_agent/cli.py``)
offers run / chat / tui (each with ``--permission`` in
read-only / ask / trusted, mirroring ``core/policy.py``),
sessions, theme, tutorial, review (static, source-linked),
doctor, cache, costs, metrics and testkit. The provider
registry (``mythic_agent/providers/registry.py``) holds 16
provider classes behind one ``get_provider`` with friendly
aliases. Subagent support is REAL: ``AgentManager``
(``mythic_agent/agents/llm.py``) spawns the six named role
subagents via the ``delegate_task`` tool, and
``mythic_agent/agents/parallel.py`` is a dependency-aware
parallel TOOL-call executor (not parallel writers).

Gaps named honestly (the connector supplies the discipline,
never the claim): (a) NO checkout lease or runtime one-writer
mechanism exists in the audited source - the one-writer law
exists as validated plan DATA in
``mythic_agent/core/worktrees.py`` ("never two writers in one
tree": a plan refuses a duplicated worktree path, a duplicated
branch, and a member holding two assignments; the module runs
no git command and enforces nothing at runtime), so the lease
below is this connector's own enforcement surface, shaped
after the X.12 Draupnir lease; (b) the GitHub integration
(``mythic_agent/integrations/github.py`` - ``create_pr`` /
``add_pr_comment`` / ``list_issues`` / ``view_issue`` /
``get_actions_status`` over the user's own ``gh`` binary, so
credentials never pass through Mythic) is NOT wired into the
CLI at the audited HEAD: its ``register_cli`` is called
nowhere and ``mythic gh`` does not exist as a shipped verb;
(c) the Samverk bridge (``mythic_agent/core/samverk_bridge.py``)
is a data-only book - no socket to the forge, nothing filed
live; (d) platform truth is the engine's own table
(``mythic_agent/core/platform_truth.py``): Linux / Windows /
macOS x install / run / TUI / voice, PROVEN only on
local-measured evidence - NO ARM64 cell and no Termux path
exists in the audited source, so native Ubuntu/Kubuntu is the
only Linux road this connector names and ARM64 evaluation is
recorded as unproven upstream, never assumed equivalent.
Credentials (item 3): provider keys resolve from the
environment or through Kista references (``kista:<name>``,
``mythic_agent/core/key_custody.py`` - config files hold
references, never secrets); this connector reads no credential
and refuses credential access by name. License: Apache-2.0,
text-verified (``LICENSE`` is the full Apache License 2.0
text, 201 lines, sha256 c71d239df917...); pyproject declares
Apache-2.0. No Mythic source is copied or vendored here.

Scope law (section 49): this connector is opt-in, default-off
and local-only. It binds NO live transport and runs NO Mythic
code: it measures a staged tree's structure, catalogues the
versioned Mythic Engineering workflow schema Hermes can call
(and Mythic CLI can independently execute as slice
gates), shapes bounded read-only research / mapping / roadmap
/ test-discovery / diff-proposal / review requests, enforces
an explicit checkout lease with ONE write owner before any
write is even planned, gates every write operation per
operation, and computes outcome metrics only from supplied
records - true acceptance (independently verified, tests
passing) is never inflated from a "done" claim.
Coordination with Draupnir (item 9): X.12 is banked with its
own plan + lease machinery; this connector coordinates only
at the record level (a Draupnir plan key may be cited as job
lineage) and binds no cross-engine execution - durable
cross-engine job lineage does not exist yet and is ticketed.
``production_ready`` is False.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

CANONICAL_REPO = "hrabanazviking/Mythic_Agent_Coder_CLI"
CANONICAL_REPO_URL = "https://github.com/hrabanazviking/Mythic_Agent_Coder_CLI"
DEFAULT_BRANCH = "development"
AUDITED_HEAD = "e991a526c412c3668016809be66dbf50148128c3"
PACKAGE_NAME = "mythic-agent"
PACKAGE_VERSION = "0.1.0"
PROJECT_LICENSE = "Apache-2.0"
LICENSE_SHA256 = "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"
ADAPTER_VERSION = "0.1.0"
WORKFLOW_SCHEMA_VERSION = "runeforge.mythic.workflow.v1"
METRICS_VERSION = "runeforge.mythic.outcomes.v1"
PERFORMANCE_BUDGET_MS = 250
MAX_REQUEST_CHARS = 16384
MAX_STEPS = 32
LEASE_TTL_SECONDS = 900.0

# Section 49 items 1-2: the Mythic Engineering workflow schema,
# extracted from the audited source. The six roles are the
# skill's roles and the engine's spawnable subagents; the five
# stages are the connector's executable cut of the skill's
# five-layer model + eight-phase workflow and the slice
# runner's gate sequence (SliceDefinition + acceptance gates +
# per-gate checkpoints in mythic_agent/workflow/slice_runner.py).
WORKFLOW_ROLES = (
    {"role": "skald", "may_write": False,
     "basis": "Mythic-Engineering_SKILL.md role 1 + delegate_task subagent (naming, framing, vision)"},
    {"role": "cartographer", "may_write": False,
     "basis": "Mythic-Engineering_SKILL.md role 5 + orientation pass (survey before touching anything)"},
    {"role": "architect", "may_write": False,
     "basis": "Mythic-Engineering_SKILL.md role 2 (system mapping, boundaries, roadmap)"},
    {"role": "forge_worker", "may_write": True,
     "basis": "Mythic-Engineering_SKILL.md role 3 - the ONLY writing role, and only inside its own leased worktree (core/worktrees.py house law)"},
    {"role": "auditor", "may_write": False,
     "basis": "Mythic-Engineering_SKILL.md role 4 + core/acceptance_gates.py (runs the gates; bare claims are not evidence)"},
    {"role": "scribe", "may_write": False,
     "basis": "Mythic-Engineering_SKILL.md role 6 (records, receipts, ledger rows)"},
)
WORKFLOW_STAGES = (
    {"stage": "orient", "role": "cartographer", "write": False,
     "purpose": "read-only repository research and architecture mapping of the target tree"},
    {"stage": "architect", "role": "architect", "write": False,
     "purpose": "actionable roadmap construction and test discovery; slice definitions with acceptance gates"},
    {"stage": "forge", "role": "forge_worker", "write": True,
     "purpose": "implementation inside ONE leased checkout by the single lease owner; parallel architects/auditors work on immutable copies"},
    {"stage": "audit", "role": "auditor", "write": False,
     "purpose": "source-linked code review and independent verification of generated patches against held evidence"},
    {"stage": "bank", "role": "scribe", "write": False,
     "purpose": "records and receipts: PR receipt, recovery log, outcome metrics; a slice banks only green"},
)
WORKFLOW_STAGE_NAMES = tuple(row["stage"] for row in WORKFLOW_STAGES)
# Section 49 item 4: read-only operations this connector shapes.
READ_ONLY_OPERATIONS = ("repo_research", "architecture_mapping",
                        "roadmap_construction", "test_discovery",
                        "diff_proposal", "source_linked_review")
# Section 49 items 5-6: write operations, each behind its own
# per-operation gate. This connector EXECUTES none of them; a
# passed gate is a shaped authorization record, not an action.
WRITE_OPERATIONS = ("checkout_write", "commit", "push",
                    "create_pr")
PERMISSION_GATES = (
    {"operation": "checkout_write", "requires": ["checkout_lease"],
     "executed_by_connector": False},
    {"operation": "commit", "requires": ["checkout_lease"],
     "executed_by_connector": False},
    {"operation": "push", "requires": ["checkout_lease", "operator_authorization"],
     "executed_by_connector": False},
    {"operation": "create_pr", "requires": ["checkout_lease", "operator_authorization"],
     "executed_by_connector": False},
    {"operation": "release", "requires": ["operator_authorization"],
     "executed_by_connector": False},
    {"operation": "publication", "requires": ["operator_authorization"],
     "executed_by_connector": False},
)
GATED_OPERATIONS = tuple(row["operation"] for row in PERMISSION_GATES)
# Refused by name in every case (items 3 + 7): credential access
# and unrestricted private companion/author data are never
# served by this connector, authorized or not.
REFUSED_OPERATIONS = ("secrets_access", "credential_read",
                      "private_companion_data_access",
                      "private_author_data_access")
# Section 49 item 7: the ONLY context a coding subagent may be
# handed through this connector - an approved subset, by key.
APPROVED_CONTEXT_KEYS = ("persona_role", "project_facts",
                         "coding_conventions", "roadmap_excerpt",
                         "slice_definition")
PRIVATE_CONTEXT_KEYS = ("companion_data", "author_data",
                        "private_memory", "credentials")
# Section 49 item 6: branch strategies the gate records accept.
BRANCH_STRATEGIES = ("team_branch", "feature_branch",
                     "slice_branch")
# Section 49 item 10 + acceptance_gates.py: held evidence kinds
# vs bare claims. Only held evidence can verify a patch.
HELD_EVIDENCE_KINDS = ("runner_output", "compile_log",
                       "ledger_row", "neighbour_log")
BARE_CLAIM_KINDS = ("feeling", "memory", "assertion", "summary")
RECOVERY_ACTIONS = ("retry_after_fetch", "rebase_then_retry",
                    "abort_and_report")
# Section 49 item 8: platform evaluation honesty at the audited
# HEAD (core/platform_truth.py - PROVEN only on local-measured
# evidence; no ARM64 cell, no Termux path in the source).
PLATFORM_EVALUATION = (
    {"platform": "ubuntu_kubuntu_linux", "status": "native_road_named",
     "basis": "platform_truth table Linux cells; the campaign machine is Linux - per-cell PROVEN still requires local-measured evidence"},
    {"platform": "windows", "status": "not_equivalent_not_assumed",
     "basis": "platform_truth lists Windows cells separately; the POSIX-only fcntl import failure in hosted CI is still in the reviewed source"},
    {"platform": "macos", "status": "not_equivalent_not_assumed",
     "basis": "platform_truth lists macOS cells separately; no macOS machine is available to the upstream campaign"},
    {"platform": "arm64_linux", "status": "unproven_upstream",
     "basis": "NO ARM64 cell exists in platform_truth at the audited HEAD; ARM64 evaluation is honest-unproven, never assumed equivalent to x86-64"},
    {"platform": "termux", "status": "no_path_in_source",
     "basis": "no Termux path exists in the audited source"},
)


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if value is None:
        return default
    return bool(value)


def workflow_catalog() -> dict[str, Any]:
    """The s.49 catalog: workflow schema, operations, gates."""
    return {
        "schema": "runeforge.mythic.catalog.v1",
        "service": "volmarr-mythic",
        "canonical_repo": CANONICAL_REPO,
        "default_branch": DEFAULT_BRANCH,
        "audited_head": AUDITED_HEAD,
        "package_name": PACKAGE_NAME,
        "package_version": PACKAGE_VERSION,
        "license": PROJECT_LICENSE,
        "workflow_schema": {
            "version": WORKFLOW_SCHEMA_VERSION,
            "executable_form": "slice definitions with sequential acceptance gates and per-gate checkpoints (mythic_agent/workflow/slice_runner.py SliceDefinition/SliceRunner); Hermes can call this schema and Mythic CLI can independently execute it",
            "roles": [dict(row) for row in WORKFLOW_ROLES],
            "stages": [dict(row) for row in WORKFLOW_STAGES],
            "writing_roles": [row["role"] for row in WORKFLOW_ROLES if row["may_write"]],
        },
        "read_only_operations": list(READ_ONLY_OPERATIONS),
        "write_operations": list(WRITE_OPERATIONS),
        "permission_gates": [dict(row) for row in PERMISSION_GATES],
        "refused_operations": list(REFUSED_OPERATIONS),
        "approved_context_keys": list(APPROVED_CONTEXT_KEYS),
        "private_context_keys_refused": list(PRIVATE_CONTEXT_KEYS),
        "branch_strategies": list(BRANCH_STRATEGIES),
        "held_evidence_kinds": list(HELD_EVIDENCE_KINDS),
        "bare_claim_kinds_not_evidence": list(BARE_CLAIM_KINDS),
        "provider_registry": {
            "provider_count": 16,
            "basis": "mythic_agent/providers/registry.py _REGISTRY holds 16 provider classes behind get_provider with friendly aliases; credentials resolve from environment variables or kista:<name> references, never from this connector",
            "credentials_read_by_connector": False,
        },
        "github_integration": {
            "module": "mythic_agent/integrations/github.py",
            "transport": "the user's own gh binary; credentials never pass through Mythic",
            "wired_into_cli_at_audited_head": False,
            "basis": "register_cli is defined in the module but called nowhere in the audited tree; no mythic gh verb ships at the audited HEAD",
        },
        "samverk_integration": {
            "module": "mythic_agent/core/samverk_bridge.py",
            "live": False,
            "basis": "data-only exchange book; no socket to the forge, nothing filed live",
        },
        "subagent_support": {
            "real": True,
            "basis": "AgentManager.spawn_subagent + delegate_task tool (six named role subagents) in mythic_agent/agents/llm.py; agents/parallel.py parallelizes tool calls, not writers",
            "context_subset_only": True,
        },
        "checkout_lease": {
            "exists_in_audited_source": False,
            "basis": "core/worktrees.py holds the one-writer law as validated plan data only (runs no git, enforces nothing at runtime); the lease enforced here is this connector's own surface, shaped after the X.12 Draupnir lease",
            "one_writer_invariant": True,
        },
        "platform_evaluation": [dict(row) for row in PLATFORM_EVALUATION],
        "draupnir_coordination": {
            "boundary": "record-level only: a Draupnir plan key may be cited as job lineage; no cross-engine execution is bound and durable cross-engine job lineage does not exist yet (X14-T4)",
            "draupnir_banked": "X.12 (plan + lease machinery of its own)",
        },
        "performance_budget_ms": PERFORMANCE_BUDGET_MS,
        "sends_anything_external": False,
        "runs_engine": False,
        "executes_operations": False,
        "production_ready": False,
    }


def _measure_tree(root: Path) -> dict[str, Any]:
    """Measure a staged Mythic checkout truthfully (no git call).

    Reads .git/HEAD + refs, the package name in pyproject.toml,
    the version in mythic_agent/__version__.py, the LICENSE
    hash, and counts Python modules / test files by filename.
    No source file's code is copied or executed.
    """
    record: dict[str, Any] = {"root": str(root), "present": root.is_dir()}
    if not root.is_dir():
        record["status"] = "tree_missing"
        return record
    head = None
    head_file = root / ".git" / "HEAD"
    if head_file.is_file():
        ref = head_file.read_text(encoding="utf-8").strip()
        if ref.startswith("ref:"):
            ref_path = root / ".git" / ref[4:].strip()
            if ref_path.is_file():
                head = ref_path.read_text(encoding="utf-8").strip()
            else:
                packed = root / ".git" / "packed-refs"
                if packed.is_file():
                    for line in packed.read_text(encoding="utf-8").splitlines():
                        parts = line.split(" ", 1)
                        if len(parts) == 2 and parts[1].strip() == ref[4:].strip():
                            head = parts[0].strip()
        elif ref:
            head = ref
    record["head"] = head
    record["head_matches_audited"] = head == AUDITED_HEAD
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        match = re.search(r'^name\s*=\s*"([^"]+)"',
                          pyproject.read_text(encoding="utf-8"), re.M)
        if match:
            record["package_name"] = match.group(1)
    version_file = root / "mythic_agent" / "__version__.py"
    if version_file.is_file():
        match = re.search(r'^__version__\s*=\s*"([^"]+)"',
                          version_file.read_text(encoding="utf-8"), re.M)
        if match:
            record["package_version"] = match.group(1)
    license_file = root / "LICENSE"
    if license_file.is_file():
        record["license_sha256"] = hashlib.sha256(
            license_file.read_bytes()).hexdigest()
        record["license_matches_audited"] = (
            record["license_sha256"] == LICENSE_SHA256)
    record["module_count"] = sum(
        1 for p in root.rglob("*.py") if ".git" not in p.parts)
    pkg = root / "mythic_agent"
    record["package_module_count"] = sum(
        1 for p in pkg.rglob("*.py")) if pkg.is_dir() else 0
    tests = root / "tests"
    record["test_file_count"] = sum(
        1 for p in tests.glob("test_*.py")) if tests.is_dir() else 0
    record["status"] = "measured" if head else "tree_partial"
    return record


def mythic_status(ctx, recorded_at: str | None = None) -> dict[str, Any]:
    """Truthful adapter status: config, staged tree, hard limits."""
    enabled = _as_bool(ctx.get_config("mythic_enabled", False))
    root_value = str(ctx.get_config("mythic_root", "") or "").strip()
    tree = _measure_tree(Path(root_value).expanduser()) if root_value else {
        "root": "", "present": False, "status": "not_configured"}
    return {
        "schema": "runeforge.mythic.status.v1",
        "service": "volmarr-mythic",
        "recorded_at": recorded_at,
        "enabled": enabled,
        "configured": bool(root_value),
        "canonical_repo": CANONICAL_REPO,
        "canonical_repo_url": CANONICAL_REPO_URL,
        "default_branch": DEFAULT_BRANCH,
        "audited_head": AUDITED_HEAD,
        "package_name": PACKAGE_NAME,
        "package_version": PACKAGE_VERSION,
        "license": PROJECT_LICENSE,
        "tree": tree,
        "mode": "opt-in, local-only Mythic Engineering workflow connector; shapes read-only plans and lease/gate records, executes no operation and runs no Mythic code",
        "sends_anything_external": False,
        "runs_engine": False,
        "executes_operations": False,
        "production_ready": False,
    }


def _failure(reason: str, *, schema: str = "runeforge.mythic.plan.v1",
             **extra: Any) -> dict[str, Any]:
    """Explicit failure: fail-closed, by name, nothing executed."""
    result: dict[str, Any] = {
        "schema": schema,
        "service": "volmarr-mythic",
        "outcome": "failure",
        "accepted": False,
        "fail_closed": True,
        "failure": reason,
        "source_revision": AUDITED_HEAD,
        "sends_anything_external": False,
        "runs_engine": False,
        "executes_operations": False,
        "production_ready": False,
    }
    result.update(extra)
    return result


def _lease_path(store_dir: Path, checkout: str) -> Path:
    digest = hashlib.sha256(checkout.encode("utf-8")).hexdigest()[:16]
    return Path(store_dir) / "leases" / f"{digest}.json"


def acquire_lease(store_dir: Path, checkout: str, owner: str,
                  heartbeat: float = 0.0) -> dict[str, Any]:
    """Checkout lease (s.49 item 5): ONE write owner per checkout.

    A second owner is refused by name (``duplicate_lease_refused``
    with the holding owner named); the holding owner re-acquiring
    refreshes its heartbeat. Parallel architects and auditors
    never need a lease - they work read-only on immutable copies.
    """
    base = {"schema": "runeforge.mythic.lease.v1", "checkout": checkout,
            "sends_anything_external": False, "production_ready": False}
    if not isinstance(checkout, str) or not checkout.strip():
        return {**base, "acquired": False, "reason": "checkout_missing"}
    if not isinstance(owner, str) or not owner.strip():
        return {**base, "acquired": False, "reason": "owner_missing"}
    path = _lease_path(store_dir, checkout)
    if path.is_file():
        held = json.loads(path.read_text(encoding="utf-8"))
        if held.get("owner") != owner:
            return {**base, "acquired": False,
                    "reason": "duplicate_lease_refused",
                    "lease_owner": held.get("owner")}
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"checkout": checkout, "owner": owner,
              "heartbeat": float(heartbeat)}
    path.write_text(json.dumps(record, indent=1, sort_keys=True),
                    encoding="utf-8")
    return {**base, "acquired": True, "owner": owner, "reason": None}


def lease_status(store_dir: Path, checkout: str, *, now: float,
                 ttl_seconds: float = LEASE_TTL_SECONDS) -> dict[str, Any]:
    """Lease liveness: a stale heartbeat means a lost writer."""
    base = {"schema": "runeforge.mythic.lease.v1", "checkout": checkout,
            "sends_anything_external": False, "production_ready": False}
    path = _lease_path(store_dir, checkout)
    if not path.is_file():
        return {**base, "status": "unleased", "owner": None}
    held = json.loads(path.read_text(encoding="utf-8"))
    stale = (now - float(held.get("heartbeat", 0.0))) > ttl_seconds
    return {**base, "status": "worker_lost" if stale else "held",
            "owner": held.get("owner"),
            "recoverable_via_checkpoint": stale}


def release_lease(store_dir: Path, checkout: str, owner: str) -> dict[str, Any]:
    """Only the lease owner may release its lease."""
    base = {"schema": "runeforge.mythic.lease.v1", "checkout": checkout,
            "sends_anything_external": False, "production_ready": False}
    path = _lease_path(store_dir, checkout)
    if path.is_file():
        held = json.loads(path.read_text(encoding="utf-8"))
        if held.get("owner") == owner:
            path.unlink()
            return {**base, "released": True, "reason": None}
        return {**base, "released": False,
                "reason": "not_lease_owner", "lease_owner": held.get("owner")}
    return {**base, "released": False, "reason": "not_leased"}


def gate_operation(operation: Any, *, lease_owner: str | None = None,
                   operator_authorized: bool = False) -> dict[str, Any]:
    """Per-operation permission gate (s.49 items 3, 5-7).

    Every refusal is by name and fail-closed. A passed gate is a
    shaped authorization record ONLY - this connector executes
    no operation, reads no credential and serves no private
    companion or author data, authorized or not.
    """
    base = {"schema": "runeforge.mythic.gate.v1", "service": "volmarr-mythic",
            "operation": operation, "executed": False,
            "source_revision": AUDITED_HEAD,
            "sends_anything_external": False, "runs_engine": False,
            "production_ready": False}
    if operation in REFUSED_OPERATIONS:
        return {**base, "allowed": False,
                "reason": "operation_refused_by_name"}
    gate = next((row for row in PERMISSION_GATES
                 if row["operation"] == operation), None)
    if gate is None:
        return {**base, "allowed": False, "reason": "unknown_operation"}
    if "checkout_lease" in gate["requires"] and not lease_owner:
        return {**base, "allowed": False, "reason": "lease_required",
                "requires": list(gate["requires"])}
    if "operator_authorization" in gate["requires"] and not operator_authorized:
        return {**base, "allowed": False,
                "reason": "operator_authorization_required",
                "requires": list(gate["requires"])}
    return {**base, "allowed": True, "reason": None,
            "requires": list(gate["requires"]),
            "lease_owner": lease_owner,
            "note": "gate passed as a record only; the connector executes nothing - the lease owner performs the operation outside this connector"}


def plan_research(request: Any) -> dict[str, Any]:
    """Shape a bounded read-only workflow request (s.49 items 2, 4, 7).

    Read-only operations (research, architecture mapping,
    roadmap construction, test discovery, diff proposals,
    source-linked reviews) are shaped into a staged plan under
    the versioned workflow schema. Write operations are never
    planned here - they are answered by their gate. A private
    repository is denied without operator authorization. The
    subagent context is an approved subset only: any private
    context key refuses the whole request by name. Nothing is
    executed; the plan is a record Hermes can call and Mythic
    CLI can independently execute as slice gates.
    """
    started = time.monotonic()
    if not isinstance(request, dict):
        return _failure("request_not_mapping")
    if len(json.dumps(request, default=str)) > MAX_REQUEST_CHARS:
        return _failure("input_too_large")
    operation = request.get("operation")
    if operation in REFUSED_OPERATIONS:
        return _failure("operation_refused_by_name", operation=operation)
    if operation in GATED_OPERATIONS:
        gate = gate_operation(
            operation, lease_owner=request.get("lease_owner"),
            operator_authorized=bool(request.get("operator_authorized")))
        return _failure("operation_requires_gate", operation=operation,
                        gate=gate)
    if operation not in READ_ONLY_OPERATIONS:
        return _failure("unknown_operation", operation=operation)
    repo = request.get("repo")
    if not isinstance(repo, dict) or not isinstance(repo.get("name"), str) \
            or not repo["name"].strip():
        return _failure("repo_missing", operation=operation)
    visibility = repo.get("visibility", "public")
    if visibility not in ("public", "private"):
        return _failure("repo_visibility_unknown", operation=operation)
    if visibility == "private" and not request.get("operator_authorized"):
        return _failure("private_repo_denied", operation=operation,
                        repo=repo["name"])
    context = request.get("context") or {}
    if not isinstance(context, dict):
        return _failure("context_not_mapping", operation=operation)
    for key in context:
        if key in PRIVATE_CONTEXT_KEYS:
            return _failure("private_context_refused", operation=operation,
                            context_key=key)
        if key not in APPROVED_CONTEXT_KEYS:
            return _failure("context_key_not_approved", operation=operation,
                            context_key=key)
    steps_in = request.get("steps") or list(WORKFLOW_STAGE_NAMES[:2])
    if not isinstance(steps_in, list) or not steps_in \
            or len(steps_in) > MAX_STEPS:
        return _failure("malformed_steps", operation=operation)
    steps = []
    for name in steps_in:
        stage = next((row for row in WORKFLOW_STAGES
                      if row["stage"] == name), None)
        if stage is None:
            return _failure("unknown_stage", operation=operation, stage=name)
        if stage["write"]:
            return _failure("write_stage_in_read_only_plan",
                            operation=operation, stage=name)
        steps.append({"stage": stage["stage"], "role": stage["role"],
                      "write": False, "purpose": stage["purpose"]})
    latency_ms = (time.monotonic() - started) * 1000.0
    plan_core = {"operation": operation, "repo": repo["name"],
                 "visibility": visibility,
                 "stages": [s["stage"] for s in steps],
                 "context_keys": sorted(context)}
    plan_key = hashlib.sha256(json.dumps(
        plan_core, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "schema": "runeforge.mythic.plan.v1",
        "service": "volmarr-mythic",
        "outcome": "plan",
        "accepted": True,
        "operation": operation,
        "workflow_schema": WORKFLOW_SCHEMA_VERSION,
        "plan_key": plan_key,
        "repo": repo["name"],
        "visibility": visibility,
        "steps": steps,
        "step_count": len(steps),
        "context_keys": sorted(context),
        "context_subset_only": True,
        "read_only": True,
        "lease_required": False,
        "latency_ms": latency_ms,
        "source_revision": AUDITED_HEAD,
        "sends_anything_external": False,
        "runs_engine": False,
        "executes_operations": False,
        "production_ready": False,
    }


_DIFF_FILE_RE = re.compile(r"^diff --git a/(.+) b/(.+)$")
_DIFF_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@")
_BUILD_LINE_RE = re.compile(
    r"^(?P<path>[^:\s][^:]*):(?P<line>\d+):(?P<col>\d+): "
    r"(?P<level>error|warning|note): (?P<message>.+)$")


def verify_patch(patch_text: Any, evidence: Any) -> dict[str, Any]:
    """Independent verification of a generated patch (s.49 gate).

    The patch is re-parsed here, never trusted from its author's
    claim: a malformed diff fails by name, and verification
    stands only on HELD evidence (runner output, compile log,
    ledger row, neighbour log - the acceptance_gates.py
    vocabulary). Bare claims (feeling / memory / assertion /
    summary) are not evidence and leave the patch unverified.
    """
    base = {"schema": "runeforge.mythic.verify.v1",
            "service": "volmarr-mythic", "source_revision": AUDITED_HEAD,
            "sends_anything_external": False, "runs_engine": False,
            "executes_operations": False, "production_ready": False}
    if not isinstance(patch_text, str) or not patch_text.strip():
        return {**base, "verified": False, "failure": "malformed_diff",
                "fail_closed": True}
    files: list[str] = []
    hunks = 0
    malformed = False
    in_hunk = False
    for line in patch_text.splitlines():
        file_match = _DIFF_FILE_RE.match(line)
        if file_match:
            files.append(file_match.group(2))
            in_hunk = False
            continue
        if line.startswith(("--- ", "+++ ")):
            continue
        if _DIFF_HUNK_RE.match(line):
            hunks += 1
            in_hunk = True
            continue
        if in_hunk and line[:1] in ("+", "-", " ", "\\"):
            continue
        if line.strip():
            malformed = True
    if malformed or not files or hunks == 0:
        return {**base, "verified": False, "failure": "malformed_diff",
                "fail_closed": True, "files": files, "hunks": hunks}
    if not isinstance(evidence, list) or not evidence:
        return {**base, "verified": False, "failure": "no_evidence",
                "fail_closed": True, "files": files, "hunks": hunks}
    kinds = []
    for item in evidence:
        if not isinstance(item, dict) or "kind" not in item:
            return {**base, "verified": False,
                    "failure": "malformed_evidence", "fail_closed": True,
                    "files": files, "hunks": hunks}
        kinds.append(item["kind"])
    bare = [k for k in kinds if k in BARE_CLAIM_KINDS]
    held = [k for k in kinds if k in HELD_EVIDENCE_KINDS]
    unknown = [k for k in kinds if k not in HELD_EVIDENCE_KINDS
               and k not in BARE_CLAIM_KINDS]
    if unknown:
        return {**base, "verified": False, "failure": "unknown_evidence_kind",
                "fail_closed": True, "evidence_kinds": kinds,
                "files": files, "hunks": hunks}
    if not held:
        return {**base, "verified": False, "failure": "unverified_claim",
                "fail_closed": True, "evidence_kinds": kinds,
                "bare_claims": bare, "files": files, "hunks": hunks}
    return {**base, "verified": True, "failure": None, "fail_closed": False,
            "files": files, "file_count": len(files), "hunks": hunks,
            "evidence_kinds": kinds, "held_evidence": held,
            "independent": True}


def parse_build_output(text: Any) -> dict[str, Any]:
    """Parse compiler-style build output (s.49 gate: malformed).

    Every non-empty line must match ``path:line:col: level:
    message``; anything else makes the whole record malformed
    by name - partial parses are never dressed up as results.
    """
    base = {"schema": "runeforge.mythic.build_output.v1",
            "service": "volmarr-mythic", "source_revision": AUDITED_HEAD,
            "sends_anything_external": False, "production_ready": False}
    if not isinstance(text, str) or not text.strip():
        return {**base, "parsed": False, "failure": "malformed_build_output",
                "fail_closed": True}
    findings = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        match = _BUILD_LINE_RE.match(raw)
        if match is None:
            return {**base, "parsed": False,
                    "failure": "malformed_build_output", "fail_closed": True,
                    "offending_line": raw}
        findings.append({"path": match.group("path"),
                         "line": int(match.group("line")),
                         "col": int(match.group("col")),
                         "level": match.group("level"),
                         "message": match.group("message")})
    return {**base, "parsed": True, "failure": None, "fail_closed": False,
            "findings": findings, "finding_count": len(findings),
            "error_count": sum(1 for f in findings if f["level"] == "error")}


def recovery_record(entry: Any) -> dict[str, Any]:
    """Failed-push recovery log shape (s.49 items 6 + test gate).

    Validates and receipts a recovery record for a failed push:
    the failure, the branch strategy, the recovery action and
    the PR receipt fields must all be present and named;
    anything malformed fails closed by name. The connector
    records the shape only - it performs no push and no recovery.
    """
    base = {"schema": "runeforge.mythic.recovery.v1",
            "service": "volmarr-mythic", "source_revision": AUDITED_HEAD,
            "sends_anything_external": False, "runs_engine": False,
            "executes_operations": False, "production_ready": False}
    if not isinstance(entry, dict):
        return {**base, "recorded": False,
                "failure": "malformed_recovery_record", "fail_closed": True}
    if entry.get("operation") != "push":
        return {**base, "recorded": False,
                "failure": "recovery_operation_not_push", "fail_closed": True}
    if not isinstance(entry.get("failure"), str) or not entry["failure"].strip():
        return {**base, "recorded": False,
                "failure": "recovery_failure_unnamed", "fail_closed": True}
    if entry.get("branch_strategy") not in BRANCH_STRATEGIES:
        return {**base, "recorded": False,
                "failure": "unknown_branch_strategy", "fail_closed": True}
    if entry.get("recovery_action") not in RECOVERY_ACTIONS:
        return {**base, "recorded": False,
                "failure": "unknown_recovery_action", "fail_closed": True}
    if not isinstance(entry.get("resolved"), bool):
        return {**base, "recorded": False,
                "failure": "recovery_outcome_missing", "fail_closed": True}
    record_core = {k: entry.get(k) for k in
                   ("operation", "failure", "branch_strategy",
                    "recovery_action", "resolved", "repo")}
    record_key = hashlib.sha256(json.dumps(
        record_core, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return {**base, "recorded": True, "failure": None, "fail_closed": False,
            "record_key": record_key, "operation": "push",
            "push_failure": entry["failure"],
            "branch_strategy": entry["branch_strategy"],
            "recovery_action": entry["recovery_action"],
            "resolved": entry["resolved"],
            "pr_receipt": entry.get("pr_receipt"),
            "note": "recovery recorded as a log shape only; no push or recovery was performed by this connector"}


def outcome_metrics(records: Any) -> dict[str, Any]:
    """Outcome metrics (s.49 item 10), from supplied records only.

    Patch tests passing, review findings resolved, clean diffs,
    recovered sessions - and true acceptance kept strictly apart
    from claimed done: a record counts as truly accepted only
    when it is independently verified AND all its patch tests
    pass. Claimed-done records failing that bar are counted as
    inflated, never merged into acceptance. Empty input
    computes nothing and says so; malformed records fail closed.
    """
    base: dict[str, Any] = {
        "schema": "runeforge.mythic.outcomes.v1",
        "service": "volmarr-mythic",
        "metrics_version": METRICS_VERSION,
        "source_revision": AUDITED_HEAD,
        "claims_production_outcomes": False,
        "sends_anything_external": False,
        "production_ready": False,
    }
    if not isinstance(records, list) or not records:
        return {**base, "computed": False, "reason": "no_records",
                "record_count": 0}
    tests_passed = 0
    tests_total = 0
    findings = 0
    resolved = 0
    clean = 0
    recovered = 0
    claimed_done = 0
    truly_accepted = 0
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            return {**base, "computed": False,
                    "reason": "malformed_record", "index": index,
                    "record_count": len(records)}
        passed = record.get("tests_passed")
        total = record.get("tests_total")
        found = record.get("review_findings")
        fixed = record.get("review_resolved")
        for value in (passed, total, found, fixed):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                return {**base, "computed": False,
                        "reason": "malformed_record", "index": index,
                        "record_count": len(records)}
        if passed > total or fixed > found:
            return {**base, "computed": False,
                    "reason": "malformed_record", "index": index,
                    "record_count": len(records)}
        tests_passed += passed
        tests_total += total
        findings += found
        resolved += fixed
        if record.get("clean_diff") is True:
            clean += 1
        if record.get("recovered") is True:
            recovered += 1
        accepted = (record.get("independently_verified") is True
                    and total > 0 and passed == total)
        if accepted:
            truly_accepted += 1
        if record.get("claimed_done") is True:
            claimed_done += 1
    total_records = len(records)
    label = ("synthetic fixtures (labelled)"
             if any(isinstance(r, dict) and r.get("synthetic")
                    for r in records)
             else "caller-supplied job records")
    return {**base, "computed": True, "reason": None,
            "record_count": total_records,
            "patch_test_pass_rate": (tests_passed / tests_total
                                     if tests_total else None),
            "tests_passed": tests_passed, "tests_total": tests_total,
            "review_resolution_rate": (resolved / findings
                                        if findings else None),
            "review_findings": findings, "review_resolved": resolved,
            "clean_diff_rate": clean / total_records,
            "recovered_sessions": recovered,
            "claimed_done": claimed_done,
            "truly_accepted": truly_accepted,
            "inflated_done": claimed_done - truly_accepted
            if claimed_done >= truly_accepted else 0,
            "true_acceptance_rate": truly_accepted / total_records,
            "source_label": label}


# Labelled synthetic request for the CLI plan verb: a read-only
# research plan over a public repo, proving the staged plan +
# gate machinery without any real workload.
SYNTHETIC_REQUEST = {
    "operation": "architecture_mapping",
    "repo": {"name": "hrabanazviking/Mythic_Agent_Coder_CLI",
             "visibility": "public"},
    "steps": ["orient", "architect"],
    "context": {"persona_role": "architect",
                "project_facts": "labelled synthetic facts only"},
}

__all__ = [
    "ADAPTER_VERSION", "APPROVED_CONTEXT_KEYS", "AUDITED_HEAD",
    "BARE_CLAIM_KINDS", "BRANCH_STRATEGIES", "CANONICAL_REPO",
    "CANONICAL_REPO_URL", "DEFAULT_BRANCH", "GATED_OPERATIONS",
    "HELD_EVIDENCE_KINDS", "LEASE_TTL_SECONDS", "LICENSE_SHA256",
    "METRICS_VERSION", "PACKAGE_NAME", "PACKAGE_VERSION",
    "PERFORMANCE_BUDGET_MS", "PERMISSION_GATES", "PLATFORM_EVALUATION",
    "PRIVATE_CONTEXT_KEYS", "PROJECT_LICENSE", "READ_ONLY_OPERATIONS",
    "RECOVERY_ACTIONS", "REFUSED_OPERATIONS", "SYNTHETIC_REQUEST",
    "WORKFLOW_ROLES", "WORKFLOW_SCHEMA_VERSION", "WORKFLOW_STAGES",
    "WORKFLOW_STAGE_NAMES", "WRITE_OPERATIONS",
    "acquire_lease", "gate_operation", "lease_status", "mythic_status",
    "outcome_metrics", "parse_build_output", "plan_research",
    "recovery_record", "release_lease", "verify_patch",
    "workflow_catalog",
]
