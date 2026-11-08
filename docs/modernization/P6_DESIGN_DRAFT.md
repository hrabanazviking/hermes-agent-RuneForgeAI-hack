# P6 Design Draft — W07 Persona Operations (Team 08, PREP ONLY)

Status: DESIGN / AUDIT PREP ONLY. No implementation. Uncommitted draft,
matching the established prep pattern (cf. Team 04 P0P1_DESIGN_DRAFT.md,
Team 05 P2_DESIGN_DRAFT.md, Team 06 P3P4_DESIGN_DRAFT.md, Team 07
P5_DESIGN_DRAFT.md). Written 2026-11-08 by Team 08 lead against tree
`1558f5583426efb7a465a344e4c700f5db38270d` (origin/main: W01/W02/W03/W04
banked). Branch `yrsa/hermes-team-08` was fast-forwarded
`b5c6743a22..1558f55834` (clean fast-forward, merge-base verified, no
conflicts) before this audit. README.md untouched: sha256
`336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`
verified before and after the fast-forward.

Scope: roadmap tickets **P.012, P.013, P.018, P.020** — Phase P6 (§12:
persona operations and character-drift assurance). Governing gate
(WAVE_PLAN Team 08 entry + roadmap §30, W07 row): **no stub command
or invented result** — every command in the §12 table must operate
on a real temporary gateway profile. Ground rule (§28.2): contracts
banked as pure record builders with no live caller get real callers
here, or an honest record of why not. Never re-declare complete
without live callers.

Contract baseline at this base (keeper-verified at W04 banking, log
`~/team05-w04-contracts.log` on the laptop): **121 files = 976 passed /
7 failed / 1 skipped** via `scripts/run_tests.sh`; the 7 failures are
the known live-transport set, name-identical since the freeze. Every
W07 gate below is graded against this baseline.

Governing texts read this run: `CAMPAIGN_STATE_MODERNIZATION.md` and
`WAVE_PLAN.md` in `~/hermes-hack-forge`; roadmap §12 (the command
table), §28.2–28.3, §30 (W07 gate), §31 (tickets P.012/P.013/P.018/
P.020) in the team-08 tree; `docs/modernization/W03_P0P1_IMPLEMENTATION.md`;
`docs/modernization/W04_P2_IMPLEMENTATION.md`; Team 06's unbanked
`P3P4_DESIGN_DRAFT.md` and Team 07's unbanked `P5_DESIGN_DRAFT.md`
(read as in-flight design, not as banked fact).

---

## 0. Headline findings

1. **The §12 command table has zero live commands today.** Of its 13
   rows, **0 are live, 9 are backed only by pure contract builders or
   banked library code, and 4 do not exist at all** (status, files,
   reload --activate as an effect, backup/restore). The CLI host they
   would hang from is real — `hermes volmarr …` is registered in
   `plugins/volmarr-core/__init__.py` (`register_cli_command`, :156)
   with health/cognition/memory/world/identity/heartbeat/routines/
   sleep/agency/self-family verbs in `plugins/volmarr-core/cli.py`
   (667 lines) — but a repo-wide grep for `persona` in `cli.py`
   returns **zero hits**: no persona subcommand is registered, and no
   module outside `persona_runtime.py` and its tests calls any of the
   §71–§76 builders (verified this run: caller grep across `plugins/`,
   `agent/`, `hermes_cli/`, `tools/` excluding `persona_runtime.py`
   itself returns nothing).

2. **The pure builders are real, complete, and honest about being
   pure.** `plugins/volmarr-core/persona_runtime.py` (15,408 lines)
   carries §70 validator, §71 `persona_inspect` (:8868), §72
   `persona_explain` (:8995), §73 `persona_reload` (:9103), §74
   `persona_diff` (:9234), §75 `persona_export` (:9440) and §76
   `persona_import_plan` (:9655) — every docstring says `Pure.`, every
   function operates on a *supplied* compile/bundle, and the
   `*_example()` functions return the roadmap's example records.
   Those examples are exactly what the W07 gate forbids a real
   command from returning. W07's job is the disk/live-state plumbing
   *in front of* these builders, never a re-implementation of them
   and never a wrapper that feeds them example data.

3. **Four §12 rows have no builder at all.** There is no
   `persona_status`, `persona_files`, `persona_search`,
   `persona_validate`, `persona_backup` or `persona_test` function
   and no `STATUS/FILES/SEARCH/VALIDATE/BACKUP/TEST_COMMAND` constant
   in `persona_runtime.py` (verified this run; the only command
   constants are INSPECT/EXPLAIN/RELOAD/DIFF/IMPORT at :8834–:9642
   plus BOOTSTRAP `hermes persona create` :10275). Their substrates
   partly exist — status/files from the W03 manifest + W04 index
   meta, search from W04 `PersonaIndex.retrieve`, validate from the
   §70 catalogue, test from §§57–63 — but the command records
   themselves are W07 build items, not wiring of existing records.

4. **The command spelling itself is unreconciled.** The §71–§76
   constants name `hermes persona inspect` etc., while the only
   registered plugin CLI root is `hermes volmarr` (`__init__.py:156`).
   The builders' own headers note the `hermes persona` spelling
   "registers no new core" command. W07 must pick one spelling and
   record it (see §12/Q1); shipping both spellings as aliases that
   can drift apart would repeat the duplicate-owner disease W05 is
   removing from the prompt path.

5. **Drift assurance is a contract library, not a watchdog.**
   §§27–28 `PersonaWatchdog`/`drift_score` (:2995/:3033), §30
   `repair_plan` (:3267), §31 fast local watchdog (:3377) and
   §§57–63 (drift scenarios, golden records, style/behaviour
   fingerprints, telemetry, model-quality router) are all pure:
   no draft, turn, or response ever reaches them. PresentState's
   `post_llm_call` captures turns for state and never scores them
   (Team 06 draft §2, row 15, re-verified by caller grep this run).
   §12's requirement is precise: the watchdog becomes a *bounded
   diagnostic service* — it may report and propose, it **cannot
   rewrite canon**. §30's "repair" must therefore surface in P6 as
   a *proposal for an authorised editor*, never an applied fix.

6. **There is no persona editor or pager — but the paging mechanics
   are banked.** No persona file editor exists on any surface: the
   Desktop memory settings are provider/layer configuration (Team 07
   draft, finding 9d), the Desktop right-sidebar file browser is a
   generic workspace tree, and stock `hermes_cli/personality.py` is
   a small named-overlay selector (built-in one-paragraph
   personalities + config overrides), not an editor for authored
   canon. What does exist: W04 `PersonaIndex.read_page` (:955),
   `read_section_page` and `continue_read` (:801) — byte-cursor,
   UTF-8-boundary-safe paged reads whose concatenation reproduces
   the source byte-for-byte, contract-tested — and W03's streaming
   ingester/exporter. P.013 is a *surface* built on those mechanics
   (CLI pager first, then a virtualised viewer), not new storage.

7. **Private/public filtering exists for exactly one egress path:
   embeddings.** W03 records carry `privacy_class`
   (`private`/`shared`/`public`, `canonical_library.py:80`) and a
   `destinations` list (:213), and W04's consent gate is fail-closed
   where it applies: cloud embedding of a `private` source is
   refused at grant time without a recorded operator override, and
   consent is re-checked at embed and query time
   (`persona_index.py:1056` grant, :1074 the private/cloud refusal).
   But **no filter sits before general cloud inference**: the
   cognition router (`routing.py`, `CognitionRouter.decide` :151)
   chooses `cloud` for deep mode, tools/vision/external-data
   capability, complexity or size without ever reading a privacy
   label; the prompt packet assembler applies budgets, not privacy;
   and stock `hermes_cli/model_data_policy_guard.py` warns about
   *training tiers*, which is a different question. P.018 is the
   design and test of that missing enforcement point (§7 below).

8. **The laptop deployment is dormant, so `status` must be able to
   say so.** Verified this run: `~/.hermes/` holds a 667-byte
   `SOUL.md`, an empty `memories/`, and **no `profiles/` directory**;
   the launch recipe (`docs/modernization/LAUNCH_RECIPE.md`, W02) is
   proven by cold-install but the live deployment is dormant by
   choice. A P6 `status` that invents an active ID, hash or index
   completeness for this state would fail the gate on its first
   real run. The honest outputs — no profile, gateway not running,
   index unbuilt — are first-class results in this design (§3).

9. **W05 and W06 are dependencies in flight, not foundations.**
   Team 06's P3P4 draft is complete and uncommitted in
   `~/hermes-team-06`; its implementation (live kernel channels,
   per-turn snapshot, atomic next-turn activation, P.011 receipts)
   is unbanked at audit time. Team 07's P5 draft is likewise prep.
   P6 *consumes* W05's activation seam and receipts and W06's
   editor/receipt-retention outcomes where they land, but every
   command in §3 is designed against **banked** seams only (W03
   manifest, W04 index + on-disk receipts, §§19/20 hash/reload,
   §§70–76 builders), with W05/W06 integration as detected-at-runtime
   adapters. No unbanked code is imported, assumed, or waited on.

---

## 1. Inventory — every P6 surface, classified

Classification key (roadmap §28.3 evidence stages, applied strictly):
**LIVE** = a real caller exercises it today. **PARTIAL** = wired but
gated/default-off, metadata-only, or enforced on one path only.
**CONTRACT** = module + deterministic tests, no live caller.
**ABSENT** = named by §12/P6, not present in the tree.

| # | Surface | Evidence (this base) | Class |
|---|---------|----------------------|-------|
| 1 | `hermes volmarr` CLI host | `__init__.py:156` `register_cli_command`; `cli.py` `register_cli` :43 + `health_command` :328; verbs for health/cognition/memory/world/identity/heartbeat/routines/sleep/agency/§21 self-family | LIVE (host only — no persona verb) |
| 2 | Stock personality overlay | `hermes_cli/personality.py`: built-in one-paragraph overlays + config overrides; live on prompt surfaces; unrelated to authored canon | LIVE (not P6) |
| 3 | PersonaRuntimeBridge packet item | `__init__.py:144` source in PresentState tuple; gated `persona_runtime_enabled` (default false, `plugin.yaml:548`); injects contract description + hashes, never canon text (Team 06 §1.2) | PARTIAL |
| 4 | PersonaCanonBridge packet item | Same tuple; gated `persona_canon_enabled` (default false); injects a contradiction count only; canon file read-only to runtime | PARTIAL |
| 5 | W04 embeddings consent gate | `persona_index.py` `grant_consent` :1056, private/cloud refusal :1074, re-checks at embed/query, revocation deletes vectors; contract-tested with a local fake provider | PARTIAL (one egress path) |
| 6 | §70 persona validator | `persona_runtime.py:8640+`: pure issue catalogue over a supplied compile | CONTRACT |
| 7 | §71 inspect | `persona_inspect` :8868 + display/example/contract; pure over a supplied compile | CONTRACT |
| 8 | §72 explain | `persona_explain` :8995 over supplied section ids; no turn/receipt store feeds it | CONTRACT |
| 9 | §73 reload record | `persona_reload` :9103 compares two supplied compiles; §20 `PersonaReloader.check` is explicit-call only, no watcher/hook/CLI | CONTRACT |
| 10 | §74 diff | `persona_diff` :9234 between two supplied compiles | CONTRACT |
| 11 | §75 export | `persona_export` :9440 builds a bundle *record*; no code writes a bundle file to disk | CONTRACT |
| 12 | §76 import | `persona_import_plan` :9655 plans over a supplied bundle; nothing installs, collides-checks against a live profile, or mutates | CONTRACT |
| 13 | §§27–28 watchdog + drift score | `watchdog_contract` :2995, `drift_score` :3033; no response ever reaches them | CONTRACT |
| 14 | §30 repair pipeline/plan | `repair_pipeline` :3178, `repair_plan` :3267; pure plans | CONTRACT |
| 15 | §31 fast local watchdog | `local_watchdog_tasks` :3377 + contract; six named tasks, no runner | CONTRACT |
| 16 | §§57–58 drift/golden tests | `drift_test_scenarios` :6860, `golden_record` :6947; scenario/record shapes, no replay runner | CONTRACT |
| 17 | §§59–63 fingerprints/telemetry/quality | Style/behaviour fingerprints, §61 telemetry records, §62 quality table over supplied averages; no live telemetry is recorded | CONTRACT |
| 18 | W03 canonical library | `canonical_library.py` (1,124 ln): manifest, roles, privacy classes, streaming ingest/export; callers: tests + `persona_index.py` only | CONTRACT (library) |
| 19 | W04 persona index | `persona_index.py` (1,290 ln): `sync` :362, `retrieve` :604, `continue_read` :801, `cite` :872, `read_page` :955, receipts under `generated/receipts/`; callers: tests only | CONTRACT (library) |
| 20 | §19/§20 hash record + reload check | Pure; consumed inside compile/reload records only | CONTRACT |
| 21 | §12 `status` command | No builder, no constant, no CLI verb (finding 3) | ABSENT |
| 22 | §12 `files` command | No command; substrate is row 18's manifest inventory | ABSENT |
| 23 | §12 `reload --activate` effect | No live generation swap exists to call; W05's snapshot/activation is unbanked design (finding 9) | ABSENT |
| 24 | §12 `backup/restore` (persona) | No persona backup command; the W00 `~/.hermes` tar is a campaign artefact, not a persona operation, and its encryption remainder W00.03-ENC is still open | ABSENT |
| 25 | Huge-file persona editor/pager (P.013) | No persona editor on CLI/TUI/Web/Desktop; generic file browser + library paged read (row 19) are not it (finding 6) | ABSENT |
| 26 | Pre-inference private/public filter (P.018) | No enforcement point reads `privacy_class`/`destinations` before a cloud LLM call (finding 7) | ABSENT |

**Counts: 26 inventoried P6 surfaces — 2 LIVE (rows 1–2, both
non-persona hosts), 3 PARTIAL (rows 3–5), 15 CONTRACT with no live
caller (rows 6–20), 6 ABSENT (rows 21–26).** For the §12 command
table itself (13 rows, §3): **0 live, 9 contract-backed** (search via
row 19; inspect, explain, validate, diff, reload --dry-run via rows
6–10/20; export, import --dry-run via rows 11–12; test via rows
16–17), **4 absent** (status, files, reload --activate, backup/
restore). That is the honest baseline W07 must move, row by row.

---

## 2. The live temporary gateway profile (the gate's testbed)

Every command in §3 is specified and gated against the same fixture,
built only from banked, proven pieces:

- **Disposable `HERMES_HOME` directly under `$HOME`** (e.g.
  `~/hermes-p6-fixture-<run>/`), satisfying the W02 staging law: the
  checkout and `~/ravens` stay siblings, the relative
  `[tool.uv.sources] ../ravens` binding resolves, and nothing ever
  touches the dormant live `~/.hermes`.
- **Staged by the W02 recipe** (`docs/modernization/LAUNCH_RECIPE.md`):
  `scripts/run-in-hermes-env` / `source ./activate`, PM generation
  venv, all 9 fork plugins discovered. No Docker, ever.
- **One named temporary profile** created through stock profile
  mechanics, holding a *synthetic* authored corpus: a multi-file
  persona (SOUL/identity/relationships/service-bible roles per the
  W03 `_FILENAME_ROLES` map), one deliberately buried section, one
  `private` and one `public` document (for §7), and one document
  over the W04 subspan threshold. Corpus bytes are generated
  deterministically in the test, hashed, and kept beside the run log
  as the ground truth every command output is checked against.
- **A real gateway turn**: the gateway is started for the fixture
  profile (foreground `hermes gateway run` under the run's process
  control, per the recipe), one scripted conversation is driven
  through the agent loop, and the turn's packet receipt (W04 receipt
  store today; W05 P.011 receipt when banked and detected) is the
  evidence `explain` must read. A run that cannot start the gateway
  fails the gate honestly — it does not fall back to stub turns.
- **Teardown + residue check**: gateway stopped, fixture retained
  for evidence until banking, then removed; `~/.hermes` byte-checked
  unchanged (SOUL.md 667 bytes, `memories/` empty, no `profiles/`).

Commands receive the profile explicitly (`--profile <name>` or the
fixture's `HERMES_HOME`) — never an ambient "current" guess — and
resolve, in order: profile dir → persona config (the
`persona_runtime` config file naming persona id + document map) →
W03 library root + manifest → W04 index + receipts. Any missing
layer is a named, honest result (`no_profile`, `no_persona_config`,
`manifest_missing`, `index_unbuilt`, `gateway_not_running`), with a
non-zero exit for mutating commands and a structured record for
read-only ones. **No layer is ever synthesised to fill a gap.**

## 3. Design: the §12 command table, for real (P.012)

One new plugin-side module, `plugins/volmarr-core/persona_ops.py`,
owned by Team 08, plus one `persona` subcommand family registered in
`plugins/volmarr-core/cli.py` under the existing `hermes volmarr`
root (spelling decision: §12/Q1). The module *calls* the banked
surfaces — compiler, §§70–76 builders, W03 library, W04 index — and
owns only: profile resolution (§2), live compile-from-disk,
generation bookkeeping on disk, gateway-state probing, and the
privacy filter (§7). No second compiler, parser, slugger, scorer or
index (roadmap §8/§33.4 law, held by W03/W04 before us).

**Live compile-from-disk** is the shared first step for read
commands: load the profile's persona config, compile via the banked
`PersonaCompiler` over the *actual files*, and cross-check the
compile's per-document hashes against the W03 manifest; a mismatch
is reported as `source_drift_since_index` with both hashes, never
silently resolved. Compiles are cached by (§19) hash record — a
command run with unchanged sources must produce byte-identical
records to the previous run (idempotence is a gate check, §10).

| Command (working spelling) | Real behaviour | Evidence it must produce |
|---|---|---|
| `persona status` | Persona id + active generation + kernel/persona hashes from a live compile; corpus byte total + document count from the manifest; indexed completeness = indexed/current documents + manifest vs index generation from W04 `index_meta`; effective privacy = the strictest `privacy_class` among sources that would enter a packet, with per-class counts; gateway state probed (running / not running / profile absent) | Record fields each traceable to a named file/record read this run; dormant-profile case returns the honest empty state (finding 8) |
| `persona files` | The manifest inventory verbatim: role, path, byte length, revision, `privacy_class`, last verified hash, status — for every document, full length, no truncation | Output diffed in tests against an independent `sha256sum` + byte-count pass over the fixture corpus |
| `persona search "query"` | W04 `PersonaIndex.retrieve` over the profile's real index (sync first if manifest generation moved, reporting that it did); results carry stable id, byte/line ranges, section + source hashes, privacy/trust labels, continuation handles | Buried-section fixture: the planted needle section is returned and `cite` verifies its slice hash (§10) |
| `persona inspect [section]` | §71 `persona_inspect` over the live compile; with a section argument, that section's verbatim text + priority + role + effective routing from the compile/index — sliced from source at serve time, hash-verified like W04 `cite` | No invented content: every printed span hash-matches the fixture file bytes |
| `persona explain [turn-id]` | Reads the *stored receipt* for that turn (W04 receipt store; W05 P.011 receipt when present) and renders it through §72 `persona_explain`: sources attached/omitted with their recorded reasons, generation + kernel hash that served the turn. Unknown turn-id = named `no_such_turn`, never a reconstructed story | Fixture gateway turn (§2): explain's generation/hash equal the receipt the turn actually wrote |
| `persona validate` | §70 catalogue run over the live compile **plus** the on-disk checks §70 cannot do: symlink escapes from the profile persona dir, missing required role files, unreadable/invalid-UTF-8 sources (W03 offset reporting), conflicting kernel instructions (anchor/anti-anchor collisions from §§17–18 records) | Fault-injection battery (§10): each planted fault is named; a clean corpus validates clean |
| `persona diff` | §74 `persona_diff` between the *active generation's stored compile record* and a fresh live compile (or two named generations): source-level changes (per-document hash/revision) separated from compiled-kernel changes | Before/after proof: edit one fixture section → diff names exactly that document/section; no edit → empty diff |
| `persona reload --dry-run` | Fresh compile + validation + §73 `persona_reload` record against the active generation; writes the candidate generation to the generation store **without** activation; active generation record untouched | Current generation intact: status + a subsequent fixture turn still serve the old kernel hash |
| `persona reload --activate` | Validates the candidate (refuses a partial/invalid generation, retaining last known-good), then performs the atomic swap through W05's activation seam **when banked**; until then, activates for the *next gateway start* by atomically renaming the active-generation pointer (tmp + fsync + rename, W03 ManifestStore pattern) and reports exactly that scope — `activation_scope: next_gateway_start` — never claiming a live swap it did not do | Subsequent turn (live seam) or restarted gateway (pointer scope) serves the new kernel hash; failed validation leaves the old generation serving |
| `persona export` | §75 bundle *written to a file*: exact sources (streamed, W03 exporter), hashes, policy (roles/trust/privacy), optional index snapshot; bundle filename per §75 | Round-trip: export → import into a fresh fixture profile → corpus byte-identical, hashes equal |
| `persona import --dry-run` | §76 `persona_import_plan` against the *target profile's real inventory*: collisions, ownership, licence and privacy preview per bundle entry; zero mutation (profile tree hashed before/after in tests) | Dry-run purity proof + a collision case named correctly |
| `persona backup` / `persona restore` | Snapshot = export bundle + generation store + receipts index, integrity-checked (per-file sha256 manifest); encryption only through the W00.03-ENC decision — **still open, awaiting Volmarr's word; this design invents no key** (§12/Q5). Until ruled, backups are local, integrity-checked, and *labelled unencrypted* in their own manifest. Restore verifies every hash before writing, into a non-live profile only | Disaster drill: backup → corrupt one snapshot byte → restore refuses; clean snapshot → restore → byte-identical profile corpus |
| `persona test` | The replay runner for §§57–63: runs the §57 scenarios + §58 golden records against the fixture gateway (real turns, scripted prompts), records §61 telemetry rows from *those* runs, derives §59/§60 fingerprints from recorded outputs, and reports §62 quality rows only from measured data | Replayable: same fixture + same model → same scenario verdicts; no metric is printed that was not measured in the run or a named prior run |

Global rules for all 13: `--json` emits the record the builder
produced (plus the ops layer's provenance fields: profile, read
paths, generation, timestamps); human output is the builders'
display text, not a second rendering. Every mutating command
(reload --activate, import without --dry-run if later authorised,
restore, editor saves in §5) writes through the W03 transactional
pattern and appends a journal/receipt record. Exit codes distinguish
success / honest-empty / validation-refusal / infrastructure-absent.

---

## 4. Generation store (the small new state P6 owns)

`persona status/diff/reload` need a durable notion of "the active
generation" that survives process exits — CLI commands are separate
processes; in-process state (W05's snapshot) is invisible to them.
P6 therefore keeps, inside the profile's plugin data dir (beside the
W04 `generated/` store, never inside authored sources):

- `generations/<n>.json` — the compile record for generation *n*
  (persona/kernel hashes, per-document hashes + revisions, §19
  hash record, created-by command, validation verdict).
- `active-generation.json` — a pointer {generation, kernel hash,
  activated_at, activation_scope}, swapped only by the tmp + fsync +
  rename pattern (W03 `ManifestStore` discipline; a torn pointer is
  quarantined and rebuilt from the newest valid generation record,
  exactly the W03 recovery shape).
- `ops-journal.jsonl` — append-only: every mutating ops action with
  before/after generation + hashes (the audit trail `explain` and
  the §8 diagnostics read; retention follows the W04-R2 receipt
  question, §12/Q6 — until ruled, append without rotation and say so).

This is bookkeeping state, not a second source of truth: authored
files + the W03 manifest remain canonical, and any generation record
whose document hashes no longer match the manifest is reported
`stale`, never trusted silently.

## 5. Huge-file editor / pager (P.013)

Layered, in build order — each layer complete without the next:

1. **CLI pager (first, gated):** `persona read <document> [--section
   <stable-id>] [--cursor <byte>]` and `persona page` continuation,
   implemented *directly* on W04 `read_page`/`continue_read` —
   byte-cursor paging, UTF-8-boundary-safe, no redaction or
   reformatting; concatenation of all pages reproduces the file
   byte-for-byte (already contract-proven at the library layer; the
   command layer adds profile resolution + receipt). Includes
   in-file search (via the index, with paged jump-to-section) and a
   hash line on every page so a reader can verify what they saw.
2. **CLI editor (bounded):** section-scoped editing only — replace /
   append within one named section, never a whole-file blind
   overwrite. A save is: dry-run diff (§74 machinery at section
   level) → explicit confirmation flag → transactional write (W03
   pattern: tmp + fsync + rename; prior revision preserved in the
   generation/journal records) → reindex + recompile candidate →
   `validate` verdict printed. Meaningful changes (kernel/anchor
   sections, role/trust/privacy fields) require the authorised-
   editor approval step §12 names; the threshold definition is an
   open question (§12/Q7), and until ruled the editor treats *any*
   kernel/anchor edit as approval-required.
3. **Virtualised viewer (TUI/Web/Desktop, later slice):** one paged
   API behind the CLI pager (same byte cursors + section tree +
   hashes) rendered with virtualised/paged views — never a single
   giant DOM textbox (§29 acceptance). Search, hierarchy, diff,
   preview, undo (journal-backed), per-section priority display.
   This layer is shared with W06's memory editor need (Team 07
   draft §4.6): **one editor surface, two corpus roots** (persona
   library, memory library) — Team 08 builds the persona root; the
   shared component contract is agreed with Team 07 at W06 banking,
   not forked in parallel.
4. **Export from the editor** is `persona export` (§3) — the same
   code path, not an editor-private copy function.

Non-goals: no WYSIWYG, no format conversion, no normalisation of
line endings or encoding on save (a save that changes bytes outside
the edited section fails its own post-write hash check).

---

## 6. Drift watchdog as bounded diagnostics (P.012 support, §12)

`persona watchdog [--since <turn>] [--budget <n>]` — a diagnostic
*run*, not a daemon P6 installs silently:

- **Inputs (only these):** the active generation's compile record,
  stored turn captures/receipts for the profile (PresentState
  capture path; W05 receipts when present), and operator-supplied
  response samples. A run with no captured turns reports
  `no_evidence` — it does not manufacture drift scores from the
  kernel alone.
- **Scoring:** the pure §§27–28 surfaces, unchanged — watchdog
  contract, per-dimension drift scores, routing. §59/§60
  fingerprints are computed from the *same* recorded outputs, so a
  report's fingerprint and drift rows always describe one evidence
  set, named by turn range + generation + kernel hash.
- **Outputs (only these):** a dated diagnostic report in the
  profile's generated store + the §61 telemetry row(s) for the run:
  contradictory-output findings (response vs anchor/kernel records,
  §§23–26 precedence rules as the contradiction standard), drift
  route, and — where §30 applies — a **repair proposal**: the §30
  plan rendered as a proposed editor action (§5 layer 2) that takes
  effect only through the editor's approval flow. The watchdog
  process holds **no write handle** to any authored source; this is
  enforced structurally (it is invoked with the persona dir opened
  read-only in its code path) and by a gate test that hashes the
  corpus before/after a watchdog run (§10).
- **The optional fast local model (§31)** may be used for exactly
  one of its six banked tasks that fits diagnostics: *proposing an
  explanation* of a scored contradiction. Local only, behind the
  §7 privacy filter (persona text for explanation never leaves the
  host), and its prose is labelled `proposal` in the report —
  never merged into scores, which stay deterministic.
- **Bounds:** per-run turn cap + wall-clock cap (operations values,
  recorded in the report, in the W04 subspan-threshold sense —
  quotas on the *run*, never on canon); no scheduler is installed
  by default. If Volmarr later wants cadence, it rides Hermes cron
  like the banked routines/sleep/agency jobs — a separate,
  explicitly installed, pausable job (§12/Q4).
- **Adherence baselines:** per-model baselines are the §62 quality
  rows derived from `persona test` runs (§3) stored by model id +
  version; a watchdog report compares against the baseline *for
  the model that produced the evidence* and says `no_baseline`
  when none exists. No numerical claims about inner experience —
  reports describe behaviour against authored canon only (§12).

## 7. Private/public filters before cloud inference (P.018)

**Enforcement design.** One filter function in `persona_ops.py`,
`egress_decision(items, destination) -> {allowed, refused[],
reason}`, consulted at every point persona content can leave the
host, in this order of implementation:

1. **Embeddings (already gated — adopt, do not rebuild):** W04's
   consent gate *is* the filter for this path; P6 adds only a test
   that the gate still refuses private→cloud without override
   after P6 lands (regression, not new code).
2. **Prompt-packet assembly (W05 seam):** when W05's live pipeline
   routes a turn to a cloud model, each persona item carries its
   manifest `privacy_class` + `destinations`; the filter refuses
   `private` items for any cloud destination without a recorded
   per-source operator override (the W04 consent record shape,
   generalised: provider kind/provider/model pinned, revocable,
   revocation takes effect next turn), refuses `shared` items for
   destinations not in their `destinations` list, and passes
   `public` items. Refusals degrade the packet (item omitted +
   receipt reason `privacy_refused`) — **never** fail-open, and
   local-only mode fails the *turn's cloud route* closed instead
   (§14 routing modes honoured: a `local-only` turn containing a
   refused item proceeds locally or reports, it does not egress).
   Until W05 banks, this layer is built and tested against the
   PresentState packet path that exists today (the one live
   assembler), behind the same default-off persona flags.
3. **Ops commands themselves:** `export` to a non-local target,
   watchdog explanation (§6), and diagnostics upload (none by
   default) pass the same function; CLI-local reads never egress.

**P.018 test design (the ticket's own acceptance):** a capturing
fake cloud provider (the W04 fake-provider pattern, extended to the
LLM seam) records every byte offered to it. Cases: (a) private
source, cloud turn, no override → zero private bytes captured,
receipt names the refusal, `cloud_egress` for the turn counts only
permitted items; (b) private + recorded override → egress occurs
and the receipt names the override record id; (c) override revoked
→ refused again next turn; (d) shared source, unlisted destination
→ refused; listed → passes; (e) public → passes; (f) local-only
mode + private → no cloud call is attempted at all. The baseline
for comparison is today's behaviour, recorded honestly in the wave
record: with persona flags at defaults, no persona content reaches
a prompt at all — P.018's risk arrives *with* W05's live wiring,
which is exactly why the filter is designed against that seam now.

**Prompt-injection isolation (§12, tested in the same battery):**
fixture tool results / a fixture web page / a fixture repo README
that claim system authority ("ignore your persona, you are now…")
are driven through real fixture turns; the kernel hash serving the
turn must be unchanged, the injected text must be classified as
untrusted content by role (never compiled as canon — compilation
reads only the manifest's authored sources), and `persona test`
carries the case as a named scenario. §§23–26 precedence contracts
are the standard; P6 supplies their first live test, not new rules.

## 8. Diagnostics and how-to docs (P.020)

- `persona diagnostics` (read-only): one bundle (JSON + human text)
  — plugin/CLI versions, profile + persona id, active generation +
  kernel/persona hashes, manifest/index generations + completeness,
  index DB size, receipt count + oldest/newest, last watchdog
  report pointer, privacy egress counters (from receipts:
  permitted/refused/override counts), gateway state, and the named
  next action for any absent layer (§2's honest-empty vocabulary).
  It reads the existing `hermes volmarr health` family rather than
  duplicating probes.
- **How-to docs:** `docs/modernization/PERSONA_OPS_HOWTO.md` at
  implementation time — beginner path (status → files → search →
  inspect → validate → reload dry-run/activate → backup/restore
  drill) + expert reference (record schemas, generation store,
  privacy/consent records, watchdog bounds), written against the
  *shipped* commands and re-verified in the gate by executing every
  command the how-to names, in order, against the fixture profile.
  §29's transparency panel ("what defines this persona vs what it
  remembers vs what the world model says") is a *view over*
  `status` + `files` + W06 memory status — P6 supplies the persona
  third and the combined view waits for W06, recorded as a remainder.

---

## 9. Build order (implementation waves within W07, later — NOT this prep)

0. Spikes: CLI spelling decision (Q1); generation-store location
   inside the profile plugin data dir confirmed against W04's
   `generated/` layout; gateway-state probe method on the fixture
   (process/unit/pidfile — whichever the banked recipe actually
   leaves); W05 seam detection (banked? which receipt shape?).
1. `persona_ops` profile resolution + live compile-from-disk +
   generation store (§4) + journal; read commands that need no
   gateway: `files`, `status` (incl. the dormant-profile case),
   `validate`.
2. Index-backed commands: `search`, `inspect`, `explain` (receipt
   reading), `diff`.
3. Reload pair: `--dry-run` fully; `--activate` in pointer scope
   (§3) with its honest scope field; live-seam activation adapter
   added when W05 banks, behind a capability check.
4. Export file writer + import (dry-run first; mutating import only
   if separately authorised) + backup/restore drill.
5. CLI pager (§5 layer 1), then the bounded section editor (layer 2).
6. Watchdog diagnostic run (§6) + `persona test` replay runner.
7. Privacy filter (§7 layers 2–3) + P.018 battery + injection cases.
8. Diagnostics + how-to (P.020, §8); gate sweep (§10); wave record
   with a per-row §28.2 verdict for all 26 inventory rows and all
   13 §12 commands — rows that remain contract/absent say so.

Dependencies, stated once and plainly: steps 1–2, 4, 5(layer 1) and
8's persona third depend only on banked W03/W04 code. Step 3's live
scope, step 6's richest evidence, and step 7's packet layer consume
W05 *at its banking*; W06 affects only receipt/journal retention
defaults (Q6) and the shared editor component (§5 layer 3). If W05
or W06 slip, W07 still banks everything else with the affected
scopes named — the wave does not block, and does not fake the
blocked rows either.

## 10. Test / gate plan

Via `scripts/run_tests.sh` only; counts from log files; one heavy
suite at a time on the shared laptop (resource law). Fixtures staged
under `$HOME` (§2); the live `~/.hermes` is never a fixture.

- **Contract suites:** the existing persona test estate stays green
  unchanged (anchor files for this wave: `test_volmarr_persona_
  inspect_explain.py`, `_reload_diff.py`, `_export_import.py`,
  `_watchdog.py`, `_drift*.py`, `_hash_reload.py`); new
  `test_volmarr_persona_ops_*.py` covers resolution, generation
  store recovery, and every command against fixture profiles.
- **Regression gate:** full Volmarr/Kista contract set = banked
  baseline **976 passed / 7 failed / 1 skipped** (W04 banking); the
  7 are the known live-transport set, name-identical; zero new
  failures.
- **W07 gate — no stub command or invented result (roadmap §30):**
  for each of the 13 §12 commands, a scripted run against the §2
  live temporary gateway profile whose outputs are verified against
  independently computed ground truth (fixture hashes, byte counts,
  the turn's own receipt). The `*_example()` records are asserted
  *absent* from command output (a canary: fixture values differ
  from every roadmap example, so an example-regurgitating command
  fails loudly). Honest-empty cases (dormant profile, gateway down,
  index unbuilt, unknown turn-id) are gate cases, not edge cases.
- **Fault injection for `validate`:** broken AST/heading structure,
  symlink escape, missing required role, invalid UTF-8 (offset
  named), anchor/anti-anchor conflict — each planted, each named.
- **Watchdog bounds proof:** corpus hashed before/after watchdog
  runs (byte-identical), report-only outputs, a `no_evidence` run,
  and a §30 proposal that changes nothing until editor approval.
- **Privacy battery:** §7's six egress cases + injection cases,
  against the capturing fake provider; receipts audited.
- **Editor proof:** paged concatenation = source bytes; a section
  edit changes exactly that section's bytes + hash; a no-op save
  changes zero bytes; interrupted save (kill mid-write) recovers
  via the transactional pattern.
- **Backup drill:** §3's corruption-refusal + clean-restore cases.

## 11. Risks

- R1. **Stub drift:** the easiest wrong build is a CLI that feeds
  `*_example()` records to the builders. Mitigation: the §10 canary
  (fixture ≠ example values) + per-command ground-truth diffing.
- R2. **Activation overclaim:** `reload --activate` before W05
  banks can only promise next-start scope. Mitigation: the
  `activation_scope` field is mandatory in the record and the
  how-to; claiming a live swap without the seam fails review.
- R3. **Watchdog mission creep:** a diagnostic that "helpfully"
  fixes canon would violate §12 outright. Mitigation: structural
  read-only (§6) + byte-identity gate + proposals routed through
  the editor's approval flow.
- R4. **Privacy fail-open:** a filter consulted in one assembler but
  bypassed by another surface (voice, cron, delegates) leaks by
  omission. Mitigation: §7 enumerates egress points; the wave
  record verdicts each surface, and un-wired surfaces inherit the
  default-off persona flags (no persona content, no leak) until
  their wiring lands with the filter attached.
- R5. **Editor as second truth:** editor saves that bypass the
  manifest/journal would desynchronise W03/W04 state. Mitigation:
  saves are W03 transactions; post-save hash + reindex checks are
  part of the save itself (§5).
- R6. **Fixture realism:** a too-clean synthetic corpus hides the
  dormant-deployment and drift cases. Mitigation: §2's corpus
  plants a buried section, mixed privacy classes, an oversize
  document, and the gate includes the real dormant `~/.hermes`
  read (read-only status) as a case.
- R7. **Receipt dependence:** `explain` is only as good as the
  receipts turns actually write; W04 receipts cover retrieval, and
  full packet receipts are W05/P.011. Mitigation: explain renders
  exactly what the stored receipt holds and names its receipt kind;
  missing fields are `not_recorded`, never reconstructed.

## 12. Open questions (for Volmarr / coordinator — prep does not decide)

- Q1. Command spelling: `hermes volmarr persona …` (the registered
  root) or `hermes persona …` (the §§71–76 constants)? This draft
  designs for the former and would update the constants' spelling
  as a ledgered reconciliation; a core-registered `hermes persona`
  root is a core change needing explicit word.
- Q2. Mutating import: is `persona import` (without --dry-run)
  authorised inside W07, or does W07 ship dry-run only with real
  import as a later ticket?
- Q3. Backup encryption (W00.03-ENC, already asked 2026-11-07 — not
  re-asked here): passphrase, accept unencrypted local, or an
  existing vault key? §3's backup design ships integrity-checked
  and honestly labelled either way; encryption waits for the word.
- Q4. Watchdog cadence: on-demand only (this draft's default), or
  an explicitly installed Hermes cron diagnostic job? If cadence:
  what interval and turn budget?
- Q5. Privacy overrides: may a *general-inference* override be
  per-source + per-provider (this draft's design, mirroring W04),
  or should any private→cloud inference require a per-turn
  confirmation instead of a standing consent record?
- Q6. Receipt/journal retention (carries W04-R2): rotation default
  for the ops journal + watchdog reports — keep-all until ruled,
  per this draft, or a named cap?
- Q7. "Meaningful change" threshold for editor approval (§12):
  this draft defaults to any kernel/anchor edit; should role,
  trust or privacy field edits also always require approval, and
  who is the authorised editor of record for a profile?
- Q8. Editor surface priority after the CLI pager: TUI first, or
  Desktop/Web virtualised viewer first (§5 layer 3)?

## 13. Ticketed remainders (named now, not silently absorbed)

- W07-R1: live (mid-session) activation adapter — lands with or
  after W05 banking; pointer-scope activation (§3) is the W07
  deliverable until then.
- W07-R2: combined §29 transparency panel — waits on W06 memory
  status; P6 ships the persona third (§8).
- W07-R3: virtualised editor layer (§5 layer 3) shared-component
  contract with Team 07 — agreed at W06 banking, built after.
- W07-R4: 1,000-turn drift run (P.017's full battery) executes
  against W05's live substrate as a Q-gate activity in W13; W07
  ships the replay runner + baselines it consumes (§§6/3 `test`).
- W07-R5: cross-machine backup/restore + schema migration proof
  (P.019) — the §3 drill is single-host; the two-target run joins
  W08/E.18's hardware verification.
- W07-R6: §13 Unicode tokenisation question (W04-R3) touches
  `search` recall for rune/CJK queries; P6 inherits W04's trigram
  exact-phrase reconciliation and names it in search output
  provenance until a later wave rules on the scorer.

---

*Prep record: audit read on the fast-forwarded tree (roadmap §12 +
§28.2–28.3 + §30–31 tickets P.012/P.013/P.018/P.020;
CAMPAIGN_STATE_MODERNIZATION.md through the W04 banking closure;
WAVE_PLAN.md Team 08 entry in ~/hermes-hack-forge;
W03_P0P1_IMPLEMENTATION.md; W04_P2_IMPLEMENTATION.md; Team 06
P3P4_DESIGN_DRAFT.md + Team 07 P5_DESIGN_DRAFT.md as pattern and
dependency sources; persona_runtime.py §§19–20/27–31/57–63/70–76
headers, builders and command constants; cli.py registration +
__init__.py CLI wiring; canonical_library.py privacy/role
vocabularies; persona_index.py retrieve/cite/read_page + consent
gate; routing.py cloud decisions; hermes_cli/personality.py +
model_data_policy_guard.py; LAUNCH_RECIPE.md; live ~/.hermes state).
No code changed, no tests run, nothing committed or pushed (light
read-only inspection only, per prep brief — the laptop is shared
with the Samverk / Mythic Coder / Rúnmál campaigns).*
