"""Build validated Registry/Catalog manifests from skill folders (spec §6).

Pure assembly: read each skill's ``SKILL.md`` frontmatter and its sibling
``catalog/<name>.yaml``, compute the §13.3 checksum, and construct the pydantic
models (which do all the validation). No file writes — and no git/network — so
this module stays trivially testable; the generator script
(``scripts/generate_registry.py``) handles all I/O (writing JSON, resolving git
dates) and injects results in.

Field sourcing:
  - SKILL.md frontmatter  → name, description (long trigger text), version
  - catalog/<name>.yaml    → summary (the registry/catalog ``description`` and
                             the design's "dek"), tags, compatible_agents,
                             license, when, highlights, example

The catalog yaml lives OUTSIDE the skill folder, so it is never installed to a
user and never affects the skill's checksum. The rich fields (description_long,
when, highlights, example, updated_at) appear only in catalog.json, never in the
lean registry.json.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from askill.core.checksum import skill_checksum
from askill.core.models import Catalog, CatalogSkill, Library, Registry, RegistrySkill


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Parse the leading ``---``-delimited YAML frontmatter block into a mapping.

    Raises ``ValueError`` if the block is missing, unclosed, empty, or not a
    YAML mapping.
    """
    if not text.startswith("---"):
        raise ValueError("frontmatter must start with '---'")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("frontmatter is not closed with a second '---'")
    data = yaml.safe_load(parts[1])
    if data is None:
        raise ValueError("frontmatter block is empty")
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return data


def _read_frontmatter(skill_dir: Path) -> dict[str, Any]:
    """Read and parse ``<skill_dir>/SKILL.md`` frontmatter."""
    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.is_file():
        raise ValueError(f"skill directory {skill_dir} does not contain SKILL.md")
    return parse_frontmatter(skill_md_path.read_text(encoding="utf-8"))


def load_catalog_meta(name: str, repo_root: Path) -> dict[str, Any]:
    """Load and parse ``<repo_root>/catalog/<name>.yaml`` into a mapping.

    This file holds the presentation/catalog metadata kept out of SKILL.md so it
    is never installed. Raises ``ValueError`` if it is missing, empty, or not a
    YAML mapping.
    """
    path = repo_root / "catalog" / f"{name}.yaml"
    if not path.is_file():
        raise ValueError(f"missing catalog metadata file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        raise ValueError(f"catalog metadata file is empty: {path}")
    if not isinstance(data, dict):
        raise ValueError(f"catalog metadata must be a YAML mapping: {path}")
    return data


def _skill_common(
    skill_dir: Path, *, repo_root: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Shared head of both skill builders: parse the SKILL.md frontmatter and the
    sibling catalog meta, and assemble the fields common to RegistrySkill and
    CatalogSkill. Returns ``(front, meta, data)`` so each builder can layer on its
    format-specific fields without re-reading anything.
    """
    front = _read_frontmatter(skill_dir)
    name = front.get("name", skill_dir.name)
    meta = load_catalog_meta(name, repo_root)
    data = {
        "name": name,
        "version": front.get("version"),
        "description": meta.get("summary"),
        "tags": meta.get("tags", []),
        "compatible_agents": meta.get("compatible_agents", ["claude-code"]),
        "license": meta.get("license"),
        "path": skill_dir.relative_to(repo_root).as_posix(),
    }
    return front, meta, data


def build_registry_skill(skill_dir: Path, *, repo_root: Path) -> RegistrySkill:
    """Read a skill's frontmatter + catalog meta + checksum into a RegistrySkill."""
    _front, _meta, data = _skill_common(skill_dir, repo_root=repo_root)
    data["checksum"] = skill_checksum(skill_dir)
    return RegistrySkill.model_validate(data)


def build_catalog_skill(
    skill_dir: Path, *, repo_root: Path, updated_at: datetime | None = None
) -> CatalogSkill:
    """Read a skill into a CatalogSkill — the rich, web-facing entry.

    ``updated_at`` (the git commit date of the folder) is injected by the caller
    so this stays free of git/subprocess side effects.
    """
    front, meta, data = _skill_common(skill_dir, repo_root=repo_root)
    data.update(
        {
            "description_long": front.get("description"),
            "updated_at": updated_at,
            "when": meta.get("when"),
            "highlights": meta.get("highlights", []),
            "example": meta.get("example"),
        }
    )
    return CatalogSkill.model_validate(data)


def _skill_dirs(skills_dir: Path) -> list[Path]:
    """Every ``<skills_dir>/*/`` that contains a SKILL.md, sorted by path."""
    return [child for child in sorted(skills_dir.iterdir()) if (child / "SKILL.md").is_file()]


def _library(repo: str, commit: str, now: datetime | None) -> Library:
    """The ``library`` block shared by both manifests (spec §6.2)."""
    return Library(
        name="askill-library",
        repo=repo,
        generated_at=now or datetime.now(UTC),
        commit=commit,
    )


def build_registry(
    skills_dir: Path,
    *,
    repo: str,
    commit: str,
    repo_root: Path,
    now: datetime | None = None,
) -> Registry:
    """Assemble a validated Registry from every ``<skills_dir>/*/SKILL.md``."""
    skills = sorted(
        (build_registry_skill(child, repo_root=repo_root) for child in _skill_dirs(skills_dir)),
        key=lambda skill: skill.name,
    )
    return Registry(schema_version="1.0", library=_library(repo, commit, now), skills=skills)


def build_catalog(
    skills_dir: Path,
    *,
    repo: str,
    commit: str,
    repo_root: Path,
    now: datetime | None = None,
    updated_at_for: Callable[[Path], datetime | None] | None = None,
) -> Catalog:
    """Assemble a validated Catalog from every ``<skills_dir>/*/SKILL.md``.

    ``updated_at_for`` resolves a skill folder to its last-modified datetime
    (the generator passes a git-backed resolver); when ``None`` the per-skill
    ``updated_at`` is left unset.
    """
    skills = sorted(
        (
            build_catalog_skill(
                child,
                repo_root=repo_root,
                updated_at=updated_at_for(child) if updated_at_for is not None else None,
            )
            for child in _skill_dirs(skills_dir)
        ),
        key=lambda skill: skill.name,
    )
    return Catalog(schema_version="1.0", library=_library(repo, commit, now), skills=skills)


def build_marketplace_manifests(
    skill_names: list[str],
    *,
    marketplace_name: str,
    plugin_name: str,
    owner_name: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the ``(marketplace.json, plugin.json)`` dicts for the bundled plugin.

    The whole library ships as ONE Claude Code plugin (``plugin_name``) inside a
    marketplace (``marketplace_name``); ``/plugin install <plugin>@<marketplace>``
    installs every skill. ``version`` is intentionally omitted from plugin.json so
    Claude Code falls back to the git commit SHA — every push is a new version.

    Pure: returns plain dicts; the generator script writes them and copies the
    skill folders into ``plugins/<plugin_name>/skills/``.
    """
    listed = ", ".join(skill_names)
    plugin = {
        "name": plugin_name,
        "description": f"Reusable agent skills: {listed}.",
        "author": {"name": owner_name},
    }
    marketplace = {
        "name": marketplace_name,
        "owner": {"name": owner_name},
        "description": "Reusable agent skills, installable into Claude Code as a plugin.",
        "plugins": [
            {
                "name": plugin_name,
                "source": f"./plugins/{plugin_name}",
                "description": plugin["description"],
                "keywords": ["skills", "claude-code"],
            }
        ],
    }
    return marketplace, plugin
