"""``askill info <name>`` — registry detail plus local install status."""

from __future__ import annotations

import typer

from askill.commands import DEFAULT_REGISTRY, cli_errors, resolve_target
from askill.core.registry import load_registry
from askill.core.state import load_state
from askill.utils.errors import UserError
from askill.utils.output import render_skill_info


def show_info(
    name: str = typer.Argument(..., help="Skill name."),
    registry: str = typer.Option(DEFAULT_REGISTRY, "--registry", help="Registry path or URL."),
    scope: str | None = typer.Option(None, "--scope", help="user | project."),
    json_mode: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Show details for one skill plus its local install status."""
    with cli_errors():
        registry_data = load_registry(registry)
        skill = next((s for s in registry_data.skills if s.name == name), None)
        if skill is None:
            raise UserError(f"skill not found in registry: {name}")
        resolved, root = resolve_target(scope)
        state = load_state(resolved, root)
        installed = state.skills.get(name) if state else None
        render_skill_info(skill, installed, json_mode)
