"""Presentation transaction lifecycle contracts."""

from __future__ import annotations

import importlib
import io
import wave

import pytest

from hermes_constants import get_hermes_home


def _enable_plugin(home) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [volmarr-voice]\n",
        encoding="utf-8",
    )


def _wav_bytes() -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b"\x00\x00" * 80)
    return output.getvalue()


def _event(presentation, *, transaction, sequence, kind="speech", session="avatar-a"):
    return presentation.build_presentation_event(
        kind=kind,
        session_id=session,
        transaction_id=transaction,
        sequence=sequence,
        audio_data=_wav_bytes() if kind == "speech" else None,
    )


def test_real_discovery_routes_replacement_before_new_audio_and_rejects_stale():
    from hermes_cli.plugins import PluginManager

    _enable_plugin(get_hermes_home())
    manager = PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-voice"]
        presentation = importlib.import_module(f"{loaded.module.__name__}.presentation")
        transport = importlib.import_module(f"{loaded.module.__name__}.transport")
        router = transport.PresentationTransactionRouter()

        first = router.route(_event(presentation, transaction="turn-a", sequence=0))
        replacement = router.route(
            _event(presentation, transaction="turn-b", sequence=0)
        )
        with pytest.raises(transport.PresentationRoutingError):
            router.route(_event(presentation, transaction="turn-a", sequence=1))
        final = router.route(
            _event(presentation, transaction="turn-b", sequence=1, kind="final")
        )
    finally:
        manager.unload()

    assert [item["type"] for item in first.responses] == ["chunk"]
    assert [item["type"] for item in replacement.responses] == ["stop", "chunk"]
    assert replacement.interrupted_transaction_id == "turn-a"
    assert replacement.responses[0]["metadata"]["interrupted"] is True
    assert [item["type"] for item in final.responses] == ["final"]
    assert router.active_transaction("avatar-a") is None


def test_router_enforces_order_session_isolation_and_disconnect_cleanup():
    from hermes_cli.plugins import PluginManager

    _enable_plugin(get_hermes_home())
    manager = PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-voice"]
        presentation = importlib.import_module(f"{loaded.module.__name__}.presentation")
        transport = importlib.import_module(f"{loaded.module.__name__}.transport")
        router = transport.PresentationTransactionRouter()

        router.route(_event(presentation, transaction="turn-a", sequence=0))
        router.route(
            _event(
                presentation,
                transaction="turn-z",
                sequence=0,
                session="avatar-b",
            )
        )
        with pytest.raises(transport.PresentationRoutingError):
            router.route(_event(presentation, transaction="turn-a", sequence=2))
        assert router.disconnect("avatar-a") is True
        assert router.disconnect("avatar-a") is False
        with pytest.raises(transport.PresentationRoutingError):
            router.route(_event(presentation, transaction="turn-a", sequence=0))
    finally:
        manager.unload()

    assert router.active_transaction("avatar-a") is None
    assert router.active_transaction("avatar-b") == "turn-z"
