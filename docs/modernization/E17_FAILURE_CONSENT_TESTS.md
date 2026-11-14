# E.17 Per-engine failure / timeout / partial-response and consent tests - audit record (Team 01, 2026-11-14)

**Outcome: TEST PASS EXECUTED - no pin moved, no fork code
changed.** Every row of integration-lock.json /
INTEGRATION_MATRIX.md was audited against four questions:
when the engine (a) fails or errors, (b) times out,
(c) returns a partial or malformed response, and (d) where
consent / egress gates apply, is refusal enforced? Six rows
with live wire or subprocess surfaces were exercised with a
live probe harness against real failure conditions (dead
port, hanging server, garbage body, oversize body, truncated
body, slow / crashing / output-polluting fake engines) -
21 scenarios, all behaving as designed, with elapsed times
recorded. The remaining rows are covered by existing
contract suites, by code inspection, or honestly carry no
testable surface (design-only / documented / blocked) -
never declared complete without live callers (roadmap
section 28.2). Gaps are ticketed E17-T1..T5 below.

## Scope and method

- Tree: worktree ~/hermes-team-01 at banked main
  5c647f9b7b (E.16 closure), clean before edits; branch
  fast-forwarded from 3b96888f8c (verified ancestor).
- Evidence classes used per row: LIVE-PROBED (real adapter
  code driven against a real failure condition in this
  slice), SUITE (existing contract tests in the banked
  tree), CODE (behavior read from the adapter source, no
  live exercise), NO-SURFACE (no adapter exists to test).
- Live harness: ~/team01-e17-live.py, full result
  ~/team01-e17-live-result.json, run under
  scripts/run-in-hermes-env against the real adapter
  modules loaded from this tree (never mocks of the
  surfaces under test). HTTP scenarios use loopback
  ThreadingHTTPServer handlers: dead port (connection
  refused), Hang (accepts, sleeps 30 s), Garbage (200 with
  a non-JSON body), Oversize (256 KiB + 100 bytes),
  Truncated (JSON body cut mid-string). Tarot scenarios
  use fake engine trees in the tests' own fixture pattern
  (slow = 30 s sleep at import, garbage = engine prints a
  stray line to stdout, crash = load_cards raises).

## Live probe results (21 scenarios, all as designed)

A.E.S.I.R. cognition (row 2), probe timeout 200 ms,
request timeout 1,000 ms (the bounded minimum):
- probe vs dead port: unreachable, error_type URLError,
  latency 3 ms.
- probe vs hanging server: unreachable, error_type
  TimeoutError, latency 201 ms - the timeout fires at its
  bound, it does not wait for the server.
- probe vs garbage body: protocol_error, JSONDecodeError.
- probe vs oversize catalog (256 KiB bound): protocol_
  error, ValueError - the read is bounded at MAX + 1.
- completion vs hanging server: CognitionProtocolError
  ("TimeoutError") raised at exactly 1.0 s.
- completion vs truncated body and vs garbage body:
  CognitionProtocolError "completion response has an
  invalid shape" - a partial response is never accepted
  as a completion; shape validation also demands exactly
  one choice and typed usage fields (code).

OpenViking (row 8), probe timeout 200 ms:
- dead port: unreachable / URLError. Hanging server:
  unreachable / TimeoutError at 201 ms. Garbage body:
  protocol_error / JSONDecodeError.
- Consent: base_url http://192.0.2.1:1933 (non-loopback)
  refused as configuration_error BEFORE any network
  traffic - the egress gate is at configuration time.

WYRD (row 10), probe timeout 200 ms: dead port
unreachable / URLError; hanging server unreachable /
TimeoutError at 201 ms; garbage body protocol_error /
JSONDecodeError.

Verdandi (row 1): publish to a missing unix socket
returns False immediately - realtime transport failure is
a fail-open drop (debug log only) and never enters the
agent turn. Socket timeout is bounded by configuration
(timeout_ms default 100, clamped 1..1,000 ms).

MemPalace retrieval (row 6): the official search has no
timeout parameter, so the adapter runs it on a daemon
thread under a bounded join (config 1..30 s). A search
sleeping 5 s with a 1 s bound returned None at 1.0 s -
the turn proceeds without episodes; a raising search
returned None immediately.

RuneTarot (row 13), tool timeout bound 1 s, through the
real tool handler:
- slow engine: {"error": "The local RuneTarot draw timed
  out."} at 1.01 s.
- engine printing a stray stdout line (corrupt/partial
  output): {"error": "The local RuneTarot engine returned
  an invalid response."}
- engine crash: {"error": "The local RuneTarot engine
  could not complete the draw."}
- missing engine root: configuration guidance error,
  engine never started.

## Per-row findings (all 26 rows)

1. Verdandi - LIVE-PROBED + SUITE. Failure = fail-open
   drop (above). Stimuli path: a malformed recent
   response is fail-open and creates no cursor (suite);
   consent = content-free allowlist, only unseen
   allowlisted metadata is applied (suite). One of the 7
   baseline failures is this row's live stimuli test -
   it is in the named live-transport set, unchanged.
2. A.E.S.I.R. - LIVE-PROBED (7 scenarios, above). HTTP
   errors classify 401/403 as authentication_error, other
   codes unreachable (code). Consent: loopback-only is
   enforced before the bearer key is sent (suite),
   redirects are refused before the key can escape
   (suite), the key file must be mode 0600, pattern-valid
   and size-bounded (code). Routing escalates a local
   failure only in auto mode (suite).
3. Bifrost - SUITE + CODE. Probe-only local storage
   meter: missing storage is reported without creating
   it. No network surface; no wire timeout exists.
4./5. Muninn / Huginn (ravens) - SUITE + CODE. Failure =
   named probe reports (package_missing,
   contract_mismatch); write operations validate and
   refuse BEFORE construction, and a profile-escaping
   store path is a configuration error. Consent =
   enablement + validation refusals (22 refusal sites in
   ravens_writes.py). Timeout: NO timeout surface exists
   at this seam - the engines are called in-process and
   synchronously, so the adapter cannot bound a hung
   call (ticket E17-T2). Partial: no wire format; typed
   library returns only.
6. MemPalace - LIVE-PROBED + SUITE. Probe is read-only:
   missing storage / missing collection reported without
   mutation. Retrieval is default-OFF opt-in; timeout
   and failure probed live (above); a failing store
   fails open and other packet producers still render
   (suite).
7. MemPalace mirror - NO-SURFACE: documented only
   (E17-T5).
8. OpenViking - LIVE-PROBED (above). Server unhealthy
   and server outdated are distinguished from unreachable
   (code); health read bounded at 64 KiB + 1 (code);
   the probe sends no credentials (suite); redirects
   refused (code, _NoRedirect).
9. OpenViking mirror - NO-SURFACE: documented only
   (E17-T5).
10. WYRD - LIVE-PROBED (above). Writes: invalid ids and
    queries are rejected before any network call, and
    failed or invalid writes do not publish (suite).
    Loopback-only at configuration time (code).
11. Kista - SUITE + CODE. CLI subprocess timeouts: 5 s
    discovery probes; per-entry cli_timeout_seconds
    default 30 s, clamped to at most 60 s. Failures are
    classified (ErrorKind includes TIMEOUT) without
    echoing CLI output (suite); malformed CLI JSON is a
    classified failure, not a crash (code). Consent: an
    unsafe initialized vault is refused BEFORE the CLI
    is invoked (suite); the canary suite guards against
    secret echo.
12. Astrology - SUITE + CODE. Subprocess runner with
    timeout config default 20 s, clamped 1..60 s;
    TimeoutExpired is caught (code). A zero-exit engine
    error is not reported as success, and engine failure
    never echoes child output (suite). Invalid inputs -
    including a partial query - are rejected before the
    engine starts (suite). Elapsed-timeout firing is not
    suite-tested (E17-T1).
13. RuneTarotEngine - LIVE-PROBED (above). Oversize
    stdout / stderr is a named error (code); invalid
    arguments are rejected before the engine starts
    (suite).
14. Seidr Engine - SUITE + CODE. Same runner pattern as
    row 13 across its tools: timeout default 10 s,
    clamped 1..30 s; TimeoutExpired and JSONDecodeError
    caught per call (code); invalid arguments rejected
    before the engine (suite). Elapsed-timeout firing
    not suite-tested (E17-T1).
15. Hamr - SUITE + CODE. Multiple runners under the
    same timeout clamp; runner-level validation errors
    are distinguished from generic failure; path escape
    is rejected and official validation errors are
    reported (suite). Elapsed-timeout firing not
    suite-tested (E17-T1).
16. Seidr-Smidja - SUITE + CODE. Subprocess calls catch
    (OSError, TimeoutExpired) together; JSON decode is
    guarded (code); discovery validates and reports
    failures without running the forge (suite).
    Elapsed-timeout firing not suite-tested (E17-T1).
17. AIAvatarKit - SUITE. Prototype presentation-shape
    translation only (E.15); translation refuses
    tampering. No transport, so no timeout / partial
    surface exists.
18. Open-LLM-VTuber - NO-SURFACE: design-only,
    reference-only, no adapter (E17-T5).
19. OmniVoice / voice boundary - SUITE. The engine is
    design-only; the fork's voice boundary enforces the
    consent side: admission refuses non-presentation
    inputs with a generic refusal that leaks no detail,
    the listener requires literal IPv4 loopback and a
    bearer token, and the loopback runner refuses bad
    auth, duplicate owner and client input. One of the
    7 baseline failures is this family's live runner
    test - named live-transport set, unchanged.
20. ChatIndex - NO-SURFACE: design-only (E.16, E17-T5).
21. MindSpark / ThoughtForge - NO-SURFACE: design-only
    (E17-T5).
22. SRD data / RPG - SUITE + CODE. In-process: data
    file read failures are caught (OSError, Unicode
    Error, JSONDecodeError -> named failure); lookups
    reject a missing source, an unknown entry and extra
    fields. No timeout surface (local files,
    deterministic).
23. Older fork (provenance) - documented; its live
    surfaces are row 26's modules.
24. Sagnaskemma engine - NO-SURFACE: row is BLOCKED
    (E12-T1); no adapter exists to test (E17-T5).
25. Hermes SessionDB - SUITE + CODE. Read-only audit:
    a missing store is reported and never created;
    sqlite connect timeout is 1.0 s; failures return a
    report carrying the error type, not an exception.
26. Persistent identity / affect / goals / agency -
    SUITE (E.16 live reconciliation stands). Fork-
    internal: no external engine, so no wire timeout or
    partial-response surface. Failure behavior is
    contract-level (the agency cycle journal counts
    failed executions); consent: the affective bridge
    is default-OFF opt-in, proven live in E.16.

## Consent / egress summary (cross-row)

- Loopback-only, enforced at configuration time before
  any traffic or credential use: A.E.S.I.R. (row 2),
  OpenViking (row 8, live-probed with a non-loopback
  address), WYRD (row 10), voice listener (row 19).
- Redirect refusal on every HTTP adapter (_NoRedirect):
  a bearer key or probe can never be redirected off
  loopback.
- Allowlists: Verdandi stimuli apply only unseen,
  allowlisted, content-free metadata (row 1).
- Opt-in, fail-closed: MemPalace retrieval default-OFF
  (row 6), affective bridge default-OFF (row 26),
  telemetry sharing refused without opt-in and to cloud
  endpoints (edge_research suite), production data-flow
  private egress refused by name without a complete
  election (production suite, 29 tests).
- Refuse-before-effect: ravens writes validate before
  construction (rows 4/5), Kista refuses an unsafe vault
  before invoking its CLI (row 11), world-bridge imports
  refuse unknown schema / unsupported version / hash
  mismatch by name (suite).
- Bounded everything: every wire read is size-bounded
  (catalog 256 KiB, completion 1 MiB, health 64 KiB)
  and every wait is time-bounded except the in-process
  ravens seam ticketed at E17-T2.

## Proofs

- Proof 1 - live harness: PASS. 21 scenarios above;
  script ~/team01-e17-live.py, result
  ~/team01-e17-live-result.json.
- Proof 2 - targeted contracts: the 27-file targeted set
  (every suite named in the findings, plus the ledger
  battery) via the serialized waiter, log
  ~/team01-e17-targeted.log. Expected: all pass except
  the 2 baseline live-transport failures inside this
  slice's area (verdandi stimuli allowlist test, voice
  loopback runner test), name-identical to the banked
  baseline set.
- Proof 3 - full gate: PENDING at commit, waiter-armed.
  The canonical 137-file set runs behind the same waiter
  (~/team01-e17-gate-waiter.sh) to
  ~/team01-e17-fullcontracts.log with marker
  ~/team01-e17-gate.done. Expected verdict, to be
  verified by the keeper before banking: 137 files =
  1,171 passed / 7 failed / 1 skipped, the 7
  name-identical to the known live-transport set - zero
  regressions. This record is NOT amended after the
  fact; the keeper's banking closure carries the
  verified counts.

## Pin / record status

- ALL pins UNMOVED. No row's pinned or current_head
  value changed; update_needed unchanged everywhere.
- integration-lock.json + INTEGRATION_MATRIX.md: only
  the six LIVE-PROBED rows (1 Verdandi, 2 A.E.S.I.R.,
  6 MemPalace, 8 OpenViking, 10 WYRD, 13 RuneTarot
  Engine) gained an E.17 note on their verdict; every
  other row's record is untouched - the per-row evidence
  for the rest lives in this record.
- Verification tally does not move: 25 verified / 0
  partially verified / 1 blocked (Sagnaskemma, E12-T1).
  E.17 deepens evidence; it changes no status.
- No adapter or code change: no fork code was modified
  in this slice, so no CUSTOMIZATIONS.md row (E.15 /
  E.16 precedent).
- README.md untouched (sha256
  336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3
  before and after).

## Honest remainders (named, not hidden)

- **E17-T1** (elapsed-timeout firing untested in the
  subprocess family): rows 12, 14, 15, 16 (and the
  Kista CLI path, row 11) catch TimeoutExpired in code,
  and row 13 is now live-probed, but no contract suite
  drives a fake slow engine to prove the timeout fires
  at its bound for the other plugins. Follow-up test
  slice: reuse this slice's fake-engine pattern per
  plugin (slow import + tiny timeout config) and add
  hang/garbage loopback fixtures for the HTTP probes
  (rows 2, 8, 10 - live-probed here, not yet in the
  suites).
- **E17-T2** (ravens seam has no timeout): Muninn /
  Huginn are called in-process and synchronously; a hung
  engine call would block the turn and the adapter has
  no bound. The daemon-thread bounded-join pattern
  exists in-tree (row 6 retrieval) as a precedent, but
  applying it changes call semantics - a design
  decision, not an audit fix. Recorded, not improvised.
- **E17-T3** (Verdandi blackhole socket untested): the
  publish timeout is bounded (1..1,000 ms) and the
  missing-socket drop is live-probed, but no probe or
  suite covers a socket that accepts and never reads.
  The payload is a single small send, so exposure is
  one bounded send timeout; recorded honestly.
- **E17-T4** (fail-open is a posture, not a proof of
  delivery): rows 1 and 6 deliberately fail open - a
  dropped Verdandi event or a skipped MemPalace episode
  is silent at debug level by design (W08 posture).
  E.17 verifies the drop is bounded and honest; it does
  not add delivery guarantees, and none are claimed.
- **E17-T5** (no-surface rows): rows 7, 9, 18, 20, 21
  and 24 are documented / design-only / blocked and
  have no adapter whose failure behavior could be
  tested. Not a defect; each must pass this same four-
  question audit in the slice that first builds its
  adapter.
- The 7 baseline failures remain exactly the named
  live-transport set; two of them (Verdandi stimuli,
  voice loopback runner) sit inside E.17's audit area
  and are unchanged by this slice - they are not
  regressions and are not hidden by this record.
