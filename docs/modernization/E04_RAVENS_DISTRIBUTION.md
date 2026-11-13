# E.04 Muninn/Huginn ravens distribution — implementation record (Team 01, 2026-11-13)

**Outcome: DISTRIBUTION PROVEN — the E.04 blocker is dissolved.**
The W08-era record "the ravens have no GitHub repo; repo creation
is Volmarr's alone" was STALE when written into the ledger: the
repo exists, was created by Volmarr himself on 2026-10-31, and
carries the muninn 1.0.0 + huginn 1.0.0 packages published that
same day — byte-identical to the packages this fork pins. The
new-machine route (clone the repo as the sibling `ravens` tree,
select the `volmarr-ravens` extra) is proven end-to-end below.
The fork pin does NOT move: it names the local tree HEAD
`fc761f020b39…`, and the repo HEAD has since advanced past the
publication with package growth at an UNCHANGED version 1.0.0 —
adopting that growth is a separate future update (E04-T1), not a
silent re-point of the pin.

## The stale record, corrected (measured, not inherited)

- Repo: `hrabanazviking/Huginn-and-Muninn-Ravens` — created by
  Volmarr on 2026-10-31 (initial commit `d54db7d`, LICENSE,
  authored by Volmarr Wyrd). No repo was created by this slice;
  repo creation remains Volmarr's alone and was never needed.
- Publication, all 2026-10-31: `f12fb39` "The ravens, as modular
  parts: muninn 1.0.0 + huginn 1.0.0" (the packages at repo root),
  `0df5a78` README + full documentation suite, `05440ddb` the
  212-slice Ravens roadmap (RAVENS_ROADMAP_2026-10-31).
- Repo HEAD measured 2026-11-13 by `git ls-remote` and by a
  fresh clone directly under $HOME (`~/ravens-e04`):
  `17d6bd8b7d8a9bc7b9446f1cdf20b8d0bff6f94c` (RM-067, dated
  2026-11-03) — 73 commits total, 69 since the roadmap commit
  `05440ddb`: the RM-001..RM-067 ravens-roadmap campaign.
  Layout: `muninn/` + `huginn/` at root (pyproject, src, tests,
  scripts, INTERFACE.md each), root LICENSE, README,
  CAMPAIGN_STATE.md, docs/.
- License: repo root `LICENSE` is the MIT text, "Copyright (c)
  2026 Volmarr Wyrd" (sha256
  `c006b7010fa0c6dc396e405025475c03352effe1495e67e0f9d9a11f427b0383`),
  present since the initial
  commit. This matches what COMPONENT_LICENSES.md records (MIT)
  for both packages — its license statements were right; only
  its "no GitHub home yet" statements were wrong, and those are
  corrected in this slice. The local pinned tree `~/ravens` has
  NO root LICENSE file: there the MIT grant lives only as the
  `license = { text = "MIT" }` declaration plus `authors =
  [{ name = "Volmarr Wyrd" }]` in each package's pyproject.toml.

## Byte-compare — repo vs the pinned tree (fc761f020b39)

Method: `diff -rq` of the repo clone against `~/ravens`, package
trees only, excluding `__pycache__` and `*.egg-info` (generated).

- **At the publication commit `f12fb39`: IDENTICAL.** Extracted
  via `git archive` to `~/ravens-pub` and diffed: the only delta
  is a `.pytest_cache` directory on the local side — a generated
  artifact, not package content (log `~/team01-e04-diff-pub.log`).
  The published 1.0.0 packages ARE the pin's packages.
- **At repo HEAD `17d6bd8b`: the packages have GROWN past the
  pin** (log `~/team01-e04-diff.log`). muninn: 8 files differ
  (pyproject.toml, INTERFACE.md, scripts/benchmark.py,
  src config.py / core.py / _db.py, 2 test files) and 79 paths
  exist only on the repo side (new src modules `_attest.py` and
  `_crypto.py`, the RM-049 store-encryption extra's support,
  gate/benchmark scripts and their JSON records, golden files,
  and ~60 new test files). huginn: 11 files differ (pyproject,
  INTERFACE.md, benchmark.py, src config.py / core.py / _db.py /
  local_backend.py / qdrant_backend.py / text.py, 2 test files)
  and 69 repo-only paths (same growth shape). The pyproject
  diffs add an `encryption` extra (`cryptography>=42,<51`) and
  dev tooling floors — and **the version fields are unchanged:
  1.0.0 in all four places** (repo muninn, repo huginn, pinned
  muninn, pinned huginn). Two different package bodies now share
  the version number 1.0.0; that hazard is ticket E04-T1's core.

## Proof (a) — the repo copies' own suites, fresh venv: PASS with root-caused environment findings

- Fresh venv under $HOME (`~/ravens-e04/.venv-e04`, Python
  3.14.4; re-run identically in `.venv-e04-312`, Python 3.12.13)
  with non-editable installs FROM THE REPO COPIES
  (`pip install ./muninn ./huginn`, cryptography 50.0.2,
  qdrant-client 1.20.0, pytest 9.2.0 — versions from the logs).
  The PyPI muninn/huginn packages were never installed anywhere
  in this slice.
- Result, identical in both interpreters (logs
  `~/team01-e04-proofa.log`, `~/team01-e04-proofa312.log`):
  **muninn 443 passed / 2 failed of 445; huginn 352 passed /
  1 failed of 353.** The totals are exactly the repo's own
  RM-067 banking counts (445 / 353) — the suites have grown far
  beyond the 1.0.0 baselines (36 / 27) through the RM campaign,
  which is why the counts differ from the W08-era numbers.
- The 3 failures are root-caused to THIS machine's SQLite, not
  to package logic (ticket E04-T2 for the ravens line):
  1. muninn `test_write_path.py::test_committed_record_carries_
     the_gate` asserts the machine SQLite equals the committed
     benchmark record's environment — record made under SQLite
     3.45.1, this machine runs 3.50.4. An environment pin, by
     the test's own design.
  2.+3. muninn + huginn `test_readonly_filesystem.py::
     test_readonly_store_file_fails_loudly_and_immediately`: the
     read-only refusal itself fires correctly, but the refused
     open leaves `h.db-wal` / `h.db-shm` sidecars at mode 0o444
     under SQLite 3.50.4, and the re-open then fails on those
     stale sidecars (`health()` reports the typed read-only
     error; `KeyError: 'integrity'` at the test's health
     assertion). Reproduced standalone both packages' shape
     (huginn repro in this slice's working notes).
  Neither failure touches distribution: both fire against the
  repo's post-1.0.0 growth code in an environment the ravens
  campaign did not bank against (its RM-067 record already
  notes its banking ran from a /var/tmp tree under a home-quota
  constraint, with home-tree reconciliation still owed there).

## Proof (b) — fork ravens contracts against the pinned tree: PASS

- `scripts/run_tests.sh` on `test_volmarr_ravens.py`,
  `test_volmarr_ravens_writes.py`, `test_volmarr_memory_fabric.py`
  in the team worktree (canonical `~/ravens` sibling at the pin):
  **3 files, 21 tests passed / 0 failed**
  (log `~/team01-e04-proofb.log`). Serialized behind the Samverk
  S-308 full suite via a waiter, per the shared-laptop law.

## Proof (c) — new-machine resolution from the repo copies: PASS

- Staging under $HOME: `~/e04-stage/hermes` = a copy of this
  worktree; `~/e04-stage/ravens` = a fresh `git clone` of
  `hrabanazviking/Huginn-and-Muninn-Ravens` (HEAD `17d6bd8b…`),
  so the staged tree's `../ravens` sibling IS the repo clone —
  no hand-carried founding tree anywhere in the stage.
- `uv sync --extra volmarr-ravens` in the staged tree: exit 0;
  the resolver built both packages from the clone
  (`huginn==1.0.0 (from file:///home/volmarr/e04-stage/ravens/
  huginn)`, same for muninn) and never reached PyPI for these
  names — the `[tool.uv.sources]` path binding does its job
  against a repo clone exactly as against the founding tree
  (log `~/team01-e04-proofc.log`).
- Imports in the staged venv resolve INTO the clone:
  `muninn.__file__` = `~/e04-stage/ravens/muninn/src/muninn/
  __init__.py`, huginn likewise; versions 1.0.0 / 1.0.0.
- Bonus proof: the fork ravens contracts (same 3 files as
  proof (b)) run in the STAGED tree — i.e. against the repo
  HEAD packages, growth and all: **21 passed / 0 failed**
  (log `~/team01-e04-proofc2.log`). The repo's current packages
  still satisfy this fork's ravens contract surface.

## The new-machine distribution recipe (exact)

1. `git clone https://github.com/hrabanazviking/hermes-agent-RuneForgeAI-hack.git`
   and, BESIDE it (same parent directory):
   `git clone https://github.com/hrabanazviking/Huginn-and-Muninn-Ravens.git ravens`
   — the sibling directory MUST be named `ravens`: the fork's
   `[tool.uv.sources]` binds `../ravens/muninn` and
   `../ravens/huginn`, editable.
2. In the fork checkout: `uv sync --extra volmarr-ravens`
   (or select the extra in whatever env build the machine uses).
   The resolver takes muninn/huginn from the sibling clone;
   PyPI is never consulted for these names. Never
   `pip install muninn` / `pip install huginn` — both PyPI
   projects are unrelated software (Slice 86 record).
3. Provenance choice: check the clone out at `f12fb39` to get
   exactly the pinned 1.0.0 packages, or at HEAD for the RM-
   grown packages (same version number — see E04-T1).

## Records updated in this slice (and what did NOT change)

- `integration-lock.json` Muninn + Huginn rows: `repo` null →
  `hrabanazviking/Huginn-and-Muninn-Ravens`; verdict → "current
  — E.04 executed 2026-11-13 (distribution repo proven; pin
  stays the local tree HEAD)"; verification method/notes carry
  the E.04 measurements. `pinned` and `current_head` UNCHANGED
  (`fc761f020b39…` — the pin is a local-tree HEAD and is not
  re-pointed at repo semantics).
- `INTEGRATION_MATRIX.md` rows 4/5: repo cell and verdict cell
  updated as above; Blockers item 4 rewritten as resolved with
  its remainders named.
- `COMPONENT_LICENSES.md` Muninn + Huginn rows: only the proven-
  wrong "no GitHub home yet" sentence replaced with the repo +
  publication facts; license (MIT), pins and the PyPI warning
  unchanged.
- Pin-guard tests: NO change needed —
  `tests/plugins/test_volmarr_integration_ledger.py` asserts the
  ravens pin / current_head / verification status and the
  absence of the superseded absence claim; it asserts no repo or
  verdict values, and all its assertions still hold on the
  updated lock (verified in the gate run below).
- README.md untouched (sha256
  `336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`
  before and after).

## Honest remainders (named, not hidden)

- **E04-T1 — repo-HEAD adoption decision (future update):** the
  repo's packages have grown 69 commits past the published
  1.0.0 (new modules, encryption extra, core growth) while the
  version stayed 1.0.0 in both pyprojects. A future slice must
  decide, with the ravens project, whether the fork pin adopts
  a repo commit — and the ravens line should bump the version
  when it next publishes, so 1.0.0 names one package body.
  Proof (c2) shows the fork contracts already pass at HEAD.
- **E04-T2 — repo-HEAD suite failures in this env:** the 3
  SQLite-3.50.4 failures in proof (a) belong to the ravens
  campaign: re-prove its suites in its own banking environment
  or fix the WAL-sidecar cleanup in the RM-030 road.
- **E04-T3 — pin tree has no remote:** `~/ravens` (the pinned
  local tree) has NO git remote configured, so it is not wired
  to its own distribution repo. Adding the remote is a small
  ravens-line action; this slice did not touch `~/ravens`.
- The §32 release scorecard still reads NOT releasable; E.04
  changes distribution truth only, nothing else.

## Fork gate — full contract set on this tree: PASS

- `scripts/run_tests.sh` (`tests/plugins/test_volmarr_*.py`
  `tests/plugins/test_kista_*.py`) on the committed E.04 tree,
  serialized behind other campaigns' suites by waiter:
  **137 files = 1,171 passed / 7 failed / 1 skipped** — the 7
  failures are exactly the known live-transport set
  (5x test_volmarr_core_plugin.py, 1x
  test_volmarr_verdandi_stimuli.py, 1x
  test_volmarr_voice_runner.py), name-identical to the banked
  baseline; zero regressions (log
  `~/team01-e04-fullcontracts.log`). The pin-guard battery
  (test_volmarr_integration_ledger.py) passes on the updated
  lock inside this run. Worktree clean at the end; README
  sha256 unchanged before and after.
