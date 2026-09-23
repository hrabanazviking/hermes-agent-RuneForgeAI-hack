"""Read-only diagnostics for Hermes' native voice pipeline."""

from __future__ import annotations

from typing import Any

from tools.registry import tool_error, tool_result


VOICE_PIPELINE_READINESS_SCHEMA = {
    "name": "voice_pipeline_readiness",
    "description": (
        "Report the active profile's Hermes voice mode, STT/TTS selection, and local "
        "prerequisite status without recording, transcription, synthesis, or provider calls."
    ),
    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
}

_VOICE_MODES = frozenset({"chained", "gpt-live"})


def _section(config: Any, key: str) -> dict[str, Any]:
    value = config.get(key) if isinstance(config, dict) else None
    return value if isinstance(value, dict) else {}


def _name(value: Any, default: str) -> str:
    if not isinstance(value, str):
        return default
    cleaned = value.strip().casefold()
    return cleaned if cleaned and len(cleaned) <= 80 else default


def _bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _tts_status(tts_config: dict[str, Any]) -> dict[str, Any]:
    from tools.tts_command_provider import (
        BUILTIN_TTS_PROVIDERS,
        _resolve_command_provider_config,
    )
    from tools.tts_tool import _get_provider, _select_builtin_engine

    requested = _name(tts_config.get("provider"), "edge")
    resolved = _name(_get_provider(tts_config), "edge")
    if resolved in BUILTIN_TTS_PROVIDERS:
        engine, error = _select_builtin_engine(resolved)
        return {
            "requested_provider": requested,
            "resolved_provider": _name(engine, resolved),
            "provider_kind": "built-in",
            "dependency_available": error is None,
        }
    command = _resolve_command_provider_config(resolved, tts_config)
    return {
        "requested_provider": requested,
        "resolved_provider": resolved,
        "provider_kind": "command" if command is not None else "plugin-or-unknown",
        "dependency_available": None,
    }


def _stt_status(stt_config: dict[str, Any]) -> dict[str, Any]:
    from tools.transcription_command import _resolve_command_stt_provider_config
    from tools.transcription_common import BUILTIN_STT_PROVIDERS
    from tools.transcription_tools import _get_provider, is_stt_enabled
    from tools.voice_mode import (
        _audio_available,
        _termux_voice_capture_available,
        check_voice_requirements,
    )

    requested = _name(stt_config.get("provider"), "auto")
    resolved = _name(_get_provider(stt_config), "none")
    command = _resolve_command_stt_provider_config(resolved, stt_config)
    locally_probeable = resolved in BUILTIN_STT_PROVIDERS or command is not None
    if locally_probeable:
        requirements = check_voice_requirements()
        capture_available = bool(requirements.get("audio_available"))
        stt_available: bool | None = bool(requirements.get("stt_available"))
    else:
        capture_available = _audio_available() or _termux_voice_capture_available()
        stt_available = None
    return {
        "stt_enabled": is_stt_enabled(stt_config),
        "requested_provider": requested,
        "resolved_provider": resolved,
        "provider_kind": (
            "built-in"
            if resolved in BUILTIN_STT_PROVIDERS
            else "command"
            if command is not None
            else "plugin-or-unknown"
        ),
        "capture_available": capture_available,
        "stt_available": stt_available,
        "capture_and_stt_available": (
            capture_available and stt_available if stt_available is not None else None
        ),
        "provider_dependency_checked": locally_probeable,
    }


def build_voice_readiness_handler():
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        if args:
            return tool_error("voice_pipeline_readiness accepts no arguments")
        try:
            from hermes_cli.config import load_config_readonly

            config = load_config_readonly()
            voice = _section(config, "voice")
            stt = _section(config, "stt")
            tts = _section(config, "tts")
            requested_mode = _name(voice.get("voice_chat_mode"), "chained")
            mode = requested_mode if requested_mode in _VOICE_MODES else "invalid"
            stt_status = _stt_status(stt)
            tts_status = _tts_status(tts)
        except Exception:
            return tool_error("Hermes voice readiness could not be resolved")

        tts_dependency_available = tts_status["dependency_available"]
        return tool_result(
            {
                "success": True,
                "calculation": "voice_pipeline_readiness",
                "voice_chat_mode": mode,
                "requested_voice_chat_mode": requested_mode,
                "input": stt_status,
                "output": tts_status,
                "controls": {
                    "auto_tts": _bool(voice.get("auto_tts"), False),
                    "barge_in": _bool(voice.get("barge_in"), True),
                    "client_direct": _bool(voice.get("client_direct"), True),
                },
                "assessment": {
                    "local_prerequisites_checked": stt_status[
                        "provider_dependency_checked"
                    ],
                    "tts_dependency_available": tts_dependency_available,
                    "credentials_checked": False,
                    "provider_connectivity_checked": False,
                    "end_to_end_verified": False,
                },
                "credentials_withheld": True,
                "microphone_opened": False,
                "audio_recorded": False,
                "transcription_performed": False,
                "speech_synthesized": False,
                "provider_contacted": False,
                "source": {
                    "engine": "Hermes Agent",
                    "apis": [
                        "hermes_cli.config.load_config_readonly",
                        "tools.voice_mode.check_voice_requirements",
                    ],
                },
            }
        )

    return handle


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="voice_pipeline_readiness",
        toolset="volmarr_voice",
        schema=VOICE_PIPELINE_READINESS_SCHEMA,
        handler=build_voice_readiness_handler(),
        description=VOICE_PIPELINE_READINESS_SCHEMA["description"],
        emoji="🎙️",
    )
