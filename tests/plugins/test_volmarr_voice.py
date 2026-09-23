"""Contracts for Volmarr's read-only Hermes voice readiness boundary."""

from __future__ import annotations

import json
from pathlib import Path

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)


def _profile(home: Path, *, mode: str, stt_provider: str, tts_provider: str) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-voice]\n"
        "voice:\n"
        f"  voice_chat_mode: {mode}\n"
        f"  auto_tts: {'true' if mode == 'gpt-live' else 'false'}\n"
        f"  barge_in: {'false' if mode == 'gpt-live' else 'true'}\n"
        "stt:\n"
        "  enabled: true\n"
        f"  provider: {stt_provider}\n"
        "tts:\n"
        f"  provider: {tts_provider}\n",
        encoding="utf-8",
    )


def test_real_discovery_reports_active_profile_a_b_a_without_voice_operations(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home_a = get_hermes_home()
    home_b = tmp_path / "home-b"
    _profile(home_a, mode="chained", stt_provider="local", tts_provider="edge")
    _profile(home_b, mode="gpt-live", stt_provider="external-voice", tts_provider="piper")

    manager = PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-voice"]
        assert loaded.enabled and loaded.tools_registered == ["voice_pipeline_readiness"]
        results = []
        for home in (home_a, home_b, home_a):
            token = set_hermes_home_override(home)
            try:
                results.append(
                    json.loads(
                        registry.dispatch(
                            "voice_pipeline_readiness", {}, scope=manager.scope_key
                        )
                    )
                )
            finally:
                reset_hermes_home_override(token)
        rejected = json.loads(
            registry.dispatch(
                "voice_pipeline_readiness", {"record": True}, scope=manager.scope_key
            )
        )
    finally:
        manager.unload()

    assert [item["voice_chat_mode"] for item in results] == [
        "chained",
        "gpt-live",
        "chained",
    ]
    assert [item["input"]["requested_provider"] for item in results] == [
        "local",
        "external-voice",
        "local",
    ]
    assert [item["output"]["requested_provider"] for item in results] == [
        "edge",
        "piper",
        "edge",
    ]
    assert results[0]["controls"] == {
        "auto_tts": False,
        "barge_in": True,
        "client_direct": True,
    }
    assert results[1]["controls"]["auto_tts"] is True
    assert results[1]["controls"]["barge_in"] is False
    assert results[1]["input"]["provider_kind"] == "plugin-or-unknown"
    assert results[1]["input"]["stt_available"] is None
    assert results[1]["input"]["provider_dependency_checked"] is False
    for item in results:
        assert item["credentials_withheld"] is True
        assert item["assessment"]["end_to_end_verified"] is False
        assert item["microphone_opened"] is False
        assert item["audio_recorded"] is False
        assert item["transcription_performed"] is False
        assert item["speech_synthesized"] is False
        assert item["provider_contacted"] is False
    assert "error" in rejected
