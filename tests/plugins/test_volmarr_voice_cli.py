"""Operator-only avatar CLI registration contracts."""

from __future__ import annotations

import argparse
import json
import socket

import pytest

from hermes_constants import get_hermes_home


def _enable_plugin(home) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [volmarr-voice]\n",
        encoding="utf-8",
    )


def test_real_discovery_registers_operator_cli_without_runtime_hooks_or_tools():
    from hermes_cli.plugins import PluginManager

    _enable_plugin(get_hermes_home())
    manager = PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-voice"]
        command = manager._cli_commands["volmarr-voice"]
        assert command["plugin"] == "volmarr-voice"
        assert command["plugin_key"] == "volmarr-voice"
        assert loaded.hooks_registered == []
        assert loaded.tools_registered == ["voice_pipeline_readiness"]
        assert set(command) >= {"setup_fn", "handler_fn", "plugin"}
    finally:
        manager.unload()


def test_status_and_invalid_paths_never_read_token_or_open_socket(
    monkeypatch, capsys
):
    from hermes_cli.plugins import PluginManager

    _enable_plugin(get_hermes_home())
    monkeypatch.setenv("VOLMARR_AVATAR_TOKEN", "do-not-read-or-print-this-token-value")

    def forbidden_socket(*_args, **_kwargs):
        raise AssertionError("status must not create a socket")

    monkeypatch.setattr(socket, "socket", forbidden_socket)
    manager = PluginManager()
    manager.discover_and_load()
    try:
        command = manager._cli_commands["volmarr-voice"]
        parser = argparse.ArgumentParser(prog="hermes volmarr-voice")
        command["setup_fn"](parser)
        args = parser.parse_args(["status", "--json"])
        assert command["handler_fn"](args) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["serve_enabled"] is True
        assert payload["listener_started"] is False
        assert payload["runtime_registered"] is False
        assert payload["automatic_voice_mirroring"] is False
        assert "VOLMARR_AVATAR_TOKEN" not in payload
        with pytest.raises(SystemExit):
            parser.parse_args(["serve", "--port", "80"])
        error_output = capsys.readouterr().err
    finally:
        manager.unload()

    assert "do-not-read-or-print-this-token-value" not in json.dumps(payload)
    assert "do-not-read-or-print-this-token-value" not in error_output
