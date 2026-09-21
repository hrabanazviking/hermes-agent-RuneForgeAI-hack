"""Contracts for the official WYRD world-model service attachment."""

from __future__ import annotations

import argparse
import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)


class _HealthHandler(BaseHTTPRequestHandler):
    version_value: str | None = None
    requests: list[dict[str, str]] = []

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
        type(self).requests.append(
            {
                "path": self.path,
                "authorization": self.headers.get("Authorization", ""),
                "cookie": self.headers.get("Cookie", ""),
            }
        )
        body: dict[str, str] = {"status": "ok"}
        if type(self).version_value is not None:
            body["version"] = type(self).version_value
        payload = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, _format: str, *_args) -> None:
        return None


class _RedirectHandler(BaseHTTPRequestHandler):
    target = ""

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
        self.send_response(307)
        self.send_header("Location", type(self).target)
        self.end_headers()

    def log_message(self, _format: str, *_args) -> None:
        return None


class _LeakDetectorHandler(BaseHTTPRequestHandler):
    requests = 0

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
        type(self).requests += 1
        self.send_response(204)
        self.end_headers()

    def log_message(self, _format: str, *_args) -> None:
        return None


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


def _write_profile(home, port: int) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        f"        wyrd_base_url: http://127.0.0.1:{port}\n"
        "        wyrd_probe_timeout_ms: 1000\n",
        encoding="utf-8",
    )


def _health_command(manager):
    command = manager._cli_commands["volmarr"]
    parser = argparse.ArgumentParser()
    command["setup_fn"](parser)
    args = parser.parse_args(["world", "health", "--json"])
    return command["handler_fn"], args


def test_wyrd_probe_accepts_official_contract_and_tracks_profiles(tmp_path, capsys):
    from hermes_cli import plugins as plugins_mod

    class Official(_HealthHandler):
        version_value = None
        requests = []

    class Documented(_HealthHandler):
        version_value = "1.1.0"
        requests = []

    profile_a = get_hermes_home()
    profile_b = tmp_path / "profile-b"
    with _server(Official) as server_a, _server(Documented) as server_b:
        _write_profile(profile_a, server_a.server_address[1])
        _write_profile(profile_b, server_b.server_address[1])
        manager = plugins_mod.PluginManager()
        manager.discover_and_load()
        try:
            handler, args = _health_command(manager)
            reports = []
            for home in (profile_a, profile_b, profile_a):
                token = set_hermes_home_override(home)
                try:
                    assert handler(args) == 0
                    reports.append(json.loads(capsys.readouterr().out))
                finally:
                    reset_hermes_home_override(token)
        finally:
            manager.unload()

    assert [report["server_version"] for report in reports] == [None, "1.1.0", None]
    assert all(report["api_contract"] == "wyrd-http-v1" for report in reports)
    assert all(report["minimum_server_version"] == "1.0.0" for report in reports)
    assert [request["path"] for request in Official.requests] == ["/health", "/health"]
    assert [request["path"] for request in Documented.requests] == ["/health"]
    assert all(
        not request["authorization"] and not request["cookie"]
        for request in Official.requests + Documented.requests
    )


def test_wyrd_probe_rejects_non_loopback_before_network(capsys):
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        "        wyrd_base_url: https://example.com\n",
        encoding="utf-8",
    )
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        handler, args = _health_command(manager)
        assert handler(args) == 1
        report = json.loads(capsys.readouterr().out)
    finally:
        manager.unload()

    assert report["status"] == "configuration_error"
    assert report["error_type"] == "WyrdConfigurationError"


def test_wyrd_probe_rejects_outdated_version(capsys):
    from hermes_cli import plugins as plugins_mod

    class Outdated(_HealthHandler):
        version_value = "0.9.9"
        requests = []

    with _server(Outdated) as server:
        _write_profile(get_hermes_home(), server.server_address[1])
        manager = plugins_mod.PluginManager()
        manager.discover_and_load()
        try:
            handler, args = _health_command(manager)
            assert handler(args) == 1
            report = json.loads(capsys.readouterr().out)
        finally:
            manager.unload()

    assert report["status"] == "server_outdated"
    assert report["server_version"] == "0.9.9"


def test_wyrd_probe_does_not_follow_redirects(capsys):
    from hermes_cli import plugins as plugins_mod

    _LeakDetectorHandler.requests = 0
    with _server(_LeakDetectorHandler) as target, _server(_RedirectHandler) as redirect:
        _RedirectHandler.target = f"http://127.0.0.1:{target.server_address[1]}/captured"
        _write_profile(get_hermes_home(), redirect.server_address[1])
        manager = plugins_mod.PluginManager()
        manager.discover_and_load()
        try:
            handler, args = _health_command(manager)
            assert handler(args) == 1
            report = json.loads(capsys.readouterr().out)
        finally:
            manager.unload()

    assert report["status"] == "protocol_error"
    assert _LeakDetectorHandler.requests == 0
