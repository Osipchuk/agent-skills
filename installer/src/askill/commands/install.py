"""``askill install <name>`` — install a skill into a scope (spec §8.3, §15)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import typer
from packaging.version import Version

from askill import __version__
from askill.commands import DEFAULT_REGISTRY, report_action
from askill.core.installer import fetch_and_place
from askill.core.models import InstalledSkill, InstalledState
from askill.core.registry import load_registry
from askill.core.scope import find_project_root, resolve_scope, target_dir
from askill.core.state import load_state, save_state
from askill.utils.errors import AskillError, ConflictError, UserError


def install(
    name: str = typer.Argument(..., help="Skill name to install."),
    registry: str = typer.Option(DEFAULT_REGISTRY, "--registry", help="Registry path or URL."),
    scope: str | None = typer.Option(None, "--scope", help="user | project."),
    force: bool = typer.Option(False, "--force", help="Reinstall / overwrite if present."),
    skip_existing: bool = typer.Option(False, "--skip-existing", help="No-op if installed."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would happen; write nothing."),
    no_checksum: bool = typer.Option(False, "--no-checksum", help="Skip checksum verification."),
    json_mode: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Install a skill from the registry into the resolved scope."""
    try:
        registry_data = load_registry(registry)
        skill = next((s for s in registry_data.skills if s.name == name), None)
        if skill is None:
            raise UserError(f"skill not found in registry: {name}")
        if skill.min_cli_version and Version(__version__) < Version(skill.min_cli_version):
            raise UserError(
                f"{name} requires askill >= {skill.min_cli_version} "
                f"(you have {__version__}); run 'askill self-update'"
            )

        resolved = resolve_scope(scope, Path.cwd(), os.environ)
        root = find_project_root(Path.cwd(), os.environ) if resolved == "project" else None
        target = target_dir(resolved, name, root)
        state = load_state(resolved, root)
        existing = state.skills.get(name) if state else None

        if existing and skip_existing:
            report_action(json_mode, "skipped", name, existing.version, resolved, target)
            return
        if not force:
            if existing and existing.version == skill.version:
                report_action(
                    json_mode, "already-installed", name, existing.version, resolved, target
                )
                return
            if existing:
                raise ConflictError(
                    f"{name} {existing.version} is installed; run 'askill update {name}' "
                    f"or use --force to install {skill.version}"
                )
            if target.exists():
                raise ConflictError(
                    f"{target} already exists but is not tracked; use --force to overwrite"
                )

        if dry_run:
            report_action(json_mode, "would-install", name, skill.version, resolved, target)
            return

        if no_checksum:
            typer.echo(f"warning: installing {name} without checksum verification", err=True)
        # Whether this install creates the scope's .claude/skills/ dir for the first time —
        # Claude Code won't watch a top-level skills dir created mid-session until restarted.
        skills_dir_created = not target.parent.exists()
        fetch_and_place(skill, registry_data.library, target, verify_checksum=not no_checksum)

        if state is None:
            state = InstalledState(
                schema_version="1.0", scope=resolved, registry_url=registry, skills={}
            )
        state.skills[name] = InstalledSkill(
            version=skill.version,
            installed_at=datetime.now(timezone.utc),
            source_commit=registry_data.library.commit,
            checksum=skill.checksum,
            path=str(target),
        )
        save_state(state, resolved, root)
        report_action(
            json_mode,
            "installed",
            name,
            skill.version,
            resolved,
            target,
            skills_dir_created=skills_dir_created,
        )
    except AskillError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(exc.exit_code) from exc
