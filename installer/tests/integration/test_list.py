"""Integration tests for `askill list` via Typer's CliRunner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from askill.cli import app

runner = CliRunner()

SHA = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_list_shows_all_skills(registry_file: str) -> None:
    result = runner.invoke(app, ["list", "--registry", registry_file])
    assert result.exit_code == 0
    assert "learning-mode" in result.output
    assert "article-translator" in result.output


def test_list_json(registry_file: str) -> None:
    result = runner.invoke(app, ["list", "--registry", registry_file, "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert {row["name"] for row in data} == {"learning-mode", "article-translator"}


def test_list_filter_by_tag(registry_file: str) -> None:
    result = runner.invoke(
        app, ["list", "--registry", registry_file, "--tag", "translation", "--json"]
    )
    assert result.exit_code == 0
    assert [row["name"] for row in json.loads(result.output)] == ["article-translator"]


def test_list_unknown_tag_is_empty(registry_file: str) -> None:
    result = runner.invoke(app, ["list", "--registry", registry_file, "--tag", "nope", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == []


def test_list_installed_user_scope(
    registry_file: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    skills_dir = tmp_path / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    state = {
        "schema_version": "1.0",
        "scope": "user",
        "registry_url": "https://example.com/registry.json",
        "skills": {
            "learning-mode": {
                "version": "0.1.0",
                "installed_at": "2026-05-21T10:00:00Z",
                "source_commit": "abc123",
                "checksum": SHA,
                "path": str(skills_dir / "learning-mode"),
            }
        },
    }
    (skills_dir / ".installed.json").write_text(json.dumps(state))
    result = runner.invoke(
        app,
        ["list", "--registry", registry_file, "--installed", "--scope", "user", "--json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert [row["name"] for row in data] == ["learning-mode"]
    assert data[0]["installed"] == "0.1.0"


def test_list_missing_registry_exit_2(tmp_path: Path) -> None:
    result = runner.invoke(app, ["list", "--registry", str(tmp_path / "nope.json")])
    assert result.exit_code == 2
