"""In-memory presentation transaction routing without network or device I/O."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

from .aiavatarkit import to_aiavatarkit_response
from .presentation import CONTRACT_VERSION, validate_presentation_event


MAX_RETIRED_TRANSACTIONS = 32


class PresentationRoutingError(ValueError):
    """Raised when presentation ordering or ownership is invalid."""


@dataclass(frozen=True)
class RoutingDecision:
    """Responses admitted for one canonical input event."""

    responses: tuple[dict[str, Any], ...]
    interrupted_transaction_id: str | None = None


@dataclass
class _SessionState:
    active_transaction_id: str
    last_sequence: int
    retired: deque[str]


class PresentationTransactionRouter:
    """Enforce one ordered presentation transaction per session."""

    def __init__(self) -> None:
        self._sessions: dict[str, _SessionState] = {}
        self._retired: dict[str, deque[str]] = {}

    def route(self, event: dict[str, Any]) -> RoutingDecision:
        canonical = validate_presentation_event(event)
        session_id = canonical["session_id"]
        transaction_id = canonical["transaction_id"]
        sequence = canonical["sequence"]
        kind = canonical["kind"]
        state = self._sessions.get(session_id)

        if state is None:
            retired = self._retired.setdefault(
                session_id, deque(maxlen=MAX_RETIRED_TRANSACTIONS)
            )
            if transaction_id in retired:
                raise PresentationRoutingError("retired presentation transaction is stale")
            if kind != "speech" or sequence != 0:
                raise PresentationRoutingError(
                    "a presentation transaction must begin with speech sequence 0"
                )
            state = _SessionState(transaction_id, sequence, retired)
            self._sessions[session_id] = state
            return RoutingDecision((to_aiavatarkit_response(canonical),))

        if transaction_id == state.active_transaction_id:
            if sequence != state.last_sequence + 1:
                raise PresentationRoutingError(
                    "presentation sequence must increase by exactly one"
                )
            state.last_sequence = sequence
            response = to_aiavatarkit_response(canonical)
            if kind == "final":
                self._retire(session_id, state)
            return RoutingDecision((response,))

        if transaction_id in state.retired:
            raise PresentationRoutingError("retired presentation transaction is stale")
        if kind != "speech" or sequence != 0:
            raise PresentationRoutingError(
                "replacement presentation transaction must begin with speech sequence 0"
            )

        previous = state.active_transaction_id
        self._append_retired(state.retired, previous)
        replacement = _SessionState(transaction_id, sequence, state.retired)
        self._sessions[session_id] = replacement
        interruption = {
            "type": "stop",
            "session_id": session_id,
            "metadata": {
                "runeforge_contract": CONTRACT_VERSION,
                "transaction_id": previous,
                "interrupted": True,
            },
        }
        return RoutingDecision(
            (interruption, to_aiavatarkit_response(canonical)),
            interrupted_transaction_id=previous,
        )

    def disconnect(self, session_id: str) -> bool:
        """Forget live session ownership while retaining bounded stale IDs."""

        state = self._sessions.pop(session_id, None)
        if state is None:
            return False
        self._append_retired(state.retired, state.active_transaction_id)
        return True

    def active_transaction(self, session_id: str) -> str | None:
        state = self._sessions.get(session_id)
        return state.active_transaction_id if state is not None else None

    def _retire(self, session_id: str, state: _SessionState) -> None:
        self._append_retired(state.retired, state.active_transaction_id)
        self._sessions.pop(session_id, None)

    @staticmethod
    def _append_retired(retired: deque[str], transaction_id: str) -> None:
        if transaction_id not in retired:
            retired.append(transaction_id)
