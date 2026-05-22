"""``askill uninstall <name>`` — remove an installed skill (spec §8.3)."""

from __future__ import annotations

import os
from pathlib import Path

import typer

from askill.commands import report_action
from askill.core.filesystem import remove_tree
from askill.core.scope import find_project_root, resolve_scope, target_dir
from askill.core.state import load_state, save_state
from askill.utils.errors import AskillError, UserError


def uninstall(
    name: str = typer.Argument(..., help="Skill name to uninstall."),
    scope: str | None = typer.Option(None, "--scope", help="user | project."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would happen; write nothing."),
    json_mode: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Remove an installed skill and drop it from installed.json."""
    try:
        resolved = resolve_scope(scope, Path.cwd(), os.environ)
        root = find_project_root(Path.cwd(), os.environ) if resolved == "project" else None
        state = load_state(resolved, root)
        existing = state.skills.get(name) if state else None
        if state is None or existing is None:
            raise UserError(f"{name} is not installed ({resolved} scope)")
        target = target_dir(resolved, name, root)
        if dry_run:
            report_action(json_mode, "would-uninstall", name, existing.version, resolved, target)
            return
        remove_tree(target)
        del state.skills[name]
        save_state(state, resolved, root)
        report_action(json_mode, "uninstalled", name, existing.version, resolved, target)
    except AskillError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(exc.exit_code) from exc
