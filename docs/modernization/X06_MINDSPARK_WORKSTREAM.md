# X.06 MindSpark ThoughtForge — ecosystem workstream 6 of 15 (Team 01, 2026-11-14)

Roadmap section 41 (Part VII workstream 6 of 15) names
MindSpark ThoughtForge: make tiny models genuinely useful.
Source: https://github.com/hrabanazviking/MindSpark_ThoughtForge,
observed branch `development`. The section's own first
instruction governs the slice: *first determine which methods
exist as tested code rather than assume all performance
claims.* This record follows the X.01–X.05 slice shape.

## Audit (re-measured, not inherited)

Staged directly under $HOME at ~/mindspark-x06 (full clone of
the `development` branch; staging under $HOME per the
standing rule). HEAD verified three ways: clone HEAD ==
`git ls-remote` development ==
68aa4d1cd29f6d6c57d1266e70833584c9b1a74e, which is also
exactly the integration lock's recorded `current_head` — the
HEAD has NOT moved since the E0 draft measurement, so no
pin-move question arises. Other branches exist (main at
6ca6dae9, plus feature branches) and tags v1.0.0–v1.2.0; the
roadmap's observed branch is `development` and that is what
was audited.

The tree is real, heavily tested code, not pseudocode:
package `thoughtforge` 1.0.0 (pyproject), src/thoughtforge
171 Python modules / ~104,700 LOC across cognition,
inference, knowledge, ETL and refinement subpackages, 149
test files. Its own campaign (CAMPAIGN_STATE.md in the
staged tree) records Parts I–VIII complete with a full gate
of 4,262 collected / 4,260 passed / 1 skipped / 1 known
environment failure (D-ENV-1) at TF-160.

Interfaces audited on the current development head
(section 41 item 1):

- **Model runner**: inference/backends.py (backend
  detection/selection: CUDA/ROCm/Metal/Vulkan/DirectML/CPU),
  inference/backend_contract.py, unified_backend.py and
  per-backend modules (llama.cpp, Ollama, HF, ONNX,
  A.E.S.I.R., LM Studio, TurboQuant), inference/profiles.py
  (hardware profiles + ProfileSelector) and
  profile_runner.py.
- **Task decomposition / scaffolding**: cognition/router.py
  (InputRouter), cognition/scaffold.py (ScaffoldBuilder),
  scaffold_registry.py, scaffold_strategies.py.
- **Retrieval scaffolds**: knowledge/ store, scoring,
  retrieval_precision, bond graph; etl/ ingestion line.
- **Verification**: refinement/ enforcement, citation
  enforcement, format enforcement, quality marks,
  truth/scoring honesty modules; cognition/determinism.py,
  error_honesty.py, latency_budgets.py; cost discipline in
  refinement/cost_discipline.py.
- **Prompting**: cognition/prompt_builder.py +
  prompt_contract.py; cognition/persona_compiler.py
  (1,611 LOC — ThoughtForge's own compiler, a separate
  artefact from the fork's single persona compiler; see
  item 5 below).
- **Hermes binding**: hermes_binding.py (TF-158, 2,773 LOC)
  already files ThoughtForge as a cognition provider shaped
  on this fork's volmarr-core contract, read from a build
  tree on the ThoughtForge side. It is a filing, not a
  runtime dependency of this fork, and X.06 does not import
  it.

**The decisive finding (item 4 evidence).** The
ThoughtForge methods that exist as tested code for the
section 41 profile tasks — InputRouter, ScaffoldBuilder,
prompt builder, hardware profile selection, cost/latency
discipline — are DETERMINISTIC and heuristic-first:
router.py's own header states "Heuristic-first
classification: keyword/pattern matching with no model
calls." The model backends exist as code, but the audited
tree carries no benchmark demonstrating a small model
beating those deterministic methods on classifier / router /
reflection / tagging / planning / validation tasks.
Independently, on purplelongship at proof time no local
model endpoint was live: Ollama is installed but its server
was not running, and the A.E.S.I.R. loopback endpoint
(127.0.0.1:18434) answered 401 without its key. Per item 4 —
*only use model inference for decisions that benefit
demonstrably* — this slice therefore builds the
**deterministic-first design and says so honestly**: model
inference is an optional seam whose benefit is NOT PROVEN
here (ticket X06-T1).

**Own-suite re-run.** The audited tree's targeted suites
(router decision table, scaffold registry/strategies, prompt
builder contract, phase-3 cognition, latency budgets,
small-model floor, profile runner, backend fallback,
local-first routing, cost discipline, persona compiler
verdict, Hermes binding) were re-run on purplelongship with
the system interpreter (log ~/team01-x06-tf-targeted.log):
**454 passed / 1 failed**. The one failure
(test_tf033_latency_budgets.py::
test_vm_profile_is_what_this_machine_auto_selects) asserts
the host auto-selects the VM/desktop_cpu hardware profile —
true on the machine that test was written for, false here:
purplelongship has a GPU and the selector correctly
auto-selects desktop_gpu. That is a host-expectation
environment artifact, not a defect in the audited methods;
the selector's correct GPU detection on this machine is
itself evidence the profile code works.

**License (text-read at the staged tree).** There is NO
standalone LICENSE or COPYING file at the audited HEAD.
The license is DECLARED as CC BY 4.0 in two places, both
read directly: the README "License" section ("This work is
licensed under the Creative Commons Attribution 4.0
International (CC BY 4.0) License", README sha256
024b76deafee…) and the pyproject `license = { text =
"CC BY 4.0" }` field (pyproject sha256 acb28765c0f5…; its
trove classifiers also carry the inconsistent line
"License :: Free for non-commercial use", noted here as a
declaration inconsistency in the source repo, not resolved
by this slice). No ThoughtForge source is incorporated into
this fork — the adapter below is original volmarr-core code
written against the audited interfaces — so no license
obligation is triggered either way.

## Registry (section 35 duty)

MindSpark already has matrix row 21 and a lock entry — no
new row (X.04 in-place precedent). INTEGRATION_MATRIX.md
row 21 and the integration-lock.json MindSpark entry were
updated IN PLACE: adapter cell now names the built
deterministic-first adapter, license cell records the
CC BY 4.0 declaration as text-read in X.06, evidence stage
documented only → contract implemented, verdict
reference-only → current — X.06 executed. **No pin was
taken**: pinned stays null, because the adapter incorporates
no ThoughtForge source and binds no runtime interface of
the source repo; the audited HEAD is recorded in the lock
entry's verification notes and in this record in place of a
pin. The lock was edited in its established compact format;
a field-level diff in the patch harness confirms only the
MindSpark entry changed and every other entry and top-level
field is value-identical after a JSON round-trip.
Verification counts are unchanged at 29 verified / 0
partially verified / 0 blocked (the entry was and remains
verified). COMPONENT_LICENSES.md is not touched: no pin
exists to record there. CUSTOMIZATIONS.md gains exactly one
ledger row for the X.06 adapter, following the directed
X.04/X.05 row precedent.

## Build (plugin-side only — section 41 items 1–9)

New module plugins/volmarr-core/mindspark.py (original
code; no core edits, no ThoughtForge source copied), four
default-off config keys in plugin.yaml (mindspark_enabled,
mindspark_model_base_url, mindspark_model_name,
mindspark_token_budget), and the CLI family below.

- **Profiles (item 2).** The six small-model cognition
  profiles exist as data (runeforge.mindspark.profiles.v1)
  and as deterministic implementations: classifier
  (keyword-signal intent classification in the spirit of
  the audited InputRouter), router (route proposals),
  reflection (extractive short-form reflection — output is
  always a subset of the input's own sentences, so nothing
  can be fabricated), persona_tagging, budget_planner
  (grant = min of profile cap, parent budget, input-scaled
  estimate), validation (inexpensive structured/text output
  checks that report malformed output as data, never raise
  on content).
- **Baseline + benchmark (items 3–4).** Every profile's
  default method IS the deterministic rules-only baseline.
  benchmark_deterministic() measures that baseline on
  synthetic authored cases on the machine it runs on:
  accuracy (label agreement) and wall-clock latency,
  reported with model_numbers and cross_device_numbers
  explicitly null — no Z13/Pi/other-device number is
  claimed, because none was run (ticket X06-T2).
- **Single persona compiler (item 5).** Persona tagging
  consumes ONLY the compiled artefact of this fork's
  existing single persona compiler
  (persona_runtime.PersonaCompiler — a dict carrying its
  index rows and kernel). A raw document, a path, or a
  hand-built dict without the compiler's shape is refused
  by name (persona_compiler_artefact_required). There is
  no second personality file. Kernel consistency is
  verified on every tagging call: every kernel source must
  resolve to an index row, and the verdict is reported
  (the section 41 "verified kernel consistency" gate).
- **Policy inheritance (item 6).** Sub-requests take the
  parent turn's policy as data; allow_model False or
  egress "none" means the model is never invoked (proven
  by a contract asserting the runner was not called).
- **Route proposals (item 7).** propose_route returns a
  proposal_only record with final_authority and
  budget_enforced_by both "hermes", naming the existing
  A.E.S.I.R. cognition routing contract (cognition.py /
  routing.py) as the consumer seam. Honest limit: **no
  HugrGate code exists in this tree** (grep across plugins
  and docs finds none), so there is no HugrGate interface
  to integrate with in this slice; inventing one would
  violate the audit-first rule. Ticketed as X06-T3.
- **Failure discipline (item 8).** run_profile wraps the
  optional model seam with cancellation (a pre-set or
  mid-run cancel event), timeout, crash, out-of-memory and
  malformed-structured-output handling — each falls back
  to the deterministic profile answer with the reason
  recorded (cancelled / model_timeout / model_crash /
  model_out_of_memory / model_malformed_output). Partial
  model output is returned flagged partial with
  complete False, never silently completed.
- **Optional model config (item 9).** Machine-specific,
  default-off, loopback-only: LocalModelRunner refuses any
  non-loopback or non-HTTP endpoint by name
  (cloud_endpoint_refused) at construction, so there is no
  hidden cloud fallback anywhere in the design. Unconfigured
  or incomplete configuration reports truthfully and every
  profile still works deterministically (clean offline
  behaviour).

## Live caller (section 28.2)

New CLI family beside the existing volmarr verbs:
`hermes volmarr mindspark {status|profiles|classify|benchmark}`.
Real proof in disposable profile homes (logs
~/team01-x06-liveproof.log and ~/team01-x06-modelproof.log):

- Unconfigured home: status answers rc 0 with
  model_configured false and the honest reason ("no model
  configured: every profile runs deterministically");
  profiles lists the six profiles rc 0; classify of a
  factual question answers intent factual, engine
  deterministic, rc 0; benchmark answers accuracy 1.0 on
  the 8 synthetic cases with this machine's measured
  latency, model numbers null, rc 0; the bare verb exits 2
  with usage.
- Configured home (synthetic loopback endpoint
  127.0.0.1:18777, model name synthetic-tiny): status
  answers model_configured true while stating liveness is
  proven only by a run. A harness then drove the REAL
  LocalModelRunner over loopback HTTP against a synthetic
  endpoint (a test double, not a real model — labelled as
  such in the log): run_profile returned engine model with
  the endpoint's structured answer, and against a dead
  endpoint it fell back to deterministic with reason
  model_crash. No real model run is claimed anywhere in
  this slice.

## Tests and gate

- X.06 targeted battery via scripts/run_tests.sh
  (tests/plugins/test_volmarr_mindspark_x06.py +
  test_volmarr_integration_ledger.py +
  test_volmarr_sagnaskemma_x05.py): 3 files, **40 passed /
  0 failed** (log ~/team01-x06-targeted.log). The 12 X.06
  contracts pin: the section 41 six profiles, baseline
  accuracy/determinism, proposal-only routing with Hermes
  authority, budget adherence (parent cap, profile cap,
  zero budget), malformed-as-data validation, extractive
  bounded reflection, single-compiler refusal + kernel
  consistency (consistent and ghost-source cases), crash /
  OOM / malformed / cancellation fallback, partial-output
  flagging, policy inheritance with a never-invoked runner,
  cloud endpoint refusal, truthful unconfigured status, and
  the CLI family (status/profiles/classify/benchmark rc 0,
  bare verb rc 2).
- Full fork gate via scripts/run_tests.sh on the team tree
  (the canonical volmarr + kista contract file list):
  **143 files, 1,241 passed / 7 failed / 1 skipped** (log
  ~/team01-x06-fullcontracts.log) — the X.05 baseline of
  1,229 passed + exactly the 12 new X.06 contracts, and the
  7 failures name-identical to the known live-transport set
  (5× test_volmarr_core_plugin.py, 1×
  test_volmarr_verdandi_stimuli.py, 1×
  test_volmarr_voice_runner.py). ZERO regressions.
- README.md untouched: sha256
  336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3
  before and after.

## Honest remainders / tickets

- **X06-T1 — model benefit unproven.** No local model has
  demonstrably beaten the deterministic baseline on the
  profile tasks. Needs a live local model on purplelongship
  (e.g. Ollama serving a small model, or the A.E.S.I.R.
  endpoint with its key) plus an accuracy/latency/RAM/tokens
  comparison run through benchmark harnesses on both paths.
  Until then the deterministic-first design stands and
  model_benefit_proven stays False everywhere.
- **X06-T2 — cross-device benchmarks not run.** Section 41
  item 3 names Z13, secondary laptop, Pi 5 and other edge
  devices. Only purplelongship numbers exist (deterministic
  baseline, measured live). No other device's numbers are
  claimed or estimated.
- **X06-T3 — HugrGate seam absent.** No HugrGate code or
  interface exists in this tree to integrate route
  proposals through; proposals currently name the existing
  A.E.S.I.R. cognition routing contract. If a HugrGate
  surface lands, wire propose_route's consumer seam to it.
- **X06-T4 — ThoughtForge's own persona compiler.** The
  audited repo carries its own persona_compiler.py; X.06
  deliberately does not bind it — section 41 item 5
  requires the fork's single compiler, and two compilers
  would be a second personality pipeline. Recorded as a
  considered-and-refused binding, not an oversight.
- **X06-T5 — source license declaration inconsistency.**
  The source repo declares CC BY 4.0 in README + pyproject
  while a pyproject trove classifier says "Free for
  non-commercial use" and no LICENSE file exists. Owned by
  the source repo's own campaign; recorded here so no later
  slice inherits the lock's stale "NONE detected (API)"
  line as fact.
- production_ready stays FALSE in every X.06 record: the
  deterministic profiles are contract-implemented and
  tested, but model benefit (T1), cross-device evidence
  (T2) and a live-model proof remain open.
