# N0 Project Triage - Phase N0 (W09, Team 01, 2026-11-08)

Status: DELIVERED as the W09 N0 remainder. This document closes the
open N0 remainder recorded in docs/modernization/W09_N0N1_IMPLEMENTATION.md.
Worktree ~/hermes-team-01, branch yrsa/hermes-team-01, on purplelongship.
Commit-only: the keeper banks serially; nothing merged or pushed here.
README.md untouched (sha256 336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3).

## Scope and evidence rule (honesty law)

Triage of ALL 18 projects named in roadmap section 19 (Phase N0:
project discovery and maturity triage) of
ROADMAP_HERMES_MODERNIZATION_UNBOUNDED_PERSONA_2026-11-07.md.

Every assignment below is grounded ONLY in material already in this
repository:

- the roadmap, section 19 (its own cautions and integration paths);
- docs/modernization/INTEGRATION_MATRIX.md (the promoted W08 E0
  ledger, 26 rows) where a project overlaps an engine row;
- CAMPAIGN_STATE_MODERNIZATION.md (campaign record);
- CUSTOMIZATIONS.md (the fork customization ledger).

No new external probes were run, no GitHub scanning was done, and
no live status is invented. Where section 19 itself calls a project
design-stage, alpha, research-stage or experimental, the category
reflects that wording.

## The four section 19 categories (verbatim definitions)

- Operational adapter candidate: public API/code already proven
  end to end.
- Research prototype: use in disposable experiments only.
- Design proposal: import ideas and research, not runtime code.
- Private collaboration surface: use only behind owner-specific
  secrets, privacy, consent and explicit account scopes.

## Method note - read before using any Operational assignment

Section 19 opens with the caution that a public README is a
direction, not evidence that every described capability works, and
that source, tests, branch and release must be inspected before
adoption. Section 55 law 6 says the same: a README promise, a pure
audit function, an installed package and a working end-to-end
integration are different evidence levels.

Accordingly, Operational adapter candidate below means candidacy
for adapter adoption on the strength of the in-repo record - it is
NOT a claim that any project is proven end to end. On the W08
matrix evidence hierarchy (section 28.3: documented only, contract
implemented, installed integration, end-to-end working, production
qualified), NO project in this triage reaches end-to-end working
inside this repository's evidence. Even the strongest row,
A.E.S.I.R. (matrix row 2), stands at contract implemented with its
live-loopback proof still owed (ticket E.02). Every Operational
assignment still owes the section 19 inspection before adoption.

## Summary table

| Project | Category | Evidence basis | Next wave |
|---|---|---|---|
| Runmal (Rúnmál) | Operational adapter candidate | Roadmap section 19 table: optional frontend via authenticated API/ACP/MCP, Hermes stays turn owner; no design/alpha qualifier in section 19 | W10 (N2/N3) |
| MimirAlloc | Research prototype | Roadmap section 19 table: experimental v0.1.0; no production substitution before correctness/sanitizer/performance gates | W12 (N5) |
| Samverk | Operational adapter candidate | Roadmap section 19 table: integrate via stable typed API/tool plugin; parity with GitHub not assumed | W10 (N2/N3) |
| Samtal | Operational adapter candidate | Roadmap section 19 table: HermES gateway transport/bot with account-scoped keys; deployed version and encryption lifecycle to verify | W10 (N2/N3) |
| Samkoma | Operational adapter candidate | Roadmap section 19 table: tool adapter drafting proposals only; never auto-publish unapproved events | W10 (N2/N3) |
| Mythic Agent Coder CLI | Operational adapter candidate | Roadmap section 19 table: share skills, planning schema and task handoffs; one write authority per checkout | W10 (N2/N3) |
| Draupnir Forge | Design proposal | Roadmap section 19 table: design-stage at latest README; bounded delegate prototype instead of a ready service | W10 (N2/N3) |
| HugrGate | Research prototype | Roadmap section 19 table: active alpha; typed decision contracts behind deterministic fallbacks | W10 (N2/N3) |
| Yggdrasil Distributed Inference System | Design proposal | Roadmap section 19 table: README describes a design phase; no assumed production mesh | W12 (N5) |
| Project Hlidhskjalf (Hliðskjálf) | Research prototype | Roadmap section 19 table: native typed read-only monitoring initially; wake/audio and accelerator claims behind physical proof | W11 (N4) |
| Project Lifthrasir (Lífþrasir) | Research prototype | Roadmap section 19 table: research-stage; diagnostic plugin and human-reviewed patch proposals only | W12 (N5) |
| Tviheimr (Tvíheimr) | Private collaboration surface | Roadmap section 19 table: privacy-first integration; distinct account owners, per-provider destination rules, local-only material never silently passed to cloud | W13 (Q0-Q4) |
| Project A.E.S.I.R. recent development | Operational adapter candidate | INTEGRATION_MATRIX.md row 2: verified, contract implemented, deterministic tool adapter in volmarr-core 0.26.0; CUSTOMIZATIONS.md cognition endpoint rows; roadmap section 19: pin capabilities from the capability ledger, no NPU/text-generation claim without hardware proof | W12 (N5) |
| Heimdall Second Life Agent | Private collaboration surface | Roadmap section 19 table: opt-in separate bot service and credential store; platform terms, rate limits and explicit world actions | W11 (N4) |
| Norse Saga / Sagnaskemma | Design proposal (BLOCKED) | INTEGRATION_MATRIX.md row 24: BLOCKED, repository not found under either candidate name, re-probed 2026-11-08; roadmap section 19: prefer actual version/API, do not import incompatible or third-party-licensed rules wholesale | W11 (N4) |
| OpenClaw personal patches | Design proposal | Roadmap section 19 table: compare behaviour against current Hermes importer and plugin APIs; reimplement useful designs at an approved boundary rather than bulk copying | W13 (Q0-Q4) |
| Runa digital-being experiments | Design proposal | Roadmap section 19 table: compare schemas with existing entity stores; only add missing, demonstrably useful capabilities | W11 (N4) |
| Bifrost Reach / broader edge projects | Design proposal | Roadmap section 19 table: signed nodes, authorized peers and replay-safe transports required before exposing personal memory; distinct from INTEGRATION_MATRIX.md row 3 (Bifrost/Mimir, probe-only) - see entry 18 | W12 (N5) |

Category counts: Operational adapter candidate 6, Research
prototype 4, Design proposal 6 (one of them blocked),
Private collaboration surface 2. Total 18.

## Per-project entries

### 1. Runmal (Rúnmál) - Operational adapter candidate
Evidence: roadmap section 19 table (sovereign Python chat UI,
persona/lorebook editor, memory UX, real-time voice/VR companion
frontends; keep Hermes as turn owner; use as optional frontend via
authenticated API/ACP/MCP; reconcile persona schema rather than
separate competing truths). No W08 matrix row exists for it and
CUSTOMIZATIONS.md records no Runmal adapter, so candidacy rests on
section 19 alone. Consumed first at W10 (N2 acceptance names
Runmal patch preparation) and again at W11 (N4 persona/lorebook
import/export). Confidence: medium - see thin-evidence note.

### 2. MimirAlloc - Research prototype
Evidence: roadmap section 19 table (experimental v0.1.0 in its
November 7 progress note; no substitution for the production
allocator before correctness, sanitizer and performance gates).
Section 24 (N5) consumes it as an independent library evaluated on
test machines first. Disposable-experiment posture only until
those gates pass. Consumed at W12 (N5). Confidence: high -
section 19 states the maturity plainly.

### 3. Samverk - Operational adapter candidate
Evidence: roadmap section 19 table (independent code forge:
repositories, issues, PRs, reviews, project work; integrate via a
stable typed API/tool plugin; avoid assuming parity with GitHub
or shipping in-progress source). The parity caution bounds the
claim; it does not reclassify the project as design-stage.
CAMPAIGN_STATE_MODERNIZATION.md records Samverk only as a W01
draft-lock spot-check name, not as triage evidence. Consumed at
W10 (N2: GitHub and later Samverk adapters with capability
checks). Confidence: medium - section 19 evidence only.

### 4. Samtal - Operational adapter candidate
Evidence: roadmap section 19 table (sovereign human/agent chat
village, live streams, files, agent identities, community
room/TTRPG venue; connect a HermES gateway transport/bot with
account-scoped keys; avoid duplicate messaging stores; verify the
actual deployed version and encryption lifecycle). The
account-scoped keys are the authentication condition of the
adapter, recorded here; they do not by themselves move Samtal
into the Private category, whose definition is reserved for
surfaces usable ONLY behind owner-specific scopes - Tviheimr
(entry 12) is that case. Consumed at W10 (N3 Samtal-native
bridge). Confidence: medium - deployed version unverified in-repo.

### 5. Samkoma - Operational adapter candidate
Evidence: roadmap section 19 table (evidence-backed planning
candidates, events, decisions, approvals, review queue; offer a
tool adapter to draft proposals; never auto-publish unapproved
events or convert unverified content to fact). The draft-only
posture is the Hermes-side safety boundary, not a maturity
finding about Samkoma itself. Consumed at W10 (N3 reviewable
event/task extraction). Confidence: medium-low - the whole
in-repo evidence is the single section 19 row; see thin-evidence
note.

### 6. Mythic Agent Coder CLI - Operational adapter candidate
Evidence: roadmap section 19 table (architecture-first Mythic
Engineering, code-work planning, multi-provider TUI, GitHub
workflows; share skills, planning schema and task handoffs; avoid
two autonomous writers in one Git checkout). No alpha or
design-stage qualifier appears in section 19. Consumed at W10
(N2 shared task schema, one write authority per checkout).
Confidence: medium - section 19 evidence only, no matrix row.

### 7. Draupnir Forge - Design proposal
Evidence: roadmap section 19 table (recursive multi-agent
software development architecture, audits and verification;
design-stage at latest README; prototype a bounded delegate
controller with operator gates instead of claiming a ready
service). Import the architecture and audit ideas, not runtime
code. Consumed at W10 (N2: shared task schema anticipates a
future Draupnir; section 54 places RFI-12 in W09-W10).
Confidence: high - section 19 states design-stage explicitly.

### 8. HugrGate - Research prototype
Evidence: roadmap section 19 table (model-agnostic probabilistic
choices in traditional programs; active alpha; adopt typed
decision contracts for uncertainty routing behind deterministic
fallbacks). Alpha software is prototype software: experiments
and contract trials behind fallbacks, never a load-bearing
runtime dependency yet. Consumed at W10 (section 54 places
RFI-13 in W09-W10). Confidence: high - alpha is stated plainly.

### 9. Yggdrasil Distributed Inference System - Design proposal
Evidence: roadmap section 19 table (edge compute mesh, temporal
routing, task and state placement; its README describes a design
phase; begin with a safe capability registry and benchmark, no
assumed production mesh). What Hermes imports now is the design:
registry shape, routing ideas, benchmark plan. Consumed at W12
(N5: node inventory and safe schedulability experiments before
authenticated peers or real inference). Confidence: high -
design phase is stated plainly.

### 10. Project Hlidhskjalf (Hliðskjálf) - Research prototype
Evidence: roadmap section 19 table (Pi 5 + Hailo HUD/edge
display, telemetry, local co-processor; use native typed
read-only monitoring initially; keep wake/audio and accelerator
claims behind physical proof). Read-only monitoring of a
physical rig is experimental use, and no proven API is recorded
in this repo - no W08 matrix row exists for it. Consumed at W11
(N4: display-safe events and metrics). Confidence: medium -
the posture is clear in section 19, the hardware proof is not
in-repo; see thin-evidence note.

### 11. Project Lifthrasir (Lífþrasir) - Research prototype
Evidence: roadmap section 19 table (self-diagnosing Linux,
verified repair proposals, upstream patch contribution;
research-stage; diagnostic plugin and human-reviewed patch
proposals only, no autonomous kernel modifications). Section 24
(N5) holds the same line: observe, report, propose only.
Consumed at W12 (N5). Confidence: high - research-stage is
stated plainly.

### 12. Tviheimr (Tvíheimr) - Private collaboration surface
Evidence: roadmap section 19 table (private dual-world
multi-agent continuity and authorized shared/private knowledge;
privacy-first integration: distinct account owners,
per-provider destination rules, local-only material never
silently passed to Muse/cloud; no private repo data in the
public roadmap). This is the section 19 definition of the
Private category applied verbatim. Consumed at W13 (Q0:
private/public boundary and AI-to-AI account ownership, whose
text names Tviheimr as essential). Confidence: high.

### 13. Project A.E.S.I.R. recent development - Operational adapter candidate
Evidence: INTEGRATION_MATRIX.md row 2 (Project A.E.S.I.R.,
verified, evidence stage contract implemented; volmarr-core
0.26.0 deterministic tool: bounded loopback OpenAI-compatible
health/catalog/completion plus route decisions; verdict update,
ticket E.02); roadmap section 19 table (pin actual engine
capabilities from its current capability ledger; never claim an
NPU or text-generation path without hardware proof);
CUSTOMIZATIONS.md cognition endpoint and local reflex execution
rows record the same adapter surface. This is the strongest
evidence of any row in this triage - and it still stands at
contract implemented, not end-to-end working: matrix row 2 lists
the live-loopback proof E.02 still owes. Consumed next at W12
(N5 benchmarking and inference-path research). Confidence: high
for candidacy, with the E.02 caveat carried verbatim.

### 14. Heimdall Second Life Agent - Private collaboration surface
Evidence: roadmap section 19 table (world-facing avatar client,
navigation/IM/embodiment ideas; opt-in separate bot service and
credential store; obey platform terms, rate limits and explicit
world actions). A separate credential store, opt-in activation
and explicit per-action authorization are exactly the
owner-specific secrets, consent and account scopes of the
Private category definition. Section 23 (N4) repeats the gate:
explicit permission and credential scope, action logs, rate
limits. Consumed at W11 (N4). Confidence: high.

### 15. Norse Saga / Sagnaskemma - Design proposal (BLOCKED)
Evidence: INTEGRATION_MATRIX.md row 24 (Sagnaskemma engine:
deferred/blocked, BLOCKED on canonical repo identification;
repository not found under hrabanazviking/Sagnaskemma or
RuneForgeAI-Sagnaskemma, re-probed 2026-11-08 under both names;
no pin possible); roadmap section 19 table (deterministic
tabletop rules engine; prefer the actual Sagnaskemma version
and API; do not import incompatible or third-party-licensed
rules wholesale). BLOCKED: identification pending - no category
above Design proposal may be claimed, and no adoption step may
start, until the canonical repository is identified from
project records. Consumed, once unblocked, at W11 (N4 game-table
work; section 54 RFI-05). Confidence: high that it is blocked;
no confidence is claimed about the engine itself.

### 16. OpenClaw personal patches - Design proposal
Evidence: roadmap section 19 table (previously studied agent
enhancements and migrations; compare behaviour against the
current Hermes importer and plugin APIs; reimplement useful
designs at an approved boundary rather than bulk copying).
Reimplementing designs is the Design proposal definition word
for word: ideas in, runtime code not imported. No N-phase names
OpenClaw directly, so its consuming wave is recorded as W13
(Q0-Q4 final audits and handoff) by elimination, and flagged as
the least-scheduled row in this triage. Confidence: high for
the category, low for the wave assignment; see thin-evidence
note.

### 17. Runa digital-being experiments - Design proposal
Evidence: roadmap section 19 table (companion lifecycle,
agency, identity and experience continuity; compare schemas
with existing entity stores; only add missing, demonstrably
useful capabilities). The section 19 path imports schema
findings and capability ideas into the fork entity stores; it
does not adopt experiment runtime code. This was the closest
call in the triage - the experiments wording pulls toward
Research prototype, the stated integration path pulls toward
Design proposal, and the path governs. Consumed at W11 (N4
embodiment and continuity work). Confidence: medium-low; see
thin-evidence note.

### 18. Bifrost Reach / broader edge projects - Design proposal
Evidence: roadmap section 19 table (device discovery,
networking, messaging and edge resource orchestration; require
signed nodes, authorized peers and replay-safe transports
before exposing personal memory). Do NOT confuse this row with
INTEGRATION_MATRIX.md row 3 (Bifrost/Mimir: probe-only adapter,
contract implemented, verified) - row 3 covers the existing
Bifrost engine surface in this fork, while section 19's
Bifrost Reach entry covers the broader edge programme, for
which this repo records preconditions, not a proven surface.
What is imported now is the transport and trust design.
Consumed at W12 (N5 edge and research). Confidence: medium -
the section 19 / row 3 distinction is explicit, the broader
programme itself is described only in one roadmap row.

## Thin-evidence register (said plainly, not guessed over)

- Samkoma (entry 5): one roadmap row is the entire in-repo
  evidence. The category follows that row's adapter posture;
  nothing stronger is claimed.
- Runa digital-being experiments (entry 17): one roadmap row,
  and the category was a close call between Research prototype
  and Design proposal, decided by the stated integration path.
- OpenClaw personal patches (entry 16): category is firm,
  consuming wave is not - no phase names it; W13 is recorded
  by elimination only.
- Runmal, Samverk, Samtal, Mythic Agent Coder CLI (entries 1,
  3, 4, 6): no W08 matrix row and no CUSTOMIZATIONS.md adapter
  record exists for any of them; every Operational assignment
  here rests on roadmap section 19 alone and remains candidacy
  pending the section 19 inspection.
- Project Hlidhskjalf (entry 10): no matrix row; the physical
  proof section 19 requires is not in this repo.
- General: no assignment in this document is backed by source
  inspection performed for this triage, because none was in
  scope - see the remainders note.

## Remainders note

1. The GitHub discovery job named at the end of roadmap
   section 19 (a job that writes a proposed diff for newly
   found RuneForgeAI apps, behind review, feeding the next
   integration-lock revision) is NOT built. It remains future
   work, exactly as W09_N0N1_IMPLEMENTATION.md remainder 5
   already records.
2. This triage is document-evidence only. No source inspection
   beyond this repository was performed for it: no project
   repository was cloned, read or probed, and no live service
   was contacted.
3. Roadmap section 19 requires source, tests, branch and
   release inspection before actual adoption of any project.
   That inspection remains future work, per project, in the
   consuming wave named in the summary table. No category in
   this document waives it.
4. Sagnaskemma (entry 15) additionally remains blocked on
   canonical repository identification from project records
   (INTEGRATION_MATRIX.md row 24) before even the inspection
   in point 3 can begin.
5. Nothing in this document moves a pin, promotes an evidence
   stage, or declares any integration complete. The W08 matrix
   and integration-lock.json remain the living compatibility
   record.
