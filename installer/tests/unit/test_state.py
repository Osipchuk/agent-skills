"""Tests for askill.core.state — read-only installed.json loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from askill.core.models import InstalledState
from askill.core.state import load_state, load_state_from_path, save_state, write_state
from askill.utils.errors import StateError

SHA = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def _installed_payload() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "scope": "user",
        "registry_url": "https://example.com/registry.json",
        "skills": {
            "learning-mode": {
                "version": "0.1.0",
                "installed_at": "2026-05-21T10:00:00Z",
                "source_commit": "abc123",
                "checksum": SHA,
                "path": "/home/user/.claude/skills/learning-mode",
            }
        },
    }


def test_absent_file_returns_none(tmp_path: Path) -> None:
    assert load_state_from_path(tmp_path / ".installed.json") is None


def test_valid_state_parses(tmp_path: Path) -> None:
    path = tmp_path / ".installed.json"
    path.write_text(json.dumps(_installed_payload()))
    state = load_state_from_path(path)
    assert isinstance(state, InstalledState)
    assert "learning-mode" in state.skills


def test_corrupt_json_raises(tmp_path: Path) -> None:
    path = tmp_path / ".installed.json"
    path.write_text("{ broken")
    with pytest.raises(StateError):
        load_state_from_path(path)


def test_schema_invalid_raises(tmp_path: Path) -> None:
    payload = _installed_payload()
    payload["scope"] = "global"  # not a valid scope literal
    path = tmp_path / ".installed.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(StateError):
        load_state_from_path(path)


def test_load_state_user_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    skills_dir = tmp_path / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / ".installed.json").write_text(json.dumps(_installed_payload()))
    state = load_state("user")
    assert state is not None
    assert "learning-mode" in state.skills


def test_load_state_absent_returns_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert load_state("user") is None


def test_write_then_read_roundtrip(tmp_path: Path) -> None:
    state = InstalledState(**_installed_payload())
    path = tmp_path / ".installed.json"
    write_state(state, path)
    assert load_state_from_path(path) == state


def test_save_state_user_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    state = InstalledState(**_installed_payload())
    save_state(state, "user")
    assert load_state("user") == state
