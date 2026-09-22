"""Hermes registration boundary for deterministic RPG mechanics."""

from __future__ import annotations

from .tools import register_tools


def register(ctx) -> None:
    """Register bounded mechanics without campaign state or prompts."""
    register_tools(ctx)
