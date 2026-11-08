# W13 / Phases Q0-Q4 — Production (design draft)

Team 05, branch `yrsa/hermes-team-05`, 2026-11-08.
Roadmap sections 25-29 (Phases Q0-Q4) + section 30 W13 gate +
section 32 release scorecard + section 28.3 evidence hierarchy.
Base: banked main `dfd6c68b8f` (W12 closure). Draft only — no code
in this commit; implementation follows in this branch.

## Slice shape (following W09-W12 pattern)

One plugin-side module, `plugins/volmarr-core/production.py`,
plus CLI `hermes volmarr production {status|scorecard|audit}`,
plus deterministic contracts in
`tests/plugins/test_volmarr_production.py`, plus
`docs/modernization/W13_Q_IMPLEMENTATION.md` and a
CUSTOMIZATIONS.md ledger row. No core patches, no live services,
no credentials. Everything not proven is named deferred/blocked
with its reason, per section 28.3 — never promoted by renaming.

## Q0 — private/public boundary (section 25)

- Account descriptor validation: `agent_identity_id` and
  `credential_owner_id` are distinct required fields, independent
  of display name and of the human owner's accounts; a descriptor
  that conflates them is refused by name.
- Data-flow audit record: provenance + destination labels on
  every packet; a local-private source routed to a non-local
  destination without a scoped, reversible, logged owner election
  is refused by name (`q0_private_egress_refused:<destination>`).
- Canary contract: a planted local-private canary string must be
  unretrievable through the public query path and must produce
  zero external requests in a local-only session record
  (embeddings, logging and model fallback included).
- Per-account disconnect/export/delete are recorded as operator
  actions with receipts; one agent inheriting another agent's
  Drive/email/calendar scope is refused by name.

## Q1 — security and threat model (section 26)

- Checklist evaluator over the section 26 threat list (prompt
  injection, heading/role impersonation, path escape / symlink /
  include, malformed UTF-8, giant-file DoS, supply chain, secret
  exposure in logs/previews/exports/telemetry, profile leakage,
  privilege escalation, egress, WAL/index attacks, replayed
  capability descriptors). Each item counts only with a named
  evidence reference (test/log), exactly like the W12
  MimirAlloc gate; gaps are listed by name.
- Secret-scan contract: a planted secret canary must not appear
  in rendered receipts, audit records or scorecard output.

## Q2 — performance and durability (section 27)

- Evidence record structure only: P50/P95/P99 fields for index
  throughput, query latency, persona compile, prompt prep,
  first-token, tool invocation, gateway restart recovery, plus
  cache/FTS/backlog counters. A field without a measured value
  from a named benchmark log is `unmeasured` — never estimated.
- No benchmark is run or claimed in the design step; the W13
  gate records which measurements exist at banking.

## Q3 — testing matrix and evidence hierarchy (section 28)

- Evidence promotion guard implementing section 28.3 verbatim:
  documented-only < contract-implemented < installed-integration
  < end-to-end-working < production-qualified, plus
  deferred/blocked with reason. Promotion without the minimum
  proof for the target stage is refused by name.
- Scorecard input: every prior wave's claimed stage is read from
  its implementation record; contract-only remainders from
  W05/W09-W12 stay at their honest stage.

## Q4 — operator experience (section 29)

- `production status` aggregates, from disk + the W08
  integration ledger + W09 capability registry: services,
  versions, capabilities, linked profile, offline status, model
  location, source privacy and next required action. Unknown or
  unavailable engines are labelled honestly (W08 matrix stages),
  never shown as working.
- Docs deliverable list for the implementation record:
  beginner setup, migration, threat model, troubleshooting,
  benchmark instructions — each marked present/absent by path.

## Section 32 release scorecard

Evaluator over the 15 scorecard items, each `met` only with a
named evidence reference, else `unmet:<item>` or
`deferred:<item>:<reason>`. `releasable` is True only when every
item is met. Expected honest outcome at W13 banking: NOT
releasable, with the unmet set named — chiefly the 7
live-transport failures (section 28.2 real-socket diagnosis
still open, no live Verdandi service on this laptop),
W00.03-ENC backup encryption (Volmarr's word, not re-asked),
W00.05 fixture archive, W00.06 boundary review, and every
contract-only remainder carried by W05/W09-W12. The campaign
does not complete on a fabricated green scorecard.

## Invariants

- README.md untouched (sha256 336813d11bbe...).
- Tests via scripts/run_tests.sh only; counts from log files.
- One heavy suite at a time on purplelongship (shared laptop).
- Banking is the keeper's serialized step, in wave order.
