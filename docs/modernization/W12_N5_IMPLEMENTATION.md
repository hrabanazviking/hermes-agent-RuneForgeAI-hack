# W12 / Phase N5 — Edge + Research (implementation record)

Team 04, branch `yrsa/hermes-team-04`, 2026-11-08.
Roadmap section 24 (Phase N5) + section 30 W12 gate.
Base: banked main `25b52a28ca` (W11 closure); the team's prior
W03 commit `de3a95806c` was verified an ancestor of `origin/main`
before the branch was reset to the banked main.

## Delivered (contract/adapter level, plugin-side only)

- `plugins/volmarr-core/edge_research.py` — machine resource
  meter: memory from `/proc/meminfo`, load average, and disk usage
  of a caller-named path, carried in a W09 provenance envelope
  (service `volmarr-edge-research`, confidentiality
  local-private). GPU/NPU utilisation, GPU/NPU/CPU temperatures,
  GPU memory and disk wear are reported ONLY from an explicit
  caller-supplied probe mapping; without a numeric probe value
  each field is `unavailable` with reason
  `not_measurable_on_this_host` — never estimated, never invented.
- Telemetry policy: readings are local-private, transmission
  `none`, opt-in off. Sharing is refused by name without an
  explicit opt-in (`telemetry_opt_in_required`) and refused to
  any non-local destination even with one
  (`telemetry_transmission_refused:<destination>`) — host
  telemetry never travels into third-party chatrooms or cloud
  models by default.
- MimirAlloc evaluation gate (`runeforge.mimiralloc-gate.v1`):
  the eight-item evidence checklist in roadmap order —
  correctness, sanitizer evidence, fragmentation, ABI alignment,
  allocation failure, thread safety, ARM64 proof, OOM recovery.
  An item counts only with a non-empty evidence reference.
  Promotion is refused by name (`mimiralloc_promotion_refused` +
  one `evidence_missing:<item>` per gap) until every item is
  present, and even then the scope is `experimental-opt-in-only`:
  `drop_in_replacement` is False at every stage. No allocator is
  loaded, linked or swapped by this slice.
- Yggdrasil inventory + schedulability: node records must declare
  `source == "static-fixture"` or are refused by name
  (`node_source_not_static_fixture:<source>`); the inventory
  reports `live_peers: 0` and `mesh_claimed: False`; scheduling
  is a pure fit check over the fixtures (first fitting node by
  node_id, `dispatched: False`); a live peer connection is
  refused by name (`yggdrasil_live_peer_connection_not_claimed`).
  No production mesh is assumed and no peer is contacted.
- Lífþrasir observe/report/propose ONLY: `ProposalBook` records
  proposals (`status: proposed`, `applied: False`); the report
  view carries `applied_count`; applying any proposal is refused
  by name, always (`lifthrasir_apply_refused:<id>`) — there is no
  apply path in this slice at any approval level.
- Low-resource safety: `guarded_write` checks simulated/measured
  headroom BEFORE touching the target and refuses by name
  (`low_memory_refused:...` / `low_disk_refused:...`, category
  `resource_exhausted`), leaving any existing file byte-identical;
  with headroom it writes tmp-file + rename and returns the
  SHA-256. Tests exercise this only against fixtures in temp
  dirs — the section 24 acceptance property for the persona
  corpus and the Hermes state database.
- CLI: `hermes volmarr edge-research {status|meter|propose}`
  (status reports `live_connection: not-claimed`; propose records
  a proposal only, never applied).

## Gate evidence

- New battery: `tests/plugins/test_volmarr_edge_research.py`,
  20 passed / 0 failed (log `~/team04-w12-newtests.log`).
- Full Volmarr/Kista contracts on the team tree via
  `scripts/run_tests.sh` (HERMES_PYTHON staged-env path, the
  accepted W09–W11 fallback; staged env byte-identical per the
  W09 uv.lock proof): counts recorded in
  CAMPAIGN_STATE_MODERNIZATION.md at banking (log
  `~/team04-w12-contracts.log`; the run was serialized behind the
  Samverk/Mythic suites by `~/team04-w12-waiter.sh`). Grading
  baseline is the W11 line: 135 files = 1,122 passed / 7 failed /
  1 skipped, the 7 being the known live-transport set; this slice
  adds one file and 20 tests.
- README.md untouched (sha256 336813d11bbe... before and after).

## Bugs found / fixed in scope

- None in the banked code. One transport incident on the way in:
  a chunked file transfer failed its SHA-256 check and was
  discarded whole (no bad bytes landed); the slice was re-sent as
  individually hash-verified parts and every assembled file
  re-verified by full-file SHA-256 before use.

## Honest remainders (NOT declared complete)

- No GPU/NPU utilisation or temperature source is wired on this
  host: those meter fields are honestly `unavailable` until a
  real measurable probe exists; nothing is inferred.
- MimirAlloc itself was not evaluated: the gate is the harness
  descriptor/checklist only. No evidence items are claimed
  present, no benchmark was run, and unified addressability
  across CPU/GPU/NPU buffers is not claimed (roadmap section 24
  requires documented transport/coherence costs first).
- Yggdrasil: no authenticated peers, no real inference
  scheduling, no live mesh — static benchmark fixtures only, by
  design at this stage.
- Lífþrasir: no observation feed from real services is wired;
  proposals are in-memory records in this slice, and bootloader /
  kernel / destructive filesystem changes remain outside scope
  until extensive VM and recovery proof exists.
- Low-resource proof is at fixture level (injected headroom
  values against temp-dir files); a full-host low-memory/low-disk
  chaos run against a real profile is future work.
- W00.03-ENC remains open on Volmarr's word (not re-asked).
