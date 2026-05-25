"""Tests for the catalog.json pydantic models — the rich web-catalog artifact.

The blog consumes catalog.json (not registry.json). CatalogSkill mirrors
RegistrySkill's validation where fields overlap, but drops install-only fields
(checksum, dependencies, …) and adds the presentation fields the design needs:
``description_long``, ``when``, ``highlights``, ``example``, ``updated_at``.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from pydantic import ValidationError

from askill.core.models import Catalog, CatalogSkill, Example, ExampleTurn, Library


def valid_catalog_skill_dict(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "name": "re-anchor",
        "version": "0.1.0",
        "description": "Re-injects the system prompt after every tool turn.",
        "path": "skills/re-anchor",
        "tags": ["agent-safety", "prompt-injection"],
        "compatible_agents": ["claude-code"],
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# ExampleTurn
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("kind", ["user", "tool", "tool_out", "assistant", "anchor"])
def test_example_turn_kinds_valid(kind: str) -> None:
    assert ExampleTurn(kind=kind, text="x").kind == kind


def test_example_turn_kind_invalid() -> None:
    with pytest.raises(ValidationError):
        ExampleTurn(kind="system", text="x")


def test_example_turn_rejects_extra() -> None:
    with pytest.raises(ValidationError):
        ExampleTurn(kind="user", text="x", surprise="no")


# --------------------------------------------------------------------------- #
# Example
# --------------------------------------------------------------------------- #


def test_example_parses_full() -> None:
    ex = Example(
        title="prompt-injection in a fetched page",
        turns=5,
        tokens=312,
        caption="Without re-anchor, the trace leaks the system prompt.",
        trace_url="https://example.com/trace",
        input=[{"kind": "user", "text": "a"}],
        output=[{"kind": "assistant", "text": "b"}],
    )
    assert isinstance(ex.input[0], ExampleTurn)
    assert ex.input[0].kind == "user"
    assert ex.output[0].text == "b"


def test_example_defaults_empty() -> None:
    ex = Example()
    assert ex.input == []
    assert ex.output == []
    assert ex.title is None
    assert ex.turns is None


def test_example_negative_counts_rejected() -> None:
    with pytest.raises(ValidationError):
        Example(turns=-1)
    with pytest.raises(ValidationError):
        Example(tokens=-1)


def test_example_rejects_extra() -> None:
    with pytest.raises(ValidationError):
        Example(surprise="no")


# --------------------------------------------------------------------------- #
# CatalogSkill — happy path & defaults
# --------------------------------------------------------------------------- #


def test_catalog_skill_parses() -> None:
    s = CatalogSkill(**valid_catalog_skill_dict())
    assert s.name == "re-anchor"
    assert s.entry == "SKILL.md"
    assert s.tags == ["agent-safety", "prompt-injection"]


def test_catalog_skill_optional_defaults() -> None:
    s = CatalogSkill(**valid_catalog_skill_dict())
    assert s.description_long is None
    assert s.when is None
    assert s.highlights == []
    assert s.example is None
    assert s.updated_at is None
    assert s.license is None


def test_catalog_skill_rich_fields_parse() -> None:
    s = CatalogSkill(
        **valid_catalog_skill_dict(
            description_long="Long trigger text. " * 20,
            when="When a loop runs >=3 tool turns.",
            highlights=["re-injects SYSTEM", "quarantines tool output"],
            updated_at="2026-04-22T00:00:00Z",
            example={"input": [{"kind": "user", "text": "x"}], "output": []},
            license="MIT",
        )
    )
    assert isinstance(s.example, Example)
    assert isinstance(s.updated_at, dt.datetime)
    assert s.highlights == ["re-injects SYSTEM", "quarantines tool output"]


def test_catalog_skill_description_long_is_uncapped() -> None:
    # Unlike `description`, the long trigger text is not capped at 1024 chars.
    s = CatalogSkill(**valid_catalog_skill_dict(description_long="x" * 5000))
    assert s.description_long is not None
    assert len(s.description_long) == 5000


def test_catalog_skill_rejects_extra() -> None:
    with pytest.raises(ValidationError):
        CatalogSkill(**valid_catalog_skill_dict(surprise="no"))


def test_catalog_skill_rejects_checksum() -> None:
    # checksum is an install concern — catalog has no business carrying it.
    with pytest.raises(ValidationError):
        CatalogSkill(**valid_catalog_skill_dict(checksum="sha256:" + "a" * 64))


@pytest.mark.parametrize("field", ["name", "version", "description", "path", "compatible_agents"])
def test_catalog_skill_required_field_omitted_raises(field: str) -> None:
    payload = valid_catalog_skill_dict()
    del payload[field]
    with pytest.raises(ValidationError):
        CatalogSkill(**payload)


# --------------------------------------------------------------------------- #
# CatalogSkill — validation rules shared with RegistrySkill
# --------------------------------------------------------------------------- #


def test_catalog_skill_version_strict_semver() -> None:
    with pytest.raises(ValidationError):
        CatalogSkill(**valid_catalog_skill_dict(version="0.1"))


def test_catalog_skill_description_single_line() -> None:
    with pytest.raises(ValidationError):
        CatalogSkill(**valid_catalog_skill_dict(description="line one\nline two and more text"))


def test_catalog_skill_description_max_length() -> None:
    with pytest.raises(ValidationError):
        CatalogSkill(**valid_catalog_skill_dict(description="x" * 1025))


def test_catalog_skill_path_absolute_rejected() -> None:
    with pytest.raises(ValidationError):
        CatalogSkill(**valid_catalog_skill_dict(path="/abs/path"))


@pytest.mark.parametrize("tags", [["UPPER"], [f"t{i}" for i in range(11)], ["under_score"]])
def test_catalog_skill_tags_invalid(tags: list[str]) -> None:
    with pytest.raises(ValidationError):
        CatalogSkill(**valid_catalog_skill_dict(tags=tags))


def test_catalog_skill_compatible_agents_requires_claude_code() -> None:
    with pytest.raises(ValidationError):
        CatalogSkill(**valid_catalog_skill_dict(compatible_agents=["codex"]))


# --------------------------------------------------------------------------- #
# Catalog
# --------------------------------------------------------------------------- #


def valid_catalog_dict(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": "1.0",
        "library": {
            "name": "askill-library",
            "repo": "https://github.com/org/repo",
            "generated_at": "2026-05-21T10:00:00Z",
            "commit": "abc123def456",
        },
        "skills": [
            valid_catalog_skill_dict(name="re-anchor"),
            valid_catalog_skill_dict(name="probe-bank"),
        ],
    }
    base.update(overrides)
    return base


def test_catalog_parses_with_skills() -> None:
    c = Catalog(**valid_catalog_dict())
    assert len(c.skills) == 2
    assert isinstance(c.library, Library)
    assert isinstance(c.skills[0], CatalogSkill)


def test_catalog_empty_skills_ok() -> None:
    assert Catalog(**valid_catalog_dict(skills=[])).skills == []


def test_catalog_duplicate_skill_names_rejected() -> None:
    dupes = [valid_catalog_skill_dict(name="x-skill"), valid_catalog_skill_dict(name="x-skill")]
    with pytest.raises(ValidationError):
        Catalog(**valid_catalog_dict(skills=dupes))


def test_catalog_rejects_extra() -> None:
    with pytest.raises(ValidationError):
        Catalog(**valid_catalog_dict(surprise="no"))
