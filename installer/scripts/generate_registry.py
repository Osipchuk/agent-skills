"""Generate registry.json (and optionally registry.schema.json) from skills/.

Maintenance / CI script — *not* part of the ``askill`` CLI surface. Run from
``installer/``::

    uv run python scripts/generate_registry.py --commit "$(git -C .. rev-parse HEAD)" --schema

It reads every ``skills/<name>/SKILL.md``, computes the §13.3 checksum of each
folder, builds a validated ``Registry`` via :mod:`askill.core.manifest`, and
writes pretty JSON to the repo root. All validation lives in the pydantic
models, so a bad frontmatter (missing ``summary``, non-semver ``version``, …)
fails loudly here rather than shipping a broken manifest.

``registry.schema.json`` is emitted as a *sibling* artifact only — it is never
referenced from ``registry.json`` itself, because the models use
``extra="forbid"`` and would reject an unknown ``$schema`` key on load.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from askill.core.manifest import build_registry
from askill.core.models import Registry

DEFAULT_REPO = "https://github.com/Osipchuk/agent-skills"
# scripts/ -> installer/ -> <repo root>
REPO_ROOT = Path(__file__).resolve().parents[2]


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


def _write_json(path: Path, payload: object) -> None:
    """Write ``payload`` as pretty JSON (indent 2, trailing newline)."""
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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
    args = parser.parse_args(argv)

    repo_root: Path = args.repo_root.resolve()
    commit: str = args.commit or _git_head(repo_root)
    output: Path = args.output or repo_root / "registry.json"

    registry = build_registry(
        repo_root / "skills",
        repo=args.repo,
        commit=commit,
        repo_root=repo_root,
    )
    _write_json(output, registry.model_dump(mode="json", exclude_none=True))
    print(f"wrote {output} — {len(registry.skills)} skills, commit {commit[:12]}")

    if args.schema:
        schema_path = output.with_name("registry.schema.json")
        _write_json(schema_path, Registry.model_json_schema())
        print(f"wrote {schema_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
