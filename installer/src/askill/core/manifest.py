"""Build a validated Registry manifest from skill folders (spec §6).

Pure assembly: read each skill's ``SKILL.md`` frontmatter, compute its §13.3
checksum, and construct the pydantic models (which do all the validation). No
file writes — the generator script (``scripts/generate_registry.py``) handles
I/O. The registry's ``description`` comes from the frontmatter's short
``summary`` key, since the long ``description`` (the agent's trigger text) can
exceed the registry's 1024-char limit.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from askill.core.checksum import skill_checksum
from askill.core.models import Library, Registry, RegistrySkill


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


def build_registry_skill(skill_dir: Path, *, repo_root: Path) -> RegistrySkill:
    """Read a skill folder's frontmatter + checksum into a validated RegistrySkill."""
    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.is_file():
        raise ValueError(f"skill directory {skill_dir} does not contain SKILL.md")
    front = parse_frontmatter(skill_md_path.read_text(encoding="utf-8"))
    path = skill_dir.relative_to(repo_root).as_posix()
    checksum = skill_checksum(skill_dir)
    data = {
        "name": front.get("name", skill_dir.name),
        "version": front.get("version"),
        "description": front.get("summary"),
        "tags": front.get("tags", []),
        "compatible_agents": front.get("compatible_agents", []),
        "license": front.get("license"),
        "path": path,
        "checksum": checksum,
    }
    return RegistrySkill.model_validate(data)


def build_registry(
    skills_dir: Path,
    *,
    repo: str,
    commit: str,
    repo_root: Path,
    now: datetime | None = None,
) -> Registry:
    """Assemble a validated Registry from every ``<skills_dir>/*/SKILL.md``."""
    skills = [
        build_registry_skill(child, repo_root=repo_root)
        for child in sorted(skills_dir.iterdir())
        if (child / "SKILL.md").is_file()
    ]
    skills.sort(key=lambda skill: skill.name)
    library = Library(
        name="askill-library",
        repo=repo,
        generated_at=now or datetime.now(timezone.utc),
        commit=commit,
    )
    return Registry(schema_version="1.0", library=library, skills=skills)
