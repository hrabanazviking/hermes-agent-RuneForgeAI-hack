"""Explicit blind-spot tracking (Self-Aware Agency roadmap §17).

§17 adds explicit blind-spot tracking over thirteen named
categories, with records carrying category / evidence_count /
confidence / mitigation / last_observed_at. Two §17 rules shape
this layer:

- blind spots affect *metacognitive confidence*, not identity:
  a record is a confidence adjustment with evidence behind it,
  never a permanent label on the entity. Nothing here writes to
  the self-model, the identity store, or any other store — the
  module imports none of them and writes only its own bounded
  log, only on explicit calls;
- blind spots decay or retire after contrary evidence: each
  category's current state is the latest snapshot in the log.
  An observation increments the evidence count and (re)activates
  the spot; a contrary-evidence record lowers confidence by a
  fixed step (0.25) and increments the contrary count. Status is
  a deterministic function of the snapshot — ``retired`` at
  three contrary records, ``decayed`` at one or two, ``active``
  otherwise — and strict read validation refuses a stored status
  that disagrees with the function, so a spot can never quietly
  become permanent or silently vanish.

The metacognitive effect is the pure :func:`adjusted_confidence`
function: a base confidence is discounted by half the strongest
active spot's confidence (a quarter for a decayed spot; retired
spots discount nothing). It is supplied for the metacognition
surfaces to apply; this module applies it to nothing itself.

Disabled by default. No hook, loop, scheduler, or turn-path
caller observes or records; both are explicit calls only.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home, mkdir_under_hermes_home

from .context_packet import ContextItem
from .identity import IdentityError, IdentityStore, _as_bool

BLIND_SPOT_VERSION = 1
DEFAULT_LOG_PATH = Path("entity") / "blind_spots.jsonl"
DEFAULT_LOG_LIMIT = 200
MAX_LOG_BYTES = 4 * 1024 * 1024
MAX_MITIGATIONS = 5
MAX_TEXT_CHARS = 500
CONTRARY_CONFIDENCE_STEP = 0.25
RETIRE_CONTRARY_COUNT = 3
ACTIVE_DISCOUNT = 0.5
DECAYED_DISCOUNT = 0.25

# The thirteen §17 categories, in roadmap order.
CATEGORIES = (
    "confirmation_bias",
    "self_serving_bias",
    "relationship_bias",
    "overconfidence",
    "underconfidence",
    "capability_confusion",
    "source_confusion",
    "temporal_blindness",
    "goal_tunnel_vision",
    "affective_distortion",
    "novelty_bias",
    "authority_confusion",
    "unknown_unknown",
)

STATUSES = frozenset({"active", "decayed", "retired"})

_FIELDS = {
    "blind_spot_version", "record_id", "owner_entity_id",
    "recorded_at", "category", "evidence_count", "contrary_count",
    "confidence", "mitigation", "last_observed_at", "status",
}

_SLUG = re.compile(r"^[a-z][a-z0-9_]*$")

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


class BlindSpotError(RuntimeError):
    """A blind-spot record cannot be safely built or read."""


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _timestamp_ok(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _epoch(value: str) -> float:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, OverflowError, OSError):
        return 0.0


def _unit(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and 0.0 <= float(value) <= 1.0
    )


def _canonical_uuid(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


def categories() -> list[str]:
    return list(CATEGORIES)


def status_for(confidence: Any, contrary_count: Any) -> str:
    """The §17 status of a snapshot — a pure function of it."""
    if isinstance(contrary_count, int) and contrary_count >= RETIRE_CONTRARY_COUNT:
        return "retired"
    if isinstance(contrary_count, int) and contrary_count >= 1:
        return "decayed"
    return "active"


def adjusted_confidence(base: float, spots: list[dict[str, Any]]) -> float:
    """Discount a base confidence by the strongest live blind spot.

    Pure. Retired spots discount nothing; decayed spots discount
    at half the active rate. The result stays in the unit interval.
    """
    if not _unit(base):
        raise BlindSpotError("base confidence is invalid")
    discount = 0.0
    for spot in spots:
        if spot.get("status") == "active":
            discount = max(discount, ACTIVE_DISCOUNT * float(spot["confidence"]))
        elif spot.get("status") == "decayed":
            discount = max(discount, DECAYED_DISCOUNT * float(spot["confidence"]))
    return round(float(base) * (1.0 - discount), 4)


class BlindSpotService:
    """The §17 blind-spot snapshot log."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("blind_spots_enabled", False), False
        )

    def _limit(self) -> int:
        try:
            value = int(self._ctx.get_config(
                "blind_spots_log_limit", DEFAULT_LOG_LIMIT))
        except (TypeError, ValueError):
            value = DEFAULT_LOG_LIMIT
        return min(500, max(10, value))

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(
            "blind_spots_log_path", str(DEFAULT_LOG_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_LOG_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_LOG_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise BlindSpotError(
                "blind spot log path resolves outside the profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    # -- snapshots -----------------------------------------------------

    def _latest_for(self, category: str) -> dict[str, Any] | None:
        rows = [row for row in self.records(limit=500)
                if row["category"] == category]
        return rows[-1] if rows else None

    def current(self) -> list[dict[str, Any]]:
        """Latest snapshot per category, in §17 category order. Read-only."""
        latest: dict[str, dict[str, Any]] = {}
        for row in self.records(limit=500):
            latest[row["category"]] = row
        return [latest[category] for category in CATEGORIES
                if category in latest]

    def observe(self, category: str, *, confidence: float,
                mitigation: Any = (),
                observed_at: str | None = None) -> dict[str, Any]:
        """Record one observation of a blind spot (explicit only).

        Increments the evidence count of the category's live spot
        and reactivates it (contrary count reset); a retired spot
        starts a fresh cycle at evidence 1. ``mitigation`` replaces
        the stored list when supplied, otherwise the previous
        list carries over.
        """
        if not self.enabled():
            raise BlindSpotError("blind spots are disabled")
        if category not in CATEGORIES:
            raise BlindSpotError("blind spot category is invalid")
        if not _unit(confidence):
            raise BlindSpotError("blind spot confidence is invalid")
        owner = self._identity.read().entity_id
        previous = self._latest_for(category)
        fresh = previous is None or previous["status"] == "retired"
        mitigations = self._mitigations(mitigation)
        if not mitigations and previous is not None:
            mitigations = list(previous["mitigation"])
        stamp = observed_at or _fmt(_now_dt())
        record = {
            "blind_spot_version": BLIND_SPOT_VERSION,
            "record_id": str(uuid.uuid4()),
            "owner_entity_id": owner,
            "recorded_at": stamp,
            "category": category,
            "evidence_count": 1 if fresh else previous["evidence_count"] + 1,
            "contrary_count": 0,
            "confidence": float(confidence),
            "mitigation": mitigations,
            "last_observed_at": stamp,
            "status": "active",
        }
        self._validate(record, owner)
        self._append(record)
        return record

    def record_contrary_evidence(self, category: str, *,
                                 observed_at: str | None = None
                                 ) -> dict[str, Any]:
        """Record evidence against a live blind spot (explicit only).

        Confidence drops by the fixed contrary step and the
        contrary count increments; at three contrary records the
        spot retires (§17 decay/retirement). ``last_observed_at``
        stays at the last *observation* — contrary evidence is not
        an observation of the spot itself.
        """
        if not self.enabled():
            raise BlindSpotError("blind spots are disabled")
        if category not in CATEGORIES:
            raise BlindSpotError("blind spot category is invalid")
        owner = self._identity.read().entity_id
        previous = self._latest_for(category)
        if previous is None or previous["status"] == "retired":
            raise BlindSpotError(
                "no live blind spot exists for that category")
        stamp = observed_at or _fmt(_now_dt())
        if not _timestamp_ok(stamp):
            raise BlindSpotError("contrary recorded_at is invalid")
        contrary = previous["contrary_count"] + 1
        confidence = round(
            max(0.0, float(previous["confidence"]) - CONTRARY_CONFIDENCE_STEP), 4)
        record = {
            "blind_spot_version": BLIND_SPOT_VERSION,
            "record_id": str(uuid.uuid4()),
            "owner_entity_id": owner,
            "recorded_at": stamp,
            "category": category,
            "evidence_count": previous["evidence_count"],
            "contrary_count": contrary,
            "confidence": confidence,
            "mitigation": list(previous["mitigation"]),
            "last_observed_at": previous["last_observed_at"],
            "status": status_for(confidence, contrary),
        }
        self._validate(record, owner)
        self._append(record)
        return record

    def discount_for(self, base: float) -> dict[str, Any]:
        """Apply :func:`adjusted_confidence` over the current spots.

        Read-only: returns the base, the adjusted value, and the
        category responsible for the largest discount (or None).
        """
        spots = self.current()
        adjusted = adjusted_confidence(base, spots)
        driver = None
        best = 0.0
        for spot in spots:
            rate = ACTIVE_DISCOUNT if spot["status"] == "active" else \
                DECAYED_DISCOUNT if spot["status"] == "decayed" else 0.0
            effect = rate * float(spot["confidence"])
            if effect > best:
                best = effect
                driver = spot["category"]
        return {
            "base": float(base), "adjusted": adjusted,
            "discount": round(float(base) - adjusted, 4),
            "driver": driver,
        }

    # -- bounded log -----------------------------------------------------

    def records(self, *, limit: int = 500) -> list[dict[str, Any]]:
        owner = self._identity.read().entity_id
        path = self.path()
        if path.is_symlink():
            raise BlindSpotError("blind spot log must not be a symbolic link")
        if not path.is_file():
            return []
        if path.stat().st_size > MAX_LOG_BYTES:
            raise BlindSpotError("blind spot log exceeds its size limit")
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except ValueError as exc:
                raise BlindSpotError("blind spot log is malformed") from exc
            self._validate(payload, owner)
            out.append(payload)
        return out[-max(1, min(500, limit)):]

    @staticmethod
    def _mitigations(value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, (list, tuple)) or len(value) > MAX_MITIGATIONS:
            raise BlindSpotError("blind spot mitigation is invalid or oversized")
        out: list[str] = []
        for item in value:
            if not isinstance(item, str) or not item.strip() \
                    or len(item.strip()) > MAX_TEXT_CHARS:
                raise BlindSpotError("blind spot mitigation entry is invalid")
            out.append(item.strip())
        return out

    @staticmethod
    def _validate(payload: Any, owner: str) -> None:
        if not isinstance(payload, dict) or set(payload) != _FIELDS:
            raise BlindSpotError("blind spot fields are invalid")
        if payload.get("blind_spot_version") != BLIND_SPOT_VERSION:
            raise BlindSpotError("blind spot version is unsupported")
        if not _canonical_uuid(payload.get("record_id")):
            raise BlindSpotError("blind spot id is invalid")
        if payload.get("owner_entity_id") != owner:
            raise BlindSpotError(
                "blind spot owner does not match entity identity")
        if not _timestamp_ok(payload.get("recorded_at")) \
                or not _timestamp_ok(payload.get("last_observed_at")):
            raise BlindSpotError("blind spot timestamps are invalid")
        if payload.get("category") not in CATEGORIES:
            raise BlindSpotError("blind spot category is invalid")
        for field in ("evidence_count", "contrary_count"):
            value = payload.get(field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise BlindSpotError(f"blind spot {field} is invalid")
        if payload["evidence_count"] < 1:
            raise BlindSpotError("blind spot evidence_count is invalid")
        if not _unit(payload.get("confidence")):
            raise BlindSpotError("blind spot confidence is invalid")
        BlindSpotService._mitigations(payload.get("mitigation"))
        status = payload.get("status")
        if status not in STATUSES:
            raise BlindSpotError("blind spot status is invalid")
        if status != status_for(payload["confidence"],
                                payload["contrary_count"]):
            raise BlindSpotError(
                "blind spot status disagrees with the §17 status function")

    def _append(self, record: dict[str, Any]) -> None:
        path = self.path()
        if path.is_symlink():
            raise BlindSpotError("blind spot log must not be a symbolic link")
        lock_path = path.with_suffix(path.suffix + ".lock")
        mkdir_under_hermes_home(lock_path.parent)
        with lock_path.open("a+b") as lock:
            lock.seek(0, os.SEEK_END)
            if lock.tell() == 0:
                lock.write(b"\0")
                lock.flush()
            lock.seek(0)
            if fcntl is not None:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            elif msvcrt is not None:
                msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            try:
                if path.exists() and path.stat().st_size > MAX_LOG_BYTES:
                    raise BlindSpotError("blind spot log exceeds its size limit")
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(
                        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                lines = path.read_text(encoding="utf-8").splitlines()
                limit = self._limit()
                if len(lines) > limit:
                    tmp = path.with_suffix(path.suffix + ".tmp")
                    tmp.write_text("\n".join(lines[-limit:]) + "\n", encoding="utf-8")
                    os.replace(tmp, path)
            finally:
                lock.seek(0)
                if fcntl is not None:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                elif msvcrt is not None:
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


class BlindSpotBridge:
    """Surface the strongest live blind spot, content-bearing only.

    No session hook — observations and contrary evidence are
    recorded only by explicit calls. The item names the category,
    its confidence, and its first mitigation; it is a confidence
    note, never an identity label.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._service = BlindSpotService(ctx)

    def hooks(self):
        return ()

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not _as_bool(
            self._ctx.get_config("blind_spots_enabled", False), False
        ):
            return []
        try:
            spots = [spot for spot in self._service.current()
                     if spot["status"] != "retired"]
        except (IdentityError, BlindSpotError, OSError):
            return []
        if not spots:
            return []
        strongest = max(spots, key=lambda spot: float(spot["confidence"]))
        content = (
            f"Blind spot (§17, {strongest['status']}): "
            f"{strongest['category']} — confidence "
            f"{strongest['confidence']:.2f} from "
            f"{strongest['evidence_count']} observation(s); it "
            f"discounts metacognitive confidence, it is not an "
            f"identity label."
        )
        if strongest["mitigation"]:
            content += f" Mitigation: {strongest['mitigation'][0]}"
        return [ContextItem(
            section="current_state",
            content=content,
            source="blind_spots",
            record_id=strongest["record_id"],
            priority=0.4,
            updated_at=_epoch(strongest["recorded_at"]),
        )]


__all__ = [
    "BLIND_SPOT_VERSION",
    "DEFAULT_LOG_PATH",
    "CATEGORIES",
    "STATUSES",
    "CONTRARY_CONFIDENCE_STEP",
    "BlindSpotError",
    "BlindSpotService",
    "BlindSpotBridge",
    "categories",
    "status_for",
    "adjusted_confidence",
]
