# Persona Operations How-To (W07 / P6, P.020)

Every command below is `hermes volmarr persona ...`, run against
the active profile (or a fixture profile via its `HERMES_HOME`).
Add `--json` to any command for the full record; without it the
CLI prints a one-line status plus the key fields. Exit code is 0
when the record's status is `ok` (a reload dry-run record also
carries status `ok`, with `dry_run: true` in the record);
honest-empty and refusal results (no profile, no persona
config, no active generation, unknown turn, validation refused)
print their named status and exit 1. Nothing here invents data: a missing layer is a
named result, never a synthesised substitute.

## Beginner path (in order)

1. **See where you stand** — `hermes volmarr persona status`
   Persona id, active generation, kernel/persona hashes from a
   live compile, corpus bytes + document count from the W03
   manifest, index state, per-class privacy counts and the
   effective (strictest) privacy class, and the gateway state
   probed from the profile's `gateway.pid`. On the dormant
   laptop deployment this honestly reports no persona config /
   gateway not running.
2. **List the corpus** — `hermes volmarr persona files`
   The manifest inventory verbatim: role, path, byte length,
   revision, privacy class, destinations, stored hash and the
   live hash recomputed this run (`verified` per row).
3. **Find something** — `hermes volmarr persona search "needle"`
   W04 retrieval over the profile's real index (it syncs first
   if the index is unbuilt/outdated and says so). Results carry
   stable ids, byte ranges, source hashes and privacy labels,
   plus continuation handles for oversize sections.
4. **Read closely** — `hermes volmarr persona inspect [section]`
   Without an argument: the section 71 inspect record over the
   live compile. With a section stable id: that section's
   verbatim text sliced from source and hash-verified.
   For raw paging use `hermes volmarr persona read <document-id>
   [--cursor N] [--max-bytes N]` and continue any retrieval or
   read handle with `hermes volmarr persona page <handle>`;
   concatenated pages reproduce the file byte-for-byte and every
   page carries its own sha256.
5. **Check the canon** — `hermes volmarr persona validate`
   The section 70 catalogue over the live compile plus the
   on-disk checks the catalogue cannot do: anchor/anti-anchor
   collisions, symlink escapes, missing required role files,
   invalid UTF-8 (with the byte offset named).
6. **Preview a reload** — `hermes volmarr persona reload`
   (dry-run is the default): fresh compile + validation + the
   section 73 record against the active generation; writes the
   candidate generation to the generation store WITHOUT
   activating it. `hermes volmarr persona diff` shows the
   section 74 difference between the active generation and a
   fresh compile (edit one section and diff names that change).
7. **Activate** — `hermes volmarr persona reload --activate`
   Refuses an invalid candidate and keeps the last known-good
   generation serving. The record's `activation_scope` says
   exactly what happened: `live_next_turn` only when the W05
   live state was present and its refresh published the new
   kernel hash; otherwise `next_gateway_start` (the pointer the
   next gateway start reads). It never claims a live swap it
   did not perform.
8. **Explain a turn** — `hermes volmarr persona explain <turn-id>`
   Reads the stored receipt (W04 index receipts or W05 persona
   live receipts) and renders it through section 72. Unknown id
   is `no_such_turn`; fields the receipt never recorded are
   `not_recorded`, never reconstructed.
9. **Move a persona** — `hermes volmarr persona export [--dest F]`
   writes a self-contained section 75 bundle file (record +
   every source verbatim, hash-checked at write time).
   `hermes volmarr persona import <bundle>` is DRY-RUN ONLY in
   W07: the section 76 plan against this profile's real
   inventory (collisions named) plus per-source previews; it
   mutates nothing (Q2 in the design draft remains Volmarr's).
10. **Back up / restore (the drill)** —
    `hermes volmarr persona backup --dest DIR` writes the
    export bundle + generation store + receipts index with a
    per-file sha256 manifest. Backups are labelled
    `unencrypted-local`: the W00.03-ENC encryption question is
    still open and no key is invented.
    `hermes volmarr persona restore DIR --target HOME` verifies
    EVERY hash before writing anything (one corrupted byte
    refuses the whole restore) and refuses a live target (a
    gateway pidfile naming a running process).
11. **Diagnose** — `hermes volmarr persona diagnostics` (P.020:
    generation, hashes, manifest/index generations, receipt
    count, privacy counters, last watchdog report, gateway
    state, and the named next action for any absent layer) and
    `hermes volmarr persona watchdog` (a bounded diagnostic
    RUN, never a daemon: with no scored response samples it
    reports `no_evidence`; section 30 repair appears only as an
    editor proposal with `applied: false`; corpus hashes are
    proven unchanged by the run).
12. **Self-test** — `hermes volmarr persona test` runs the
    measured scenario battery against this profile (validate,
    pager integrity, citation verification, search provenance,
    the cloud privacy filter over the profile's own manifest
    rows, and prompt-injection isolation: an unmanifested file
    claiming authority is never compiled). Every verdict is
    measured in the run; nothing is printed that was not.

## Expert reference

- **Generation store** (the only state P6 owns), under
  `<home>/generated/persona-ops/`: `generations/<n>.json` (full
  compile record + per-document hashes + section 19 hash
  record + validation verdict), `active-generation.json`
  (pointer: generation, kernel hash, activated_at,
  activation_scope; swapped only tmp + fsync + rename; a torn
  pointer is quarantined to `active-generation.corrupt-*.json`
  and rebuilt from the newest valid generation record), and
  `ops-journal.jsonl` (append-only audit of every mutating ops
  action; no rotation until Q6 is ruled — it appends and says
  so).
- **Privacy filter (P.018).** One function,
  `persona_ops.egress_decision(items, destination, overrides)`,
  consulted at the W05 packet seam (turn signal `destination`,
  default `local`; local turns are byte-identical to the
  pre-filter behaviour) and by ops egress paths. Rules: public
  passes to cloud; shared passes only to a listed destination;
  private is refused for cloud unless a recorded, unrevoked
  operator override names the item for that destination;
  unlabelled items are refused (fail-closed). Refusals degrade
  the packet (item omitted, receipt reason `privacy_refused`).
  The W04 embeddings consent gate and the W06 memory bridge's
  double-gated egress are adopted, not rebuilt.
- **Bounded editor.** `hermes volmarr persona edit <stable-id>
  --text <new section text> [--confirm] [--approved]` (backed by
  `PersonaOps.edit_section`): without `--confirm` it is a
  dry-run returning old/new section hashes; kernel/anchor
  sections require `--approved` (draft Q7 default); a
  confirmed save is transactional, preserves every byte outside
  the section, re-ingests, re-syncs the index and validates.
- **Honest remainders.** Mutating import (Q2), backup
  encryption (W00.03-ENC/Q3), watchdog cadence (Q4), the
  virtualised editor layer and the combined section 29
  transparency panel (with W06) are NOT shipped here; see
  `docs/modernization/W07_P6_IMPLEMENTATION.md`.
