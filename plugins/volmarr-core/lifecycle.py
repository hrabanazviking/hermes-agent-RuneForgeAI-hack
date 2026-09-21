"""Map safe Hermes lifecycle metadata onto versioned Verðandi events."""

from __future__ import annotations

from typing import Any, Callable, Iterable

from .verdandi import VerdandiPublisher


Hook = tuple[str, Callable[..., None]]


def _text(value: Any, limit: int = 256) -> str:
    return str(value or "")[:limit]


class LifecycleBridge:
    """Observer-only hook adapter; raw content never enters the event envelope."""

    def __init__(self, plugin_context, publisher: VerdandiPublisher | None = None) -> None:
        self._ctx = plugin_context
        self._publisher = publisher or VerdandiPublisher()

    def hooks(self) -> Iterable[Hook]:
        return (
            ("on_session_start", self.on_session_start),
            ("on_session_end", self.on_turn_end),
            ("on_session_finalize", self.on_session_finalize),
            ("pre_tool_call", self.on_tool_start),
            ("post_tool_call", self.on_tool_end),
        )

    def _publish(self, event_type: str, **context: Any) -> None:
        self._publisher.publish(self._ctx, event_type, context)

    def on_session_start(
        self,
        *,
        session_id: str = "",
        model: str = "",
        platform: str = "",
        **_: Any,
    ) -> None:
        self._publish(
            "hermes.session.started",
            session_id=_text(session_id),
            model=_text(model),
            platform=_text(platform, 64),
        )

    def on_turn_end(
        self,
        *,
        session_id: str = "",
        task_id: str = "",
        turn_id: str = "",
        completed: bool = False,
        failed: bool = False,
        interrupted: bool = False,
        turn_exit_reason: str = "",
        model: str = "",
        platform: str = "",
        **_: Any,
    ) -> None:
        if interrupted:
            event_type = "hermes.turn.interrupted"
        elif failed:
            event_type = "hermes.turn.failed"
        else:
            event_type = "hermes.turn.completed"
        self._publish(
            event_type,
            session_id=_text(session_id),
            task_id=_text(task_id),
            turn_id=_text(turn_id),
            completed=bool(completed),
            exit_reason=_text(turn_exit_reason, 128),
            model=_text(model),
            platform=_text(platform, 64),
        )

    def on_session_finalize(self, *, session_id: str = "", **_: Any) -> None:
        self._publish("hermes.session.ended", session_id=_text(session_id))

    def on_tool_start(
        self,
        *,
        tool_name: str = "",
        session_id: str = "",
        task_id: str = "",
        turn_id: str = "",
        tool_call_id: str = "",
        api_request_id: str = "",
        **_: Any,
    ) -> None:
        self._publish(
            "hermes.tool.started",
            tool_name=_text(tool_name, 128),
            session_id=_text(session_id),
            task_id=_text(task_id),
            turn_id=_text(turn_id),
            tool_call_id=_text(tool_call_id),
            api_request_id=_text(api_request_id),
        )

    def on_tool_end(
        self,
        *,
        tool_name: str = "",
        session_id: str = "",
        task_id: str = "",
        turn_id: str = "",
        tool_call_id: str = "",
        api_request_id: str = "",
        duration_ms: int = 0,
        status: str = "ok",
        error_type: str | None = None,
        **_: Any,
    ) -> None:
        normalized_status = _text(status or "ok", 64)
        event_type = (
            "hermes.tool.completed"
            if normalized_status == "ok"
            else "hermes.tool.failed"
        )
        self._publish(
            event_type,
            tool_name=_text(tool_name, 128),
            session_id=_text(session_id),
            task_id=_text(task_id),
            turn_id=_text(turn_id),
            tool_call_id=_text(tool_call_id),
            api_request_id=_text(api_request_id),
            duration_ms=max(0, int(duration_ms or 0)),
            status=normalized_status,
            error_type=_text(error_type, 128),
        )
