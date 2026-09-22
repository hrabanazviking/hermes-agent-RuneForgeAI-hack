"""Hermes registration boundary for Volmarr's local tarot tools."""

from __future__ import annotations

from .tools import register_tools


def register(ctx) -> None:
    """Register deterministic draws without prompts, state, or providers."""
    register_tools(ctx)
