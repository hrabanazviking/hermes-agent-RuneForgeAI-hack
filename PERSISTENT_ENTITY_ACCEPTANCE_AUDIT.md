# Persistent Entity Roadmap — Acceptance Audit (2026-10-30, post-refresh)

Audit of `VOLMARR_HERMES_PERSISTENT_ENTITY_ROADMAP.md` against the refreshed
tree (local `main` == `origin/main` ==
`9754aa239a8ecf01cd1821989f0f20dc8ef0b628`, upstream intake
`6bb377a51d5c8e279a7a5e34d717d653d421d064`). Method: roadmap milestone
statuses (§29) and `CUSTOMIZATIONS.md` ledger rows cross-checked against the
code on disk, plus a fresh contract-test run on the refreshed tree.

## Verification run (this audit)

- Command: `scripts/run_tests.sh` (never bare pytest) with
  `HERMES_PYTHON=.venv/bin/python`, over all 37
  `tests/plugins/test_volmarr_*.py` / `test_kista_*.py` contract files.
- Result: **212 passed, 7 failed, 1 skipped; 3 of 37 files with failures.**
- The 7 failures are the **name-identical pre-existing environmental set**
  recorded in `CAMPAIGN_STATE.md` from the pre-merge baseline
  (`111f58aa`): 5 in `test_volmarr_core_plugin.py` and 1 in
  `test_volmarr_verdandi_stimuli.py` (Verðandi Unix-socket transport; needs
  a live Verðandi service) and 1 in `test_volmarr_voice_runner.py` (real
  loopback runner; connection refused in this sandbox).
- Verdict: **no intake regressions.** Every other contract file passed,
  including memory fabric, MemPalace, OpenViking, SessionDB, present state,
  context packet, affective, PAD, WYRD, identity, relationships, goals,
  heartbeat, routines, consolidation, cognition endpoint/routing/execution,
  Kista secret source + canary, astrology, tarot, Seiðr, RPG, Hamr,
  Seiðr-Smiðja, and the voice presentation/transport files.

## Phase-by-phase verdicts

| Phase (§) | Verdict | Evidence / gap |
|---|---|---|
| 1 Cognition Router (§6) | Complete (application contract) | Milestone 2 status in roadmap; cognition endpoint/routing/execution contract tests pass. Automatic interception of ordinary Hermes turns is explicitly not claimed. |
| 2 Verðandi nervous system (§7) | Complete, live-transport NOT PROVEN in this sandbox | Milestone 1 status; lifecycle/health code passes except the 6 pre-existing socket-transport failures above, identical pre- and post-merge, which need a live Verðandi service. |
| 3 Memory Fabric (§8) | **IN PROGRESS — first unmet phase** | Milestone 3 status: Bifröst attachment (Mímir read-only), Present State, MemPalace health, OpenViking health, SessionDB preservation, and the bounded context packet are implemented and pass. **Unmet:** precise episodic/durable **retrieval** (MemPalace and OpenViking retrieval/ingestion remain disabled by design); Bifröst Huginn, Muninn reinforcement, consolidation, and decay remain disabled pending their own contracts. |
| 4 Affective refactor (§9) | Complete | Milestone 4 status; affective + PAD + Verðandi-stimuli contracts pass (except the one pre-existing stimuli transport failure above). |
| 5 WYRD world model (§10) | Complete | Milestone 5 status incl. restart acceptance against official WYRD v1.0.0; WYRD contract tests pass. |
| 6 Identity & continuity (§11) | Complete | Milestone 6 status; identity/relationships/goals contracts pass. |
| 7 Background life (§12) | Complete | Milestone 6 status; heartbeat, frequent routine, and sleep/consolidation contracts pass. Cadence is delegated to Hermes cron; no resident timer. |
| 8 Kista secret source (§13) | Complete | Milestone 7 status (slices 28–31); Kista + canary contract tests pass. |
| 9 Spiritual/RPG suite (§14) | In progress | Astrology (7 tools), Tarot, Seiðr poetry, and the minimal RPG mechanics family are complete per Milestone 8 progress (slices 32–53) and pass. **Unmet:** PageIndex/document retrieval, listed in Milestone 8's scope, has no slice yet. |
| 10 Avatar & embodiment (§15) | In progress | Hamr and Seiðr-Smiðja are read-only preflight only (slices 54–64); no build authority. Realtime presence is at the presentation-contract stage (Phase 11 slices). Second Life is a separate project, out of this tree. |
| 11 Voice (§16) | In progress | Hermes remains the voice owner (roadmap §16 as amended); readiness + provider-free dispatch + presentation envelope/loopback feed are implemented (slices 65–82) and pass except the one pre-existing loopback-runner sandbox failure. Automatic native-voice mirroring is deferred by the slice-75 audit (`post_tool_call` cannot cover direct TTS calls). Next per slice 82: consolidate the exhausted official avatar-shell candidates into an explicit admission gate. |
| 12 H.E.R.E.T.I.C. body (§17) | Not started | No code or audit in this tree. |
| 13 Component mines (§18) | Partial, opportunistic | PAD, heartbeat, and sleep/consolidation concepts were ported inside Phases 4/6–7; no dedicated mining slice for Runa/WaifuOS/Cortex/ChatIndex concepts. ChatIndex/PageIndex retrieval overlaps the Phase 9 gap. |
| 14 Context construction (§19) | Partial | The bounded context packet (single prompt-facing assembly point) is implemented and passes. **Unmet:** per-turn tool-schema narrowing and local-model packet preparation/compression. |
| 15 Cloud escalation & cost governor (§20) | Partial | The router chooses deterministic/local/cloud tiers and forced modes truthfully. **Unmet:** budget configuration (`daily_budget_usd` etc.), measured cloud usage, and cost accounting. |
| 16 Self-health & recovery (§21) | Partial | Per-domain health commands exist (Verðandi, cognition, memory, WYRD, identity). **Unmet:** one unified self-health check over all §21 items and any recovery orchestration. |
| 17 Backup / continuity vault (§22) | Not started | Milestone 10 not started in this tree. (Volmarr's Samtal noon backup is a different project's pipeline and does not count here.) |
| 18 Migration proof (§23) | Not started | Milestone 11 gated on Phase 17. |
| 19 Cloud host migration (§24) | Not started | Gated on Phase 18; provider choice is deliberately deferred by the roadmap itself. |

## Resume point

Per the campaign queue (verify phases in order, continue at the first
unmet), the next slice is **Slice 83 — MemPalace bounded episodic
retrieval** (Phase 3), specified below in implementation-ready form.
Slices are numbered continuing the roadmap's own sequence (last: 82).

---

# Slice 83 — MemPalace Bounded Episodic Retrieval (implementation-ready spec)

## Purpose

Connect the already-attached MemPalace verbatim episodic store to the
already-implemented bounded context packet as a `relevant_episodes`
producer, so the entity can recall precise old episodes per turn without
sending huge histories to the LLM — the remaining core of Milestone 3's
"Done when". Ingestion/writes stay disabled; this slice is read-only
retrieval only.

## Gate 0 — official API audit (blocking, first step)

Prior slices never invent an upstream API (see slices 57, 66, 72, 81, 82).
Before any code:

1. Audit the installed official MemPalace package (≥ 3.10.0, the floor the
   health probe already enforces) for its search/query surface: exact
   module, function, arguments, return shape, and whether querying opens
   ChromaDB read-only or read-write.
2. If no read-only-safe query path exists, this slice **becomes an audit
   document only** (the slice 66/72 pattern), records the gap, and the
   campaign moves to the OpenViking retrieval audit as Slice 84. Do not
   open ChromaDB read-write from a per-turn hook, and do not read
   `chroma.sqlite3` embedding tables directly as a substitute API.

## Design (when Gate 0 passes)

- New module `plugins/volmarr-core/mempalace_retrieval.py`:
  `MemPalaceRetrievalBridge(ctx)` with
  `packet_items(session_id, user_message) -> list[ContextItem]`,
  following the `WyrdContextBridge` producer pattern exactly.
- Registration: one additional entry in the `packet_sources` tuple passed
  to `PresentStateBridge` in `plugins/volmarr-core/__init__.py`. No core
  files touched; no memory-provider registration (plugins policy: the
  catalog owns providers; this stays an additive volmarr-core surface).
- Opt-in only: config `mempalace_retrieval_enabled`, default `false`
  (same `_as_bool` helper pattern as `wyrd_context_enabled`).
- Query: the current user message only, stripped, hard-capped at 2,000
  chars; empty/non-string message → no items. No conversation history is
  sent to the store.
- Bounds: at most 5 results (the packet's `relevant_episodes` section
  limit is already 5), each item's content hard-capped at 800 chars
  before it reaches the packet builder; a bounded timeout on the query;
  results with non-string or empty content are dropped.
- Items: `section="relevant_episodes"`, `source="mempalace/drawers"`,
  `record_id` = the store's own drawer/record identifier when the API
  exposes one, otherwise the first 16 hex chars of the SHA-256 of the
  content (the `wyrd_context` pattern); `priority` = the API's relevance
  score when it is a finite number in a documented range, else `0.5`.
- Fail-open: every exception, missing package, missing/failed health
  state, or malformed result returns `[]` and never breaks the turn
  (the `pre_llm_call` source loop already swallows producer exceptions;
  the bridge also guards internally, matching the existing producers).
- Profile isolation: palace path and collection name resolve through the
  existing `mempalace.py` helpers/config keys
  (`mempalace_path`, `mempalace_collection_name`) so A→B→A isolation is
  inherited, not re-implemented.
- No mutation proof: the palace directory tree (including
  `chroma.sqlite3` and any WAL/SHM) must be byte-identical before/after
  retrieval in tests; if the official query path creates sidecar files,
  that fact is recorded and Gate 0's read-only verdict revisited before
  shipping.
- Privacy: retrieved text enters only the central context packet, which
  already treats it as untrusted, fence-escaped reference data. Nothing
  is logged, published to Verðandi, or persisted by this bridge.

## Tests (new file `tests/plugins/test_volmarr_mempalace_retrieval.py`)

Behaviour contracts through real plugin discovery with a temp
`HERMES_HOME`, per `tests/AGENTS.md` (no source-reading, no
change-detectors):

1. Disabled by default: healthy palace + query → no episodes item.
2. Enabled: a seeded store returns the matching episode as one
   `relevant_episodes` packet item with provenance label.
3. A→B→A profile isolation: each profile retrieves only its own palace.
4. Read-only: palace bytes identical before/after; missing store,
   missing package, and outdated package all yield no items and no
   exception.
5. Bounds: >5 results truncated to section limit; oversize content
   capped; hostile fence-shaped content reaches the packet escaped.
6. Query discipline: empty message → no query call; oversize message
   truncated to the cap (asserted via the fixture store's recorded
   query).
7. Failure fail-open: a store whose query raises yields a normal turn
   context (other producers' items still render).

The fixture store double implements only the Gate-0-audited official
API surface, at the same boundary the health tests stub
(`sys.modules["mempalace"]`), and is replaced by a real-store test if
the official package is importable in the test environment.

## Bookkeeping on completion

- `CUSTOMIZATIONS.md`: one Runtime Customizations ledger row (behavior,
  surface, verification, upstream-sync risk) — required for every
  intentional difference.
- Roadmap §29 Milestone 3 status: append the slice-83 paragraph in the
  established style; MemPalace retrieval then counts as connected, and
  Milestone 3's remaining items are OpenViking retrieval and the
  Bifröst Huginn/Muninn/consolidation/decay contracts.
- `CAMPAIGN_STATE.md`: record the slice, test numbers, and the next
  resume point.
- Bank locally only; no push without Volmarr's word for this line.
