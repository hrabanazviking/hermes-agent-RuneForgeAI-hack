"""Contracts for the profile-local Kista Secret Source plugin."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

from agent.secret_sources.base import ErrorKind
from tests.secret_sources.conformance import SecretSourceConformance


_PLUGIN_DIR = Path(__file__).parents[2] / "plugins" / "kista-secret-source"


def _source_module():
    spec = importlib.util.spec_from_file_location(
        "test_kista_secret_source_impl", _PLUGIN_DIR / "source.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def source_module():
    return _source_module()


@pytest.fixture
def source(source_module):
    return source_module.KistaSource()


class TestKistaSourceConformance(SecretSourceConformance):
    @pytest.fixture
    def source(self, source_module):
        return source_module.KistaSource()


def test_fetch_uses_explicit_cli_contract_and_never_surfaces_secret(
    source, source_module, tmp_path, monkeypatch, caplog, capsys
):
    canary = "KISTA-CANARY-DO-NOT-LEAK"
    calls = []
    fake_binary = tmp_path / "kista"
    fake_binary.write_text("fixture", encoding="utf-8")
    monkeypatch.setattr(
        source_module, "_resolve_command", lambda _path: ([str(fake_binary)], fake_binary)
    )

    def fake_run(argv, *, allow_env=(), extra_env=None, timeout=30):
        calls.append((argv, allow_env, extra_env, timeout))
        return subprocess.CompletedProcess(argv, 0, json.dumps({"key": canary}), "")

    monkeypatch.setattr(source_module, "run_secret_cli", fake_run)

    result = source.fetch(
        {
            "enabled": True,
            "env": {"OPENROUTER_API_KEY": "kista://openrouter/key"},
        },
        tmp_path,
    )

    assert result.ok
    assert result.secrets == {"OPENROUTER_API_KEY": canary}
    assert calls == [
        (
            [str(fake_binary), "get", "--", "openrouter"],
            (),
            {"KISTA_DIR": str((tmp_path / "credentials").resolve()), "PYTHONUTF8": "1"},
            30.0,
        )
    ]
    captured = capsys.readouterr()
    assert canary not in captured.out
    assert canary not in captured.err
    assert canary not in caplog.text


def test_fetch_deduplicates_entry_reads_for_multiple_fields(
    source, source_module, tmp_path, monkeypatch
):
    fake_binary = tmp_path / "kista"
    fake_binary.write_text("fixture", encoding="utf-8")
    monkeypatch.setattr(
        source_module, "_resolve_command", lambda _path: ([str(fake_binary)], fake_binary)
    )
    calls = []

    def fake_run(argv, **_kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(
            argv, 0, json.dumps({"username": "runa", "password": "warded"}), ""
        )

    monkeypatch.setattr(source_module, "run_secret_cli", fake_run)
    result = source.fetch(
        {
            "env": {
                "SERVICE_USER": "kista://service/username",
                "SERVICE_PASSWORD": "kista://service/password",
            }
        },
        tmp_path,
    )

    assert result.secrets == {"SERVICE_USER": "runa", "SERVICE_PASSWORD": "warded"}
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("stdout", "returncode", "expected_kind"),
    [
        ("not-json", 0, ErrorKind.INTERNAL),
        ("No entry found", 1, ErrorKind.REF_INVALID),
        (json.dumps({"key": ""}), 0, ErrorKind.EMPTY_VALUE),
    ],
)
def test_failures_are_classified_without_echoing_cli_output(
    source, source_module, tmp_path, monkeypatch, stdout, returncode, expected_kind
):
    fake_binary = tmp_path / "kista"
    fake_binary.write_text("fixture", encoding="utf-8")
    monkeypatch.setattr(
        source_module, "_resolve_command", lambda _path: ([str(fake_binary)], fake_binary)
    )
    monkeypatch.setattr(
        source_module,
        "run_secret_cli",
        lambda argv, **_kwargs: subprocess.CompletedProcess(argv, returncode, stdout, stdout),
    )

    result = source.fetch({"env": {"API_KEY": "kista://service/key"}}, tmp_path)

    assert not result.ok
    assert result.error_kind == expected_kind
    assert stdout not in (result.error or "")
    assert stdout not in "\n".join(result.warnings)


def test_vault_path_cannot_escape_active_profile(
    source, source_module, tmp_path, monkeypatch
):
    called = False

    def forbidden(_path):
        nonlocal called
        called = True
        return None, None

    monkeypatch.setattr(source_module, "_resolve_command", forbidden)
    result = source.fetch(
        {"vault_dir": "../shared", "env": {"API_KEY": "kista://service/key"}},
        tmp_path,
    )

    assert not result.ok
    assert result.error_kind == ErrorKind.NOT_CONFIGURED
    assert not called


def test_real_subprocess_keeps_a_b_a_vaults_isolated(source, tmp_path):
    helper = tmp_path / "fake_kista.py"
    helper.write_text(
        "import json, os\n"
        "from pathlib import Path\n"
        "profile = Path(os.environ['KISTA_DIR']).parent.name\n"
        "print(json.dumps({'key': 'secret-for-' + profile}))\n",
        encoding="utf-8",
    )
    home_a = tmp_path / "profile-a"
    home_b = tmp_path / "profile-b"
    home_a.mkdir()
    home_b.mkdir()
    cfg = {
        "binary_path": str(helper),
        "env": {"PROFILE_API_KEY": "kista://service/key"},
    }

    values = [source.fetch(cfg, home).secrets["PROFILE_API_KEY"] for home in (home_a, home_b, home_a)]

    assert values == ["secret-for-profile-a", "secret-for-profile-b", "secret-for-profile-a"]


def test_real_plugin_discovery_registers_and_applies_kista(tmp_path, monkeypatch):
    from agent.secret_sources import registry
    from hermes_constants import hermes_home_key
    from hermes_cli.plugins import PluginManager

    home = tmp_path / "home"
    home.mkdir()
    helper = tmp_path / "fake_kista.py"
    helper.write_text("import json\nprint(json.dumps({'key': 'from-kista'}))\n", encoding="utf-8")
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [kista-secret-source]\n"
        "secrets:\n"
        "  kista:\n"
        "    enabled: true\n"
        f"    binary_path: {json.dumps(str(helper))}\n"
        "    env:\n"
        "      HERMES_TEST_KISTA_API_KEY: kista://openrouter/key\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.delenv("HERMES_TEST_KISTA_API_KEY", raising=False)
    registry._reset_registry_for_tests()
    monkeypatch.setattr(
        PluginManager, "_refresh_secret_sources_after_discovery", lambda _self: None
    )

    try:
        manager = PluginManager()
        manager.discover_and_load()

        loaded = manager._plugins["kista-secret-source"]
        registered = registry.get_source("kista", scope=hermes_home_key(home))
        environment = {}
        report = registry.apply_all(
            {
                "kista": {
                    "enabled": True,
                    "binary_path": str(helper),
                    "env": {"HERMES_TEST_KISTA_API_KEY": "kista://openrouter/key"},
                }
            },
            home,
            environ=environment,
        )
        assert loaded.enabled
        assert registered is not None
        assert registered.scheme == "kista"
        assert environment["HERMES_TEST_KISTA_API_KEY"] == "from-kista"
        assert report.provenance["HERMES_TEST_KISTA_API_KEY"].source == "kista"
    finally:
        os.environ.pop("HERMES_TEST_KISTA_API_KEY", None)
        registry._reset_registry_for_tests()
