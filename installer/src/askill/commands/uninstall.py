"""``askill uninstall <name>`` — remove an installed skill (spec §8.3)."""

from __future__ import annotations

import typer

from askill.commands import cli_errors, report_action, resolve_target
from askill.core.filesystem import remove_tree
from askill.core.scope import target_dir
from askill.core.state import load_state, save_state
from askill.utils.errors import UserError


def uninstall(
    name: str = typer.Argument(..., help="Skill name to uninstall."),
    scope: str | None = typer.Option(None, "--scope", help="user | project."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would happen; write nothing."),
    json_mode: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Remove an installed skill and drop it from installed.json."""
    with cli_errors():
        resolved, root = resolve_target(scope)
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
