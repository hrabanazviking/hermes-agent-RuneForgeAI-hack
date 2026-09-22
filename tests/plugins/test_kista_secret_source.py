"""Contracts for the profile-local Kista Secret Source plugin."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
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


def _initialized_vault(root: Path) -> Path:
    vault = root / "credentials"
    vault.mkdir()
    (vault / ".vault_key").write_text("fixture-key", encoding="utf-8")
    (vault / "vault.json.enc").write_text("fixture-vault", encoding="utf-8")
    return vault


def test_fetch_refuses_an_unsafe_initialized_vault_before_invoking_kista(
    source, source_module, tmp_path, monkeypatch
):
    vault = _initialized_vault(tmp_path)
    called = False

    def forbidden(_path):
        nonlocal called
        called = True
        return None, None

    monkeypatch.setattr(
        source_module,
        "_validate_vault_security",
        lambda path: "unsafe vault" if path == vault else None,
    )
    monkeypatch.setattr(source_module, "_resolve_command", forbidden)

    result = source.fetch(
        {"env": {"API_KEY": "kista://service/key"}},
        tmp_path,
    )

    assert not result.ok
    assert result.error_kind == ErrorKind.NOT_CONFIGURED
    assert result.error == "unsafe vault"
    assert not called


def test_windows_sddl_accepts_only_user_system_and_administrators(source_module):
    user = "S-1-5-21-111-222-333-1001"
    private = (
        "D:PAI"
        f"(A;;FA;;;{user})"
        "(A;;FA;;;SY)"
        "(A;;FA;;;BA)"
    )
    broad = private + "(A;;FR;;;S-1-1-0)"
    another_user = private + "(A;;FR;;;S-1-5-21-111-222-333-1002)"

    assert source_module._sddl_is_private(private, user)
    assert not source_module._sddl_is_private(broad, user)
    assert not source_module._sddl_is_private(another_user, user)
    assert not source_module._sddl_is_private("D:PAI(A;;FA;;;SY)", user)


def test_windows_audit_checks_directory_key_and_ciphertext(
    source_module, tmp_path, monkeypatch
):
    vault = _initialized_vault(tmp_path)
    checked = []
    monkeypatch.setattr(source_module, "_uses_windows_acls", lambda: True)
    monkeypatch.setattr(
        source_module, "_windows_current_sid", lambda: "S-1-5-21-1-2-3-1001"
    )
    monkeypatch.setattr(
        source_module,
        "_windows_acl_is_private",
        lambda path, _sid: checked.append(path) or path.name != "vault.json.enc",
    )

    error = source_module._validate_vault_security(vault)

    assert "ACL" in error
    assert checked == [vault, vault / ".vault_key", vault / "vault.json.enc"]


@pytest.mark.skipif(os.name != "nt", reason="Windows ACL contract")
def test_windows_audit_reads_real_acl_and_rejects_everyone_grant(source_module, tmp_path):
    executable = shutil.which("icacls")
    if executable is None:
        pytest.skip("icacls is unavailable")
    vault = _initialized_vault(tmp_path)
    grant = subprocess.run(
        [executable, str(vault), "/grant", "*S-1-1-0:(RX)"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=5,
        check=False,
    )
    if grant.returncode != 0:
        pytest.skip("the test filesystem does not permit ACL changes")

    assert "ACL" in source_module._validate_vault_security(vault)


@pytest.mark.skipif(os.name == "nt", reason="POSIX ownership and mode contract")
def test_posix_audit_requires_private_directory_and_file_modes(source_module, tmp_path):
    vault = _initialized_vault(tmp_path)
    vault.chmod(0o700)
    (vault / ".vault_key").chmod(0o600)
    (vault / "vault.json.enc").chmod(0o600)
    assert stat.S_IMODE(vault.stat().st_mode) == 0o700
    assert source_module._validate_vault_security(vault) is None

    (vault / "vault.json.enc").chmod(0o640)
    assert "group or world" in source_module._validate_vault_security(vault)


def test_initialized_vault_rejects_linked_key(source_module, tmp_path):
    vault = _initialized_vault(tmp_path)
    target = tmp_path / "outside-key"
    target.write_text("fixture-key", encoding="utf-8")
    (vault / ".vault_key").unlink()
    try:
        (vault / ".vault_key").symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")

    assert "links" in source_module._validate_vault_security(vault)


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

    values = [
        source.fetch(cfg, home).secrets["PROFILE_API_KEY"]
        for home in (home_a, home_b, home_a)
    ]

    assert values == ["secret-for-profile-a", "secret-for-profile-b", "secret-for-profile-a"]


def test_orchestrator_registers_exact_redaction_per_profile(source, tmp_path):
    from agent.redact import (
        clear_vault_redaction_values,
        redact_sensitive_text,
    )
    from agent.secret_sources import registry
    from hermes_constants import (
        hermes_home_key,
        reset_hermes_home_override,
        set_hermes_home_override,
    )

    helper = tmp_path / "fake_kista.py"
    helper.write_text(
        "import json, os\n"
        "from pathlib import Path\n"
        "profile = Path(os.environ['KISTA_DIR']).parent.name\n"
        "print(json.dumps({'key': 'opaque-canary-for-' + profile}))\n",
        encoding="utf-8",
    )
    home_a = tmp_path / "redact-a"
    home_b = tmp_path / "redact-b"
    home_a.mkdir()
    home_b.mkdir()
    scope_a = hermes_home_key(home_a)
    scope_b = hermes_home_key(home_b)
    cfg = {
        "kista": {
            "enabled": True,
            "binary_path": str(helper),
            "env": {"PROFILE_PASSWORD": "kista://service/key"},
        }
    }
    registry._reset_registry_for_tests()
    assert registry.register_source(source, scope=scope_a)
    assert registry.register_source(source, scope=scope_b)

    try:
        values = []
        for home in (home_a, home_b, home_a):
            environment = {}
            report = registry.apply_all(cfg, home, environ=environment)
            assert report.sources[0].result.ok
            values.append(environment["PROFILE_PASSWORD"])

        secret_a, secret_b, repeated_a = values
        assert repeated_a == secret_a
        token = set_hermes_home_override(home_a)
        try:
            assert redact_sensitive_text(secret_a) != secret_a
            assert redact_sensitive_text(secret_b) == secret_b
        finally:
            reset_hermes_home_override(token)
        token = set_hermes_home_override(home_b)
        try:
            assert redact_sensitive_text(secret_b) != secret_b
            assert redact_sensitive_text(secret_a) == secret_a
        finally:
            reset_hermes_home_override(token)
    finally:
        clear_vault_redaction_values(scope=scope_a)
        clear_vault_redaction_values(scope=scope_b)
        registry._reset_registry_for_tests()


def test_real_plugin_discovery_registers_and_applies_kista(tmp_path, monkeypatch):
    from agent.redact import (
        clear_vault_redaction_values,
        redact_registered_vault_values,
    )
    from agent.secret_sources import registry
    from hermes_constants import hermes_home_key
    from hermes_cli.plugins import PluginManager

    home = tmp_path / "home"
    home.mkdir()
    helper = tmp_path / "fake_kista.py"
    canary = "KISTA-DISCOVERY-CANARY"
    helper.write_text(
        f"import json\nprint(json.dumps({{'key': {canary!r}}}))\n", encoding="utf-8"
    )
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
        assert environment["HERMES_TEST_KISTA_API_KEY"] == canary
        assert report.provenance["HERMES_TEST_KISTA_API_KEY"].source == "kista"
        assert redact_registered_vault_values(canary, scope=home) != canary
    finally:
        clear_vault_redaction_values(scope=home)
        os.environ.pop("HERMES_TEST_KISTA_API_KEY", None)
        registry._reset_registry_for_tests()
