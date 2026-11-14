"""Read-only attachment probe for the official WYRD HTTP world-model service."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit


DEFAULT_BASE_URL = "http://127.0.0.1:8765"
DEFAULT_PROBE_TIMEOUT_MS = 2_000
MINIMUM_SERVER_VERSION = "1.0.0"
API_CONTRACT = "wyrd-http-v1"
MAX_HEALTH_BYTES = 64 * 1024
_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[.+-][0-9A-Za-z.-]+)?$")


class WyrdConfigurationError(ValueError):
    """The configured service crosses the initial loopback-only boundary."""


class WyrdProtocolError(ValueError):
    """The local service did not satisfy the bounded WYRD HTTP contract."""


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = _VERSION_RE.fullmatch(value.strip())
    if not match:
        raise ValueError("WYRD health response has an invalid version")
    return tuple(int(part) for part in match.groups())


def _loopback_base_url(value: Any) -> str:
    raw = str(value or DEFAULT_BASE_URL).strip().rstrip("/")
    parsed = urlsplit(raw)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise WyrdConfigurationError(
            "initial WYRD attachment must be plain HTTP on 127.0.0.1"
        )
    try:
        port = parsed.port
    except ValueError as exc:
        raise WyrdConfigurationError("WYRD endpoint has an invalid port") from exc
    if port is None or not 1 <= port <= 65535:
        raise WyrdConfigurationError("WYRD endpoint requires an explicit port")
    return urlunsplit(("http", f"127.0.0.1:{port}", "", "", ""))


def _bounded_timeout(value: Any) -> float:
    if isinstance(value, bool):
        value = DEFAULT_PROBE_TIMEOUT_MS
    try:
        timeout_ms = int(value)
    except (TypeError, ValueError, OverflowError):
        timeout_ms = DEFAULT_PROBE_TIMEOUT_MS
    return min(10_000, max(50, timeout_ms)) / 1_000


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open_local(request: urllib.request.Request, timeout: float):
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        _NoRedirect(),
    )
    return opener.open(request, timeout=timeout)


def request_wyrd_json(
    ctx,
    path: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call one allowlisted local WYRD route with bounded JSON transport."""
    if not path.startswith("/") or "#" in path:
        raise WyrdProtocolError("invalid WYRD request path")
    base_url = _loopback_base_url(ctx.get_config("wyrd_base_url", DEFAULT_BASE_URL))
    timeout = _bounded_timeout(
        ctx.get_config("wyrd_probe_timeout_ms", DEFAULT_PROBE_TIMEOUT_MS)
    )
    encoded = None
    headers = {
        "Accept": "application/json",
        "User-Agent": "runeforgeai-hermes-wyrd-tools/1",
    }
    if body is not None:
        encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        if len(encoded) > 32 * 1024:
            raise WyrdProtocolError("WYRD request exceeds 32 KiB")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=encoded,
        method=method,
        headers=headers,
    )
    try:
        with _open_local(request, timeout) as response:
            raw = response.read(MAX_HEALTH_BYTES + 1)
    except urllib.error.HTTPError as exc:
        if exc.code in {301, 302, 303, 307, 308}:
            raise WyrdProtocolError("WYRD refused a redirected response") from exc
        raise WyrdProtocolError(f"WYRD returned HTTP {exc.code}") from exc
    except Exception as exc:
        raise WyrdProtocolError("WYRD service is unreachable") from exc
    if len(raw) > MAX_HEALTH_BYTES:
        raise WyrdProtocolError("WYRD response exceeds 64 KiB")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WyrdProtocolError("WYRD response is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise WyrdProtocolError("WYRD response is not an object")
    return payload


@dataclass(frozen=True)
class WyrdHealth:
    healthy: bool
    status: str
    base_url: str
    api_contract: str = API_CONTRACT
    server_version: str | None = None
    minimum_server_version: str = MINIMUM_SERVER_VERSION
    latency_ms: int | None = None
    error_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def probe_wyrd(ctx) -> WyrdHealth:
    """Probe the official read-only liveness contract without credentials or writes."""
    configured = ctx.get_config("wyrd_base_url", DEFAULT_BASE_URL)
    try:
        base_url = _loopback_base_url(configured)
        timeout = _bounded_timeout(
            ctx.get_config("wyrd_probe_timeout_ms", DEFAULT_PROBE_TIMEOUT_MS)
        )
    except Exception as exc:
        return WyrdHealth(
            False,
            "configuration_error",
            str(configured),
            error_type=type(exc).__name__,
        )

    request = urllib.request.Request(
        f"{base_url}/health",
        headers={
            "Accept": "application/json",
            "User-Agent": "runeforgeai-hermes-wyrd-health/1",
        },
    )
    started = time.monotonic()
    try:
        with _open_local(request, timeout) as response:
            raw = response.read(MAX_HEALTH_BYTES + 1)
        latency_ms = max(0, round((time.monotonic() - started) * 1_000))
        if len(raw) > MAX_HEALTH_BYTES:
            raise ValueError("WYRD health response exceeds 64 KiB")
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("WYRD health response is not an object")
        version = payload.get("version")
        if version is not None and not isinstance(version, str):
            raise ValueError("WYRD health response has an invalid version")
        if payload.get("status") != "ok":
            return WyrdHealth(
                False,
                "server_unhealthy",
                base_url,
                server_version=version,
                latency_ms=latency_ms,
            )
        # The official 1.0.0 implementation returns only {"status": "ok"},
        # while its published HTTP documentation also shows a version field.
        # Accept both. If a server volunteers a version, enforce the minimum.
        if version is not None and _version_tuple(version) < _version_tuple(
            MINIMUM_SERVER_VERSION
        ):
            return WyrdHealth(
                False,
                "server_outdated",
                base_url,
                server_version=version,
                latency_ms=latency_ms,
            )
        return WyrdHealth(
            True,
            "healthy",
            base_url,
            server_version=version,
            latency_ms=latency_ms,
        )
    except urllib.error.HTTPError as exc:
        latency_ms = max(0, round((time.monotonic() - started) * 1_000))
        status = (
            "protocol_error"
            if exc.code in {301, 302, 303, 307, 308}
            else "unreachable"
        )
        return WyrdHealth(False, status, base_url, latency_ms=latency_ms)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        latency_ms = max(0, round((time.monotonic() - started) * 1_000))
        return WyrdHealth(
            False,
            "protocol_error",
            base_url,
            latency_ms=latency_ms,
            error_type=type(exc).__name__,
        )
    except Exception as exc:
        latency_ms = max(0, round((time.monotonic() - started) * 1_000))
        return WyrdHealth(
            False,
            "unreachable",
            base_url,
            latency_ms=latency_ms,
            error_type=type(exc).__name__,
        )


# ======================================================================
# X.04 upgrade (roadmap section 39, ecosystem workstream 4 of 15)
#
# The E.07 slice moved the WYRD pin to the official package
# v1.5.0 at development HEAD 89ed09394c7e and verified the
# existing adapter against it. This section upgrades that SAME
# adapter -- there is still exactly one world connector -- with
# the section 39 semantics the engine's audited contract
# supports: capability negotiation with truthful version
# mismatch, namespaced source-linked references, explicit truth
# classes (durable canonical facts vs tentative observations vs
# quoted external evidence vs fictional game state), a durable
# transactional/idempotent write journal with revision checks
# and replay, deterministic conflict resolution with causal
# provenance, bounded provenance-bearing prompt packets, event
# subscriptions / streaming over the verified HTTP contract
# (the pinned server exposes no push endpoint, so streaming is
# bounded polling -- stated here, never dressed up as push),
# and authorized-consumer seams. Identities and private
# relationship memories stay OUTSIDE WYRD (section 39 item 9):
# the write paths below refuse those fact kinds by name.
# ======================================================================

import hashlib
import sqlite3
from pathlib import Path

SOURCE_REPO = "hrabanazviking/WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model"
SOURCE_BRANCH = "development"
SOURCE_PIN = "89ed09394c7e13b2e63f91e342fbab8ff9890cbc"
SOURCE_PACKAGE_VERSION = "1.5.0"
SOURCE_LICENSE = ("CC BY 4.0 (README License section + pyproject "
                  "declaration verified in E.07, 2026-11-13; no "
                  "standalone LICENSE file)")
RECORD_SCHEMA_VERSION = "1.0.0"
SUPPORTED_API_VERSIONS = (1,)
ENGINE_STORE_SCHEMA = {"world_store": 2, "memory_store": 1,
                       "event_journal": 1}
ADAPTER_METHODS = ("liveness", "capabilities", "snapshot",
                   "facts", "query", "subscribe", "stream",
                   "write_fact", "write_observation")
TRUTH_CLASSES = ("canonical_fact", "tentative_observation",
                 "quoted_evidence", "fictional_state")
_CLASS_RANK = {"canonical_fact": 3, "quoted_evidence": 2,
               "tentative_observation": 1, "fictional_state": 0}
PRIVATE_FACT_PREFIXES = ("identity.", "relationship.",
                         "private.", "persona_identity.")
PRIVATE_RECORD_KINDS = frozenset(
    {"identity", "relationship", "relationship_memory",
     "private_memory", "persona_identity"})
_NAMESPACE_RE = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{0,63})$")
_COMPONENT_RE = re.compile(r"^[a-z0-9](?:[a-z0-9_.-]{0,63})$")


class WyrdError(Exception):
    """Named refusal in the X.04 adapter layer."""

    def __init__(self, name: str, detail: str) -> None:
        super().__init__(f"{name}: {detail}")
        self.name = name
        self.detail = detail


def _major(version: Any) -> int | None:
    if not isinstance(version, str):
        return None
    head = version.strip().lstrip("v").split(".", 1)[0]
    return int(head) if head.isdigit() else None


def check_record_schema_version(version: Any) -> str:
    """Fail truthfully on an incompatible record schema revision.

    Canonical world data is NEVER silently migrated between
    incompatible schema revisions (section 39 item 10): a
    major-version mismatch raises version_mismatch by name."""
    if version is None:
        return RECORD_SCHEMA_VERSION
    if _major(version) != _major(RECORD_SCHEMA_VERSION):
        raise WyrdError(
            "version_mismatch",
            f"record schema {version!r} is incompatible with "
            f"the adapter record schema {RECORD_SCHEMA_VERSION}; "
            "canonical world data is not silently migrated "
            "between incompatible schema revisions (section 39)")
    return str(version)


def negotiate_capabilities(health: dict | None = None, *,
                             api_version: Any = None,
                             server_version: Any = None,
                             record_schema_version: Any = None) -> dict:
    """Capability negotiation against one liveness reading.

    Distinct from liveness: liveness says the server answers;
    negotiation says whether what it answers is a contract this
    adapter can speak. Every incompatibility is named in
    ``mismatches`` -- nothing is silently adapted to."""
    mismatches: list[str] = []
    reachable = bool(health and health.get("healthy"))
    status = (health or {}).get("status", "unreachable")
    version = server_version
    if version is None and health:
        version = health.get("server_version")
    if api_version is not None:
        try:
            api_major = int(api_version)
        except (TypeError, ValueError):
            api_major = None
        if api_major not in SUPPORTED_API_VERSIONS:
            mismatches.append(
                f"api_version {api_version!r} not in supported "
                f"{list(SUPPORTED_API_VERSIONS)}")
    if version is not None:
        try:
            if _version_tuple(str(version)) < _version_tuple(
                    MINIMUM_SERVER_VERSION):
                mismatches.append(
                    f"server_version {version} below minimum "
                    f"{MINIMUM_SERVER_VERSION}")
        except ValueError:
            mismatches.append(
                f"server_version {version!r} is not a version")
    if record_schema_version is not None and \
            _major(record_schema_version) != _major(RECORD_SCHEMA_VERSION):
        mismatches.append(
            f"record schema {record_schema_version!r} incompatible "
            f"with {RECORD_SCHEMA_VERSION} (no silent migration)")
    compatible: bool | None
    if not reachable:
        compatible = None
    else:
        compatible = not mismatches
    return {
        "schema": "runeforge.wyrd.capabilities.v1",
        "service": "volmarr-wyrd",
        "api_contract": API_CONTRACT,
        "supported_api_versions": list(SUPPORTED_API_VERSIONS),
        "minimum_server_version": MINIMUM_SERVER_VERSION,
        "record_schema_version": RECORD_SCHEMA_VERSION,
        "engine_store_schema": dict(ENGINE_STORE_SCHEMA),
        "source_pin": SOURCE_PIN,
        "source_package_version": SOURCE_PACKAGE_VERSION,
        "methods": list(ADAPTER_METHODS),
        "server": {"reachable": reachable, "status": status,
                   "version": version},
        "compatible": compatible,
        "mismatches": mismatches,
    }


def require_compatible(caps: dict) -> dict:
    if caps.get("compatible") is False:
        raise WyrdError(
            "version_mismatch",
            "WYRD capability negotiation failed: "
            + "; ".join(caps.get("mismatches") or ["unknown"]))
    return caps


# ------------------------------------------------------------ references

def valid_namespace(value: Any) -> bool:
    return isinstance(value, str) and bool(_NAMESPACE_RE.fullmatch(value))


def make_ref(namespace: str, entity_id: str,
             component: str | None = None) -> str:
    """One source-linked entity/component reference."""
    if not valid_namespace(namespace):
        raise WyrdError("record_malformed",
                        f"namespace {namespace!r} is not a valid "
                        "world namespace")
    if not isinstance(entity_id, str) or \
            not re.fullmatch(r"[a-z0-9](?:[a-z0-9_]{0,63})", entity_id):
        raise WyrdError("record_malformed",
                        f"entity_id {entity_id!r} is not a valid "
                        "WYRD entity id")
    ref = f"wyrd://{namespace}/{entity_id}"
    if component is not None:
        if not _COMPONENT_RE.fullmatch(component):
            raise WyrdError("record_malformed",
                            f"component {component!r} is invalid")
        ref += f"#{component}"
    return ref


def parse_ref(ref: Any) -> dict:
    if not isinstance(ref, str) or not ref.startswith("wyrd://"):
        raise WyrdError("record_malformed",
                        f"reference {ref!r} is not a wyrd:// ref")
    rest = ref[len("wyrd://"):]
    namespace, _, tail = rest.partition("/")
    entity_id, _, component = tail.partition("#")
    if not valid_namespace(namespace) or not entity_id:
        raise WyrdError("record_malformed",
                        f"reference {ref!r} lacks namespace/entity")
    return {"namespace": namespace, "entity_id": entity_id,
            "component": component or None}


# ------------------------------------------------------------ world records

def _require_provenance(provenance: Any) -> dict:
    if not isinstance(provenance, dict) or \
            not provenance.get("source"):
        raise WyrdError(
            "record_malformed",
            "provenance.source is required: every world record "
            "carries causal provenance (section 39 item 7)")
    return {
        "source": str(provenance["source"]),
        "source_ref": provenance.get("source_ref"),
        "observed_at": provenance.get("observed_at", ""),
        "caused_by": provenance.get("caused_by"),
    }


def build_world_record(*, namespace: str, entity_id: str,
                       truth_class: str, key: str = "",
                       value: str = "", title: str = "",
                       summary: str = "", confidence: float = 0.5,
                       provenance: dict | None = None,
                       kind: str = "", reality: str = "real",
                       revision: int = 0,
                       idempotency_key: str = "",
                       recorded_at: str = "") -> dict:
    """Build one validated world record in exactly one truth class.

    The four classes are kept distinct by construction
    (section 39 item 4): a canonical fact is durable and needs
    full provenance; a tentative observation can never present
    itself as durable canon; quoted evidence must name the
    source it quotes; fictional game state carries the
    fictional reality tag and can never validate as a canonical
    fact about the real world. Identity / private relationship
    material is refused by name (item 9)."""
    if kind in PRIVATE_RECORD_KINDS or \
            any(key.startswith(p) for p in PRIVATE_FACT_PREFIXES):
        raise WyrdError(
            "private_memory_refused",
            "identities and private relationship memories stay "
            "outside WYRD (section 39 item 9); no world record "
            "is built for them")
    if truth_class not in TRUTH_CLASSES:
        raise WyrdError("record_malformed",
                        f"truth_class {truth_class!r} is not one "
                        f"of {list(TRUTH_CLASSES)}")
    prov = _require_provenance(provenance)
    if truth_class == "canonical_fact":
        if not key or not value:
            raise WyrdError("record_malformed",
                            "a canonical fact needs key and value")
        if not prov.get("source_ref"):
            raise WyrdError(
                "record_malformed",
                "a durable canonical fact needs provenance."
                "source_ref (the durable source it rests on)")
    elif truth_class == "tentative_observation":
        if not (title or summary):
            raise WyrdError("record_malformed",
                            "an observation needs title or summary")
    elif truth_class == "quoted_evidence":
        if not prov.get("source_ref"):
            raise WyrdError(
                "record_malformed",
                "quoted external evidence must name the source "
                "it quotes (provenance.source_ref)")
        if not (summary or value):
            raise WyrdError("record_malformed",
                            "quoted evidence needs quoted content")
    elif truth_class == "fictional_state":
        if reality != "fictional":
            raise WyrdError(
                "record_malformed",
                "fictional game state must carry reality "
                "\"fictional\"; it is never real-world canon")
        if not key or not value:
            raise WyrdError("record_malformed",
                            "fictional state needs key and value")
    if isinstance(confidence, bool) or \
            not isinstance(confidence, (int, float)) or \
            not 0.0 <= float(confidence) <= 1.0:
        raise WyrdError("record_malformed",
                        "confidence must be a number in [0, 1]")
    ref = make_ref(namespace, entity_id, key or None)
    digest_src = "|".join([namespace, entity_id, truth_class, key,
                            value, title, summary,
                            str(prov.get("source_ref") or ""),
                            idempotency_key])
    record_id = "wr-" + hashlib.sha256(
        digest_src.encode("utf-8")).hexdigest()[:16]
    return {
        "schema": "runeforge.wyrd.record.v1",
        "record_schema_version": RECORD_SCHEMA_VERSION,
        "record_id": record_id,
        "ref": ref,
        "namespace": namespace,
        "entity_id": entity_id,
        "truth_class": truth_class,
        "durable": truth_class == "canonical_fact",
        "key": key, "value": value,
        "title": title, "summary": summary,
        "confidence": float(confidence),
        "reality": reality,
        "provenance": prov,
        "revision": int(revision),
        "idempotency_key": idempotency_key,
        "recorded_at": recorded_at,
    }


def validate_world_record(record: Any) -> dict:
    if not isinstance(record, dict):
        raise WyrdError("record_malformed", "record not a dict")
    if record.get("schema") != "runeforge.wyrd.record.v1":
        raise WyrdError("record_malformed", "wrong schema")
    check_record_schema_version(record.get("record_schema_version"))
    cls = record.get("truth_class")
    if cls not in TRUTH_CLASSES:
        raise WyrdError("record_malformed", "truth_class")
    if record.get("durable") is not (cls == "canonical_fact"):
        raise WyrdError(
            "record_malformed",
            "durability must match the truth class: only "
            "canonical facts are durable (section 39 item 4)")
    if cls == "fictional_state" and record.get("reality") != "fictional":
        raise WyrdError(
            "record_malformed",
            "fictional state validated without its fictional "
            "reality tag")
    if cls == "canonical_fact" and record.get("reality") == "fictional":
        raise WyrdError(
            "record_malformed",
            "fictional state can never validate as a canonical "
            "fact about the real world")
    parsed = parse_ref(record.get("ref"))
    if parsed["namespace"] != record.get("namespace") or \
            parsed["entity_id"] != record.get("entity_id"):
        raise WyrdError("record_malformed",
                        "ref does not match namespace/entity")
    _require_provenance(record.get("provenance"))
    return record


def resolve_conflict(records: list) -> dict:
    """Deterministic resolution of competing records for one slot.

    All records must address the same (namespace, entity, key).
    Rule, in order: canonical fact outranks quoted evidence,
    which outranks a tentative observation, which outranks
    fictional state; within a class, higher confidence wins,
    then the later causal observation time, then the smallest
    record_id (a stable, content-derived tiebreak). Every
    competing record is returned in ``superseded`` with the
    full causal provenance preserved -- nothing is silently
    dropped (section 39 item 7)."""
    if not records:
        raise WyrdError("record_malformed",
                        "no records to resolve")
    for record in records:
        validate_world_record(record)
    slots = {(r["namespace"], r["entity_id"], r["key"])
             for r in records}
    if len(slots) != 1:
        raise WyrdError(
            "record_malformed",
            "conflict resolution needs competing records for "
            "exactly one (namespace, entity, key) slot")

    def rank(r):
        return (_CLASS_RANK[r["truth_class"]],
                r.get("confidence", 0.5),
                (r.get("provenance") or {}).get("observed_at", ""))

    ordered = sorted(records, key=lambda r: r["record_id"])
    winner = ordered[0]
    for candidate in ordered[1:]:
        if rank(candidate) > rank(winner):
            winner = candidate
    superseded = [r for r in ordered if r is not winner]
    return {
        "schema": "runeforge.wyrd.conflict-resolution.v1",
        "slot": {"namespace": winner["namespace"],
                 "entity_id": winner["entity_id"],
                 "key": winner["key"]},
        "winner": winner,
        "superseded": superseded,
        "rule": "truth-class rank, then confidence, then later "
                "observed_at, then smallest record_id",
        "causal_provenance": [
            {"record_id": r["record_id"],
             "provenance": r["provenance"]} for r in ordered],
    }


# ------------------------------------------------------------ write journal

class WyrdJournal:
    """Durable adapter-side write journal (SQLite, WAL).

    The pinned WYRD HTTP contract confirms a write with
    ``{"ok": true}`` but exposes no transaction or idempotency
    surface of its own, so transactional discipline lives here,
    in the adapter (section 39 item 5): a write is committed to
    this journal ONLY after the server confirms it through the
    injected sender; an unconfirmed write leaves no trace and
    bumps no revision. Re-committing the same idempotency key
    with the same payload is a no-op duplicate (the sender is
    not called again); the same key with a different payload is
    refused by name. A write whose expected revision does not
    match the journal's current revision for its slot is a
    stale write and is rejected before any traffic. Replaying
    the journal folds committed events in sequence order and
    is idempotent: replaying twice yields the identical state,
    and a fresh journal object over the same file (a restart)
    replays the identical state too. Journals at different
    paths are fully isolated (profile isolation)."""

    def __init__(self, path: Any) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._connect()
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS wyrd_events ("
                "seq INTEGER PRIMARY KEY AUTOINCREMENT, "
                "idempotency_key TEXT UNIQUE, payload_hash TEXT, "
                "namespace TEXT, entity_id TEXT, fact_key TEXT, "
                "value TEXT, truth_class TEXT, revision INTEGER, "
                "record_json TEXT)")
            conn.commit()
        finally:
            conn.close()

    @property
    def path(self) -> Path:
        return self._path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        return conn

    @staticmethod
    def _payload_hash(entry: dict) -> str:
        blob = json.dumps(
            {k: entry.get(k) for k in (
                "namespace", "entity_id", "key", "value",
                "truth_class", "title", "summary")},
            sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def current_revision(self, namespace: str, entity_id: str,
                         key: str) -> int:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT MAX(revision) FROM wyrd_events WHERE "
                "namespace=? AND entity_id=? AND fact_key=?",
                (namespace, entity_id, key)).fetchone()
        finally:
            conn.close()
        return int(row[0]) if row and row[0] is not None else 0

    def commit(self, entry: dict, *, sender) -> dict:
        """One transactional, idempotent write.

        ``sender(entry) -> bool`` performs the server write and
        returns the server's confirmation. Order of checks:
        private-kind refusal, idempotency, revision, THEN the
        sender; the journal row is written only on confirmation,
        in the same step that reports the new revision."""
        key_name = str(entry.get("key") or "")
        if any(key_name.startswith(p) for p in PRIVATE_FACT_PREFIXES):
            raise WyrdError(
                "private_memory_refused",
                "identities and private relationship memories "
                "stay outside WYRD (section 39 item 9)")
        idem = str(entry.get("idempotency_key") or "")
        payload_hash = self._payload_hash(entry)
        conn = self._connect()
        try:
            if idem:
                row = conn.execute(
                    "SELECT payload_hash, revision FROM "
                    "wyrd_events WHERE idempotency_key=?",
                    (idem,)).fetchone()
                if row is not None:
                    if row[0] != payload_hash:
                        raise WyrdError(
                            "idempotency_conflict",
                            "idempotency key already committed "
                            "with a different payload; the write "
                            "is refused, never silently merged")
                    return {"status": "duplicate",
                            "revision": int(row[1]),
                            "idempotency_key": idem,
                            "sender_called": False}
            current = self.current_revision(
                entry["namespace"], entry["entity_id"], key_name)
            expected = entry.get("expected_revision")
            if expected is not None and int(expected) != current:
                raise WyrdError(
                    "stale_write_rejected",
                    f"expected revision {expected} but the "
                    f"current revision for this slot is {current}; "
                    "the stale write is rejected before any "
                    "traffic (section 39 item 7)")
        finally:
            conn.close()
        confirmed = bool(sender(entry))
        if not confirmed:
            return {"status": "unconfirmed", "revision": current,
                    "idempotency_key": idem, "sender_called": True}
        new_revision = current + 1
        record = dict(entry)
        record["revision"] = new_revision
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO wyrd_events (idempotency_key, "
                "payload_hash, namespace, entity_id, fact_key, "
                "value, truth_class, revision, record_json) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (idem or None, payload_hash, entry["namespace"],
                 entry["entity_id"], key_name,
                 str(entry.get("value") or ""),
                 str(entry.get("truth_class") or ""),
                 new_revision,
                 json.dumps(record, ensure_ascii=False,
                            sort_keys=True)))
            conn.commit()
        finally:
            conn.close()
        return {"status": "committed", "revision": new_revision,
                "idempotency_key": idem, "sender_called": True}

    def events(self) -> list:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT record_json FROM wyrd_events "
                "ORDER BY seq").fetchall()
        finally:
            conn.close()
        return [json.loads(row[0]) for row in rows]

    def replay(self) -> dict:
        """Fold committed events into current state, in order.

        Pure with respect to the journal: replaying any number
        of times yields the identical state (idempotent event
        replay, section 39 test gate)."""
        state: dict[str, Any] = {}
        for event in self.events():
            slot = (f"{event['namespace']}/{event['entity_id']}/"
                    f"{event.get('key') or ''}")
            state[slot] = {
                "value": event.get("value", ""),
                "truth_class": event.get("truth_class", ""),
                "revision": event.get("revision", 0),
                "record_id": event.get("record_id"),
                "ref": event.get("ref"),
                "provenance": event.get("provenance"),
            }
        return state


# ------------------------------------------------------------ prompt packets

def build_prompt_packet(items: list, *, max_chars: int = 4000,
                        max_items: int = 32) -> dict:
    """One bounded, provenance-bearing prompt packet.

    Retrieval NEVER dumps the entire world database into a
    prompt (section 39 item 6): at most ``max_items`` items and
    ``max_chars`` of item text are carried, higher-priority
    items first, and every item keeps its source-linked ref and
    its provenance, so an agent prompt can always be traced to
    the world records it came from (prompt provenance gate).
    Overflow is reported (``truncated`` / ``omitted``), never
    silent."""
    max_chars = max(64, int(max_chars))
    max_items = max(1, int(max_items))
    ordered = sorted(
        enumerate(items),
        key=lambda pair: (-float(pair[1].get("priority", 0.0)),
                          pair[0]))
    kept: list = []
    used = 0
    truncated = False
    for _idx, item in ordered:
        if len(kept) >= max_items:
            truncated = True
            break
        text = str(item.get("text") or "")
        remaining = max_chars - used
        if remaining <= 0:
            truncated = True
            break
        if len(text) > remaining:
            text = text[: remaining - 1].rstrip() + "\u2026" \
                if remaining > 1 else "\u2026"
            truncated = True
        kept.append({
            "ref": item.get("ref"),
            "text": text,
            "provenance": item.get("provenance"),
            "truth_class": item.get("truth_class"),
        })
        used += len(text)
    return {
        "schema": "runeforge.wyrd.prompt-packet.v1",
        "items": kept,
        "item_count": len(kept),
        "total_chars": used,
        "max_chars": max_chars,
        "max_items": max_items,
        "truncated": truncated,
        "omitted": len(items) - len(kept) if truncated else 0,
    }


# ------------------------------------------------------------ consumer seams

CONSUMER_SEAMS = {
    "heimdall": {
        "consumer": "Heimdall / Second Life presence (X.03)",
        "namespace": "second-life",
        "allowed": ["submit_qualified_observation", "read_query"],
        "refused": ["write_canonical_fact", "read_private_memory"],
        "truth_class": "tentative_observation",
        "note": "presence arrives as qualified observations "
                "only, never accepted world truth (section 38.5)",
    },
    "sagnaskemma": {
        "consumer": "Sagnaskemma table world",
        "namespace": "sagnaskemma-campaign",
        "allowed": ["write_fictional_state", "read_query"],
        "refused": ["write_canonical_fact"],
        "truth_class": "fictional_state",
        "note": "game state lives in its own fictional "
                "namespace; roleplay events never mix with "
                "real-world observations (section 40.7)",
    },
    "voice_avatar": {
        "consumer": "voice / avatar embodiment",
        "namespace": None,
        "allowed": ["read_query", "read_snapshot"],
        "refused": ["write_canonical_fact", "write_observation"],
        "truth_class": None,
        "note": "embodiment reads world state; it does not "
                "author it",
    },
    "local_sensors": {
        "consumer": "optional local sensors",
        "namespace": "local-sensors",
        "allowed": ["submit_observation_with_uncertainty"],
        "refused": ["write_canonical_fact"],
        "truth_class": "tentative_observation",
        "note": "every sensor observation must carry its "
                "uncertainty (a confidence value)",
    },
}


def consumer_seams() -> list:
    return [{"name": name, **seam}
            for name, seam in sorted(CONSUMER_SEAMS.items())]


def authorize_consumer(consumer: Any, operation: Any, *,
                       confidence: Any = None) -> dict:
    """Gate one consumer operation at its seam (item 8).

    Seams only: the consumers themselves are not built here.
    Unknown consumers and unlisted operations are refused by
    name; there is no silent default in either direction."""
    seam = CONSUMER_SEAMS.get(consumer) \
        if isinstance(consumer, str) else None
    if seam is None:
        raise WyrdError(
            "unknown_consumer_refused",
            f"consumer {consumer!r} has no authorized WYRD "
            "seam; authorized consumers are "
            f"{sorted(CONSUMER_SEAMS)}")
    if operation in seam["refused"] or \
            operation not in seam["allowed"]:
        raise WyrdError(
            "consumer_operation_refused",
            f"consumer {consumer!r} may not perform "
            f"{operation!r} at the WYRD seam; allowed here: "
            f"{seam['allowed']}")
    if operation == "submit_observation_with_uncertainty" and \
            confidence is None:
        raise WyrdError(
            "uncertainty_required",
            "local sensor observations must carry clear "
            "uncertainty (a confidence value) (section 39.8)")
    return {"consumer": consumer, "operation": operation,
            "allowed": True, "namespace": seam["namespace"],
            "truth_class": seam["truth_class"]}


# ------------------------------------------------------------ the adapter

Transport = Any  # callable(method, path, body=None) -> dict payload


def _default_transport(ctx) -> Any:
    def _call(method: str, path: str, body: dict | None = None):
        return request_wyrd_json(ctx, path, method=method, body=body)
    return _call


def _entity_id_of(row: Any) -> str | None:
    if isinstance(row, str):
        return row
    if isinstance(row, dict):
        value = row.get("entity_id") or row.get("id")
        return value if isinstance(value, str) else None
    return None


class WyrdAdapter:
    """The one WYRD adapter, upgraded in place (section 39.2).

    Distinct methods per capability (item 3): ``liveness``,
    ``capabilities``, ``snapshot``, ``facts`` and ``query``
    (read-only), ``subscribe`` / ``poll_once`` / ``stream``
    (event subscriptions and streaming state changes), and
    ``write_fact`` / ``write_observation`` (transactional
    writes). The transport is injectable so contracts can be
    proven against a capturing fake; the default transport is
    the pre-existing bounded loopback HTTP contract above."""

    def __init__(self, ctx, *, transport=None, journal=None,
                 telemetry=None) -> None:
        self._ctx = ctx
        self._transport = transport or _default_transport(ctx)
        self._injected = transport is not None
        self._journal = journal
        self._telemetry = telemetry
        self._subscribers: dict[str, list] = {}
        self._last_snapshot_hash: str | None = None
        self._last_snapshot: dict | None = None

    # -- reads --------------------------------------------------

    def liveness(self) -> dict:
        """Liveness only: does the server answer /health?"""
        if not self._injected:
            return probe_wyrd(self._ctx).as_dict()
        try:
            payload = self._transport("GET", "/health")
        except WyrdProtocolError as exc:
            return {"healthy": False, "status": "unreachable",
                    "error": str(exc)}
        healthy = payload.get("status") == "ok"
        return {"healthy": healthy,
                "status": "healthy" if healthy else "server_unhealthy",
                "server_version": payload.get("version")}

    def capabilities(self) -> dict:
        """Capability negotiation (distinct from liveness)."""
        health = self.liveness()
        caps = negotiate_capabilities(
            health, server_version=health.get("server_version"))
        return require_compatible(caps) if health.get("healthy") else caps

    def snapshot(self, namespace: str | None = None) -> dict:
        payload = self._transport("GET", "/world")
        if not {"world_id", "formatted_for_llm"}.issubset(payload):
            raise WyrdProtocolError(
                "WYRD world response is missing required fields")
        if payload.get("schema_version") is not None:
            check_record_schema_version(payload["schema_version"])
        world_id = payload.get("world_id")
        if namespace is not None and namespace != world_id:
            raise WyrdError(
                "namespace_mismatch",
                f"caller asked for namespace {namespace!r} but "
                f"the server reports world {world_id!r}; worlds "
                "are never silently mixed (section 39 item 4)")
        refs = []
        for row in payload.get("present_entities") or []:
            entity_id = _entity_id_of(row)
            if entity_id:
                refs.append(make_ref(str(world_id), entity_id))
        return {"world": payload, "world_id": world_id,
                "references": refs}

    def facts(self, entity_id: str,
              namespace: str | None = None) -> dict:
        """Read-only canonical-facts query for one entity."""
        from urllib.parse import urlencode
        payload = self._transport(
            "GET", f"/facts?{urlencode({'entity_id': entity_id})}")
        facts = payload.get("facts")
        if not isinstance(facts, list):
            raise WyrdProtocolError("WYRD facts response is invalid")
        references = []
        if namespace is not None:
            for row in facts:
                references.append({
                    "ref": make_ref(namespace, entity_id),
                    "record_id": row.get("record_id")
                    if isinstance(row, dict) else None,
                    "source": "wyrd/facts"})
        return {"entity_id": entity_id, "namespace": namespace,
                "facts": facts, "references": references}

    def query(self, persona_id: str, query: str) -> dict:
        """Read-only Passive Oracle query (item 3).

        The Passive Oracle policy is enforced here exactly as in
        the pre-existing tools: the turn loop stays off, so no
        LLM generation and no memory writeback can occur."""
        payload = self._transport(
            "POST", "/query",
            {"persona_id": persona_id, "user_input": query,
             "use_turn_loop": False})
        response = payload.get("response")
        if not isinstance(response, str):
            raise WyrdProtocolError(
                "WYRD query response has no text response")
        return {"persona_id": persona_id, "context": response,
                "writeback": False,
                "provenance": {"source": "wyrd/passive_oracle",
                               "persona_id": persona_id,
                               "writeback": False}}

    # -- subscriptions / streaming -------------------------------

    def subscribe(self, topic: str, callback) -> None:
        """Subscribe to state-change events (topics: state, facts).

        The pinned server exposes no push/subscription endpoint
        (its verified surface is /health, /world, /facts,
        /query, /event), so subscriptions are served by bounded
        polling in ``poll_once`` -- recorded honestly here and
        in the X.04 record, never claimed as server push."""
        if topic not in ("state", "facts"):
            raise WyrdError("record_malformed",
                            f"unknown subscription topic {topic!r}")
        self._subscribers.setdefault(topic, []).append(callback)

    def poll_once(self) -> list:
        snap = self.snapshot()
        world = snap["world"]
        blob = json.dumps(
            {k: v for k, v in world.items()
             if k != "query_timestamp"},
            sort_keys=True, ensure_ascii=False, default=str)
        digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
        events: list = []
        if self._last_snapshot_hash is not None and \
                digest != self._last_snapshot_hash:
            before = self._last_snapshot or {}
            before_facts = before.get("canonical_facts") or {}
            after_facts = world.get("canonical_facts") or {}
            changed = sorted(
                k for k in set(before_facts) | set(after_facts)
                if before_facts.get(k) != after_facts.get(k))
            events.append({
                "schema": "runeforge.wyrd.change-event.v1",
                "type": "world_changed",
                "ref": f"wyrd://{snap['world_id']}",
                "before_hash": self._last_snapshot_hash,
                "after_hash": digest,
                "changed_fact_keys": changed,
            })
            topics = ["state"] + (["facts"] if changed else [])
            for topic in topics:
                for callback in self._subscribers.get(topic, []):
                    callback(events[-1])
        self._last_snapshot_hash = digest
        self._last_snapshot = world
        return events

    def stream(self, *, max_polls: int = 1):
        """Yield change events across bounded polls (streaming)."""
        for _ in range(max(1, int(max_polls))):
            yield from self.poll_once()

    # -- writes ---------------------------------------------------

    def _send_event(self, entry: dict) -> bool:
        if entry.get("truth_class") == "canonical_fact":
            payload: dict[str, Any] = {
                "subject_id": entry["entity_id"],
                "key": entry.get("key") or "",
                "value": entry.get("value") or ""}
            if entry.get("confidence") is not None:
                payload["confidence"] = entry["confidence"]
            if entry.get("domain"):
                payload["domain"] = entry["domain"]
            body = {"event_type": "fact", "payload": payload}
        else:
            body = {"event_type": "observation", "payload": {
                "title": entry.get("title") or "observation",
                "summary": entry.get("summary")
                or entry.get("value") or ""}}
        response = self._transport("POST", "/event", body)
        return response.get("ok") is True

    def _signal(self, change_kind: str, *, revision) -> bool:
        """Signal Verðandi ONLY after WYRD confirmed the write.

        The seam is the pre-existing WorldChangeTelemetry
        (content-free metadata via the profile Verðandi
        publisher); it is invoked from exactly one place --
        after a confirmed commit -- so an unconfirmed or
        duplicate write can never signal."""
        if self._telemetry is None:
            return False
        record_write = getattr(self._telemetry, "record_write", None)
        if record_write is not None:
            return bool(record_write(self._ctx, change_kind,
                                     revision=revision))
        return bool(self._telemetry.record(self._ctx, change_kind))

    def write_fact(self, *, namespace: str, entity_id: str,
                   key: str, value: str, confidence=None,
                   domain: str = "", provenance: dict | None = None,
                   expected_revision=None, idempotency_key: str = "",
                   recorded_at: str = "") -> dict:
        record = build_world_record(
            namespace=namespace, entity_id=entity_id,
            truth_class="canonical_fact", key=key, value=value,
            confidence=0.85 if confidence is None else confidence,
            provenance=provenance, idempotency_key=idempotency_key,
            recorded_at=recorded_at)
        entry = {**record, "domain": domain,
                 "expected_revision": expected_revision}
        return self._commit(entry, "fact")

    def write_observation(self, *, namespace: str, entity_id: str,
                          title: str, summary: str, confidence=0.5,
                          provenance: dict | None = None,
                          expected_revision=None,
                          idempotency_key: str = "",
                          recorded_at: str = "") -> dict:
        record = build_world_record(
            namespace=namespace, entity_id=entity_id,
            truth_class="tentative_observation", title=title,
            summary=summary, confidence=confidence,
            provenance=provenance, idempotency_key=idempotency_key,
            recorded_at=recorded_at)
        entry = {**record, "key": "", "expected_revision": expected_revision}
        return self._commit(entry, "observation")

    def _commit(self, entry: dict, change_kind: str) -> dict:
        if self._journal is not None:
            result = self._journal.commit(entry, sender=self._send_event)
            if result["status"] == "committed":
                published = self._signal(
                    change_kind, revision=result["revision"])
                result["event_published"] = published
            else:
                result["event_published"] = False
            return result
        if not self._send_event(entry):
            raise WyrdProtocolError(
                "WYRD did not confirm the write")
        published = self._signal(change_kind, revision=None)
        return {"status": "committed", "revision": None,
                "event_published": published, "sender_called": True}


def wyrd_status(ctx, *, recorded_at: str = "") -> dict:
    """Truthful WYRD status for the live caller.

    If no WYRD server is running, this says so: liveness is the
    real probe result and capability compatibility is null
    (unknown), never dressed up as negotiated."""
    health = probe_wyrd(ctx)
    health_dict = health.as_dict()
    caps = negotiate_capabilities(
        health_dict, server_version=health_dict.get("server_version"))
    return {
        "schema": "runeforge.wyrd.status.v1",
        "service": "volmarr-wyrd",
        "availability": "contract-implemented",
        "source_repo": SOURCE_REPO,
        "source_branch": SOURCE_BRANCH,
        "source_pin": SOURCE_PIN,
        "source_package_version": SOURCE_PACKAGE_VERSION,
        "source_license": SOURCE_LICENSE,
        "pin_moved_in_x04": False,
        "server": health_dict,
        "server_present": bool(health_dict.get("healthy")),
        "live_server_claimed": bool(health_dict.get("healthy")),
        "capabilities": caps,
        "consumers": consumer_seams(),
        "recorded_at": recorded_at,
    }
