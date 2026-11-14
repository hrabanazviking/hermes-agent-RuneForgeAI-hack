# X.02 Lifthrasir - ecosystem workstream 2 of 15 (Team 01, 2026-11-14)

**Outcome: AUDIT EXECUTED + REGISTRY ROW ADDED + READ-ONLY
DIAGNOSTICS PROTOTYPE BUILT. NO PIN TAKEN, NO EXISTING PIN
MOVED, NO REPAIR OR DEPLOYMENT CAPABILITY CLAIMED.** Roadmap
Part VII section 37, second of the fifteen ecosystem
workstreams, taken in roadmap order after X.01 (section 36)
banked. The fork gains, plugin-side in volmarr-core: a
read-only local diagnostics adapter, the versioned
DiagnosticReport contract with redaction, and a proposal-only
layer behind `hermes volmarr lifthrasir {status|diagnose|propose}`.
Section 37 scopes the initial Hermes tooling as
observe/report/propose only; this slice builds exactly that
research track and nothing beyond it.

## Audit (re-measured, not inherited)

- Source: `hrabanazviking/RuneForgeAI-Lifthrasir`, branch
  `main`. `git ls-remote` 2026-11-14: HEAD ==
  `refs/heads/main` ==
  `69fb1ed99cb238cacd9f35c057c6936137041724`; **no tags**.
  Tree cloned under $HOME at `~/lifthrasir-audit`, HEAD
  verified. No repository was created. (The same HEAD is the
  Lifthrasir campaign's own banked seat on purpleraider; this
  fork slice is a read-only audit plus original bridge code -
  the source repo's sole write owner is its own campaign.)
- README self-describes **research stage**: the planned
  autonomous Linux features are not yet implemented. The tree
  has nevertheless grown real executable code under its own
  separate 64-slice campaign (banked at code/fixture level):
  - `src/lifthrasir/` - 44 Python modules (collectors,
    acceptance, approval, confinement, DAG executor and kin);
    `src/` overall ~28,798 LOC; `tests/` - 71 Python files;
    plus `lab/` collectors and a read-only Phase 2 host
    observer running on purpleraider.
  - Its activation Phase 3 (host repairs) and Phase 4
    (upstream delivery) have **not started**. There is **no
    pyproject.toml / setup.py** at the root, no package
    version, no CHANGELOG and no release - no verified
    install path exists, so no pin could honestly be taken.
  - HEAD is a moving target (the source campaign commits its
    own keeper ticks to main); the HEAD recorded here is the
    audit-time measurement.
- **License: GPL-2.0-only - verified at text level.**
  `LICENSE` at the audited HEAD is the GNU GPL Version 2
  (June 1991) text, sha256
  `8177f97513213526df2c...` (prefix as recorded in the lock).
  Consequence recorded plainly: GPL-2.0 source is **not
  incorporated** into this fork; the bridge below is original
  volmarr-core code written against the section 37 contract.

## Registry (section 35 duty)

Lifthrasir had NO row in the ledger. Row 28 is added to
`docs/modernization/INTEGRATION_MATRIX.md` and a matching
entry to `docs/modernization/integration-lock.json` (compact
format preserved). Adapter mode `prototype`, evidence stage
`contract implemented`, verification `verified` (audit
facts), **pinned: null - no pin taken** (research-stage
source, no installable package). No existing engine pin
moved. Count assertions in
`test_volmarr_integration_ledger.py` /
`test_volmarr_production.py` updated 27 -> 28 rows
(verified 26 -> 27) for the new row.

## Build (plugin-side only - section 37 items 1-3 and 7)

`plugins/volmarr-core/lifthrasir.py` (new, fork-only):

- **Read-only diagnostics adapter** (item 1): systemd failed
  units + version, bounded journal (warning+, 50 lines),
  kernel uname, hostname, installed package metadata
  (dpkg-query), filesystems, low-memory telemetry
  (/proc/meminfo + pressure), and configuration drift -
  reported **only** against a caller-supplied baseline;
  without one the report says `baseline_not_supplied` and
  guesses nothing. Every command comes from a fixed allowlist
  of read-only argv vectors, runs unprivileged with no shell;
  any other argv (mutating verbs, shells, unknown tools) is
  refused by name (`mutating_command_refused`) before it can
  run.
- **DiagnosticReport contract** (item 2):
  `runeforge.lifthrasir.diagnostic-report.v1` records the
  commands executed, privileges used (unprivileged only -
  a tampered privilege claim fails validation), error codes,
  timestamps, and captured evidence as sha256 over the
  **redacted** capture. Redaction rules cover secret
  assignments, bearer tokens, token shapes (GitHub/AWS/Slack),
  private keys and `/home/<user>` paths, applied before
  anything is recorded.
- **Proposal-only layer** (item 3): from a validated report,
  Hermes may record an explanation, a candidate fix or an
  upstream bug report - each evidence-linked, explicitly
  `proposed-unexecuted`, requiring human approval.
  `execute_proposal` refuses by name, always
  (`execution_refused`): prototype repair in a disposable
  lab and any rollback recipe are a later slice (X02-T1,
  section 37 items 4-5).
- **Separation is structural** (item 7): every record carries
  a lifecycle map (diagnosed / repair-proposed /
  repair-executed / deployed / verified-resolved); a report
  can only ever assert `diagnosed`, and validation rejects
  any report claiming execution, deployment or resolution.

No network, no root escalation, no mutation anywhere. No
CUSTOMIZATIONS.md row (fork-only code, E18-T1/X.01
precedent).

## Live caller (section 28.2)

`hermes volmarr lifthrasir {status|diagnose|propose}` in a
disposable profile home (log `~/team01-x02-liveproof.log`):
status reports `contract-implemented`,
`autonomous_features_claimed: false` and the audited source
facts; `diagnose` produced a real DiagnosticReport
(`diag-70f2f067b5b751a7`, stage `diagnosed`, 6 allowlisted
commands executed) whose findings include the host's real
failed unit `apport-autoreport.service`; `propose` recorded
an evidence-linked, unexecuted explanation proposal from
that report.

## Tests and gate

- Targeted: `tests/plugins/test_volmarr_lifthrasir.py` +
  `test_volmarr_integration_ledger.py` +
  `test_volmarr_production.py` via scripts/run_tests.sh =
  3 files, **53 passed / 0 failed** (log
  `~/team01-x02-targeted.log`). The lifthrasir contracts pin
  report completeness, redaction of a seeded secret, the
  read-only guarantee, the diagnosis/repair separation,
  truthful privilege recording and CLI status.
- Full fork gate: 139 files, **1,193 passed / 7 failed /
  1 skipped** - the X.01 baseline of 1,186 plus 7 new
  lifthrasir tests; the 7 failures are name-identical to the
  known live-transport set, ZERO regressions (log
  `~/team01-x02-fullcontracts.log`).
- Merged tree byte-identical to the tested team tree.
  README untouched (sha256 336813d11bbe...).

## Honest remainders / tickets

- X02-T1: prototype repair + rollback in a disposable
  namespace/VM (section 37 items 4-5) - not built; execution
  stays refused by name until a lab slice passes recovery
  tests.
- X02-T2: evidence bundles for upstream patch submission
  with license checks (item 6) - not built.
- X02-T3: Mythic Agent/Draupnir proposal-and-review wiring
  (item 8) - not built.
- X02-T4: Kubuntu / Raspberry Pi Linux / disposable ARM64
  independent test proof (item 9) - the adapter ran live on
  purplelongship (Kubuntu-family x86_64) only; no
  cross-device claim is made.
- The source project's own Phase 3/4 (host repairs, upstream
  delivery) has not started upstream of this fork; nothing
  here pre-empts it.
