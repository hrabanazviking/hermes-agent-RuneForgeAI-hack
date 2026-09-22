"""End-to-end containment contract for secrets supplied by Kista."""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import socket
from pathlib import Path


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


def _invoke_cognition_route(manager, request_path: Path) -> int:
    request_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "operation": "memory.tagging",
                "input_bytes": 42,
            }
        ),
        encoding="utf-8",
    )
    command = manager._cli_commands["volmarr"]
    parser = argparse.ArgumentParser()
    command["setup_fn"](parser)
    args = parser.parse_args(["cognition", "route", "--request", str(request_path)])
    return command["handler_fn"](args)


def _profile_database_bytes(home: Path) -> bytes:
    database_suffixes = (".db", ".db-wal", ".db-shm")
    return b"".join(
        path.read_bytes()
        for path in home.rglob("*")
        if path.is_file() and path.name.endswith(database_suffixes)
    )


def test_kista_canary_never_reaches_durable_or_observable_surfaces(
    tmp_path,
    monkeypatch,
    capsys,
    caplog,
):
    from agent.redact import (
        RedactingFormatter,
        clear_vault_redaction_values,
        redact_terminal_output,
    )
    from agent.secret_sources import registry
    from hermes_cli.plugins import PluginManager
    from hermes_constants import hermes_home_key
    from hermes_state import SessionDB

    home = tmp_path / "profile"
    home.mkdir()
    helper = tmp_path / "fake_kista.py"
    canary = "kista-canary-opaque-value-7f36e1"
    helper.write_text(
        f"import json\nprint(json.dumps({{'key': {canary!r}}}))\n",
        encoding="utf-8",
    )
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [kista-secret-source, volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        "        socket_path: state/test-runa.sock\n"
        "        source: hermes-canary-test\n"
        "secrets:\n"
        "  kista:\n"
        "    enabled: true\n"
        f"    binary_path: {json.dumps(str(helper))}\n"
        "    env:\n"
        "      HERMES_TEST_KISTA_PASSWORD: kista://service/key\n",
        encoding="utf-8",
    )

    payloads: list[bytes] = []
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.delenv("HERMES_TEST_KISTA_PASSWORD", raising=False)
    monkeypatch.setattr(socket, "AF_UNIX", object(), raising=False)
    monkeypatch.setattr(socket, "socket", lambda *_args: _SocketRecorder(payloads))
    # Discovery must register the real source. Applying it explicitly keeps this
    # test independent of the host interpreter's optional dotenv dependency.
    monkeypatch.setattr(
        PluginManager, "_refresh_secret_sources_after_discovery", lambda _self: None
    )
    registry._reset_registry_for_tests()
    manager = None
    logger = logging.getLogger("tests.kista_canary")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(RedactingFormatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    try:
        manager = PluginManager()
        manager.discover_and_load()
        assert set(manager._plugins) >= {"kista-secret-source", "volmarr-core"}
        assert registry.get_source("kista", scope=hermes_home_key(home)) is not None

        environment: dict[str, str] = {}
        report = registry.apply_all(
            {
                "kista": {
                    "enabled": True,
                    "binary_path": str(helper),
                    "env": {
                        "HERMES_TEST_KISTA_PASSWORD": "kista://service/key",
                    },
                }
            },
            home,
            environ=environment,
        )
        assert report.sources[0].result.ok
        assert environment["HERMES_TEST_KISTA_PASSWORD"] == canary

        manager.invoke_hook(
            "on_session_start",
            session_id="canary-session",
            model="local-model",
            platform="cli",
        )
        manager.invoke_hook(
            "pre_tool_call",
            tool_name="terminal",
            args={"command": f"printf {canary}"},
            session_id="canary-session",
            tool_call_id="canary-call",
        )
        manager.invoke_hook(
            "post_tool_call",
            tool_name="terminal",
            args={"command": f"printf {canary}"},
            result=canary,
            error_message=canary,
            error_type="ToolError",
            status="error",
            session_id="canary-session",
            tool_call_id="canary-call",
        )
        manager.invoke_hook(
            "on_session_end",
            session_id="canary-session",
            failed=True,
            turn_exit_reason="tool_error",
        )
        manager.invoke_hook("on_session_finalize", session_id="canary-session")
        assert _invoke_cognition_route(manager, tmp_path / "route-request.json") == 0

        redacted = redact_terminal_output(
            f"tool returned {canary}", command="printf secret", force=True
        )
        assert canary not in redacted
        assert "«redacted-vault-secret»" in redacted

        db_path = home / "state.db"
        db = SessionDB(db_path=db_path)
        try:
            db.create_session("canary-session", source="cli")
            db.append_message(
                "canary-session",
                role="tool",
                content=redacted,
                tool_name="terminal",
                tool_call_id="canary-call",
            )
            messages = db.get_messages("canary-session")
            assert len(messages) == 1
            assert canary not in messages[0]["content"]
        finally:
            db.close()

        logger.info("formatter boundary: %s", canary)
        handler.flush()
        assert canary not in stream.getvalue()
        assert "«redacted-vault-secret»" in stream.getvalue()

        serialized_events = b"\n".join(payloads)
        assert payloads
        assert canary.encode() not in serialized_events
        event_types = {json.loads(payload)["type"] for payload in payloads}
        assert "hermes.tool.failed" in event_types
        assert "hermes.cognition.local" in event_types

        # Includes state.db and every memory database or sidecar actually
        # created by Volmarr hooks. Kista itself must create no memory store.
        assert canary.encode() not in _profile_database_bytes(home)
        if (home / "memory").exists():
            assert not list((home / "memory").glob("*.db"))

        captured = capsys.readouterr()
        assert canary not in captured.out
        assert canary not in captured.err
        assert canary not in caplog.text
    finally:
        logger.removeHandler(handler)
        handler.close()
        if manager is not None:
            manager.unload()
        clear_vault_redaction_values(scope=home)
        os.environ.pop("HERMES_TEST_KISTA_PASSWORD", None)
        registry._reset_registry_for_tests()
