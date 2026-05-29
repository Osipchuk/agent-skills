"""askill command implementations (thin Typer layer over core)."""

from __future__ import annotations

import contextlib
import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

import typer

from askill.core.scope import find_project_root, resolve_scope
from askill.utils.errors import AskillError

# Default registry source: the published manifest on the main branch, so
# `askill install <name>` / `list` / `info` work with no --registry flag.
# The registry's library.commit is pinned, so installs stay reproducible even
# though the manifest is read from main. Local development overrides this with
# --registry ../registry.json (as do the tests).
DEFAULT_REGISTRY = "https://raw.githubusercontent.com/Osipchuk/agent-skills/main/registry.json"


def resolve_target(scope: str | None) -> tuple[Literal["user", "project"], Path | None]:
    """Resolve the install scope and project root from the live cwd/env.

    The command layer always works against the real process; the pure core
    resolvers take ``cwd``/``env`` explicitly, so this is the one place those live
    values are read instead of being repeated in every command.
    """
    resolved = resolve_scope(scope, Path.cwd(), os.environ)
    root = find_project_root(Path.cwd(), os.environ) if resolved == "project" else None
    return resolved, root


@contextlib.contextmanager
def cli_errors() -> Iterator[None]:
    """Map any ``AskillError`` raised in the block to a ``typer.Exit`` with its code.

    Replaces the identical try/except tail every Typer command used to carry.
    """
    try:
        yield
    except AskillError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(exc.exit_code) from exc


def report_action(
    json_mode: bool,
    status: str,
    name: str,
    version: str,
    scope: str,
    target: Path,
    *,
    skills_dir_created: bool | None = None,
) -> None:
    """Emit an install/uninstall result as one human line or a JSON object.

    ``skills_dir_created`` (install only): True when this install created the
    scope's ``.claude/skills/`` directory. Claude Code does not watch a top-level
    skills directory created mid-session, so the user must restart it to load the
    new skill. ``None`` omits the field entirely (e.g. for uninstall).
    """
    if json_mode:
        payload: dict[str, object] = {
            "status": status,
            "name": name,
            "version": version,
            "scope": scope,
            "path": str(target),
        }
        if skills_dir_created is not None:
            payload["skills_dir_created"] = skills_dir_created
        print(json.dumps(payload))
    else:
        typer.echo(f"{status}: {name} {version} ({scope}) -> {target}")
        if skills_dir_created:
            typer.echo(
                "note: created .claude/skills/ — restart Claude Code "
                "(or open a new session) to load newly installed skills"
            )
