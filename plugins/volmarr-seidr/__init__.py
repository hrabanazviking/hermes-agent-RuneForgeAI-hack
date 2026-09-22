"""Hermes registration boundary for deterministic Seiðr poetry."""

from __future__ import annotations

from .tools import register_tools


def register(ctx) -> None:
    """Register deterministic composition without prompts, state, or providers."""
    register_tools(ctx)
