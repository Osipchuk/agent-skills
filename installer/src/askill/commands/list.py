"""``askill list`` — show skills from the registry (optionally only installed)."""

from __future__ import annotations

import typer

from askill.commands import DEFAULT_REGISTRY, cli_errors, resolve_target
from askill.core.registry import load_registry
from askill.core.state import load_state
from askill.utils.output import render_skill_list


def list_skills(
    registry: str = typer.Option(DEFAULT_REGISTRY, "--registry", help="Registry path or URL."),
    installed: bool = typer.Option(False, "--installed", help="Only skills installed locally."),
    scope: str | None = typer.Option(None, "--scope", help="user | project."),
    tag: str | None = typer.Option(None, "--tag", help="Filter by tag."),
    json_mode: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """List skills available in the registry."""
    with cli_errors():
        registry_data = load_registry(registry)
        skills = [s for s in registry_data.skills if tag is None or tag in s.tags]
        installed_map = None
        if installed:
            resolved, root = resolve_target(scope)
            state = load_state(resolved, root)
            installed_map = state.skills if state else {}
            skills = [s for s in skills if s.name in installed_map]
        render_skill_list(skills, installed_map, json_mode)
