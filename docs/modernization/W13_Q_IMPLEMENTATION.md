# W13 / Phases Q0-Q4 — Production (implementation record)

Team 05, branch `yrsa/hermes-team-05`, 2026-11-08.
Roadmap sections 25-29 (Phases Q0-Q4) + section 28.3 evidence
hierarchy + section 30 W13 gate + section 32 release scorecard.
Base: banked main `dfd6c68b8f` (W12 closure). Design draft:
`docs/modernization/W13_Q_DESIGN_DRAFT.md` (commit `c2dc57a5d7`).
Implementation commits: `2ab17241e3` (production.py + CLI),
`f3c3aa7239` (contracts), plus this record's commit.

## Delivered (contract level, plugin-side only)

- `plugins/volmarr-core/production.py` — Q0 private/public
  boundary: account descriptor validation keeps
  `agent_identity_id` and `credential_owner_id` as distinct
  required fields (independent of display name); conflation is
  refused by name (`account_identity_conflated:...`). Data-flow
  audit: every packet carries provenance/destination labels; a
  local-private source routed to a non-local destination without
  a scoped, reversible, logged owner election is refused by name
  (`q0_private_egress_refused:<destination>`). `FlowLog` audit
  records carry labels and decisions ONLY — payload text is never
  copied in. Canary contract: `CanaryStore` public queries search
  public documents only, so a planted local-private canary is
  unretrievable through the public path by construction; a
  local-only session record counts every non-local destination
  (embeddings, logging and model fallback included) and the
  contract passes only at zero external requests. Per-account
  disconnect/export/delete are recorded by `OperatorBook` as
  operator actions with metadata-only receipts. One agent
  inheriting another agent's Drive/email/calendar scope is
  refused by name (`q0_scope_inheritance_refused:<scope>`).
- Q1 security/threat model: `threat_checklist` evaluates the 12
  section 26 threat items (prompt injection, heading/role
  impersonation, path escape/symlink/include, malformed UTF-8,
  giant-file DoS, supply chain, secret exposure, profile
  leakage, privilege escalation, egress, WAL/index attacks,
  replayed capability descriptors); an item counts only with a
  named evidence reference, gaps are listed by name. Rendered
  receipts/audit/scorecard output passes through exact-value
  redaction, and `scan_rendered` verifies a planted secret
  canary does not appear in it.
- Q2 performance/durability: `performance_record` is an evidence
  record STRUCTURE only — P50/P95/P99 for index throughput,
  query latency, persona compile, prompt preparation,
  first-token, tool invocation, audio latency and gateway
  restart recovery, plus cache/FTS/backlog counters. A field
  without a measured value from a named benchmark log is
  `unmeasured` — partial measurements stay unmeasured and are
  never estimated. NO benchmark was run or claimed in W13.
- Q3 evidence hierarchy: `promotion_decision` implements
  section 28.3 verbatim — documented-only < contract-implemented
  < installed-integration < end-to-end-working <
  production-qualified, each stage gated on its named minimum
  proof (design ref; module+tests refs; dependency+discovery+
  probe refs; call+output+side-effects+failure-path refs;
  security+persistence+performance+operating-limits+rollback+
  cross-platform refs). Promotion without the minimum proof is
  refused by name (`evidence_promotion_refused` + one
  `proof_missing:<key>` per gap); backward/same-stage moves are
  not promotions; deferred/blocked is valid only with an
  explicit reason (`deferred_reason_required` otherwise).
- Q4 operator experience: `production_status` aggregates from
  disk + the W08 integration ledger (`integration_status`) + the
  W09 capability registry (`builtin_status`); a reader failure
  degrades that block to `unavailable` with the reason named.
  An engine counts as working ONLY at the end-to-end-working or
  production-qualified ledger stage; at W13 banking the ledger's
  26 rows contain NO such row (13 contract-implemented verified,
  3 contract-implemented partially verified, 2 installed-
  integration, 7 documented-only, 1 deferred/blocked), so
  `working_count` is honestly 0 and no engine is shown as
  working. Docs deliverables, measured from this tree by path:
  beginner setup PRESENT (`docs/modernization/LAUNCH_RECIPE.md`),
  threat model PRESENT (`SECURITY.md`), migration ABSENT (no
  dedicated migration guide; `UPSTREAM_SYNC.md` covers upstream
  intake only), troubleshooting ABSENT, benchmark instructions
  ABSENT. Linked profile, model location and offline status are
  reported `unknown` (no live profile context in this slice);
  `live_connection` is `not-claimed`.
- Section 32 release scorecard: `evaluate_scorecard` over the 15
  items; `met` only with a named evidence reference, else
  `unmet:<item>` or `deferred:<item>:<reason>`; `releasable` is
  True only when every item is met. The CLI default scorecard
  supplies NO evidence and the five known deferrals
  (`KNOWN_DEFERRED`: W00.03-ENC on the backup item, W08
  contract-only rows on installed smoke, Q2 unmeasured on
  performance, the 7 live-transport failures on hidden
  regressions, W00.05/W00.06 on docs/code agreement) — the
  honest result is 0 met / 10 unmet / 5 deferred, NOT
  releasable. No green scorecard is fabricated.
- CLI: `hermes volmarr production {status|scorecard|audit}`
  (scorecard exits 1 while not releasable; audit returns the
  threat gaps, the all-unmeasured performance record and the Q0
  policy names in a W09 provenance envelope).

## Gate evidence

- New battery: `tests/plugins/test_volmarr_production.py`,
  29 passed / 0 failed (log `~/team05-w13-newtests.log`).
- Full Volmarr/Kista contracts on the team tree via
  `scripts/run_tests.sh` (HERMES_PYTHON staged-env path, the
  accepted W09-W12 fallback; staged env byte-identical per the
  W09 uv.lock proof, sha256 584af160...): counts recorded in
  CAMPAIGN_STATE_MODERNIZATION.md at banking (log
  `~/team05-w13-contracts.log`; the run was serialized behind
  the Mythic Coder and Runmal suites by
  `~/team05-w13-waiter.sh`). Grading baseline is the W12 line:
  136 files = 1,142 passed / 7 failed / 1 skipped, the 7 being
  the known live-transport set; this slice adds one file and
  29 tests (expected 137 files = 1,171 passed / 7 failed /
  1 skipped, to be verified from the log at banking).
- README.md untouched (sha256 336813d11bbe... before and after).

## Bugs found / fixed in scope

- None in the delivered code — recorded plainly. All files were
  authored on-device (no chunked base64 transport), py_compile
  verified before every commit, and the new battery passed on
  its first run.
- One defect in this slice's own test infrastructure, found and
  fixed before it could bite: the first contract waiter
  (W12-style `pgrep -f 'pytest -q'` / `'unittest discover'`)
  deadlocked — its launching shell's command line contained the
  same literals and stayed alive as the waiter's parent, so the
  waiter would have waited on its own launcher forever. The
  orphan shell and waiter were killed (both this slice's own
  processes; no other campaign touched) and waiter v2 anchors
  its patterns at the interpreter path
  (`^[^ ]*python[^ ]* -m pytest` / `-m unittest discover`),
  launched fully detached via setsid. Verified live: v2 waits
  only on the real Mythic/Samverk python suites.

## Honest remainders (NOT declared complete)

- The release is NOT releasable at W13: scorecard 0 met /
  10 unmet / 5 deferred with the default honest inputs. The
  campaign does not complete on a fabricated green scorecard.
- The 7 live-transport contract failures remain open exactly as
  at every prior wave (5 core-plugin Verdandi socket/discovery,
  1 Verdandi stimuli, 1 voice-runner loopback; no live Verdandi
  service on this laptop) — section 28.2 real-socket diagnosis
  is still E.01 work, not claimed here.
- W00 remains open: W00.03-ENC backup encryption (Volmarr's
  word, not re-asked), W00.05 fixture archive + COMPAT_MANIFEST
  fate, W00.06 boundary review.
- Q1 is a checklist evaluator, not a penetration/fuzz campaign:
  no threat item is claimed evidenced except by named
  references a caller supplies; with no supplied evidence all
  12 items are gaps.
- Q2 ran no benchmarks: every performance/durability field is
  `unmeasured`; degenerate-corpus and power-cut durability
  tests from section 27 are not run by this slice.
- Contract-only remainders carried by W05/W09-W12 stay at their
  honest stages (live persona surfaces, capability-bus live
  dispatch, Samtal/Samkoma live connections, Heimdall/WYRD live
  wiring, MimirAlloc evaluation, Yggdrasil live mesh): none is
  promoted by this slice, and the Q4 status surface labels them
  accordingly.
- Operator receipts, flow audit records and the session record
  are in-memory contract structures in this slice; no on-disk
  receipt store, dashboard UI, or live gateway wiring is built
  or claimed.
- Missing operator docs (migration guide, troubleshooting,
  benchmark instructions) are named absent by the status
  surface and its `next_required_action`; authoring them is
  follow-on documentation work, not silently assumed.
