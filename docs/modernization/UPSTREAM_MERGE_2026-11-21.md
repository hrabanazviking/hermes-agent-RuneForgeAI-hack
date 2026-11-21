# Upstream Merge 2026-11-21 — v0.23.3 Release Intake

Staged release intake on branch `integration/upstream-2026-11-21`, executed
2026-11-21 on purplelongship under Volmarr's approval of the same morning
("proceed to make all that need my permission"). Pattern: W01 guarded intake
(UPSTREAM_SYNC.md + scripts/sync_upstream.py), pin-the-release per the
integration lock. This record is the W01.09-style intake record for the
v0.23.3 pin move; the banking closure is in CAMPAIGN_STATE_MODERNIZATION.md.

## Pin and provenance

- Personal base: `fe0efbc9f0f00fd61caebcd8767202da8315c695` (origin/main at
  intake; X.15 closure head).
- Selected upstream: official release tag `v0.23.3` (tag object
  `2861fe3744f8134b782659438961a4f69ab5d495`), peeled commit
  `caafe5389ae585ef77387a962aee05b1bcf17029` (2026-11-20).
- Merge-base is exactly `0e28218d19f04d7df0bcafbede975cfa73ce1794` (the
  2026-11-09 upstream-main intake), so this intake is the 9,919 upstream
  commits the fork lacked against the pin (12,433 commits past the v0.23.0
  pin 2bd378ed1b).
- Reviewed merge commit: `70bca6b50e037060472e134716ecdb6687da662f`, parents
  = personal base + pin. Follow-up fix commit: `391f4b1d55` (sessiondb
  contract import, below).
- Diff of the merge: 8,466 files staged (upstream restructure waves:
  redact module split, hermes_state -> persistence/sqlite relocation).

## Procedure and one recorded deviation

- Followed UPSTREAM_SYNC.md and scripts/sync_upstream.py. As at W01, the
  script merges a branch ref; the peeled pin was placed at the
  remote-tracking ref `upstream/v0.23.3-pin` and the script was run in its
  supported `--no-fetch --branch v0.23.3-pin` mode. Clean-tree refusal,
  no-commit no-ff merge, README restoration and conflict reporting all ran
  as documented.
- README proof: sha256
  `336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3` before
  the merge, after the merge, and after the merge commit — byte-identical.

## Conflicts: exactly two files, three hunks

Pre-merge watch (merge-tree simulation) and the guarded merge agreed:
`agent/redact.py` and `pm/environment.py` only.

1. `agent/redact.py` (1 hunk). Upstream split the module (redact_hermes_home,
   redact_credential_stores, redact_approval_display, redact_db_url,
   redact_vault_values, ...). The fork's only delta against the merge-base
   was the vault-value registry (f286e20000): scope-aware signatures
   (`scope=None` routed through `hermes_home_key`) over the registry upstream
   had inline at the base. Resolution: upstream side taken in redact.py
   (the merged file is byte-identical to the pin's; the registry is
   re-exported from `agent/redact_vault_values`), AND the fork's scope
   generalization ported into `agent/redact_vault_values.py` — `_vault_scope
   (scope=None)` via `hermes_home_key` (verified byte-identical in both
   trees), `scope=` on all three functions, fork header wording restored.
   Nothing taken wholesale the other way: fork callers
   (`agent/secret_sources/registry.py` passes `scope=self.redaction_scope`;
   kista contracts call `clear_vault_redaction_values(scope=...)`) keep
   working unchanged.
2. `pm/environment.py` (2 hunks). Fork had refactored `lock()` onto
   `_lock_command()` (W02 release-age gate scoped to registry sources,
   local-path packages exempted by name); upstream added
   `upgrade_packages` (`--upgrade-package` per requirement) to `lock()`.
   Resolution: COMBINED, under Volmarr's combine-both ruling of 2026-11-09
   for this same file — `_lock_command` gains `upgrade_packages` and
   `lock()` passes it through; the fork gate scoping and the upstream
   targeted-upgrade behaviour both hold on the same command.

## Intake adaptation (not a conflict)

Upstream relocated the SessionDB schema: `SCHEMA_SQL`/`SCHEMA_VERSION`
moved from `hermes_state_common` to `persistence/sqlite/_schema_ddl.py`.
Verified before touching anything: the relocated DDL is a strict superset
of the fork's schema (identical except one added upstream column,
`sessions.prompt_cache_clock`); `SCHEMA_VERSION` is 33 on both sides; no
production code imported the names from the old module — only the fork
contract `tests/plugins/test_volmarr_sessiondb.py`, which failed at
collection on the merged tree. Fix `391f4b1d55` imports them from the new
canonical home (the same import upstream's own storage fixture uses); the
file then passes 4/4.

## Verification — all via scripts/run_tests.sh on purplelongship

- Baseline first, per the W01 method: the 3 known-failure files run on the
  untouched personal base give 4 passed / 7 failed, the 7 names
  byte-identical to the banked live-transport set (5x
  test_volmarr_core_plugin.py, 1x test_volmarr_verdandi_stimuli.py, 1x
  test_volmarr_voice_runner.py) — log ~/hermes-v0233-baseline3.log.
- Full fork contracts (tests/plugins/test_volmarr_*.py +
  test_kista_*.py) on the merged tree: **152 files = 1,348 passed / 7
  failed / 1 skipped, zero errors** — exactly the X.15 banked baseline;
  the sorted FAILED-name set is md5-identical to the pre-intake baseline
  set. Zero regressions (log ~/hermes-v0233-contracts2.log).
- Targeted redact/vault/secret family (tests/agent, 50 files): **1,504
  passed / 0 failed**; one import error, tests/agent/
  test_vault_key_storage.py (`No module named 'keyring'`), reproduced
  identically on the pure pin tree — environmental, not an intake
  regression (logs ~/hermes-v0233-redact.log,
  ~/hermes-v0233-keyring-control.log).
- Targeted pm suite (tests/pm): merged tree 158 files = 971 passed / 32
  failed / 168 errors / 83 skipped; pure pin control 157 files = 962 / 32 /
  168 / 83. FAILED and ERROR name sets identical between the two trees.
  Root cause on both: the worker-contract fixture asserts a real `uv`
  (`tests/pm/_fixtures.py`: "the worker contract requires real uv") plus
  network/TLS lifecycle tests — host-environmental on this machine, present
  in upstream's own tree, not intake regressions. The merged tree's +1 file
  / +9 passed is the fork's extra pm test file (logs
  ~/hermes-v0233-pm.log, ~/hermes-v0233-pm-control.log).
- Targeted state suites (tests/hermes_state + tests/persistence_sqlite,
  the upstream state-restructure area): **363 files = 2,815 passed / 0
  failed / 17 skipped** (log ~/hermes-v0233-state.log).
- Native smoke: CLI entry runs on the merged tree — `Hermes Agent
  v0.23.3+482.g391f4b1 (2026.9.24) · upstream fe0efbc9 · local 391f4b1d
  (+9921 carried commits)`, clean exit; plugin discovery in a disposable
  HERMES_HOME lists all 9 fork plugins as bundled at their frozen versions
  (volmarr-core 0.26.0, volmarr-voice 1.0.0, volmarr-astrology 0.8.0,
  volmarr-rpg 0.8.0, volmarr-seidr 0.4.0, volmarr-tarot 0.3.0, volmarr-hamr
  0.4.0, volmarr-smidja 0.1.0, kista-secret-source 0.2.0) — logs
  ~/hermes-v0233-smoke.log, ~/hermes-v0233-plugins.log.

## Pin move

integration-lock.json `upstream` section: v0.23.3 commit + tag object
recorded, merge_base / last_intake advanced to the 2026-11-09 intake point,
intake_banked updated. The ADAPTER_COMPATIBILITY_MATRIX.md table is a W02
verification snapshot (2026-11-07) and is left as the historical record it
is; the lock is the carrying document, as its own header states.

## Not in this intake / deferred honestly

- The full upstream test suite was not run (selected suites per the W01
  gate were). Suites outside the touched areas were not re-baselined.
- `hermes pm lock` regeneration was not attempted; the merged uv.lock is
  upstream's as merged, and the gate env staged hash-verified from it.
- Live cross-surface wiring checks (gateway/session owner, Verdandi live
  transport) remain the standing live-transport baseline: no live Verdandi
  service runs on this laptop, unchanged by this intake.
