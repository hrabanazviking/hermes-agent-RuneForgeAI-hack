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

---

# Slice 83 — Gate 0 outcome and implementation (2026-10-30, later tick)

**Gate 0 verdict: PASS via the official BM25 route only.** Measured against
the official `mempalace` 3.11.0 wheel (current PyPI release; floor is
3.10.0), installed in a scratch venv outside the tree:

- API surface: `mempalace.searcher.search_memories(query, palace_path,
  wing=None, room=None, source_file=None, since=None, before=None,
  n_results=5, max_distance=0.0, vector_disabled=False,
  candidate_strategy="vector", collection_name=None, ...) -> dict` with
  `results[]` hits carrying `drawer_id`, `text`, `wing`, `room`,
  `source_file`, `similarity` (vector path).
- Vector path NOT read-only-safe: `_open_search_collection` requests
  `get_collection(..., create=False, read_only=True)`, but the Chroma
  backend's own source states client opening/closing writes to
  `chroma.sqlite3`. Measured: two consecutive `search_memories` calls on
  a test palace each changed the `chroma.sqlite3` sha256, and the first
  created `.blob_seq_ids_migrated` + `.collection_type_fixed` marker
  files in the palace directory. This route is never used by the bridge.
- BM25 route read-only-safe: `vector_disabled=True` routes to the
  official sqlite-only fallback (`_bm25_only_via_sqlite`, response
  marker `fallback: bm25_only_via_sqlite`), which reads `chroma.sqlite3`
  through a read-only sqlite connection and never opens a Chroma client.
  Measured on a populated palace (one mined drawer): the query returned
  that drawer verbatim with its `drawer_id`, and the whole palace tree
  was sha256-identical before/after. BM25 hits carry `similarity=None`,
  so the bridge assigns the spec's fallback priority 0.5.
- Scope honesty: this retrieval is lexical (exact-word BM25), not
  semantic vector search. That is the full extent of the read-only-safe
  official surface in 3.11.0.

**Implementation (as specified):** `plugins/volmarr-core/mempalace_retrieval.py`
(`MemPalaceRetrievalBridge`), registered as one added `packet_sources`
producer in `plugins/volmarr-core/__init__.py`; opt-in
`mempalace_retrieval_enabled` default false; health-probe gated
(`probe_mempalace`); query cap 2,000 chars; ≤5 items, content cap 800
chars; `drawer_id` as record_id with sha256 fallback; bounded timeout
(`mempalace_retrieval_timeout_seconds`, default 5, clamped 1–30) via a
daemon thread; fail-open throughout. New contracts:
`tests/plugins/test_volmarr_mempalace_retrieval.py` (9 tests).

**Tests:** targeted run (retrieval + mempalace health + context packet):
17 passed, 0 failed. Full volmarr/kista contract run (38 files): the
only failures are the same 7 pre-existing environmental failures in the
same 3 files recorded in `CAMPAIGN_STATE.md` — no new failures.

**Next resume point: Slice 84 — OpenViking retrieval audit** (Phase 3's
remaining retrieval connection), then the Bifröst
Huginn/Muninn/consolidation/decay contracts.

---

# Slice 84 — OpenViking Retrieval Audit (Gate 0, 2026-10-30)

**Verdict: CONDITIONAL PASS — corpus-read-only retrieval exists via
`POST /api/v1/search/find` only; Slice 85 (below) may implement a bridge
on that route under the stated conditions. No bridge code in this slice.**

## Sources audited

- The catalog-pinned official source: `volcengine/OpenViking` at
  `e855796c83f9eb575d9b0f3082926660730f6a63` — the exact pin in this
  repo's `plugin-catalog/openviking.yaml` (Hermes plugin 2.1.2; Quick
  Local installs the newest OpenViking 0.5.x server from PyPI; latest
  PyPI release at audit time: 0.5.2.1). Audited in a scratch clone
  outside the tree.
- The existing attachment in this tree: `plugins/volmarr-core/openviking.py`
  (credential-free, loopback-only health probe; server floor 0.4.21).
- Official docs for find-vs-search semantics (docs.openviking.ai,
  retrieval concept page).

## The retrieval surface

- `POST /api/v1/search/find` — semantic search **without session
  context**. Request (`FindRequest`, extra fields forbidden): `query`,
  `target_uri`, `context_type` (`memory`/`resource`/`skill`),
  `limit` (≥1), `score_threshold`, `filter`, `level`, `read_content`,
  `telemetry` (default false), plus time/tag filters. Response envelope:
  `{status: "ok", result: {memories: [...], resources: [...],
  skills: [...], total: N}}`; each hit carries `context_type`, `uri`,
  `level`, `score`, `abstract`, `tags` (and `origin_score`/`time_score`
  when rerank provenance exists). Full text is NOT in a plain hit: with
  `read_content=true` the router additionally inlines a `content` field
  per hit via the server's own visible-content read.
- `POST /api/v1/search/search` — **excluded.** With a `session_id` it
  loads session state and, when intent analysis is enabled, runs an LLM
  intent pass over session content; `mode="context"` adds budgeting,
  query expansion/rewrite, and cross-turn dedup state. Not a stateless
  read from the caller's side.
- `POST /api/v1/search/recall` — deprecated preset over the same
  context assembly as search mode=context. **Excluded** for the same
  reason.
- `POST /api/v1/search/grep` and `/glob` — filesystem pattern walks,
  not episodic semantic retrieval. Out of scope for this phase.
- The official Hermes provider's own prefetch (examples/hermes-plugin)
  confirms the shape: it posts to `/search/search` with a session id
  and falls back to `/search/find` with `{query, limit,
  score_threshold, context_type}` — i.e. `/find` is the session-free
  face of the same API.

## Read-only evidence (corpus)

- The `/find` call chain — router → `SearchService.find` →
  `VikingFS.find` (`openviking/storage/viking_fs/_semantic.py`) →
  `HierarchicalRetriever` → vector-store `search_by_vector` /
  `search_by_keywords` — contains **no corpus writes**: no insert,
  update, upsert, or delete against the context/vector store anywhere
  on the path (grep-verified at the pin). `_ensure_retrieval_scope` is
  an ACL/existence check, not creation. `RetrievalStats` is an
  in-memory, process-lifetime accumulator only.
- `/find` never loads a session, never runs intent analysis, and
  creates no session state (contrast `/search` above).
- No ingestion or extraction is triggered by `/find`; extraction/write
  paths live on entirely different routes (resources, skills, session
  commit).

## Conditions and disclosed side effects

1. **Server-owned usage audit (default ON).** The server's
   observability config defaults `usage_audit.enabled=true` (sqlite
   backend). `/health` is audit-excluded, but the search routes are
   deliberately projected into usage/audit rows and retrieval counters
   (`openviking/observability/usage_audit/projection.py`). A `/find`
   call therefore causes the **server itself** to append audit rows to
   its own observability store — the same accounting the official
   provider's prefetch already triggers on every turn it serves. This
   is not a corpus mutation and not ingestion, but it is a real
   server-side write, disclosed here rather than hidden: the Slice 85
   bridge stays opt-in default-off, and a server operator who wants
   zero audit writes can set `observability.usage_audit.enabled=false`
   server-side. Volmarr-core cannot read that setting remotely (the
   health response does not expose it), so the bridge does not claim
   to verify it.
2. **Auth gate.** `/health` exposes the server's effective
   `auth_mode`. Credential-free retrieval exists only in `dev` mode
   (auto-selected when no root API key is configured). `api_key` and
   `trusted` modes require a key **even on localhost**. The existing
   attachment law is credential-free and loopback-only, so the bridge
   must fail closed (no items) unless health reports `auth_mode ==
   "dev"`, and must never read, send, or store a credential.
3. **Embedding egress is server-side and unattestable remotely.** The
   query text goes only to the loopback server, but the server embeds
   it with **its own configured embedder**, which may be a remote API;
   `/health` does not expose embedder locality. Opt-in enablement is
   the operator's attestation; the bridge sends only the current user
   message (capped), never history, never a session id.
4. **Live-server measurement NOT PROVEN in this sandbox.** Unlike
   Slice 83's library-level byte measurement, no live OpenViking
   server was run here: the server cannot embed without a configured
   embedding model/provider, and none is available in this sandbox.
   The verdict rests on the pinned-source audit above plus the
   upstream test suite's coverage of these routes, and is recorded as
   such — the same honesty class as Phase 2's live Verðandi transport.

## Slice 85 — OpenViking bounded retrieval bridge (implementation-ready spec)

- New module `plugins/volmarr-core/openviking_retrieval.py`:
  `OpenVikingRetrievalBridge(ctx)` with `packet_items(session_id,
  user_message) -> list[ContextItem]`, following the Slice 83 producer
  pattern. One added `packet_sources` entry in
  `plugins/volmarr-core/__init__.py`; no core files, no provider
  registration, no credentials anywhere.
- Opt-in only: config `openviking_retrieval_enabled`, default `false`.
- Gates, in order: existing `probe_openviking` healthy → health
  `auth_mode == "dev"` (the bridge reads `auth_mode` from its own
  bounded health GET reusing `openviking.py`'s loopback validation, or
  the probe grows an optional `auth_mode` field — implementer's choice,
  additive either way) → only then POST.
- Request: `POST {base}/api/v1/search/find`, JSON body exactly
  `{query, limit: 5, context_type: "memory", read_content: true}`,
  `telemetry` omitted (false), no session id, no target_uri (server
  default scope), headers mirroring the probe (`Accept:
  application/json`, the runeforgeai user-agent), no redirects, no
  proxy, loopback base URL validated by the existing
  `_loopback_base_url`. HTTP timeout from
  `openviking_probe_timeout_ms` semantics (bounded, ≤10 s).
- Query discipline: current user message only, stripped, hard-capped
  at 2,000 chars; empty/non-string → no items and no request.
- Items: from `result.memories` only (resources/skills are not
  episodes); content = hit `content` when a non-empty string, else hit
  `abstract`; hard cap 800 chars; `section="relevant_episodes"`,
  `source="openviking/memories"`, `record_id` = hit `uri` when a
  non-empty string, else sha256-16 of content; `priority` = hit
  `score` when a finite number in [0, 1], else 0.5; at most 5 items.
- Fail-open: any non-200 (including 401/403 in non-dev modes),
  malformed envelope, timeout, or exception returns `[]`.
- Privacy: retrieved text enters only the central context packet
  (already fence-escaped, untrusted). Nothing is logged, published, or
  persisted by the bridge. Disclosed server side effects when enabled:
  the server's own usage-audit rows (condition 1) and its embedding of
  the query with its configured embedder (condition 3).
- Tests (new file `tests/plugins/test_volmarr_openviking_retrieval.py`):
  behaviour contracts through real plugin discovery with a temp
  `HERMES_HOME` and a local stub HTTP server implementing only the
  audited `/health` + `/find` shapes — disabled by default; enabled +
  dev-mode health returns the seeded episode as one packet item with
  provenance; api_key-mode health → no request to `/find` at all
  (asserted on the stub's request log); A→B→A profile isolation;
  bounds (>5 hits truncated, oversize content capped, fence-shaped
  content escaped by the packet); empty message → no request; query
  truncated to the cap (asserted from the stub's received body);
  `/find` raising/500/malformed → fail-open with other producers'
  items intact.
- Bookkeeping on completion: `CUSTOMIZATIONS.md` ledger row; roadmap
  §29 Milestone 3 slice-85 paragraph; `CAMPAIGN_STATE.md` update
  naming the next resume point (the Bifröst Huginn/Muninn/
  consolidation/decay contracts). Bank locally only; no push.

---

# Slice 85 — Implementation outcome (2026-10-30, later tick)

**Implemented as specified.** `plugins/volmarr-core/openviking_retrieval.py`
(`OpenVikingRetrievalBridge`), registered as one added `packet_sources`
producer in `plugins/volmarr-core/__init__.py`. The probe grew the
additive optional `auth_mode` field on `OpenVikingHealth` (populated
from `/health` on the healthy, unhealthy, and outdated returns), and
the bridge gates in order: opt-in config → non-empty capped query →
`probe_openviking` healthy → `auth_mode == "dev"` → POST. The request
body is exactly `{query, limit: 5, context_type: "memory",
read_content: true}`; timeout reuses the probe's bounded
`openviking_probe_timeout_ms` semantics; transport reuses the probe's
no-redirect/no-proxy loopback opener; responses are byte-capped
(1 MiB) and any non-200, malformed envelope, timeout, or exception
returns `[]`. Items come from `result.memories` only, content falling
back to `abstract`, capped at 800 chars, `uri` as record_id with the
sha256-16 fallback, `score` as priority when finite in [0, 1] else 0.5.

**Tests:** new `tests/plugins/test_volmarr_openviking_retrieval.py`
(8 tests) against a stub server implementing only the audited
`/health` + `/find` shapes — disabled-by-default makes no requests at
all; dev-mode retrieval emits both content and abstract-fallback
episodes with provenance and the exact audited request body;
api_key/trusted/unreported auth modes consult health but never POST;
A→B→A profile isolation; bounds; fence escaping; query discipline
(empty → no request, oversize truncated to 2,000 asserted from the
received body); `/find` 500 / non-JSON / malformed-envelope fail-open
with other producers' items intact. Targeted run (new file + OpenViking
health + MemPalace retrieval): 21 passed, 0 failed. Full volmarr/kista
contract run (39 files): **229 passed, 7 failed, 1 skipped** — the
failures are the same name-identical pre-existing environmental set
(5 core-plugin, 1 Verðandi-stimuli socket, 1 voice-runner loopback);
no new failures.

**Next resume point:** the Bifröst Huginn/Muninn/consolidation/decay
contracts — Milestone 3's last remaining item. Banked locally only;
no push.
---

# Slice 86 — Bifröst Huginn/Muninn/Consolidation/Decay Gate 0 Audit (2026-10-30)

**Verdict: NO-GO for every Bifröst write path at this time; the audit
itself is complete and the one safe next step is specified as Slice 87
below (a read-only Muninn store probe, no package import, no bridge
call). No bridge code, no config change, and no enabling in this
slice.** Three independent grounds, each sufficient on its own:

1. **The two backend packages the write paths live in cannot be
   audited.** `BifrostBridge.decay()` and `.consolidate()` delegate
   entirely to the external `muninn` package, Muninn reinforcement
   writes through it, and Huginn ingestion/search go through the
   external `huginn` package. Neither package has an auditable
   canonical source (details below), so their mutation semantics —
   what decay prunes, what consolidation rewrites, what an activation
   writes — are **NOT PROVEN** and cannot be specified honestly.
2. **Reads through the bridge are not reads.** In the audited bridge
   source, `recall()` always logs a Muninn activation, and `search()`
   reinforces co-activations whenever reinforcement is enabled — both
   are writes on the read path, into a store whose package is ground 1.
3. **The auto flags are dead.** `auto_consolidate`, `auto_decay`,
   `consolidation_threshold`, and `decay_interval_hours` are declared
   in `BifrostConfig` and never read anywhere in the bridge. Flipping
   the Hermes wrapper's `False` values would change nothing; there is
   no scheduler in the package. Consolidation/decay happen only via
   explicit `bridge.decay()` / `bridge.consolidate()` calls, which no
   code in this tree makes.

## The in-tree attachment surface (verified on this tree)

- The whole Bifröst **code** surface in this tree is:
  `plugins/volmarr-core/memory_fabric.py` (`BifrostSettings`,
  `build_bifrost_bridge`, `probe_bifrost`), the
  `hermes volmarr memory health` CLI action that calls `probe_bifrost`,
  two path keys in `plugin.yaml` (`bifrost_mimir_db_path`,
  `bifrost_muninn_db_path`), and
  `tests/plugins/test_volmarr_memory_fabric.py` (3 contracts, which
  stub the `bifrost` package in `sys.modules`). Around that code sit
  documentation/provenance mentions only: `ARCHITECTURE_VOLMARR.md`
  § Slice 8, the `CUSTOMIZATIONS.md` ledger row, `THIRD_PARTY_NOTICES.md`,
  and the `COMPONENT_LICENSES.md` pin — no other code path touches
  Bifröst.
- `build_bifrost_bridge` only constructs: it resolves both DB paths
  against the active profile (relative escapes are rejected before
  construction), imports `bifrost`, and builds a `BifrostConfig` with
  `default_backend=MIMIR`, `enable_hebbian_reinforcement=False`,
  `auto_consolidate=False`, `auto_decay=False`. **No caller in this
  tree calls any bridge method** (`search`, `store`, `recall`,
  `decay`, `consolidate`, `health`, `stats` are all uncalled);
  `probe_bifrost` discards the constructed bridge and validates Mímir
  itself through a read-only sqlite URI (`mode=ro`), requiring the
  `memories` table and returning its count, rejecting symlinks and
  missing files without creating anything.
- The `bifrost` package is **not a dependency of this tree**: it is
  absent from `pyproject.toml` and `uv.lock` and is not installed in
  the test environment (import fails), so `package_missing` is the
  normal health status on a stock tree and the contract tests stub it.
- Not to be conflated: `plugins/volmarr-core/consolidation.py` is the
  entity consolidation *checkpoint* (identity/relationships/goals/
  heartbeat digests; its own docstring states it does not rewrite
  memory). It is complete under Phase 7 and is **not** Bifröst
  consolidation; it does not discharge this item.

## The external package (audited source)

- `hrabanazviking/bifrost` at `b66e98cc8a79d4dede22ba11d68a1a5ecd22ebd6`
  (HEAD of `main` at audit time; package version 1.0.0, zero core
  dependencies, `huginn`/`muninn` as optional extras).
  `COMPONENT_LICENSES.md` in this tree pins exactly this commit as
  the provenance record — so the audited source is precisely the
  recorded version — but the package is still not a dependency in
  `pyproject.toml`/`uv.lock` (below) and no equivalent pin exists
  for `huginn` or `muninn`. Audited in a scratch clone outside the
  tree. (Correction appended the same tick: an earlier draft of this
  section wrongly said no pin exists in this tree; the
  `COMPONENT_LICENSES.md` pin was found by the full-tree sweep after
  the first banking and the text was fixed before any push.)
- Upstream `BifrostConfig` defaults run opposite to this tree's
  attachment law: `default_backend=ALL`,
  `enable_hebbian_reinforcement=True`, `auto_consolidate=True`,
  `auto_decay=True`, DB paths anchored to `~/.hermes` (launch home,
  not the active profile), `qdrant_url=http://localhost:6333`. The
  Hermes wrapper overrides the paths, the default backend, and the
  three enable flags — but not `min_activation_threshold` (default 3),
  the scoring weights, `max_results_per_backend`, `qdrant_url`, or
  the (dead) consolidation/decay knobs.
- **Lazy-init trap:** every bridge method calls
  `_ensure_initialized()`, which unconditionally tries to construct
  Huginn (`HuginnMemory(config=None)` — the configured `qdrant_url`
  is never passed) and Muninn (`HebbianMemory(MuninnConfig(db_path=…))`)
  regardless of the requested backend. A Mímir-only `search()` would
  still construct both. Their constructors' side effects (DB creation,
  migrations) live in the unauditable packages of ground 1.
  `_ensure_mimir` itself opens sqlite read-write and executes
  `PRAGMA journal_mode=WAL` — an open that can change the store's
  journal mode and create WAL sidecars. The existing probe's refusal
  to touch the bridge is therefore load-bearing, not incidental.
- Operation inventory in `src/bifrost/core.py`:
  - `search(query, …)` — Mímir FTS5 + Huginn semantic + Muninn
    association reads, composite-scored; then, if
    `enable_hebbian_reinforcement` and >1 result,
    `_reinforce_coactivation()` writes Muninn activations/connections
    (anchor-gated by `min_activation_threshold`: at/above → full
    `activate_batch`; below → individual `activate()` logs only —
    still writes). The wrapper's `False` keeps this tree's config on
    the safe side, but only as a config value on an uncalled object.
  - `recall(memory_id)` — Mímir row read that **always** calls
    `muninn.activate(memory_id)` when Muninn loaded. Write-on-read.
  - `store(content, …)` — the only ingestion path: Mímir
    `INSERT` + commit, Huginn `upsert_memory` (this is "Huginn
    ingestion"), Muninn `activate`. Unbounded, ungated, no opt-in
    exists for it in `plugin.yaml`.
  - `decay(days=1.0)` — returns `muninn.decay(days=days)` only.
    Rate, floor, and pruning semantics are entirely Muninn's.
  - `consolidate()` — returns `muninn.consolidate()` only;
    `consolidation_threshold` is never consulted.
  - `health()` / `stats()` — also run `_ensure_initialized()`, so
    even the bridge's own health check constructs the write backends.
- `src/bifrost/bridges/memory_bridge.py` (`BifrostMemory`, an
  NSE-facing Mímir+Hebbian retrieve/store shim) is a separate surface:
  it is not exported by `bifrost/__init__.py`, its default paths are
  `Path.home()/.hermes`-anchored, its connections are read-write with
  WAL pragmas, and its `store_memory` writes Mímir. It is **not**
  attached by this tree and stays out of scope.

## The dependency blocker (ground 1, in full)

- `pyproject.toml` of the audited package declares the extras as bare
  unpinned names: `huginn = ["huginn"]`, `muninn = ["muninn"]` — no
  version, no index, no URL.
- The public PyPI projects under those exact names are unrelated
  packages (PyPI `huginn` is an anomalous-spike investigation tool;
  PyPI `muninn` is an unrelated legacy package); neither provides
  `HebbianMemory` or `HuginnMemory`. Installing the extras by name
  would pull the wrong software — a name-collision hazard, recorded
  as a discovered defect of the audited package's packaging.
- No public repository exists under `hrabanazviking/muninn` or
  `hrabanazviking/huginn` (`git ls-remote`: repository not found),
  and no copy of either package exists in this tree. The bridge's own
  test suite (`tests/test_hebbian_guard.py`) imports the real
  `muninn`, proving a canonical package exists somewhere — on
  Volmarr's own machines/history — but its location is not recorded
  in either repo. **What is needed from Volmarr: the canonical
  `muninn` (and, if Huginn is still wanted, `huginn`) source
  locations or pins.** Until then, Huginn ingestion, Muninn
  reinforcement, and Bifröst consolidation/decay cannot be specified,
  let alone enabled; Gate 0 reopens on those sources when supplied.
- Schema evidence that *is* available from the audited bridge code
  alone: the Muninn store is expected to carry `activation_log`
  (`memory_id`, read by `_get_activation_count`) and, per the NSE
  bridge, `hebbian_connections` (`memory_a_id`, `memory_b_id`,
  `strength`, `co_activation_count`). That is enough for a read-only
  store probe (Slice 87) and for nothing more.

## Slice 87 — Muninn read-only association-store probe (implementation-ready spec)

- Extend `plugins/volmarr-core/memory_fabric.py` with
  `probe_bifrost_muninn(ctx) -> BifrostMuninnHealth` (frozen dataclass,
  `as_dict()`), mirroring `probe_bifrost`'s discipline exactly:
  resolve the Muninn path through the existing `BifrostSettings`
  (same profile-escape rejection), reject symlinks and missing files
  without creating anything, open via the read-only sqlite URI
  (`mode=ro`, 1 s timeout), require both `hebbian_connections` and
  `activation_log` tables, and report their row counts. Statuses:
  `healthy`, `storage_missing`, `schema_missing`, `storage_error`,
  `configuration_error`, with `error_type` on failures. The probe
  must **not** import `bifrost` or `muninn`, must not construct a
  bridge, and must not require the `bifrost` package to be installed.
- CLI: add the `muninn health` sub-action beside the existing memory
  health actions in `plugins/volmarr-core/cli.py`
  (`hermes volmarr memory muninn health [--json]`, label "Bifröst
  Muninn"), following the mempalace/openviking/sessiondb pattern.
- No config changes, no packet producer, no writes of any kind: this
  slice only attests that a Muninn store exists for the active
  profile, matches the schema the audited bridge code expects, and
  how much association state it holds.
- Tests (new file `tests/plugins/test_volmarr_bifrost_muninn.py`,
  real plugin discovery with a temp `HERMES_HOME`, per
  `tests/AGENTS.md`): healthy store reports both counts; A→B→A
  profile isolation; missing store reports `storage_missing` and
  creates nothing; a store missing either table reports
  `schema_missing`; store bytes identical before/after the probe;
  profile-escaping path reports `configuration_error`; the probe
  succeeds with no `bifrost` package present (the stock-tree case).
- Bookkeeping on completion: `CUSTOMIZATIONS.md` ledger row (the CLI
  surface widens); roadmap §29 Milestone 3 slice-87 paragraph;
  `CAMPAIGN_STATE.md` update. Bank locally only; no push.
- After Slice 87, Milestone 3's write paths (Huginn ingestion,
  Muninn reinforcement, Bifröst consolidation/decay) stay parked on
  the dependency blocker above — they are the one Milestone 3 item
  that cannot proceed without Volmarr's word on the canonical
  package sources. The campaign then moves to roadmap queue item 2
  (Emergent Agency, Phase 0) per `CAMPAIGN_STATE.md` ordering, and
  returns here when the sources are supplied.
