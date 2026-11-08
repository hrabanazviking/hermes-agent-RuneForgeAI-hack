# W11 / Phase N4 — Embodiment & World (implementation record)

Team 03 (keeper continuation), branch `yrsa/hermes-team-03`, 2026-11-08.
Roadmap section 23 (Phase N4) + section 30 W11 gate.

## Delivered (contract/adapter level, plugin-side only)

- `plugins/volmarr-core/world_bridge.py` — Runmal interchange:
  versioned `runeforge.world-interchange.v1` JSON bundles; source
  documents ride as base64 bytes with per-doc sha256, so an
  export/import round trip is byte-identical; authorship is a
  required field carried verbatim; unknown schema names and
  unsupported versions are refused by name; hash mismatches are
  refused; shared documents import read-only unless the operator
  passes the explicit promotion flag.
- WYRD world events: typed records (`observation`, `location`,
  `action-outcome`, `availability`) whose provenance (service,
  source ref, recorded-at, confidentiality) is mandatory; routing
  an event into a persona/fictional/persona-memory store is a hard
  refusal by name — world facts are never blended into fictional
  or persona memory.
- Remote presence (Heimdall/Second Life): authorization resolves
  through the W09 capability-bus policy against an owner-only
  descriptor that does not declare local-private data, so private
  persona reads are refused by name and non-owner callers are
  refused by name. The descriptor is design-only: NO credentials
  and NO live connection exist in this slice; no fake SL client.
- Hlidskjalfr HUD filter: allow-list only (kind/title/value/unit/
  status/service/recorded_at); sensitive fields (transcript,
  content, text, secret, token, persona_text, prompt) are dropped
  by name and unknown fields by default.
- Avatar/VR separation: view and gesture/emotion-animation layers
  are returned apart from decision fields, which are named, never
  merged into the animation layer.
- Availability: derived only from an explicit probe result; no
  probe reports unavailable with zero capabilities — nothing a
  device does not expose is implied. Offline `WorkQueue` holds
  items while offline and flushes each item exactly once.
- CLI: `hermes volmarr world-bridge {status|presence-check}`
  (read-only; status reports live_connection not-claimed).

## Gate evidence

- New battery: `tests/plugins/test_volmarr_world_bridge.py`,
  18 passed / 0 failed (log `~/team03-w11-newtests.log`).
- Full Volmarr/Kista contracts on the team tree via
  `scripts/run_tests.sh` (HERMES_PYTHON staged-env path, the
  accepted W09/W10 fallback): counts recorded in
  CAMPAIGN_STATE_MODERNIZATION.md at banking
  (log `~/team03-w11-contracts.log`).

## Honest remainders (NOT declared complete)

- No live Heimdall/Second Life connection, credentials, rate-limit
  enforcement against a real service, or in-world terms compliance
  check — design-only descriptor only.
- No live WYRD service wiring: world events are contract records;
  the 7 known live-transport contract failures remain
  environment-bound (no live Verdandi/WYRD service on this laptop).
- No live Hlidskjalfr HUD display, no avatar/VR client, no voice
  rooms or 3D rooms (deferred per roadmap section 22/23 until the
  upstream services have real tested interfaces).
- Schema translation is v1-only: other versions are refused by
  name rather than translated; a v0 translator is future work.
- W00.03-ENC backup encryption still awaits Volmarr's word.
