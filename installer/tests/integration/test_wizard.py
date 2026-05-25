"""Integration tests for `askill wizard` — the interactive multi-select installer.

The wizard is a thin TTY layer over the same install core. Here we drive it
headlessly by monkeypatching questionary's `checkbox`/`select` prompts to return
canned selections, and assert the chosen skills are installed.
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


class _Answer:
    """Stand-in for a questionary prompt object whose .ask() returns a canned value."""

    def __init__(self, value: object) -> None:
        self._value = value

    def ask(self) -> object:
        return self._value


def _build_archive(tmp_path: Path, name: str) -> tuple[bytes, str]:
    prefix = "agent-skills-deadbeef"
    skill_dir = tmp_path / "build" / prefix / "skills" / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("hello")
    checksum = skill_checksum(skill_dir)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        tar.add(tmp_path / "build" / prefix, arcname=prefix)
    return buffer.getvalue(), checksum


def _registry_file(tmp_path: Path, name: str, checksum: str) -> str:
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
        ],
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(payload))
    return str(path)


def test_wizard_installs_checked_skills(
    tmp_path: Path, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    archive, checksum = _build_archive(tmp_path, "learning-mode")
    reg = _registry_file(tmp_path, "learning-mode", checksum)
    httpx_mock.add_response(url=ARCHIVE_URL, content=archive)
    monkeypatch.setattr(wizard.questionary, "checkbox", lambda *a, **k: _Answer(["learning-mode"]))
    monkeypatch.setattr(wizard.questionary, "select", lambda *a, **k: _Answer("user"))

    result = runner.invoke(app, ["wizard", "--registry", reg])

    assert result.exit_code == 0, result.output
    assert (tmp_path / ".claude" / "skills" / "learning-mode" / "SKILL.md").read_text() == "hello"


def test_wizard_no_selection_is_noop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    _, checksum = _build_archive(tmp_path, "learning-mode")
    reg = _registry_file(tmp_path, "learning-mode", checksum)
    monkeypatch.setattr(wizard.questionary, "checkbox", lambda *a, **k: _Answer([]))
    monkeypatch.setattr(wizard.questionary, "select", lambda *a, **k: _Answer("user"))

    result = runner.invoke(app, ["wizard", "--registry", reg])

    assert result.exit_code == 0
    assert not (tmp_path / ".claude" / "skills" / "learning-mode").exists()
