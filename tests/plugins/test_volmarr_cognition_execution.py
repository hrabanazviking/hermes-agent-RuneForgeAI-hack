"""Behavior contracts for bounded local reflex execution."""

from __future__ import annotations

import argparse
import json
import socket
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from hermes_constants import get_hermes_home


SERVICE_KEY = "reflex_key_" + "a" * 32


class _CompletionHandler(BaseHTTPRequestHandler):
    requests: list[dict] = []
    response_status = 200

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        self.requests.append(
            {
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "content_type": self.headers.get("Content-Type"),
                "body": json.loads(body),
            }
        )
        if self.response_status != 200:
            self.send_response(self.response_status)
            self.end_headers()
            return
        payload = json.dumps(
            {
                "id": "cmpl-aesir-1",
                "object": "chat.completion",
                "model": "aesir-test",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "calm"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 1,
                    "total_tokens": 6,
                },
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, _format: str, *_args) -> None:
        return None


class _RedirectHandler(BaseHTTPRequestHandler):
    target_url = ""

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
        self.send_response(307)
        self.send_header("Location", self.target_url)
        self.end_headers()

    def log_message(self, _format: str, *_args) -> None:
        return None


class _LeakDetectorHandler(BaseHTTPRequestHandler):
    requests = 0

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
        type(self).requests += 1
        self.send_response(204)
        self.end_headers()

    def log_message(self, _format: str, *_args) -> None:
        return None


@contextmanager
def _completion_server(*, response_status: int = 200):
    _CompletionHandler.requests = []
    _CompletionHandler.response_status = response_status
    server = ThreadingHTTPServer(("127.0.0.1", 0), _CompletionHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@contextmanager
def _server(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _load_plugin(port: int):
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    (home / "secrets").mkdir(parents=True, exist_ok=True)
    key_path = home / "secrets" / "aesir.key"
    key_path.write_text(SERVICE_KEY + "\n", encoding="ascii")
    key_path.chmod(0o600)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        f"        cognition_base_url: http://127.0.0.1:{port}/v1\n"
        "        cognition_api_key_file: secrets/aesir.key\n"
        "        cognition_local_input_limit_bytes: 100\n"
        "        cognition_request_timeout_ms: 1000\n"
        "        cognition_local_max_tokens: 64\n",
        encoding="utf-8",
    )
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    return manager


def _invoke_execute(manager, tmp_path: Path, payload: dict) -> int:
    request_path = tmp_path / "execution-request.json"
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    command = manager._cli_commands["volmarr"]
    parser = argparse.ArgumentParser()
    command["setup_fn"](parser)
    args = parser.parse_args(
        ["cognition", "execute", "--request", str(request_path)]
    )
    return command["handler_fn"](args)


def _execution_payload(*, mode: str = "auto", content: str = "classify this") -> dict:
    return {
        "schema_version": 1,
        "route": {
            "schema_version": 2,
            "operation": "event.classification",
            "input_bytes": len(content.encode("utf-8")),
            "mode": mode,
        },
        "local": {
            "model": "aesir-test",
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 32,
        },
    }


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


def test_real_local_execution_is_tool_free_bounded_and_content_safe_in_telemetry(
    tmp_path,
    capsys,
    monkeypatch,
):
    telemetry: list[bytes] = []
    with _completion_server() as server:
        real_socket = socket.socket
        unix_family = object()
        monkeypatch.setattr(socket, "AF_UNIX", unix_family, raising=False)
        monkeypatch.setattr(
            socket,
            "socket",
            lambda family, *args, **kwargs: (
                _SocketRecorder(telemetry)
                if family is unix_family
                else real_socket(family, *args, **kwargs)
            ),
        )
        manager = _load_plugin(server.server_address[1])
        try:
            assert _invoke_execute(manager, tmp_path, _execution_payload()) == 0
            result = json.loads(capsys.readouterr().out)
        finally:
            manager.unload()

    assert result["status"] == "completed"
    assert result["decision"]["route"] == "local"
    assert result["completion"] == {
        "model": "aesir-test",
        "text": "calm",
        "finish_reason": "stop",
        "prompt_tokens": 5,
        "completion_tokens": 1,
        "latency_ms": result["completion"]["latency_ms"],
    }
    assert result["completion"]["latency_ms"] >= 0

    assert len(_CompletionHandler.requests) == 1
    request = _CompletionHandler.requests[0]
    assert request["path"] == "/v1/chat/completions"
    assert request["authorization"] == f"Bearer {SERVICE_KEY}"
    assert request["content_type"] == "application/json"
    assert request["body"] == {
        "model": "aesir-test",
        "messages": [{"role": "user", "content": "classify this"}],
        "max_tokens": 32,
        "stream": False,
        "n": 1,
    }

    events = [json.loads(payload) for payload in telemetry]
    assert [event["type"] for event in events] == [
        "hermes.cognition.local",
        "hermes.cognition.local_completed",
    ]
    serialized = json.dumps(events)
    assert "classify this" not in serialized
    assert "calm" not in serialized
    assert SERVICE_KEY not in serialized
    assert events[1]["data"]["context"]["model"] == "aesir-test"


def test_deep_mode_returns_an_escalation_directive_without_calling_a_provider(
    tmp_path,
    capsys,
):
    with _completion_server() as server:
        manager = _load_plugin(server.server_address[1])
        payload = _execution_payload(mode="deep")
        payload.pop("local")
        try:
            assert _invoke_execute(manager, tmp_path, payload) == 0
            result = json.loads(capsys.readouterr().out)
        finally:
            manager.unload()

    assert result["status"] == "escalation_required"
    assert result["decision"]["route"] == "cloud"
    assert result["completion"] is None
    assert _CompletionHandler.requests == []


def test_local_failure_escalates_only_when_mode_is_auto(tmp_path, capsys):
    with _completion_server(response_status=503) as server:
        manager = _load_plugin(server.server_address[1])
        try:
            assert _invoke_execute(manager, tmp_path, _execution_payload()) == 0
            automatic = json.loads(capsys.readouterr().out)
            assert _invoke_execute(
                manager,
                tmp_path,
                _execution_payload(mode="local"),
            ) == 1
            forced = json.loads(capsys.readouterr().out)
        finally:
            manager.unload()

    assert automatic["status"] == "escalation_required"
    assert automatic["error_type"] == "CognitionProtocolError"
    assert forced["status"] == "failed"
    assert forced["error_type"] == "CognitionProtocolError"


def test_declared_input_must_match_local_content_before_network_use(tmp_path, capsys):
    with _completion_server() as server:
        manager = _load_plugin(server.server_address[1])
        payload = _execution_payload()
        payload["route"]["input_bytes"] += 1
        try:
            assert _invoke_execute(manager, tmp_path, payload) == 0
            result = json.loads(capsys.readouterr().out)
        finally:
            manager.unload()

    assert result["status"] == "escalation_required"
    assert result["error_type"] == "RoutingRequestError"
    assert _CompletionHandler.requests == []


def test_completion_refuses_redirects_before_the_bearer_key_can_escape(
    tmp_path,
    capsys,
):
    _LeakDetectorHandler.requests = 0
    with _server(_LeakDetectorHandler) as leak_server:
        _RedirectHandler.target_url = (
            f"http://127.0.0.1:{leak_server.server_address[1]}/capture"
        )
        with _server(_RedirectHandler) as redirect_server:
            manager = _load_plugin(redirect_server.server_address[1])
            try:
                assert _invoke_execute(manager, tmp_path, _execution_payload()) == 0
                result = json.loads(capsys.readouterr().out)
            finally:
                manager.unload()

    assert result["status"] == "escalation_required"
    assert result["error_type"] == "CognitionProtocolError"
    assert _LeakDetectorHandler.requests == 0
