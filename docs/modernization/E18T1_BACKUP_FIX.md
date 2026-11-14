# E18-T1/T2 fix slice - hollow fresh-profile backup (Team 01, 2026-11-14)

**Outcome: E18-T1 FIXED (ensure-first backup/export, truthful
empty restore), E18-T2 FIXED (stale ravens path prose in
COMPONENT_LICENSES.md). Plugin-side only; no core files
touched; no pin moved; README.md untouched.**

Base: banked main `d0fae07a9d0af8c3dd7750ed498e9adb9013335a`
(E.18 closure), team worktree `~/hermes-team-01` on
`yrsa/hermes-team-01`, clean before edits, README sha256
`336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`
verified before and after.

## E18-T1 root cause

`PersonaOps.export_bundle()` built the bundle's source list
solely from the W03 manifest (`ManifestStore.load()`). On a
profile whose corpus was never ingested the manifest has no
documents, so the bundle carried ZERO sources - yet
`export_bundle()` returned `status: ok`, `backup()` (which
delegates to it) returned `status: ok` with a complete-looking
integrity manifest, and `restore()` of that hollow bundle
returned `status: ok` with `written: []`. Ingestion
(`ensure_library()`) happened only as a side effect of a
confirmed `persona edit`, or programmatically; no CLI verb
ensured the library before export. Proven live on both E.18
hardware targets (see E18_HARDWARE_VERIFICATION.md, ticket
E18-T1) - a backup verb that can silently bundle nothing is a
footgun on exactly the disaster path it exists for.

## Chosen semantics: ensure-first (plus truthful refusals)

The E.18 record listed two directions - ensure the library
first, OR refuse/warn when the manifest is unbuilt. This slice
implements **ensure-first**, the record's first-listed
direction, because it is the semantics the existing design
already trusts everywhere else:

- `ensure_library()` is idempotent by design (its docstring's
  own contract): re-ingest preserves each existing record's
  privacy class and destinations; only genuinely new documents
  take the W03 default (`private`). Ensuring before export
  therefore changes nothing for an already-ingested profile -
  the existing W07 battery's expectations are untouched.
- The codebase already treats ensure as the normal pre-step:
  a confirmed `edit_section` calls `ensure_library()` before
  re-syncing, and the `ops` test fixture calls it as a matter
  of course. Backup/export was the outlier, not the rule.
- Refuse/warn-first would have made the disaster-path verb
  fail on exactly the profiles most likely to need it (a
  fresh profile that was never otherwise touched), pushing
  the operator to discover a second verb before the first
  one works. Ensure-first makes `backup` simply correct.

Two truthful-refusal guards ride the same fix, for the cases
ensure-first cannot repair:

- `export_bundle()` raises `PersonaOpsError("export_empty")`
  if the persona config declares documents but, after
  ensuring, none could be ingested from disk (e.g. the source
  files are missing). It never writes a hollow bundle file.
- `restore()` raises `PersonaOpsError("backup_empty")` when
  the bundle it was handed carries zero sources - the shape
  of every hollow backup written before this fix. The check
  runs after manifest/bundle integrity verification and
  before any write, so a refused restore creates nothing.
  (Restore only ever restores bundle sources; a zero-source
  bundle restores nothing by construction, so refusing it
  loses no legitimate case.) Both refusals surface through
  the CLI's existing `PersonaOpsError` path (JSON error on
  stderr, exit 1).

`backup()` additionally returns the `sources` count it
actually bundled, so the number is visible in the verb's own
output instead of only inside the bundle file.

## What changed (T1)

- `plugins/volmarr-core/persona_ops.py`:
  `export_bundle()` calls `self.ensure_library()` before
  compiling/reading the manifest, and refuses hollow exports
  as above; `backup()` surfaces `sources`;
  `restore()` refuses zero-source bundles as above.
  No other verb's behaviour changes; no core files touched.
- `tests/plugins/test_volmarr_persona_ops.py`: three new
  regression tests (below).

## Regression tests (T1)

Built on a genuinely never-ingested profile (a fresh home
whose own manifest is asserted empty as a precondition;
files present on disk):

- `test_backup_fresh_profile_bundles_real_sources` - backup
  returns ok with `sources == 3`; the bundle carries exactly
  persona/core.md, persona/bible.md, persona/diary.md, each
  hash- and byte-identical to the on-disk sources; restoring
  that backup writes all three byte-identically.
- `test_export_fresh_profile_bundles_real_sources` - the
  export verb itself bundles the 3 real sources.
- `test_restore_empty_bundle_refused` - a forged pre-fix
  hollow backup (zero sources, backup manifest recomputed so
  integrity checks PASS, exactly the on-disk shape a pre-fix
  hollow backup has) is refused with `backup_empty`, and the
  restore target is never created.

## E18-T2 fix

`COMPONENT_LICENSES.md` lines 13-14 (Muninn and Huginn rows)
cited the ravens tree at `~/workspace/ravens` (the VM layout).
Both rows now cite `~/ravens`, the tree the
`[tool.uv.sources]` sibling binding actually resolves on
purplelongship (HEAD `fc761f020b39`, untouched by this
slice). Path prose only - pins, package commits, licenses
and every other byte of the rows unchanged. The full gate
below includes the integration-ledger tests that parse this
file.

## CUSTOMIZATIONS.md ledger

No row added. The ledger records intentional divergences
from stock upstream Hermes; `volmarr-core` is fork-only code
with no upstream counterpart, and this slice corrects that
plugin's own bug without touching any upstream surface - it
is not a new divergence, and the W07 persona-ops row already
covers the plugin. The T2 change is a factual path
correction in a ledger-parsed doc, recorded here.

## Test evidence

- Targeted: `scripts/run_tests.sh
  tests/plugins/test_volmarr_persona_ops.py` =
  11 passed / 0 failed (8 pre-existing + 3 new).
  Log: `~/team01-e18t1-targeted.log`.
- Full fork contract gate: `scripts/run_tests.sh tests/plugins/test_volmarr_*.py tests/plugins/test_kista_*.py` =
  137 files, 1,174 passed / 7 failed / 1 skipped. The 7 are
  name-identical to the banked baseline live-transport set
  (5x test_volmarr_core_plugin.py, 1x
  test_volmarr_verdandi_stimuli.py, 1x
  test_volmarr_voice_runner.py); the passed count is the
  1,171 baseline + the 3 new tests - ZERO regressions.
  Log: `~/team01-e18t1-fullcontracts.log`, marker
  `~/team01-e18t1-gate.done`.

## Remaining tickets

E18-T3 (banner label on tag-less clones) and E18-T4 (ravens
pin not stageable from the repo on a second machine) are
unchanged by this slice and remain open exactly as recorded
in E18_HARDWARE_VERIFICATION.md - both are Volmarr's call,
not defects this slice may improvise around. No new bug was
discovered during this slice.
