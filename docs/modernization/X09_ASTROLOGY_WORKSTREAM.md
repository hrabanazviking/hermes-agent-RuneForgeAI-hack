# X.09 Astrology Engine — ecosystem workstream 9 of 15 (Team 01, 2026-11-14)

Roadmap section 44 executed: the Astrology Engine adapter is
upgraded from the E.09 narrow surface to the richer VERIFIED
capability catalog, plugin-side only. Slice discipline:
`volmarr-astrology` 0.7.0 -> 0.8.0 (its own plugin, no core
edits, no engine source copied), a new `astrology` module +
`hermes volmarr astrology {status|catalog|batch}` CLI family in
volmarr-core following the X.05–X.08 pattern, registry updated
in place (INTEGRATION_MATRIX row 12 + the integration-lock.json
Astrology entry; field-diff asserted — only that entry changed,
only its adapter plugin string and verdict), exactly one
CUSTOMIZATIONS.md ledger row, README.md byte-identical (sha256
336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3,
verified before and after). Commit-only on
`yrsa/hermes-team-01`; the keeper banks serially.

## Audit (re-measured, not inherited)

- Source: `hrabanazviking/astrology-engine`, HEAD re-measured
  by `git ls-remote` 2026-11-14:
  `bb4ede4fbb326d21df34a5ca0ca6e343f4f49fbe` — IDENTICAL to the
  E.09 pin. No pin move is taken or needed; the staged tree
  `~/astrology-e09` sits at the same HEAD. Package version
  4.0.0 in `pyproject.toml` at the pin.
- License text-verified at the audited HEAD: `LICENSE` is the
  full Apache-2.0 text, sha256
  `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`
  — identical to the E.09 verification. COMPONENT_LICENSES.md
  therefore unchanged (license and pin facts did not change).
- README claim vs measurement: the roadmap recorded the README
  describing **47 CLI subcommands**. Measured at the pin: the
  engine's own `--help` lists **57 subcommands**; its
  `capabilities` document (schema_version 1.0) names **28
  capability ids**; its `tools` document names **26 agent
  tools** with JSON input schemas (one shared `ChartRequest`
  family: date/time/latitude/longitude/timezone, ayanamsa and
  house-system enums, ephemeris_path). The README number is
  stale in the conservative direction; this record follows the
  engine's own outputs.
- Engine surface facts the build rests on (all probed live at
  the pin against `~/astrology-e09` in `.venv-e09-live`):
  - The structured family (`vedic`, `vargas`, `dashas`,
    `panchanga`, `location`) REQUIRES an explicit IANA
    `--timezone` and returns structured JSON carrying its own
    provenance block (requested vs actual backend per body,
    Swiss Ephemeris version, rule_version) — including the
    honest warning "Swiss data files unavailable for some
    bodies; actual backend is Moshier" in this environment
    (E09-T3: `seas_18.se1` absent in a plain install).
  - The legacy family (`natal`, `transit`, `predict`,
    `synastry`, `geoastrology`, `hellenistic`, `dignity`,
    `forecast`, `solar-return`) accepts an optional explicit
    `--timezone` (synastry: `--timezone1`/`--timezone2`);
    `planet-hours` and `lunar` accept none.
  - Output sizes at the reference chart (2000-01-01 12:00,
    Stockholm): vedic 9,422 B, vargas 35,552 B, dashas
    33,751 B, panchanga 10,313 B, location 14,335 B,
    hellenistic 4,215 B, dignity 3,152 B, runic --json
    3,843 B — all inside the adapter's existing 64 KiB bound.
  - `runic --json` separates `computation` from interpretation
    and labels its source "Pennick (2023), a modern synthesis";
    the interpretive layer is behind `--reading`, which the
    adapter never passes.
- Engine's own suite at the pin, re-run this slice staged the
  E.09 way (the tree bound at the author's hardcoded
  `/home/hatch/workspace/astrology-engine` path inside a
  bubblewrap sandbox; log `~/team01-x09-engine-suite.log`):
  **634 passed / 0 failed** — identical to the E.09 staged
  result. Unstaged, the suite still cannot collect
  `test_runic_reading.py` / `test_runic_tides.py` (module-level
  open of the hardcoded path) — E09-T1, unchanged.

## Registry (section 35 duty)

- `integration-lock.json`: Astrology Engine entry updated in
  place — adapter plugin `volmarr-astrology 0.7.0` -> `0.8.0`,
  verdict gains the X.09 execution note. Field-diff asserted
  against the banked tree: ONLY the Astrology entry changed,
  only those two fields; the JSON round-trips; engine count
  unchanged at 30, no other entry or top-level key touched.
  Pin, license and verification status unchanged.
- `INTEGRATION_MATRIX.md`: row 12 updated in place (one line:
  adapter 0.8.0 + the X.09 surface summary + verdict). No other
  row changed.
- `COMPONENT_LICENSES.md`: unchanged — pin and license facts
  did not change (see Audit).
- Version assertions updated where the version genuinely
  moved: the capability-bus seed descriptor for
  volmarr-astrology (`plugins/volmarr-core/capability_bus.py`,
  0.7.0 -> 0.8.0) and its contract in
  `test_volmarr_capability_bus.py`. The `0.7.0` literal in
  `test_volmarr_production.py` is a synthetic fixture input,
  not a version assertion, and is deliberately untouched.

## Build (plugin-side only — section 44 items 1–10)

`plugins/volmarr-astrology/tools.py` (0.8.0):

- Retained, hardened (items 2, 4): the seven deterministic
  tools keep their fixed-argv bounded subprocess shape and —
  when no timezone is supplied — their EXACT legacy result
  shapes (the pre-X.09 contracts pass unmodified). New on the
  retained tools: an optional explicit `timezone` (natal,
  transit, predict, astrocartography; `timezone_a`/`timezone_b`
  on synastry) that is validated as an IANA name, forwarded as
  the engine's `--timezone`, echoed in the result only when
  supplied, and — when a local time accompanies it — checked
  against the zone's DST rules with stdlib zoneinfo: a fold
  (ambiguous) or gap (nonexistent) local time is REJECTED
  before the engine runs. No silent guessed geocodes anywhere:
  coordinates were already mandatory and remain so.
- E09-T2 DISCHARGED (item 4): `predict` and
  `astrology_astrocartography` now REQUIRE a known birth time
  (schema + handler), matching the engine's contract at the
  pin; an omitted time returns an explicit error naming the
  requirement instead of the engine's rc=2 failure. Unknown
  birth time elsewhere stays explicit: natal/transit/synastry
  report `time_known: False`, and the structured family
  requires a time outright.
- Added, engine-verified (items 2, 3): `astrology_vedic`,
  `astrology_vargas`, `astrology_dashas`,
  `astrology_panchanga` (the structured Jyotisha family;
  optional validated `ayanamsa`), `astrology_relocation`
  (the structured `location` command: fixed-instant relocation
  lines for an explicit query pair), `astrology_hellenistic`
  (sect/bonification/joys) and `astrology_dignity` (essential
  dignities with scoring) as report tools, and
  `astrology_runic` (runic cycle layers, computation only).
  Every new result carries the provenance envelope: engine
  repo, pin, package version, the ephemeris provenance string
  (pyswisseph 2.10.3.2; Moshier fallback named), timezone,
  time_precision, cache key and cache_hit — calculation only,
  `interpretation_included: False` (item 5: nothing in the
  adapter invents or substitutes a position; the engine's own
  report is carried verbatim).
- Discovery (item 6): `astrology_capabilities` runs the
  engine's `capabilities` + `tools` commands and intersects
  them with the pinned 28-id allowlist measured at the E.09
  pin; anything the engine reports off-allowlist is never
  surfaced as a capability or a tool. Backwards compatibility:
  the seven E.09 tools work unchanged against the pinned
  engine, and discovery degrades to the truthful configuration
  error when no engine is configured.
- Cache + privacy (item 7): new-family and discovery calls go
  through a cache keyed on sha256(engine pin + exact argv),
  bounded at 128 entries, held ONLY in process memory — a hit
  replays the stored report byte-for-byte and does not re-run
  the engine. Chart contents are never logged, persisted, or
  transmitted; the child environment stays scrubbed (the
  pre-X.09 containment contracts still pass), and identity /
  city fields are refused by every schema.
- Batch (item 8): `plugins/volmarr-core/astrology.py`
  `build_batch_plan` — a pure deterministic plan for
  time-series/location comparisons: per-item validation with
  refusals by name (`unknown_calculation`, `invalid_date`,
  `unknown_birth_time`, `local_time_fold`, `local_time_gap`,
  `batch_item_cap`), the same cache keys the plugin uses,
  latency caps (item cap also bounded by total budget /
  per-item timeout: 15 items at the 32/20 s/300 s defaults),
  a cancellation checkpoint per item, and a replay key
  (sha256 over the canonical plan) — same items, same plan,
  same key. The plan runs no engine.
- Offline recipe (item 9): recorded in the catalog
  (`OFFLINE_RECIPE`): clone at the pin, venv +
  `pip install -e .[geo]` (the geo extra is a deployment
  requirement — E09-T1), plugin engine_path/python_path
  configuration, and the ephemeris data provenance/licensing
  note (Swiss Ephemeris 2.10.03 via pyswisseph; .se1 files
  optional, Moshier fallback honest per body).
- Structured cross-app results (item 10): NOT built — the
  catalog/status records are the permission seam; no Rúnmál,
  Samtal or Hliðskjálf surface receives chart data in this
  slice (ticket X09-T5).

## Live caller (section 28.2)

`hermes volmarr astrology {status|catalog|batch}` plus the
plugin's 16 live tools — proven in disposable HERMES_HOME homes
(log `~/team01-x09-liveproof.log`):

- Unconfigured home: status truthful (`enabled: false`,
  `configured: false`, tree `not_configured`,
  `production_ready: false`); catalog lists the 16 exposed
  tools with the measured engine surface (57 / 28 / 26) and
  the not-exposed families with reasons; batch plans the
  labelled synthetic set (2 planned, 1 refused
  `unknown_birth_time` — the synthetic predict item carries no
  time by design); bare verb rc 2.
- Configured home (`astrology_enabled: true`,
  `astrology_root: ~/astrology-e09`): status measures the REAL
  staged tree — `head_matches_pin: true`, LICENSE sha256
  matches the audited text, `package_version: 4.0.0` read from
  the tree's own pyproject.
- Plugin harness against the real engine
  (`~/astrology-e09/astrology_engine.py`, `.venv-e09-live`
  interpreter), two cold processes: 16 tools registered;
  vedic, natal (with explicit timezone), runic and
  hellenistic all succeed; discovery returns the full measured
  catalog (28 capabilities, 26 engine tools). Determinism:
  report sha256s byte-identical across the two processes
  (vedic `87770160529d...`, natal `d5819ccd7f02...` — the
  natal hash is IDENTICAL to E.09's live natal proof hash at
  the same inputs, cross-verifying both slices — runic
  `ee77f78627ad...`). The vedic report's own provenance names
  the Moshier backend honestly in this environment.
- Failure truthfulness in the same harness: a DST-fold natal
  (2026-11-01 01:30 America/New_York) returns the explicit
  ambiguous-time error and never reaches the engine; predict
  without a birth time returns the explicit E09-T2 error;
  with `engine_path` pointed at a nonexistent checkout, a
  vedic dispatch returns the truthful configuration error.
- Environment note (recorded, not hidden): the first harness
  attempt ran its disposable homes under /tmp and died — pm
  installs ~2.1 GB of tools per HERMES_HOME and /tmp (a 20 GB
  tmpfs, already near-full from other campaigns) hit ENOSPC,
  and a stray `/tmp/inspect.py` from another campaign's work
  shadows the stdlib `inspect` module for scripts launched
  from /tmp. The proof was rerun with homes and harness on
  disk; the stray file is not this campaign's and was left
  untouched.

## Tests and gate

- New contracts: `tests/plugins/test_volmarr_astrology_x09.py`
  (14 tests) pinning the section 44 gates — structured argv +
  provenance envelope, the structured/legacy family smoke set,
  cache replay byte-identical with the engine run exactly
  once, DST fold AND gap rejected before the engine, unknown
  birth time explicit (predict / astrocartography / vedic),
  invalid IANA zone refused, identity/city fields refused
  (private-data containment), timezone forwarding with the
  legacy result shape preserved when it is absent, runic argv
  + fold rejection, allowlist-bounded discovery (an unvetted
  engine-reported id is never surfaced), local-time
  classification, batch determinism/caps/refusals-by-name,
  truthful chart-free status, catalog-vs-README measurement,
  and the CLI family. The pre-existing
  `test_volmarr_astrology.py` discovery assertion gains the
  nine new tool names; its other contracts are unmodified and
  pass — the retained tools' legacy shapes are intact.
- Targeted (log `~/team01-x09-targeted.log`): 4 files
  (astrology + astrology_x09 + integration_ledger +
  capability_bus) = **67 passed / 0 failed** — the X.08-era
  astrology+ledger+bus baseline (53) + 14 new.
- Full contract gate (log `~/team01-x09-fullcontracts.log`):
  serialized behind the Samverk campaign's unittest suite by
  the established waiter pattern (final waiter PID 2209645,
  log `~/team01-x09-waiter.log`; an earlier waiter first
  launched the whole-repo suite and was replaced within the
  slice — the plugins contract set is the precedent scope).
  In the X.08-canonical scope (test_volmarr_*.py + the two
  kista files): **146 files = 1,275 passed / 7 failed /
  1 skipped** — the X.08 baseline (145 files = 1,261 / 7 / 1)
  plus exactly the 14 new X.09 contracts, the 7 failures
  name-identical to the known live-transport set (5x
  test_volmarr_core_plugin.py, 1x
  test_volmarr_verdandi_stimuli.py, 1x
  test_volmarr_voice_runner.py), ZERO regressions (volmarr-only
  detail log `~/team01-x09-volmarr-gate.log`: 144 files,
  1,250 / 7 / 0; kista pair re-run on this tree: 25 / 0 / 1).
  The broader tests/plugins/ sweep in the same log (303
  files = 3,315 passed / 7 failed / 5 skipped) shows the same
  7 failures and no others.

## Honest remainders / tickets

- X09-T1 (engine line, = E09-T1 continued): the engine suite's
  hardcoded `/home/hatch/workspace/astrology-engine` paths
  still make two test files uncollectable on any other machine
  unstaged; the engine also still fails closed without the
  geo extra. Both are engine-repo fixes, not adapter defects.
- X09-T2 (scope decision, recorded): the engine's interpretive
  and divination modes (reading, dossier, forecast's symbolic
  keys, tarot, lenormand, cartomancy, numerology, iching,
  runecast, ogham, mantras) are NOT exposed — section 44.5
  keeps calculation separate from interpretation. Exposing any
  of them is a future, separately decided slice.
- X09-T3 (privacy design): the engine's chart library
  (charts/chart/chart-show/chart-delete, `--save`/`--load`)
  is NOT used — it persists personal chart data to disk. The
  adapter keeps chart data in process memory only; a
  persistence design with profile-data protections is future
  work if ever wanted.
- X09-T4 (incremental surface): verified-but-unadapted engine
  families — solar-return, progressions, composite, synergy,
  antiscia, lots, aspect-grid, yogas, shadbala, ashtakavarga,
  jaimini, draconic, asteroids, midpoints, stars, elect,
  watch, profection, solar-arc, wheel, western, relationship,
  bazi/chinese/tibetan — each is a small fixed-argv addition
  on this slice's builders when wanted. Eclipse/ingress root
  finding is already covered by the retained `predict` tool's
  engine output; no separate adapter exists.
- X09-T5 (section 44 item 10): structured results for Rúnmál,
  Samtal and Hliðskjálf are not wired; they wait on explicit
  per-app data permissions that do not exist yet.
- E09-T3 stands: asteroid ephemeris `seas_18.se1` is absent
  in a plain install, so optional bodies are omitted with the
  engine's own warning while core calculations succeed.
- The section 32 release scorecard still reads NOT
  releasable (0 met / 10 unmet / 5 deferred);
  `production_ready` stays False in every X.09 record.
