"""``askill info <name>`` — registry detail plus local install status."""

from __future__ import annotations

import os
from pathlib import Path

import typer

from askill.commands import DEFAULT_REGISTRY
from askill.core.registry import load_registry
from askill.core.scope import find_project_root, resolve_scope
from askill.core.state import load_state
from askill.utils.errors import AskillError, UserError
from askill.utils.output import render_skill_info


def show_info(
    name: str = typer.Argument(..., help="Skill name."),
    registry: str = typer.Option(DEFAULT_REGISTRY, "--registry", help="Registry path or URL."),
    scope: str | None = typer.Option(None, "--scope", help="user | project."),
    json_mode: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Show details for one skill plus its local install status."""
    try:
        registry_data = load_registry(registry)
        skill = next((s for s in registry_data.skills if s.name == name), None)
        if skill is None:
            raise UserError(f"skill not found in registry: {name}")
        resolved = resolve_scope(scope, Path.cwd(), os.environ)
        root = find_project_root(Path.cwd(), os.environ) if resolved == "project" else None
        state = load_state(resolved, root)
        installed = state.skills.get(name) if state else None
        render_skill_info(skill, installed, json_mode)
    except AskillError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(exc.exit_code) from exc
