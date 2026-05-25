"""Generate registry.json + catalog.json (and their schemas) from skills/.

Maintenance / CI script — *not* part of the ``askill`` CLI surface. Run from
``installer/``::

    uv run python scripts/generate_registry.py --commit "$(git -C .. rev-parse HEAD)" --schema

It reads every ``skills/<name>/SKILL.md`` plus its sibling
``catalog/<name>.yaml``, computes the §13.3 checksum of each folder, builds a
validated ``Registry`` and ``Catalog`` via :mod:`askill.core.manifest`, and
writes pretty JSON to the repo root. All validation lives in the pydantic
models, so a bad input (missing ``catalog/<name>.yaml``, missing ``summary``,
non-semver ``version``, …) fails loudly here rather than shipping a broken
manifest.

Two artifacts are produced:
  - ``registry.json``  — the lean installer manifest (what ``askill`` consumes).
  - ``catalog.json``   — the rich, presentation-oriented manifest a web client
                         (e.g. a Skills Library page) consumes. Carries the long
                         description, ``when``/``highlights``/``example``, and a
                         git-derived per-skill ``updated_at``.

The ``*.schema.json`` files are emitted as *sibling* artifacts only — they are
never referenced from the manifests themselves, because the models use
``extra="forbid"`` and would reject an unknown ``$schema`` key on load.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from askill.core.manifest import build_catalog, build_marketplace_manifests, build_registry
from askill.core.models import Catalog, Registry

DEFAULT_REPO = "https://github.com/Osipchuk/agent-skills"
# scripts/ -> installer/ -> <repo root>
REPO_ROOT = Path(__file__).resolve().parents[2]

# Claude Code plugin marketplace: the whole library ships as one bundled plugin.
# "agent-skills" is a reserved marketplace name, so the marketplace is "askill".
MARKETPLACE_NAME = "askill"
PLUGIN_NAME = "skills"
DEFAULT_OWNER = "Evgenii Osipchuk"


def _git_head(repo_root: Path) -> str:
    """Return the current ``HEAD`` SHA of the repo at ``repo_root``."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _git_last_commit_dt(repo_root: Path, rel_path: str) -> datetime | None:
    """Datetime of the last commit that touched ``rel_path`` (None if untracked).

    Uses ``%cI`` (strict-ISO committer date). Needs full git history — in CI,
    check out with ``fetch-depth: 0`` or every skill collapses to the same date.
    """
    result = subprocess.run(
        ["git", "log", "-1", "--format=%cI", "--", rel_path],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    stamp = result.stdout.strip()
    return datetime.fromisoformat(stamp) if stamp else None


def _write_json(path: Path, payload: object) -> None:
    """Write ``payload`` as pretty JSON (indent 2, trailing newline)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_marketplace(repo_root: Path, skill_names: list[str], owner: str) -> None:
    """Emit the Claude Code plugin marketplace: ``.claude-plugin/marketplace.json``
    plus the bundled plugin under ``plugins/<PLUGIN_NAME>/`` with every skill copied
    in (plugins are copied to a cache on install and can't reference files outside
    their dir, so the skills must live inside the plugin)."""
    marketplace, plugin = build_marketplace_manifests(
        skill_names,
        marketplace_name=MARKETPLACE_NAME,
        plugin_name=PLUGIN_NAME,
        owner_name=owner,
    )
    plugin_root = repo_root / "plugins" / PLUGIN_NAME

    # Re-copy the skill folders fresh so removals/renames don't leave stragglers.
    plugin_skills = plugin_root / "skills"
    shutil.rmtree(plugin_skills, ignore_errors=True)
    for name in skill_names:
        shutil.copytree(repo_root / "skills" / name, plugin_skills / name)

    _write_json(plugin_root / ".claude-plugin" / "plugin.json", plugin)
    _write_json(repo_root / ".claude-plugin" / "marketplace.json", marketplace)
    print(
        f"wrote marketplace '{MARKETPLACE_NAME}' + plugin '{PLUGIN_NAME}' "
        f"({len(skill_names)} skills)"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate registry.json from skills/.")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="library repo URL")
    parser.add_argument(
        "--commit", default=None, help="commit SHA the archive is pinned to (default: git HEAD)"
    )
    parser.add_argument(
        "--output", type=Path, default=None, help="output path (default: <repo-root>/registry.json)"
    )
    parser.add_argument(
        "--repo-root", type=Path, default=REPO_ROOT, help="repo root holding skills/ (default: ..)"
    )
    parser.add_argument(
        "--schema", action="store_true", help="also write registry.schema.json next to the output"
    )
    parser.add_argument("--owner", default=DEFAULT_OWNER, help="marketplace/plugin owner name")
    args = parser.parse_args(argv)

    repo_root: Path = args.repo_root.resolve()
    commit: str = args.commit or _git_head(repo_root)
    output: Path = args.output or repo_root / "registry.json"

    skills_dir = repo_root / "skills"

    registry = build_registry(
        skills_dir,
        repo=args.repo,
        commit=commit,
        repo_root=repo_root,
    )
    _write_json(output, registry.model_dump(mode="json", exclude_none=True))
    print(f"wrote {output} — {len(registry.skills)} skills, commit {commit[:12]}")

    def _updated_at(skill_dir: Path) -> datetime | None:
        return _git_last_commit_dt(repo_root, skill_dir.relative_to(repo_root).as_posix())

    catalog = build_catalog(
        skills_dir,
        repo=args.repo,
        commit=commit,
        repo_root=repo_root,
        updated_at_for=_updated_at,
    )
    catalog_output = output.with_name("catalog.json")
    _write_json(catalog_output, catalog.model_dump(mode="json", exclude_none=True))
    print(f"wrote {catalog_output} — {len(catalog.skills)} skills")

    _write_marketplace(repo_root, [skill.name for skill in registry.skills], args.owner)

    if args.schema:
        schema_path = output.with_name("registry.schema.json")
        _write_json(schema_path, Registry.model_json_schema())
        print(f"wrote {schema_path}")

        catalog_schema_path = output.with_name("catalog.schema.json")
        _write_json(catalog_schema_path, Catalog.model_json_schema())
        print(f"wrote {catalog_schema_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
