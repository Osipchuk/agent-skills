"""Pydantic v2 models for the askill data formats.

Two JSON formats are modelled here:
  - registry.json  → Library, RegistrySkill, Registry   (spec §6.2/§6.4)
  - installed.json → InstalledSkill, InstalledState      (spec §10.1)

Every model forbids unknown fields. The test suite in
``tests/unit/test_models.py`` is the spec.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# --------------------------------------------------------------------------- #
# Shared validation helpers
# --------------------------------------------------------------------------- #

_SEMVER_RE = re.compile(r"\d+\.\d+\.\d+")
_CHECKSUM_RE = re.compile(r"sha256:[0-9a-f]{64}")
_KEBAB_RE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


def _ensure_strict_semver(value: str) -> str:
    """A reusable field validator: take the value, raise ``ValueError`` (which
    pydantic surfaces as a ``ValidationError``) if it's bad, otherwise return
    it unchanged. Strict semver = three dotted non-negative integers, nothing
    else. We deliberately do NOT use ``packaging.version`` — it would accept
    ``1.2``, ``1.2.0a1``, ``v1.2.3``.
    """
    if not _SEMVER_RE.fullmatch(value):
        raise ValueError(f"version must be strict MAJOR.MINOR.PATCH, got {value!r}")
    return value


def _ensure_checksum(value: str) -> str:
    """Validate a ``sha256:<64 lowercase hex>`` checksum string."""
    if not _CHECKSUM_RE.fullmatch(value):
        raise ValueError(f"checksum must be in format 'sha256:<64 lowercase hex>', got {value!r}")
    return value


def _ensure_short_description(value: str) -> str:
    """Validate a short, single-line description (10..1024 chars)."""
    if not 10 <= len(value) <= 1024:
        raise ValueError("description must be 10..1024 characters")
    if "\n" in value or "\r" in value:
        raise ValueError("description must be a single line (no newlines)")
    return value


def _ensure_relative_path(value: str) -> str:
    """Reject absolute paths — registry/catalog paths are relative to the repo root."""
    if value.startswith("/"):
        raise ValueError("path must be relative to the repo root, not absolute")
    return value


def _ensure_kebab_tags(value: list[str]) -> list[str]:
    """Validate a tag list: at most 10 kebab-case strings."""
    if len(value) > 10:
        raise ValueError("at most 10 tags are allowed")
    for tag in value:
        if not _KEBAB_RE.fullmatch(tag):
            raise ValueError(f"tag is not kebab-case: {tag!r}")
    return value


def _ensure_has_claude_code(value: list[str]) -> list[str]:
    """v1 rule: ``compatible_agents`` must include ``claude-code``."""
    if "claude-code" not in value:
        raise ValueError("compatible_agents must include 'claude-code' (v1)")
    return value


def _duplicate_skill_names(names: Iterable[str]) -> list[str]:
    """Sorted list of names that occur more than once (empty when all unique)."""
    counts = Counter(names)
    return sorted(name for name, count in counts.items() if count > 1)


# --------------------------------------------------------------------------- #
# registry.json models
# --------------------------------------------------------------------------- #


class Library(BaseModel):
    """The ``library`` block of registry.json (spec §6.2)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    repo: str
    generated_at: datetime
    commit: str


class RegistrySkill(BaseModel):
    """One skill entry in registry.json (spec §6.4)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=r"^[a-z][a-z0-9-]{2,63}$")
    version: str
    description: str
    path: str
    entry: str = "SKILL.md"
    tags: list[str] = Field(default_factory=list)
    compatible_agents: list[str]
    dependencies: list[str] = Field(default_factory=list)
    checksum: str
    min_cli_version: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    author: str | None = None
    license: str | None = None

    @field_validator("version")
    @classmethod
    def _validate_version(cls, value: str) -> str:
        return _ensure_strict_semver(value)

    @field_validator("min_cli_version")
    @classmethod
    def _validate_min_cli_version(cls, value: str | None) -> str | None:
        return None if value is None else _ensure_strict_semver(value)

    @field_validator("checksum")
    @classmethod
    def _validate_checksum(cls, value: str) -> str:
        return _ensure_checksum(value)

    @field_validator("description")
    @classmethod
    def _validate_description(cls, value: str) -> str:
        return _ensure_short_description(value)

    @field_validator("path")
    @classmethod
    def _validate_path_relative(cls, value: str) -> str:
        return _ensure_relative_path(value)

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, value: list[str]) -> list[str]:
        return _ensure_kebab_tags(value)

    @field_validator("compatible_agents")
    @classmethod
    def _validate_compatible_agents(cls, value: list[str]) -> list[str]:
        return _ensure_has_claude_code(value)


class Registry(BaseModel):
    """The full registry.json manifest (spec §6.2)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    library: Library
    skills: list[RegistrySkill]

    @model_validator(mode="after")
    def _check_unique_skill_names(self) -> Registry:
        """Reject a manifest containing two skills with the same ``name``."""
        duplicates = _duplicate_skill_names(skill.name for skill in self.skills)
        if duplicates:
            raise ValueError("duplicate skill names: " + ", ".join(duplicates))
        return self


# --------------------------------------------------------------------------- #
# catalog.json models — the rich, presentation-oriented web artifact
#
# Clients (e.g. a Skills Library web page) consume catalog.json, NOT
# registry.json. CatalogSkill is a superset of the registry fields the UI needs
# minus install-only ones (no checksum/dependencies): it carries the short
# ``description`` (the design's "dek"), the full ``description_long`` trigger
# text, the editorial ``when``/``highlights``, a structured ``example`` trace,
# and a git-derived ``updated_at``. None of this is installed to a user; it is
# authored in ``catalog/<name>.yaml`` (see askill.core.manifest).
# --------------------------------------------------------------------------- #


class ExampleTurn(BaseModel):
    """One message in an example trace (spec: catalog ``example`` block)."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["user", "tool", "tool_out", "assistant", "anchor"]
    text: str


class Example(BaseModel):
    """A worked input→output trace shown on a skill's detail page."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    turns: int | None = Field(default=None, ge=0)
    tokens: int | None = Field(default=None, ge=0)
    caption: str | None = None
    trace_url: str | None = None
    input: list[ExampleTurn] = Field(default_factory=list)
    output: list[ExampleTurn] = Field(default_factory=list)


class CatalogSkill(BaseModel):
    """One skill entry in catalog.json (the web/presentation artifact)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=r"^[a-z][a-z0-9-]{2,63}$")
    version: str
    description: str
    description_long: str | None = None
    path: str
    entry: str = "SKILL.md"
    tags: list[str] = Field(default_factory=list)
    compatible_agents: list[str]
    license: str | None = None
    updated_at: datetime | None = None
    when: str | None = None
    highlights: list[str] = Field(default_factory=list)
    example: Example | None = None

    @field_validator("version")
    @classmethod
    def _validate_version(cls, value: str) -> str:
        return _ensure_strict_semver(value)

    @field_validator("description")
    @classmethod
    def _validate_description(cls, value: str) -> str:
        return _ensure_short_description(value)

    @field_validator("path")
    @classmethod
    def _validate_path_relative(cls, value: str) -> str:
        return _ensure_relative_path(value)

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, value: list[str]) -> list[str]:
        return _ensure_kebab_tags(value)

    @field_validator("compatible_agents")
    @classmethod
    def _validate_compatible_agents(cls, value: list[str]) -> list[str]:
        return _ensure_has_claude_code(value)


class Catalog(BaseModel):
    """The full catalog.json manifest the blog fetches over HTTPS."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    library: Library
    skills: list[CatalogSkill]

    @model_validator(mode="after")
    def _check_unique_skill_names(self) -> Catalog:
        """Reject a catalog containing two skills with the same ``name``."""
        duplicates = _duplicate_skill_names(skill.name for skill in self.skills)
        if duplicates:
            raise ValueError("duplicate skill names: " + ", ".join(duplicates))
        return self


# --------------------------------------------------------------------------- #
# installed.json models
# --------------------------------------------------------------------------- #


class InstalledSkill(BaseModel):
    """One installed-skill record in installed.json (spec §10.1).

    Note: ``path`` here is an absolute on-disk path, so (unlike
    RegistrySkill.path) it is NOT constrained to be relative.
    """

    model_config = ConfigDict(extra="forbid")

    version: str
    installed_at: datetime
    source_commit: str
    checksum: str
    path: str

    @field_validator("version")
    @classmethod
    def _validate_version(cls, value: str) -> str:
        return _ensure_strict_semver(value)

    @field_validator("checksum")
    @classmethod
    def _validate_checksum(cls, value: str) -> str:
        return _ensure_checksum(value)


class InstalledState(BaseModel):
    """The full installed.json state file for one scope (spec §10.1)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    scope: Literal["user", "project"]
    registry_url: str
    skills: dict[str, InstalledSkill] = Field(default_factory=dict)
