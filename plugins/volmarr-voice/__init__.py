"""Hermes registration boundary for Volmarr voice diagnostics."""

from __future__ import annotations

from .tools import register_tools


def register(ctx) -> None:
    """Register the non-operating voice readiness probe."""
    register_tools(ctx)
