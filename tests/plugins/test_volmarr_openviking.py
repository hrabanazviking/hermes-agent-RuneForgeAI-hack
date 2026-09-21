"""Contracts for the OpenViking provider/server attachment."""

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
    version = "0.4.21"
    requests: list[dict[str, str]] = []

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
        type(self).requests.append(
            {
                "path": self.path,
                "authorization": self.headers.get("Authorization", ""),
            }
        )
        payload = json.dumps(
            {"status": "ok", "healthy": True, "version": type(self).version}
        ).encode()
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
        f"        openviking_base_url: http://127.0.0.1:{port}\n"
        "        openviking_probe_timeout_ms: 1000\n",
        encoding="utf-8",
    )


def _health_command(manager):
    command = manager._cli_commands["volmarr"]
    parser = argparse.ArgumentParser()
    command["setup_fn"](parser)
    args = parser.parse_args(["memory", "openviking", "health", "--json"])
    return command["handler_fn"], args


def test_openviking_probe_tracks_profiles_and_sends_no_credentials(
    tmp_path,
    capsys,
):
    from hermes_cli import plugins as plugins_mod

    class ProfileA(_HealthHandler):
        version = "0.4.21"
        requests = []

    class ProfileB(_HealthHandler):
        version = "0.4.22"
        requests = []

    profile_a = get_hermes_home()
    profile_b = tmp_path / "profile-b"
    with _server(ProfileA) as server_a, _server(ProfileB) as server_b:
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

    assert [report["server_version"] for report in reports] == [
        "0.4.21",
        "0.4.22",
        "0.4.21",
    ]
    assert all(report["provider_available"] for report in reports)
    assert all(report["minimum_server_version"] == "0.4.21" for report in reports)
    assert [request["path"] for request in ProfileA.requests] == ["/health", "/health"]
    assert [request["path"] for request in ProfileB.requests] == ["/health"]
    assert all(not request["authorization"] for request in ProfileA.requests + ProfileB.requests)


def test_openviking_probe_rejects_non_loopback_before_network(capsys):
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        "        openviking_base_url: https://example.com\n",
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
    assert report["error_type"] == "OpenVikingConfigurationError"


def test_openviking_probe_reports_outdated_server(capsys):
    from hermes_cli import plugins as plugins_mod

    class Outdated(_HealthHandler):
        version = "0.4.20"
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
    assert report["server_version"] == "0.4.20"
    assert report["minimum_server_version"] == "0.4.21"


def test_openviking_probe_does_not_follow_redirects(capsys):
    from hermes_cli import plugins as plugins_mod

    _LeakDetectorHandler.requests = 0
    with _server(_LeakDetectorHandler) as target, _server(_RedirectHandler) as redirect:
        _RedirectHandler.target = (
            f"http://127.0.0.1:{target.server_address[1]}/captured"
        )
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
