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

Banking closure (keeper, 2026-11-07 ~23:10 EST): W02 / Phase U2 BANKED to main.
Team 03 branch yrsa/hermes-team-03 (5 commits over banked 1cd7d59015:
2e809aba89 PM release-age gate scoped to registry sources, 492aedf008
ravens staging comment, e1e031461a launch recipe + cold-install script,
05a445d8c0 SBOM + adapter matrix, 5ddd716ceb audit/completion/ledger)
merged --no-ff by the keeper as 4c676d0587, conflict-free; closure commit
follows this entry. Keeper verified from logs on the laptop before
banking: contracts 117 files = 929 passed / 7 failed / 1 skipped (the 7
are the known live-transport set, name-identical to the freeze baseline -
zero regressions; log ~/team03-contracts.log); PM suites 9 new + 53
existing passed, 0 failed; cold-install gate PASSED from a throwaway
profile under $HOME (evidence ~/hermes-cold-evidence-20261107-230016/),
closing W00.07; ravens selected in cold install: muninn 36 + huginn 27
passed. SBOM committed: 358 components (352 registry, 3 editable-local,
2 git, 1 archive-url). README untouched (sha256 336813d11bbe... = banked
main). Ticketed beyond W02 (recorded in U2_COMPLETION.md): T1 from-scratch
relock fails on spacy 2.0.17 sdist under Python 3.14 (committed lock is
load-bearing - needs a dependency decision); T2 PyYAML ARM64 wheel smoke
on Mimir open; T3 first-party ravens publication route design-only;
T4 automated license/leak sweep beyond the SBOM not built. W00.03-ENC
still awaits Volmarr's key/passphrase word. Next per WAVE_PLAN: Team 04
W03 prep draft (P0P1_DESIGN_DRAFT.md) is complete and uncommitted in
~/hermes-team-04 - W03 implementation follows in roadmap order; Teams
05-08 muster gradually, prep-only until their wave's base banks.

Banking closure (keeper, 2026-11-07 ~23:47 EST): W03 / Phases P0+P1 BANKED to main.
Team 04 branch yrsa/hermes-team-04 (3 commits over 073660ff15: 9fc83c0c69
canonical library P.001-P.005 plugin-side, 7ea57de312 contracts + P.016 gate,
de3a95806c implementation record + ledger) merged --no-ff by the keeper as
973c55c93c, conflict-free; closure commit follows this entry. Keeper verified
from logs on the laptop before banking: W03 tests 28 passed / 0 failed
(~/team04-w03-both.log, final run 23:38 EST; the 23:34/23:36 scale logs record
a mid-build test-expectation failure - adversary section list missing
_preamble - fixed in the tests before the final green run); P.016 gate corpus
148,174,328 bytes / 30 files, ingest wall 7.1s, RSS growth ~11.6 MB, byte
identity across ingest/verify/reindex/export; contracts 119 files = 957
passed / 7 failed / 1 skipped (957 = 929 baseline + 28 new; the 7 are the
known live-transport set, name-identical - zero regressions; log
~/team04-w03-contracts.log). Merged tree is byte-identical to the tested team
tree (git diff de3a95806c..merge is empty). README untouched (sha256
336813d11bbe...). Bug fixed in scope: a YAML front-matter closing --- was
promoting its last line to a Setext heading, corrupting section identity -
fixed in the ingester with regression tests. Ticketed remainders: serialisable
parser-state checkpoints (W04 refinement if subspan work needs them) and the
ulimit -v low-memory honesty case not yet exercised. W04 prep draft (Team 05)
is complete and uncommitted in ~/hermes-team-05 (P2_DESIGN_DRAFT.md, 45,403 B,
sha256 8fa79f40...) - W04 implementation follows now that W03 has banked; its
steps 2+ consume W03 manifest/byte ranges per that draft. Teams 07/08
worktrees mustered this tick at b5c6743a22 (yrsa/hermes-team-07/08), prep-only
until their waves base. W00.03-ENC still awaits Volmarr word.

Banking closure (keeper, 2026-11-08 ~00:15 EST): W04 / Phase P2 BANKED to main.
Team 05 branch yrsa/hermes-team-05 (5 commits over banked 7ce3db56f0:
28fcada587 design draft committed, 8e112890de merge of banked main,
4af51ae372 persona_index.py FTS5 index, 1dfdd00c66 contracts + gate,
7bfe5db1d0 implementation record + ledger) merged --no-ff by the keeper
as 53f27519db, conflict-free; closure commit follows this entry. Keeper
verified from logs on the laptop before banking: contracts 121 files =
976 passed / 7 failed / 1 skipped (976 = 957 W03 baseline + 19 new W04;
the 7 are the known live-transport set, name-identical - zero
regressions; log ~/team05-w04-contracts.log); W04 gate green standalone
(~/team05-w04-gate.log) after a first-run gate failure was fixed in the
tests (~/team05-w04-tests.log records it). Merged tree is byte-identical
to the tested team tree (git diff 7bfe5db1d0..merge is empty). README
untouched (sha256 336813d11bbe...). Gate: buried-section recall 100%
(9 needle checks, hash-verified citations, zero source loss across
reindex cycles) on a deterministic >2 MB fixture. Bugs fixed in scope:
subspan search-projection mid-character decode crash; section-13 ASCII
slug limitation reconciled at the P2 fusion layer via verbatim trigram
exact-phrase contact (scorer untouched). Ticketed remainders: W04-R1
full 100 MB gate corpus run in an uncontended window (at banking),
W04-R2 receipt retention/rotation default, W04-R3 Unicode tokeniser
question for a later wave; row_pk 2^40 subspan offset deviation and
in_kernel=0 recorded in the implementation record. Team 06 W05 prep
draft is complete and uncommitted in ~/hermes-team-06
(P3P4_DESIGN_DRAFT.md, 28,957 B, sha256 8e062732...): 30 persona/prompt
surfaces audited - 4 live, 2 partial default-off, 24 with no live
caller; zero persona-runtime contracts inject persona content into a
live prompt today. W05 implementation follows in roadmap order; its
draft section 12 carries 5 open questions for Volmarr (Q1 two-channel
vs core patch first). W00.03-ENC still awaits Volmarr word.

Banking closure (keeper, 2026-11-08 ~01:40 EST): W05 / Phases P3+P4 BANKED to main.
Team 06 branch yrsa/hermes-team-06 (commits over banked 1558f55834:
9edf303f5d design draft, 47b240accc merge of banked main, cc0a424536
live persona wiring, 2ce3dfbb0a implementation record + ledger)
merged --no-ff by the keeper as ba3a03c9f7, conflict-free; closure
commit follows this entry. Keeper verified from logs on the laptop
before banking: contracts 123 files = 991 passed / 7 failed /
1 skipped (991 = 976 W04 baseline + 15 new W05; the 7 are the known
live-transport set, name-identical - zero regressions; log
~/team06-w05-contracts.log); W05 new tests 15/15
(~/team06-w05-newtests3.log after two in-slice fixes: render unpack,
tier-down P0 order), neighbors 34/34, present_state 4/4; the gate
proves an opt-in profile gets the kernel on BOTH channels through
the real plugin manager + a real AIAgent system-prompt build, and a
non-opt-in profile is byte-for-byte stock. Merged tree is
byte-identical to the tested team tree (git diff 2ce3dfbb0a..merge
is empty). README untouched (sha256 336813d11bbe...). What W05
delivered: persona content finally reaches live prompts - Channel S
frozen kernel section (volmarr.persona.kernel, after_memory) +
Channel T per-turn pipeline through PresentState as sole owner,
first live callers for the section 20 reloader snapshot, section 14
router, section 13 retriever and section 15 budgeter; P.010 opt-in
refusal while legacy SOUL is loaded; section 36 delegate fragments
only; P.011/P.017 operator receipts carry no persona text.
Honest remainders: design draft section 2 rows 13-15, 20, 22, 24-28
stay contract-only and are NOT declared complete; draft section 12
open questions Q1-Q5 remain Volmarr's (the two-channel plan
proceeded under the section 0.2 ground rules); the 7 live-transport
failures stay environment-bound (no live Verdandi service on this
laptop) - real-socket diagnosis beyond name-identity stays open.
Next per WAVE_PLAN: Team 07 W06/P5 implementation from its prep
draft (41,557 B, sha256 dd263480...) now that W05 has banked;
Team 08 W07/P6 prep draft complete and uncommitted in
~/hermes-team-08 (44,531 B, sha256 27d91eea...), prep-only until
its wave's base banks. W00.03-ENC still awaits Volmarr word.

## W06 / P5 BANKED — 2026-11-08 ~02:57 EST (keeper banking)
Team 07 branch yrsa/hermes-team-07 banked: merge 8dd843d5ec
of 420a9af46b onto main dad0e25d42; closure commit follows this
entry. Keeper verified from logs on the laptop before banking:
contracts 128 files = 1,029 passed / 7 failed / 1 skipped
(1,029 = 991 W05 baseline + 38 new W06; the 7 are the known
live-transport set, name-identical - zero regressions; log
~/team07-w06-contracts.log); new W06 tests 38/38 across corpus,
digest, adapter, bridge+CLI and gate logs; P.016 gate: 20 MB
MEMORY.md (2,500 sections) + 2 MB USER.md imported byte-identical
(sha256), 6 buried needles exact-recalled with hash-verified
citations, paged-read concatenation byte-exact, zero source loss
across sync/reindex/repair; neighbours 97 passed / 5 failed
(live-transport members only); stock memory control 230/230.
Merged tree byte-identical to the tested team tree (git diff
420a9af46b..merge is empty). README untouched (sha256
336813d11bbe...). What W06 delivered: memory_corpus.py (W03
library rooted at the profile, dry-run-first verbatim import,
transactional scoped writes, backup/restore with index rebuild),
memory_digest.py (deterministic source-linked digest; section 41
overwrite guard's first live caller), memory_adapter.py
(stock-shaped tool surface with truthful full-store vs hot-view
status; overflow lands in the full store, never silently cut),
memory_bridge.py (PresentState packet source; PresentState stays
sole prompt owner; P.018 double-gated cloud egress, private
sources refused and named on receipts); plugin.yaml hygiene fix
(mempalace/openviking bridge flags declared). Bugs fixed in
scope: adapter entry-model flaw (entry edits now refused against
free-form authored documents); CLI contract namespace mismatch
(test-side). Honest remainders (in W06_P5_IMPLEMENTATION.md, NOT
declared complete): M6 Desktop/API editor surface, M7 separate
consolidation-link record, ChatIndex deferred, no Bifrost read
path, multi-process concurrency battery not run, backup
encryption inherits open W00.03-ENC. Next per WAVE_PLAN: Team 08
W07/P6 implementation from its prep draft (44,531 B, sha256
27d91eea...) now that W06 has banked; Team 09 W08/E0 next in
order. W00.03-ENC still awaits Volmarr word.

## W06 / P5 BANKED - 2026-11-08 ~02:57 EST (keeper banking)
Team 07 branch yrsa/hermes-team-07 banked: merge 8dd843d5ec
of 420a9af46b onto main dad0e25d42; closure commit follows this
entry. Keeper verified from logs on the laptop before banking:
contracts 128 files = 1,029 passed / 7 failed / 1 skipped
(1,029 = 991 W05 baseline + 38 new W06; the 7 are the known
live-transport set, name-identical - zero regressions; log
~/team07-w06-contracts.log); new W06 tests 38/38 across corpus,
digest, adapter, bridge+CLI and gate logs; P.016 gate: 20 MB
MEMORY.md (2,500 sections) + 2 MB USER.md imported byte-identical
(sha256), 6 buried needles exact-recalled with hash-verified
citations, paged-read concatenation byte-exact, zero source loss
across sync/reindex/repair; neighbours 97 passed / 5 failed
(live-transport members only); stock memory control 230/230.
Merged tree byte-identical to the tested team tree (git diff
420a9af46b..merge is empty). README untouched (sha256
336813d11bbe...). What W06 delivered: memory_corpus.py (W03
library rooted at the profile, dry-run-first verbatim import,
transactional scoped writes, backup/restore with index rebuild),
memory_digest.py (deterministic source-linked digest; section 41
overwrite guard first live caller), memory_adapter.py
(stock-shaped tool surface with truthful full-store vs hot-view
status; overflow lands in the full store, never silently cut),
memory_bridge.py (PresentState packet source; PresentState stays
sole prompt owner; P.018 double-gated cloud egress, private
sources refused and named on receipts); plugin.yaml hygiene fix
(mempalace/openviking bridge flags declared). Bugs fixed in
scope: adapter entry-model flaw (entry edits now refused against
free-form authored documents); CLI contract namespace mismatch
(test-side).
Honest remainders (in W06_P5_IMPLEMENTATION.md, NOT
declared complete): M6 Desktop/API editor surface, M7 separate
consolidation-link record, ChatIndex deferred, no Bifrost read
path, multi-process concurrency battery not run, backup
encryption inherits open W00.03-ENC. Next per WAVE_PLAN: Team 08
W07/P6 implementation from its prep draft (44,531 B, sha256
27d91eea...) now that W06 has banked; Team 09 W08/E0 next in
order. W00.03-ENC still awaits Volmarr word.

## W07 BANKED — 2026-11-08 ~03:41 EST (keeper)
W07/P6 persona controls banked to main: merge 6bbe5ced1e of yrsa/hermes-team-08 79d5153f12 + this closure commit. Delivered: persona_ops.py (1,382 lines) making all 13 section-12 commands live against real profiles (status/files/search/inspect/explain/validate/diff/reload dry-run+activate with exactly-named scope/export file/import dry-run/backup/restore/test), generation store with torn-pointer recovery, P.013 pager + bounded editor, bounded read-only watchdog, P.020 diagnostics + PERSONA_OPS_HOWTO.md, P.018 fail-closed egress filter wired into the persona_live.py packet seam (local turns byte-identical); CLI hermes volmarr persona, 18 verbs. Gate evidence (keeper-verified from laptop logs): contracts 130 files = 1,046 passed / 7 failed / 1 skipped (1,046 = 1,029 + 17 new W07; 7 = known live-transport set, name-identical = zero regressions; log ~/team08-w07-contracts.log); new tests 17/17 (~/team08-w07-newtests.log). Bugs fixed in scope: section-75 export bundle writer corrupted its own bundles via sort_keys reordering (now order-preserving); bounded editor had no CLI verb (persona edit wired). Honest remainders: mutating import awaits Q2; backup encryption inherits open W00.03-ENC (backups labelled unencrypted-local); watchdog on-demand only (Q4 unruled); W07-R2 rendered section-29 panel and W07-R3 virtualised editor not built; W07-R4 1,000-turn drift run stays W13; W07-R5 cross-machine restore stays W08; activation scope next_gateway_start at the CLI-process seam. Next per WAVE_PLAN: Team 09 W08/E0-E5 implementation from its ledger draft (24 rows, 7 first pins; ravens-ABSENT rows corrected at promotion per Team 03 disk proof). W00.03-ENC still awaits Volmarr word.

## W08 BANKED — 2026-11-08 ~04:10 EST (keeper)
W08/E0 existing-engines ledger banked to main: merge f2af8b5cec of yrsa/hermes-team-09 1dd59c2f3a + this closure commit. Delivered: E0 ledger promoted to docs/modernization/INTEGRATION_MATRIX.md — 26 rows (24 draft rows + 2 section-13 rows the draft omitted): 21 verified / 4 partially verified (license-text questions on OpenViking mirror, WYRD, Hamr, SRD, named per row) / 1 blocked (Sagnaskemma — re-probed 2026-11-08 under both candidate names, repository not found again; identification is Volmarr's-records work, repo creation his alone). Ravens correction applied at promotion: rows 4/5 record Muninn/Huginn PRESENT on purplelongship (~/ravens fc761f020b39, byte-identical to VM canonical, muninn 36 / huginn 27 green per Team 03 U2 proof); the draft's absence claim was the relative ../ravens staging artifact. integration-lock.json promoted DRAFT to verified lock (schema runeforge.integration-lock/v1): all 21 measurable GitHub HEADs re-measured by ls-remote at promotion, identical to the draft's 2026-11-07 measurements — no engine moved; all 7 E0 first pins recorded and still equal to current HEADs. First live caller (section 28.2): read-only stdlib-only plugins/volmarr-core/integration_ledger.py + hermes volmarr engines {status|show|validate} — refuses a DRAFT lock by name, enforces the 7 first pins, rejects the superseded ravens-absent claim, stat-checks adapter files, resolves the local ravens HEAD from .git alone. E1-E5 audit/design-only exactly as the draft scoped them: NO pin moved, no engine upgrade executed or claimed. Gate evidence (keeper-verified from laptop logs): contracts 131 files = 1,063 passed / 7 failed / 1 skipped (1,063 = 1,046 + 17 new W08; 7 = known live-transport set, name-identical = zero regressions; log ~/team09-w08-contracts.log); new battery 17/17 (~/team09-w08-newtests.log). First two contract attempts failed at environment setup (GitHub HTTP 504 fetching the kittentts wheel during uv lock; logs preserved as ~/team09-w08-contracts-attempt{1,2}-setupfail.log); third attempt on the unchanged tree produced the counts above. Banking note: the merge initially collided with the main tree's untracked DRAFT integration-lock.json (the file this wave promotes); the draft was preserved byte-identical to ~/hermes-backups/pre-bank-2026-11-08/integration-lock.main-untracked-DRAFT.json (sha256 835ea52d...) before removal, and the banked lock is the promoted file (sha256 e056baf3...). Honest remainders: E.01-E.18 per-engine upgrades none executed; 4 license-text verifications open; ravens distribution route (E.04) design-only; COMPAT_MANIFEST fate rides W00.05; cross-machine restore (W07-R5) not run. Next per WAVE_PLAN: W09 new projects (N0/N1). W00 still open: W00.03-ENC (Volmarr's word, not re-asked), W00.05 fixture archive + COMPAT_MANIFEST fate, W00.06 boundary review — WAVE_PLAN.md + BASELINE_2026-11-07.md remain untracked in the main tree riding that closure.
