# Hermes Hack - Modernization Campaign State (2026-11-07)

Sibling to CAMPAIGN_STATE.md (the 2026-10-30/11-01 campaign, Slices 83-164,
four roadmaps declared complete 2026-11-01). This file is the resume point
for the NEW campaign. Any agent (Muse or Hermes) resumes from here.

## Commission (Volmarr, 2026-11-07 21:24 EST, main chat)

- Hammer this repo on purplelongship with 9 teams x 6 Mythic Engineering
  roles (scout, designer, 3 builders, tester) = 54 roles; Volmarr said 53
  subagents - the coordinator is the 54th seat, 53 workers in the teams.
- Muster GRADUALLY (a 60-agent simultaneous spawn was throttled on
  2026-11-06): probe team first, then 2-3 teams at a time.
- A 10-minute keeper minder guards this campaign (keeper law: it
  CONTINUES stopped work slice by slice, never merely reports).
- Order of work: (1) ALL upstream changes in, guarded; (2) every one of
  Volmarr's own apps integrated in the fork updated to its current
  version; (3) prove everything works together; (4) finish any unmet
  work in the four older roadmaps (their contracts are banked, but the
  new roadmap states several persona sections have NO live caller and
  several bridges are health/preflight-only - wiring those live is core
  work, not re-implementation); (5) then the NEW roadmap Volmarr pushed
  today (see below - in its own ordering, the new roadmap's Parts I-II
  ARE steps 1-3, Part III is step 2 continued per-engine, Parts IV-VI
  follow; where the older roadmaps' live-wiring gaps fall inside a new
  roadmap phase, that phase's tickets carry them).
- His hacks are NOT donated upstream: no PRs to NousResearch, ever.
  Upstream is pull-only. The fork is open source; upstream may come
  take the hacks themselves if they want them.
- Laws: README never touched by us (protected in sync; new protected
  sha in baseline), no Docker, no force-push, divergence stays additive
  via volmarr-core plugin (CUSTOMIZATIONS.md ledger row per change),
  tests via scripts/run_tests.sh only, per-team worktrees, bank
  incrementally with ls-remote verification, never leave a discovered
  bug unfixed, one heavy suite at a time on the shared laptop.

## The new roadmap

ROADMAP_HERMES_MODERNIZATION_UNBOUNDED_PERSONA_2026-11-07.md (894 lines)
Parts I-VI, Phases U0 U1 U2 | P0-P6 | E0-E5 | N0-N5 | Q0-Q4, delivery
Waves W00-W13, tickets W00.01-07, W01.01-09, P.001-020, E.01-18, N.01-16,
release scorecard (section 32), handoff protocol (section 33).
It arrived in 4 commits tonight on top of 8233a43ee6: 7d01c3a385
(Parts I-II), 45005e722e (completed), cec5d0fb25 (status + README link),
281843f10f (section count). Full ordered slice list: WAVE_PLAN.md and
the Phase 0 report.

## Verified baseline (Phase 0 recon, coordinator, 2026-11-07 evening)

Full detail: docs/modernization/BASELINE_2026-11-07.md +
 docs/modernization/integration-lock.json (DRAFT).
- Tree ~/hermes-hack-forge on purplelongship: branch main, HEAD
  281843f10fb0d2c6ca6ee7dab9e99070f7e141ba, CLEAN. Checkout recovered
  from a stale index.lock (see baseline) and verified.
- Upstream: merge-base = last intake 6bb377a51d; 2852 commits to
  upstream main (334f66b835, itself unstable tonight - 3 SHAs in
  ~15 min), 1792 to v0.23.0 release commit 2bd378ed1b. Fork 281 ahead.
- External engines: every pinned engine differs from its current HEAD
  (table in baseline) except the MemPalace mirror, which matches its
  pin but is itself behind official MemPalace. Ravens tree absent on
  this laptop = known U2 blocker. COMPAT_MANIFEST.md missing from tree.
- ~/.hermes deployment exists on the laptop; hermes CLI not on PATH;
  launch recipe unknown (Team 1 inventory).

## Status

- Phase 0 recon: DONE (this file + WAVE_PLAN.md + baseline + draft lock,
  all UNCOMMITTED in the laptop tree - nothing pushed this run).
- Next: Team 1 takes W00/U0 completion (backups, baseline tests,
  inventory) per WAVE_PLAN.md, then Team 2 the U1 guarded intake.
  No upstream merge has been started. No code has been changed.

## W00 / U0 Freeze - Team 01 completion (2026-11-07 21:36-21:47 EST)

Freeze candidate RE-PINNED and UNCHANGED: origin/main == local HEAD ==
281843f10fb0d2c6ca6ee7dab9e99070f7e141ba (re-verified by foreground
git fetch this run; nothing further was pushed during the run).
README.md sha256 verified 83a8c2b4b82b068d9f36c2a015e6e42c49b05fa2198e780d152c4d85c79ae0f4.

Ticket status:
- W00.01 DONE - freeze SHA above; integration branches: none exist yet
  (Team 02 creates integration/upstream-2026-11-07).
- W00.02 PARTIAL - plugin/version matrix verified against the tree
  (all 9 plugin.yaml versions match baseline + integration-lock.json:
  volmarr-core 0.26.0, volmarr-voice 1.0.0, volmarr-astrology 0.7.0,
  volmarr-tarot 0.3.0, volmarr-seidr 0.4.0, volmarr-rpg 0.8.0,
  volmarr-hamr 0.4.0, volmarr-smidja 0.1.0, kista-secret-source 0.2.0).
  Launch recipe: NONE FOUND (full search recorded in the baseline) -
  no systemd user unit, alias, desktop file, cron entry, autostart,
  pipx/uv tool, or running process; hermes CLI not on PATH.
  Active profiles: NONE - no ~/.hermes/profiles directory exists.
  Both are formal findings for U2.
- W00.03 DONE with one named remainder - backup at
  ~/hermes-backups/2026-11-07-w00/ (outside the repo):
  hermes-home.tar.gz 38,114 bytes, permissions-preserving; the live
  tree holds only 3 files / 564K (SOUL.md + 2 logs, other dirs empty).
  MANIFEST.sha256 + inventory.txt written; restore drill PASSED
  (extracted hashes identical to live, permissions 700/600 preserved).
  SQLite step vacuous: ZERO live .db/.sqlite files exist under
  ~/.hermes (find-verified twice); sqlite3 CLI 3.46.1 present.
  REMAINDER W00.03-ENC: the tar is NOT encrypted - no age recipient
  and no gpg key exists on this laptop; encryption needs a key or
  passphrase from Volmarr. Do not invent one.
- W00.04 NOT ESTABLISHED - baseline suite could not run on this host.
  Attempt 1 (canonical scripts/run_tests.sh): environment staging
  FAILED at uv lock - editable source ../ravens/huginn missing
  (the known ravens U2 blocker), pm install failed, EXIT 1
  (log: ~/hermes-team01-baseline.log). Attempt 2 (HERMES_PYTHON =
  system python3 3.14.4): 117 volmarr/kista files, 0 passed /
  0 failed / 933 errors / 1 skipped - system python lacks the
  project deps (first cause: No module named ruamel,
  hermes_yaml.py:10) (log: ~/hermes-team01-baseline2.log).
  The 7 historical environment failures are NOT YET REPRODUCED -
  they presuppose a staged env. U2 owns env repair (ravens lock
  first), then W00.04 re-runs. Note: the volmarr/kista contract
  set is now 117 files, not the 49 of the 2026-10-30 campaign.
- W00.05 REMAINING - fixture archive + provenance export not
  produced; next action: Team 09 / E0 builds it from
  integration-lock.json once the lock is promoted. Draft lock rows
  spot-checked this run: Verdandi, Bifrost, Samverk and MemPalace
  mirror HEADs re-measured by ls-remote, all match the lock exactly.
- W00.06 REMAINING - repo-boundary review not done this run; next
  action: keeper schedules it as a standalone audit before U1
  merge banking. No boundary change was made or needed by W00.
- W00.07 REMAINING - offline install recipe not captured; it
  depends on the same env staging as W00.04 (ravens lock), so it
  follows the U2 cold-install reproduction (W02 gate).
- COMPAT_MANIFEST.md fate: ABSENT at every path in HEAD
  (git ls-tree -r verified); mentioned only in historical
  CAMPAIGN_STATE.md. Exact removal commit not determined (one
  blobless history search timed out, not retried) - minor remainder.
- Ravens blocker resolution path (for U2): tree pinned at fc761f0 in
  COMPONENT_LICENSES.md, lives only in the VM copy per the baseline;
  placing that copy beside this checkout (~/ravens) unblocks uv
  lock, env staging, W00.04 and W00.07. Not done this run (U2 task).

Next: Team 02 (U1 guarded intake) may start from the freeze SHA
above; W00.04 / W00.07 close inside U2 once the ravens lock lands.

## W01 / U1 Guarded Upstream Intake - Team 02 completion (2026-11-07 21:46-22:05 EST)

Status: DONE on branch `integration/upstream-2026-11-07` in worktree
~/hermes-team-02, committed LOCALLY, NOT pushed. Banking to main is the
keeper/coordinator step after review. Full record: `upstream-changes.md`
at repo root (filed with this state update).

- Freeze verified before and after: HEAD 281843f10fb0d2c6ca6ee7dab9e99070f7e141ba
  == origin/main; README.md sha256 83a8c2b4b82b068d9f36c2a015e6e42c49b05fa2198e780d152c4d85c79ae0f4
  at freeze, after merge, and after the merge commit.
- Pin: v0.23.0 tag df177429 peeled to 2bd378ed1b8d6bf2192cb26e0a55ff3091e6bd19;
  merge-base exactly 6bb377a51d (2026-10-30 intake); 1,792 upstream commits
  taken. Upstream main reviewed at 30c8a273da (1,153 past the pin), not chased.
- Merge commit 6d8a10d38335479a3524ffc35127fa5e06a9b0c1 (parents: freeze + pin);
  2,171 files changed, 94,802 insertions, 17,434 deletions.
- Conflicts: exactly ONE - uv.lock, one hunk, minimal union (fork muninn
  editable line kept; upstream nemo-relay >=0.11,<0.12 bump taken; merged
  lock package entry 0.11.0 consistent; pm installed hash-verified via
  this lock for all test runs). Watch-list was 4 files (agent/redact.py,
  pm/extras.py, pyproject.toml, uv.lock); the other three auto-merged and
  were hand-verified to retain every fork customization (pyyaml, ravens
  extra + uv.sources, ANCHORS row, redact vault union, redaction_scope
  applier). CUSTOMIZATIONS.md gained the 2026-11-07 intake ledger row.
- Procedure deviation, recorded: sync_upstream.py ran in its supported
  --no-fetch mode against a remote-tracking ref holding the peeled pin,
  because the default fetch would merge moving upstream main.
- Tests (scripts/run_tests.sh, this host): Volmarr/Kista contracts
  117 files = 929 passed / 7 failed / 1 skipped; the 7 are the known
  live-transport set (5 core-plugin + 1 Verdandi-stimuli + 1 voice-runner),
  proven name-identical on the untouched freeze tree on this host
  (3 files there: 4 passed / 7 failed, same names) - zero regressions.
  Targeted upstream suites (agent redact/secret-scope + all
  tests/hermes_state): 222 files = 2,355 passed / 0 failed / 16 skipped.
- Smoke: CLI runs on merged tree (exit 0); hermes plugins list discovers
  all 9 fork plugins bundled at frozen versions.
- Ravens staging note (Team 03 correction, confirmed in this run): the
  tree IS present at ~/ravens (fc761f0); env staging works from a tree
  directly under $HOME because the uv.sources binding is ../ravens-
  relative. Failures elsewhere are staging-location artifacts, not a
  missing tree.
- Remaining before banking: coordinator review of this branch; the
  keeper then banks serially (merge -> closure -> push -> ls-remote
  verify). Deferred beyond W01: full upstream suite (selected suites
  ran per the W01 gate), pm relock gate (U2), W00.04 remainder + W00.07
  (close inside U2).

Ticket status: W01.01 DONE, W01.02 DONE, W01.03-W01.05 audited at intake
(no fork intersection; live wiring is W05), W01.06 DONE (contracts +
discovery), W01.07 audited (no fork intersection), W01.08 DONE,
W01.09 DONE (upstream-changes.md + this entry).

Banking note (Team 02, at branch completion): origin/main MOVED during
the W01 run, 281843f10f -> e229b1d390, by two docs commits from outside
this branch (6c49ee7a9c: 15 ecosystem workstreams added to the
modernization roadmap, +493 lines; e229b1d390: one README roadmap-
description line, README sha on origin now 336813d11bbe...). This
branch touched neither file, so a keeper merge onto the new main
should be conflict-free; the freeze-baseline README proof above stands
relative to the freeze. The new roadmap workstreams are future-wave
scope, not W01.

Banking closure (keeper, 2026-11-07 ~22:12 EST): W01 BANKED to main.
Local main was first fast-forwarded 281843f10f -> e229b1d390 (Volmarr's
two docs commits that landed during the intake; README on main is now
sha256 336813d11bbe... - his edit governs, freeze proof stands relative
to the freeze). The pre-bank untracked 138-line copy of this file was
preserved at ~/hermes-backups/pre-bank-2026-11-07/ (sha256 3aeec7c5...)
after diff proved the branch version is a strict superset.
Merge commit fb05080843 (no-ff, conflict-free, exactly as the banking
note predicted). Tree proof: merged main differs from the tested
integration tree d6461c1872 in exactly two files - README.md (1 line)
and the roadmap (+493 lines); zero code differences.
Extra keeper verification this tick: FULL tests/plugins on the merged
integration tree via scripts/run_tests.sh = 262 files, 2,846 passed /
7 failed / 5 skipped (log ~/team02-contracts.log); the 7 failures are
the same known live-transport set, name-identical to the freeze.
W00 remains open on: W00.03-ENC (needs Volmarr's encryption key or
passphrase), W00.05 fixture archive, W00.06 boundary review, W00.07
offline install recipe (U2 cold-install gate), integration-lock
promotion (Team 09 / W08), and the 7-failure real-socket diagnosis
(W05 carries the live wiring). Next per WAVE_PLAN: Team 03 W02/U2
continues from its audit draft; Teams 04-08 muster gradually, 2-3
team leads per tick, prep-only until their wave's base banks.
