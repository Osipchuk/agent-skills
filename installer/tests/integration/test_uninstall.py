"""Integration tests for `askill uninstall`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from askill.cli import app

runner = CliRunner()

SHA = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def _install_state(tmp_path: Path, name: str = "learning-mode") -> Path:
    """Seed a user-scope installed.json + skill folder under home=tmp_path."""
    skills_dir = tmp_path / ".claude" / "skills"
    target = skills_dir / name
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("hello")
    state = {
        "schema_version": "1.0",
        "scope": "user",
        "registry_url": "https://example.com/registry.json",
        "skills": {
            name: {
                "version": "0.1.0",
                "installed_at": "2026-05-21T10:00:00Z",
                "source_commit": "abc123",
                "checksum": SHA,
                "path": str(target),
            }
        },
    }
    (skills_dir / ".installed.json").write_text(json.dumps(state))
    return target


def _read_state(tmp_path: Path) -> dict:
    return json.loads((tmp_path / ".claude" / "skills" / ".installed.json").read_text())


def test_uninstall_removes_skill(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    target = _install_state(tmp_path)
    result = runner.invoke(app, ["uninstall", "learning-mode", "--scope", "user", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["status"] == "uninstalled"
    assert not target.exists()
    assert "learning-mode" not in _read_state(tmp_path)["skills"]


def test_uninstall_not_installed_exit_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    result = runner.invoke(app, ["uninstall", "learning-mode", "--scope", "user"])
    assert result.exit_code == 1


def test_uninstall_dry_run_keeps_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    target = _install_state(tmp_path)
    result = runner.invoke(
        app, ["uninstall", "learning-mode", "--scope", "user", "--dry-run", "--json"]
    )
    assert result.exit_code == 0
    assert json.loads(result.output)["status"] == "would-uninstall"
    assert target.exists()
    assert "learning-mode" in _read_state(tmp_path)["skills"]
