# E.18 Verify build/docs/versions at two named hardware targets - verification record (Team 01, 2026-11-14)

**Outcome: BOTH TARGETS PASS, with named remainders
ticketed E18-T1..T4. No pin moved, no fork code changed.**
The banked tree (6ee85497da, E.17 closure) was staged
cold and verified end to end on the two named hardware
targets: (1) purplelongship, x86_64, and (2) Mimir
(purpleviking1), aarch64 Raspberry Pi 5. On both: the
environment stages natively from uv.lock (no Docker),
the CLI runs, all 9 fork plugins are discovered at the
versions their plugin.yaml files declare, PyYAML is
6.0.3, and the staged Python is 3.14.9. The W07-R5
remainder - cross-machine persona backup/restore -
closed in this slice: a backup created on purplelongship
restored byte-identical on Mimir, a backup created on
Mimir restored byte-identical on purplelongship, and a
one-byte-corrupted backup was refused whole on Mimir.
Docs/versions agreement was checked across
integration-lock.json, INTEGRATION_MATRIX.md,
COMPONENT_LICENSES.md, the plugin manifests and both
CLIs' own reports; every disagreement found is
ticketed below, none silently fixed.

## Scope and method

- Tree under test: banked main
  6ee85497da9607b957b511edc336337866536215 (E.17
  closure). Team worktree ~/hermes-team-01 at that SHA,
  clean before edits; the only file this slice adds is
  this record.
- Target 1 staging: scripts/u2-cold-install.sh (the
  W02/U2 proof script) run from the team worktree into
  a disposable HERMES_HOME under $HOME
  (~/hermes-cold-home-20261114-063437, KEEP_HOME=1 so
  the staged env could be interrogated; removed after
  the slice). Evidence: ~/team01-e18-evidence-t1/ on
  purplelongship (cold-install.log, version.txt,
  plugins.txt, pyyaml.txt, ravens-*.log, shas.txt,
  version-offline.txt).
- Target 2 staging: fresh clone of the fork repo to
  ~/hermes-e18 on the Pi (HEAD measured =
  6ee85497da9607b957b511edc336337866536215), staged
  with HERMES_HOME=~/hermes-e18-home and
  HERMES_RUNTIME_DIR=~/hermes-e18-runtime - fully
  isolated: the Pi's live ~/.hermes (18 GB) and its
  existing ~/hermes-agent checkout (v0.14.0 tree at
  6b2cb5c266, pre-existing untracked research/) were
  measured and NOT modified; Samtal on port 8787 was
  verified listening before and after, never touched.
  Evidence: ~/hermes-e18-stage.log, ~/hermes-e18-
  ravens*.log on purpleviking1.
- Persona drill fixture: synthetic persona e18ette
  (core/bible/diary, hashes 7b39408f... / 71d7e4f6...
  / 97631c47...), built identically in each target's
  disposable home. Disposable profiles only; no real
  user data was read or moved.

## Target 1 - purplelongship (x86_64): PASS

- Host: x86_64, system Python 3.14.4, 39 GB RAM.
- Cold install: `== COLD INSTALL OK` - environment
  staged from uv.lock through PM, hash-verified.
- Banner: `Hermes Agent v0.23.0+2940.g6ee8549
  (2026.9.24) - upstream 6ee85497`; install dir the
  team worktree; Python 3.14.9 (PM tool store);
  OpenAI SDK 2.54.0; pinned uv 0.13.5
  (x86_64-unknown-linux-gnu).
- Plugins: all 9 fork plugins discovered, versions
  equal to plugin.yaml on disk - volmarr-core 0.26.0,
  volmarr-voice 1.0.0, volmarr-astrology 0.7.0,
  volmarr-tarot 0.3.0, volmarr-seidr 0.4.0,
  volmarr-rpg 0.8.0, volmarr-hamr 0.4.0,
  volmarr-smidja 0.1.0, kista-secret-source 0.2.0.
  All report "not enabled" in a cold home - opt-in
  by design; with volmarr-core enabled in the
  disposable home's config, its verbs answer (below).
- PyYAML 6.0.3 importable in the staged env.
- Ravens: absent from the default env (opt-in extra
  law holds); with --extra volmarr-ravens from a
  scratch tree under $HOME, muninn imports from
  /home/volmarr/ravens/muninn and the suites pass:
  muninn 36 passed, huginn 27 passed. Sibling tree
  HEAD fc761f020b39 = the lock pin.
- Cloud-denied start: staged venv binary under a dead
  proxy + minimal env prints the banner.
- Ledger: `hermes volmarr engines validate` in the
  staged env returns {"problems": [], "status":
  "ok"}; `engines status` reports verification
  counts {verified: 25, blocked: 1}, the ravens tree
  present with head == pin, and
  readme_sha256_at_promotion =
  336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3,
  equal to the banked tree's README sha256 measured
  in this slice.

## Target 2 - Mimir / purpleviking1 (aarch64 Pi 5): PASS with remainders E18-T3/T4

- Host: aarch64, system Python 3.11.2, 16 GB RAM,
  197 GB free. Pre-existing ~/hermes-agent measured
  (HEAD 6b2cb5c266, pyproject version 0.14.0 - an
  older upstream-era checkout, NOT the fork) and
  left untouched.
- Clone + stage: fork cloned to ~/hermes-e18, HEAD =
  6ee85497da9607b957b511edc336337866536215 (== Target
  1 tree); README sha256 identical
  (336813d11bbe...). PM staged natively on aarch64:
  uv 0.13.5 (aarch64-unknown-linux-gnu), CPython
  3.14.9 linux-aarch64 - the same staged Python and
  uv versions as Target 1; no Docker anywhere.
- Banner: `Hermes Agent vgit.6ee8549 (2026.9.24) -
  upstream 6ee85497`; Python 3.14.9; OpenAI SDK
  2.54.0. The local-SHA component equals Target 1
  exactly; the version LABEL differs (E18-T3).
- Plugins: all 9 fork plugins discovered at versions
  identical to Target 1 and to plugin.yaml
  (volmarr-core 0.26.0 shown enabled - the
  disposable home's config enables it; the other
  eight opt-in, as designed).
- PyYAML 6.0.3; ravens absent from the default env.
- Ravens extra on aarch64: sibling tree ~/ravens =
  the published repo at f12fb39 (see E18-T4);
  `uv sync --frozen --extra volmarr-ravens` exit 0;
  muninn imports from /home/pi/ravens/muninn;
  suites on aarch64: muninn 36 passed, huginn 27
  passed - identical counts to Target 1.
- Cloud-denied start: staged binary under a dead
  proxy prints the banner.
- Ledger: `engines validate` returns exactly ONE
  problem - the ravens tree HEAD (f12fb39) differs
  from the recorded pin fc761f020b39 (E18-T4);
  `engines status` otherwise agrees: counts
  {verified: 25, blocked: 1}, readme sha at
  promotion equal to the staged tree's README.

## W07-R5 cross-machine backup/restore: PROVEN both directions

Persona backup schema on both targets:
`runeforge.persona-backup` version 1, bundle schema
`runeforge.persona-ops`, encryption labelled
`unencrypted-local` (Volmarr's W00.03-ENC ruling).
Backups moved machine-to-machine over the LAN with
sha256 verified at every hop.

- purplelongship -> Mimir: backup of the e18ette
  fixture created in Target 1's cold home via
  `hermes volmarr persona backup` (3 sources;
  manifest bundle sha256 84dd6edb...). Restored on
  Mimir into the non-live ~/hermes-e18-restore-
  target: status ok, written = persona/core.md,
  persona/bible.md, persona/diary.md, each
  byte-identical to the Target 1 source fixture
  (7b39408f... / 71d7e4f6... / 97631c47...).
- Corruption refusal on Mimir: the same backup with
  one byte appended to bundle.persona.json -
  restore refused whole with
  `backup_integrity_failed` (bundle.persona.json);
  the target directory was never created.
- Mimir -> purplelongship: the identical fixture
  built and backed up on the Pi (3 sources, same
  per-file hashes; generations.json byte-identical
  to Target 1's - the generation record is
  deterministic across architectures, and ingest
  assigned identical document IDs doc_5694e09f...
  on both machines). Restored on purplelongship
  into ~/team01-e18-restore-from-t2: status ok,
  all 3 files byte-identical.
- Schema-migration honesty: no legacy backup schema
  exists to migrate FROM - the format was born in
  W07 at version 1 and both targets speak exactly
  that version, so what this slice proves is
  cross-machine, cross-architecture schema
  AGREEMENT (same schema strings, same integrity
  rules, deterministic IDs/hashes). A true
  old-to-new migration case remains untestable
  until a version 2 exists; it is not claimed here.
- Execution note (recorded, not hidden): the first
  Mimir backup attempt produced a 0-source bundle
  because the ingest harness had not in fact
  transferred (its fetch had silently failed and
  stderr was discarded in that invoke). The hollow
  restore it produced (status ok, written = []) is
  exactly the E18-T1 failure shape; the drill was
  re-run with every step verified, giving the
  results above.

## Docs/versions agreement (banked tree vs measured reality)

- integration-lock.json fork.plugins versions ==
  plugin.yaml on disk == both CLIs' plugin tables:
  all 9 agree, no drift.
- Every engine pin in integration-lock.json appears
  in INTEGRATION_MATRIX.md and COMPONENT_LICENSES.md
  (full or documented short form); the ravens rows
  record pin fc761f0 with package commits 4eafc31 /
  54dd839 and the published f12fb39 - consistent
  with the trees measured on both targets.
- The lock's fork.head (0d62b657) is the W08
  promotion base and the lock itself says so
  (head_note: the tree the rows were verified
  against, not a moving target) - by design, not
  drift.
- Hermes version: banner base v0.23.0 == the lock's
  upstream v0.23.0 pin (2bd378ed); local component
  == banked HEAD on both targets.
- Disagreements found: E18-T2 (stale ravens path in
  COMPONENT_LICENSES.md), E18-T3 (banner label on
  tag-less clones), E18-T4 (pin not stageable from
  the repo on a second machine). No doc was edited
  in this slice: T2's fix is one line but the same
  file is parsed by the ledger tooling, and the
  E.14/E.16 precedent tickets doc conflicts for the
  banking decision rather than fixing mid-audit.

## Tickets (honest remainders)

- **E18-T1** (fresh-profile CLI backup can be
  hollow): on a profile whose corpus was never
  ingested, `hermes volmarr persona backup` returns
  status ok with a bundle carrying ZERO sources,
  and restoring it returns ok having written
  nothing. No CLI verb calls ensure_library before
  export; ingestion happens only as a side effect
  of a confirmed `persona edit`, or programmatically
  (the W07 battery's pattern, used in this slice on
  both targets). Proven live on both targets in
  this slice. Fix direction for a future slice:
  backup/export should ensure the library first,
  or refuse/warn when the manifest is unbuilt - a
  backup verb that can silently bundle nothing is
  a footgun on exactly the disaster path it exists
  for. Never leave a discovered bug unfixed: this
  ticket IS the commission - it is recorded here
  and in the campaign state for the keeper to
  schedule; it is not fixed in this verification
  slice because the fix changes backup semantics
  and deserves its own tested slice.
- **E18-T2** (stale path in COMPONENT_LICENSES.md):
  the Muninn/Huginn rows locate the ravens tree at
  `~/workspace/ravens`; the actual tree - the one
  the [tool.uv.sources] sibling binding resolves -
  is `~/ravens` on purplelongship (and was staged
  at `~/ravens` on Mimir). Pins and licenses in the
  same rows are correct; only the path prose is
  stale. One-line doc fix, banker's call (the file
  is parsed by ledger tooling).
- **E18-T3** (banner version label depends on
  checkout tags): the fork repo carries no release
  tags, so a fresh clone's banner reads
  `vgit.6ee8549` while the campaign checkout - which
  has upstream tags fetched - reads
  `v0.23.0+2940.g6ee8549`. The local SHA, upstream
  SHA, Python and SDK components are identical;
  only the describe-derived label differs. Not a
  code defect. If a stable label on fresh clones is
  wanted, the fork needs its own tag or a version
  stamp - Volmarr's call, not improvised here.
- **E18-T4** (the ravens pin cannot be staged from
  the repo on a second machine): pin fc761f020b39
  is a commit in purplelongship's local ~/ravens,
  which has no remote configured, so Mimir could
  only stage the published repo tree f12fb39. The
  delta is provably package-neutral (fc761f0 adds
  BUILD_NOTES.md, BUILD_STATE.md and two benchmark
  scripts; muninn/huginn package sources are
  byte-identical, and both suites pass identically
  on both targets), but `engines validate` on
  Mimir reports the HEAD mismatch as its one
  problem. This is E04-T1's adoption decision seen
  from the second machine: adopting a repo commit
  as the pin would make two-target validation fully
  green. Decision recorded, not taken here - E.18
  moves no pin.

## Ledger / banking notes

- No engine pin moved; integration-lock.json and
  INTEGRATION_MATRIX.md are untouched by this slice
  (E.18's subject is the fork build itself, not an
  engine row). Verification tally does not move:
  25 verified / 0 partially verified / 1 blocked
  (Sagnaskemma, E12-T1).
- No fork code changed, so no CUSTOMIZATIONS.md row
  (E.15-E.17 precedent). The only tree change is
  this record.
- README.md untouched: sha256
  336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3
  before and after, on both targets.
- Disposable staging left in place for keeper
  inspection: purplelongship ~/team01-e18-evidence-t1,
  ~/team01-e18-backup-t1, ~/team01-e18-backup-from-t2,
  ~/team01-e18-restore-from-t2, cold home
  ~/hermes-cold-home-20261114-063437; Mimir
  ~/hermes-e18, ~/hermes-e18-home,
  ~/hermes-e18-runtime, ~/ravens (new clone - the Pi
  had none), ~/hermes-e18-backup-from-t1,
  ~/hermes-e18-backup-t2, ~/hermes-e18-restore-target,
  ~/hermes-e18-ravens-scratch. Mimir's pre-existing
  ~/hermes-agent and live ~/.hermes untouched;
  Samtal (port 8787) verified listening at the end.

## Gate

Targeted batteries (this slice's surfaces - the
integration ledger and the persona-ops verbs):
scripts/run_tests.sh over
tests/plugins/test_volmarr_integration_ledger.py,
test_volmarr_persona_ops.py and
test_volmarr_persona_ops_gate.py = 3 files, 34 tests
passed, 0 failed (log ~/team01-e18-targeted.log).

Full contract gate on the committed team tree:
scripts/run_tests.sh tests/plugins/test_volmarr_*.py
tests/plugins/test_kista_*.py = 137 files, 1,171
passed / 7 failed / 1 skipped (log
~/team01-e18-gate.log). The 7 failures are
exactly the banked baseline's named live-transport
set - 5x test_volmarr_core_plugin.py (Verdandi
socket), 1x test_volmarr_verdandi_stimuli.py
(allowlist), 1x test_volmarr_voice_runner.py
(loopback) - name-identical to the baseline, so
ZERO regressions. Gate-run circumstance, recorded
honestly: another campaign's single-threaded
unittest suite occupied 1 of 16 cores for the
gate's first minutes (load 1.29 at launch, falling
to idle); no failure outside the named set
appeared, and the named set is transport-shaped,
not timing-shaped.
