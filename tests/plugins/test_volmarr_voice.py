"""Contracts for Volmarr's read-only Hermes voice readiness boundary."""

from __future__ import annotations

import json
import wave
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


def _dispatch_fixture(home: Path) -> None:
    plugin = home / "plugins" / "voice-loop-fixture"
    plugin.mkdir(parents=True)
    (plugin / "plugin.yaml").write_text(
        "manifest_version: 2\n"
        "name: voice-loop-fixture\n"
        'version: "1.0.0"\n'
        "description: Provider-free voice-loop test fixture.\n"
        "author: RuneForgeAI tests\n",
        encoding="utf-8",
    )
    (plugin / "__init__.py").write_text(
        '''from pathlib import Path
import wave

from agent.transcription_provider import TranscriptionProvider
from agent.tts_provider import TTSProvider


class RuneSTT(TranscriptionProvider):
    @property
    def name(self):
        return "rune-stt"

    def transcribe(self, file_path, **extra):
        return {"success": True, "transcript": "wyrd wakes", "provider": self.name}


class RuneTTS(TTSProvider):
    @property
    def name(self):
        return "rune-tts"

    def synthesize(self, text, output_path, **extra):
        target = Path(output_path).with_suffix(".wav")
        with wave.open(str(target), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8000)
            audio.writeframes(b"\\x00\\x00" * 80)
        return str(target)


def register(ctx):
    ctx.register_transcription_provider(RuneSTT())
    ctx.register_tts_provider(RuneTTS())
''',
        encoding="utf-8",
    )
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-voice, voice-loop-fixture]\n"
        "stt:\n"
        "  enabled: true\n"
        "  provider: rune-stt\n"
        "tts:\n"
        "  provider: rune-tts\n",
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


def test_real_discovery_completes_provider_free_stt_to_tts_dispatch(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.transcription_tools import transcribe_audio
    from tools.tts_tool import text_to_speech_tool

    home = get_hermes_home()
    _dispatch_fixture(home)
    source = tmp_path / "source.wav"
    with wave.open(str(source), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b"\x00\x00" * 80)
    source_before = source.read_bytes()

    manager = PluginManager()
    manager.discover_and_load()
    try:
        assert manager._plugins["volmarr-voice"].enabled
        assert manager._plugins["voice-loop-fixture"].enabled
        transcript = transcribe_audio(str(source), source="volmarr_voice_contract")
        speech = json.loads(
            text_to_speech_tool(
                transcript["transcript"], output_path=str(tmp_path / "spoken.wav")
            )
        )
    finally:
        manager.unload()

    output = Path(speech["file_path"])
    assert transcript == {
        "success": True,
        "transcript": "wyrd wakes",
        "provider": "rune-stt",
    }
    assert speech["success"] is True
    assert speech["provider"] == "rune-tts"
    assert speech["chunk_count"] == 1
    assert output == tmp_path / "spoken.wav"
    assert output.is_file() and output.stat().st_size > 44
    assert source.read_bytes() == source_before
