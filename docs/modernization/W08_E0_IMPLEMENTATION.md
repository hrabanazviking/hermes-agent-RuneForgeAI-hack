# W08 / E0–E5 Implementation Record (Team 09, 2026-11-08)

Wave: W08 Existing engines — E0 ledger + lock promotion, first pins,
and the E1–E5 audit accounting. Branch `yrsa/hermes-team-09` in
worktree `~/hermes-team-09` on purplelongship, based on banked main
`0d62b657bd2d63b02cf5d16839f512aca75801f2` (W07 banking closure).
Commit-only: the keeper banks; nothing was pushed or merged here.

README.md untouched: sha256
`336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`
verified before the work, after the base fast-forward, and at the
end. No Docker used. No core files touched — all code is plugin-side
(`plugins/volmarr-core/`), per the ground rules.

## What was delivered

### 1. Base + draft preservation
- The worktree stood at the freeze `281843f10f` with one untracked
  deliverable, `docs/modernization/E0_LEDGER_DRAFT.md` (sha256
  `912087aff4b99f73bef8e58c4d0eedd6e588a28376d20fc37dbf102d5b511219`).
  It was backed up outside the repo, the branch was fast-forwarded
  onto banked main `0d62b657bd`, and the draft's sha256 was verified
  byte-identical after the move. The draft is committed unchanged as
  the promotion's source record.

### 2. E0 ledger promoted — `docs/modernization/INTEGRATION_MATRIX.md`
The draft's 24 rows, promoted with corrections, plus two §13 rows
the draft omitted (Hermes SessionDB; Persistent identity / affect /
goals / agency) = **26 rows**, each with pin, current HEAD, license,
adapter (plugin + §13 mode), §28.3 evidence stage, verification
state, and verdict/ticket:
- **21 verified / 4 partially verified / 1 blocked.**
- Partially verified rows are license-text questions, named per
  row: OpenViking mirror (9), WYRD (10), Hamr (15), SRD data (22).
- Blocked: Sagnaskemma (24) — canonical repo still unidentified;
  re-probed at promotion under both candidate names, repository
  not found again.

**Correction banked with the promotion (the draft's central error):**
rows 4/5 claimed the ravens tree was ABSENT on purplelongship.
False — on Team 03's disk proof: `~/ravens` is present at
`fc761f020b39f9be875310d271aac7423239d5f8`, byte-identical to the VM
canonical tree, muninn 36 / huginn 27 green on the laptop, W02 cold
install selecting both. The draft-era failures were the relative
`../ravens` staging-location artifact. The stale claim is not in
the promoted ledger, and the new registry refuses it if it ever
reappears (contract test).

### 3. Lock promoted — `docs/modernization/integration-lock.json`
From DRAFT to a verified lock (schema `runeforge.integration-lock/v1`):
- Fork block updated to the promotion base (banked main
  `0d62b657bd`, README sha `336813d1…`); the nine plugin versions
  re-read from the banked tree's `plugin.yaml` files (unchanged:
  volmarr-core 0.26.0, volmarr-voice 1.0.0, astrology 0.7.0, tarot
  0.3.0, seidr 0.4.0, rpg 0.8.0, hamr 0.4.0, smidja 0.1.0,
  kista-secret-source 0.2.0).
- All 26 rows carry a per-row verification record (method + notes).
  Every GitHub HEAD was **re-measured by `git ls-remote` at
  promotion (2026-11-08 ~04:00 EST): all 21 measurable HEADs are
  identical to the draft's 2026-11-07 measurements — no engine
  moved.** The seven E0 first pins are recorded as pins, and for
  all seven the re-measured HEAD still equals the pin exactly.
- Ravens rows corrected as above; W01's banked intake recorded in
  the upstream block. Anything not fully verified is marked
  `partially_verified` or `blocked` with the reason — no row was
  silently upgraded.

### 4. The lock's first live caller — registry + CLI (E0 wiring)
`plugins/volmarr-core/integration_ledger.py` (new, read-only,
stdlib-only: no network, no subprocess, no mutation) plus a new
`hermes volmarr engines {status|show|validate}` family in the
plugin's existing CLI (`cli.py`, same registration seam as the W07
persona family):
- loads the promoted lock and refuses a DRAFT lock by name
  (`lock_still_draft`), a missing lock (`lock_missing`), and an
  unreadable one (`lock_invalid`);
- validates structure and honesty: every row classified under a
  §13 adapter mode and a §28.3 evidence stage, verification state
  present, no duplicate rows;
- enforces the seven E0 first pins byte-for-byte — a silent drift
  fails validation by name;
- rejects the superseded ravens-absent claim anywhere in a ravens
  row;
- checks, locally, that every row's declared adapter files exist
  in this tree, and resolves the local ravens tree HEAD from
  `.git` alone to compare with the recorded tree pin — an absent
  or moved tree is reported as a named problem, never hidden.
This is the §28.2 fix for the lock itself: before W08 it was a
contract-only artefact no code consumed; now its state is one
command and one contract battery away at all times.

### 5. E1–E5 accounting (audit/design only where the draft scoped it)
No pin moved and no engine upgrade was executed in W08 — the §13
protocol requires each engine's own suite green in its own tree
first, per engine, one at a time (E.01–E.18). What the wave did
per phase is recorded in INTEGRATION_MATRIX.md ("What W08 did per
phase E1–E5"): E1 = the E.02 Aesir audit; E2 = the fabric-row
verifications + the ravens correction (ChatIndex stays
design-only, as W06 recorded); E3 = the E.01 Verdandi audit; E4 =
AIAvatarKit/OmniVoice first pins + output-only boundary audit;
E5 = Astrology verification at its existing pin, RuneTarot/Seidr
first pins, and the SRD/Sagnaskemma blockers named, not worked
around. The E.01–E.03 audits are carried into the matrix with
their exact update-proof lists intact.

## Tests (all via scripts/run_tests.sh, counts from logs)
- New W08 battery: `tests/plugins/test_volmarr_integration_ledger.py`
  — **17 passed / 0 failed** (log `~/team09-w08-newtests.log`):
  promoted-lock load/validate, §13 coverage, no-row-past-its-proof,
  status against this tree, ravens correction, first-pin drift
  refusal, DRAFT/missing/invalid refusal, stale-claim rejection,
  fake-home ravens match, absent-ravens honesty, missing-adapter
  reporting, and the live CLI family (status/show/validate/usage).
- Full contracts: **131 files = 1,063 passed / 7 failed / 1 skipped**
  (log `~/team09-w08-contracts.log`); 1,063 = 1,046 W07 baseline +
  17 new. The 7 failures are name-identical to the known
  live-transport set — 5× `test_volmarr_core_plugin.py`,
  1× `test_volmarr_verdandi_stimuli.py`, 1×
  `test_volmarr_voice_runner.py` — zero regressions.
- Housekeeping honesty: the first two contract attempts failed at
  environment *setup*, before any test ran — `uv lock` could not
  fetch the kittentts 0.8.1 wheel (GitHub HTTP 504 through the
  egress path). Both attempt logs are preserved
  (`~/team09-w08-contracts-attempt1-setupfail.log`,
  `~/team09-w08-contracts-attempt2-setupfail.log`); the third
  attempt, once GitHub answered again, staged from the same tree
  and produced the counts above. No code changed between attempts.

## Honest remainders (NOT declared complete)
- E.01–E.18 per-engine upgrades: none executed. Each begins with
  the engine's own suite in its own tree (§13 step 3) and moves
  exactly one pin, with its own lock revision.
- License texts unverified: WYRD (E.07), Hamr (E.13), SRD (E.12),
  OpenViking mirror (E.06) — recorded per row, never badged.
- Sagnaskemma (E.12): blocked on canonical-repo identification
  from Volmarr's project records; repo creation is his alone.
- Ravens distribution (E.04): the tree is present and pinned, but
  there is still no repo or publication route (W02 ticket T3 is
  design-only) — a fresh machine cannot resolve the
  `volmarr-ravens` extra without the tree being carried to it.
- COMPAT_MANIFEST.md: still absent; the matrix + lock are the
  living compatibility record meanwhile (W00.05 stays open).
- W00.03-ENC (backup encryption) still awaits Volmarr's word —
  untouched by W08, not re-asked.
- Cross-machine restore verification (W07's W07-R5 remainder,
  assigned to W08): not run in this wave — no second target
  machine was staged for a persona-backup restore, and this record
  does not claim it.
