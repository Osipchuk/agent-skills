"""Tests for askill.core.models — the pydantic v2 manifest/state models.

These tests are the SPEC for core/models.py. Make them pass.

The models map the spec's two JSON formats:
  - registry.json  → Library, RegistrySkill, Registry   (spec §6.2/§6.4)
  - installed.json → InstalledSkill, InstalledState      (spec §10.1)

Every model rejects unknown fields (pydantic ConfigDict(extra="forbid")).
Invalid input must raise pydantic.ValidationError.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from pydantic import ValidationError

from askill.core.models import (
    InstalledSkill,
    InstalledState,
    Library,
    Registry,
    RegistrySkill,
)

# A 64-hex sha256 (the empty-string digest) used as a valid checksum value.
SHA = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def valid_skill_dict(**overrides: Any) -> dict[str, Any]:
    """A minimal-but-complete valid RegistrySkill payload; override per-test."""
    base: dict[str, Any] = {
        "name": "pdf-extractor",
        "version": "1.2.0",
        "description": "Extract text and tables from PDF files.",
        "path": "skills/pdf-extractor",
        "entry": "SKILL.md",
        "tags": ["pdf", "data-tools"],
        "compatible_agents": ["claude-code"],
        "dependencies": [],
        "checksum": SHA,
    }
    base.update(overrides)
    return base


def valid_installed_skill_dict(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "version": "1.2.0",
        "installed_at": "2026-05-21T10:00:00Z",
        "source_commit": "abc123def456",
        "checksum": SHA,
        "path": "/home/user/.claude/skills/pdf-extractor",
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# RegistrySkill — happy path & defaults
# --------------------------------------------------------------------------- #


def test_valid_skill_parses() -> None:
    skill = RegistrySkill(**valid_skill_dict())
    assert skill.name == "pdf-extractor"
    assert skill.version == "1.2.0"
    assert skill.compatible_agents == ["claude-code"]


def test_entry_defaults_to_skill_md() -> None:
    payload = valid_skill_dict()
    del payload["entry"]
    assert RegistrySkill(**payload).entry == "SKILL.md"


def test_optional_fields_default_to_none_or_empty() -> None:
    skill = RegistrySkill(**valid_skill_dict())
    assert skill.min_cli_version is None
    assert skill.size_bytes is None
    assert skill.author is None
    assert skill.license is None
    assert skill.dependencies == []


def test_optional_fields_accepted_when_present() -> None:
    skill = RegistrySkill(
        **valid_skill_dict(
            min_cli_version="0.1.0",
            size_bytes=12480,
            author="user@example.com",
            license="MIT",
        )
    )
    assert skill.min_cli_version == "0.1.0"
    assert skill.size_bytes == 12480


def test_extra_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RegistrySkill(**valid_skill_dict(surprise="nope"))


@pytest.mark.parametrize(
    "field",
    ["name", "version", "description", "path", "compatible_agents", "checksum"],
)
def test_required_field_omitted_raises(field: str) -> None:
    payload = valid_skill_dict()
    del payload[field]
    with pytest.raises(ValidationError):
        RegistrySkill(**payload)


# --------------------------------------------------------------------------- #
# RegistrySkill — field validation rules
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", ["pdf-extractor", "abc", "a1b", "x" * 64])
def test_name_valid(name: str) -> None:
    # pattern: ^[a-z][a-z0-9-]{2,63}$  → starts lower-alpha, total length 3..64
    RegistrySkill(**valid_skill_dict(name=name))


@pytest.mark.parametrize(
    "name",
    ["PDF-Extractor", "1abc", "ab", "-abc", "abc_def", "x" * 65, "abc!"],
)
def test_name_invalid(name: str) -> None:
    with pytest.raises(ValidationError):
        RegistrySkill(**valid_skill_dict(name=name))


@pytest.mark.parametrize("version", ["1.2.0", "0.0.1", "10.20.30"])
def test_version_valid(version: str) -> None:
    RegistrySkill(**valid_skill_dict(version=version))


@pytest.mark.parametrize(
    "version",
    ["1.2", "1.2.0.0", "1.2.0a1", "v1.2.3", "1.2.x", "", "1"],
)
def test_version_invalid_strict_semver(version: str) -> None:
    # Strict MAJOR.MINOR.PATCH — NOT packaging.version (which would accept these).
    with pytest.raises(ValidationError):
        RegistrySkill(**valid_skill_dict(version=version))


def test_description_min_length() -> None:
    with pytest.raises(ValidationError):
        RegistrySkill(**valid_skill_dict(description="too short"))  # 9 chars


def test_description_max_length() -> None:
    with pytest.raises(ValidationError):
        RegistrySkill(**valid_skill_dict(description="x" * 1025))


def test_description_single_line() -> None:
    with pytest.raises(ValidationError):
        RegistrySkill(**valid_skill_dict(description="line one\nline two here"))


def test_description_boundary_lengths_ok() -> None:
    RegistrySkill(**valid_skill_dict(description="x" * 10))
    RegistrySkill(**valid_skill_dict(description="x" * 1024))


@pytest.mark.parametrize("path", ["skills/pdf-extractor", "a/b/c", "single"])
def test_path_relative_ok(path: str) -> None:
    RegistrySkill(**valid_skill_dict(path=path))


@pytest.mark.parametrize("path", ["/abs/path", "/etc/passwd"])
def test_path_absolute_rejected(path: str) -> None:
    with pytest.raises(ValidationError):
        RegistrySkill(**valid_skill_dict(path=path))


@pytest.mark.parametrize("tags", [[], ["pdf"], ["pdf", "data-tools"], ["a1", "b-2-c"]])
def test_tags_valid(tags: list[str]) -> None:
    RegistrySkill(**valid_skill_dict(tags=tags))


@pytest.mark.parametrize(
    "tags",
    [["PDF"], ["-x"], ["x-"], ["a--b"], ["under_score"], [f"t{i}" for i in range(11)]],
)
def test_tags_invalid(tags: list[str]) -> None:
    with pytest.raises(ValidationError):
        RegistrySkill(**valid_skill_dict(tags=tags))


@pytest.mark.parametrize(
    "agents", [["claude-code"], ["claude-code", "codex"], ["codex", "claude-code"]]
)
def test_compatible_agents_valid(agents: list[str]) -> None:
    RegistrySkill(**valid_skill_dict(compatible_agents=agents))


@pytest.mark.parametrize("agents", [[], ["codex"], ["claude"], ["Claude-Code"]])
def test_compatible_agents_must_include_claude_code(agents: list[str]) -> None:
    with pytest.raises(ValidationError):
        RegistrySkill(**valid_skill_dict(compatible_agents=agents))


@pytest.mark.parametrize(
    "checksum",
    [
        "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "sha256:" + "a" * 64,
        "sha256:" + "0" * 64,
    ],
)
def test_checksum_valid(checksum: str) -> None:
    RegistrySkill(**valid_skill_dict(checksum=checksum))


@pytest.mark.parametrize(
    "checksum",
    [
        "md5:" + "a" * 64,  # wrong algo prefix
        "sha256:" + "a" * 63,  # too short
        "sha256:" + "a" * 65,  # too long
        "sha256:" + "g" * 64,  # non-hex
        "a" * 64,  # missing prefix
        "sha256:ABCDEF" + "0" * 58,  # uppercase hex not allowed
    ],
)
def test_checksum_invalid(checksum: str) -> None:
    with pytest.raises(ValidationError):
        RegistrySkill(**valid_skill_dict(checksum=checksum))


def test_min_cli_version_strict_semver() -> None:
    RegistrySkill(**valid_skill_dict(min_cli_version="0.1.0"))
    with pytest.raises(ValidationError):
        RegistrySkill(**valid_skill_dict(min_cli_version="0.1"))


def test_size_bytes_non_negative() -> None:
    with pytest.raises(ValidationError):
        RegistrySkill(**valid_skill_dict(size_bytes=-1))


# --------------------------------------------------------------------------- #
# Library
# --------------------------------------------------------------------------- #


def test_library_parses_and_parses_datetime() -> None:
    lib = Library(
        name="askill-library",
        repo="https://github.com/org/repo",
        generated_at="2026-05-21T10:00:00Z",
        commit="abc123def456",
    )
    assert isinstance(lib.generated_at, dt.datetime)
    assert lib.generated_at.tzinfo is not None  # trailing Z → aware datetime


def test_library_rejects_extra() -> None:
    with pytest.raises(ValidationError):
        Library(
            name="x",
            repo="https://github.com/org/repo",
            generated_at="2026-05-21T10:00:00Z",
            commit="abc",
            extra_field="no",
        )


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #


def valid_registry_dict(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": "1.0",
        "library": {
            "name": "askill-library",
            "repo": "https://github.com/org/repo",
            "generated_at": "2026-05-21T10:00:00Z",
            "commit": "abc123def456",
        },
        "skills": [
            valid_skill_dict(name="pdf-extractor"),
            valid_skill_dict(name="docx-builder"),
        ],
    }
    base.update(overrides)
    return base


def test_registry_parses_with_skills() -> None:
    reg = Registry(**valid_registry_dict())
    assert len(reg.skills) == 2
    assert isinstance(reg.library, Library)
    assert {s.name for s in reg.skills} == {"pdf-extractor", "docx-builder"}


def test_registry_empty_skills_ok() -> None:
    assert Registry(**valid_registry_dict(skills=[])).skills == []


def test_registry_duplicate_skill_names_rejected() -> None:
    dupes = [valid_skill_dict(name="pdf-extractor"), valid_skill_dict(name="pdf-extractor")]
    with pytest.raises(ValidationError):
        Registry(**valid_registry_dict(skills=dupes))


# --------------------------------------------------------------------------- #
# InstalledSkill / InstalledState
# --------------------------------------------------------------------------- #


def test_installed_skill_parses() -> None:
    sk = InstalledSkill(**valid_installed_skill_dict())
    assert sk.version == "1.2.0"
    assert isinstance(sk.installed_at, dt.datetime)


def test_installed_skill_version_is_strict_semver() -> None:
    with pytest.raises(ValidationError):
        InstalledSkill(**valid_installed_skill_dict(version="1.2"))


def valid_installed_state_dict(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": "1.0",
        "scope": "user",
        "registry_url": "https://example.com/registry.json",
        "skills": {"pdf-extractor": valid_installed_skill_dict()},
    }
    base.update(overrides)
    return base


def test_installed_state_parses() -> None:
    state = InstalledState(**valid_installed_state_dict())
    assert state.scope == "user"
    assert "pdf-extractor" in state.skills
    assert isinstance(state.skills["pdf-extractor"], InstalledSkill)


def test_installed_state_skills_defaults_empty() -> None:
    payload = valid_installed_state_dict()
    del payload["skills"]
    assert InstalledState(**payload).skills == {}


@pytest.mark.parametrize("scope", ["global", "system", "", "User"])
def test_installed_state_scope_literal(scope: str) -> None:
    with pytest.raises(ValidationError):
        InstalledState(**valid_installed_state_dict(scope=scope))
