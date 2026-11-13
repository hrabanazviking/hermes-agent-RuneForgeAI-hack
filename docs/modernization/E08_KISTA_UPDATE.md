# E.08 Kista update — implementation record (Team 01, 2026-11-13)

**Outcome: PIN MOVED — all proofs pass, with pre-existing engine
findings named as tickets (all identical at the pin; the pin..target
delta carries no code at all).** The fork's surface is unchanged: the
`kista-secret-source 0.2.0` plugin, read-only — Secret Source `get`
via the plugin API, redaction-scoped. No Kista source was copied into
the fork. This slice also discharges the W08 ledger's Vault/CLI/
rotation audit assignment for row 11 (see Audit below).

## Target (re-measured, not inherited)

- Pin (before this slice): `ce6313cc392589abd43a5fcf614e0e272663961f`
  (package v2.0.0) — COMPONENT_LICENSES.md, integration-lock.json,
  INTEGRATION_MATRIX row 11.
- Target: `41a6d65863af9ec5d41ca148828a0b6863605b86` — HEAD +
  branches re-measured 2026-11-13 by `git ls-remote`: HEAD == `main`
  at that SHA; the repo carries **no tags**. The re-measured HEAD is
  identical to the lock's recorded `current_head` (measured
  2026-11-08): upstream has not moved since the ledger measurement,
  and the pin move below adopts exactly that recorded head, as in
  E.05–E.07. The pin is an ancestor of the target; the delta is
  **6 commits**, measured in the fresh clone directly under $HOME
  (`~/kista-e08`, HEAD `41a6d65863af`, clean except the `.venv`
  built for the proofs). A second clone at the pin lives at
  `~/kista-pin` for diffing.
- Delta shape: **docs-only.** 9 files changed, +36,536 / −1: two
  Bifröst roadmap documents, the Cyber-Viking visual design lawbook
  (.md + .pdf), a RuneForgeAI code-example document, three small
  repo-governance notes, and one README front-matter line removed.
  **Zero changes to `scripts/`, `tests/`, `pyproject.toml` or
  `LICENSE`** — `scripts/credstore.py` and `tests/test_credstore.py`
  are byte-identical at pin and target (verified with `diff`).
  Nothing in the delta can touch the plugin's `kista get <service>`
  JSON protocol surface.
- Package version at target: **2.0.0** (unchanged) — read in
  `pyproject.toml`, in `scripts/credstore.py` (`__version__`, and
  `--version` prints `credstore.py 2.0.0`), and from the installed
  distribution in the target venv (`kista==2.0.0 (from
  file:///home/volmarr/kista-e08)`, log `~/team01-e08-install.log`).
- License: **MIT — PASS, verified at the text level this slice.**
  `LICENSE` is byte-identical at pin and target (sha256
  `eff52e4122e240fe81f3a3b5c26399381ad82fef2b240cf44510848fefb56477`,
  MIT License, Copyright (c) 2026 Runa Gridweaver), read via
  `git show <ref>:LICENSE` and from the target tree on disk.

## Proof 1 — Kista's own suite at target: PASS with two root-caused pre-existing findings

- Suite: `tests/test_credstore.py` (the repo's only test file),
  system Python 3.14.4 / pytest 9.0.2 / cryptography 46.0.5, run in
  `~/kista-e08` at the target: **146 passed / 3 failed** in 1.28s
  (log `~/team01-e08-proof1.log`). The same suite at the pin in
  `~/kista-pin`: **146 passed / 3 failed** (log
  `~/team01-e08-proof1-pin.log`) — identical counts.
- Root cause of 2 of the 3 failures (environment, not code):
  `tests/test_credstore.py:32` hardcodes `CREDSTORE_SCRIPT` to
  `~/.hermes/skills/devops/runa-credentials/scripts/credstore.py`
  — an installed-skill location that does not exist on this host —
  so every test that reads or runs that path fails with
  FileNotFoundError while the 146 tests that import the module from
  the checkout pass. With a scratch HOME staging the target script
  at exactly that path (`~/kista-e08-proofhome`), the target suite
  reads **148 passed / 1 failed** (log
  `~/team01-e08-proof1-full-staged.log`), and the pin suite staged
  the same way also reads **148 passed / 1 failed** (log
  `~/team01-e08-proof1-pin-staged.log`).
- The remaining failure is a stale engine test, identical at pin
  and target: `TestVersionFlag::test_version_flag` asserts
  `"1.3.0" in stdout`, but the program at both refs prints
  `credstore.py 2.0.0` — the assertion was never updated when the
  package version moved to 2.0.0 (before the pin). Named as
  remainder **E08-T1**, not hidden and not rounded up to green.
  Neither finding is a pin..target regression: the test file and
  the program are byte-identical across the move.

## Proof 2 — fork kista contracts (contract set, fake-CLI surface): PASS

- Before the pin move, on the unmodified team tree:
  `scripts/run_tests.sh` on `test_kista_secret_source.py`,
  `test_kista_canary_leaks.py` and
  `test_volmarr_integration_ledger.py` = **3 files, 42 tests
  passed / 0 failed / 1 skipped** (log
  `~/team01-e08-baseline.log`). The canary battery is the
  redaction contract: the mapped secret value must never surface
  in stdout, stderr or logs outside `FetchResult.secrets`.

## Proof 3 — live Secret Source get against a synthetic target vault: PASS

- Harness `~/team01-e08-live.py` (scratch, kept on the laptop as
  evidence; log `~/team01-e08-live.log`, full result
  `~/team01-e08-live-result.json`): it builds a **synthetic** vault
  with the REAL target CLI (`~/kista-e08/scripts/credstore.py`:
  `init`, then `add e08svc` with a synthetic username and the
  synthetic canary password — no real credential was read or
  touched anywhere in this slice), in a disposable profile under
  `~/kista-e08-live`, then runs the fork's real `KistaSource.fetch`
  (binary_path pinned to the target script) against it, in the
  target venv (`~/kista-e08/.venv`, Python with cryptography
  50.0.2, kista 2.0.0 installed from the local clone).
- Result: fetch ok, both mapped fields resolve exactly
  (`E08_USER`, `E08_PASS`), zero warnings. The raw target
  `get -- e08svc` returns the entry JSON with the same fields;
  `kista list` output does **not** contain the canary (the engine
  masks sensitive fields in list); `kista status` rc 0. The canary
  appears 0 times in the harness log and result JSON — it exists
  only inside `FetchResult.secrets`, per the API contract.
- One environment condition, recorded honestly: the first live
  attempt ran the adapter under the Hermes dev-env interpreter,
  which lacks `cryptography`; the engine's import-time bootstrap
  then prints pip output to **stdout**, the adapter's JSON parse
  fails, and the fetch reports INTERNAL with both fields
  unresolved. In an interpreter where the declared dependency is
  installed (the target venv, or any real `pip install kista`
  deployment, whose environment carries cryptography), stdout is
  clean JSON and the proof passes as above. The bootstrap is
  identical at the pin (same file bytes). Named as remainder
  **E08-T2**: an engine-side wart — a consumer-visible JSON
  protocol should never share stdout with a dependency installer.

## Proof 4 — fork targeted batteries after the pin move: PASS

- Same three batteries as Proof 2, after the pin move:
  **3 files, 42 tests passed / 0 failed / 1 skipped** (log
  `~/team01-e08-targeted.log`) — the ledger battery carries the
  new Kista pin-guard assertion (`engines show Kista` pinned ==
  `41a6d65863af...`). Counts identical to the pre-move baseline.

## Proof 5 — absent / unavailable source probes fail truthfully: PASS

- In the same live harness (result JSON above): absent binary
  (`binary_path` to a nonexistent path) → fetch fails
  **BINARY_MISSING**, no secrets; unknown service
  (`kista://nosuchsvc/password` against the live synthetic vault)
  → **REF_INVALID**, no secrets; uninitialized profile (no vault)
  → **REF_INVALID**, no secrets. No error text carries the canary
  in any probe. Nothing was installed or faked to produce these.
- Classification note on the uninitialized case: the engine's
  `_get_key()` **auto-creates `.vault_key`** in the resolved vault
  directory on the read path (observed on disk in the disposable
  empty profile), after which `get` reports "No entry found" —
  hence REF_INVALID rather than NOT_CONFIGURED. A read-only get
  creating key material is an engine-side side effect worth
  naming: remainder **E08-T3** (identical at the pin).

## Vault / CLI / rotation audit (the W08 ledger's E.08 duty)

- Vault layout at target (identical at pin): `KISTA_DIR` selects
  the vault directory (default `~/.hermes/credentials`); files
  `.vault_key`, `vault.json.enc`, `vault_meta.json`, `config.json`
  and a `backups/` directory. The adapter's required-files pair
  (`.vault_key`, `vault.json.enc`) matches the engine's layout.
- File hardening: the engine chmods key, ciphertext, meta,
  config, backups and export outputs to 0600 (`_chmod_600`). The
  vault **directory** is left at the process umask (measured
  0o755 after `kista init` in this slice's harness) — and the
  fork adapter refuses any vault whose directory permits group or
  world access, per its own remediation text ("ensure its
  directory, key, and ciphertext are private to the current
  user"). A kista-initialized vault therefore needs its
  directory hardened to 0700 before the Hermes source will read
  it; the live proof applied exactly that step. Remainder
  **E08-T5** (engine init should chmod the vault directory too).
- CLI surface at target (identical at pin): `init`, `repair`,
  `add` (plus typed shortcuts incl. apikey/sshkey/certificate/
  note/totp/license/identity), `get` (full entry JSON on stdout),
  `list` (sensitive fields masked), `update`, `remove`, `check`,
  `search`, `generate-password`, `status`, `export`, `import`,
  `backup`, `restore`, `github-backup`, `config set/get/list`.
- **Rotation: there is no key-rotation or rekey verb** in the CLI
  at pin or target (no `rotate`/`rekey` anywhere in
  `credstore.py`). The available recovery paths are `repair`
  (from backups), `export`/`import` and `backup`/`restore`;
  rotating the vault key today means export → re-init → import
  by hand. Named as remainder **E08-T4** — an engine gap, not an
  adapter defect; the fork's read-only surface does not depend on
  it.

## Pin move

- Pin moved in this slice: `ce6313cc392589abd43a5fcf614e0e272663961f`
  -> `41a6d65863af9ec5d41ca148828a0b6863605b86` (package v2.0.0,
  main HEAD) in integration-lock.json (Kista row: `pinned` =
  `current_head` = `41a6d65863af...`, `update_needed` false,
  verdict "current - E.08 executed", verification rewritten with
  this slice's method and the audit findings),
  COMPONENT_LICENSES.md, INTEGRATION_MATRIX.md row 11, and the
  pin-guard assertion in
  `tests/plugins/test_volmarr_integration_ledger.py` (`engines
  show Kista` assertion added, following the E.05–E.07 pattern).
  Kista's verification status was already `verified` and stays
  `verified` — the ledger counts do not move (23 verified /
  2 partially verified / 1 blocked).
- No adapter change: no fork code was modified in this slice;
  the delta carries no protocol change to adapt to.
- No CUSTOMIZATIONS.md row: no adapter behaviour changed in this
  slice; a pin move is ledger state, already carried by the
  records above (E.03 / E.05 / E.06 / E.07 precedent).
- `docs/modernization/ADAPTER_COMPATIBILITY_MATRIX.md` still
  shows the W08-era pin for Kista (as it does for MemPalace,
  OpenViking and WYRD): it is a dated audit snapshot that no
  E.05–E.07 slice updated, and it is left untouched here for the
  same reason.
- README.md untouched (sha256
  `336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`
  before and after).

## Honest remainders (named, not hidden)

- **E08-T1** (engine test defect, pre-existing): the engine
  suite's version-flag test asserts `1.3.0` while the program
  prints `2.0.0`; identical failure at pin and target.
- **E08-T2** (engine wart, pre-existing): when `cryptography` is
  absent in the invoking interpreter, credstore's import-time
  bootstrap writes pip output to stdout and breaks the JSON get
  protocol for that run (the fork adapter reports INTERNAL).
  Deployments that install kista normally carry the dependency
  and never see it.
- **E08-T3** (engine side effect, pre-existing): a `get` against
  an uninitialized profile auto-creates `.vault_key`; the fork
  surfaces the outcome as REF_INVALID, not NOT_CONFIGURED.
- **E08-T4** (engine gap): no vault key rotation / rekey verb
  exists; rotation is a manual export → re-init → import.
- **E08-T5** (engine hardening gap): `kista init` leaves the
  vault directory at umask permissions (0o755 measured) while
  chmodding its files to 0600; the fork adapter requires the
  directory private too, so a fresh vault needs a manual
  `chmod 700` before Hermes will read it.
- The section 32 release scorecard still reads NOT releasable;
  E.08 changes engine currency only, nothing else.
- Next in roadmap order: E.09.

## Fork gate — full contract set on this tree: PASS

- Full contract set via `scripts/run_tests.sh`
  (`tests/plugins/test_volmarr_*.py` + `tests/plugins/test_kista_*.py`)
  on this tree: **137 files = 1,171 passed / 7 failed /
  1 skipped** — the 7 failures are exactly the known
  live-transport set (5x test_volmarr_core_plugin.py, 1x
  test_volmarr_verdandi_stimuli.py, 1x
  test_volmarr_voice_runner.py), name-identical to the banked
  baseline; zero regressions (log
  `~/team01-e08-fullcontracts.log`; gate start 18:50:50 EST,
  load at launch 0.82 / 1.95 / 3.86 recorded in that log).
- README sha256 unchanged before and after (`336813d11bbe...`).
  Worktree banking is the keeper step that follows this record.
