"""X.06 MindSpark ThoughtForge adapter (roadmap section 41).

Roadmap section 41 (Part VII workstream 6 of 15) names
MindSpark ThoughtForge: make tiny models genuinely useful.
The X.06 audit (docs/modernization/X06_MINDSPARK_WORKSTREAM.md,
2026-11-14) staged the source repo
hrabanazviking/MindSpark_ThoughtForge directly under $HOME at
~/mindspark-x06, development HEAD
68aa4d1cd29f6d6c57d1266e70833584c9b1a74e (== ls-remote, ==
the integration lock's recorded current_head; HEAD has NOT
moved since the E0 draft measurement). The audited tree is
real, heavily tested code: package thoughtforge 1.0.0,
src/thoughtforge 171 modules / ~104,700 LOC, 149 test files;
its own campaign records a full gate of 4,262 collected /
4,260 passed / 1 skipped / 1 known environment failure at
TF-160, and the X.06 targeted re-run of its router / scaffold
/ prompt / profile / backend / cost / persona-compiler /
Hermes-binding suites on purplelongship measured 454 passed /
1 failed, the one failure a host-profile expectation written
for a VM (this GPU laptop correctly auto-selects the
desktop_gpu profile instead of desktop_cpu).

The decisive audit finding shapes this whole slice: the
ThoughtForge methods that exist as tested code -- its
InputRouter, ScaffoldBuilder, prompt builder, hardware
profile selector and cost/latency discipline -- are
DETERMINISTIC, heuristic-first, and make no model calls at
all ("Heuristic-first classification: keyword/pattern
matching with no model calls", cognition/router.py). Its
model runners (llama.cpp / Ollama / HF / ONNX backends) exist
as code, but no benchmark in the audited tree demonstrates a
small model beating the deterministic methods on the section
41 profile tasks, and no local model endpoint was live on
purplelongship at proof time (Ollama installed, server not
running; the A.E.S.I.R. loopback endpoint answers 401 without
its key). Section 41 item 4 therefore governs: this adapter
is DETERMINISTIC-FIRST. Model inference is an optional,
explicitly configured, loopback-only seam behind the
deterministic profiles; it is never required, never a hidden
fallback, and its benefit is recorded as NOT PROVEN in this
slice (ticket X06-T1). No ThoughtForge source is incorporated
into this fork -- this module is original volmarr-core code
written against the audited interfaces, plugin-side only.
License: there is NO standalone LICENSE file at the audited
HEAD; the CC BY 4.0 declaration lives in the README License
section and the pyproject license field (both read at the
staged tree in X.06).

What this slice builds, honestly scoped to section 41:

- the six small-model cognition PROFILES as data plus
  deterministic implementations (item 2): classifier, router,
  short-form reflection, persona section tagging, token-
  budget planner, inexpensive validation;
- a deterministic rules-only BASELINE for every profile and
  a benchmark harness that measures the baseline's accuracy
  on synthetic cases plus latency on this machine (items 3
  and 4; cross-device numbers are NOT claimed -- ticket
  X06-T2);
- persona section tagging that consumes ONLY the compiled
  artefact of the fork's existing SINGLE persona compiler
  (persona_runtime.PersonaCompiler) -- a raw document, a
  path, or any dict without the compiler's shape is refused
  by name; no second personality file exists here (item 5);
- sub-requests that INHERIT the parent turn's privacy /
  egress policy: a parent policy that disallows model use or
  egress is honoured exactly, and the only model transport
  this adapter will construct is plain HTTP on 127.0.0.1 --
  any other endpoint is refused by name, so there is no
  hidden cloud fallback anywhere (items 6 and test gates);
- route PROPOSALS only: a proposal names the existing
  A.E.S.I.R. cognition routing contract (cognition.py /
  routing.py) as its consumer seam -- no HugrGate code exists
  in this tree to integrate with, and that absence is stated,
  not papered over -- while final authority and budget
  enforcement stay in Hermes (item 7);
- failure discipline (item 8): cancellation, model crash,
  out-of-memory, timeout, partial output and malformed
  structured responses each fall back to the deterministic
  profile behaviour with the reason recorded, never raise
  into the caller and never silently complete partial work;
- optional model configuration that is machine-specific and
  default-off, with clean offline behaviour: unconfigured or
  absent models report truthfully and every profile still
  works deterministically (item 9).
"""
from __future__ import annotations

import json
import re
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from copy import deepcopy
from typing import Any, Callable
from urllib.parse import urlsplit

SOURCE_REPO = "hrabanazviking/MindSpark_ThoughtForge"
SOURCE_BRANCH = "development"
SOURCE_HEAD_AUDITED = "68aa4d1cd29f6d6c57d1266e70833584c9b1a74e"
SOURCE_PACKAGE = "thoughtforge"
SOURCE_VERSION_AUDITED = "1.0.0"
SOURCE_LICENSE = ("CC BY 4.0 declared (README License section + "
                  "pyproject license field, both text-read at the "
                  "staged tree in X.06); NO standalone LICENSE "
                  "file exists at the audited HEAD; no source "
                  "incorporated into this fork")
SERVICE_SCHEMA = "runeforge.mindspark.service.v1"
PROFILE_SCHEMA = "runeforge.mindspark.profiles.v1"
DECISION_SCHEMA = "runeforge.mindspark.route-decision.v1"
BENCHMARK_SCHEMA = "runeforge.mindspark.benchmark.v1"
NOT_CONFIGURED = "not configured"
MAX_INPUT_CHARS = 20_000
MAX_OUTPUT_CHARS = 8_000

PROFILES = (
    {"name": "classifier", "task": "intent/tone classification",
     "method": "deterministic", "model_eligible": True,
     "max_output_tokens": 64, "latency_budget_ms": 50},
    {"name": "router", "task": "route proposal for a sub-request",
     "method": "deterministic", "model_eligible": True,
     "max_output_tokens": 64, "latency_budget_ms": 50},
    {"name": "reflection", "task": "short-form reflection",
     "method": "deterministic", "model_eligible": True,
     "max_output_tokens": 256, "latency_budget_ms": 100},
    {"name": "persona_tagging",
     "task": "persona section tagging (compiler artefact only)",
     "method": "deterministic", "model_eligible": False,
     "max_output_tokens": 0, "latency_budget_ms": 100},
    {"name": "budget_planner", "task": "token-budget planning",
     "method": "deterministic", "model_eligible": False,
     "max_output_tokens": 0, "latency_budget_ms": 25},
    {"name": "validation", "task": "inexpensive output validation",
     "method": "deterministic", "model_eligible": False,
     "max_output_tokens": 0, "latency_budget_ms": 25},
)
PROFILE_NAMES = tuple(p["name"] for p in PROFILES)
_PROFILES_BY_NAME = {p["name"]: p for p in PROFILES}

INTENTS = ("technical", "debugging", "planning", "editing",
           "brainstorming", "factual", "support", "conversation")
_INTENT_SIGNALS = {
    "debugging": ("error", "traceback", "exception", "bug",
                  "fails", "broken", "crash"),
    "technical": ("implement", "function", "api", "database",
                  "code", "server", "compile"),
    "planning": ("plan", "schedule", "steps", "roadmap",
                 "organise", "organize", "deadline"),
    "editing": ("rewrite", "edit", "proofread", "shorten",
                "rephrase", "polish"),
    "brainstorming": ("ideas", "brainstorm", "names for",
                      "suggest", "what if"),
    "factual": ("what is", "who is", "when did", "how many",
                "capital of"),
    "support": ("worried", "anxious", "tired", "overwhelmed",
                "sad", "struggling"),
}
_SECTION_TAGS = {
    "identity": ("identity", "who i am", "name", "origin"),
    "voice": ("voice", "speech", "tone", "speaks", "language"),
    "knowledge": ("knowledge", "knows", "lore", "history",
                  "facts"),
    "relationship": ("relationship", "friend", "family",
                     "bond", "trust"),
    "boundary": ("never", "must not", "boundary", "refuses",
                 "limit"),
    "memory": ("memory", "remembers", "past", "childhood"),
}


class MindSparkError(Exception):
    """Named refusal in the X.06 adapter layer."""

    def __init__(self, name: str, detail: str) -> None:
        super().__init__(f"{name}: {detail}")
        self.name = name
        self.detail = detail


def _profile(name: Any) -> dict:
    if name not in _PROFILES_BY_NAME:
        raise MindSparkError(
            "unknown_profile",
            f"profile {name!r} is not a MindSpark profile; "
            f"known: {list(PROFILE_NAMES)}")
    return _PROFILES_BY_NAME[name]


def _bounded_text(text: Any) -> str:
    if not isinstance(text, str):
        raise MindSparkError("input_not_text",
                             "profile input must be text")
    if len(text) > MAX_INPUT_CHARS:
        raise MindSparkError(
            "input_too_large",
            f"input is {len(text)} chars; the profile bound is "
            f"{MAX_INPUT_CHARS}")
    return text


# ---------------------------------------------------------- classifier

def classify_task(text: Any) -> dict:
    """Deterministic intent classifier (the rules-only baseline).

    Keyword-signal scoring in the spirit of the audited
    ThoughtForge InputRouter: distinct matching signals score,
    table order breaks ties, no signal at all is conversation.
    Same input, same output, no model call -- ever.
    """
    text = _bounded_text(text)
    lowered = " " + text.lower() + " "
    scores = {}
    for intent, signals in _INTENT_SIGNALS.items():
        hits = [s for s in signals if s in lowered]
        if hits:
            scores[intent] = hits
    if scores:
        best = max(scores, key=lambda k: (len(scores[k]),
                                          -list(_INTENT_SIGNALS).index(k)))
        matched = scores[best]
    else:
        best, matched = "conversation", []
    return {"profile": "classifier", "intent": best,
            "signals": matched, "signal_count": len(matched),
            "method": "deterministic", "model_called": False}


# ---------------------------------------------------------- reflection

_SENTENCE_RE = re.compile(r"[^.!?]+[.!?]")


def reflect_short(text: Any, *, max_chars: int = 400) -> dict:
    """Extractive short-form reflection (deterministic baseline).

    Picks the input's own sentences ranked by shared-word
    overlap with the whole text, in original order, bounded.
    The output is always a subset of the input's sentences --
    nothing is generated, so nothing can be fabricated.
    """
    text = _bounded_text(text)
    sentences = [s.strip() for s in _SENTENCE_RE.findall(text)
                 if s.strip()]
    if not sentences:
        sentences = [text.strip()] if text.strip() else []
    words = re.findall(r"[a-z0-9']+", text.lower())
    freq: dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1

    def score(sentence: str) -> int:
        return sum(freq.get(w, 0) for w in
                   re.findall(r"[a-z0-9']+", sentence.lower()))

    ranked = sorted(range(len(sentences)),
                    key=lambda i: (-score(sentences[i]), i))
    chosen: list[int] = []
    total = 0
    for i in ranked:
        if total + len(sentences[i]) > max_chars and chosen:
            continue
        chosen.append(i)
        total += len(sentences[i])
        if total >= max_chars:
            break
    picked = [sentences[i] for i in sorted(chosen)]
    return {"profile": "reflection", "reflection": " ".join(picked),
            "sentences_used": len(picked),
            "sentences_total": len(sentences),
            "method": "deterministic", "model_called": False}


# ---------------------------------------------------------- validation

def validate_output(profile_name: Any, raw: Any) -> dict:
    """Inexpensive validation (deterministic; never raises on content).

    Structured profiles (classifier / router) must answer with
    a JSON object carrying their required keys; free profiles
    must answer with non-empty bounded text. Malformed output
    is reported as data -- the caller falls back, per item 8.
    """
    _profile(profile_name)
    errors: list[str] = []
    parsed = None
    if not isinstance(raw, str):
        errors.append("output_not_text")
    elif not raw.strip():
        errors.append("output_empty")
    elif len(raw) > MAX_OUTPUT_CHARS:
        errors.append("output_too_large")
    elif profile_name in {"classifier", "router"}:
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            errors.append("output_not_json")
        else:
            if not isinstance(parsed, dict):
                errors.append("output_not_object")
                parsed = None
            else:
                required = ("intent",) if profile_name == "classifier" \
                    else ("route",)
                for key in required:
                    if key not in parsed:
                        errors.append(f"missing_key:{key}")
    return {"profile": "validation", "valid": not errors,
            "errors": errors, "parsed": parsed,
            "method": "deterministic", "model_called": False}


# ---------------------------------------------------------- budget planner

def plan_token_budget(profile_name: Any, *, input_chars: int,
                      parent_budget_tokens: Any = None) -> dict:
    """Token-budget planner (deterministic; Hermes enforces).

    The grant is the smallest of the profile cap, the parent
    turn's remaining budget when one is declared, and an
    input-scaled estimate. The planner proposes; enforcement
    stays with the Hermes turn that owns the budget (item 7).
    """
    profile = _profile(profile_name)
    if isinstance(input_chars, bool) or not isinstance(input_chars, int) \
            or input_chars < 0:
        raise MindSparkError("budget_input_invalid",
                             "input_chars must be a non-negative int")
    estimate = max(16, input_chars // 4 + 16)
    granted = min(profile["max_output_tokens"] or estimate, estimate)
    clamped_by = "profile_cap" if granted == profile["max_output_tokens"] \
        else "estimate"
    if parent_budget_tokens is not None:
        if isinstance(parent_budget_tokens, bool) \
                or not isinstance(parent_budget_tokens, int) \
                or parent_budget_tokens < 0:
            raise MindSparkError(
                "budget_input_invalid",
                "parent_budget_tokens must be a non-negative int")
        if parent_budget_tokens < granted:
            granted = parent_budget_tokens
            clamped_by = "parent_budget"
    return {"profile": "budget_planner", "for_profile": profile_name,
            "granted_tokens": granted, "clamped_by": clamped_by,
            "profile_cap": profile["max_output_tokens"],
            "parent_budget_tokens": parent_budget_tokens,
            "enforced_by": "hermes",
            "method": "deterministic", "model_called": False}


# ---------------------------------------------------------- persona tagging

def tag_persona_sections(compiled: Any) -> dict:
    """Tag sections of the SINGLE persona compiler's artefact.

    Section 41 item 5: persona kernel and context flow through
    the existing single RuneForge persona compiler
    (persona_runtime.PersonaCompiler), never a second
    personality file. This function therefore accepts ONLY a
    compiler artefact -- a dict carrying the compiler's
    ``index`` rows and ``kernel`` -- and refuses anything else
    by name. Kernel consistency is verified: every kernel
    source must resolve to an index row.
    """
    if not isinstance(compiled, dict) \
            or not isinstance(compiled.get("index"), list) \
            or not isinstance(compiled.get("kernel"), dict):
        raise MindSparkError(
            "persona_compiler_artefact_required",
            "persona tagging consumes only the compiled artefact "
            "of the single persona compiler (persona_runtime."
            "PersonaCompiler): a dict with index rows and a "
            "kernel. Raw documents, paths and hand-built dicts "
            "are refused -- there is no second personality file.")
    rows = []
    for entry in compiled["index"]:
        if not isinstance(entry, dict):
            continue
        heading = str(entry.get("heading", ""))
        body = str(entry.get("text", entry.get("content", "")))
        haystack = (heading + " " + body).lower()
        tag = "other"
        for name, signals in _SECTION_TAGS.items():
            if any(s in haystack for s in signals):
                tag = name
                break
        rows.append({"role": entry.get("role"),
                     "section_id": entry.get("section_id"),
                     "heading": heading, "tag": tag})
    index_keys = {(r.get("role"), r.get("section_id"))
                  for r in compiled["index"] if isinstance(r, dict)}
    kernel_sources = compiled["kernel"].get("sources", [])
    unresolved = [s for s in kernel_sources
                  if (s.get("role"), s.get("section_id"))
                  not in index_keys]
    return {"profile": "persona_tagging", "sections": rows,
            "section_count": len(rows),
            "kernel_consistent": not unresolved,
            "kernel_unresolved": len(unresolved),
            "compiler": "persona_runtime.PersonaCompiler (single)",
            "method": "deterministic", "model_called": False}


# ---------------------------------------------------------- router

def propose_route(profile_name: Any, text: Any, *,
                  parent_policy: Any = None,
                  model_configured: bool = False) -> dict:
    """A route PROPOSAL (item 7): deterministic-first, advisory only.

    The deterministic method is chosen unless the profile is
    model-eligible AND a model is explicitly configured AND
    the inherited parent policy permits model use. Even then
    the record is a proposal: final authority and budget
    enforcement stay in Hermes, and the consumer seam named is
    the existing A.E.S.I.R. cognition routing contract.
    """
    profile = _profile(profile_name)
    _bounded_text(text)
    policy = parent_policy if isinstance(parent_policy, dict) else {}
    policy_allows = policy.get("allow_model", True) is not False \
        and policy.get("egress", "local-only") != "none"
    use_model = bool(profile["model_eligible"] and model_configured
                     and policy_allows)
    return {"schema": DECISION_SCHEMA, "profile": profile_name,
            "route": "model" if use_model else "deterministic",
            "proposal_only": True, "final_authority": "hermes",
            "budget_enforced_by": "hermes",
            "consumer_seam": "volmarr-core cognition routing "
                             "(cognition.py / routing.py)",
            "parent_policy_inherited": True,
            "model_configured": bool(model_configured),
            "method": "deterministic", "model_called": False}


# ---------------------------------------------------------- model seam

def _loopback_only(base_url: Any) -> str:
    raw = str(base_url or "").strip().rstrip("/")
    parsed = urlsplit(raw)
    if parsed.scheme != "http" or parsed.hostname not in {
            "127.0.0.1", "localhost"} or parsed.username \
            or parsed.password or parsed.query or parsed.fragment:
        raise MindSparkError(
            "cloud_endpoint_refused",
            "the only model transport this adapter constructs is "
            "plain HTTP on a loopback host; any other endpoint is "
            "refused -- there is no cloud fallback (section 41 "
            "items 6 and 9)")
    try:
        port = parsed.port
    except ValueError as exc:
        raise MindSparkError("model_endpoint_invalid",
                             "model endpoint has an invalid port") from exc
    if port is None or not (1 <= port <= 65535):
        raise MindSparkError("model_endpoint_invalid",
                             "model endpoint requires an explicit port")
    return raw


class LocalModelRunner:
    """Bounded loopback OpenAI-compatible runner (optional, item 9).

    Constructed only from explicit machine-specific config.
    The request shape matches the fork's existing cognition
    endpoint contract ({model, messages, max_tokens}).
    """

    def __init__(self, base_url: Any, model: Any, *,
                 timeout_seconds: float = 5.0) -> None:
        self.base_url = _loopback_only(base_url)
        self.model = str(model or "")
        if not self.model:
            raise MindSparkError("model_not_configured",
                                 "a model name is required")
        self.timeout_seconds = min(60.0, max(0.5, float(timeout_seconds)))

    def __call__(self, prompt: str, max_tokens: int) -> str:
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": int(max_tokens)}).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + "/chat/completions", data=body,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request,
                                    timeout=self.timeout_seconds) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return str(payload["choices"][0]["message"]["content"])


def _deterministic_result(profile_name: str, text: str,
                          compiled: Any) -> dict:
    if profile_name == "classifier":
        return classify_task(text)
    if profile_name == "reflection":
        return reflect_short(text)
    if profile_name == "persona_tagging":
        return tag_persona_sections(compiled)
    if profile_name == "router":
        return propose_route(profile_name, text)
    if profile_name == "budget_planner":
        return plan_token_budget(profile_name,
                                 input_chars=len(text))
    return validate_output("classifier", text)


def run_profile(profile_name: Any, text: Any = "", *,
                runner: Callable[..., Any] | None = None,
                parent_policy: Any = None,
                compiled: Any = None,
                cancel: threading.Event | None = None,
                timeout_seconds: float = 5.0) -> dict:
    """Run one profile with the full item 8 failure discipline.

    Deterministic-first: without an eligible, configured,
    policy-permitted runner the deterministic method answers.
    With one, every failure mode -- cancellation, crash,
    out-of-memory, timeout, malformed structured output --
    falls back to the deterministic answer with the reason
    recorded. Partial model output is returned flagged as
    partial, never silently completed. This function never
    raises for model-side failures; adapter misuse (unknown
    profile, oversize input, non-compiler persona input)
    still raises MindSparkError by name.
    """
    profile = _profile(profile_name)
    if profile_name != "persona_tagging":
        _bounded_text(text)
    policy = parent_policy if isinstance(parent_policy, dict) else {}
    fallback = {"used": False, "reason": None}

    def deterministic(reason: str | None) -> dict:
        out = _deterministic_result(profile_name, text, compiled)
        out = deepcopy(out)
        out["fallback"] = {"used": reason is not None,
                           "reason": reason}
        out["engine"] = "deterministic"
        return out

    if cancel is not None and cancel.is_set():
        return deterministic("cancelled")
    if runner is None or not profile["model_eligible"]:
        return deterministic(None)
    if policy.get("allow_model", True) is False \
            or policy.get("egress", "local-only") == "none":
        return deterministic("parent_policy_denies_model")
    budget = plan_token_budget(profile_name, input_chars=len(text),
                               parent_budget_tokens=policy.get(
                                   "token_budget"))
    prompt = str(text)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(runner, prompt,
                                 budget["granted_tokens"])
            try:
                raw = future.result(timeout=timeout_seconds)
            except FutureTimeout:
                if cancel is not None:
                    cancel.set()
                return deterministic("model_timeout")
    except MemoryError:
        return deterministic("model_out_of_memory")
    except Exception:
        return deterministic("model_crash")
    if cancel is not None and cancel.is_set():
        return deterministic("cancelled")
    partial = False
    if isinstance(raw, dict):
        partial = bool(raw.get("partial"))
        raw = raw.get("text", "")
    if not isinstance(raw, str) or not raw.strip():
        return deterministic("model_malformed_output")
    if profile_name in {"classifier", "router"}:
        verdict = validate_output(profile_name, raw)
        if not verdict["valid"]:
            return deterministic("model_malformed_output")
    out = {"profile": profile_name, "output": raw[:MAX_OUTPUT_CHARS],
           "method": "model", "model_called": True,
           "engine": "model", "partial": partial,
           "complete": not partial,
           "fallback": fallback,
           "budget": budget}
    return out


# ---------------------------------------------------------- benchmark

BENCHMARK_CASES = (
    ("The function throws an exception and the traceback shows a bug",
     "debugging"),
    ("Implement an api function for the database server", "technical"),
    ("Make a plan with steps and a deadline for the roadmap",
     "planning"),
    ("Rewrite and shorten this paragraph, then proofread it",
     "editing"),
    ("Brainstorm ideas and suggest names for the project",
     "brainstorming"),
    ("What is the capital of Norway and how many people live there",
     "factual"),
    ("I feel worried and overwhelmed and struggling today", "support"),
    ("Hello, nice weather for a walk in the forest", "conversation"),
)


def benchmark_deterministic(cases: Any = None) -> dict:
    """Measure the deterministic baseline honestly, on this machine.

    Accuracy is agreement with the synthetic cases' authored
    labels; latency is wall time of the classifier measured
    here, now. No model numbers and no other machine's
    numbers are reported -- they were not measured (item 3).
    """
    rows = list(cases) if cases is not None else list(BENCHMARK_CASES)
    correct = 0
    latencies: list[float] = []
    for text, expected in rows:
        start = time.perf_counter()
        got = classify_task(text)["intent"]
        latencies.append((time.perf_counter() - start) * 1000.0)
        if got == expected:
            correct += 1
    latencies.sort()
    total = len(rows) or 1
    return {"schema": BENCHMARK_SCHEMA, "cases": len(rows),
            "correct": correct, "accuracy": correct / total,
            "latency_ms_mean": (sum(latencies) / total) if latencies else 0.0,
            "latency_ms_max": latencies[-1] if latencies else 0.0,
            "method": "deterministic",
            "measured_on": "this machine, at call time",
            "model_numbers": None,
            "cross_device_numbers": None}


# ---------------------------------------------------------- status / config

def model_from_ctx(ctx) -> dict:
    """Machine-specific optional model config (item 9), truthful."""
    base_url = str(ctx.get_config("mindspark_model_base_url", "") or "")
    model = str(ctx.get_config("mindspark_model_name", "") or "")
    record = {"configured": False, "base_url": base_url,
              "model": model, "reason": NOT_CONFIGURED}
    if not base_url and not model:
        record["reason"] = ("no model configured: every profile "
                            "runs deterministically (the section "
                            "41 item 4 default)")
        return record
    if not base_url or not model:
        record["reason"] = ("model configuration is incomplete "
                            "(base_url and model are both required)")
        return record
    try:
        _loopback_only(base_url)
    except MindSparkError as exc:
        record["reason"] = f"{exc.name}: {exc.detail}"
        return record
    record["configured"] = True
    record["reason"] = ("loopback model endpoint configured; "
                        "liveness is proven only by a run, never "
                        "assumed here")
    return record


def profile_catalog() -> dict:
    return {"schema": PROFILE_SCHEMA, "service": "volmarr-mindspark",
            "profiles": [dict(p) for p in PROFILES],
            "design": "deterministic-first (section 41 item 4): "
                      "the audited ThoughtForge methods that exist "
                      "as tested code are deterministic; model "
                      "inference is an optional loopback-only seam "
                      "whose benefit is not proven in this slice",
            "model_benefit_proven": False}


def mindspark_status(ctx, *, recorded_at: str = "") -> dict:
    """Truthful status for the live caller (items 1, 4, 9)."""
    model = model_from_ctx(ctx)
    enabled = bool(ctx.get_config("mindspark_enabled", False))
    return {
        "schema": SERVICE_SCHEMA,
        "service": "volmarr-mindspark",
        "availability": "contract-implemented",
        "enabled": enabled,
        "design": "deterministic-first",
        "model": model,
        "model_configured": model["configured"],
        "model_benefit_proven": False,
        "model_benefit_reason": (
            "no local model demonstrably beat the deterministic "
            "baseline on the profile tasks in this slice: no "
            "local model endpoint was live on the proof machine "
            "and the audited ThoughtForge tree carries no such "
            "benchmark either (ticket X06-T1)"),
        "source_repo": SOURCE_REPO,
        "source_branch": SOURCE_BRANCH,
        "source_head_audited": SOURCE_HEAD_AUDITED,
        "source_package": SOURCE_PACKAGE,
        "source_version_audited": SOURCE_VERSION_AUDITED,
        "source_license": SOURCE_LICENSE,
        "pin_taken_in_x06": False,
        "pin_reason": ("no pin taken: this adapter incorporates "
                       "no ThoughtForge source and binds no "
                       "runtime interface of the source repo; "
                       "the audited HEAD is recorded in the lock "
                       "entry in place of a pin"),
        "profiles": profile_catalog(),
        "production_ready": False,
        "production_ready_reason": (
            "deterministic profiles are contract-implemented and "
            "tested; model benefit, cross-device benchmarks and "
            "a live-model proof remain open (X06-T1/T2)"),
        "recorded_at": recorded_at,
    }


def service_record(ctx, *, recorded_at: str = "") -> dict:
    return mindspark_status(ctx, recorded_at=recorded_at)
