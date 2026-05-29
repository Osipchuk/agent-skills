"""``askill wizard`` — interactive multi-select installer (TTY only).

A thin layer over the same install core as ``askill install``: pick skills from a
checklist, pick a scope, install. ``run_wizard`` is the Typer command; ``_wizard``
holds the logic so the bare-``askill`` TTY entrypoint in ``cli.py`` can call it
with defaults without going through Typer's option parsing.

Multi-install downloads the (whole-repo) archive ONCE and places every selected
skill from it, saves state after each success (so a later failure can't lose an
earlier install), and isolates per-skill errors into the summary.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import questionary
import typer
from rich.console import Console
from rich.table import Table

from askill.commands import DEFAULT_REGISTRY
from askill.core.installer import download_archive, extracted_archive, place_skill
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


def _installed_scopes(name: str, project_root: Path | None) -> list[str]:
    """Which scopes already have ``skills/<name>/`` on disk (truthful, scope-aware)."""
    scopes = []
    if (Path.home() / ".claude" / "skills" / name).is_dir():
        scopes.append("user")
    if project_root is not None and (project_root / ".claude" / "skills" / name).is_dir():
        scopes.append("project")
    return scopes


def _wizard(registry: str, scope: str | None, no_checksum: bool) -> None:
    console = Console()
    try:
        registry_data = load_registry(registry)
        project_root = find_project_root(Path.cwd(), os.environ)

        choices = []
        for skill in registry_data.skills:
            where = _installed_scopes(skill.name, project_root)
            marker = f"   (installed: {', '.join(where)})" if where else ""
            choices.append(
                questionary.Choice(
                    title=f"{skill.name} — {skill.description}{marker}", value=skill.name
                )
            )
        selected = questionary.checkbox("Select skills to install", choices=choices).ask()
        if not selected:
            console.print("Nothing selected.")
            return

        default_scope = "project" if project_root is not None else "user"
        chosen = (
            scope
            or questionary.select(
                "Install where?", choices=["user", "project"], default=default_scope
            ).ask()
        )
        if not chosen:
            console.print("Cancelled.")
            return

        resolved = resolve_scope(chosen, Path.cwd(), os.environ)
        root = project_root if resolved == "project" else None
        state = load_state(resolved, root) or InstalledState(
            schema_version="1.0", scope=resolved, registry_url=registry, skills={}
        )
        by_name = {skill.name: skill for skill in registry_data.skills}

        # Download the whole-repo archive ONCE, then place every selected skill from it.
        archive = download_archive(registry_data.library)
        results: list[tuple[str, str, str, str]] = []
        failure_codes: list[int] = []
        created_any = False
        with extracted_archive(archive) as extracted:
            for name in selected:
                skill = by_name[name]
                target = target_dir(resolved, name, root)
                created = not target.parent.exists()
                try:
                    place_skill(extracted, skill, target, verify_checksum=not no_checksum)
                except AskillError as exc:
                    results.append((name, skill.version, "failed", exc.message))
                    failure_codes.append(exc.exit_code)
                    continue
                state.skills[name] = InstalledSkill(
                    version=skill.version,
                    installed_at=datetime.now(UTC),
                    source_commit=registry_data.library.commit,
                    checksum=skill.checksum,
                    path=str(target),
                )
                save_state(state, resolved, root)  # incremental: a later failure can't lose this
                created_any = created_any or created
                results.append((name, skill.version, "installed", str(target)))

        _render_summary(console, results, resolved)
        if created_any:
            console.print(
                "[yellow]note[/]: created .claude/skills/ — restart Claude Code "
                "(or open a new session) to load newly installed skills"
            )
        if failure_codes:
            # Preserve the underlying failure's exit code so automation can still
            # distinguish a user error (1) from a transient/system failure (2,
            # e.g. checksum/network) or a conflict (3). On mixed failures, surface
            # the most severe code rather than collapsing everything to 1.
            raise typer.Exit(max(failure_codes))
    except AskillError as exc:
        console.print(f"[red]error[/]: {exc.message}")
        raise typer.Exit(exc.exit_code) from exc


def _render_summary(console: Console, results: list[tuple[str, str, str, str]], scope: str) -> None:
    table = Table(title=f"Installed into {scope} scope")
    table.add_column("Skill")
    table.add_column("Version")
    table.add_column("Result")
    for name, version, status, detail in results:
        # ``detail`` is the install path on success and the error message on failure.
        mark = f"[green]✓ {detail}[/]" if status == "installed" else f"[red]✗ {detail}[/]"
        table.add_row(name, version, mark)
    console.print(table)
