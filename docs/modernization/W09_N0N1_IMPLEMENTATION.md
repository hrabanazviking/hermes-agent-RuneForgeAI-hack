# W09 / N0+N1 Implementation Record (Team 01, 2026-11-08)

Wave: W09 New projects - N0 project review, N1 capability bus.
Branch yrsa/hermes-team-01 in worktree ~/hermes-team-01 on
purplelongship, based on banked main
b93cd4ad62176bd3b91302d238b9cb1d9de91038 (W08 banking closure).
Commit-only: the keeper banks serially; nothing was pushed or
merged here. No Docker used. No core files touched - all code is
plugin-side (plugins/volmarr-core/), per the ground rules.

README.md untouched: sha256
336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3
verified before the work and at the end.

## What was delivered - N1 capability bus (contract slice)

### 1. Module - plugins/volmarr-core/capability_bus.py (486 lines)
- Versioned runeforge.capability.v1 descriptor validation:
  strict, and malformed contracts are refused by name (named
  problem strings), never repaired silently, never defaulted.
- In-memory CapabilityRegistry with TTL expiry enforced on every
  read, plus lazy discovery from a directory of JSON descriptor
  files; malformed files are refused by name in the discovery
  record, never silently skipped.
- Pure fail-closed permission policy (authorize): who may call
  which action on whose data, on which device, with what human
  approval, and where outputs may travel. local-private data
  never travels beyond local; shared never travels to public or
  cloud; write actions always need approval; side-effect
  services need approval beyond read/propose; cross-owner calls
  need scoped auth plus approval; owner-only services refuse
  non-owners; device allowlists are enforced. Every refusal
  names its reason; an absent descriptor is a refusal.
- Provenance-required result and error envelopes: a result
  cannot be constructed without service, reviewed version,
  source reference, timestamp and confidentiality class; error
  envelopes use exactly the roadmap section 20 uniform error
  categories (unavailable, unauthorized, validation_failure,
  version_mismatch, resource_exhausted, timeout,
  partial_result, completed).
- JobBook: separately tracked jobs with receipts and
  idempotency keys - creating the same job twice returns the
  same record, never a duplicate; status transitions are
  guarded by name.
- Three built-in seed descriptors for tools that already exist
  in this fork, at their real plugin.yaml versions:
  volmarr-astrology 0.7.0 (calculate_astrology),
  volmarr-tarot 0.3.0 (draw_tarot), volmarr-seidr 0.4.0
  (compose_seidr). builtin_status() validates each descriptor
  and stat-checks the adapter plugin.yaml file in this tree.
  Availability is contract-implemented for all three - NOT
  proven-by-live-probe, and no descriptor here dispatches a
  call.

### 2. CLI - plugins/volmarr-core/cli.py (+68/-1)
New read-only family: hermes volmarr capabilities
{list|show|validate|authorize}. list/show/validate serve the
built-in descriptors and their tree validation; authorize runs
the permission policy for one built-in service and exits 0 only
when the decision is allowed. The usage line gains the
capabilities family name.

### 3. Tests - tests/plugins/test_volmarr_capability_bus.py
16 contract tests (342 lines): descriptor validation and
refusal by name, registry expiry and replacement, discovery
refusing malformed files by name, policy allow/refuse matrix
(plain local read, absent service, unoffered action, write and
side-effect approval, privacy travel, owner rules, device
restriction), provenance-required envelopes, error categories,
idempotent and transition-guarded jobs, seed descriptors real
and present, and CLI list/show/validate/authorize end to end
through the real argparse registration and dispatcher.

## Verified counts (from log files on purplelongship)

- New tests only (~/team01-w09-newtests.log): 1 file,
  16 tests passed / 0 failed. Exit 0.
- Full Volmarr/Kista contract set (~/team01-w09-contracts.log):
  132 files, 1,079 passed / 7 failed / 1 skipped. That is the
  W08 banked baseline (131 files, 1,063 passed) plus exactly
  the 16 new W09 tests - zero regressions.
- The 7 failures were name-checked and are exactly the known
  live-transport set: 5 in test_volmarr_core_plugin.py
  (Verdandi socket/discovery), 1 in
  test_volmarr_verdandi_stimuli.py, 1 in
  test_volmarr_voice_runner.py (loopback). No live Verdandi
  service runs on this laptop; these failures pre-date W09 and
  are byte-identical in kind to every prior wave baseline.
- Test-runner note, recorded honestly: the canonical
  scripts/run_tests.sh env staging for this worktree failed
  twice on a network fetch (GitHub 504 for the kittentts wheel,
  a direct-URL dependency) before any test ran. The runs above
  therefore used the runner with its documented HERMES_PYTHON
  path, pointing at an already-staged test environment whose
  uv.lock and pyproject.toml are byte-identical to this
  worktree (sha256 584af160... for uv.lock in team-01,
  team-09 and hermes-hack-forge alike). The runner, its
  per-file isolation and its counts are unchanged; only the
  interpreter source differs, and only because the staging
  download was unavailable.

## Code review and bugs

The inherited uncommitted module, CLI diff and test file were
reviewed in full before running: descriptor validation, expiry
semantics, discovery refusal, policy matrix, envelope
provenance, job idempotency and seed versions (checked
against the three plugin.yaml files in this tree: 0.7.0 /
0.3.0 / 0.4.0 - all match). No defect was found and no fix was
needed; the suite passed as written. Bugs fixed in W09: none,
because none were found in scope - recorded plainly rather
than padded.

## N0 half - status

The N0 triage of all 18 section 19 projects was assigned as
part of this wave (docs/modernization/N0_PROJECT_TRIAGE.md).
That document is NOT delivered in this commit: its transfer
to the laptop was interrupted mid-write during this run and
the partial file was removed rather than banked half-made.
It remains an open W09 remainder for the keeper to re-run;
nothing in this record claims the triage is on disk. The
category framework, evidence sources and honesty rules for it
stand as briefed (roadmap section 19 categories; evidence
only from section 19, the W08 integration matrix, campaign
state and CUSTOMIZATIONS.md; unproven marked unproven;
Sagnaskemma cross-referenced to the blocked W08 matrix
row 24).

## Honest remainders (NOT done, NOT claimed)

1. Section 20 / section 30 W09 gate - 3 live heterogeneous
   tools participating: NOT proven. The seeds are
   contract-implemented descriptors only; there is no live
   dispatch, no live probe, and service absence behaviour is
   proven only at policy level (absent descriptor refused),
   not against three real running apps.
2. Descriptor signing: NOT implemented. The roadmap asks the
   registry to cache SIGNED descriptors; this slice validates
   shape and provenance fields but verifies no signature.
3. CBOR: NOT implemented. Descriptors are JSON only; the
   roadmap JSON/CBOR-style wording is only half met.
4. Generated Python/TypeScript client fixtures and
   compatibility probes: NOT built.
5. GitHub discovery job for new projects: NOT built. Per
   section 19 it may only write a proposed diff behind a
   review flow; no scanning or importing was done here.
6. N0 triage document: not delivered this run (see above).
7. Per-service start/stop ownership, cancellation and
   progress streams for jobs, and cross-host authenticated
   transport: designed in the roadmap, not implemented in
   this slice (JobBook tracks status transitions only).
8. Follow-on waves W10-W12 consume the bus (N2/N3 coding and
   Samtal/Samkoma, N4 embodiment, N5 edge/research) - they
   inherit every remainder above.

## Files in this wave

- plugins/volmarr-core/capability_bus.py (new, 486 lines)
- plugins/volmarr-core/cli.py (+68/-1)
- tests/plugins/test_volmarr_capability_bus.py (new, 342 lines)
- docs/modernization/W09_N0N1_IMPLEMENTATION.md (this record)
- CUSTOMIZATIONS.md (one W09 ledger row added)
