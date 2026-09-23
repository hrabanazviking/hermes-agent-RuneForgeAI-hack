"""Bounded stdin orchestration for an explicitly constructed avatar feed."""

from __future__ import annotations

import asyncio
import json
from typing import Any, BinaryIO

from .loopback import AvatarLoopbackError, AvatarLoopbackFeed
from .presentation import MAX_WAV_BYTES, PresentationContractError, validate_presentation_event


MAX_EVENT_LINE_BYTES = ((MAX_WAV_BYTES + 2) // 3) * 4 + 65536


class AvatarRunnerError(RuntimeError):
    """Raised without echoing rejected event or audio content."""


async def run_feed_from_stream(feed: AvatarLoopbackFeed, stream: BinaryIO) -> int:
    """Run one explicit feed until binary-stream EOF; always close the feed."""

    published = 0
    await feed.start()
    try:
        while True:
            raw = await asyncio.to_thread(stream.readline, MAX_EVENT_LINE_BYTES + 1)
            if raw == b"":
                return published
            if not isinstance(raw, bytes):
                raise AvatarRunnerError("avatar event input must be a binary stream")
            if len(raw) > MAX_EVENT_LINE_BYTES:
                raise AvatarRunnerError("avatar event line exceeds the maximum size")
            if not raw.endswith(b"\n"):
                raise AvatarRunnerError("avatar event line must end with a newline")
            try:
                text = raw[:-1].decode("utf-8")
                event: Any = json.loads(text)
                canonical = validate_presentation_event(event)
            except (
                UnicodeDecodeError,
                json.JSONDecodeError,
                RecursionError,
                PresentationContractError,
            ) as exc:
                raise AvatarRunnerError("avatar event line was refused") from exc
            try:
                await feed.publish(canonical)
            except AvatarLoopbackError as exc:
                raise AvatarRunnerError("avatar event delivery failed") from exc
            published += 1
    finally:
        await feed.stop()
