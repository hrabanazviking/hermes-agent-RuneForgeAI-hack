"""Read explicitly mapped credentials from the official Kista CLI."""

from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from agent.secret_sources.base import (
    ErrorKind,
    FetchResult,
    SecretSource,
    coerce_float,
    is_valid_env_name,
    run_secret_cli,
)

_REFERENCE_RE = re.compile(
    r"^kista://(?P<service>[a-z0-9][a-z0-9_.-]{0,127})/"
    r"(?P<field>[a-z_][a-z0-9_]{0,63})$"
)
_MAX_OUTPUT_BYTES = 256 * 1024
_DEFAULT_VAULT_DIR = "credentials"
_DEFAULT_CLI_TIMEOUT_SECONDS = 30.0
_REQUIRED_VAULT_FILES = (".vault_key", "vault.json.enc")
_SDDL_ACE_RE = re.compile(r"\(([^()]*)\)")
_WINDOWS_TRUSTED_ACL_PRINCIPALS = frozenset(
    {
        "SY",  # LocalSystem
        "BA",  # Built-in Administrators
        "S-1-5-18",
        "S-1-5-32-544",
    }
)


def _validate_references(
    references: Optional[Dict[str, object]],
) -> Tuple[Dict[str, Tuple[str, str]], List[str]]:
    """Return valid ENV_VAR -> (service, field) bindings without echoing refs."""
    valid: Dict[str, Tuple[str, str]] = {}
    warnings: List[str] = []
    for name, reference in (references or {}).items():
        if not isinstance(name, str) or not is_valid_env_name(name):
            warnings.append("Skipping an invalid environment-variable name")
            continue
        if not isinstance(reference, str):
            warnings.append(f"Skipping {name}: Kista reference must be a string")
            continue
        match = _REFERENCE_RE.fullmatch(reference.strip())
        if match is None:
            warnings.append(f"Skipping {name}: invalid kista:// service/field reference")
            continue
        valid[name] = (match.group("service"), match.group("field"))
    return valid, warnings


def _resolve_vault_dir(cfg: dict, home_path: Path) -> Optional[Path]:
    """Resolve a non-escaping profile-local vault directory."""
    raw = cfg.get("vault_dir", _DEFAULT_VAULT_DIR)
    if not isinstance(raw, str) or not raw.strip() or "\x00" in raw:
        return None
    relative = Path(raw.strip())
    if relative.is_absolute():
        return None
    try:
        home = home_path.expanduser().resolve()
        candidate = Path(os.path.abspath(home / relative))
        candidate.relative_to(home)
        candidate.resolve().relative_to(home)
    except (OSError, RuntimeError, ValueError):
        return None
    return candidate


def _is_link_or_reparse(path: Path) -> bool:
    """Reject POSIX links and Windows junctions/reparse points."""
    try:
        info = path.lstat()
    except OSError:
        return True
    attributes = getattr(info, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(info.st_mode) or bool(attributes & reparse)


def _windows_current_sid() -> Optional[str]:
    executable = shutil.which("whoami")
    if executable is None:
        return None
    try:
        proc = subprocess.run(
            [executable, "/user", "/fo", "csv", "/nh"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        row = next(csv.reader(io.StringIO(proc.stdout)))
    except (OSError, StopIteration, subprocess.SubprocessError):
        return None
    if proc.returncode != 0 or len(row) < 2 or not row[1].startswith("S-1-"):
        return None
    return row[1]


def _windows_acl_sddl(path: Path) -> Optional[str]:
    """Read the DACL in SID form so localized account names are irrelevant."""
    executable = shutil.which("icacls")
    if executable is None:
        return None
    try:
        with tempfile.TemporaryDirectory(prefix="hermes-kista-acl-") as temp_dir:
            output = Path(temp_dir) / "acl.txt"
            proc = subprocess.run(
                [executable, str(path), "/save", str(output), "/Q"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=5,
                check=False,
            )
            if proc.returncode != 0 or not output.is_file():
                return None
            return output.read_text(encoding="utf-16")
    except (OSError, UnicodeError, subprocess.SubprocessError):
        return None


def _sddl_is_private(sddl: str, current_sid: str) -> bool:
    """Allow grants only to the current user, LocalSystem, or Administrators."""
    if any(marker in sddl for marker in ("(XA;", "(ZA;", "(XU;")):
        # Conditional allow ACEs have a nested expression that this deliberately
        # small parser cannot safely attribute. Refuse rather than guess.
        return False
    trusted = _WINDOWS_TRUSTED_ACL_PRINCIPALS | {current_sid}
    current_user_granted = False
    for raw_ace in _SDDL_ACE_RE.findall(sddl):
        fields = raw_ace.split(";")
        if len(fields) < 6 or fields[0] not in {"A", "OA"}:
            continue
        principal = fields[5]
        if principal not in trusted:
            return False
        if principal == current_sid:
            current_user_granted = True
    return current_user_granted


def _windows_acl_is_private(path: Path, current_sid: str) -> bool:
    sddl = _windows_acl_sddl(path)
    return bool(sddl and _sddl_is_private(sddl, current_sid))


def _uses_windows_acls() -> bool:
    return sys.platform == "win32"


def _validate_vault_security(vault_dir: Path) -> Optional[str]:
    """Return a generic refusal reason when an initialized vault is unsafe."""
    if not vault_dir.exists():
        # Let Kista retain ownership of the normal uninitialized-vault error.
        return None
    if _is_link_or_reparse(vault_dir) or not vault_dir.is_dir():
        return "Kista vault storage must be a real profile-local directory."

    required = [vault_dir / name for name in _REQUIRED_VAULT_FILES]
    if any(
        not path.exists()
        or _is_link_or_reparse(path)
        or not path.is_file()
        for path in required
    ):
        return "Kista vault storage is incomplete or uses unsupported links."

    if _uses_windows_acls():
        current_sid = _windows_current_sid()
        if current_sid is None or any(
            not _windows_acl_is_private(path, current_sid)
            for path in (vault_dir, *required)
        ):
            return (
                "Kista vault ACLs permit access outside the current user "
                "and system administrators."
            )
        return None

    owner = getattr(os, "geteuid", lambda: None)()
    for path in (vault_dir, *required):
        try:
            info = path.stat()
        except OSError:
            return "Kista vault permissions could not be verified."
        if owner is not None and info.st_uid != owner:
            return "Kista vault storage is not owned by the current user."
        if stat.S_IMODE(info.st_mode) & 0o077:
            return "Kista vault storage permits group or world access."
    return None


def _resolve_command(binary_path: str) -> Tuple[Optional[List[str]], Optional[Path]]:
    """Resolve the official entry point, with .py support for source checkouts."""
    configured = binary_path.strip()
    if configured:
        expanded = Path(configured).expanduser()
        if expanded.suffix.lower() == ".py":
            try:
                script = expanded.resolve()
            except OSError:
                return None, None
            if not script.is_file():
                return None, None
            return [sys.executable, str(script)], script

        if expanded.is_absolute() or expanded.parent != Path("."):
            try:
                resolved = expanded.resolve()
            except OSError:
                return None, None
            if not resolved.is_file() or not os.access(resolved, os.X_OK):
                return None, None
            return [str(resolved)], resolved

    found = shutil.which(configured or "kista")
    if not found:
        return None, None
    resolved = Path(found).resolve()
    return [str(resolved)], resolved


def _failure_kind(output: str) -> ErrorKind:
    lowered = output.lower()
    if "no entry found" in lowered:
        return ErrorKind.REF_INVALID
    if any(
        token in lowered
        for token in ("not initialized", "vault key not found", "run 'kista init'")
    ):
        return ErrorKind.NOT_CONFIGURED
    if any(token in lowered for token in ("invalid token", "decrypt", "authentication")):
        return ErrorKind.AUTH_FAILED
    return ErrorKind.INTERNAL


def _read_entry(
    command: Sequence[str], service: str, vault_dir: Path, timeout: float
) -> Tuple[Optional[dict], Optional[ErrorKind]]:
    """Read one Kista entry; returned failures carry no CLI output or reference."""
    try:
        proc = run_secret_cli(
            [*command, "get", "--", service],
            extra_env={"KISTA_DIR": str(vault_dir), "PYTHONUTF8": "1"},
            timeout=timeout,
        )
    except RuntimeError as exc:
        lowered = str(exc).lower()
        if "timed out" in lowered:
            kind = ErrorKind.TIMEOUT
        elif "failed to invoke" in lowered:
            kind = ErrorKind.BINARY_MISSING
        else:
            kind = ErrorKind.INTERNAL
        return None, kind

    combined = f"{proc.stdout}\n{proc.stderr}"
    if proc.returncode != 0:
        return None, _failure_kind(combined)
    if len(proc.stdout.encode("utf-8", errors="replace")) > _MAX_OUTPUT_BYTES:
        return None, ErrorKind.INTERNAL
    try:
        payload = json.loads(proc.stdout)
    except (TypeError, json.JSONDecodeError):
        return None, ErrorKind.INTERNAL
    if not isinstance(payload, dict):
        return None, ErrorKind.INTERNAL
    return payload, None


class KistaSource(SecretSource):
    """Mapped, read-only Kista source using explicit top-level entry fields."""

    name = "kista"
    label = "Kista"
    shape = "mapped"
    scheme = "kista"
    override_existing_default = False

    def config_schema(self) -> dict:
        return {
            "enabled": {"description": "Master switch", "default": False},
            "env": {
                "description": "Map of ENV_VAR to kista://service/field reference",
                "default": {},
            },
            "binary_path": {
                "description": "Pinned Kista executable or official credstore.py checkout",
                "default": "",
            },
            "vault_dir": {
                "description": "Kista vault directory relative to the active Hermes profile",
                "default": _DEFAULT_VAULT_DIR,
            },
            "cli_timeout_seconds": {
                "description": "Per-entry Kista CLI timeout",
                "default": _DEFAULT_CLI_TIMEOUT_SECONDS,
            },
            "override_existing": {
                "description": "Resolved values overwrite existing environment values",
                "default": False,
            },
        }

    def remediation(self, kind: Optional[ErrorKind], cfg: dict) -> str:
        hints = {
            ErrorKind.NOT_CONFIGURED: (
                "Initialize the active profile's Kista vault with `kista init` and ensure "
                "its directory, key, and ciphertext are private to the current user."
            ),
            ErrorKind.BINARY_MISSING: (
                "Install Kista or set secrets.kista.binary_path to its executable."
            ),
            ErrorKind.REF_INVALID: "Check the configured kista://service/field bindings.",
            ErrorKind.AUTH_FAILED: "Repair or restore the active profile's encrypted Kista vault.",
            ErrorKind.TIMEOUT: "Raise secrets.kista.cli_timeout_seconds if Kista remains healthy.",
        }
        return hints.get(kind, "")

    def fetch(self, cfg: dict, home_path: Path) -> FetchResult:
        cfg = cfg if isinstance(cfg, dict) else {}
        result = FetchResult()
        env_map = cfg.get("env")
        valid, warnings = _validate_references(env_map if isinstance(env_map, dict) else None)
        result.warnings.extend(warnings)
        if not valid:
            kind = ErrorKind.REF_INVALID if warnings else ErrorKind.NOT_CONFIGURED
            message = (
                "No valid Kista credential bindings were configured."
                if warnings
                else "secrets.kista.env is empty; add ENV_VAR: kista://service/field bindings."
            )
            return result.fail(message, kind)

        vault_dir = _resolve_vault_dir(cfg, home_path)
        if vault_dir is None:
            return result.fail(
                "secrets.kista.vault_dir must stay within the active Hermes profile.",
                ErrorKind.NOT_CONFIGURED,
            )
        permission_error = _validate_vault_security(vault_dir)
        if permission_error is not None:
            return result.fail(permission_error, ErrorKind.NOT_CONFIGURED)

        command, binary = _resolve_command(str(cfg.get("binary_path") or ""))
        result.binary_path = binary
        if command is None:
            return result.fail(
                "The Kista CLI was not found; install Kista or configure binary_path.",
                ErrorKind.BINARY_MISSING,
            )

        timeout = coerce_float(
            cfg.get("cli_timeout_seconds", _DEFAULT_CLI_TIMEOUT_SECONDS),
            _DEFAULT_CLI_TIMEOUT_SECONDS,
        )
        if timeout <= 0:
            timeout = _DEFAULT_CLI_TIMEOUT_SECONDS
        timeout = min(timeout, 60.0)

        entries: Dict[str, dict] = {}
        failures: List[ErrorKind] = []
        for service in sorted({service for service, _field in valid.values()}):
            entry, failure = _read_entry(command, service, vault_dir, timeout)
            if failure is not None:
                failures.append(failure)
            elif entry is not None:
                entries[service] = entry

        for env_name, (service, field) in valid.items():
            entry = entries.get(service)
            if entry is None:
                result.warnings.append(f"Kista could not resolve {env_name}")
                continue
            value = entry.get(field)
            if not isinstance(value, str) or not value:
                result.warnings.append(f"Kista returned no usable value for {env_name}")
                failures.append(ErrorKind.EMPTY_VALUE)
                continue
            result.secrets[env_name] = value

        if result.secrets:
            return result
        kind = failures[0] if failures else ErrorKind.EMPTY_VALUE
        return result.fail("Kista did not resolve any configured credentials.", kind)
