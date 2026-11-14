# X.07 Huginn-and-Muninn-Ravens — ecosystem workstream 7 of 15 (Team 01, 2026-11-14)

Roadmap section 42 (Part VII workstream 7 of 15) names
Huginn-and-Muninn-Ravens: make the dedicated repo the audited
memory-package authority. Source:
https://github.com/hrabanazviking/Huginn-and-Muninn-Ravens.
This slice reconciles section 42 with the E.04 distribution
proof (docs/modernization/E04_RAVENS_DISTRIBUTION.md) and
follows the X.01–X.06 slice shape. The old W08-era claim that
the ravens have no GitHub repo was stale and is NOT repeated:
Volmarr created the repo on 2026-10-31 and the packages were
published to it that day (E.04 record).

## Audit (re-measured, not inherited)

- **Dedicated repo.** `hrabanazviking/Huginn-and-Muninn-Ravens`,
  HEAD re-measured by `git ls-remote` this slice:
  `17d6bd8b7d8a9bc7b9446f1cdf20b8d0bff6f94c` — unchanged since
  the E.04 measurement (2026-11-13). E.04 already proved the
  publication commit `f12fb39` carries packages byte-identical
  to this fork's pinned tree, and that the repo HEAD has since
  grown past 1.0.0 at an UNCHANGED version 1.0.0 (adoption is
  ticket E04-T1, carried below — not silently taken here).
- **Pinned local tree.** `~/ravens` on purplelongship at HEAD
  `fc761f020b39f9be875310d271aac7423239d5f8` == the fork pin.
  Its only dirt is its own BUILD_STATE.md modification plus
  test `__pycache__` from its own green runs; this slice did
  not touch the tree. Tree history read directly: `4eafc31`
  "muninn 1.0.0", `54dd839` "huginn 1.0.0", `fc761f0`
  benchmarks/integration record on top.
- **Independent package pins (section 42 item 3).** Full SHAs
  resolved from the tree history: Muninn package pin
  `4eafc3101e5ea6805cb2f0c11784c6524b30ec6f`, Huginn package
  pin `54dd839c931f0856366fecff120fc30ad7443e1d`. Both
  packages are version 1.0.0 in their pyprojects.
- **Real APIs (item 5).** Muninn `HebbianMemory`
  (muninn/core.py): remember / store, associate,
  activate_batch, get_associations, spread_activation,
  decay, consolidate, heal_structure, health, dump, backup —
  the association / reinforcement / decay / consolidation
  backend. Huginn `HuginnMemory` (huginn/core.py):
  upsert_memory, search, fly, multi_hop_retrieve, get,
  delete, health — the retrieval / ingestion / ranking
  backend (local TF-IDF store; Qdrant backend exists behind
  its config, unused here).
- **Import independence (item 5).** Cross-import grep over
  both packages' `src/` trees: ZERO hits in both directions
  (no `import huginn` / `from huginn` in muninn, no
  `import muninn` / `from muninn` in huginn). Proven live
  again by the adapter's subprocess blocker proof and the
  staged smoke below.
- **Own suites re-run at the pin** on purplelongship (log
  ~/team01-x07-ravens-suites.log), each package separately
  (their test basenames collide in one invocation):
  **muninn 36 passed, huginn 27 passed** — exactly the
  W02/U2-era counts for the pinned 1.0.0 packages.
- **License (text-verified this slice).** The dedicated
  repo's root LICENSE at HEAD `17d6bd8b` is the MIT text,
  "Copyright (c) 2026 Volmarr Wyrd", sha256
  `c006b7010fa0c6dc396e405025475c03352effe1495e67e0f9d9a11f427b0383`,
  read in the `~/ravens-e04` clone. The pinned tree has no
  standalone LICENSE file; there the grant is the
  `license = { text = "MIT" }` declaration plus
  `authors = [{ name = "Volmarr Wyrd" }]` in each package's
  pyproject.toml — both read directly. COMPONENT_LICENSES.md
  records MIT for both packages; its statements are now
  text-verified, and both rows carry the X.07 verification
  note in place.
- **Item 4 discipline kept.** The `[tool.uv.sources]`
  sibling path binding (`../ravens/muninn`, `../ravens/huginn`,
  editable) is retained deliberately: E.04 proved it resolves
  from a fresh sibling clone with PyPI never consulted, and
  this slice re-proved it in a staged tree (below). The
  PyPI `muninn`/`huginn` projects are unrelated software and
  were never installed anywhere in this slice.

## Registry (section 35 duty)

Muninn and Huginn already have matrix rows 4/5 and lock
entries — no new rows (X.04/X.06 in-place precedent).
Updated IN PLACE, field-diff asserted by the edit harness
(only the two ravens entries changed in the lock; every other
entry and top-level field is value-identical after a JSON
round-trip in the lock's compact format):

- `integration-lock.json`: each raven entry gains an
  independent `package_pin` (Muninn `4eafc310…`, Huginn
  `54dd839c…`) recorded additively — the shared `pinned`
  tree HEAD `fc761f020b39…` is unchanged, per the ledger
  guard's asserted semantics; the originating repository
  stays recorded in `repo`
  (`hrabanazviking/Huginn-and-Muninn-Ravens`); adapter paths
  gain `plugins/volmarr-core/ravens_authority.py`; verdict
  and verification texts gain the X.07 record.
- `INTEGRATION_MATRIX.md` rows 4/5: verdict cells updated in
  place with the X.07 execution note and each row's own
  package pin.
- `COMPONENT_LICENSES.md` Muninn + Huginn rows: only the
  X.07 license-text verification note appended in place;
  license (MIT), pins and the PyPI warning unchanged.
- Verification counts unchanged at 29 verified / 0 partially
  verified / 0 blocked; evidence stage stays
  "installed integration". CUSTOMIZATIONS.md gains exactly
  one ledger row for the X.07 adapter.

## Build (plugin-side only — section 42 items 1–10)

New module `plugins/volmarr-core/ravens_authority.py`
(original code; no core edits, no ravens source copied or
vendored), two default-off config keys in plugin.yaml
(`ravens_authority_enabled`, `ravens_qdrant_agreed`), and
the CLI family below. Existing `ravens.py` /
`ravens_writes.py` / `memory_fabric.py` bindings are
unchanged and reconciled as follows (item 10): the profile
bindings keep their Slice 90 semantics (Muninn profile-bound
directly and through Bifröst, Huginn constructed directly
only, local backend), the write operations stay behind
their existing default-off operator flags, and the new
authority module records the pins/roles those bindings
already assume — no description in CUSTOMIZATIONS.md needed
correction beyond the new X.07 row.

- **Authority record.** Canonical repo + URL, repo HEAD
  audited, tree pin, independent package pins, MIT license
  + repo LICENSE sha256, per-package import-only presence /
  version / real-API completeness attestation.
- **Role separation (item 5).** Muninn = association /
  reinforcement / decay / consolidation backend; Huginn =
  retrieval / ingestion / ranking backend, each bound to
  the real class surface listed in the audit. The packages
  do not need each other to import (grep + live proof).
- **Bifröst preserved (item 6).** The authority module
  creates no second agent memory store; its smoke stores
  are throwaway fixtures. Bifröst remains the optional
  coordination layer, exactly as E.03 left it.
- **Records & policies (item 7).** The packages' own
  schemas already version stored records (nodes carry
  created/updated timestamps, metadata, tags, importance,
  emotional valence; associations carry strength,
  co-activation counts, consolidation state and activation
  history; deletion exists as forget/delete). The adapter
  surfaces these through the smoke (dump export +
  close/reopen restore) and invents no parallel schema.
- **Consolidation safety (item 8).** Automatic consolidation
  jobs are NOT enabled by this slice: `consolidate()` stays
  behind the existing default-off `ravens_writes` flags.
  The packages' own suites at the pin cover concurrency,
  WAL crash-proofing and self-healing shapes; a fork-level
  interrupted-consolidation repair proof remains ticketed
  (X07-T4).
- **Qdrant (item 9).** NOT enabled: Huginn is constructed
  with `backend="local"` only, in the smoke as in the
  existing binding. `ravens_qdrant_agreed` (default false)
  records that no privacy agreement has been given; SQLite /
  local retrieval remains the fully working default path.

## Live caller (section 28.2)

New CLI family beside the existing volmarr verbs:
`hermes volmarr ravens {status|roles|smoke}` (the older
`hermes volmarr memory ravens {health|reinforce|decay|
consolidate|ingest}` family is untouched). Real proof with
the REAL pinned packages in a staged sibling tree under
$HOME (`~/x07-stage/hermes` = copy of this worktree,
`~/x07-stage/ravens` = copy of the pinned tree at
`fc761f020b39`; `uv sync --extra volmarr-ravens` built both
packages from the sibling — `muninn==1.0.0 (from
file:///home/volmarr/x07-stage/ravens/muninn)`, same for
huginn — and imports resolve into the staged tree; log
~/team01-x07-uvsync.log). In a disposable profile home
(log ~/team01-x07-liveproof.log):

- `ravens status --json` rc 0: both packages present,
  version 1.0.0, APIs complete, independent package pins
  reported, `enabled` false (default-off, truthful).
- `ravens roles --json` rc 0: the section 42 role split.
- `ravens smoke --json` rc 0, `ok` true against the real
  packages: Muninn remember/associate/reinforce/decay/
  consolidate + dump + close/reopen restore; Huginn
  upsert/search ranking (best-first, deterministic across
  repeats) + fly + get; import independence proven in both
  directions by subprocess blocker.
- Bare `ravens` verb rc 2 with usage.
- Absent-package truth: the same module under a Python with
  no ravens installed reports `package_missing` by name for
  both packages and the smoke reports `package_missing`
  (muninn) — nothing is installed or fetched as a fallback
  (same log).

## Tests and gate

- X.07 targeted battery via scripts/run_tests.sh
  (tests/plugins/test_volmarr_ravens_x07.py +
  test_volmarr_integration_ledger.py + test_volmarr_ravens.py
  + test_volmarr_ravens_writes.py +
  test_volmarr_memory_fabric.py): 5 files, **46 passed /
  0 failed** (log ~/team01-x07-targeted.log). The 8 new
  X.07 contracts pin: the authority record, the independent
  lock pins + originating repo, the role split, package
  presence with complete APIs, import independence, the
  exact API smoke (deterministic + restore), smoke store
  containment, and the CLI family (status/roles/smoke
  rc 0, bare verb rc 2). Contract-environment honesty: the
  stock test tree has neither raven installed (Slice 90 /
  E.04 record), so — exactly like
  test_volmarr_ravens.py — the contracts inject faithful
  stub packages mirroring the real APIs (SQLite-backed, so
  close/reopen restore is real); the REAL packages are
  proven in the staged tree above, not in the contract env.
- Full fork gate via scripts/run_tests.sh on the team tree
  (the canonical volmarr + kista contract file list):
  **144 files, 1,249 passed / 7 failed / 1 skipped** (log
  ~/team01-x07-fullcontracts.log) — the X.06 baseline of
  1,241 passed + exactly the 8 new X.07 contracts, and the
  7 failures name-identical to the known live-transport set
  (5× test_volmarr_core_plugin.py, 1×
  test_volmarr_verdandi_stimuli.py, 1×
  test_volmarr_voice_runner.py). ZERO regressions.
- README.md untouched: sha256
  336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3
  before and after.

## Honest remainders / tickets

- **X07-T1 (= E04-T1) — repo-HEAD adoption decision.** The
  dedicated repo's packages have grown 69 commits past the
  published 1.0.0 while the version stayed 1.0.0. Adopting a
  repo commit as a future pin is a separate update, owned
  with the ravens line, which should bump the version when
  it next publishes so 1.0.0 names one package body. The
  X.07 package pins name the pinned tree's package commits;
  they do not adopt repo HEAD.
- **X07-T2 (= E04-T2) — repo-HEAD suite failures in this
  environment.** The 3 SQLite-3.50.4 failures E.04 measured
  against the repo-HEAD (grown) packages belong to the
  ravens campaign; the PINNED packages' suites are green
  here (36/27, re-run this slice).
- **X07-T3 (= E04-T3) — pin tree has no remote.** `~/ravens`
  has no git remote configured, so the pinned tree is not
  wired to its own distribution repo. A small ravens-line
  action; this slice did not touch `~/ravens`.
- **X07-T4 — fork-level consolidation repair proof.**
  Section 42 item 8's interrupted-consolidation repair,
  WAL-checkpoint and power-loss replay proofs exist at the
  package level (the packages' own robustness suites at
  the pin), but no fork-level proof drives an interrupted
  consolidation through the Hermes binding yet, and
  automatic consolidation jobs stay disabled until one
  exists.
- **X07-T5 — Qdrant stays off.** Optional vector operation
  (item 9) needs verified Qdrant availability plus an
  explicit privacy agreement; neither exists, so the local
  backend remains the only constructed path.
- production_ready stays FALSE in every X.07 record: the
  authority surface is contract-implemented and live-proven
  against the pinned packages, but repo-HEAD adoption
  (T1), the fork-level consolidation proof (T4) and any
  Qdrant decision (T5) remain open.
