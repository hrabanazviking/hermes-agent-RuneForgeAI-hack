"""Explicit, unregistered loopback feed for presentation-only consumers."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from typing import Any

from websockets.asyncio.server import Server, ServerConnection, serve
from websockets.exceptions import ConnectionClosed

from .admission import (
    AvatarAdmissionError,
    authorize_bearer,
    load_avatar_token,
    parse_ready_message,
    validate_listener_target,
)
from .presentation import CONTRACT_VERSION, validate_presentation_event
from .transport import PresentationRoutingError, PresentationTransactionRouter


class AvatarLoopbackError(RuntimeError):
    """Raised for unavailable consumers or invalid feed lifecycle."""


class AvatarLoopbackFeed:
    """One explicit loopback listener; never registered or auto-started by the plugin."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        path: str,
        environ: Mapping[str, str],
        ready_timeout_seconds: float = 2.0,
    ) -> None:
        self.host, self.port, self.path = validate_listener_target(
            host=host,
            port=port,
            path=path,
            origin=None,
        )
        if not 0.1 <= ready_timeout_seconds <= 10.0:
            raise AvatarLoopbackError("avatar readiness timeout must be 0.1 through 10 seconds")
        self._token = load_avatar_token(environ)
        self._ready_timeout = float(ready_timeout_seconds)
        self._router = PresentationTransactionRouter()
        self._server: Server | None = None
        self._connections: dict[str, ServerConnection] = {}
        self._send_locks: dict[str, asyncio.Lock] = {}
        self._ownership_lock = asyncio.Lock()

    async def start(self) -> None:
        if self._server is not None:
            raise AvatarLoopbackError("avatar loopback feed is already started")
        self._server = await serve(
            self._handle_connection,
            self.host,
            self.port,
            origins=[None],
            compression=None,
            open_timeout=self._ready_timeout,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=2,
            max_size=512,
            max_queue=1,
            write_limit=32768,
        )

    async def stop(self) -> None:
        server = self._server
        self._server = None
        async with self._ownership_lock:
            owned = tuple(self._connections.items())
            self._connections.clear()
            self._send_locks.clear()
        for session_id, connection in owned:
            self._router.disconnect(session_id)
            await connection.close(code=1001, reason="presentation feed stopped")
        if server is not None:
            server.close()
            await server.wait_closed()

    async def publish(self, event: dict[str, Any]) -> int:
        if self._server is None:
            raise AvatarLoopbackError("avatar loopback feed is not started")
        canonical = validate_presentation_event(event)
        session_id = canonical["session_id"]
        async with self._ownership_lock:
            connection = self._connections.get(session_id)
            send_lock = self._send_locks.get(session_id)
        if connection is None or send_lock is None:
            raise AvatarLoopbackError("no presentation consumer owns this session")
        try:
            decision = self._router.route(canonical)
        except PresentationRoutingError as exc:
            raise AvatarLoopbackError("presentation event ordering was refused") from exc

        async with send_lock:
            sent = 0
            for response in decision.responses:
                async with self._ownership_lock:
                    if self._connections.get(session_id) is not connection:
                        raise AvatarLoopbackError("presentation consumer ownership changed")
                try:
                    await connection.send(
                        json.dumps(response, separators=(",", ":"), ensure_ascii=True)
                    )
                except ConnectionClosed as exc:
                    await self._release(session_id, connection)
                    raise AvatarLoopbackError("presentation consumer disconnected") from exc
                sent += 1
            return sent

    async def _handle_connection(self, connection: ServerConnection) -> None:
        session_id: str | None = None
        try:
            request = connection.request
            origin = request.headers.get("Origin")
            validate_listener_target(
                host=self.host,
                port=self.port,
                path=request.path,
                origin=origin,
            )
            authorize_bearer(request.headers.get("Authorization"), self._token)
            raw = await asyncio.wait_for(
                connection.recv(), timeout=self._ready_timeout
            )
            ready = parse_ready_message(raw)
            session_id = ready.session_id
            async with self._ownership_lock:
                if session_id in self._connections:
                    raise AvatarAdmissionError("avatar session already has a consumer")
                self._connections[session_id] = connection
                self._send_locks[session_id] = asyncio.Lock()
            await connection.send(
                json.dumps(
                    {
                        "type": "connected",
                        "session_id": session_id,
                        "metadata": {"runeforge_contract": CONTRACT_VERSION},
                    },
                    separators=(",", ":"),
                )
            )
            await connection.recv()
            await connection.close(code=1003, reason="consumer input is forbidden")
        except (AvatarAdmissionError, asyncio.TimeoutError):
            await connection.close(code=1008, reason="presentation admission refused")
        except ConnectionClosed:
            pass
        finally:
            if session_id is not None:
                await self._release(session_id, connection)

    async def _release(
        self, session_id: str, connection: ServerConnection
    ) -> None:
        async with self._ownership_lock:
            if self._connections.get(session_id) is not connection:
                return
            self._connections.pop(session_id, None)
            self._send_locks.pop(session_id, None)
        self._router.disconnect(session_id)
