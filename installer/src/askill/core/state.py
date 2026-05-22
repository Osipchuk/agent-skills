"""Read the installed.json state file (spec §10).

Read-only in this sub-project: we locate and parse state, but never write it
(atomic writes, backups, and recreation arrive with the install commands). An
absent file is a normal "nothing installed yet" → ``None``; a present-but-broken
file is surfaced as a ``StateError`` rather than silently ignored.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from askill.core.filesystem import atomic_write_text
from askill.core.models import InstalledState
from askill.core.scope import installed_json_path
from askill.utils.errors import StateError


def load_state_from_path(path: Path) -> InstalledState | None:
    """Load and validate an installed.json file; ``None`` if it does not exist."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StateError(f"installed state is not valid JSON ({path}): {exc}") from exc
    try:
        return InstalledState.model_validate(data)
    except ValidationError as exc:
        raise StateError(f"installed state failed validation ({path}):\n{exc}") from exc


def load_state(scope: str, project_root: Path | None = None) -> InstalledState | None:
    """Load installed.json for a resolved scope (``None`` when not present)."""
    return load_state_from_path(installed_json_path(scope, project_root))


def write_state(state: InstalledState, path: Path) -> None:
    """Atomically serialise ``state`` to ``path`` as JSON (spec §10.2)."""
    atomic_write_text(path, state.model_dump_json(indent=2))


def save_state(state: InstalledState, scope: str, project_root: Path | None = None) -> None:
    """Write ``state`` to the installed.json location for a resolved scope."""
    write_state(state, installed_json_path(scope, project_root))
