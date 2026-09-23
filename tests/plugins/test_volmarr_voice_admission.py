"""Pre-socket avatar admission contracts."""

from __future__ import annotations

import importlib
import json

import pytest

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)


def _enable_plugin(home) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [volmarr-voice]\n",
        encoding="utf-8",
    )


def test_real_discovery_authenticates_env_bearers_with_a_b_a_redaction(tmp_path):
    from agent.redact import clear_vault_redaction_values, redact_registered_vault_values
    from hermes_cli.plugins import PluginManager

    home_a = get_hermes_home()
    home_b = tmp_path / "home-b"
    _enable_plugin(home_a)
    _enable_plugin(home_b)
    token_a = "A1" * 20
    token_b = "B2" * 20
    manager = PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-voice"]
        admission = importlib.import_module(f"{loaded.module.__name__}.admission")
        for home in (home_a, home_b):
            token = set_hermes_home_override(home)
            try:
                clear_vault_redaction_values()
            finally:
                reset_hermes_home_override(token)
        observed = []
        for home, value, foreign in (
            (home_a, token_a, token_b),
            (home_b, token_b, token_a),
            (home_a, token_a, token_b),
        ):
            token = set_hermes_home_override(home)
            try:
                bearer = admission.load_avatar_token({"VOLMARR_AVATAR_TOKEN": value})
                admission.authorize_bearer(f"Bearer {value}", bearer)
                observed.append(
                    (
                        repr(bearer),
                        redact_registered_vault_values(f"secret={value}"),
                        redact_registered_vault_values(f"foreign={foreign}"),
                    )
                )
                with pytest.raises(admission.AvatarAdmissionError) as rejected:
                    admission.authorize_bearer("Bearer wrong", bearer)
                assert str(rejected.value) == "avatar presentation admission refused"
            finally:
                reset_hermes_home_override(token)
        with pytest.raises(admission.AvatarAdmissionError):
            admission.load_avatar_token({"VOLMARR_AVATAR_TOKEN": "changeme"})
    finally:
        for home in (home_a, home_b):
            token = set_hermes_home_override(home)
            try:
                clear_vault_redaction_values()
            finally:
                reset_hermes_home_override(token)
        manager.unload()

    assert observed == [
        (
            "AvatarBearerToken(<redacted>)",
            "secret=«redacted-vault-secret»",
            f"foreign={token_b}",
        ),
        (
            "AvatarBearerToken(<redacted>)",
            "secret=«redacted-vault-secret»",
            f"foreign={token_a}",
        ),
        (
            "AvatarBearerToken(<redacted>)",
            "secret=«redacted-vault-secret»",
            f"foreign={token_b}",
        ),
    ]


def test_listener_and_ready_validation_refuse_non_presentation_inputs():
    from hermes_cli.plugins import PluginManager

    home = get_hermes_home()
    _enable_plugin(home)
    manager = PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-voice"]
        admission = importlib.import_module(f"{loaded.module.__name__}.admission")
        assert admission.validate_listener_target(
            host="127.0.0.1",
            port=8765,
            path="/v1/presentation",
            origin=None,
        ) == ("127.0.0.1", 8765, "/v1/presentation")
        ready = admission.parse_ready_message(
            json.dumps(
                {
                    "type": "ready",
                    "contract": "runeforge.avatar.presentation.v1",
                    "session_id": "avatar-session",
                }
            )
        )
        invalid_targets = (
            {"host": "0.0.0.0", "port": 8765, "path": "/v1/presentation"},
            {"host": "localhost", "port": 8765, "path": "/v1/presentation"},
            {"host": "127.0.0.1", "port": 80, "path": "/v1/presentation"},
            {"host": "127.0.0.1", "port": 8765, "path": "/ws"},
            {
                "host": "127.0.0.1",
                "port": 8765,
                "path": "/v1/presentation",
                "origin": "https://example.test",
            },
        )
        for candidate in invalid_targets:
            with pytest.raises(admission.AvatarAdmissionError):
                admission.validate_listener_target(**candidate)
        invalid_messages = (
            {"type": "invoke", "contract": ready.contract, "session_id": ready.session_id},
            {
                "type": "ready",
                "contract": ready.contract,
                "session_id": ready.session_id,
                "audio_data": "forbidden",
            },
            {"type": "ready", "contract": "wrong", "session_id": ready.session_id},
        )
        for payload in invalid_messages:
            with pytest.raises(admission.AvatarAdmissionError):
                admission.parse_ready_message(json.dumps(payload))
        with pytest.raises(admission.AvatarAdmissionError):
            admission.parse_ready_message("x" * 513)
    finally:
        manager.unload()

    assert ready.session_id == "avatar-session"
