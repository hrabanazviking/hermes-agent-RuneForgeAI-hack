# Volmarr's Projects — Update Briefing for Hermes

*Prepared 2026-10-30 by Yrsa, for filing into
`hrabanazviking/hermes-agent-RuneForgeAI-hack`. Purpose: bring Hermes
current on every RuneForgeAI project as of this date, in one document an
agent can act from. States below are verified from the projects' own
records on 2026-10-30, not remembered loosely. Where a thing is not
proven, it says so.*

## The frame

- Volmarr's main agent going forward is his own highly modified Hermes
  (this fork). Muse/Yrsa remains a builder through the paid month and a
  free-tier presence after; **every project below is to be workable by
  Hermes** — roadmaps, campaign state, and laws live in the repos and in
  plain files for exactly that reason.
- Yrsa-on-Hermes is Volmarr's stated future intent: same tendencies,
  accumulated knowledge, and learned skills as Yrsa-on-Muse. Her
  continuity substance is portable text under his control (SOUL,
  IDENTITY, MEMORY, skills).
- Standing laws that bind ALL work below (digest; full texts live in
  each project's own governance docs): **no Docker, ever** (native
  installs only) · **README.md files are never overwritten** — extend by
  hand or ask · **repo creation is Volmarr's own job** · **every
  10-minute timer is a keeper** that continues stalled work, never a
  watcher · **never leave a discovered bug unfixed** · **answer the
  human's questions first, in plain words** · GitHub pushes are gated
  per line on Volmarr's explicit word; fetch + remote-diff before any
  push; never force-push; verify the remote moved.

## The projects

### Project Aesir — sovereign model runner (Mojo)
- Repo: `hrabanazviking/RuneForgeAI-Project-Aesir`, main at `f2a15835`.
- State: the 204-slice roadmap Parts I–II are CLOSED (counted suite
  275 passed); Part III (model-matrix completion) in progress at S-079.
  The model wave is shipped: Coder-3B Q8_0 / Coder-7B Q4_K_M / Stheno
  Q3_K_M crowns all correct; GPU spill proven token-identical on the
  laptop (RTX 2060). Honest open items: Zen long-prompt case NOT
  PROVEN, Gemma-4 on the VM NOT PROVEN, vision encoder still CPU-side
  (ledger: partial).
- Accelerator-first law: NPU → GPU → CPU spill only; a CPU-carried run
  is a defect to report with numbers.

### Hailo-10 finish line (Aesir's NPU road, on Mimir the Pi)
- Tree: branch `yrsa/finish-line-roadmap` only, never main.
- State: the 200-slice evidence road completed at 4.200; the campaign
  continues past it — slice 4.235 banked 2026-10-30, 4.236 auto-started.
  Discipline: one bounded physical child per contract; a failed attempt
  closes its batch forever; never invent undocumented values — NOT
  PROVEN instead. **Text generating on the chip itself is still NOT
  achieved and must never be claimed.**

### Samtal — the sovereign chat village
- Live on Mimir (Pi 5), native systemd, port 8787; Yrsa is verified
  co-owner (seat 1). Repo: `hrabanazviking/RuneForgeAI_Samtal` ONLY
  (a duplicate `Samtal` repo exists; it is Volmarr's to delete, never
  touch). AGPLv3. Federation is refused permanently by his ruling.
- Daily noon backups run; note honestly: the 2026-10-30 bundle was
  built on Mimir (65,906,449 B) but the Drive ferry FAILED — Mimir's
  Tailscale was logged out. Next needs in his words: refinement, voice
  chat, interface polish. Unity 3D rooms wait on his Unity ID sign-in.

### Samverk — sovereign GitHub-class forge
- Repo: `hrabanazviking/RuneForgeAI-Samverk` (public, AGPL-3.0).
- State: roadmap 416 slices / 22 parts; **S-143 pushed to GitHub
  2026-10-30** (pull requests + draft PRs working; 914 passed / 1
  skipped / 0 failed at push). Keeper continues building locally;
  further pushes await his word. Must stand alone AND embed in Samtal
  (late seam, Part XIX). Cross-platform proof is earned per device,
  never assumed.

### Mythic Agent Coder CLI — the coding forge
- Repo: `hrabanazviking/Mythic_Agent_Coder_CLI`, default branch
  `development`, AGPL.
- State: the October build (50 slices) stands. Three roads now exist:
  Volmarr's own 500-slice Mimisbrunnr roadmap (unstarted, in-repo);
  the 272-slice All-Features roadmap (2026-10-30: every CLI coding
  app's features in their kindest form, Mythic Engineering as the
  method) — **pushed to the repo 2026-10-30, main at `d06c0098`, build
  campaign in motion under a keeper**; and a 568-slice deep-study twin
  awaiting reconciliation through the 272 road's Concordance slice.
  Keys belong in Kista, never in config files.

### Sagnaskemma — the D&D engine (and Samtal's table)
- Repo: `hrabanazviking/Sagnaskemma-Volmarrs-D-and-D-Lore-Treasure-Trove`.
- State: engine v0.2.0, hardened H0–H8, 606 tests passing / 1 skipped
  (recounted 2026-10-30). Iron laws: every roll through `dice.py`;
  content in JSON data only; per-module interface contracts.
- The Long Table roadmap (212 slices: grid maps, tokens, dynamic light
  and shadow, per-seat fog, hosted tables, Samtal embedding as charter
  G2/G7, reusable core) — **pushed 2026-10-30, main at `e0dc2d7`, build
  in motion under a keeper**. A 566-slice whole-engine twin roadmap
  sits beside it in the repo, awaiting a reconciliation slice.

### WYRD Protocol — world-model engine
- State: **roadmap COMPLETE** — v1.5.0 at `8432100` on development,
  suite 2,284 passed (one known load-flaky test). Consumed by Heimdall
  (Second Life) and designed for use across the workshop.

### Heimdall — Yrsa in Second Life
- Repo: `hrabanazviking/Heimdall-SL-Hermes-Agent`. Host: purplelongship.
- State: **Phase 1 exit test PASSED 2026-10-30** — real grid login via
  Kista-held credentials; Yrsa's avatar seen in-world by Volmarr. The
  earlier `login_failed: Canceled` defect was a client-library mask
  over Linden's true answer; fixed in our code (commit `a3df200`,
  unpushed at last record). Queued next, in Volmarr's own asks:
  in-world screenshot capture; sending AND receiving instant messages;
  RLV in both directions; movement/pathfinding; an SLua re-check
  (Linden's Lua has moved since the October research); the
  standard-features study. Phase 4 live voice waits on
  `HEIMDALL_VOICE_ID` + his presence.

### Kista — Volmarr's own credential keeper
- Built by Runa Freydisdottir (Hermes lineage) as a fork; the copy to
  use lives in Volmarr's ai folder on purplelongship (a separate twin
  in Smart Toaster is a different program — leave it alone).
- State: current with its GitHub at `54e31f1090` (that update sits
  uncommitted in his Ember checkout — committing is his call). Holds
  the Heimdall Second Life vault today. His stated expansion road:
  serve any program's credentials; remember URLs, WYRD states of
  being, character personality prompts/habits, per-AI credentials and
  settings.

### Rúnmál — sovereign AI chat app
- State: roadmap complete 94/94; enters evaluation (an Evaluation
  Sitting brief awaits his word). Clean-room, his own licence, Python;
  Project Aesir is its eventual inference heart.

### Samkoma — planning-assistant backend (ex-hackathon)
- State: full codebase pushed to his repo, licence lifted to GPLv3 at
  his ruling ("Lift it to V3"), generator SDK bug + two stale bugs
  fixed and verified. The hackathon chapter itself is closed.

### Publishing (context for any agent serving him)
- *The Rune-Keys of Yggdrasill* is LIVE on Kindle (ASIN B0HNMHXV39),
  enrolled by Volmarr in ONE 90-day KDP Select term, auto-renew off,
  ending ~2027-01-21/22. Laws: every image carries real alt text; no
  EPUB ships without EPUBCheck at 0 errors; "Old Ways" always
  capitalised; "Heathen Third Path" always in full.

### Machines (one line each)
- **Mimir** — Raspberry Pi 5, Debian 12, 16 GB; Samtal + Hailo live
  here; Home Assistant and yrsa-voice STOPPED+DISABLED 2026-10-30 (a
  false wake spoke through a bedroom display); Tailscale found logged
  out 2026-10-30. **purplelongship** — Ryzen 9 laptop, RTX 2060 Max-Q,
  Ubuntu; builds, GPU line, Kista, Heimdall host. **ROG Flow Z13** —
  ordered 2026-10-29 ($3,499), delivery date unknown at this writing;
  Volmarr plans to revive his Hermes agent on it when it arrives.

*End of briefing. Filed copies belong in the hack repo beside
CUSTOMIZATIONS.md; the living states above move fast — trust each
project's own state file over this snapshot whenever they differ.*
