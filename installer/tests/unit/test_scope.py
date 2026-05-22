"""Tests for askill.core.scope — install-scope resolution (spec §9).

This file is the SPEC for core/scope.py. Implement THREE pure functions with
exactly these signatures:

    def resolve_scope(
        explicit: str | None,
        cwd: Path,
        env: Mapping[str, str],
    ) -> Literal["user", "project"]: ...

    def target_dir(scope: str, name: str, project_root: Path | None = None) -> Path: ...

    def installed_json_path(scope: str, project_root: Path | None = None) -> Path: ...

The key design idea (spec §9.1): the world is PASSED IN (cwd, env), never read
from globals — that's what keeps these pure and testable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from askill.core.scope import (
    find_project_root,
    installed_json_path,
    resolve_scope,
    target_dir,
)

PROJECT_ENV = "CLAUDE_CODE_PROJECT_ROOT"


# --------------------------------------------------------------------------- #
# resolve_scope — precedence order (§9.1):
#   1. explicit flag (validated)  2. cwd/ancestor has .claude/  3. env  4. user
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("explicit", ["user", "project"])
def test_explicit_scope_is_returned(explicit: str, tmp_path: Path) -> None:
    assert resolve_scope(explicit, tmp_path, {}) == explicit


def test_explicit_wins_over_cwd_and_env(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()  # would otherwise force "project"
    env = {PROJECT_ENV: str(tmp_path)}
    assert resolve_scope("user", tmp_path, env) == "user"


@pytest.mark.parametrize("explicit", ["global", "system", "", "User", "PROJECT"])
def test_invalid_explicit_scope_raises(explicit: str, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        resolve_scope(explicit, tmp_path, {})


def test_cwd_with_dot_claude_is_project(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    assert resolve_scope(None, tmp_path, {}) == "project"


def test_ancestor_with_dot_claude_is_project(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    deep = tmp_path / "src" / "pkg" / "sub"
    deep.mkdir(parents=True)
    assert resolve_scope(None, deep, {}) == "project"


def test_env_var_forces_project(tmp_path: Path) -> None:
    # no .claude anywhere under tmp_path, but the project-root env var is set
    assert resolve_scope(None, tmp_path, {PROJECT_ENV: str(tmp_path)}) == "project"


def test_defaults_to_user(tmp_path: Path) -> None:
    assert resolve_scope(None, tmp_path, {}) == "user"


def test_dot_claude_must_be_a_directory_not_a_file(tmp_path: Path) -> None:
    # a regular file named .claude should NOT count as a project marker
    (tmp_path / ".claude").write_text("not a dir")
    assert resolve_scope(None, tmp_path, {}) == "user"


# --------------------------------------------------------------------------- #
# target_dir — where a skill's files live (§9.2)
# --------------------------------------------------------------------------- #


def test_target_dir_user(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert target_dir("user", "pdf-extractor") == tmp_path / ".claude" / "skills" / "pdf-extractor"


def test_target_dir_project(tmp_path: Path) -> None:
    got = target_dir("project", "pdf-extractor", project_root=tmp_path)
    assert got == tmp_path / ".claude" / "skills" / "pdf-extractor"


def test_target_dir_project_without_root_raises() -> None:
    with pytest.raises(ValueError):
        target_dir("project", "pdf-extractor")


# --------------------------------------------------------------------------- #
# installed_json_path — per-scope state file (§9.3). Filename is `.installed.json`
# (the §9.3 path table is authoritative over the §10.1 prose, which omits the dot).
# --------------------------------------------------------------------------- #


def test_installed_json_path_user(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert installed_json_path("user") == tmp_path / ".claude" / "skills" / ".installed.json"


def test_installed_json_path_project(tmp_path: Path) -> None:
    got = installed_json_path("project", project_root=tmp_path)
    assert got == tmp_path / ".claude" / "skills" / ".installed.json"


def test_installed_json_path_project_without_root_raises() -> None:
    with pytest.raises(ValueError):
        installed_json_path("project")


# --------------------------------------------------------------------------- #
# find_project_root — used by --installed for project scope
# --------------------------------------------------------------------------- #


def test_find_project_root_via_dot_claude(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    assert find_project_root(deep, {}) == tmp_path


def test_find_project_root_via_env(tmp_path: Path) -> None:
    assert find_project_root(tmp_path, {PROJECT_ENV: str(tmp_path)}) == tmp_path


def test_find_project_root_none(tmp_path: Path) -> None:
    assert find_project_root(tmp_path, {}) is None
