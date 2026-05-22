"""Install-scope resolution (spec §9).

Each function takes the world it needs as arguments (cwd, env, project_root)
rather than reading globals — that keeps them pure and testable.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Literal

_PROJECT_ENV = "CLAUDE_CODE_PROJECT_ROOT"


def resolve_scope(
    explicit: str | None,
    cwd: Path,
    env: Mapping[str, str],
) -> Literal["user", "project"]:
    """Resolve the install scope using the §9.1 precedence order.

    1. ``explicit`` if given (validated; anything else raises ``ValueError``).
    2. else "project" if ``cwd`` or an ancestor holds a ``.claude`` directory.
    3. else "project" if ``CLAUDE_CODE_PROJECT_ROOT`` is in ``env``.
    4. else "user".
    """
    if explicit is not None:
        if explicit == "user":
            return "user"
        if explicit == "project":
            return "project"
        raise ValueError(f"scope must be 'user' or 'project', got {explicit!r}")
    if _has_dot_claude_dir(cwd):
        return "project"
    if _PROJECT_ENV in env:
        return "project"
    return "user"


def target_dir(scope: str, name: str, project_root: Path | None = None) -> Path:
    """Directory a skill's files live in (§9.2): ``<skills>/<name>``."""
    return _scope_skills_dir(scope, project_root) / name


def installed_json_path(scope: str, project_root: Path | None = None) -> Path:
    """Per-scope state file (§9.3): ``<skills>/.installed.json``."""
    return _scope_skills_dir(scope, project_root) / ".installed.json"


def find_project_root(cwd: Path, env: Mapping[str, str]) -> Path | None:
    """The project root for project scope: the nearest ancestor of ``cwd`` that
    holds a ``.claude`` directory, else the ``CLAUDE_CODE_PROJECT_ROOT`` path,
    else ``None``."""
    for directory in (cwd, *cwd.parents):
        if (directory / ".claude").is_dir():
            return directory
    root = env.get(_PROJECT_ENV)
    return Path(root) if root else None


def _has_dot_claude_dir(cwd: Path) -> bool:
    """True if ``cwd`` or any ancestor contains a ``.claude`` directory."""
    return any((directory / ".claude").is_dir() for directory in (cwd, *cwd.parents))


def _scope_skills_dir(scope: str, project_root: Path | None) -> Path:
    """The ``.claude/skills`` directory for an already-resolved scope."""
    if scope == "user":
        return Path.home() / ".claude" / "skills"
    if scope == "project":
        if project_root is None:
            raise ValueError("project_root is required for project scope")
        return project_root / ".claude" / "skills"
    raise ValueError(f"scope must be 'user' or 'project', got {scope!r}")
