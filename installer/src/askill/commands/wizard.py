"""``askill wizard`` — interactive multi-select installer (TTY only).

A thin layer over the same install core as ``askill install``: pick skills from a
checklist, pick a scope, install. ``run_wizard`` is the Typer command; ``_wizard``
holds the logic so the bare-``askill`` TTY entrypoint in ``cli.py`` can call it
with defaults without going through Typer's option parsing.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import questionary
import typer

from askill.commands import DEFAULT_REGISTRY
from askill.core.installer import fetch_and_place
from askill.core.models import InstalledSkill, InstalledState
from askill.core.registry import load_registry
from askill.core.scope import find_project_root, resolve_scope, target_dir
from askill.core.state import load_state, save_state
from askill.utils.errors import AskillError


def run_wizard(
    registry: str = typer.Option(DEFAULT_REGISTRY, "--registry", help="Registry path or URL."),
    scope: str | None = typer.Option(None, "--scope", help="user | project (else you're asked)."),
    no_checksum: bool = typer.Option(False, "--no-checksum", help="Skip checksum verification."),
) -> None:
    """Interactively choose skills and a scope, then install them."""
    _wizard(registry, scope, no_checksum)


def _wizard(registry: str, scope: str | None, no_checksum: bool) -> None:
    try:
        registry_data = load_registry(registry)

        # Default scope (from cwd) drives both the installed-status markers and the
        # default highlighted in the scope prompt.
        default_scope = resolve_scope(scope, Path.cwd(), os.environ)
        display_root = (
            find_project_root(Path.cwd(), os.environ) if default_scope == "project" else None
        )
        display_state = load_state(default_scope, display_root)
        installed = display_state.skills if display_state else {}

        choices = [
            questionary.Choice(
                title=f"{skill.name} — {skill.description}"
                + (
                    f"  [installed {installed[skill.name].version}]"
                    if skill.name in installed
                    else ""
                ),
                value=skill.name,
            )
            for skill in registry_data.skills
        ]
        selected = questionary.checkbox("Select skills to install", choices=choices).ask()
        if not selected:
            typer.echo("Nothing selected.")
            return

        chosen = (
            scope
            or questionary.select(
                "Install where?", choices=["user", "project"], default=default_scope
            ).ask()
        )
        if not chosen:
            typer.echo("Cancelled.")
            return

        resolved = resolve_scope(chosen, Path.cwd(), os.environ)
        root = find_project_root(Path.cwd(), os.environ) if resolved == "project" else None
        state = load_state(resolved, root) or InstalledState(
            schema_version="1.0", scope=resolved, registry_url=registry, skills={}
        )
        by_name = {skill.name: skill for skill in registry_data.skills}

        created_any = False
        for name in selected:
            skill = by_name[name]
            target = target_dir(resolved, name, root)
            if not target.parent.exists():
                created_any = True
            fetch_and_place(skill, registry_data.library, target, verify_checksum=not no_checksum)
            state.skills[name] = InstalledSkill(
                version=skill.version,
                installed_at=datetime.now(timezone.utc),
                source_commit=registry_data.library.commit,
                checksum=skill.checksum,
                path=str(target),
            )
            typer.echo(f"installed: {name} {skill.version} ({resolved}) -> {target}")

        save_state(state, resolved, root)
        if created_any:
            typer.echo(
                "note: created .claude/skills/ — restart Claude Code "
                "(or open a new session) to load newly installed skills"
            )
    except AskillError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(exc.exit_code) from exc
