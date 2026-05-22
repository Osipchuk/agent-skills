"""Tests for askill.core.manifest — build a validated Registry from skill folders."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from askill.core.checksum import skill_checksum
from askill.core.manifest import build_registry, build_registry_skill, parse_frontmatter
from askill.core.models import Registry, RegistrySkill


def _write_skill(repo_root: Path, folder: str, **overrides: Any) -> Path:
    """Create <repo_root>/skills/<folder>/SKILL.md with valid frontmatter."""
    meta: dict[str, Any] = {
        "name": folder,
        "description": "x" * 60,  # long trigger text (the registry uses `summary`)
        "summary": f"Short registry summary for {folder}.",
        "version": "0.1.0",
        "tags": ["alpha", "beta"],
        "compatible_agents": ["claude-code"],
        "license": "MIT",
    }
    meta.update(overrides)
    skill_dir = repo_root / "skills" / folder
    skill_dir.mkdir(parents=True)
    front = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)
    (skill_dir / "SKILL.md").write_text(f"---\n{front}---\n\n# {folder}\n\ninstructions\n")
    return skill_dir


# --------------------------------------------------------------------------- #
# parse_frontmatter
# --------------------------------------------------------------------------- #


def test_parse_frontmatter_valid() -> None:
    text = "---\nname: demo\ndescription: hi\n---\n\n# Body\n"
    assert parse_frontmatter(text) == {"name": "demo", "description": "hi"}


def test_parse_frontmatter_no_delimiters() -> None:
    with pytest.raises(ValueError):
        parse_frontmatter("# Just a heading\n\nno frontmatter here\n")


def test_parse_frontmatter_single_delimiter() -> None:
    with pytest.raises(ValueError):
        parse_frontmatter("---\nname: demo\nstill going, no closing fence\n")


def test_parse_frontmatter_empty_block() -> None:
    with pytest.raises(ValueError):
        parse_frontmatter("---\n---\n\nbody\n")


def test_parse_frontmatter_non_mapping() -> None:
    with pytest.raises(ValueError):
        parse_frontmatter("---\n- a\n- b\n---\n")


# --------------------------------------------------------------------------- #
# build_registry_skill
# --------------------------------------------------------------------------- #


def test_build_registry_skill_fields(tmp_path: Path) -> None:
    skill_dir = _write_skill(tmp_path, "learning-mode")
    skill = build_registry_skill(skill_dir, repo_root=tmp_path)
    assert isinstance(skill, RegistrySkill)
    assert skill.name == "learning-mode"
    assert skill.version == "0.1.0"
    assert skill.tags == ["alpha", "beta"]
    assert skill.compatible_agents == ["claude-code"]
    assert skill.license == "MIT"
    assert skill.entry == "SKILL.md"


def test_build_registry_skill_description_is_summary(tmp_path: Path) -> None:
    skill_dir = _write_skill(tmp_path, "demo-skill", summary="Just the short bit.")
    skill = build_registry_skill(skill_dir, repo_root=tmp_path)
    assert skill.description == "Just the short bit."  # not the long `description`


def test_build_registry_skill_path_is_relative_posix(tmp_path: Path) -> None:
    skill_dir = _write_skill(tmp_path, "demo-skill")
    skill = build_registry_skill(skill_dir, repo_root=tmp_path)
    assert skill.path == "skills/demo-skill"


def test_build_registry_skill_checksum_matches(tmp_path: Path) -> None:
    skill_dir = _write_skill(tmp_path, "demo-skill")
    skill = build_registry_skill(skill_dir, repo_root=tmp_path)
    assert skill.checksum == skill_checksum(skill_dir)


def test_build_registry_skill_missing_summary_raises(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skills" / "demo-skill"
    skill_dir.mkdir(parents=True)
    front = yaml.safe_dump(
        {"name": "demo-skill", "version": "0.1.0", "compatible_agents": ["claude-code"]}
    )
    (skill_dir / "SKILL.md").write_text(f"---\n{front}---\n\nbody\n")
    with pytest.raises(ValidationError):  # description (from summary) is missing
        build_registry_skill(skill_dir, repo_root=tmp_path)


# --------------------------------------------------------------------------- #
# build_registry
# --------------------------------------------------------------------------- #

NOW = dt.datetime(2026, 5, 22, 10, 0, tzinfo=dt.timezone.utc)


def test_build_registry_two_skills_sorted(tmp_path: Path) -> None:
    _write_skill(tmp_path, "zebra-skill")
    _write_skill(tmp_path, "alpha-skill")
    reg = build_registry(
        tmp_path / "skills", repo="https://example.com/r", commit="abc123", repo_root=tmp_path
    )
    assert isinstance(reg, Registry)
    assert [s.name for s in reg.skills] == ["alpha-skill", "zebra-skill"]  # sorted


def test_build_registry_library_fields(tmp_path: Path) -> None:
    _write_skill(tmp_path, "demo-skill")
    reg = build_registry(
        tmp_path / "skills",
        repo="https://example.com/r",
        commit="abc123",
        repo_root=tmp_path,
        now=NOW,
    )
    assert reg.schema_version == "1.0"
    assert reg.library.repo == "https://example.com/r"
    assert reg.library.commit == "abc123"
    assert reg.library.generated_at == NOW


def test_build_registry_skips_dirs_without_skill_md(tmp_path: Path) -> None:
    _write_skill(tmp_path, "demo-skill")
    (tmp_path / "skills" / "not-a-skill").mkdir()  # no SKILL.md inside
    reg = build_registry(
        tmp_path / "skills", repo="https://example.com/r", commit="abc", repo_root=tmp_path
    )
    assert [s.name for s in reg.skills] == ["demo-skill"]


def test_build_registry_duplicate_names_raise(tmp_path: Path) -> None:
    # two different folders whose frontmatter declares the same skill name
    _write_skill(tmp_path, "dir-one", name="dup")
    _write_skill(tmp_path, "dir-two", name="dup")
    with pytest.raises(ValidationError):
        build_registry(
            tmp_path / "skills", repo="https://example.com/r", commit="abc", repo_root=tmp_path
        )
