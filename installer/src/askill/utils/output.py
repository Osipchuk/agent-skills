"""Render command results as human-friendly tables or machine JSON.

Commands call these helpers and never branch on ``--json`` themselves: the
``json_mode`` flag is the single switch and it lives here. JSON goes to stdout
verbatim (the machine-checked surface); human output uses a Rich table with a
fixed width so it is stable under pipes and tests.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from rich.console import Console
from rich.table import Table

from askill.core.models import InstalledSkill, RegistrySkill


def _console(console: Console | None) -> Console:
    return console or Console(width=120, no_color=True, highlight=False)


def render_skill_list(
    skills: Sequence[RegistrySkill],
    installed: dict[str, InstalledSkill] | None,
    json_mode: bool,
    console: Console | None = None,
) -> None:
    """Render a list of skills (with install status when available)."""
    installed = installed or {}
    if json_mode:
        payload = [
            {
                "name": skill.name,
                "version": skill.version,
                "description": skill.description,
                "tags": skill.tags,
                "installed": installed[skill.name].version if skill.name in installed else None,
            }
            for skill in skills
        ]
        print(json.dumps(payload, indent=2))
        return

    table = Table(title="Skills")
    table.add_column("Name")
    table.add_column("Version")
    table.add_column("Installed")
    table.add_column("Tags")
    for skill in skills:
        installed_version = installed[skill.name].version if skill.name in installed else "-"
        table.add_row(skill.name, skill.version, installed_version, ", ".join(skill.tags))
    _console(console).print(table)


def render_skill_info(
    skill: RegistrySkill,
    installed: InstalledSkill | None,
    json_mode: bool,
    console: Console | None = None,
) -> None:
    """Render full detail for a single skill plus its local install status."""
    if json_mode:
        payload = skill.model_dump(mode="json")
        payload["installed"] = installed.model_dump(mode="json") if installed else None
        print(json.dumps(payload, indent=2))
        return

    table = Table(title=skill.name, show_header=False)
    table.add_column("field")
    table.add_column("value")
    table.add_row("version", skill.version)
    table.add_row("description", skill.description)
    table.add_row("path", skill.path)
    table.add_row("tags", ", ".join(skill.tags))
    table.add_row("compatible_agents", ", ".join(skill.compatible_agents))
    table.add_row("installed", installed.version if installed else "no")
    _console(console).print(table)
