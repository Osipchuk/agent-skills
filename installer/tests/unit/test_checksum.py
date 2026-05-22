"""Tests for askill.core.checksum — deterministic skill-folder checksums (§13.3)."""

from __future__ import annotations

import os
import re
from pathlib import Path

from askill.core.checksum import skill_checksum

_FORMAT = re.compile(r"^sha256:[0-9a-f]{64}$")


def _make_skill(root: Path, files: dict[str, str]) -> Path:
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return root


def test_checksum_has_registry_format(tmp_path: Path) -> None:
    folder = _make_skill(tmp_path / "skill", {"SKILL.md": "hello"})
    assert _FORMAT.fullmatch(skill_checksum(folder))


def test_checksum_is_deterministic(tmp_path: Path) -> None:
    files = {"SKILL.md": "hello", "scripts/run.py": "print(1)"}
    a = _make_skill(tmp_path / "a", files)
    b = _make_skill(tmp_path / "b", files)
    assert skill_checksum(a) == skill_checksum(b)


def test_checksum_changes_with_content(tmp_path: Path) -> None:
    a = _make_skill(tmp_path / "a", {"SKILL.md": "hello"})
    b = _make_skill(tmp_path / "b", {"SKILL.md": "HELLO"})
    assert skill_checksum(a) != skill_checksum(b)


def test_checksum_ignores_mtime(tmp_path: Path) -> None:
    folder = _make_skill(tmp_path / "skill", {"SKILL.md": "hello"})
    before = skill_checksum(folder)
    os.utime(folder / "SKILL.md", (0, 0))
    assert skill_checksum(folder) == before


def test_checksum_depends_on_filename(tmp_path: Path) -> None:
    a = _make_skill(tmp_path / "a", {"SKILL.md": "x"})
    b = _make_skill(tmp_path / "b", {"OTHER.md": "x"})
    assert skill_checksum(a) != skill_checksum(b)
