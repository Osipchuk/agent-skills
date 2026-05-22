"""Integration tests for `askill info` via Typer's CliRunner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from askill.cli import app

runner = CliRunner()


def test_info_found(registry_file: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    result = runner.invoke(
        app, ["info", "learning-mode", "--registry", registry_file, "--scope", "user"]
    )
    assert result.exit_code == 0
    assert "learning-mode" in result.output
    assert "0.1.0" in result.output


def test_info_json_not_installed(
    registry_file: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    result = runner.invoke(
        app,
        ["info", "learning-mode", "--registry", registry_file, "--scope", "user", "--json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["name"] == "learning-mode"
    assert data["installed"] is None


def test_info_unknown_skill_exit_1(registry_file: str) -> None:
    result = runner.invoke(app, ["info", "does-not-exist", "--registry", registry_file])
    assert result.exit_code == 1
