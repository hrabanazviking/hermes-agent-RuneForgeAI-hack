"""Contracts for the local official Astrology Engine tool boundary."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)


def _write_profile(home: Path, engine: Path, *, timeout: object = 20) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-astrology]\n"
        "  entries:\n"
        "    volmarr-astrology:\n"
        "      settings:\n"
        f"        engine_path: {json.dumps(str(engine))}\n"
        f"        python_path: {json.dumps(sys.executable)}\n"
        f"        timeout_seconds: {json.dumps(timeout)}\n",
        encoding="utf-8",
    )


def _engine_script(path: Path, report: str, *, record: Path | None = None) -> None:
    lines = ["import json, os, sys"]
    if record is not None:
        lines.extend(
            [
                "payload = {",
                "    'argv': sys.argv[1:],",
                "    'stdin_closed': sys.stdin.read(1) == '',",
                "    'secret_present': os.environ.get('OPENROUTER_API_KEY') is not None,",
                "    'hermes_home_present': os.environ.get('HERMES_HOME') is not None,",
                "}",
                f"open({str(record)!r}, 'w', encoding='utf-8').write(json.dumps(payload))",
            ]
        )
    lines.append(f"print({report!r})")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_real_discovery_runs_lunar_with_fixed_argv_and_scrubbed_environment(
    tmp_path,
    monkeypatch,
):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home = get_hermes_home()
    engine = tmp_path / "astrology_engine.py"
    record = tmp_path / "invocation.json"
    _engine_script(engine, "CURRENT LUNAR STATE", record=record)
    _write_profile(home, engine)
    monkeypatch.setenv("OPENROUTER_API_KEY", "must-not-reach-astrology")

    manager = PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-astrology"]
        assert loaded.enabled
        assert set(loaded.tools_registered) == {
            "astrology_lunar",
            "astrology_planetary_hours",
        }
        result = json.loads(
            registry.dispatch("astrology_lunar", {}, scope=manager.scope_key)
        )
    finally:
        manager.unload()

    assert result == {
        "success": True,
        "engine": "hrabanazviking/astrology-engine",
        "calculation": "lunar",
        "interpretation_included": False,
        "report": "CURRENT LUNAR STATE",
    }
    assert json.loads(record.read_text(encoding="utf-8")) == {
        "argv": ["lunar"],
        "stdin_closed": True,
        "secret_present": False,
        "hermes_home_present": False,
    }


def test_lunar_tool_resolves_active_profile_a_b_a(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home_a = get_hermes_home()
    home_b = tmp_path / "profile-b"
    engine_a = tmp_path / "astrology_a.py"
    engine_b = tmp_path / "astrology_b.py"
    _engine_script(engine_a, "MOON FOR PROFILE A")
    _engine_script(engine_b, "MOON FOR PROFILE B")
    _write_profile(home_a, engine_a)
    _write_profile(home_b, engine_b)

    manager = PluginManager()
    manager.discover_and_load()
    try:
        reports = []
        for home in (home_a, home_b, home_a):
            token = set_hermes_home_override(home)
            try:
                payload = json.loads(
                    registry.dispatch("astrology_lunar", {}, scope=manager.scope_key)
                )
                reports.append(payload["report"])
            finally:
                reset_hermes_home_override(token)
    finally:
        manager.unload()

    assert reports == ["MOON FOR PROFILE A", "MOON FOR PROFILE B", "MOON FOR PROFILE A"]


def test_planetary_hours_uses_validated_date_and_coordinates_without_geocoding(
    tmp_path,
):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home = get_hermes_home()
    engine = tmp_path / "astrology_engine.py"
    record = tmp_path / "planet-hours.json"
    _engine_script(engine, "PLANETARY HOURS REPORT", record=record)
    _write_profile(home, engine)

    manager = PluginManager()
    manager.discover_and_load()
    try:
        result = json.loads(
            registry.dispatch(
                "astrology_planetary_hours",
                {
                    "date": "2026-09-22",
                    "latitude": 0,
                    "longitude": -86.1581,
                },
                scope=manager.scope_key,
            )
        )
    finally:
        manager.unload()

    assert result["calculation"] == "planetary_hours"
    assert result["report"] == "PLANETARY HOURS REPORT"
    assert result["interpretation_included"] is False
    invocation = json.loads(record.read_text(encoding="utf-8"))
    assert invocation["argv"] == [
        "planet-hours",
        "--date",
        "2026-09-22",
        "--lat",
        "0",
        "--lon",
        "-86.1581",
    ]
    assert "--city" not in invocation["argv"]
    assert "--nation" not in invocation["argv"]


def test_planetary_hours_rejects_invalid_inputs_before_starting_engine(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home = get_hermes_home()
    engine = tmp_path / "astrology_engine.py"
    marker = tmp_path / "should-not-exist"
    engine.write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('called')\n",
        encoding="utf-8",
    )
    _write_profile(home, engine)

    manager = PluginManager()
    manager.discover_and_load()
    try:
        failures = [
            json.loads(
                registry.dispatch(
                    "astrology_planetary_hours",
                    payload,
                    scope=manager.scope_key,
                )
            )
            for payload in (
                {"date": "2026-02-30", "latitude": 39, "longitude": -86},
                {"date": "2026-09-22", "latitude": True, "longitude": -86},
                {"date": "2026-09-22", "latitude": 39, "longitude": 181},
            )
        ]
    finally:
        manager.unload()

    assert all("error" in result for result in failures)
    assert not marker.exists()


def test_planetary_hours_zero_exit_error_is_not_reported_as_success(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home = get_hermes_home()
    engine = tmp_path / "astrology_engine.py"
    engine.write_text(
        "print('Error calculating planetary hours: polar night')\n",
        encoding="utf-8",
    )
    _write_profile(home, engine)

    manager = PluginManager()
    manager.discover_and_load()
    try:
        result = json.loads(
            registry.dispatch(
                "astrology_planetary_hours",
                {"date": "2026-12-21", "latitude": 69.6492, "longitude": 18.9553},
                scope=manager.scope_key,
            )
        )
    finally:
        manager.unload()

    assert result["error"] == "The local Astrology Engine could not complete the calculation."


def test_lunar_tool_rejects_arguments_before_starting_engine(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home = get_hermes_home()
    engine = tmp_path / "astrology_engine.py"
    marker = tmp_path / "should-not-exist"
    engine.write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('called')\n",
        encoding="utf-8",
    )
    _write_profile(home, engine)

    manager = PluginManager()
    manager.discover_and_load()
    try:
        result = json.loads(
            registry.dispatch(
                "astrology_lunar",
                {"date": "2026-09-22"},
                scope=manager.scope_key,
            )
        )
    finally:
        manager.unload()

    assert "error" in result
    assert not marker.exists()


def test_engine_failure_never_echoes_child_output(tmp_path, capsys, caplog):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home = get_hermes_home()
    engine = tmp_path / "astrology_engine.py"
    canary = "ASTROLOGY-CHILD-FAILURE-CANARY"
    engine.write_text(
        f"import sys\nprint({canary!r})\nprint({canary!r}, file=sys.stderr)\nsys.exit(9)\n",
        encoding="utf-8",
    )
    _write_profile(home, engine)

    manager = PluginManager()
    manager.discover_and_load()
    try:
        raw = registry.dispatch("astrology_lunar", {}, scope=manager.scope_key)
    finally:
        manager.unload()

    assert canary not in raw
    assert "error" in json.loads(raw)
    captured = capsys.readouterr()
    assert canary not in captured.out
    assert canary not in captured.err
    assert canary not in caplog.text


def test_upstream_zero_exit_dependency_message_is_not_reported_as_success(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home = get_hermes_home()
    engine = tmp_path / "astrology_engine.py"
    engine.write_text("print('pyswisseph required.')\n", encoding="utf-8")
    _write_profile(home, engine, timeout=".nan")

    manager = PluginManager()
    manager.discover_and_load()
    try:
        result = json.loads(
            registry.dispatch("astrology_lunar", {}, scope=manager.scope_key)
        )
    finally:
        manager.unload()

    assert result["error"] == (
        "The configured Astrology Engine Python environment does not have "
        "pyswisseph installed."
    )


def test_engine_output_is_bounded(tmp_path):
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    home = get_hermes_home()
    engine = tmp_path / "astrology_engine.py"
    engine.write_text("print('x' * 70000)\n", encoding="utf-8")
    _write_profile(home, engine)

    manager = PluginManager()
    manager.discover_and_load()
    try:
        result = json.loads(
            registry.dispatch("astrology_lunar", {}, scope=manager.scope_key)
        )
    finally:
        manager.unload()

    assert result["error"] == "The local Astrology Engine returned an oversized response."
