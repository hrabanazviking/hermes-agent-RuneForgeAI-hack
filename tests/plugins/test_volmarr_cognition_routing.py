"""Behavior contracts for the metadata-only cognition routing API."""

from __future__ import annotations

import argparse
import json
import socket

import pytest

from hermes_constants import get_hermes_home


def _load_router_plugin():
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        "        cognition_local_input_limit_bytes: 100\n",
        encoding="utf-8",
    )
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    return manager


def _invoke_route(manager, tmp_path, payload):
    request_path = tmp_path / "route-request.json"
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    command = manager._cli_commands["volmarr"]
    parser = argparse.ArgumentParser()
    command["setup_fn"](parser)
    args = parser.parse_args(
        ["cognition", "route", "--request", str(request_path)]
    )
    return command["handler_fn"](args)


@pytest.mark.parametrize(
    ("request_overrides", "route", "reason"),
    [
        (
            {"deterministic_available": True, "requires_tools": True},
            "deterministic",
            "deterministic.available",
        ),
        ({}, "local", "local.within_bounds"),
        ({"requires_tools": True}, "cloud", "capability.tools"),
        ({"requires_vision": True}, "cloud", "capability.vision"),
        ({"requires_external_data": True}, "cloud", "capability.external_data"),
        ({"local_failures": 1}, "cloud", "local.previous_failure"),
        ({"complexity": "high"}, "cloud", "complexity.high"),
        ({"input_bytes": 101}, "cloud", "input.over_local_limit"),
    ],
)
def test_route_contract_selects_the_first_required_capability_tier(
    tmp_path,
    capsys,
    request_overrides,
    route,
    reason,
):
    manager = _load_router_plugin()
    payload = {
        "schema_version": 1,
        "operation": "event.classification",
        "input_bytes": 42,
        **request_overrides,
    }
    try:
        assert _invoke_route(manager, tmp_path, payload) == 0
        decision = json.loads(capsys.readouterr().out)
        assert decision["schema"] == "runeforge.cognition.route"
        assert decision["schema_version"] == 1
        assert decision["route"] == route
        assert decision["reason"] == reason
        assert decision["local_input_limit_bytes"] == 100
    finally:
        manager.unload()


class _SocketRecorder:
    def __init__(self, payloads: list[bytes]) -> None:
        self._payloads = payloads

    def __enter__(self):
        return self

    def __exit__(self, *_exc) -> None:
        return None

    def settimeout(self, _timeout: float) -> None:
        return None

    def connect(self, _path: str) -> None:
        return None

    def sendall(self, payload: bytes) -> None:
        self._payloads.append(payload)


def test_route_decisions_publish_versioned_content_free_telemetry(
    tmp_path,
    capsys,
    monkeypatch,
):
    payloads: list[bytes] = []
    monkeypatch.setattr(socket, "AF_UNIX", object(), raising=False)
    monkeypatch.setattr(socket, "socket", lambda *_args: _SocketRecorder(payloads))
    manager = _load_router_plugin()
    try:
        for route_request in (
            {
                "schema_version": 1,
                "operation": "memory.tagging",
                "input_bytes": 42,
            },
            {
                "schema_version": 1,
                "operation": "code.review",
                "input_bytes": 42,
                "requires_tools": True,
            },
        ):
            assert _invoke_route(manager, tmp_path, route_request) == 0
            capsys.readouterr()

        messages = [json.loads(payload.decode()) for payload in payloads]
        assert [message["type"] for message in messages] == [
            "hermes.cognition.local",
            "hermes.cognition.escalated",
        ]
        assert all(
            message["data"]["schema"] == "runeforge.cognition.telemetry"
            for message in messages
        )
        assert all(message["data"]["schema_version"] == 1 for message in messages)
        serialized = json.dumps(messages)
        assert "prompt" not in serialized
        assert "messages" not in serialized
        assert "response" not in serialized
    finally:
        manager.unload()


def test_route_contract_rejects_content_fields_without_echoing_content(tmp_path, capsys):
    manager = _load_router_plugin()
    payload = {
        "schema_version": 1,
        "operation": "event.classification",
        "input_bytes": 12,
        "prompt": "never echo rune-secret",
    }
    try:
        assert _invoke_route(manager, tmp_path, payload) == 2
        captured = capsys.readouterr()
        assert captured.out == ""
        error = json.loads(captured.err)
        assert error["error"] == "invalid_routing_request"
        assert "prompt" in error["detail"]
        assert "rune-secret" not in captured.err
    finally:
        manager.unload()


def test_route_contract_rejects_non_boolean_capability_flags(tmp_path, capsys):
    manager = _load_router_plugin()
    payload = {
        "schema_version": 1,
        "operation": "event.classification",
        "input_bytes": 12,
        "requires_tools": "false",
    }
    try:
        assert _invoke_route(manager, tmp_path, payload) == 2
        error = json.loads(capsys.readouterr().err)
        assert error["error"] == "invalid_routing_request"
        assert error["detail"] == "requires_tools must be a boolean"
    finally:
        manager.unload()
