"""Tests for askill.core.manifest — build validated Registry/Catalog from skills/.

Field sourcing after the catalog split:
  - SKILL.md frontmatter  → name, description (long trigger text), version
  - catalog/<name>.yaml    → summary (registry/catalog `description`), tags,
                             compatible_agents, license, when, highlights, example
The catalog yaml lives OUTSIDE the skill folder, so it is never installed and
never affects the skill's checksum.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from askill.core.checksum import skill_checksum
from askill.core.manifest import (
    build_catalog,
    build_catalog_skill,
    build_registry,
    build_registry_skill,
    load_catalog_meta,
    parse_frontmatter,
)
from askill.core.models import Catalog, CatalogSkill, Registry, RegistrySkill

_FRONT_KEYS = {"name", "description", "version"}
_META_KEYS = {"summary", "tags", "compatible_agents", "license", "when", "highlights", "example"}


def _write_skill(repo_root: Path, folder: str, *, catalog: bool = True, **overrides: Any) -> Path:
    """Create skills/<folder>/SKILL.md + catalog/<name>.yaml with valid content.

    Overrides route to the right file by key; pass ``catalog=False`` to skip
    writing the catalog yaml (for the missing-metadata error path).
    """
    name = overrides.get("name", folder)
    front: dict[str, Any] = {"name": name, "description": "x" * 60, "version": "0.1.0"}
    meta: dict[str, Any] = {
        "summary": f"Short registry summary for {name}.",
        "tags": ["alpha", "beta"],
        "compatible_agents": ["claude-code"],
        "license": "MIT",
    }
    for key, value in overrides.items():
        if key in _FRONT_KEYS:
            front[key] = value
        elif key in _META_KEYS:
            meta[key] = value
        else:  # pragma: no cover - guards against typos in tests
            raise KeyError(f"unknown override {key!r}")

    skill_dir = repo_root / "skills" / folder
    skill_dir.mkdir(parents=True)
    front_yaml = yaml.safe_dump(front, sort_keys=False, allow_unicode=True)
    (skill_dir / "SKILL.md").write_text(f"---\n{front_yaml}---\n\n# {folder}\n\ninstructions\n")

    if catalog:
        _write_catalog(repo_root, name, meta)
    return skill_dir


def _write_catalog(repo_root: Path, name: str, meta: dict[str, Any]) -> None:
    catalog_dir = repo_root / "catalog"
    catalog_dir.mkdir(exist_ok=True)
    text = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)
    (catalog_dir / f"{name}.yaml").write_text(text)


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
# load_catalog_meta
# --------------------------------------------------------------------------- #


def test_load_catalog_meta_reads_yaml(tmp_path: Path) -> None:
    _write_catalog(tmp_path, "demo-skill", {"summary": "hi", "tags": ["a"]})
    meta = load_catalog_meta("demo-skill", tmp_path)
    assert meta == {"summary": "hi", "tags": ["a"]}


def test_load_catalog_meta_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        load_catalog_meta("nope", tmp_path)


def test_load_catalog_meta_empty_raises(tmp_path: Path) -> None:
    (tmp_path / "catalog").mkdir()
    (tmp_path / "catalog" / "demo.yaml").write_text("\n")
    with pytest.raises(ValueError):
        load_catalog_meta("demo", tmp_path)


def test_load_catalog_meta_non_mapping_raises(tmp_path: Path) -> None:
    (tmp_path / "catalog").mkdir()
    (tmp_path / "catalog" / "demo.yaml").write_text("- a\n- b\n")
    with pytest.raises(ValueError):
        load_catalog_meta("demo", tmp_path)


# --------------------------------------------------------------------------- #
# build_registry_skill — now sources catalog fields from catalog/<name>.yaml
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


def test_build_registry_skill_description_is_catalog_summary(tmp_path: Path) -> None:
    skill_dir = _write_skill(tmp_path, "demo-skill", summary="Just the short bit.")
    skill = build_registry_skill(skill_dir, repo_root=tmp_path)
    assert skill.description == "Just the short bit."  # from catalog, not SKILL.md


def test_build_registry_skill_path_is_relative_posix(tmp_path: Path) -> None:
    skill_dir = _write_skill(tmp_path, "demo-skill")
    skill = build_registry_skill(skill_dir, repo_root=tmp_path)
    assert skill.path == "skills/demo-skill"


def test_build_registry_skill_checksum_matches(tmp_path: Path) -> None:
    skill_dir = _write_skill(tmp_path, "demo-skill")
    skill = build_registry_skill(skill_dir, repo_root=tmp_path)
    assert skill.checksum == skill_checksum(skill_dir)


def test_build_registry_skill_missing_catalog_raises(tmp_path: Path) -> None:
    skill_dir = _write_skill(tmp_path, "demo-skill", catalog=False)
    with pytest.raises(ValueError):
        build_registry_skill(skill_dir, repo_root=tmp_path)


def test_build_registry_skill_missing_summary_raises(tmp_path: Path) -> None:
    skill_dir = _write_skill(tmp_path, "demo-skill", catalog=False)
    _write_catalog(tmp_path, "demo-skill", {"tags": ["a"], "compatible_agents": ["claude-code"]})
    with pytest.raises(ValidationError):  # description (from summary) missing
        build_registry_skill(skill_dir, repo_root=tmp_path)


# --------------------------------------------------------------------------- #
# build_catalog_skill
# --------------------------------------------------------------------------- #


def test_build_catalog_skill_core_fields(tmp_path: Path) -> None:
    skill_dir = _write_skill(tmp_path, "demo-skill", summary="The short dek line.")
    skill = build_catalog_skill(skill_dir, repo_root=tmp_path)
    assert isinstance(skill, CatalogSkill)
    assert skill.name == "demo-skill"
    assert skill.version == "0.1.0"
    assert skill.description == "The short dek line."
    assert skill.path == "skills/demo-skill"
    assert skill.tags == ["alpha", "beta"]
    assert skill.license == "MIT"


def test_build_catalog_skill_description_long_from_frontmatter(tmp_path: Path) -> None:
    skill_dir = _write_skill(tmp_path, "demo-skill", description="The long trigger text here.")
    skill = build_catalog_skill(skill_dir, repo_root=tmp_path)
    assert skill.description_long == "The long trigger text here."


def test_build_catalog_skill_rich_meta(tmp_path: Path) -> None:
    skill_dir = _write_skill(
        tmp_path,
        "demo-skill",
        when="When a loop runs.",
        highlights=["does a", "does b"],
        example={"input": [{"kind": "user", "text": "hi"}], "output": []},
    )
    skill = build_catalog_skill(skill_dir, repo_root=tmp_path)
    assert skill.when == "When a loop runs."
    assert skill.highlights == ["does a", "does b"]
    assert skill.example is not None
    assert skill.example.input[0].kind == "user"


def test_build_catalog_skill_updated_at_passthrough(tmp_path: Path) -> None:
    skill_dir = _write_skill(tmp_path, "demo-skill")
    when = dt.datetime(2026, 4, 22, tzinfo=dt.UTC)
    skill = build_catalog_skill(skill_dir, repo_root=tmp_path, updated_at=when)
    assert skill.updated_at == when


def test_build_catalog_skill_updated_at_defaults_none(tmp_path: Path) -> None:
    skill_dir = _write_skill(tmp_path, "demo-skill")
    assert build_catalog_skill(skill_dir, repo_root=tmp_path).updated_at is None


def test_build_catalog_skill_missing_catalog_raises(tmp_path: Path) -> None:
    skill_dir = _write_skill(tmp_path, "demo-skill", catalog=False)
    with pytest.raises(ValueError):
        build_catalog_skill(skill_dir, repo_root=tmp_path)


# --------------------------------------------------------------------------- #
# build_registry / build_catalog
# --------------------------------------------------------------------------- #

NOW = dt.datetime(2026, 5, 22, 10, 0, tzinfo=dt.UTC)


def test_build_registry_two_skills_sorted(tmp_path: Path) -> None:
    _write_skill(tmp_path, "zebra-skill")
    _write_skill(tmp_path, "alpha-skill")
    reg = build_registry(
        tmp_path / "skills", repo="https://example.com/r", commit="abc123", repo_root=tmp_path
    )
    assert isinstance(reg, Registry)
    assert [s.name for s in reg.skills] == ["alpha-skill", "zebra-skill"]


def test_build_registry_skips_dirs_without_skill_md(tmp_path: Path) -> None:
    _write_skill(tmp_path, "demo-skill")
    (tmp_path / "skills" / "not-a-skill").mkdir()
    reg = build_registry(
        tmp_path / "skills", repo="https://example.com/r", commit="abc", repo_root=tmp_path
    )
    assert [s.name for s in reg.skills] == ["demo-skill"]


def test_build_registry_duplicate_names_raise(tmp_path: Path) -> None:
    _write_skill(tmp_path, "dir-one", name="dup")
    _write_skill(tmp_path, "dir-two", name="dup")
    with pytest.raises(ValidationError):
        build_registry(
            tmp_path / "skills", repo="https://example.com/r", commit="abc", repo_root=tmp_path
        )


def test_build_catalog_two_skills_sorted(tmp_path: Path) -> None:
    _write_skill(tmp_path, "zebra-skill")
    _write_skill(tmp_path, "alpha-skill")
    cat = build_catalog(
        tmp_path / "skills", repo="https://example.com/r", commit="abc123", repo_root=tmp_path
    )
    assert isinstance(cat, Catalog)
    assert [s.name for s in cat.skills] == ["alpha-skill", "zebra-skill"]


def test_build_catalog_library_fields(tmp_path: Path) -> None:
    _write_skill(tmp_path, "demo-skill")
    cat = build_catalog(
        tmp_path / "skills",
        repo="https://example.com/r",
        commit="abc123",
        repo_root=tmp_path,
        now=NOW,
    )
    assert cat.schema_version == "1.0"
    assert cat.library.repo == "https://example.com/r"
    assert cat.library.commit == "abc123"
    assert cat.library.generated_at == NOW


def test_build_catalog_uses_updated_at_resolver(tmp_path: Path) -> None:
    _write_skill(tmp_path, "demo-skill")
    when = dt.datetime(2026, 4, 22, tzinfo=dt.UTC)
    cat = build_catalog(
        tmp_path / "skills",
        repo="https://example.com/r",
        commit="abc",
        repo_root=tmp_path,
        updated_at_for=lambda _dir: when,
    )
    assert cat.skills[0].updated_at == when


def test_build_catalog_skips_dirs_without_skill_md(tmp_path: Path) -> None:
    _write_skill(tmp_path, "demo-skill")
    (tmp_path / "skills" / "not-a-skill").mkdir()
    cat = build_catalog(
        tmp_path / "skills", repo="https://example.com/r", commit="abc", repo_root=tmp_path
    )
    assert [s.name for s in cat.skills] == ["demo-skill"]
