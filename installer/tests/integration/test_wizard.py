"""Integration tests for `askill wizard` — the interactive multi-select installer.

Driven headlessly by monkeypatching questionary's `checkbox`/`select` prompts to
return canned selections. Covers: single/multi install, no-op on empty selection,
that a multi-skill install downloads the archive ONCE, and that a per-skill failure
doesn't lose the skills that already succeeded.
"""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from askill.cli import app
from askill.commands import wizard
from askill.core.checksum import skill_checksum

runner = CliRunner()

REPO = "https://github.com/example/agent-skills"
COMMIT = "deadbeef"
ARCHIVE_URL = f"{REPO}/archive/{COMMIT}.tar.gz"
DESC = "A valid skill description used across wizard integration tests."
BAD_CHECKSUM = "sha256:" + "0" * 64


class _Answer:
    """Stand-in for a questionary prompt object whose .ask() returns a canned value."""

    def __init__(self, value: object) -> None:
        self._value = value

    def ask(self) -> object:
        return self._value


def _build_archive(tmp_path: Path, names: list[str]) -> tuple[bytes, dict[str, str]]:
    """Build one gzipped repo tarball holding skills/<name>/ for each name."""
    prefix = "agent-skills-deadbeef"
    base = tmp_path / "build" / prefix / "skills"
    checksums: dict[str, str] = {}
    for name in names:
        skill_dir = base / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(f"hello {name}")
        checksums[name] = skill_checksum(skill_dir)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        tar.add(tmp_path / "build" / prefix, arcname=prefix)
    return buffer.getvalue(), checksums


def _registry_file(tmp_path: Path, skills: list[tuple[str, str]]) -> str:
    payload = {
        "schema_version": "1.0",
        "library": {
            "name": "askill-library",
            "repo": REPO,
            "generated_at": "2026-05-25T10:00:00Z",
            "commit": COMMIT,
        },
        "skills": [
            {
                "name": name,
                "version": "0.1.0",
                "description": DESC,
                "path": f"skills/{name}",
                "entry": "SKILL.md",
                "tags": [],
                "compatible_agents": ["claude-code"],
                "dependencies": [],
                "checksum": checksum,
            }
            for name, checksum in skills
        ],
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(payload))
    return str(path)


def _pick(monkeypatch: pytest.MonkeyPatch, names: list[str], scope: str) -> None:
    monkeypatch.setattr(wizard.questionary, "checkbox", lambda *a, **k: _Answer(names))
    monkeypatch.setattr(wizard.questionary, "select", lambda *a, **k: _Answer(scope))


def _state(tmp_path: Path) -> dict:
    return json.loads((tmp_path / ".claude" / "skills" / ".installed.json").read_text())


def test_wizard_installs_checked_skill(
    tmp_path: Path, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    archive, checks = _build_archive(tmp_path, ["learning-mode"])
    reg = _registry_file(tmp_path, [("learning-mode", checks["learning-mode"])])
    httpx_mock.add_response(url=ARCHIVE_URL, content=archive)
    _pick(monkeypatch, ["learning-mode"], "user")

    result = runner.invoke(app, ["wizard", "--registry", reg])

    assert result.exit_code == 0, result.output
    assert (
        tmp_path / ".claude" / "skills" / "learning-mode" / "SKILL.md"
    ).read_text() == "hello learning-mode"


def test_wizard_no_selection_is_noop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    _, checks = _build_archive(tmp_path, ["learning-mode"])
    reg = _registry_file(tmp_path, [("learning-mode", checks["learning-mode"])])
    _pick(monkeypatch, [], "user")

    result = runner.invoke(app, ["wizard", "--registry", reg])

    assert result.exit_code == 0
    assert not (tmp_path / ".claude" / "skills" / "learning-mode").exists()


def test_wizard_downloads_archive_once_for_multiple_skills(
    tmp_path: Path, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two skills, ONE mocked archive response: a second download would 404 in the
    mock, so passing proves the archive is fetched once and reused."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    archive, checks = _build_archive(tmp_path, ["learning-mode", "toxic-senior-reviewer"])
    reg = _registry_file(
        tmp_path,
        [
            ("learning-mode", checks["learning-mode"]),
            ("toxic-senior-reviewer", checks["toxic-senior-reviewer"]),
        ],
    )
    httpx_mock.add_response(url=ARCHIVE_URL, content=archive)  # exactly one
    _pick(monkeypatch, ["learning-mode", "toxic-senior-reviewer"], "user")

    result = runner.invoke(app, ["wizard", "--registry", reg])

    assert result.exit_code == 0, result.output
    skills = tmp_path / ".claude" / "skills"
    assert (skills / "learning-mode" / "SKILL.md").exists()
    assert (skills / "toxic-senior-reviewer" / "SKILL.md").exists()


def test_wizard_partial_failure_keeps_successful_state(
    tmp_path: Path, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If one skill fails (bad checksum), the one that succeeded is still recorded."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    archive, checks = _build_archive(tmp_path, ["learning-mode", "toxic-senior-reviewer"])
    reg = _registry_file(
        tmp_path,
        [("learning-mode", checks["learning-mode"]), ("toxic-senior-reviewer", BAD_CHECKSUM)],
    )
    httpx_mock.add_response(url=ARCHIVE_URL, content=archive)
    _pick(monkeypatch, ["learning-mode", "toxic-senior-reviewer"], "user")

    result = runner.invoke(app, ["wizard", "--registry", reg])

    # A checksum mismatch is a system error: the wizard must surface that exit
    # code (2), not collapse every per-skill failure to a generic 1, so retry
    # automation can still tell transient/system failures from user errors.
    assert result.exit_code == 2
    state = _state(tmp_path)
    assert "learning-mode" in state["skills"]  # the good one survived
    assert "toxic-senior-reviewer" not in state["skills"]
