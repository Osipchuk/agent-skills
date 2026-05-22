"""askill command implementations (thin Typer layer over core)."""

from __future__ import annotations

import json
from pathlib import Path

import typer

# Default registry source. In the distribution sub-project this becomes the
# GitHub raw URL; for now it's a cwd-relative path that manual runs and tests
# override with --registry.
DEFAULT_REGISTRY = "registry.json"


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
