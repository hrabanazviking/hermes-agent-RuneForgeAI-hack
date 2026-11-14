# E.10 RuneTarotEngine update — implementation record (Team 01, 2026-11-13)

**Outcome: PIN UNMOVED — audit executed, all proofs pass, with
the branch-split finding and the development branch's missing
license named as tickets.** The pinned main tree carries no code
at all; the entire engine lives only on the unrelated
`development` branch. The fork surface is unchanged: the
`volmarr-tarot 0.3.0` plugin, a deterministic tool running
seeded draws via bounded subprocess against a local checkout.
No RuneTarotEngine source was copied into the fork.

## Target (re-measured, not inherited)

- Pin (before and after this slice):
  `432e461136ba58cb3e507bb9cd86b4bb2faba80b` — the first pin
  established at E0 (2026-11-07, Team 09 ls-remote), recorded in
  integration-lock.json and INTEGRATION_MATRIX row 13.
  COMPONENT_LICENSES.md carried no RuneTarotEngine row before
  this slice; the row is added here (see Pin status below).
- Re-measurement this slice: HEAD == `main` at the pin, no
  tags (lock `latest_tag` null); the fresh pin tree directly
  under $HOME (`~/tarot-e10`) contains exactly two entries:
  `LICENSE` and `README.md`. A second tree at the
  `development` branch root lives at `~/tarot-e10-dev`.
- License: **MIT — PASS, verified at the text level this
  slice.** The `LICENSE` at the pin carries sha256
  `c006b7010fa0…` (truncated as recorded in the lock),
  Copyright (c) 2026 Volmarr Wyrd, byte-identical at the root
  commit `7b9b46c` and at the pin. Before this slice the lock
  recorded the license as MIT (API); it is now verified at
  text level.
- Branch split (headline finding, detailed below): the
  `development` branch root is
  `5c2ed4746b1c303590bca85bb0d30a3d7b1e437b`, a root commit
  unrelated to `main`. The entire engine — `src/deck.py`,
  `src/spreads.py`, `src/golden_dawn.py`, `data/` — exists
  only on that branch.

## Proof 1 — engine exercise against both trees: PASS

- Harness exercise (log `~/team01-e10-proof1.log`, full result
  `~/team01-e10-engine-result.json`) against the pin tree
  (`~/tarot-e10`) and the development tree (`~/tarot-e10-dev`):
  **ENGINE_OK**, engine_exit=0.
- Pin tree entries, as read by the harness: `LICENSE`,
  `README.md` — nothing else. The engine cannot run from the
  pin tree (see Proof 5).
- Development tree: deck loads **78** cards. A seed-42 draw of
  5 returns, in order: Wheel of Fortune (major_10, reversed),
  The Fool (major_0, upright), Princess of Pentacles
  (pentacles_princess, reversed), 10 of Pentacles — Wealth
  (pentacles_10, upright), Princess of Swords
  (swords_princess, upright); `draw_deterministic` is true.
- Spread keys in the engine: 8 — celtic_cross,
  opening_of_the_key, past_life, relationship, single_card,
  three_card, tree_of_life, zodiac_wheel. The adapter enum is
  missing nothing in the engine (`adapter_enum_missing_in_engine`
  is empty). Adapter spread card counts: celtic_cross 10,
  opening_of_the_key 5, past_life 5, relationship 7,
  three_card 3, tree_of_life 10, zodiac_wheel 12.
- Elemental balance of the 3-card seed-42 spread: fire 1,
  water 0, air 1, earth 1. Dignities pairs: 2.

## Proof 2 — fork tarot contracts before the edits: PASS

- `scripts/run_tests.sh` on `test_volmarr_tarot.py` and
  `test_volmarr_integration_ledger.py` on the pre-edit team
  tree: **2 files, 21 tests passed / 0 failed** (tarot 4,
  ledger 17; log `~/team01-e10-baseline.log`).

## Proof 3 — live adapter calls against the development tree: PASS

- Live harness (log `~/team01-e10-live.log`, full result
  `~/team01-e10-live-result.json`) drives the fork adapter
  against the real development tree (`~/tarot-e10-dev`,
  engine_python `/usr/bin/python3`): **LIVE_OK**.
- Single draw (seed 42, reversals allowed): success, report
  sha256 `fc8124c969b5244a672b86c5b0069cb44e21bd1fd5b6b03a0cb545ca6963999f`;
  the card is major_10, Wheel of Fortune, reversed — the same
  first card as the direct engine exercise in Proof 1. The
  no-reversals draw returns the same card upright, report
  sha256 `60f21e2a55a30a36501376e15a4b02924c3be1a7ca1280426b8b5d91d8d3fa2f`.
- Three-card spread (seed 42): success, report sha256
  `9498f54a9d5cff8e07b48e512358d91edbec6d9543cd825bfe8d9e745986c793`;
  cards major_10, major_0, pentacles_princess — byte-identical
  to the engine's own seeded sequence.
- Celtic cross (seed 7): success, 10 cards, report sha256
  `aaec08637e581478c3954e8a08fe64b2198183947d2d2ea1b8c0c3d163f1819a`.

## Proof 4 — fork targeted batteries after the edits: PASS

- Same two batteries as Proof 2, after the ledger edits:
  **2 files, 21 tests passed / 0 failed** (log
  `~/team01-e10-targeted.log`) — the ledger battery now
  carries the new pin-guard assertion for RuneTarotEngine
  (pinned == `432e461136ba58cb3e507bb9cd86b4bb2faba80b`).
  The pin-guard adds assertions inside the existing ledger
  file, not new tests, so counts are identical to the
  pre-edit baseline.

## Proof 5 — absent and pin-tree engine roots fail truthfully: PASS

- In the same live harness (result JSON above): with the
  engine root absent, and again with the engine root pointed
  at the pin tree (`~/tarot-e10`), both the draw and the
  spread handlers return the truthful configuration error:
  "Configure volmarr-tarot engine_root and a Python
  interpreter with the RuneTarotEngine deck dependencies
  installed." Nothing was installed or faked to produce
  these; the pin tree fails because it carries no engine
  code (Proof 1).

## Branch-split finding (judged, not worked around)

- **The pin names a tree with no engine in it.** `main` at
  `432e461136ba` holds only `LICENSE` and `README.md`. Every
  executable part of RuneTarotEngine — `src/deck.py`,
  `src/spreads.py`, `src/golden_dawn.py`, the `data/` card
  and spread definitions, `runetarot.py` — exists only on
  the `development` branch, whose root commit
  `5c2ed4746b1c303590bca85bb0d30a3d7b1e437b` is unrelated to
  `main` (a separate git root, not a descendant).
- **Consequence for deployment:** a checkout of the pinned
  ref cannot serve the adapter at all (Proof 5). A working
  deployment must check out the `development` branch and
  point `engine_root` at that tree — which is exactly how
  the live proof in Proof 3 was run. Named as remainders
  **E10-T1** and **E10-T4**; no adapter workaround was
  added, and the pin was not silently re-pointed at the
  development root, because the pin is the E0 first pin and
  moving it is a ruling, not an audit fix.
- **The executed code is unlicensed on its own branch.**
  The `development` tree carries no `LICENSE` file, and its
  README license wording reads "Free for personal and
  spiritual use" — different terms from the MIT text
  verified at the pin on `main`. The MIT verification in
  this slice covers the pin tree only. Named as remainder
  **E10-T2**.
- **Neither branch carries a test suite.** pytest collects
  0 tests in both trees. Engine behaviour is therefore held
  by the fork contracts (Proofs 2 and 4) and by the E.10
  engine and live proofs (Proofs 1 and 3), not by any
  upstream suite. Named as remainder **E10-T3**.

## Pin status

- Pin **unmoved** in this slice: `pinned` == `current_head`
  == `432e461136ba58cb3e507bb9cd86b4bb2faba80b` in
  integration-lock.json (RuneTarotEngine row only: license
  MIT now text-verified, verdict "current - E.10 executed",
  `update_needed` false), INTEGRATION_MATRIX.md row 13,
  the new RuneTarotEngine row in COMPONENT_LICENSES.md, and
  the pin-guard assertion in
  `tests/plugins/test_volmarr_integration_ledger.py`,
  following the E.05–E.09 pattern.
- The Tarot verification status was already `verified` and
  stays `verified` — the ledger counts do not move
  (23 verified / 2 partially verified / 1 blocked).
- No adapter change: no fork code was modified in this
  slice; the branch-split and license findings above are
  recorded as tickets, not adapted to silently.
- No CUSTOMIZATIONS.md row: the existing volmarr-tarot row
  already records the plugin and notes the official
  executable lives on the `development` branch; this slice
  changes ledger state only (E.03 / E.05–E.09 precedent).
- `docs/modernization/ADAPTER_COMPATIBILITY_MATRIX.md`
  still shows the W08-era line for RuneTarotEngine ("no pin
  recorded"): a dated audit snapshot that no E.05–E.09 slice
  updated, left untouched here for the same reason.
- README.md untouched (sha256
  `336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`
  before and after).

## Gate evidence — full fork contracts

Full fork contracts on the audited team tree via scripts/run_tests.sh = 137 files, 1,171 passed / 7 failed / 1 skipped — exactly the banked baseline, the 7 name-identical to the known live-transport set (5 core-plugin + 1 Verdandi stimuli + 1 voice runner); ZERO regressions (log ~/team01-e10-fullcontracts.log, completed 2026-11-14 00:09 EST via the serialized gate waiter). Targeted batteries (tarot + integration ledger) 21 passed / 0 failed both pre-audit (~/team01-e10-baseline.log) and post-edit (~/team01-e10-targeted.log).

## Honest remainders (named, not hidden)

- **E10-T1** (branch split): the pinned `main` tree is
  LICENSE + README only; the engine exists solely on the
  unrelated `development` branch root `5c2ed4746b1c`.
  Anything deploying from the pin alone gets no engine.
- **E10-T2** (license gap on the code-bearing branch): the
  `development` branch carries no LICENSE file and its
  README states "Free for personal and spiritual use",
  while the MIT text is verified only at the pin on
  `main`. The branch that actually runs is unlicensed at
  text level until its author adds the license there.
- **E10-T3** (no upstream tests): neither branch carries a
  test suite (pytest collects 0 in both trees); engine
  behaviour rests on the fork contracts and the E.10
  proofs.
- **E10-T4** (deployment requirement): deployments must
  check out the `development` branch and point the
  adapter's `engine_root` at that checkout; checking out
  the pinned ref is not a working deployment.
- The section 32 release scorecard still reads NOT
  releasable; E.10 changes engine currency only, nothing
  else.
- Next in roadmap order: E.11.
