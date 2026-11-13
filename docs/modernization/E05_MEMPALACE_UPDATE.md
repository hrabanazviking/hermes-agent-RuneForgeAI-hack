# E.05 MemPalace (official) update — implementation record (Team 01, 2026-11-13)

**Outcome: PIN MOVED — all five proofs pass.** The official
engine has moved two minor versions past the pin (3.10.0 →
3.12.0, 585 commits). The fork's surface is unchanged and
read-only: a version-checked probe that reads the palace's
`chroma.sqlite3` collections table through a read-only sqlite
connection (never opening ChromaDB), plus an opt-in default-off
BM25 retrieval route that calls only
`search_memories(vector_disabled=True)`. At the target the
upstream `mempalace.searcher` module has been restructured into
a package, but its own header states the public import path
remains `mempalace.searcher`, `search_memories` is still
exported there, and every proof below runs against the real
target package. No MemPalace source was copied into the fork.

## Target (re-measured, not inherited)

- Pin (before this slice): `22fd87f09c19d5ffb2d6966486483353937931c0`
  (v3.10.0 — exactly the peeled `v3.10.0^{}` commit) —
  COMPONENT_LICENSES.md, integration-lock.json,
  INTEGRATION_MATRIX row 6.
- Target: `0ed1be82dcbe4f59081b87c4eaa0986af0768ff4` —
  re-measured 2026-11-13 by
  `git ls-remote https://github.com/MemPalace/mempalace.git HEAD`,
  identical to the keeper's measurement the same day; the lock's
  2026-11-08 `current_head` (`fa6ae179d852…`) is superseded.
- Tags re-measured by ls-remote and in the clone: `v3.11.0^{}` =
  `602d796c699cabba2971982cd9dccbbf46abfe79`; `v3.12.0` resolves
  to commit `4df7b830ff1398332d4118884520a24f1aab9cc1`. HEAD is
  past the v3.12.0 tag merge and the package `__version__` at
  HEAD (read from `mempalace/version.py` in the clone and from
  the installed package) is **3.12.0**.
- Delta in a fresh clone directly under $HOME (`~/mempalace-e05`):
  `git log 22fd87f0..0ed1be82` = **585 commits**.
- Mirror row is NOT part of this pin move: `hrabanazviking/mempalace`
  HEAD re-measured = `ff1bdf03407bc5d6c571fa85f8c621d7177de616`,
  unchanged; it stays reference-only.
- License: MIT — PASS, verified at the text level this slice:
  `LICENSE` at the pin and at the target are byte-identical
  (sha256 of both, read via `git show <commit>:LICENSE` in
  `~/mempalace-e05`:
  `81dc6cc278d80f0f1b028ecd86af30d61e441b9ae53d9d9a2ed19389ba657a5d`).
  The license does not change across the pin move.

## Proof 1 — MemPalace's own suite at target: PASS with root-caused environment findings

- Environment: clean venv under the clone
  (`~/mempalace-e05/.venv-e05-313`, Python 3.13.13 — inside
  upstream CI's tested matrix 3.10/3.11/3.13) with the package
  installed FROM THE LOCAL CLONE (`pip install -e ".[dev]"`,
  mempalace 3.12.0 editable from `~/mempalace-e05`, chromadb
  1.5.9, pytest 9.2.0; log `~/team01-e05-setup313.log`). No PyPI
  pull of a different mempalace version anywhere in this slice.
- Full run (CI's own command shape: `pytest tests/
  --ignore=tests/benchmarks -n auto --dist loadfile -q`, with
  the launch shell's soft fd limit raised to 65536):
  **8,556 passed / 4 failed / 79 skipped, 0 errors** in 161s
  (log `~/team01-e05-proof1-313.log`).
- The 4 failures are root-caused to this machine, not the engine,
  and all 4 pass on re-run (below):
  1.–3. `test_init.py::test_init_strips_foreign_paths_beneath_
     the_running_prefix[other-python|nested-venv|site-packages-child]`:
     the test spawns `python -c` with cwd = the system temp dir;
     a stray `/tmp/inspect.py` (253 bytes, dated 2026-11-05, a
     leftover WoldVirtual dissection scratch file that opens a
     since-deleted wv-stage1 path) shadows the stdlib `inspect`
     module for that subprocess, so its later `import
     pydantic_core` crashes inside `typing_extensions`. The
     behaviour under test was itself correct in the captured
     output (`OWN_PRESENT: True`, `FOREIGN_PRESENT: False` —
     MemPalace stripped the foreign path as designed). The stray
     file was left untouched (it is not this campaign's to
     delete); the re-run used a clean `TMPDIR` under $HOME.
  4. `test_hook_mine_shutdown.py::test_armed_watchdog_waits_for_
     interpreter_shutdown`: the spawned process died with
     returncode −9 (SIGKILL) during the full parallel run, while
     the laptop carried a load average above 17 from other
     campaigns' work; it passes serially (below).
- Re-run of exactly those 4 tests, serially, with `TMPDIR`
  pointed at a clean directory under $HOME and the same fd
  limit: **4 passed / 0 failed** in 1.71s
  (log `~/team01-e05-proof1-rerun.log`). Proof 1 therefore
  stands at 8,560 distinct tests passing at the target.
- First attempt, recorded honestly: the same suite first ran
  under the laptop's default Python 3.14.4 (outside upstream's
  CI matrix) with the default soft fd limit of 1024 and scored
  7,444 passed / 781 failed / 79 skipped / 335 errors
  (log `~/team01-e05-proof1.log`) — 1,117 "Too many open files"
  occurrences across 16 xdist workers, cascading into ChromaDB
  "unable to open database file" fixture errors. That run is an
  environment artifact, superseded by the 3.13 run above; it is
  kept as the reason this record specifies interpreter and fd
  limit for future MemPalace suite runs on this laptop.

## Proof 2 — store-schema verification at target (the lock's E.05 assignment): PASS

Harness `~/team01-e05-palace.py` (deterministic hash embeddings,
the engine's own test-fixture shape; 3 drawers: JWT auth,
Alembic/PostgreSQL, sprint planning). Palaces were built with
the REAL packages through ChromaDB's `PersistentClient`
(`get_or_create_collection("mempalace_drawers")`), never by
hand-writing the sqlite schema.

- **Target-built palace** (`~/e05-proof-palace-target`, built by
  mempalace 3.12.0, log `~/team01-e05-build-target.log`): the
  fork's real `probe_mempalace` (the team tree's
  `plugins/volmarr-core/mempalace.py`, loaded with the target
  package importable) reports **healthy, collection_present,
  package_version 3.12.0, database_bytes 196608**
  (log `~/team01-e05-proof23-target.log`).
- **Back-compat, pin-built store under the target package:** a
  second palace built by the PIN package (3.10.0, clone
  `~/mempalace-e05-pin` at `22fd87f0…`, own venv, log
  `~/team01-e05-build-pin.log`) probes **healthy under the fork
  adapter with the target 3.12.0 package installed**, and its
  BM25 search (proof 3 route) returns the correct drawer
  non-mutating (sha256 `b31668a5b46c…` before and after;
  log `~/team01-e05-proof2b-target-on-pin.log`). Control: the
  same store also probes healthy under the pin package itself
  (log `~/team01-e05-proof2b-pin-on-pin.log`). A 3.10.0 store
  therefore does NOT break at the target — this is why
  `MINIMUM_PACKAGE_VERSION` stays **3.10.0** (see Pin move).

## Proof 3 — read-only BM25 retrieval at target: PASS

- Signature verified live at the target:
  `search_memories` parameters include `query`, `palace_path`,
  `n_results`, `collection_name` and `vector_disabled` (full
  list in the proof logs) — the fork's keyword call shape is
  unchanged and valid.
- Against the target-built palace, calling exactly as
  `mempalace_retrieval.py` does (`query="JWT authentication
  tokens"`, `n_results=5`, `collection_name="mempalace_drawers"`,
  `vector_disabled=True`): **1 result, the JWT drawer first**
  (`drawer_proj_backend_aaa`, verbatim text), and
  `chroma.sqlite3` sha256 **byte-identical before/after**
  (`1233aca87736892c5f0e19c85110e1bebe581bef5355b78f48c922a5684fc71e`).
  The vector path was never used; non-mutation, the load-bearing
  claim of the 2026-10-30 audit, still holds at 3.12.0
  (log `~/team01-e05-proof23-target.log`).

## Proof 4 — fork contracts: PASS (baseline; gate run below)

- Before the pin move, on the unmodified team tree:
  `scripts/run_tests.sh` on `test_volmarr_mempalace.py`,
  `test_volmarr_mempalace_retrieval.py` and
  `test_volmarr_integration_ledger.py` = **3 files, 31 tests
  passed / 0 failed** (5 + 9 + 17;
  log `~/team01-e05-baseline.log`).
- After the pin move the same batteries plus the full contract
  set are the fork gate, recorded at the end of this file.

## Proof 5 — absent / outdated package behaviour stays truthful: PASS

- Absent: in the laptop's system Python, where `import
  mempalace` fails, the fork probe answers **`package_missing`**
  (healthy False, error_type ModuleNotFoundError) — harness
  `~/team01-e05-proof5.py`, log `~/team01-e05-proof5.log`.
  Nothing was installed or faked to produce this.
- Outdated: the fork contract `test_mempalace_probe_rejects_
  pre_310_package` (a 3.9.0 package identity answers
  `package_outdated` against the 3.10.0 floor, store bytes
  unchanged) passes inside proof 4's baseline run and the gate
  run below.

## Pin move and MINIMUM_PACKAGE_VERSION

- Pin moved in this slice: `22fd87f09c19d5ffb2d6966486483353937931c0`
  → `0ed1be82dcbe4f59081b87c4eaa0986af0768ff4` (v3.12.0) in
  integration-lock.json (MemPalace row: `current_head` =
  `0ed1be82dcbe…`, `latest_tag` v3.12.0, `update_needed` false,
  verdict "current - E.05 executed"), COMPONENT_LICENSES.md
  (official half of the line only; the mirror half is
  unchanged), INTEGRATION_MATRIX.md row 6, and the pin-guard
  assertion in `tests/plugins/test_volmarr_integration_ledger.py`
  (`engines show MemPalace` added, following the E.01–E.03
  pattern — MemPalace had no such assertion before).
- `MINIMUM_PACKAGE_VERSION` stays **"3.10.0"**, unchanged in
  `plugins/volmarr-core/mempalace.py`: the pin records the
  verified current version, the minimum is the adapter's
  accepted floor, and proof 2 shows a store built at 3.10.0
  probing healthy and searching correctly under the target —
  no proof gives a reason to raise the floor and refuse 3.10
  stores.
- No CUSTOMIZATIONS.md row: no adapter behaviour changed in
  this slice; a pin move is ledger state, already carried by
  the records above (E.03 precedent).
- README.md untouched (sha256
  `336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`
  before and after).

## Honest remainders (named, not hidden)

- **E05-T1 — suite environment on this laptop (note, not a
  blocker):** MemPalace's own suite on purplelongship needs a
  CI-matrix interpreter (3.13 used here), a raised soft fd
  limit for xdist, and a temp dir free of stdlib-shadowing
  scratch files (`/tmp/inspect.py`, left in place, is the
  current example). Future engine-suite runs here should start
  from those settings instead of re-diagnosing them.
- The retrieval surface remains lexical BM25 only, exactly as
  the adapter's header records; the vector path still mutates
  the store by design of the upstream Chroma open and is still
  never used by this fork. Nothing in E.05 changes that scope.
- The §32 release scorecard still reads NOT releasable; E.05
  changes engine currency only, nothing else.
- Next in roadmap order: E.06 (OpenViking update).
