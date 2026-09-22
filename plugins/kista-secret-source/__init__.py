"""Hermes registration boundary for the Kista secret source."""

from __future__ import annotations

from .source import KistaSource


def register(ctx) -> None:
    """Register Kista without adding tools, hooks, or prompt-visible surfaces."""
    ctx.register_secret_source(KistaSource())
