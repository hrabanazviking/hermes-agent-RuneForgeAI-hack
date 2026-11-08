# W07 Implementation Record — Phase P6: Persona Operations and Character-Drift Assurance

Team 08 (W07), 2026-11-08. Tickets **P.012, P.013, P.018,
P.020** per `docs/modernization/P6_DESIGN_DRAFT.md` (committed
on this branch before implementation, `5c85df2a25`). Built on
the banked W06 tree (`d3010f7672`; contracts baseline 128 files
= **1,029 passed / 7 failed / 1 skipped**, the 7 the known
live-transport set). All personal code is plugin-side in
`plugins/volmarr-core/`; no Hermes core file is touched and
README.md is untouched (sha256 verified before and after:
`336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`,
identical to banked main).

Continuation note: the first implementation pass was
interrupted (cron timeout) with the code written but untested.
This record covers the finished slice: the inherited code was
reviewed line-by-line against the design draft, completed
(the CLI editor verb, the P.020 how-to), fixed where broken
(the section 75 bundle bug below), and only then tested and
graded. Nothing untested is claimed here.

Roadmap section 28.2 law held: a surface is declared live only
where this wave gave it a real caller on a real path, against
real fixture profiles whose outputs are checked against
independently computed ground truth. What is not complete is
named under Remainders, never declared complete.

## What was built (design draft build order 1–8)

- **Ops core + generation store (steps 1–2).** New module
  `plugins/volmarr-core/persona_ops.py` (1,382 lines):
  `PersonaOps` (profile resolution with the draft section 2
  honest-empty vocabulary — `no_profile`, `no_persona_config`,
  `manifest_missing`, `index_unbuilt`, `gateway_not_running`,
  `no_such_turn`, `no_evidence`; live compile-from-disk via the
  banked section 6 compiler with manifest cross-checks reported
  as `source_drift_since_index`, never silently resolved;
  gateway state probed from the profile pidfile) and
  `GenerationStore` (draft section 4: `generations/<n>.json`,
  the `active-generation.json` pointer swapped only tmp + fsync
  + rename, a torn pointer quarantined and rebuilt from the
  newest valid generation record, and the append-only
  `ops-journal.jsonl`). The module calls the banked surfaces —
  sections 70–76 builders, the W03 canonical library, the W04
  index, the W05 live seam, the W06 memory doors — and builds
  no second compiler, parser, slugger, scorer or index.
- **The section 12 command table (steps 2–4), all 13 rows
  live.** `status` (every field traced to a read this run;
  the dormant-profile case returns the honest empty state),
  `files` (manifest inventory with per-row live hash
  verification), `search` (W04 retrieval; syncs first when the
  index moved and says so), `inspect` (section 71 over the
  live compile; a named section is sliced from source and
  hash-verified like W04 `cite`), `explain` (reads the stored
  receipt — W04 index receipts or W05 persona-live receipts —
  and renders it through section 72; unknown id is
  `no_such_turn`, unrecorded fields are `not_recorded`),
  `validate` (section 70 catalogue plus the on-disk checks:
  anchor/anti-anchor collisions, symlink escapes, missing
  required roles, invalid UTF-8 with the byte offset),
  `diff` (section 74, active generation vs fresh compile),
  `reload --dry-run` (candidate generation written, active
  generation untouched), `reload --activate` (invalid
  candidates refused with last known-good retained; the record
  names its scope exactly — `live_next_turn` only when a W05
  `PersonaLiveState` was supplied and its refresh published the
  new kernel hash, otherwise `next_gateway_start`),
  `export` (the section 75 bundle actually written to a file:
  record + every source verbatim, hash-checked at write),
  `import` (**dry-run only** — the section 76 plan against the
  target profile's real inventory plus per-source collision
  previews; zero mutation; mutating import awaits ruling Q2),
  `backup`/`restore` (export bundle + generation store +
  receipts index under a per-file sha256 manifest; restore
  verifies every hash before writing anything and refuses a
  live target; labelled `unencrypted-local` — W00.03-ENC is
  still open and no key is invented), and `test` (the measured
  scenario battery: validate, pager integrity, citation
  verification, search provenance, the cloud privacy filter
  over the profile's own manifest rows, prompt-injection
  isolation — an unmanifested file claiming authority is never
  compiled; every verdict measured in the run).
- **CLI surface.** `hermes volmarr persona ...` in
  `plugins/volmarr-core/cli.py` (+114 lines): 18 verbs — the 13
  table commands plus `read`/`page` (the P.013 pager),
  `edit` (the bounded editor), `watchdog` and `diagnostics`.
  Command spelling is draft Q1's default (the registered
  `hermes volmarr` root); the sections 71–76 constants keep
  their roadmap spelling as record metadata only. Q1 remains
  Volmarr's to overrule.
- **Pager + bounded editor (P.013, step 5).** `read`/`page`
  ride W04 `read_page`/`continue_read` directly (byte-cursor,
  UTF-8-boundary-safe, per-page sha256; concatenation
  reproduces the source byte-for-byte — proven in the gate on
  a ~120 KB single-section document). `edit` is section-scoped
  only: dry-run by default (old/new section hashes, nothing
  written), kernel/anchor sections require `--approved`
  (draft Q7 default), a confirmed save is transactional,
  preserves every byte outside the section, then re-ingests,
  re-syncs the index and validates.
- **Watchdog (step 6).** A bounded diagnostic RUN, never a
  daemon and no scheduler installed (Q4 unruled): inputs are
  only the active compile, stored receipts and operator-supplied
  response samples carrying explicit per-dimension scores (the
  pure sections 27–28 surfaces score nothing from prose, and
  neither does this layer); no scored samples is a named
  `no_evidence` result. Section 30 repair surfaces only as an
  editor proposal with `applied: false`. Corpus hashes are
  taken before and after every run and must agree.
- **Privacy filter (P.018, step 7).** One pure function,
  `persona_ops.egress_decision`, consulted at the W05 packet
  seam (`plugins/volmarr-core/persona_live.py`, +43 lines: the
  destination arrives as a turn signal, default `local`, and
  local turns are byte-identical to the pre-filter behaviour;
  privacy labels come from the W03 manifest; refusals omit the
  item and land on the turn receipt as `privacy_refused`) and
  by the ops layer's provider seam (`offer_to_provider`).
  Rules: public passes to cloud; shared passes only to a
  listed destination; private is refused for cloud without a
  recorded, unrevoked operator override naming the item;
  unlabelled items are refused (fail-closed). The W04
  embeddings consent gate and the W06 memory bridge's
  double-gated egress are adopted and consumed, not rebuilt
  (`memory_egress` returns the W06 receipt verbatim, and only
  after both W06 gates are on). The gate battery covers draft
  section 7 cases (a)–(f) against a capturing fake provider:
  zero private bytes captured without an override, egress with
  the override named, refusal again after revocation, shared
  listed/unlisted, public pass, and local = no cloud egress.
- **Diagnostics + how-to (P.020, step 8).** `persona
  diagnostics`: one read-only bundle (ops version, generation,
  kernel/persona hashes, manifest/index state, receipt count,
  privacy counts, cloud-egress total, last watchdog report,
  gateway state, W06 memory-corpus status, and the named next
  action for any absent layer). How-to:
  `docs/modernization/PERSONA_OPS_HOWTO.md` (beginner path in
  the draft's order + expert reference), written against the
  shipped commands.

## Bugs fixed in scope (never left unfixed)

1. **Section 75 bundles corrupted by their own file writer.**
   `export_bundle` serialised the bundle through the shared
   `_atomic_write_json` helper, whose `sort_keys=True` dump
   reorders the section 50 manifest dict but cannot reorder
   the `source_documents` list — and `validate_persona_export`
   requires the two orders to agree. Every exported bundle
   therefore failed validation on re-import (`persona bundle
   is invalid` at the source-documents check). Found by
   `test_export_import_dry_run_round_trip`; fixed by writing
   the bundle as order-preserving JSON, with the ordering law
   recorded in a comment at the write site.
2. **The bounded editor had no CLI verb** (design section 5
   layer 2 is a CLI editor). Wired `persona edit <stable-id>
   --text ... [--confirm] [--approved]` through the same
   dispatch as every other verb, and covered its dry-run
   purity through the CLI path in the gate tests.

## Verification (counts from the logs, laptop)

- **New W07 tests: 17 passed / 0 failed** —
  `tests/plugins/test_volmarr_persona_ops.py` 8/8 (status/files
  vs independent ground truth, buried-needle search + citation,
  live inspect, validate fault injection — collision, invalid
  UTF-8 at a named offset, symlink escape — reload dry-run
  purity + diff, live-scope activation with the W05 state,
  export/import round trip, backup/restore + corruption
  refusal) and `tests/plugins/test_volmarr_persona_ops_gate.py`
  9/9 (the full command battery against ground truth on a
  4-document fixture with a buried section, mixed privacy
  classes and an oversize document; ONE REAL gateway turn
  driven through the actual plugin manager's `pre_llm_call`
  hook chain, then `explain` reading that turn's W05 receipt;
  pager concatenation + continuation; editor dry-run then
  confirmed edit with byte-exact preservation outside the
  section; watchdog bounds + `no_evidence`; the P.018
  capturing-provider battery; generation-store torn-pointer
  recovery; honest-empty profile; the CLI family incl. the
  edit verb). Log: `~/team08-w07-newtests.log`. The
  example-record canary holds throughout: fixture values
  differ from every roadmap example and the builders' example
  records are asserted absent from command output.
- **Full contract set: 130 files = 1,046 passed / 7 failed /
  1 skipped** via `scripts/run_tests.sh
  tests/plugins/test_volmarr_*.py tests/plugins/test_kista_*.py`
  (log: `~/team08-w07-contracts.log`). 1,046 = 1,029 (banked
  W06 baseline) + 17 new W07 tests; 130 = 128 + 2 new files.
  The 7 failures are name-identical to the baseline
  live-transport set — zero regressions:
  `test_volmarr_core_plugin.py::test_missing_unix_socket_support_is_fail_open`,
  `::test_real_discovery_publishes_versioned_metadata_without_sensitive_content`,
  `::test_registered_health_cli_requires_a_valid_verdandi_pong`,
  `::test_relative_socket_path_cannot_escape_the_active_profile`,
  `::test_transport_failure_is_fail_open_for_the_pre_tool_policy_hook`,
  `test_volmarr_verdandi_stimuli.py::test_real_plugin_applies_only_unseen_allowlisted_metadata`,
  `test_volmarr_voice_runner.py::test_real_loopback_runner_delivers_canonical_stdin_event_then_eof`.
  Resource law held: the contract run waited for the other
  campaigns' heavy suites (Samverk unittest discover, Runmal
  pytest) to clear before starting (detached waiter; the
  final grading run launched with no other heavy suite
  running).
- README.md sha256 `336813d11bbe...` verified unchanged at
  close; the dormant live `~/.hermes` was never a fixture
  (all fixtures are harness homes under the test runner).

## Section 28.2 verdicts (design draft inventories)

- Section 12 table (13 rows): **0 live at audit → 13 live**,
  with two named scopes: `import` is dry-run only (Q2) and
  `reload --activate` is `live_next_turn` only where the W05
  live state is present in-process (proven), otherwise the
  honestly labelled `next_gateway_start` pointer scope.
- Draft inventory rows 6–17 (sections 70–76 builders, watchdog
  + drift, repair pipeline, fast local watchdog tasks,
  drift/golden surfaces, fingerprints/telemetry/quality):
  the sections 70–76 builders now have live callers (this
  wave's commands); sections 27–28/30 have their first live
  caller in the watchdog run, as bounded diagnostics only;
  sections 57–63 have a measured battery (`persona test`)
  rather than a full replay runner — see W07-R4.
- Rows 21–26 (absent at audit): status, files,
  reload --activate, backup/restore, the huge-file pager and
  the pre-inference filter are built and live as scoped
  above; the editor is CLI pager + bounded CLI editor
  (layers 1–2), not the virtualised viewer (W07-R3).

## Honest remainders (NOT declared complete)

- **W07-R1 (closed in part):** live mid-session activation
  works where a `PersonaLiveState` is in-process (the W05
  seam, proven in tests); a CLI invocation is a separate
  process and its activation scope stays `next_gateway_start`,
  named in every record.
- **W07-R2:** the combined section 29 transparency panel as a
  rendered view is not shipped; diagnostics carries the
  persona third plus the W06 memory-corpus status field.
- **W07-R3:** the virtualised editor layer (TUI/Web/Desktop)
  and its shared-component contract with Team 07 are not
  built; CLI pager + bounded CLI editor shipped.
- **W07-R4:** the 1,000-turn drift run (P.017's full battery)
  remains a W13 Q-gate activity; W07 ships the measured
  fixture-scale battery it will consume.
- **W07-R5:** backup/restore is proven single-host only;
  cross-machine restore + schema migration joins W08/E.18.
- **Mutating import** awaits ruling Q2; **backup encryption**
  awaits W00.03-ENC (backups are integrity-checked and
  labelled `unencrypted-local`); **watchdog cadence** awaits
  Q4 (on-demand only, no scheduler installed); **Q5** stands
  at the draft's design (per-source recorded overrides) until
  ruled; **Q6** stands at keep-all (the ops journal appends
  without rotation and the record says so).
- **Filter scope note:** at the packet seam the kernel item is
  judged by the strictest privacy class among its source
  documents with no destination list of its own, so a kernel
  whose strictest source is `shared` is refused for cloud even
  when that source lists the destination (fail-closed);
  per-source destinations apply to retrieved items. Surfaces
  that never wire persona content (voice, cron, delegates at
  their defaults) inherit the default-off persona flags — no
  persona content, no leak — until their wiring lands with
  the filter attached (draft risk R4).
- **CLI exit shape:** read-only honest-empty results return
  exit 1 from the CLI with the structured record printed;
  the library API returns the same records directly.
- The 7 live-transport failures stay environment-bound (no
  live Verdandi service on this laptop); real-socket diagnosis
  beyond name-identity stays open, as at every prior banking.
