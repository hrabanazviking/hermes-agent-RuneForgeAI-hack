# E.12 RPG boundary review - SRD data + Sagnaskemma (Team 01, 2026-11-14)

**Outcome: SRD FIRST PIN ESTABLISHED, license text-verified;
Sagnaskemma canonical repo IDENTIFIED, pin still blocked
honestly on staged-tree proof.** The SRD boundary holds: the
fork copies no SRD content - `volmarr-rpg 0.8.0` reads an
external `srd_root` checkout and returns OGL-1.0a provenance,
and that hardcoded claim now matches the staged LICENSE text
exactly. Sagnaskemma's earlier "unknown repo" block was a
wrong-names probe, not a missing repo: the governing roadmap
itself names the canonical repo, and it answers `ls-remote`
today.

## A. SRD data (matrix row 22) - re-measured, not inherited

- Repo: `hrabanazviking/dnd-5e-srd`. Re-measurement this
  slice: `git ls-remote` HEAD == `master` at
  `2e62e0413061c2443e21369cdc074c7a7356a857` - identical to
  the recorded `current_head`. Tree staged directly under
  $HOME at `~/srd-e12`, HEAD verified at that commit.
- **License: TEXT-VERIFIED at the pin this slice.** The
  staged `LICENSE` (sha256
  `4defc80a9d12057597eaa0da5581dabd85eff658843b73f410eb62e4d2270cdb`)
  is a composite file, read in full:
  1. *SRD 5.0 Legal Information*: permission to copy,
     modify and distribute the System Reference Document
     5.0 is granted **solely through the Open Gaming
     License, Version 1.0a**. Product Identity is
     designated (Dungeons & Dragons, D&D, Wizards of the
     Coast marks, named places/creatures including
     beholder, mind flayer/illithid, yuan-ti, etc.) and is
     **not** Open Game Content; all the rest of the SRD5
     is Open Game Content under OGL Section 1(d).
  2. The full **OGL v1.0a** text (Copyright 2000, Wizards
     of the Coast, Inc.), whose Section 15 copyright
     notice reads: "System Reference Document 5.0
     Copyright 2016, Wizards of the Coast, Inc.; Authors
     Mike Mearls, Jeremy Crawford, Chris Perkins, Rodney
     Thompson, Peter Lee, James Wyatt, Robert J. Schwalb,
     Bruce R. Cordell, Chris Sims, and Steve Townshend".
  3. **MIT License, Copyright (c) 2017 Ben Morton** - the
     repo's own conversion code, in the same LICENSE file.
  The same OGL legal text is carried inside the data tree
  itself as section `00 legal` (`json/00 legal.json` sha256
  `de4375552b3313de3746bf964de40f773d0df3a8645917539162e85dcddd48ab`;
  `markdown/00 legal.md` sha256
  `1fa1e55ebb5562936163edd2bed852a1aee94bba19329ff34551fb10b56edd3e`).
  A tree-wide search finds **no Creative Commons / CC-BY
  text anywhere** - this repo is the SRD 5.0 (2016) OGL
  release, not a CC-licensed SRD release. The GitHub API's
  NOASSERTION is therefore superseded by a text-verified
  classification: **OGL-1.0a for the SRD content, MIT for
  the conversion code.**

## Proof 1 - fork rpg + ledger contracts before the edits: PASS

- `scripts/run_tests.sh` on `test_volmarr_rpg.py` and
  `test_volmarr_integration_ledger.py` on the pre-edit team
  tree (at banked main `84d7bf8ac9`): **2 files, 33 tests
  passed / 0 failed** (log `~/team01-e12-baseline.log`).

## Proof 2 - live adapter lookups against the staged SRD: PASS

- Live harness (log `~/team01-e12-live.log`, full result
  `~/team01-e12-live-result.json`) drives the fork adapter
  handler directly against the real staged tree
  (`~/srd-e12`): **LIVE_OK**. Every lookup was run twice
  and asserted byte-identical at the raw response level.
- Blinded: success, real SRD definition (2 lines) from
  `json/12 conditions.json` (7,474 bytes at the pin, inside
  the adapter's 64 KiB bound), source provenance returned
  as `{corpus: System Reference Document 5.0, file:
  json/12 conditions.json, license: OGL-1.0a}` - exactly
  the license the staged LICENSE text establishes.
- Prone (queried as ` prone `): success, canonical name
  `Prone`, response sha256 begins `19f63b1b517f264c`
  (full hashes in the result JSON).
- Unconscious: success, deterministic across both calls.

## Proof 3 - absent srd_root fails truthfully: PASS

- In the same harness: with `srd_root` pointed at a
  nonexistent path, the lookup returns the truthful
  configuration error: "Configure volmarr-rpg srd_root as
  an absolute path to the official SRD checkout." Nothing
  was installed or faked to produce this.

## B. Sagnaskemma engine (matrix row 24) - IDENTIFIED

- The 2026-11-07/08 probes (and the honest re-probes this
  slice, 2026-11-14) covered only two short names -
  `hrabanazviking/Sagnaskemma` and
  `hrabanazviking/RuneForgeAI-Sagnaskemma` - and both still
  return "Repository not found" (`gh api` returns 404 for
  `hrabanazviking/Sagnaskemma` even authenticated).
- The canonical repo was in the governing records all
  along: the roadmap's section 40 ("Exact requested
  source") and its section 13 source table name
  **github.com/hrabanazviking/Sagnaskemma-Volmarrs-D-and-D-Lore-Treasure-Trove**,
  engine at `tree/main/engine`, supplied by Volmarr.
  Volmarr's Samtal G2 records (2026-10-21/22) independently
  name the same repo and verified its engine contract
  there (engine.api discover/execute, protocol 1.0, 90
  commands, sole third-party dependency Avrae `d20`).
- This slice: `git ls-remote` of that repo succeeds -
  HEAD == `main` at
  `a1f474f4b8803b7003b35b09f486a53145545685` (branches
  `development` and `yrsa/long-table-build` also present);
  `gh api` confirms the repo under that exact name. No
  repo was created - creation is Volmarr's alone, and
  none was needed.
- **Status stays blocked, honestly and narrowly:** no tree
  is staged on purplelongship, no engine proof has run
  here, there is no adapter, and the roadmap treats the
  repo as private canon (no internal corpus exported).
  The block is now exactly "staged-tree proof", recorded
  as remainder **E12-T1**.

## Pin status

- SRD: **FIRST PIN established at E.12** -
  `pinned` == `current_head` ==
  `2e62e0413061c2443e21369cdc074c7a7356a857` in
  integration-lock.json (row only: pin_source now
  COMPONENT_LICENSES.md, license text-verified,
  `update_needed` false, verdict "current - E.12
  executed"), INTEGRATION_MATRIX.md row 22, the new SRD
  data row in COMPONENT_LICENSES.md, and the pin-guard
  assertion in
  `tests/plugins/test_volmarr_integration_ledger.py`
  (CLI `engines show` for the SRD row), following the
  E.05-E.11 pattern. Admissible because the boundary
  review supports it: HEAD re-measured, tree staged and
  proven live, license text read, and the fork's use is
  external lookup only - no SRD content is copied, so no
  OGL redistribution duty is triggered inside the fork.
- Sagnaskemma: **no pin** - repo and HEAD recorded in the
  lock (row only), INTEGRATION_MATRIX.md row 24, and a
  COMPONENT_LICENSES.md identification row; verification
  status stays `blocked` pending E12-T1.
- The SRD verification status moves `partially_verified`
  -> `verified`; the ledger counts move to **24 verified
  / 1 partially verified (Hamr only) / 1 blocked
  (Sagnaskemma)** - the ledger test's count assertions
  are updated in this same slice.
- No adapter change: no fork code was modified in this
  slice. No CUSTOMIZATIONS.md row: ledger state only
  (E.03 / E.05-E.11 precedent).
- README.md untouched (sha256
  `336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`
  before and after).

## Gate evidence - full fork contracts

Full fork contracts on the edited team tree via
scripts/run_tests.sh = 137 files, 1,171 passed / 7 failed
/ 1 skipped - exactly the banked baseline, the 7
name-identical to the known live-transport set (5
test_volmarr_core_plugin.py + 1
test_volmarr_verdandi_stimuli.py + 1
test_volmarr_voice_runner.py); ZERO regressions (log
~/team01-e12-fullcontracts.log, run on the team tree via
the serialized gate waiter ~/team01-e12-gate-waiter.sh).
Targeted batteries (rpg + integration ledger) 33 passed /
0 failed both pre-edit (~/team01-e12-baseline.log) and
post-edit (~/team01-e12-targeted.log) - the pin-guard and
count assertions add checks inside the existing ledger
tests, so the count is unchanged.

## Honest remainders (named, not hidden)

- **E12-T1** (Sagnaskemma staged-tree proof): sparse
  engine-only stage of
  `Sagnaskemma-Volmarrs-D-and-D-Lore-Treasure-Trove`
  under $HOME on purplelongship (the Samtal road proved
  full clones of this media-heavy repo fail; sparse
  `engine/**` + root markdown was ~1.5 MB), a native
  `d20` venv (no Docker), engine suite + `discover()`
  proof, license text read at the staged tree - then a
  pin decision and the section 13/40 adapter design.
  Until then the row stays blocked.
- **E12-T2** (matrix tally drift): the INTEGRATION_MATRIX
  "Verification tally" paragraph still carries its W08
  promotion counts (21/4/1); E.06, E.07 and this slice
  each moved rows without updating it. The lock and the
  ledger test are the enforced truth (24/1/1 after this
  slice); the tally paragraph wants a dedicated
  correction pass, out of this slice's rows-only scope.
- The section 32 release scorecard still reads NOT
  releasable; E.12 changes engine currency only, nothing
  else.
- Next in roadmap order: E.13.
