"""X.13 HugrGate: structured uncertainty, bounded (s.48).

HugrGate (``hrabanazviking/RuneForgeAI-HugrGate``, audited at
``2aa74350fa76``) is Volmarr's local-first, model-agnostic
probabilistic decision runtime. The audit (from source, not
README) found: package ``hugrgate`` 1.0.0 (pyproject +
``hugrgate/__init__.__version__``; the roadmap's "active alpha
v0.1.0" observation is stale - the README now reports a
substantial working alpha, still not production-hardened);
sole hard dependency pyyaml, with optional extras for the
heavier rungs (ml / onnx / nli / llm / server / vllm / mlx);
468 Python modules under ``hugrgate/``, 1,000 Python files in
the tree, 499 test files under ``tests/``; an import smoke of
the staged tree passes (``hugrgate`` 1.0.0, ``SPEC_TYPES``
read back). ``DecisionSpec`` (``hugrgate/spec.py``) declares
five contract types - categorical, binary, ordinal, numeric,
multilabel - and ``hugrgate/validation.py`` enforces result
invariants for all five, but NO bundled backend claims numeric
or multilabel support: the deterministic ``RuleBackend``
(``hugrgate/backends/rules.py``) verifies categorical /
binary / ordinal, the scikit-learn backends categorical /
binary, the embedding prototype categorical / binary, NLI
binary only, and the local-LLM backend categorical / ordinal /
binary. This connector therefore offers ONLY binary,
categorical and ordinal for evaluation and refuses numeric /
multilabel by name as unverified at the audited HEAD. The
engine's ladder (``hugrgate/ladder.py``) orders pure rules ->
classical statistics/ML -> embeddings/ONNX -> tiny local LLM
-> larger local models, with a privacy gate: remote rungs
require ``policy.remote_inference=True``. NO cloud adapter
ships at the audited HEAD, so the authorized-cloud rung is
catalogued as existing only as a policy concept - it is never
offered by this connector and never used as a fallback.
License: Apache-2.0, text-verified (``LICENSE`` is the full
Apache License 2.0 text, 201 lines, sha256 c71d239df917...);
pyproject declares Apache-2.0.

Scope law (section 48): this connector is opt-in, default-off
and local-only. It binds NO live transport and runs NO engine
code: it measures a staged tree's structure, catalogues the
verified contract types and the ladder honestly, and evaluates
decisions with its own deterministic pure-rules evaluator -
bounded input, typed results carrying decision type,
confidence, calibration profile and source revision, explicit
failure, and abstain/unknown as a first-class outcome whose
task-control effect is stated. Any failure, timeout or
malformed output falls back deterministically and fail-closed,
never to an unannounced cloud provider. Cyclic inference
routes through HugrGate, A.E.S.I.R. or ThoughtForge/MindSpark
are refused by name. Uncertainty outputs may feed candidate
routing, relevance classification and observational
prioritization only - secrets access and destructive-action
authorization are refused by name as decision subjects, and a
Boolean permission rule is never turned into a model gamble.
Privacy labels and output provenance are preserved.
Calibration metrics (Brier score, log loss, abstention rate)
are computed only from real evaluated examples; production
calibration is honestly unproven per the roadmap's Observed
note. ``production_ready`` is False.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
from pathlib import Path
from typing import Any

CANONICAL_REPO = "hrabanazviking/RuneForgeAI-HugrGate"
CANONICAL_REPO_URL = "https://github.com/hrabanazviking/RuneForgeAI-HugrGate"
AUDITED_HEAD = "2aa74350fa76bc4a35a0841db4582d6fa8b12ae9"
PACKAGE_VERSION = "1.0.0"
PROJECT_LICENSE = "Apache-2.0"
LICENSE_SHA256 = "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"
ADAPTER_VERSION = "0.1.0"
CALIBRATION_VERSION = "runeforge.hugrgate.calibration.v1"
PERFORMANCE_BUDGET_MS = 250
DEFAULT_TIMEOUT_MS = 250
MAX_FEATURES = 32
MAX_TEXT_CHARS = 2000
MAX_INPUT_CHARS = 16384
MAX_EXAMPLES = 500

# Section 48 item 3: the engine schema declares five contract
# types, but only three are verified by a bundled backend at
# the audited HEAD (the deterministic RuleBackend). Numeric and
# multilabel carry schema + result-validation support only and
# are refused by name rather than claimed.
SPEC_TYPES_DECLARED = ("binary", "categorical", "ordinal",
                       "numeric", "multilabel")
VERIFIED_TYPES = ("binary", "categorical", "ordinal")
UNVERIFIED_TYPES = ("numeric", "multilabel")
CONTRACT_CATALOG = (
    {"type": "binary", "declared_in_engine_schema": True,
     "verified_at_audited_head": True,
     "connector_evaluation": "deterministic_rules",
     "basis": "hugrgate/spec.py SPEC_TYPES + backends/rules.py RuleBackend supports binary (also logreg/nli/llm)"},
    {"type": "categorical", "declared_in_engine_schema": True,
     "verified_at_audited_head": True,
     "connector_evaluation": "deterministic_rules",
     "basis": "hugrgate/spec.py SPEC_TYPES + backends/rules.py RuleBackend supports categorical (also logreg/embedding/llm)"},
    {"type": "ordinal", "declared_in_engine_schema": True,
     "verified_at_audited_head": True,
     "connector_evaluation": "deterministic_rules",
     "basis": "hugrgate/spec.py SPEC_TYPES + backends/rules.py RuleBackend supports ordinal (also llm)"},
    {"type": "numeric", "declared_in_engine_schema": True,
     "verified_at_audited_head": False,
     "connector_evaluation": "refused_unverified",
     "basis": "schema + hugrgate/validation.py result invariants only; NO bundled backend claims numeric in capabilities() at the audited HEAD"},
    {"type": "multilabel", "declared_in_engine_schema": True,
     "verified_at_audited_head": False,
     "connector_evaluation": "refused_unverified",
     "basis": "schema + validation + contracts/multilabel.py constraints only; NO bundled backend claims multilabel in capabilities() at the audited HEAD"},
)
# Section 48 item 4: the configurable inference ladder. Only
# rungs that exist in the audited engine are catalogued as
# existing; the connector itself binds only the pure-rules
# rung. The cloud rung has NO adapter at the audited HEAD: it
# is never offered and never a fallback.
INFERENCE_LADDER = (
    {"rung": "pure_rules", "exists_in_engine": True,
     "offered_by_connector": True, "connector_binds": True,
     "requires_authorization": False,
     "basis": "hugrgate/backends/rules.py RuleBackend - deterministic, no optional dependencies"},
    {"rung": "classical_statistics_ml", "exists_in_engine": True,
     "offered_by_connector": False, "connector_binds": False,
     "requires_authorization": False,
     "basis": "hugrgate/backends/logreg.py + forest.py + boosting.py (scikit-learn 'ml' extra); engine rung exists, connector binds no model transport"},
    {"rung": "embeddings_onnx", "exists_in_engine": True,
     "offered_by_connector": False, "connector_binds": False,
     "requires_authorization": False,
     "basis": "hugrgate/backends/embedding.py PrototypeBackend + hugrgate/runtimes/ ('onnx' extra); engine rung exists, connector binds none"},
    {"rung": "tiny_local_llm", "exists_in_engine": True,
     "offered_by_connector": False, "connector_binds": False,
     "requires_authorization": False,
     "basis": "hugrgate/backends/llm.py LLMBackend + runtimes/llama_cpp.py ('llm' extra); engine rung exists, connector binds none"},
    {"rung": "larger_local_model", "exists_in_engine": True,
     "offered_by_connector": False, "connector_binds": False,
     "requires_authorization": False,
     "basis": "server / vllm / mlx extras in pyproject; engine rung exists, connector binds none"},
    {"rung": "authorized_cloud_model", "exists_in_engine": False,
     "offered_by_connector": False, "connector_binds": False,
     "requires_authorization": True,
     "basis": "NO cloud adapter ships at the audited HEAD; the ladder privacy gate requires policy.remote_inference=True - a policy concept only, never offered and never an unannounced fallback"},
)
LADDER_RUNGS = tuple(row["rung"] for row in INFERENCE_LADDER)
# Section 48 items 5-6: uncertainty feeds these uses only.
ALLOWED_USES = ("candidate_routing", "relevance_classification",
                "observational_prioritization")
REFUSED_SUBJECTS = ("secrets_access",
                    "destructive_action_authorization")
# Section 48 item 8: cyclic inference routes refused by name.
CYCLIC_ROUTES_REFUSED = ("hugrgate", "aesir", "thoughtforge",
                         "mindspark")
RULE_OPS = ("equals", "gte", "lte", "contains")
ABSTAIN_TASK_CONTROL = (
    "hold_and_use_deterministic_default: no value is issued, "
    "the caller keeps its deterministic path; the abstention "
    "itself is the control signal")
DECISION_TASK_CONTROL = (
    "advisory only: may inform candidate routing, relevance "
    "classification and observational prioritization; never "
    "secrets access or destructive-action authorization")


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if value is None:
        return default
    return bool(value)


def decision_catalog() -> dict[str, Any]:
    """The s.48 catalog: contracts, ladder, refused subjects."""
    return {
        "schema": "runeforge.hugrgate.catalog.v1",
        "service": "volmarr-hugrgate",
        "canonical_repo": CANONICAL_REPO,
        "audited_head": AUDITED_HEAD,
        "package_version": PACKAGE_VERSION,
        "license": PROJECT_LICENSE,
        "contracts": [dict(row) for row in CONTRACT_CATALOG],
        "verified_types": list(VERIFIED_TYPES),
        "unverified_types": list(UNVERIFIED_TYPES),
        "inference_ladder": [dict(row) for row in INFERENCE_LADDER],
        "cloud_rung_offered": False,
        "cloud_requires_explicit_authorization": True,
        "allowed_uses": list(ALLOWED_USES),
        "refused_subjects": list(REFUSED_SUBJECTS),
        "cyclic_routes_refused": list(CYCLIC_ROUTES_REFUSED),
        "calibration_metrics": ["brier_score", "log_loss",
                                "abstention_rate"],
        "calibration_version": CALIBRATION_VERSION,
        "production_calibration": "unproven",
        "performance_budget_ms": PERFORMANCE_BUDGET_MS,
        "sends_anything_external": False,
        "runs_engine": False,
        "production_ready": False,
    }


def _measure_tree(root: Path) -> dict[str, Any]:
    """Measure a staged HugrGate checkout truthfully (no git call).

    Reads .git/HEAD + refs, the package version in pyproject.toml,
    the LICENSE hash, and counts Python modules / test files by
    filename. No source file's code is copied or executed.
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
        match = re.search(r'^version\s*=\s*"([^"]+)"',
                          pyproject.read_text(encoding="utf-8"), re.M)
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
    pkg = root / "hugrgate"
    record["package_module_count"] = sum(
        1 for p in pkg.rglob("*.py")) if pkg.is_dir() else 0
    tests = root / "tests"
    record["test_file_count"] = sum(
        1 for p in tests.glob("test_*.py")) if tests.is_dir() else 0
    record["status"] = "measured" if head else "tree_partial"
    return record


def hugrgate_status(ctx, recorded_at: str | None = None) -> dict[str, Any]:
    """Truthful adapter status: config, staged tree, hard limits."""
    enabled = _as_bool(ctx.get_config("hugrgate_enabled", False))
    root_value = str(ctx.get_config("hugrgate_root", "") or "").strip()
    tree = _measure_tree(Path(root_value).expanduser()) if root_value else {
        "root": "", "present": False, "status": "not_configured"}
    return {
        "schema": "runeforge.hugrgate.status.v1",
        "service": "volmarr-hugrgate",
        "recorded_at": recorded_at,
        "enabled": enabled,
        "configured": bool(root_value),
        "canonical_repo": CANONICAL_REPO,
        "canonical_repo_url": CANONICAL_REPO_URL,
        "audited_head": AUDITED_HEAD,
        "package_version": PACKAGE_VERSION,
        "license": PROJECT_LICENSE,
        "tree": tree,
        "mode": "opt-in, local-only decision evaluation; deterministic pure-rules connector evaluator, no live engine transport bound",
        "sends_anything_external": False,
        "runs_engine": False,
        "production_ready": False,
    }


def _spec_problem(spec: Any) -> str | None:
    """Structural schema conformance for a DecisionSpec dict."""
    if not isinstance(spec, dict):
        return "spec_not_mapping"
    spec_type = spec.get("type")
    if spec_type not in SPEC_TYPES_DECLARED:
        return "spec_type_unknown"
    if spec_type == "binary":
        if not isinstance(spec.get("statement"), str) or not spec["statement"]:
            return "spec_statement_missing"
    elif spec_type == "categorical":
        options = spec.get("options")
        if (not isinstance(options, list) or len(options) < 2
                or len(set(options)) != len(options)
                or any(not isinstance(o, str) or not o for o in options)):
            return "spec_options_invalid"
    elif spec_type == "ordinal":
        levels = spec.get("levels")
        if (not isinstance(levels, list) or len(levels) < 2
                or len(set(levels)) != len(levels)
                or any(not isinstance(o, str) or not o for o in levels)):
            return "spec_levels_invalid"
    elif spec_type == "numeric":
        low, high = spec.get("minimum"), spec.get("maximum")
        if (not isinstance(low, (int, float))
                or not isinstance(high, (int, float)) or low >= high):
            return "spec_bounds_invalid"
    elif spec_type == "multilabel":
        labels = spec.get("labels")
        if (not isinstance(labels, list) or len(labels) < 1
                or len(set(labels)) != len(labels)
                or any(not isinstance(o, str) or not o for o in labels)):
            return "spec_labels_invalid"
    return None


def _value_space(spec: dict) -> list[str]:
    if spec["type"] == "binary":
        return ["true", "false"]
    if spec["type"] == "categorical":
        return list(spec["options"])
    if spec["type"] == "ordinal":
        return list(spec["levels"])
    return []


def _failure(reason: str, *, decision_type: Any = None,
             fallback: str = "deterministic_abstain",
             **extra: Any) -> dict[str, Any]:
    """Explicit failure (s.48 item 9): fail-closed, by name."""
    result: dict[str, Any] = {
        "schema": "runeforge.hugrgate.result.v1",
        "service": "volmarr-hugrgate",
        "outcome": "failure",
        "decision_type": decision_type,
        "value": None,
        "accepted": False,
        "fail_closed": True,
        "failure": reason,
        "fallback_applied": fallback,
        "fallback_used": True,
        "task_control_effect": (
            "hold: no decision issued; the caller keeps its "
            "deterministic default path"),
        "source_revision": AUDITED_HEAD,
        "sends_anything_external": False,
        "runs_engine": False,
        "production_ready": False,
    }
    result.update(extra)
    return result


def _rule_matches(rule: dict, features: dict) -> bool:
    if rule.get("default") is True:
        return True
    field = rule.get("field")
    if field not in features:
        return False
    actual = features[field]
    op = rule.get("op")
    expected = rule.get("value")
    if op == "equals":
        return actual == expected
    if op == "gte":
        return (isinstance(actual, (int, float))
                and isinstance(expected, (int, float))
                and actual >= expected)
    if op == "lte":
        return (isinstance(actual, (int, float))
                and isinstance(expected, (int, float))
                and actual <= expected)
    if op == "contains":
        return isinstance(actual, str) and str(expected) in actual
    return False


def _rule_problem(rule: Any, space: list[str]) -> str | None:
    if not isinstance(rule, dict):
        return "malformed_rule"
    outcome = rule.get("outcome")
    if outcome not in space:
        return "malformed_rule"
    confidence = rule.get("confidence")
    if (not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0.0 < float(confidence) <= 1.0):
        return "malformed_rule"
    if rule.get("default") is True:
        return None
    if not isinstance(rule.get("field"), str) or not rule["field"]:
        return "malformed_rule"
    if rule.get("op") not in RULE_OPS or "value" not in rule:
        return "malformed_rule"
    return None


def evaluate_decision(request: Any, *, timeout_ms: int | None = None,
                      elapsed_ms: float = 0.0,
                      cloud_authorized: bool = False) -> dict[str, Any]:
    """decision.evaluate (s.48 items 2, 5-10): bounded, typed.

    Pure deterministic rules evaluation over a bounded request.
    Every refusal is by name and fail-closed: unverified
    contract types, refused decision subjects, cyclic routes,
    unauthorized or unavailable cloud rungs, oversized input,
    malformed rules and timeouts all produce an explicit
    failure with a deterministic fallback - never an
    unannounced cloud call. A request for an engine rung this
    connector does not bind is answered by the deterministic
    rules rung with the fallback announced in the result.
    Abstain/unknown is a first-class outcome.
    """
    started = time.monotonic()
    if not isinstance(request, dict):
        return _failure("request_not_mapping")
    spec = request.get("spec")
    problem = _spec_problem(spec)
    if problem is not None:
        bad_type = spec.get("type") if isinstance(spec, dict) else None
        return _failure(problem, decision_type=bad_type)
    decision_type = spec["type"]
    subject = request.get("subject")
    if subject in REFUSED_SUBJECTS:
        return _failure("decision_subject_refused",
                        decision_type=decision_type, subject=subject)
    use = request.get("use")
    if use is not None and use not in ALLOWED_USES:
        return _failure("use_not_allowed", decision_type=decision_type,
                        use=use)
    for route in request.get("route_via") or []:
        normalized = str(route).strip().lower()
        if any(name in normalized for name in CYCLIC_ROUTES_REFUSED):
            return _failure("cyclic_route_refused",
                            decision_type=decision_type, route=route)
    if decision_type in UNVERIFIED_TYPES:
        return _failure("contract_type_unverified",
                        decision_type=decision_type)
    rung = request.get("rung") or "pure_rules"
    if rung not in LADDER_RUNGS:
        return _failure("unknown_rung", decision_type=decision_type,
                        rung=rung)
    if rung == "authorized_cloud_model":
        if not cloud_authorized:
            return _failure("cloud_not_authorized",
                            decision_type=decision_type, rung=rung)
        return _failure("cloud_adapter_unavailable",
                        decision_type=decision_type, rung=rung)
    fallback_reason = None
    if rung != "pure_rules":
        fallback_reason = f"rung_not_bound:{rung}"
    features = request.get("features") or {}
    if not isinstance(features, dict):
        return _failure("features_not_mapping",
                        decision_type=decision_type)
    if len(features) > MAX_FEATURES:
        return _failure("input_too_large", decision_type=decision_type)
    if any(isinstance(v, str) and len(v) > MAX_TEXT_CHARS
           for v in features.values()):
        return _failure("input_too_large", decision_type=decision_type)
    if len(json.dumps(request, default=str)) > MAX_INPUT_CHARS:
        return _failure("input_too_large", decision_type=decision_type)
    budget = timeout_ms
    if budget is None:
        budget = request.get("timeout_ms") or DEFAULT_TIMEOUT_MS
    if elapsed_ms > budget:
        return _failure("timeout", decision_type=decision_type)
    space = _value_space(spec)
    rules = request.get("rules") or []
    if not isinstance(rules, list):
        return _failure("malformed_rule", decision_type=decision_type)
    for rule in rules:
        if _rule_problem(rule, space) is not None:
            return _failure("malformed_rule",
                            decision_type=decision_type)
    ordered = ([r for r in rules if r.get("default") is not True]
               + [r for r in rules if r.get("default") is True])
    matched = None
    for rule in ordered:
        if _rule_matches(rule, features):
            matched = rule
            break
    latency_ms = (time.monotonic() - started) * 1000.0
    if latency_ms > budget:
        return _failure("timeout", decision_type=decision_type)
    provenance = {"audited_head": AUDITED_HEAD,
                  "adapter_version": ADAPTER_VERSION,
                  "rung_requested": rung, "rung_used": "pure_rules",
                  "source_revision": AUDITED_HEAD}
    privacy_label = request.get("privacy_label") or "local-private"
    if matched is None:
        return {
            "schema": "runeforge.hugrgate.result.v1",
            "service": "volmarr-hugrgate",
            "outcome": "abstain",
            "decision_type": decision_type,
            "value": None,
            "accepted": False,
            "abstain_reason": "no_rule_matched",
            "probability": 0.0,
            "confidence": 0.0,
            "distribution": {},
            "uncertainty": 1.0,
            "backend": "deterministic_rules",
            "model": "connector-ruleset",
            "source_revision": AUDITED_HEAD,
            "calibration_profile": "none",
            "latency_ms": latency_ms,
            "fallback_used": bool(fallback_reason),
            "fallback_reason": fallback_reason,
            "privacy_label": privacy_label,
            "provenance": provenance,
            "task_control_effect": ABSTAIN_TASK_CONTROL,
            "sends_anything_external": False,
            "runs_engine": False,
            "production_ready": False,
        }
    outcome = matched["outcome"]
    confidence = float(matched["confidence"])
    others = [v for v in space if v != outcome]
    other_mass = round((1.0 - confidence) / len(others), 12) if others else 0.0
    distribution = {v: other_mass for v in others}
    distribution[outcome] = round(1.0 - other_mass * len(others), 12)
    probability = distribution[outcome]
    return {
        "schema": "runeforge.hugrgate.result.v1",
        "service": "volmarr-hugrgate",
        "outcome": "decision",
        "decision_type": decision_type,
        "value": outcome,
        "accepted": True,
        "probability": probability,
        "confidence": probability,
        "distribution": distribution,
        "uncertainty": round(1.0 - probability, 12),
        "backend": "deterministic_rules",
        "model": "connector-ruleset",
        "source_revision": AUDITED_HEAD,
        "calibration_profile": "none",
        "calibration": "unproven (production calibration unproven at audited HEAD)",
        "latency_ms": latency_ms,
        "fallback_used": bool(fallback_reason),
        "fallback_reason": fallback_reason,
        "privacy_label": privacy_label,
        "provenance": provenance,
        "task_control_effect": DECISION_TASK_CONTROL,
        "sends_anything_external": False,
        "runs_engine": False,
        "production_ready": False,
    }


def calibration_metrics(examples: Any) -> dict[str, Any]:
    """Versioned calibration surface (s.48 item 7).

    Brier score, log loss and abstention rate computed ONLY
    from the evaluated examples supplied - never fabricated.
    Synthetic fixtures are labelled as such; production
    calibration stays honestly unproven.
    """
    base: dict[str, Any] = {
        "schema": "runeforge.hugrgate.calibration.v1",
        "service": "volmarr-hugrgate",
        "metrics_version": CALIBRATION_VERSION,
        "source_revision": AUDITED_HEAD,
        "claims_production_calibration": False,
        "production_calibration": "unproven",
        "sends_anything_external": False,
        "production_ready": False,
    }
    if not isinstance(examples, list) or not examples:
        return {**base, "computed": False, "reason": "no_examples",
                "example_count": 0}
    if len(examples) > MAX_EXAMPLES:
        return {**base, "computed": False, "reason": "too_many_examples",
                "example_count": len(examples)}
    scored: list[tuple[float, float]] = []
    abstained = 0
    for index, example in enumerate(examples):
        if not isinstance(example, dict):
            return {**base, "computed": False,
                    "reason": "malformed_example", "index": index,
                    "example_count": len(examples)}
        if example.get("abstained") is True:
            abstained += 1
            continue
        prob = example.get("probability")
        actual = example.get("actual")
        if (not isinstance(prob, (int, float))
                or isinstance(prob, bool)
                or not 0.0 <= float(prob) <= 1.0
                or actual not in (True, False, 0, 1)):
            return {**base, "computed": False,
                    "reason": "malformed_example", "index": index,
                    "example_count": len(examples)}
        scored.append((float(prob), 1.0 if actual in (True, 1) else 0.0))
    total = len(examples)
    label = ("synthetic fixtures (labelled)"
             if any(isinstance(e, dict) and e.get("synthetic")
                    for e in examples)
             else "caller-supplied evaluated examples")
    if not scored:
        return {**base, "computed": False, "reason": "all_abstained",
                "example_count": total, "scored_count": 0,
                "abstention_rate": 1.0, "source_label": label}
    brier_terms = [(p - y) ** 2 for p, y in scored]
    brier = sum(brier_terms) / len(brier_terms)
    variance = sum((t - brier) ** 2 for t in brier_terms) / len(brier_terms)
    brier_se = math.sqrt(variance) / math.sqrt(len(brier_terms))
    eps = 1e-15
    log_loss = -sum(
        y * math.log(min(max(p, eps), 1.0 - eps))
        + (1.0 - y) * math.log(min(max(1.0 - p, eps), 1.0 - eps))
        for p, y in scored) / len(scored)
    return {**base, "computed": True, "reason": None,
            "example_count": total, "scored_count": len(scored),
            "abstained_count": abstained,
            "abstention_rate": abstained / total,
            "brier_score": brier, "brier_standard_error": brier_se,
            "log_loss": log_loss, "source_label": label}


# Labelled synthetic requests for the CLI evaluate verb: one
# deterministic decision and one abstention, proving the typed
# result + fallback machinery without any real workload.
SYNTHETIC_REQUEST = {
    "spec": {"type": "binary",
             "statement": "Route the candidate to the local review queue"},
    "features": {"queue_depth": 2, "candidate": "raven-report"},
    "use": "candidate_routing",
    "privacy_label": "local-private",
    "rules": [{"field": "queue_depth", "op": "lte", "value": 3,
               "outcome": "true", "confidence": 0.9}],
}
SYNTHETIC_ABSTAIN_REQUEST = {
    "spec": {"type": "binary",
             "statement": "Route the candidate to the local review queue"},
    "features": {"queue_depth": 99, "candidate": "raven-report"},
    "use": "candidate_routing",
    "privacy_label": "local-private",
    "rules": [{"field": "queue_depth", "op": "lte", "value": 3,
               "outcome": "true", "confidence": 0.9}],
}

__all__ = [
    "ABSTAIN_TASK_CONTROL", "ADAPTER_VERSION", "ALLOWED_USES",
    "AUDITED_HEAD", "CALIBRATION_VERSION", "CANONICAL_REPO",
    "CANONICAL_REPO_URL", "CONTRACT_CATALOG", "CYCLIC_ROUTES_REFUSED",
    "DECISION_TASK_CONTROL", "DEFAULT_TIMEOUT_MS", "INFERENCE_LADDER",
    "LADDER_RUNGS", "LICENSE_SHA256", "PACKAGE_VERSION",
    "PERFORMANCE_BUDGET_MS", "PROJECT_LICENSE", "REFUSED_SUBJECTS",
    "SPEC_TYPES_DECLARED", "SYNTHETIC_ABSTAIN_REQUEST",
    "SYNTHETIC_REQUEST", "UNVERIFIED_TYPES", "VERIFIED_TYPES",
    "calibration_metrics", "decision_catalog", "evaluate_decision",
    "hugrgate_status",
]
