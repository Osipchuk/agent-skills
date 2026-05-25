"""askill command implementations (thin Typer layer over core)."""

from __future__ import annotations

import json
from pathlib import Path

import typer

# Default registry source: the published manifest on the main branch, so
# `askill install <name>` / `list` / `info` work with no --registry flag.
# The registry's library.commit is pinned, so installs stay reproducible even
# though the manifest is read from main. Local development overrides this with
# --registry ../registry.json (as do the tests).
DEFAULT_REGISTRY = "https://raw.githubusercontent.com/Osipchuk/agent-skills/main/registry.json"


def report_action(
    json_mode: bool, status: str, name: str, version: str, scope: str, target: Path
) -> None:
    """Emit an install/uninstall result as one human line or a JSON object."""
    if json_mode:
        payload = {
            "status": status,
            "name": name,
            "version": version,
            "scope": scope,
            "path": str(target),
        }
        print(json.dumps(payload))
    else:
        typer.echo(f"{status}: {name} {version} ({scope}) -> {target}")
