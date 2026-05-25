"""Tests for askill.core.installer — archive fetch, verify, and place."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import httpx
import pytest
from pytest_httpx import HTTPXMock

from askill.core.checksum import skill_checksum
from askill.core.installer import archive_url, download_archive, fetch_and_place
from askill.core.models import Library, RegistrySkill
from askill.utils.errors import ChecksumError, RegistryError

DESC = "A valid skill description used across installer tests."
LIBRARY = Library(
    name="askill-library",
    repo="https://github.com/example/agent-skills",
    generated_at="2026-05-21T10:00:00Z",
    commit="deadbeef",
)
ARCHIVE_URL = "https://github.com/example/agent-skills/archive/deadbeef.tar.gz"


def _skill(name: str, checksum: str) -> RegistrySkill:
    return RegistrySkill(
        name=name,
        version="0.1.0",
        description=DESC,
        path=f"skills/{name}",
        compatible_agents=["claude-code"],
        checksum=checksum,
    )


def _build_archive(
    tmp_path: Path, name: str, files: dict[str, str], prefix: str = "agent-skills-deadbeef"
) -> tuple[bytes, str]:
    """Build a gzipped repo tarball (prefix/skills/<name>/...); return (bytes, checksum)."""
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


def test_archive_url() -> None:
    assert archive_url(LIBRARY) == ARCHIVE_URL


def test_fetch_and_place_installs_files(tmp_path: Path, httpx_mock: HTTPXMock) -> None:
    archive, checksum = _build_archive(
        tmp_path, "learning-mode", {"SKILL.md": "hello", "scripts/run.py": "print(1)"}
    )
    httpx_mock.add_response(url=ARCHIVE_URL, content=archive)
    target = tmp_path / "out" / "learning-mode"
    fetch_and_place(_skill("learning-mode", checksum), LIBRARY, target)
    assert (target / "SKILL.md").read_text() == "hello"
    assert (target / "scripts" / "run.py").read_text() == "print(1)"


def test_checksum_mismatch_raises(tmp_path: Path, httpx_mock: HTTPXMock) -> None:
    archive, _ = _build_archive(tmp_path, "learning-mode", {"SKILL.md": "hello"})
    httpx_mock.add_response(url=ARCHIVE_URL, content=archive)
    skill = _skill("learning-mode", "sha256:" + "0" * 64)
    with pytest.raises(ChecksumError):
        fetch_and_place(skill, LIBRARY, tmp_path / "out")


def test_no_checksum_skips_verification(tmp_path: Path, httpx_mock: HTTPXMock) -> None:
    archive, _ = _build_archive(tmp_path, "learning-mode", {"SKILL.md": "hello"})
    httpx_mock.add_response(url=ARCHIVE_URL, content=archive)
    skill = _skill("learning-mode", "sha256:" + "0" * 64)  # deliberately wrong
    target = tmp_path / "out"
    fetch_and_place(skill, LIBRARY, target, verify_checksum=False)
    assert (target / "SKILL.md").read_text() == "hello"


def test_skill_not_in_archive_raises(tmp_path: Path, httpx_mock: HTTPXMock) -> None:
    archive, checksum = _build_archive(tmp_path, "other-skill", {"SKILL.md": "x"})
    httpx_mock.add_response(url=ARCHIVE_URL, content=archive)
    with pytest.raises(RegistryError):
        fetch_and_place(_skill("learning-mode", checksum), LIBRARY, tmp_path / "out")


def test_download_404_raises(tmp_path: Path, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=ARCHIVE_URL, status_code=404)
    with pytest.raises(RegistryError):
        fetch_and_place(_skill("learning-mode", "sha256:" + "0" * 64), LIBRARY, tmp_path / "out")


def test_download_retries_transient_then_succeeds(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dropped connection is transient — retry instead of failing the install."""
    monkeypatch.setattr("askill.core.installer.time.sleep", lambda *_: None)
    httpx_mock.add_exception(httpx.TransportError("Server disconnected"), url=ARCHIVE_URL)
    httpx_mock.add_response(url=ARCHIVE_URL, content=b"archive-bytes")
    assert download_archive(LIBRARY) == b"archive-bytes"


def test_download_gives_up_after_retries(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("askill.core.installer.time.sleep", lambda *_: None)
    for _ in range(3):  # retries=2 -> 3 attempts
        httpx_mock.add_exception(httpx.TransportError("Server disconnected"), url=ARCHIVE_URL)
    with pytest.raises(RegistryError, match="failed to download"):
        download_archive(LIBRARY)
