"""Contracts for the profile-scoped A.E.S.I.R. endpoint attachment."""

from __future__ import annotations

import argparse
import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)


KEY_A = "a" * 32
KEY_B = "b" * 32


class _CatalogHandler(BaseHTTPRequestHandler):
    requests: list[dict[str, str]] = []

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
        authorization = self.headers.get("Authorization", "")
        self.requests.append({"path": self.path, "authorization": authorization})
        model = {
            f"Bearer {KEY_A}": "aesir-profile-a",
            f"Bearer {KEY_B}": "aesir-profile-b",
        }.get(authorization)
        if model is None:
            self.send_response(401)
            self.end_headers()
            return
        payload = json.dumps(
            {"object": "list", "data": [{"id": model, "object": "model"}]}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, _format: str, *_args) -> None:
        return None


@contextmanager
def _catalog_server():
    _CatalogHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _CatalogHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _write_profile(home: Path, port: int, key: str, *, base_host="127.0.0.1") -> None:
    (home / "secrets").mkdir(parents=True, exist_ok=True)
    key_path = home / "secrets" / "aesir.key"
    key_path.write_text(key + "\n", encoding="ascii")
    key_path.chmod(0o600)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        f"        cognition_base_url: http://{base_host}:{port}/v1\n"
        "        cognition_api_key_file: secrets/aesir.key\n"
        "        cognition_probe_timeout_ms: 1000\n",
        encoding="utf-8",
    )


def _health_command(manager):
    command = manager._cli_commands["volmarr"]
    parser = argparse.ArgumentParser()
    command["setup_fn"](parser)
    args = parser.parse_args(["cognition", "health", "--json"])
    return command["handler_fn"], args


def test_real_catalog_probe_keeps_credentials_and_config_profile_scoped(
    tmp_path,
    capsys,
):
    from hermes_cli import plugins as plugins_mod

    profile_a = get_hermes_home()
    profile_b = tmp_path / "profile-b"
    with _catalog_server() as server:
        port = server.server_address[1]
        _write_profile(profile_a, port, KEY_A)
        _write_profile(profile_b, port, KEY_B)

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

            assert [report["models"] for report in reports] == [
                ["aesir-profile-a"],
                ["aesir-profile-b"],
                ["aesir-profile-a"],
            ]
            assert [row["authorization"] for row in _CatalogHandler.requests] == [
                f"Bearer {KEY_A}",
                f"Bearer {KEY_B}",
                f"Bearer {KEY_A}",
            ]
            assert all(row["path"] == "/v1/models" for row in _CatalogHandler.requests)
            assert KEY_A not in json.dumps(reports)
            assert KEY_B not in json.dumps(reports)
        finally:
            manager.unload()


def test_probe_refuses_non_loopback_endpoint_before_sending_the_key(capsys):
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    _write_profile(home, 18434, KEY_A, base_host="example.com")
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        handler, args = _health_command(manager)
        assert handler(args) == 1
        report = json.loads(capsys.readouterr().out)
        assert report["status"] == "configuration_error"
        assert report["error_type"] == "CognitionConfigurationError"
        assert KEY_A not in json.dumps(report)
    finally:
        manager.unload()
