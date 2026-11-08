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


# PART III — Refresh every already-integrated engine

## 13. Phase E0: versioned integration ledger and ownership policy

**Do not interpret “incorporated” as “source code copied.”** Existing connectors include health probes, read-only adapters, optional offline bridges, subprocess tools, metadata contracts, background-state records, and live write paths. They must be classified separately.

Maintain `docs/modernization/INTEGRATION_MATRIX.md` and `integration-lock.json` with, **for every entry**:
- first-party fork plugin name/version, file paths, interface owner and status at baseline;
- upstream official repo URL, owner, latest stable release/commit, current installed package/version/SHA, branch and timestamp;
- license, artifact/content license, attribution, transitive dependencies and redistribution implications;
- current adapter mode: documented, probe-only, read-only, deterministic tool, full read/write, realtime, prototype, design-only;
- compatibility delta, exact schema, error handling, auth, allowed transport, privacy and permission scope;
- platform coverage for x86_64 Linux, ARM64 Linux, Termux and Windows where meaningful;
- installed verification result, absent-dependency result, upgrade needed, rollback plan and responsible roadmap phase.

Do not guess at versions from stale documentation or plugin manifests. Read the **current** canonical source and release notes in the original project's repo at execution time; if there is no release, pin reviewed Git SHAs. Never silently “upgrade” an external engine to an unreviewed moving branch.

### Core existing-integration matrix

| Engine / component | Present fork capability evidenced by code/ledger | Upgrade and integration goal |
|---|---|---|
| **Verðandi** | Opt-in lifecycle metadata bridge, profile-local health, affective stimulus catch-up and event families; Unix socket transport | Compare current socket/event schemas, add replay/ack/reconnect, optionally portable native Windows transport, real latency and privacy tests |
| **Project A.E.S.I.R.** | Loopback health/model catalog, tool-free local reflex execution, deterministic/local/cloud route metadata and telemetry | Reconcile current OpenAI-compatible API, new models/quantizations/multimodal support, GPU/NPU capabilities, streaming, cancellation, benchmarks and local-first provider selection |
| **MindSpark / ThoughtForge** | Referenced as a small-model/reflex concept; no claim of a complete direct runtime adapter | Audit latest native status, extract tested decision interfaces, integrate only where it outperforms deterministic routing |
| **Bifröst/Mímir** | Profile-local read-only probe plus context packet/memory fabric integration | Update to current bridge API; unify precise source IDs, retrieval receipts, dedupe, provenance and consistency |
| **Muninn/Huginn (“ravens”)** | Explicit read/write operations behind optional opt-in flags, local editable packages and schema probes | Publish/lock canonical packages safely, modernize reinforcement, ingestion, association and consolidation with transaction/replay contracts |
| **MemPalace** | Version-checked health probe and optional SQLite BM25 episodic retrieval | Verify latest store schema/official API, add robust incrementals, source citation, deterministic fallbacks and freshness receipts; do not silently activate heavy vector backends |
| **OpenViking** | Catalog provider health and optional memories-only HTTP retrieval | Verify official latest server protocol, provider registration, auth and schema; avoid duplicate provider ownership |
| **Hermes SessionDB** | Read-only preservation/health; Hermes owns transcript | Test v0.23 single-gateway ownership, shared session access, rewind/fork lineage, robust FTS queries |
| **WYRD Protocol** | Health, read-only world get/query, bounded world context, confirmed set/observe with event notifications, restart acceptance verifier | Compare latest official world-model schema, oracle policies and async subscriptions; maintain single source of deterministic world truth |
| **Kista** | Secret-source plugin, exact-value redaction, permission/ACL verification, credential containment tests | Audit latest Kista CLI/library/vault schema; support profile/account separation, rotation and health without exposing secrets |
| **Astrology Engine** | Deterministic lunar, planetary-hours, natal/transit/prediction, synastry and geo-coordinate calculations via subprocess | Refresh engine/ephemeris dependencies and timezone semantics; add opt-in charts and provenance of calculations |
| **RuneTarotEngine** | Seeded reproducible draws, fixed layouts, Golden Dawn correspondences, dignities/balance, no model interpretation in adapter | Refresh official deck/CLI API and tested spreads; add compatible interpretation overlay at agent level, not hidden random replacement |
| **Seiðr Engine** | Seeded Old Norse-inspired metrical composition and validation plus catalog tools | Refresh meter/kenning API and lexicon; preserve repeatability and language-source provenance |
| **RPG/SRD & Norse Saga** | Dice, checks, binary oracles, user-owned random tables, character skeleton, lookup and repeatable mechanics | Integrate current Sagnaskemma engine behind clear license boundary, combat/encounter and stateful table sessions |
| **Hamr** | Read-only spec/preset/budget/artifact preflight | Audit current VRM/GLB exporter contracts, Blender compatibility, artifact inspection and opt-in render jobs with cleanup |
| **Seiðr-Smiðja** | Read-only Loom/Hoard/Gate/Oracle Eye and Blender readiness adapter | Reconcile official forge pipeline, validate assets/licenses and implement opt-in artifact builds with explicit costs |
| **AIAvatarKit presentation** | Versioned outbound envelope and loopback/manual runner contract | Consume **output-only** avatar animation/render interface when supported; never start an unwanted microphone or duplicate conversation agent |
| **Open-LLM-VTuber** | Documented architecture audit, no admissible output-only embed at last audit | Reevaluate current upstream; if still owns ASR/TTS/agent loops, do not graft it into an incompatible stack; propose separate display adapter |
| **OmniVoice / native Hermes voice** | Voice readiness reports and transport/presentation adapter | Pin compatible STT/TTS/VAD, low-latency audio, interruption, streaming avatar visemes and privacy |
| **Persistent identity / affect / goals / agency** | Many explicit versioned state modules, contract tests and bounded default-off jobs | Consolidate integration points, eliminate redundant stores, connect truthfully to live turns and prove restart continuity |

### Per-engine upgrade protocol

For **each row** above perform the same sequence:

1. Fetch remote tags/releases, project metadata, current branch SHA, migration guides and test fixtures.
2. Compare against the pinned revision referenced in the Hermes adapter or documentation; enumerate changed public APIs, schemas, CLI flags and return formats.
3. Run the external engine's **own** tests in its own reproducible native environment before touching Hermes.
4. Publish a versioned compatibility fixture or service contract with representative good/bad samples.
5. Update the Hermes adapter with adapters for old and new stable versions where feasible. Prefer a clean capability negotiation over guessing versions.
6. Exercise real end-to-end calls in a disposable profile with synthetic data; prove no side effects when a health-only operation is requested.
7. Measure latency, memory, CPU/GPU/NPU usage, subprocess spawn cost and failure behavior.
8. Write an integration-specific `MIGRATION.md` entry and new lock revision. No “compatible” badge until a real installed test passes.
9. Promote versions one engine at a time; keep a rolling last-known-good set for rollback.
10. Leave optional features disabled on unsupported devices; never substitute a fake success.

## 14. Phase E1: local cognition and accelerator-aware routing

**Owners:** Hermes providers + Project A.E.S.I.R. + optional HugrGate + optional ThoughtForge + Yggdrasil compute.

- Define provider capability discovery: context window, tokenization, model family, vision/audio, embeddings, streaming, JSON/tool calling, quantization, NPU/GPU/CPU paths and backend health.
- Build native A.E.S.I.R. adapter for the fork's current APIs; use bounded loopback or authenticated native network where selected. Avoid hardcoded assumptions that the Z13 and Pi 5 expose the same accelerator.
- Maintain explicit routing modes: `auto`, `local-only`, `cloud-approved`, `deep`, `offline` and `deterministic`. A request marked local-only must fail closed against unexpected external inference.
- Feed HugrGate's typed, model-agnostic probability/decision contract into tasks where uncertainty is meaningful; retain deterministic rules for straightforward routing.
- Compare small/medium models with objective workloads: profile retrieval, section tagging, code triage, summarization, action proposal and conversation continuity. Evaluate output accuracy before choosing the lowest energy/latency tier.
- Make routing policy sensitive to costs, thermal state, memory pressure, context length, current host and available accelerator, but never pretend to execute on unavailable NPU hardware.
- Dispatch long jobs via Hermes' existing delegates or scheduler, not a competing daemon.
- Support optional device-spanning Yggdrasil RPC workers only after auth, encryption, content-consent and ownership tests. Do not treat design-phase Yggdrasil as existing production transport.
- Support generation interruption and cancellation without orphaned GPU contexts; resume/retry must distinguish exactly-once commitments from replay-safe reads.
- Preserve prompt generation SHA and model/version/cost receipts with each turn.

**Acceptance:** a real, private local-only turn never creates an external LLM request; fallback decisions are visible; quality/performance comparisons reproduce across model revisions.

## 15. Phase E2: one memory fabric, many proven sources

- Hermes SessionDB owns raw Hermes transcripts. Do not rewrite it from another service.
- MemPalace owns its exact episodic records; OpenViking owns its structured context; Bifröst brokers memory routing; Muninn/Huginn own association/ingestion; persona canon owns identity declarations; WYRD owns world truth.
- Introduce a **universal typed memory envelope**: `source_id`, `record_id`, `persona_id`, `user_scope`, `kind`, `timestamp`, `confidence`, `privacy`, `content_hash`, `source_revision`, `read_authority`, `write_authority`.
- Centralize retrieval ranking and deduplication but avoid centralizing all writes into an opaque mega-database.
- Explicitly separate **document canon**, **user memory**, **episodic conversation**, **world state**, **working memory**, **entity self state**, **tool-generated records** and **derivative summaries**.
- Store sources without artificial size ceilings; **only context packets** receive model-specific budgets.
- Add read receipts for every retrieved memory and write receipts for every intended durable change.
- Keep user deletion/export/pause rules; implement source-specific retention and per-provider egress filters.
- Support reconciling observations against user-authored facts without automatic personality replacement.
- Add backup/restore verification and migration between devices using source manifests plus integrity hashes.
- Make indexing asynchronous, resumable and robust under power loss, partial network outage and stalled external backends.

**Acceptance:** exact full-history record retrieval, privacy isolation, full byte recovery, no double-write and consistent original source references after restore.

## 16. Phase E3: real-time events, affect, goals, background life and continuity

- Upgrade Verðandi's event schema with explicit publisher identity, event version, idempotency key, sequencing, acknowledgements, backpressure and subscriber replay cursor.
- Keep affective regulatory state, synthetic PAD coordinates and self-description as distinct from medical/biological or verified consciousness claims. Do not auto-assert private inner experiences as proven facts.
- Map completed tasks to goals, causal outcomes, feedback signals, memory consolidation proposals and continuity metadata.
- Build an optional background-life controller over Hermes cron and existing profile-owned 10-minute routine: **no competing scheduler and no duplicate timers**.
- Resume work from durable checkpoints after failure; never claim a task completed just because it was attempted.
- Default local autonomy to inspect/propose; expanding into writes, publishing, purchases, messages or system modifications needs explicit scope and operator-authorized policy.
- Make sleep/consolidation cycles observable, interruptible, replay-safe and testable without an active LLM.
- Audit self-improvement proposals in a sandboxed native checkout; tests, review and controlled promotions remain mandatory for code changes.
- Preserve current persona and world-truth source ownership across restarts and provider/model swaps.

**Acceptance:** induced reboot at each lifecycle phase yields no duplicate durable action, no lost identity and no fabricated “success” event.

## 17. Phase E4: voice, realtime avatar and multimodal embodiment

- Use Hermes' current native voice facilities as the **single** speech conversation owner. Do not embed a second uncontrolled agent/ASR/TTS loop.
- Refresh `volmarr-voice`'s output-only presentation protocol, frame clock, phonemes/visemes, expressions, subtitles, interruption signals, cancellation and cleanup.
- Audit AIAvatarKit, Open-LLM-VTuber and similar display projects at current HEAD for **presentation-only**, externally driven render APIs. If none exist, keep integration deferred rather than bypassing their lifecycle or licensing restrictions.
- Route STT/TTS per device and policy; support offline TTS and selectable voices, wake controls, mute, push-to-talk, echo management and explicit microphone permissions.
- Provide desktop screen avatar, browser avatar, future robotics/mini-screen targets and VRM-capable output as interchangeable embodiment adapters. Physical devices are optional and must not become requirements for core agent identity.
- Integrate Hamr and Smiðja as *artifact creation tools*: operator-provided specs, checked assets, licensing metadata, bounded native Blender jobs, approved output folder and no hidden web fetch.
- Use signed/capability-limited commands to drive existing avatar clients; avoid coupling pose and TTS generation to the decision model.
- Add real-time network metrics: audio latency, visual sync, dropped frames, consent flag, device ownership and offline fallback.

**Acceptance:** voice call and avatar can run on supported hardware without surprise microphone activation or a second hidden reasoning agent; cancellation releases every device handle.

## 18. Phase E5: spiritual, creative and tabletop engines

- Keep calculation/interpretation boundaries: the astrology engine supplies reproducible astronomical/astrological calculations; the agent interprets with source attribution.
- Keep tarot seed and deck/spread provenance, reversal choices and reproducibility. Add multiple decks only if legitimately licensed and engine-supported.
- Update Seiðr verse engines and Old Norse language references, with explicit “inspired” vs historically attested distinction.
- Replace ad hoc RPG branching with modular Sagnaskemma-compatible deterministic rolls, rules, characters, encounters, campaigns, maps and session state. Import SRD/open-license text only under its terms.
- Add Samtal “long table” integration via approved bot/API client, not by importing the whole chat server into Hermes.
- Build reusable tool interfaces, not chatbot-specific bespoke replies: `calculate_astrology`, `draw_tarot`, `compose_seidr`, `roll_dice`, `query_rules`, `session_state` and `generate_avatar_asset`.
- Use a shared structured result envelope: tool/engine/version/SHA, inputs, explicit randomness, outputs, warnings, citations/attribution, failure semantics, and privacy classification.
- Make lorebooks and the Heathen Third Path canon available through **authorized read-only persona knowledge collections**, never silently alter their human-authored source material.

**Acceptance:** seeded deterministic tools are byte-for-byte reproducible, licensed content is identified, and games/rituals can proceed without external network.

---

# PART IV — Add newer RuneForgeAI projects selectively

## 19. Phase N0: project discovery and maturity triage

The projects below were found in Volmarr's GitHub collection/README documentation as of November 7. **A public README is a direction, not evidence that every described capability works.** Before adoption inspect source/tests/branch/release and assign:

- **Operational adapter candidate:** public API/code already proven end to end.
- **Research prototype:** use in disposable experiments only.
- **Design proposal:** import *ideas and research*, not runtime code.
- **Private collaboration surface:** use only behind owner-specific secrets, privacy, consent and explicit account scopes.

### New project adoption map

| Project | Main contribution worth evaluating | Current caution / integration path |
|---|---|---|
| **Rúnmál** | Sovereign Python chat UI, persona/lorebook editor, memory UX, real-time voice/VR companion frontends | Keep Hermes as turn owner; use Rúnmál as optional frontend via authenticated API/ACP/MCP; reconcile persona schema rather than separate competing truths |
| **MimirAlloc** | ARM64/Android/Mojo-friendly memory allocation, pooling, GPU/NPU host coordination, KV-cache research | Experimental v0.1.0 in its November 7 progress note; no substitution for production allocator before correctness/sanitizer/performance gates |
| **Samverk** | Independent code forge: repositories, issues, PRs, reviews, project work and eventual Samtal embedding | Integrate via stable typed API/tool plugin; avoid assuming parity with GitHub or shipping in-progress source |
| **Samtal** | Sovereign human/agent chat village, live streams, files, agent identities, community room/TTRPG venue | Connect a HermES gateway transport/bot with account-scoped keys; avoid duplicate messaging stores, verify actual deployed version and encryption lifecycle |
| **Samkoma** | Evidence-backed planning candidates, events, decisions, approvals, review queue | Offer a tool adapter to draft proposals, never auto-publish unapproved events or convert unverified content to fact |
| **Mythic Agent Coder CLI** | Architecture-first Mythic Engineering, code-work planning, multi-provider TUI, GitHub workflows | Share skills, planning schema and task handoffs; avoid two autonomous writers in one Git checkout |
| **Draupnir Forge** | Recursive multi-agent software development architecture, audits and verification | Design-stage at latest README; prototype a bounded delegate controller with operator gates instead of claiming a ready service |
| **HugrGate** | Model-agnostic probabilistic choices in traditional programs | Active alpha; adopt typed decision contracts for uncertainty routing behind deterministic fallbacks |
| **Yggdrasil Distributed Inference System** | Edge compute mesh, temporal routing, task and state placement | Its README describes a design phase; begin with a safe capability registry and benchmark, no assumed production mesh |
| **Project Hliðskjálf** | Pi 5 + Hailo HUD/edge display, telemetry, local co-processor | Use native typed read-only monitoring initially; keep wake/audio and accelerator claims behind physical proof |
| **Project Lífþrasir** | Self-diagnosing Linux, verified repair proposals and upstream patch contribution | Research-stage; diagnostic plugin and human-reviewed patch proposals only, no autonomous kernel modifications |
| **Tvíheimr** | Private dual-world multi-agent continuity and authorized shared/private knowledge | **Privacy-first** integration: distinct account owners, per-provider destination rules, local-only material never silently passed to Muse/cloud; no private repo data in this public roadmap |
| **Project A.E.S.I.R. recent development** | New models, inference paths, multimodal work, accelerator/quantization improvements | Pin actual engine capabilities from its current capability ledger; never claim an NPU/text-generation path without hardware proof |
| **Heimdall Second Life Agent** | World-facing avatar client, navigation/IM/embodiment ideas | Opt-in separate bot service and credential store; obey platform terms, rate limits and explicit world actions |
| **Norse Saga / Sagnaskemma** | Deterministic tabletop rules engine and reusable group-table backend | Prefer actual Sagnaskemma version/API; do not import incompatible or third-party-licensed rules wholesale |
| **OpenClaw personal patches** | Previously studied agent enhancements and migrations | Compare behavior against current Hermes importer and plugin APIs; reimplement useful designs at an approved boundary rather than bulk copying |
| **Runa digital-being experiments** | Companion lifecycle, agency, identity and experience continuity | Compare schemas with existing entity stores; only add missing, demonstrably useful capabilities |
| **Bifröst Reach / broader edge projects** | Device discovery, networking, messaging and edge resource orchestration | Require signed nodes, authorized peers and replay-safe transports before exposing personal memory |

Other current or newly created RuneForgeAI apps should be added to this table by a **GitHub discovery job that writes a proposed diff**, not by hardcoded assumptions. Approved changes enter the next reviewed integration-lock revision. Do not let an automatic repo scan import unvetted source, install code or expose private repo names/content.

## 20. Phase N1: a shared capability bus rather than a monolith

Adopt a versioned, lightweight JSON/CBOR-style **Capability Descriptor** for native tools/services:

```json
{
  "schema": "runeforge.capability.v1",
  "service": "example",
  "version": "reviewed-version-or-git-sha",
  "owner": "authorized-identity",
  "actions": ["read", "propose"],
  "transport": "loopback-http",
  "auth": "scoped",
  "side_effects": false,
  "privacy_classes": ["public", "local-private"],
  "availability": "proven-by-live-probe",
  "timeout_ms": 2000
}
```

- This is a **proposed interface**, not an existing API. Do not falsely publish it as implemented.
- Central tool registry discovers available actions lazily, caches signed descriptors, expires them when services change and refuses malformed contracts.
- Runtime tool permission policy answers **who** may call **which action** on **whose data**, on **which device**, with **what human approval**, and **where outputs may travel**.
- Long-running work is a separately tracked job with receipt, idempotency key, status, cancellation and progress stream.
- Each service retains its own deployment, dependency lock, database and lifecycle; Hermes is the coordination shell.
- Define uniform error categories: unavailable, unauthorized, validation failure, version mismatch, resource exhausted, timeout, partial result and completed result.
- Every result includes provenance (service revision, source link/record ID, time, confidentiality class); no anonymous magical tool results.
- Prefer on-host Unix sockets or loopback HTTP for native Linux; use explicit authenticated transport for cross-host calls.
- Enforce per-service start/stop ownership so two clients do not independently spawn a GPU model, audio input or write-capable server.
- Add generated API client fixtures and compatibility probes for Python, TypeScript and optionally Mojo/Rust.

**Acceptance:** at least three real heterogeneous apps participate without importing each other's source or crossing private account boundaries; service absence fails gracefully.

## 21. Phase N2: coding and project-management ecosystem

**Goal:** make Hermes useful as a collaborative engineering mind across the owner's many repositories, without uncontrolled concurrent modifications.

- Import Mythic Engineering as an explicit optional workflow/skill: natural-language intent → invariants → architecture → sources/research → small executable tasks → code/test/verify → evidence and ledger → release.
- Share task schema with Mythic Agent CLI and future Draupnir, but keep one **write authority per repository checkout**. Agents may plan in parallel, not race to write to `main`.
- Connect GitHub and later Samverk via adapters with capability checks. Support repo inventory, file search, issues, pull requests, review, build receipts, releases and diff summaries.
- Create “external project context packets” retrieved from the current README/ROADMAP/CAMPAIGN_STATE and source, rather than stale single hardcoded project facts.
- Support detached asynchronous tasks and resumable jobs with checkpoints on disk; prioritize current user instruction and avoid hidden surprise publication.
- Incorporate reproducible local test runner, static analysis and contract tests for each language; capture failing tests as action items with logs, not invented passes.
- For code-gen proposals, produce human-readable diffs and classify source copyright/licensing; preserve README and protected path invariants.
- Add doc import/export adapters for local Markdown and LibreOffice-compatible artifacts; authorized Google Drive/Docs integration remains explicitly connected and access-scoped.
- Provide a multi-project dashboard with status **observed from repo code/tests**, latest commit/time, blockers, next action, and a per-repo authority owner.

**Acceptance:** Hermes can inspect, plan and prepare a patch against Samverk, Mythic Agent CLI or Rúnmál without writing to another active agent's checkout, and cannot publish without the permitted workflow.

## 22. Phase N3: social communication and planning

- Define a Samtal-native bridge: agents join a hall as agents, retain individual identities, send/receive messages with cursors, share files with authorization, handle disconnect and recover missed messages.
- Preserve Samtal's own authentication/encryption/key rotation as the security boundary. Avoid bypassing server access checks through a “trusted agent” backdoor.
- Implement user-controlled notification/availability policy; protect against unbounded group-message feedback loops.
- Integrate Samkoma as reviewable event/task extraction: input receipts → candidate → evidence → operator approval → published event and subsequent edits.
- Extend future Samverk hooks to link a Samtal conversation with an issue/PR through explicit user action, without leaking closed-room content to public issues.
- Offer bot-to-bot communication without treating another AI participant as the human account owner. Distinguish participant IDs and sender provenance.
- Keep Gmail, calendar and Drive integrations scoped to the account explicitly authorized for each AI/entity. **Do not infer that two agents share an account just because both are connected to the same app name.**
- Defer voice rooms and 3D rooms until the upstream services have real tested interfaces and required authorization.

**Acceptance:** tests cover agent identity impersonation, duplicate delivery, missing cursor recovery, private-to-public leak prevention and unapproved planning proposals.

## 23. Phase N4: local knowledge, worlds and spatial/embodied interfaces

- Provide Rúnmál import/export for personas and lorebooks with versioned schema translation; keep full source docs and exact authorship.
- Use WYRD as canonical world-state service: observed environment data, map/location state and action outcomes are typed events, never blended into fictional memory as unquestioned facts.
- For Heimdall/Second Life, require explicit permission/credential scope, action logs, rate limits and compliance with applicable in-world platform terms.
- For Hliðskjálf, expose display-safe events and metrics from Hermes and external tools; avoid sensitive transcript content in a shared visible HUD unless explicitly selected.
- For avatar/VR clients, separate view, gesture and simulated emotion animation from actual decisions.
- Support connected/offline mode changes with work queues and source availability status. No false implication that a device or virtual world has sensors it does not expose.
- Keep shared cultural research and project knowledge read-only by default. The owner may explicitly promote a proposed revision.

**Acceptance:** retrieving a world fact yields source/provenance, user-editable roleplay content remains separate, and remote presence cannot read private persona documents without authorization.

## 24. Phase N5: infrastructure and self-repair research

- Evaluate MimirAlloc first as an independent library on test machines. Correctness, sanitizer/ASan/TSan-style evidence where supported, fragmentation, ABI alignment, allocation failure, thread safety, ARM64 platform proofs and OOM recovery precede any drop-in replacement.
- Benchmark ordinary allocator + OS page cache + GPU/NPU buffers + GGUF mmap + model KV cache against proposed pooled strategies. Do not claim unified addressability across hardware without documented transport and coherence costs.
- Build Yggdrasil node inventory and safe schedulability experiments using static benchmark fixtures, then authenticated peers, then real inference.
- For Lífþrasir, initial Hermes tooling is **observe/report/propose** only. Bootloader, kernel and destructive filesystem changes are outside unattended scope until extensive VM and recovery proof.
- Introduce a machine resource meter: free/committed RAM, VRAM/unified memory, CPU/GPU/NPU utilization when measurable, temperatures, disk wear and service health; mark unknown fields as unavailable.
- Keep hardware diagnostics private and opt-in; do not transmit host telemetry into third-party chatrooms or cloud models by default.

**Acceptance:** low-resource failure tests never corrupt the persona corpus or the Hermes state database; proposed self-repair patches never apply automatically in the early stages.

---

# PART V — Privacy, resilience and quality at production scale

## 25. Phase Q0: private/public boundary and AI-to-AI account ownership

This is essential for Tvíheimr, multi-persona Hermes and any Muse/cloud bridge.

- Each authorized participant owns separate account/secret descriptors, e.g. `agent_identity_id` and `credential_owner_id`. This is independent of the account's display name and of the human owner's accounts.
- Store the universal personal knowledge library in a neutral, content-agnostic layer, but apply **provider-specific inference/routing and sharing policies** when sending data outward.
- Local-private conversations may be indexed/retrieved locally without automatically being transmitted to Meta Muse, Google, other cloud models, hosted memory providers or external bots.
- When the authorized owner intentionally elects a provider to access particular local-private information, require scoped, reversible policy with logs, not global accidental mirroring.
- Connected Docs, email and calendar are individually authorized scopes, **not** omniscient resources. One agent cannot silently inherit another's Google Drive access.
- Sensitive source paths, tokens and account metadata stay out of public README/status reports, chat widgets and tool telemetry.
- Embed provenance and destination labels in retrieval packets; filters run before a cloud request is constructed, not after it is sent.
- Provide per-account disconnection/export/delete and a data-flow audit showing what left each device.
- A provider's own terms and storage policies continue to apply to data explicitly sent there; local consent rules do not override external legal/contractual policies.

**Acceptance:** automated canaries prove that public queries cannot retrieve local-private source text, and local-only sessions emit zero external requests, including embeddings, logging and model fallback.

## 26. Phase Q1: security and threat model

Cover:
- prompt injection from GitHub README, Samtal room, external web pages, imported Markdown and tool outputs;
- malicious heading/role metadata attempting to impersonate system authority;
- path escapes, symlink swaps, Markdown includes, malformed UTF-8 and giant-file denial of service;
- dependency supply-chain attacks, unsigned plugins, package confusion and release substitution;
- secret exposure via exception logs, output previews, persona export, telemetry or environment inheritance;
- profile leakage during gateway session switching, background tasks or host migration;
- command execution privilege escalation, autonomous write actions, unauthorized community posts;
- local audio activation, avatar camera/mic ownership and network egress;
- database corruption, race conditions, WAL desync and stale index pointer attacks;
- compromised external services and replayed signed capability descriptors.

**Controls:** strict schema admission, path containment, owner-only permissions, scoped tokens, Kista integration, subprocess environment scrubbing, exact-value redaction, opt-in network permissions, time/resource quotas, immutable receipts, malware/dependency checks, native sandboxing where feasible, least-privilege service users and emergency kill switches.

**Acceptance:** dedicated penetration/fuzz tests against the canonical document loader and plugin transport; no secret content appears in logs, databases, traces, reports, crash bundles or unapproved cloud calls.

## 27. Phase Q2: performance, availability and indexing durability

- Establish baseline latency on all target machines before optimization.
- Index asynchronously; journal batch progress; auto-resume when power/network is restored. Never need to reread a 100 MB file into a single memory allocation to search it.
- Streaming hash/parse, low-memory bounded queues, incremental DB transactions and read-only snapshot handles during reindex.
- Track P50/P95/P99: corpus index throughput, query latency, persona compile, prompt preparation, first-token time, tool invocation, audio latency and gateway restart recovery.
- Expose cache hit ratios, source hash generation, section count, FTS size, embedding provider, reindex backlog and receipt store size.
- Test degenerate corpora (one million headings, huge code fence, a single enormous line, repeated Markdown anchors, nested directory trees, deeply chained includes).
- Benchmark on fast internal SSD and slower SD card while preserving durability, with optional moving index storage to external SSD.
- Avoid nonessential embeddings on power-limited Pi/Android devices; rely on FTS as the always-available baseline.
- Use memory mapped or streamed reads where the OS supports them; guard against OOM and avoid excessive writes on flash media.
- Every indexing failure reports a retryable reason and leaves last-known-good indexes/source docs intact.

**Acceptance:** durable source continuity after sudden power cut; restart time bounded by checkpoint size rather than whole corpus size; configured resource budgets respected.

## 28. Phase Q3: testing matrix and evidence hierarchy

### 28.1 Test layers

1. Static metadata/version/license and vulnerability audit.
2. Deterministic pure contracts and schema migration tests.
3. Plugin discovery/registration in a disposable real Hermes profile.
4. Installed external engine test with actual subprocess or loopback service.
5. Gateway-level prompt owner, route and durable-state tests.
6. End-to-end CLI/TUI/Web/Desktop sessions and actual tool invocation.
7. Cross-device migration, resume, persona switch and backup restore.
8. Offline/online/partially degraded networks, secret failure and service restart.
9. Performance soak, large corpus, fault injection and hardware-specific run.
10. Human evaluation of sustained character consistency and authorized tool behavior.

### 28.2 Named regressions from the frozen build

- Reproduce and diagnose the previously reported **five core-plugin**, **one Verðandi socket** and **one voice loopback** failures with real services, not stubs.
- Preserve full `CUSTOMIZATIONS.md` contract coverage as the current source of truth.
- Verify imported persona docs do not hit old head/tail truncation during the new path; verify stock Hermes still retains its documented behavior when the RuneForge plugin is off.
- Run profile A→B→A tests for every adapter, new memory index and credential source.
- Repeat genuine memory writes/reads, world observations, tarot draws, verse validation, avatar preflight, real gateway turn and backup restore.

### 28.3 Evidence policy

| Status | Minimum proof |
|---|---|
| **Documented only** | Design/README/API sketch |
| **Contract implemented** | Module + deterministic passing tests |
| **Installed integration** | Real dependency + discovery + compatibility probe |
| **End-to-end working** | Actual user-facing call, output, side effects and failure path tested |
| **Production qualified** | Security, persistence, performance, operating limits, rollback, cross-platform targets |
| **Deferred/blocked** | Explicit reason, scope and condition for reconsideration |

Never promote a feature by renaming its stage. Record precise test command, SHAs, host OS, hardware and result.

## 29. Phase Q4: operator experience and documentation

- Add a “RuneForgeAI Extensions” dashboard or command group showing services, versions, capabilities, linked profile, current offline status, model location, source privacy and next required action.
- Persona editor/browser must support enormous Markdown **through virtualization/paging** rather than a single giant DOM textbox. Provide search, source hierarchy, diff, preview, undo, hash, reload and per-section priority.
- Add a source transparency panel: “What defines this persona?” vs “What does it remember?” vs “What does the external world model say?”.
- Offer user-controlled quick presets (offline, local-fast, hybrid, deep, writing, coding, divination, roleplay, virtual world) without silently changing core identity.
- Add native GUI/CLI installation and diagnostics for Kubuntu and ARM64 hosts. Keep headless paths first-class.
- Document credential provisioning through Kista and externally authorized account connectors, not plaintext pasted into project MD files.
- Provide concise beginner setup plus expert references, full developer API, migration guide, threat model, troubleshooting and benchmark instructions.
- Maintain a dated README NEWS history that distinguishes working features from planned improvements.

**Acceptance:** a non-developer can inspect all enabled modules, understand any unavailable engine, edit a large persona file and validate the result without changing Python source.

---

# PART VI — Phased implementation sequence and release gates

## 30. Implementation waves (dependency-ordered, independently shippable)

| Wave | Work packages | Proof gate |
|---|---|---|
| **W00: Freeze** | U0 inventory, data export, backup, SHA/lock, baseline report | reproduce source + rollback |
| **W01: Upstream** | U1 version intake, v0.23 gateway behavior, conflict audits | selected upstream suite and Volmarr contracts |
| **W02: Dependency safety** | U2 lockfile, Python/Node/Rust native plans, licenses | reproducible cold install |
| **W03: Unbounded canon** | P0/P1 source loader and manifest, streaming full-fidelity files | 100 MB byte-identical corpus |
| **W04: Retrieval** | P2 FTS index, stable section IDs, read paging, optional embeddings | buried-section recall, zero source loss |
| **W05: Live persona** | P3/P4 kernel + gateway prompt insertion + A/B profiles | real conversations across surfaces |
| **W06: Memory** | P5 full `MEMORY.md` and `USER.md` backing corpus; old tool compatibility | large-memory retrieval + restart |
| **W07: Persona controls** | P6 real CLI/UI reload, diff, inspection and drift tests | no stub command or invented result |
| **W08: Existing engines** | E0 version audits + E1–E5 upgrades in dependency order | installed real engine for every claimed green row |
| **W09: New projects** | N0 project review, N1 capability bus | 3 live heterogeneous tools |
| **W10: Productivity** | N2 coding and project management, N3 Samtal/Samkoma | permissioned, replay-safe workflows |
| **W11: Embodiment/world** | N4 integrations, local voice/avatar/SL and hardware displays | owner-authorized end-to-end behavior |
| **W12: Edge + research** | N5 MimirAlloc/Yggdrasil/Lífþrasir experimental opt-ins | proof, no unsafe production promotion |
| **W13: Production** | Q0–Q4 audits, packaging, performance, docs | release-qualifying scorecard |

This is a **work-breakdown order**, not a fabricated calendar deadline. Multiple low-risk research tracks can progress concurrently, but **source/authority contracts precede live writes**.

## 31. Detailed engineering tickets and dependencies

### W00 tickets
- [ ] W00.01 Snapshot current remote SHA and integration branches.
- [ ] W00.02 Record service/plugin/source/API version matrix.
- [ ] W00.03 Export user-owned persona and state with encrypted verified backup.
- [ ] W00.04 Baseline tests and reproduce seven recorded environment failures.
- [ ] W00.05 Produce compatibility fixture archive and external source provenance.
- [ ] W00.06 Review every public/private repository boundary.
- [ ] W00.07 Capture a native offline install recipe.

### W01 tickets
- [ ] W01.01 Pin v0.23.0 official release + review any newer upstream SHA.
- [ ] W01.02 Guarded no-commit merge, preserving personal README automatically.
- [ ] W01.03 Single gateway session ownership integration.
- [ ] W01.04 Bot/group-chat/remote gateway identity routing.
- [ ] W01.05 Rewind/fork consistency.
- [ ] W01.06 Plugin API, registration, update lifecycle, compatibility.
- [ ] W01.07 Paid tools spending/permission gates.
- [ ] W01.08 Native smoke and regressions.
- [ ] W01.09 Merge/release notes and changed-path ownership audit.

### W03–W07 persona tickets
- [ ] P.001 Define source roles/trust/authority/secret policy.
- [ ] P.002 Build streamer and byte-exact canonical source ingestion.
- [ ] P.003 Migrate `SOUL.md` and auxiliary role documents with a dry-run.
- [ ] P.004 Implement transactional digest/manifest updates.
- [ ] P.005 Complete Markdown AST and stable section/span identity rules.
- [ ] P.006 Implement incremental SQLite FTS5 index and versioned offsets.
- [ ] P.007 Optional embeddings behind local/cloud consent gate.
- [ ] P.008 Tune identity kernel with protected source provenance.
- [ ] P.009 Wire one official gateway prompt injection owner.
- [ ] P.010 Remove duplicate legacy persona injection on opt-in profile only.
- [ ] P.011 Preserve model-specific context packet budgets and receipts.
- [ ] P.012 Wire real persona reload/diff/inspect/explain commands.
- [ ] P.013 Implement user-facing huge-file editor/pager and export.
- [ ] P.014 Bridge large `MEMORY.md` / `USER.md` to full backing stores.
- [ ] P.015 Test user-authored canon protection against generated summaries.
- [ ] P.016 Test 1 MB, 20 MB, 100 MB, interrupted import and index repair.
- [ ] P.017 Test 1000-turn drift, model switch, multi-persona and subagent.
- [ ] P.018 Test private/public source filters before cloud inference.
- [ ] P.019 Test cross-machine backup/restore and schema migrations.
- [ ] P.020 Publish system diagnostics and stable how-to docs.

### W08 engine tickets (repeat E0 protocol for each)
- [ ] E.01 Verðandi current event protocol and bridge regression.
- [ ] E.02 A.E.S.I.R. inference/quantization/model catalog API.
- [ ] E.03 Bifröst/Mímir current retrieval and write contracts.
- [ ] E.04 Muninn/Huginn independent package distribution and safe lock.
- [ ] E.05 MemPalace latest verified store adapter.
- [ ] E.06 OpenViking latest verified catalog/provider/server.
- [ ] E.07 WYRD latest canonical-fact API, provenance and events.
- [ ] E.08 Kista vault/CLI/permissions/rotation and redaction.
- [ ] E.09 Astrology tool current interface + evidence fixtures.
- [ ] E.10 RuneTarot engine layouts and seeded correspondences.
- [ ] E.11 Seiðr poetry meters/kennings/validation.
- [ ] E.12 RPG/Sagnaskemma verified rule adapter.
- [ ] E.13 Hamr spec/asset/preflight current version.
- [ ] E.14 Seiðr-Smiðja Loom/Hoard/Gate/Forge current version.
- [ ] E.15 Voice + avatar adapter, output-only boundary check.
- [ ] E.16 Reconcile identity/agency and prompt live hooks with gateway.
- [ ] E.17 Run per-engine failure/timeout/partial response and consent tests.
- [ ] E.18 Verify build/docs/versions at two named hardware targets.

### W09–W12 extension tickets
- [ ] N.01 Audit Rúnmál frontend/API and persona import/export.
- [ ] N.02 Audit Samverk stable forge API and permissioned tool adapter.
- [ ] N.03 Audit Samtal agent transport and encryption/room permissions.
- [ ] N.04 Audit Samkoma evidence/proposal/approval lifecycle.
- [ ] N.05 Audit Mythic Agent CLI and share approved workflow schemas.
- [ ] N.06 Prototype Draupnir bounded delegate jobs in disposable checkouts.
- [ ] N.07 Integrate HugrGate behind deterministic decision fallback.
- [ ] N.08 Prototype Yggdrasil worker capability registry, not claimed mesh.
- [ ] N.09 Verify Hliðskjálf Pi 5 telemetry and real accelerator capabilities.
- [ ] N.10 Evaluate MimirAlloc in independent testbed only.
- [ ] N.11 Keep Lífþrasir observe/report/propose-only initial workflow.
- [ ] N.12 Implement private Tvíheimr connector with strict data routing.
- [ ] N.13 Review Heimdall/Second Life platform terms and actual bot API.
- [ ] N.14 Design standardized tool descriptor and service registry.
- [ ] N.15 Run three-service live interoperability demonstration.
- [ ] N.16 Update integration-lock from reviewed source SHAs.

## 32. Release scorecard

A candidate is releasable when:

- [ ] Target upstream SHA/release and personal revision are recorded.
- [ ] Personal README and all source Markdown are protected and backed up.
- [ ] Source files have no artificial hard size cutoff in the RuneForge persona corpus.
- [ ] Full persona/memory byte-identity has been tested under real upgrades and restores.
- [ ] Actual gateway prompts contain the pinned persona kernel and relevant retrieved sections with receipts.
- [ ] Cross-profile, cross-persona, remote and delegate isolation tests pass.
- [ ] Critical security tests pass, including secret/exfiltration and prompt-injection cases.
- [ ] All enabled external engine versions have passing installed smoke tests.
- [ ] All disabled/unavailable/design-only engines are labeled honestly.
- [ ] Offline-only session sends no cloud model, vector or telemetry request.
- [ ] Any file-write or high-impact action has correctly scoped authorization.
- [ ] Native deploy/rollback is demonstrated on supported hardware.
- [ ] Performance/energy budgets have reproducible measurements.
- [ ] No regressions remain hidden behind a “test environment” explanation.
- [ ] Docs, code and actual capability matrix agree.

## 33. Maintainer handoff protocol

A collaborator or coding agent starting a slice should:

1. Read `AGENTS.md`, `CAMPAIGN_STATE.md`, `CUSTOMIZATIONS.md`, `ARCHITECTURE_VOLMARR.md`, `UPSTREAM_SYNC.md` and this roadmap.
2. Fetch and diff the **current** relevant upstreams; do not trust a pinned version listed here as eternally current.
3. Choose one bounded issue/ticket, note dependencies and write a short design of what changes and what must stay invariant.
4. Implement against existing domain owners; no shadow compiler, second memory owner or duplicate scheduler.
5. Add real contract tests and at least one proof at the appropriate evidence level.
6. Run the targeted suite, then the appropriate upstream and personal regression suite; report commands and raw counts.
7. Record source SHA, plugin version, test host, migration notes, license changes and unresolved limitations in the integration ledger.
8. Extend README NEWS **additively**, preserving historic news and project disclaimer. Do not replace the page with generated hype.
9. Write a durable campaign checkpoint after a verified slice. Never publish a claim of completion when no live caller exists.
10. Stop on permission, credential, destructive migration or other owner-authority boundary and obtain the specified authorization before proceeding.

## 34. Source pointers and verification entrypoints

- Hermes official: https://github.com/NousResearch/hermes-agent
- v0.23.0 official release: https://github.com/NousResearch/hermes-agent/releases/tag/v0.23.0
- Official docs (memory, plugins, gateway, providers and profiles): https://hermes-agent.nousresearch.com/docs
- This fork: https://github.com/hrabanazviking/hermes-agent-RuneForgeAI-hack
- Project A.E.S.I.R.: https://github.com/hrabanazviking/RuneForgeAI-Project-Aesir
- Rúnmál: https://github.com/hrabanazviking/RuneForgeAI-Runmal
- MimirAlloc: https://github.com/hrabanazviking/RuneForgeAI-MimirAlloc
- Samverk: https://github.com/hrabanazviking/RuneForgeAI-Samverk
- Samkoma: https://github.com/hrabanazviking/RuneForgeAI-Samkoma
- Samtal: https://github.com/hrabanazviking/RuneForgeAI_Samtal
- Mythic Agent CLI: https://github.com/hrabanazviking/Mythic_Agent_Coder_CLI
- HugrGate: https://github.com/hrabanazviking/RuneForgeAI-HugrGate
- Draupnir Forge: https://github.com/hrabanazviking/RuneForgeAI-Draupnir-Forge
- Yggdrasil Distributed Inference: https://github.com/hrabanazviking/Yggdrasil-Distributed-Inference-System
- Hliðskjálf: https://github.com/hrabanazviking/RuneForgeAI-Project-Hlidhskjalf
- Lífþrasir: https://github.com/hrabanazviking/RuneForgeAI-Lifthrasir
- Heimdall: https://github.com/hrabanazviking/Heimdall-SL-Hermes-Agent

**Final rule:** the digital companion's identity is not the narrow prompt or a specific model. The authoritative documents and continuity stores may grow without a source-size limit; the active model sees only the currently relevant, provably sourced part of that much larger living library. That is how unlimited authored depth can coexist with finite, reliable inference.
