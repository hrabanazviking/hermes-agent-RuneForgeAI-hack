"""W02/U2: the release-age gate is scoped to registry sources only.

``[tool.uv] exclude-newer`` dates index packages. A package bound to a local
path by ``[tool.uv.sources]`` (the editable ravens) has no publish time by
construction, so PM's lock path exempts exactly those names — derived from
the project's own sources table, never hand-maintained — and an undated
diagnostic naming one reads as a local-source fault, not an index fault.
Registry packages keep the gate and the index hint exactly as before.
"""

from __future__ import annotations

from pathlib import Path

from pm.environment import (
    PythonEnvironment,
    classify_uv_failure,
    local_source_packages,
)
from pm.package import InstallError


def _project(tmp_path: Path, sources: str) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n\n[tool.uv]\nexclude-newer = "3 days"\n\n'
        f"[tool.uv.sources]\n{sources}\n",
        encoding="utf-8",
    )
    return tmp_path


def test_local_source_packages_derives_only_local_entries(tmp_path):
    root = _project(
        tmp_path,
        'muninn = { path = "../ravens/muninn", editable = true }\n'
        'huginn = { path = "../ravens/huginn", editable = true }\n'
        'member = { workspace = true }\n'
        'gitpkg = { git = "https://example.invalid/repo", rev = "abc" }\n'
        'urlpkg = { url = "https://example.invalid/pkg.whl" }\n'
        'idxpkg = { index = "internal" }\n',
    )
    assert local_source_packages(root) == ["huginn", "member", "muninn"]


def test_local_source_packages_normalizes_names(tmp_path):
    root = _project(tmp_path, 'My_Pkg = { path = "../my_pkg", editable = true }\n')
    assert local_source_packages(root) == ["my-pkg"]


def test_local_source_packages_missing_or_malformed(tmp_path):
    assert local_source_packages(tmp_path) == []
    (tmp_path / "pyproject.toml").write_text("not [valid toml", encoding="utf-8")
    assert local_source_packages(tmp_path) == []


def test_real_fork_pyproject_binds_exactly_the_ravens():
    """The fork's own table yields muninn+huginn and nothing else."""
    from pm.paths import repo_root

    assert local_source_packages(repo_root()) == ["huginn", "muninn"]


def _environment(tmp_path: Path) -> PythonEnvironment:
    return PythonEnvironment(
        uv=tmp_path / "uv",
        python=tmp_path / "python",
        destination=tmp_path / "venv",
        cache=tmp_path / "cache",
        env={},
    )


def test_lock_command_exempts_local_sources_only(tmp_path):
    root = _project(
        tmp_path,
        'muninn = { path = "../ravens/muninn", editable = true }\n'
        'huginn = { path = "../ravens/huginn", editable = true }\n',
    )
    env = _environment(tmp_path)
    command = env._lock_command(root)
    assert command[:3] == ["lock", "--python", str(tmp_path / "python")]
    assert command.count("--exclude-newer-package") == 2
    assert "muninn=false" in command and "huginn=false" in command
    # The CA-trust exemption in pyproject is PM law, not this list: the lock
    # command must not grow a certifi exemption of its own.
    assert "certifi=false" not in command
    check = env._lock_command(root, check=True)
    assert check[1] == "--check" and "muninn=false" in check
    upgrade = env._lock_command(root, upgrade=True)
    assert "--upgrade" in upgrade and "huginn=false" in upgrade


_SEEDED_LOCAL = (
    "  x No solution found when resolving dependencies:\n"
    "  Because muninn==1.0.0 has no publish time and hermes-agent[volmarr-ravens] "
    "depends on muninn==1.0.0, we can conclude that hermes-agent's requirements "
    "are unsatisfiable."
)
_SEEDED_REGISTRY = (
    "  x No solution found when resolving dependencies:\n"
    "  Because resvg-py==0.4.0 has no publish time and hermes-agent depends on "
    "resvg-py==0.4.0, we can conclude that hermes-agent's requirements are unsatisfiable."
)


def test_undated_local_package_is_a_local_fault_not_an_index_fault():
    err = classify_uv_failure("lock", 1, _SEEDED_LOCAL, local_packages=["huginn", "muninn"])
    assert isinstance(err, InstallError)
    assert "local path" in err.remedy and "[tool.uv.sources]" in err.remedy
    assert "pypi.org" not in err.remedy


def test_undated_registry_package_keeps_the_index_hint():
    err = classify_uv_failure("lock", 1, _SEEDED_REGISTRY, local_packages=["huginn", "muninn"])
    assert "upload times" in err.remedy and "pypi.org" in err.remedy


def test_undated_mixed_failure_keeps_the_index_hint():
    mixed = _SEEDED_LOCAL + "\n" + _SEEDED_REGISTRY
    err = classify_uv_failure("lock", 1, mixed, local_packages=["huginn", "muninn"])
    assert "upload times" in err.remedy and "pypi.org" in err.remedy


def test_undated_without_local_context_is_unchanged():
    """Callers that cannot name the project's locals keep the old verdict."""
    err = classify_uv_failure("lock", 1, _SEEDED_LOCAL)
    assert "upload times" in err.remedy and "pypi.org" in err.remedy
