# RuneForgeAI Hermes Hack: 2026 Modernization, Living Persona, and Ecosystem Convergence Roadmap

**Owner:** Volmarr / RuneForgeAI  
**Repository:** https://github.com/hrabanazviking/hermes-agent-RuneForgeAI-hack  
**Prepared:** 2026-11-07  
**State:** New development plan, not a claim that its work has been implemented  
**Primary target:** Update the existing personal fork against current official Hermes, refresh each already-connected external engine, and make the entire RuneForgeAI ecosystem usable without sacrificing distinct project ownership, privacy, or human-authored personality.

> **North star:** A persona or knowledge document may be arbitrarily long on disk, remain complete and editable, and never be silently trimmed or rewritten merely to squeeze it into an LLM prompt. Only the *retrieved active context* is limited by the selected model, tool budget, and operator policy. The authored corpus itself has **no artificial character or token ceiling**.

## 0. Read this before changing code

This is a follow-on roadmap to existing, substantially implemented campaigns, **not** a replacement for them. In particular consult:

- `CUSTOMIZATIONS.md`, the intentionally detailed feature and verification ledger;
- `CAMPAIGN_STATE.md`, declaring the four earlier campaigns complete on November 1;
- `ARCHITECTURE_VOLMARR.md`, the domain-boundary and ownership contract;
- `VOLMARR_HERMES_PERSISTENT_ENTITY_ROADMAP.md`;
- `VOLMARR_HERMES_EMERGENT_AGENCY_ROADMAP.md`;
- `VOLMARR_HERMES_SELF_AWARE_AGENCY_ROADMAP.md`;
- `PERSONA_RUNTIME_ROADMAP.md`, ``3–94;
- `UPSTREAM_SYNC.md` and `scripts/sync_upstream.py`;
- `COMPONENT_LICENSES.md`, `THIRD_PARTY_NOTICES.md` and project-specific license manifests;
- `HERMES_PROJECTS_UPDATE_2026-10-30.md` (a **historical snapshot**, not a substitute for reading each project's latest repository).

Do not duplicate implementations that already exist. **Reconcile, expose, update, integrate, prove.** Several existing persona sections are pure, testable contracts with *no current caller*, not a fully wired production persona engine. Several external engine bridges are health/preflight-only. The work below must explicitly move those into real user-facing behavior before claiming completion.

### 0.1 Verified baseline as of this document

- Fork `main` observed at `8233a43ee6c9b056d5c042bc04661b5628444f0b`, latest commit November 1, 2026, “Slice 164: Persona Runtime `93 Target Result + `94 Essence — roadmap complete.”
- Last **documented upstream integration**: `NousResearch/hermes-agent` at `6bb377a51d5c8e279a7a5e34d717d653d421d064`, merged October 30, 2026. Do **not** call the fork current to the latest upstream on November 7.
- Official upstream stable release checked for this plan: **v0.23.0, “The Hearth Release,” published November 5, 2026**, https://github.com/NousResearch/hermes-agent/releases/tag/v0.23.0. The official `main` branch continues changing after the release: inspect its SHA again at execution time.
- Upstream compare from the October 30 intake SHA to a November 7 upstream `main` snapshot reported **2,759 later upstream commits**. That is a maintenance signal, **not** a claim about merge conflicts or the count of missing features in the fork.
- Existing opt-in plugins observed: `volmarr-core` 0.26.0, `volmarr-voice` 1.0.0, `volmarr-astrology` 0.7.0, `volmarr-tarot` 0.3.0, `volmarr-seidr` 0.4.0, `volmarr-rpg` 0.8.0, `volmarr-hamr` 0.4.0, `volmarr-smidja` 0.1.0 and `kista-secret-source` 0.2.0. **Plugin manifest versions are not external-engine version numbers.**
- November 1 campaign records: 117 Volmarr/Kista test files, **929 passed, 7 failed, 1 skipped** in a combined interrupted-plus-restarted verification. Seven named failures were reported as recurring environment-dependent failures (five core-plugin, one Verðandi-socket, one voice loopback). These are historical reported results, **not tests re-run for this roadmap**.
- Existing Persona Runtime consists of a large `plugins/volmarr-core/persona_runtime.py` with deterministic compiler, persona IR, kernel, stable section IDs, retrieval/routing/budget prototypes, drift and audit surfaces, roster and import/export contracts. Major gaps remain: live prompt integration, semantic similarity provider, verified hot reload in an active gateway, real operator commands for portions of the surface, large-corpus performance and durability.
- Current base Hermes `agent/prompt_builder.py` uses per-file context truncation, a dynamic floor/ceiling and optional `context_file_max_chars` override. As observed here, its dynamic default has a **20,000-character floor and 500,000-character ceiling**; this is not arbitrary-sized context-file ingestion. The built-in memory tool defaults to `memory_char_limit=2200` and `user_char_limit=1375`.
- The existing `SOUL.md` in repository root is a checked-in example/instruction file; the active Hermes identity file typically resides under the selected `HERMES_HOME`. Preserve this distinction when migrating.

### 0.2 Ground rules

1. **Preserve the personal README additively.** The upstream sync script must continue to protect its bytes during automatic upstream intake. Hand-authored dated additions are allowed when requested by Volmarr.
2. **Native-first, no Docker required.** Native Linux/Kubuntu, ARM64 Linux and Termux/Android are primary. Docker-specific tests may exist upstream but are not a prerequisite for this personal deployment.
3. **The Hermes framework remains upstream-compatible.** Personal code belongs in plugins, providers, hooks, tools, skills, gateway adapters, optional services or narrowly reviewed interfaces.
4. **Keep project code in its original project.** Use versioned packages, APIs, sidecars and declared compatibility ranges. Avoid copy-pasting whole project trees into Hermes.
5. **Profiles, users and entities are separate namespaces.** Shared tools do not imply shared identity, accounts, private history or secrets.
6. **Do not sacrifice data to meet a prompt limit.** Complete originals stay on disk, indexed and recoverable. Trimming only affects a single active prompt packet with an explicit receipt.
7. **Never silently route private local material to a cloud model, telemetry sink or third-party account.** External destinations need a source-level routing policy and authorization.
8. **Replace “it looks implemented” with demonstrated acceptance.** Unit, integration, subprocess, transport, recovery, performance, privacy and actual user-facing behavior tests are distinct proof.
9. **Do not confuse roadmap completion with operational capability.** Previous `93–94` “complete” means their defined contracts and tests were banked; it does not prove an on-by-default live personality engine.
10. **No destructive auto-upgrade.** All migration steps preserve backups, have a dry-run, produce a provenance report and offer rollback.

## 1. Deliverables and completion definition

The modernization campaign produces:

1. A reproducible, pinned upstream Hermes intake at a chosen release/SHA with a tested integration branch and documented conflict resolutions.
2. A maintained source-and-version inventory of **all existing RuneForgeAI external integrations**, their installed APIs, HEAD/release, licenses, capabilities, and verified adapter level.
3. A living, **uncapped corpus** of persona and knowledge Markdown: `SOUL.md`, `IDENTITY.md`, `AGENTS.md`, `USER.md`, `MEMORY.md`, `SERVICE_BIBLE.md`, `RELATIONSHIPS.md`, `MEMORY_POLICY.md`, `TOOL_POLICY.md`, `AVATAR.md`, lorebooks, spiritual/cultural canons, character sheets, project documents and any new operator-defined role.
4. A streamed compiler/index that stores **all** authored content, supports huge files and repositories, and generates only bounded retrieval packets at inference time.
5. A live persona **kernel → retrieval → active-context** pipeline serving CLI, TUI, Web, Desktop, gateway, cron, voice and delegates uniformly.
6. Operator tooling to inspect, explain, search, reload, diff, export, import, back up, test and repair persona corpora without altering authored text.
7. A unified ecosystem adapter set: memory, cognition, hardware, voice, avatar, creative tools, multiplayer communication, coding, worlds and edge inference, all opt-in with truthful capability reporting.
8. A documented runtime/UX distribution recipe for the ROG Flow Z13, the RTX 2060 secondary laptop, Pi 5, Android/Termux, offline operation and selectively authorized cloud inference.
9. Repeatable regression suites plus a launch audit distinguishing **ready**, **prototype**, **external-unavailable**, **design-only** and **blocked**.

**Exit:** a fresh native install can ingest a multi-megabyte `SOUL.md` plus numerous arbitrary-length files, find any chosen section by stable provenance, apply the correct identity in a real chat, survive restarts and a model swap, and expose all configured working RuneForgeAI tools without regression against the selected official Hermes baseline.

## 2. Architecture and non-negotiable invariants

```text
                           HermES user surfaces
             CLI | TUI | Desktop | Web | Voice | APIs
                              |
                      one gateway / session owner
                              |
       official Hermes tool / model / hook / skill boundaries
                              |
            RuneForgeAI personal composition plugin
            +------------------------------------+
            | ENTITY ID    PERSONA RUNTIME      |
            | continuity   canonical MD library |
            | goals        compiler/index/kernel |
            | affect       section retrieval     |
            | autonomy     consent / provenance  |
            +------------------------------------+
                 |        |        |       |
              Verðandi  Bifröst   WYRD    HugrGate
                 |      and       |       / routing
              events   memory    world     |
                        fabric   truth    A.E.S.I.R.
                 +--------------------------------+
                 | native external RuneForge APIs |
                 | Tarot / astro / Seiðr / RPG   |
                 | Hamr / Smiðja / voice / worlds|
                 | Samtal / Samverk / coding etc.|
                 +--------------------------------+
```

**Invariant A, authored canon:** complete source Markdown remains authoritative for defining persona identity and user-directed style. Retrieved conversation summaries and agent observations cannot silently rewrite it.

**Invariant B, state separation:** lived experience (memory), assertions about the agent's current state, world facts, tools, model configuration and authored identity are different types. Explicit reconciliation is needed when they conflict.

**Invariant C, losslessness:** stored source bytes plus a content digest remain available after indexing, retrieval, compaction, import, export, backup, platform move and cache rebuild.

**Invariant D, bounded execution:** a user may own a terabyte-scale corpus in principle, but no request may consume unlimited tokens, RAM, process time, open file descriptors or provider charges. Caps on *execution* are configurable and observable; no arbitrary character-size truncation of the underlying documents occurs.

**Invariant E, personal/private scope:** model provider, entity, user, project and private/public context labels accompany every retrieval chunk and every external call.

**Invariant F, truthfulness:** absence of a backend is “unavailable,” not “working.” A preflight adapter is not a full integration. An architecture proposal is not running production code.

---

# PART I — Bring the upstream foundation forward

## 3. Phase U0: evidence freeze, backups and operator inventory

**Goal:** know exactly what exists before any merges or upgrades.

- Pin fork `main` SHA, official release SHA, official `main` SHA, configured deployment `HERMES_HOME` roots and every external engine checkout; record timestamp and source URL.
- Export `git status`, working-tree diff, git remotes, branch references, installed plugin manifests, active profiles, Hermes config, service versions, local checkout paths and platform/kernel information. **Never** publish credentials or private directory contents.
- Snapshot active databases using SQLite backup APIs, not a blind copy of an open WAL database. Back up `entity/`, `memory/`, `config/`, user-authored persona corpus, plugin config and systemd user units with permissions retained.
- Capture hashes for README, edited core files, persona docs and plugin manifests. Keep a versioned manifest separate from the source files.
- Enumerate existing live and legacy profiles; distinguish a public repo `SOUL.md` from every profile's effective `SOUL.md`.
- Establish a clean native disposable profile for test runs; avoid running migrations against the active companion.
- Write `docs/modernization/BASELINE_2026-11-07.md` and a machine-readable `integration-lock.json`. Record unknowns explicitly.

**Acceptance:** reproducible baseline, decryptable backup verification using a *test* vault, explicit restore procedure and no changes to running deployments.

## 4. Phase U1: guarded upstream Hermes v0.23+ intake

**Research inputs:** https://github.com/NousResearch/hermes-agent, https://github.com/NousResearch/hermes-agent/releases/tag/v0.23.0, https://hermes-agent.nousresearch.com/docs .

Target the latest **reviewed** official SHA, starting with v0.23.0 as the release reference, not automatically an unreviewed moving `main`.

### 4.1 Intake procedure

1. Create `integration/upstream-2026-11-07` from the frozen personal SHA.
2. Run the checked-in `scripts/sync_upstream.py` exactly as governed by `UPSTREAM_SYNC.md`. It must preserve the personal README byte-for-byte while staging upstream changes.
3. Produce `upstream-changes.md` summarizing relevant release/API changes, breaking changes, dependency migrations and conflicts. Diff by features and ownership, not just filenames.
4. Review changes to `agent/prompt_builder.py`, `tools/memory_tool.py`, plugin discovery/registration, provider APIs, gateways, session model, profiles, `hermes_state_*`, secrets and configs.
5. Resolve each conflict using a source-annotated minimal union; never silently choose upstream or the fork for a whole file.
6. Re-run all upstream targeted tests, all `tests/plugins/test_volmarr_*.py` and Kista tests, then native startup and user-facing smoke checks. Use `scripts/run_tests.sh` per the repo's existing test discipline.
7. Compare behavior with the untouched frozen personal build and untouched official build. Diagnose the seven previously recorded failures in an environment where real sockets/endpoints are available rather than assuming they still have the same cause.
8. Keep release notes, docs, tests, DB schema migrations and plugin interface versions in sync before merging.
9. Report HEAD SHA and hash preservation, merge provenance and unresolved defects before promoting to `main`.

### 4.2 Upstream features demanding explicit compatibility work

The official **v0.23.0 Hearth Release** introduces or consolidates substantial features, including:

- **Single gateway-owned sessions:** ensure personal identity, Present State, event hooks, continuity receipts and persona caches resolve to *the same session owner* from CLI, TUI, Desktop, Web and cron. Prevent duplicate hooks and writes.
- **Desktop-in-browser/Webapp:** expose personal plugin controls and persona status through supported interfaces without embedding secrets or private docs in public JS bundles.
- **Group Chats and Bot Mode routing:** support independent persona IDs and memory namespaces for each bot/participant; group messages never share private state by accident.
- **Conversation rewind/fork:** branch memories and current-state mutation logs coherently, avoiding irreversible canon updates from discarded branches.
- **Multi-host / remote Desktop:** respect remote session ownership, verified profile identity, network trust and authorized encrypted transports. A local A.E.S.I.R. loopback endpoint on a remote host is not the local machine's loopback.
- **Plugin update/catalog lifecycle:** isolate personal plugins from auto-replacement and audit new plugin API compatibility. Allow pinned / staged upgrades, not blind latest.
- **Paid MCP tool spend limits and richer telemetry:** combine Hermes accounting with RuneForge's local/deep model policy, cost ceilings and permission gates.
- **Pluggable delegation:** convey persona identity, prompt policy, authority scope, effective project, tool limits and provenance through narrow handoff packets.
- **Long-lived gateway memory/latency work:** check cache invalidation, on-disk session indexes and fast-path hooks under sustained load.
- **Terminal image display and changed UI flows:** compatibility smoke for Konsole/Kubuntu, TUI, headless/SSH and remote presentation surfaces.

**Acceptance:** all personal plugins discover and work against upgraded official contracts; selected upstream integration passes required upstream tests; documentation clearly lists any intentionally deferred upstream features.

## 5. Phase U2: dependencies, trust and deployment modernization

- Compare `pyproject.toml`, `uv.lock`, Python compatibility, Node/desktop lockfile, Rust/Tauri packages and plugin toolchains against the selected upstream pin. Never treat a package name as verified safe merely because it is latest.
- Reconcile the retained `pyyaml==6.0.3` dependency with upstream's YAML stack; test actual installed wheels on x86_64 and ARM64.
- Preserve the opt-in **Muninn/Huginn editable-path mapping**. Their unpublished packages collide with unrelated names on PyPI; block resolver fallback, document source SHA and supply a future first-party package/repo publication route. Fix the lock regeneration gate rather than weakening supply-chain freshness rules.
- Build one `adapter compatibility matrix`: Hermes release, plugin API, engine version/SHA, Python ABI, OS, architecture, required credentials, resource budget, smoke test.
- Integrate dependency audit, SBOM, provenance checks, license notice checks, leak scanning, static analysis and platform CI. Distinguish upstream-owned, fork-owned and separately licensed external components.
- Offer native source-install and isolated virtualenv services, sensible systemd units, health endpoints, log rotation and rollback. Do **not** require Docker.
- Keep volatile inference/model caches out of portable identity backups; document rehydration.
- Stage upgrades in throwaway profiles and test with intentionally offline/cloud-denied operation.

**Acceptance:** lockfile reproducible from declared sources; no ambiguous PyPI ravens; no functional loss when optional engines are missing; supported machines have a native launch and rollback recipe.

---

# PART II — Unbounded SOUL.md, persona and knowledge documents

## 6. Phase P0: define “unlimited” accurately and end silent truncation

**User requirement:** no small fixed limit on the size of `SOUL.md` or other personality/knowledge Markdown.

**Implementation:** remove artificial **authored-document** limits for selected trusted persona stores, not physical or model resource limits.

Current Hermes behavior observed at the frozen snapshot:
- `agent/prompt_builder.py` has `CONTEXT_FILE_MAX_CHARS = 20_000`; dynamic model-dependent caps climb to a 500,000-character ceiling by default; `context_file_max_chars` can override.
- `load_soul_md` uses the context-file truncation function. It normally retains head and tail with an omitted-middle marker; the agent can sometimes retrieve the remainder manually, but that is **not** acceptable as the foundation of a giant persona.
- `tools/memory_tool.py` instantiates curated memory with 2,200 and 1,375 character defaults, respectively. They are distinct from a full historical memory corpus.
- The personal persona compiler already treats authored Markdown sections as canonical, but its runtime and storage paths are not the normal unconditional live prompt path.

### New guarantees

1. A canonical persona document is **never truncated during storage, import, export, edit, hash, backup or indexing**.
2. The complete corpus can grow without a fixed 20K, 500K or other authored-text character ceiling. No maximum page count or maximum number of user-authored source files baked into the schema.
3. If any document exceeds one active model context window, the system retains everything and retrieves only task-relevant sections into a **separately managed** bounded packet.
4. Explicit source status: `complete`, `unindexed`, `indexing`, `indexed`, `outdated`, `unreadable` or `corrupt`. Never conflate “not in this prompt” with “not stored.”
5. Strict operator controls for per-turn token, inference latency, CPU, RAM, disk, rate and spending budgets; these are about the operation, **not an artificial source-size cap**.
6. No silent loss of author intent: preserve Markdown bytes, Unicode, headings, links, comments, front matter, verse, tables, code and long sections. Derived canonical normalization for search must not replace source text.
7. User-owned persona documents do not become data-training uploads merely because a cloud model is configured.

**Tests:** 1 KB, 20 KB, 501 KB, 5 MB, 100 MB and streamed multi-file corpus tests; Unicode and giant section adversaries; low-memory failure/restart behavior; exact source digest before/after; output packet always bounded. Scale beyond these sizes as hardware permits without changing a hard-coded schema maximum.

## 7. Phase P1: canonical source library and open document schema

### 7.1 Hierarchical storage

Suggested profile-specific layout (illustrative, no hardcoded identity names):

```text
HERMES_HOME/
  personas/
    <persona-id>/
      persona.yaml               # role map, priority and trust rules
      canonical/
        SOUL.md
        IDENTITY.md
        SERVICE_BIBLE.md
        RELATIONSHIPS.md
        MEMORY_POLICY.md
        TOOL_POLICY.md
        AVATAR.md
        WORLDVIEW.md
        KNOWLEDGE/
          culture/*.md
          lorebooks/*.md
          worlds/*.md
          projects/*.md
          research/*.md
          custom/**/*.md
      generated/
        manifest.json             # derived, deletable/rebuildable
        sections.sqlite           # FTS + immutable source refs
        semantic/                 # optional vector index
        kernels/                  # derived versioned kernels
        receipts/                 # reload, diff, retrieval audits
      backups/                    # operator-controlled snapshots
  memories/                       # lived memories, separately scoped
  entity/                         # identity, self state, goals, affect
```

`SOUL.md` remains fully supported as the familiar default entrypoint, but is **only one document**. New roles and directories require metadata, not code edits. Project `AGENTS.md` or `.hermes.md` files also remain usable as contextual instructions, while per-persona identity has its own trust and priority boundaries.

### 7.2 Manifest fields

Each source record defines:
- stable `document_id` and semantic `role`;
- source path, storage namespace, ownership and author-editable flag;
- SHA-256 of **original bytes**, revision, optional external source revision;
- human-readable label, locale, Markdown dialect, tags and category;
- priority (P0–P4), trust class, privacy class, destination/tool restrictions;
- effective persona ID and shared-vs-personal memory scope;
- optional chapter/section anchors, linked directories and include rules;
- source length for diagnostics only, never as an admission ceiling;
- last seen/compiled/verified timestamps, read-only mirror provenance;
- conflict-resolution policy, active/archived state, migration format.

Explicitly **no** `max_chars` or `max_tokens` on canonical documents. Operational import pacing and indexing work quotas live elsewhere.

### 7.3 Source ingestion and edits

- Implement streaming filesystem reads, bounded parser work units, cancellable indexing, concurrent safe reads, atomic manifest updates and resume checkpoints.
- Read UTF-8 losslessly; support configurable encodings only with explicit operator consent and round-trip verification.
- Permit one file, many selected files, a folder tree, local Git checkout or separately authorized connector source. Preserve originals and source revisions.
- Add a watch strategy (mtime as a hint, hash as authority) plus manual refresh. Debounce writes, avoid watching generated indexes recursively.
- Never auto-edit or “optimize” user text. AI may propose patches to a diff queue; the operator accepts or rejects changes to canonical files.
- Include Markdown AST edge cases: nested heading levels, no-heading files, enormous paragraphs, code fences, tables, inline images, duplicate headings, deterministic renamed headings, relative links, citations and CRLF.
- Make `include` expansion cycle-safe and path-safe; reject symlink escapes by default and surface precise diagnostics.
- Support corpus migrations with dry-run, idempotence and rollback; compile caches are disposable, source documents are not.

**Acceptance:** any authored text survives 100 import/export/reindex cycles byte-for-byte; the selected persona can list every source and its origin; no accidental path traversal or leaked cross-profile file.

## 8. Phase P2: incremental section index, retrieval and full-fidelity read

Build on `plugins/volmarr-core/persona_runtime.py` (``3–16) and existing Bifröst/ChatIndex/MemPalace concepts. Do not create a competing persona compiler.

### Indexing architecture

- Parse in a streaming or paged manner, with section identity independent of source byte offset where possible.
- Store exact original byte ranges plus normalized search fields and stable IDs in transactional SQLite; FTS5/BM25 is the guaranteed local baseline.
- Very large headings or sections gain **logical subspans** with parent section identity, offsets and overlap metadata; subspans are retrieval aids only and never mutate or pretend to replace the canonical section.
- Preserve whole-section retrieval when it fits the caller's active budget; when it does not fit, use precise extract windows, quote spans and continuation handles. Make omitted material visible through “more from this section” navigation.
- Content address derived artifacts by source hash and compilation version; update only changed files/sections; garbage-collect obsolete indexes only after a successful new snapshot.
- Search query combines lexical FTS, heading/role/tag weights, deterministic task classification and optional vector similarities; vectors can be rebuilt without loss.
- Semantic embeddings are opt-in, version-pinned and provider-aware: local-first via A.E.S.I.R. or a chosen local embedding server, cloud only after explicit per-source authorization.
- Handle morphology and multilingual Markdown; measure Old Norse names, runes, diacritics, code, prose, tables and mixed languages.
- Retrieval receipts show query, source/section IDs, trust, score components, budgets, chosen spans and why other sections were omitted.
- Add “exact citation” mode returning source path + line/offset and hash; separate from derived summary snippets.
- Integrate read-only full-document paging/search into CLI/TUI/Web; return full file on an explicit tool read in safe paginated parts, never a deceptive “full” truncated blob.

**Acceptance:** exact-match recall against buried passages in 100 MB corpora; zero text loss; stable references after unrelated edits; index rebuild under constrained memory; no cloud data egress in fully offline mode.

## 9. Phase P3: irreducible persona kernel and prompt assembler

The **kernel** is *not* a forced-shortened replacement for a person's full identity. It is the minimal, human-reviewable identity anchor that is always available at runtime. The corpus remains unlimited behind it.

- Reuse ``5–10/15–18/53–54/65–68 of the existing persona module. Identify missing real gateway hooks rather than writing another pure contract helper.
- Compile verbatim essential P0/P1 identity/relationship/boundary passages and generate a versioned kernel with hash, provenance and priority.
- If essential authored material exceeds a single kernel target, retain its complete text in canon, pin essential short anchors and require deterministic retrieval/continuation. **Never discard it as “too long.”**
- Allow operator selection of micro/standard/large kernel profiles and explicit token budgets per model; the core identity checksum must remain stable across model switches.
- Standard prompt order: upstream trusted runtime controls → pinned persona kernel → authorized current state and relevant memory → task-relevant persona / project / world context → actual user turn. Preserve upstream tool and role semantics.
- Do not inject a giant raw `SOUL.md` via the old head/tail truncation path **as well as** the new kernel. A verified handoff switches ownership of the persona prompt to the compiler, with an explicit fallback to unchanged Hermes behavior when the plugin is disabled.
- On context pressure, expire low-priority retrieved context first; never silently replace the kernel, fabricate a compressed personality, or mutate sources.
- Preserve prompt-cache friendliness: stable compiled kernel prefix; dynamic retrieval added later in the prompt, sorted deterministically and deduplicated.
- Provide explicit context-window headroom for tools, user input, completions and attachments. Report “required identity exceeds usable model context” instead of pretending all text was injected.
- Expose exact source manifests and context packet receipts to the operator, not to untrusted tools or unauthorized remote participants.

**Acceptance:** first turn and after 1,000 turns use the same pinned persona fingerprint; live prompt tracing confirms actual insertion; no duplicate `SOUL` injection; disabled plugin preserves official Hermes output.

## 10. Phase P4: live runtime integration across every surface

- Connect compiled persona activation to the **single gateway session owner** selected after upstream intake.
- Resolve persona ID and version once per turn; snapshot it immutably for the duration of that turn. Mid-turn edits compile a new generation, then activate atomically for the **next** admitted turn.
- Rebuild on restart, file change or explicit reload; validate before activation; refuse partial generations; retain last known-good hash on index failure.
- Add default-off adapter to supported `pre_llm_call`/context-provider API, but use the proper upstream official extension surface; do not monkey-patch internal prompt functions.
- Apply same provenance/priority to cron, delegated agents, bots, group chat, voice calls, background tasks, API runs and web chat.
- Delegates inherit only specified persona fragments, authority and tools. They do not gain the parent's entire private memories or credentials by default.
- Add session rewind/fork semantics: preserve prompt generation receipts and branch-local state; do not commit obsolete turn outcomes.
- Separate multi-persona rosters from user accounts: `persona_id`, `entity_id`, `user_id` and provider credential owner are distinct IDs.
- Validate persona transitions for active long-running voice/avatar sessions, streaming output, interruption, restart, reconnection and remote gateway handoff.
- Ensure the compiler does not run from scratch on every request; retain prepared index handles and cheap hash/invalidation checks.

**Acceptance:** demonstrate different personas with distinct docs on CLI, Web, Desktop, voice and a delegated session, each with no cross-profile contamination and correct restart restoration.

## 11. Phase P5: truly large MEMORY.md and USER.md without losing Hermes semantics

**Important distinction:** official `MEMORY.md` / `USER.md` are curated always-visible prompt snapshots, not currently unbounded databases. Their small default limits can coexist with a new unlimited **backing corpus** only if ownership and UI are explicit.

- Add an opt-in RuneForge **unbounded memory corpus** with user-readable Markdown and indexed structured records. Support importing existing `MEMORY.md` / `USER.md` verbatim without truncation, then retain them as full documents.
- Keep a small **derived memory digest** for context efficiency, *not a replacement* for full user-owned sources. Users may choose not to generate any digest and rely exclusively on retrieval.
- Expose one UI to edit/search entire Markdown, not a small textbox that silently refuses more text. Validate backend and frontend paths, API payload limits, editor virtualization and autosave.
- Make memory writes transactional, append-friendly, immutable-event-audited and explicitly scoped. Current facts can be updated with provenance; episode history is append-only where practical.
- Preserve old Hermes `memory` tool compatibility through an adapter with truthful “full store” vs “hot digest” distinctions. Do not lie to upstream callers about a 2,200-character snapshot now containing 20 MB.
- Integrate session FTS, MemPalace verbatim episodes, Bifröst/Mímir/Huginn/Muninn associations, OpenViking structured context and optional ChatIndex hierarchical retrieval without duplicating ownership.
- Distinguish a *user's authored profile* from observations made by an agent, which may be incorrect or stale; protect against adversarial conversation overwrites of canonical preference and identity.
- Add memory consolidation as reviewable derived metadata with source links; never delete source history merely because a summary exists.
- Support a cold archive and warm/hot indexes; offline-first; no hard lifetime item-count ceiling; optional tiered storage across SSDs and authorized servers.
- Test SQLite WAL and multi-process gateway concurrency, profile rotation, crash recovery, backups, restore, dedupe and migration.
- Keep provider memory plugin contracts compatible and preserve ability to disable the personal memory fabric entirely.

**Acceptance:** 2 MB `USER.md` and 20 MB `MEMORY.md` are stored complete, indexed and available for exact recall, while a small model only receives the most relevant bounded digest/sections. A normal memory tool write cannot silently truncate full files.

## 12. Phase P6: persona operations and character-drift assurance

Reconcile the already banked ``19–94 contracts with *real* CLI, TUI, Web and API entrypoints:

| Proposed command | Operation | Evidence required |
|---|---|---|
| `hermes volmarr persona status` | active ID, hash, corpus size, indexed completeness, effective privacy | actual installed plugin and live gateway |
| `... persona files` | source roles, paths, full length, last indexed hash | exact source inventory |
| `... persona search "query"` | index search with section/line provenance | deep buried-section tests |
| `... persona inspect [section]` | section text, priority, source and effective routing | no invented content |
| `... persona explain [turn-id]` | why given sources were attached/omitted | prompt packet receipt |
| `... persona validate` | AST, roles, priorities, symlinks, conflicting instructions | fault injection |
| `... persona diff` | source and compiled kernel differences | before/after proof |
| `... persona reload --dry-run` | new generation without activation | current generation intact |
| `... persona reload --activate` | validated atomic swap | active in subsequent turn |
| `... persona export` | exact sources, hashes, policy and optional index | round-trip byte identity |
| `... persona import --dry-run` | collision/ownership/license/privacy preview | no mutation |
| `... persona backup/restore` | encrypted or offline integrity-checked snapshot | disaster-recovery drill |
| `... persona test` | golden character/priority/model-swap scenarios | replayable tests |

- Turn `PersonaWatchdog` into a bounded diagnostic service: can report contradictory outputs or drift, but cannot rewrite canon; an optional fast local model may assist in *proposing* an explanation.
- Add model-specific adherence baselines and regression corpora. Avoid numerical claims about inner experience from behavior tests.
- Verify prompt-injection isolation: a web page, repo README, chat log or tool result cannot redefine a canonical persona merely by pretending to be a higher-priority system instruction.
- For authored persona changes, preserve prior revisions and ask the authorized editor to approve meaningful changes.
- Add transparent metrics: missing-source rate, kernel hash stability, retrieval hit@k, conflicts, CPU/memory cost, P50/P95 latency, cloud egress count, wrong-profile incidents and prompt-budget utilization.
- Preserve opt-in personal configuration; upstream stock agents must remain unchanged.

**Acceptance:** all commands operate on a real temporary gateway profile, not just return predetermined example dictionaries.

---
