"""Integration tests for `askill install` — the §15 conflict matrix."""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from askill.cli import app
from askill.core.checksum import skill_checksum

runner = CliRunner()

REPO = "https://github.com/example/agent-skills"
COMMIT = "deadbeef"
ARCHIVE_URL = f"{REPO}/archive/{COMMIT}.tar.gz"
DESC = "A valid skill description used across install integration tests."
BAD_CHECKSUM = "sha256:" + "0" * 64


def _build_archive(tmp_path: Path, name: str, files: dict[str, str]) -> tuple[bytes, str]:
    prefix = "agent-skills-deadbeef"
    skill_dir = tmp_path / "build" / prefix / "skills" / name
    skill_dir.mkdir(parents=True)
    for rel, content in files.items():
        target = skill_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    checksum = skill_checksum(skill_dir)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        tar.add(tmp_path / "build" / prefix, arcname=prefix)
    return buffer.getvalue(), checksum


def _registry_file(
    tmp_path: Path, name: str, version: str, checksum: str, filename: str = "registry.json"
) -> str:
    payload = {
        "schema_version": "1.0",
        "library": {
            "name": "askill-library",
            "repo": REPO,
            "generated_at": "2026-05-21T10:00:00Z",
            "commit": COMMIT,
        },
        "skills": [
            {
                "name": name,
                "version": version,
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
    path = tmp_path / filename
    path.write_text(json.dumps(payload))
    return str(path)


def _args(reg: str, *extra: str) -> list[str]:
    return ["install", "learning-mode", "--registry", reg, "--scope", "user", *extra]


def _installed(tmp_path: Path) -> Path:
    return tmp_path / ".claude" / "skills" / "learning-mode"


def test_install_success_user_scope(
    tmp_path: Path, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    archive, checksum = _build_archive(tmp_path, "learning-mode", {"SKILL.md": "hello"})
    reg = _registry_file(tmp_path, "learning-mode", "0.1.0", checksum)
    httpx_mock.add_response(url=ARCHIVE_URL, content=archive)
    result = runner.invoke(app, _args(reg))
    assert result.exit_code == 0
    assert (_installed(tmp_path) / "SKILL.md").read_text() == "hello"
    state = json.loads((tmp_path / ".claude" / "skills" / ".installed.json").read_text())
    assert state["skills"]["learning-mode"]["version"] == "0.1.0"


def test_install_json(
    tmp_path: Path, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    archive, checksum = _build_archive(tmp_path, "learning-mode", {"SKILL.md": "hello"})
    reg = _registry_file(tmp_path, "learning-mode", "0.1.0", checksum)
    httpx_mock.add_response(url=ARCHIVE_URL, content=archive)
    result = runner.invoke(app, _args(reg, "--json"))
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "installed"
    assert data["version"] == "0.1.0"


def test_install_already_installed_noop(
    tmp_path: Path, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    archive, checksum = _build_archive(tmp_path, "learning-mode", {"SKILL.md": "hello"})
    reg = _registry_file(tmp_path, "learning-mode", "0.1.0", checksum)
    httpx_mock.add_response(url=ARCHIVE_URL, content=archive)  # used by the first install only
    assert runner.invoke(app, _args(reg)).exit_code == 0
    second = runner.invoke(app, _args(reg, "--json"))
    assert second.exit_code == 0
    assert json.loads(second.output)["status"] == "already-installed"


def test_install_conflict_different_version_exit_3(
    tmp_path: Path, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    archive, checksum = _build_archive(tmp_path, "learning-mode", {"SKILL.md": "hello"})
    reg1 = _registry_file(tmp_path, "learning-mode", "0.1.0", checksum)
    reg2 = _registry_file(tmp_path, "learning-mode", "0.2.0", checksum, "registry2.json")
    httpx_mock.add_response(url=ARCHIVE_URL, content=archive)
    assert runner.invoke(app, _args(reg1)).exit_code == 0
    result = runner.invoke(app, _args(reg2))  # different version, no --force
    assert result.exit_code == 3


def test_install_force_overwrites(
    tmp_path: Path, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    archive, checksum = _build_archive(tmp_path, "learning-mode", {"SKILL.md": "hello"})
    reg = _registry_file(tmp_path, "learning-mode", "0.1.0", checksum)
    httpx_mock.add_response(url=ARCHIVE_URL, content=archive)
    httpx_mock.add_response(url=ARCHIVE_URL, content=archive)  # second fetch for --force
    assert runner.invoke(app, _args(reg)).exit_code == 0
    result = runner.invoke(app, _args(reg, "--force", "--json"))
    assert result.exit_code == 0
    assert json.loads(result.output)["status"] == "installed"


def test_install_dry_run_writes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    reg = _registry_file(tmp_path, "learning-mode", "0.1.0", BAD_CHECKSUM)
    result = runner.invoke(app, _args(reg, "--dry-run", "--json"))
    assert result.exit_code == 0
    assert json.loads(result.output)["status"] == "would-install"
    assert not _installed(tmp_path).exists()


def test_install_unknown_skill_exit_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    reg = _registry_file(tmp_path, "learning-mode", "0.1.0", BAD_CHECKSUM)
    result = runner.invoke(app, ["install", "does-not-exist", "--registry", reg, "--scope", "user"])
    assert result.exit_code == 1


def test_install_checksum_mismatch_exit_2(
    tmp_path: Path, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    archive, _ = _build_archive(tmp_path, "learning-mode", {"SKILL.md": "hello"})
    reg = _registry_file(tmp_path, "learning-mode", "0.1.0", BAD_CHECKSUM)
    httpx_mock.add_response(url=ARCHIVE_URL, content=archive)
    result = runner.invoke(app, _args(reg))
    assert result.exit_code == 2


def test_install_no_checksum_bypass(
    tmp_path: Path, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    archive, _ = _build_archive(tmp_path, "learning-mode", {"SKILL.md": "hello"})
    reg = _registry_file(tmp_path, "learning-mode", "0.1.0", BAD_CHECKSUM)
    httpx_mock.add_response(url=ARCHIVE_URL, content=archive)
    result = runner.invoke(app, _args(reg, "--no-checksum"))
    assert result.exit_code == 0
    assert (_installed(tmp_path) / "SKILL.md").exists()
