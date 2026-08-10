"""Generate registry.json + catalog.json (and their schemas) from skills/.

Maintenance / CI script — *not* part of the ``askill`` CLI surface. Run from
``installer/``::

    uv run python scripts/generate_registry.py --commit "$(git -C .. rev-parse HEAD)" --schema

It reads every ``skills/<name>/SKILL.md`` plus its sibling
``catalog/<name>.yaml``, computes the §13.3 checksum of each folder, builds a
validated ``Registry`` and ``Catalog`` via :mod:`askill.core.manifest`, and
writes pretty JSON under ``manifest/``. All validation lives in the pydantic
models, so a bad input (missing ``catalog/<name>.yaml``, missing ``summary``,
non-semver ``version``, …) fails loudly here rather than shipping a broken
manifest.

Artifacts produced:
  - ``registry.json``  — the lean installer manifest (what ``askill`` consumes).
  - ``catalog.json``   — the rich, presentation-oriented manifest a web client
                         (e.g. a Skills Library page) consumes. Carries the long
                         description, ``when``/``highlights``/``example``, and a
                         git-derived per-skill ``updated_at``.
  - ``.claude-plugin/{marketplace,plugin}.json`` — the bundled Claude Code plugin.
  - the README "Available skills" block (between the ``available-skills`` markers).

``--check`` writes nothing and exits 1 if any committed artifact no longer
matches ``skills/`` + ``catalog/`` (ignoring the volatile ``generated_at`` /
``commit`` / ``updated_at`` fields) — CI runs this on every PR.

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

from askill.core.manifest import (
    build_catalog,
    build_marketplace_manifests,
    build_registry,
    readme_skills_section,
    splice_generated_block,
)
from askill.core.models import Catalog, Registry

DEFAULT_REPO = "https://github.com/Osipchuk/agent-skills"
# scripts/ -> installer/ -> <repo root>
REPO_ROOT = Path(__file__).resolve().parents[2]

# README block rewritten on every run so "Available skills" can never go stale.
README_SKILLS_START = "<!-- available-skills:start -->"
README_SKILLS_END = "<!-- available-skills:end -->"

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


def _comparable(payload: object, *, normalize: bool) -> object:
    """A deep copy ready for equality checks; ``normalize`` drops the volatile
    fields (``library.generated_at``/``commit``, per-skill ``updated_at``) that
    legitimately differ between a contributor's run and a CI re-run."""
    data = json.loads(json.dumps(payload))
    if not normalize or not isinstance(data, dict):
        return data
    library = data.get("library")
    if isinstance(library, dict):
        library.pop("generated_at", None)
        library.pop("commit", None)
    skills = data.get("skills")
    if isinstance(skills, list):
        for skill in skills:
            if isinstance(skill, dict):
                skill.pop("updated_at", None)
    return data


def _check_json(path: Path, payload: object, *, normalize: bool) -> str | None:
    """Return a problem line when ``path`` is missing or stale, else None."""
    if not path.is_file():
        return f"{path}: missing"
    committed = json.loads(path.read_text(encoding="utf-8"))
    if _comparable(committed, normalize=normalize) != _comparable(payload, normalize=normalize):
        return f"{path}: stale (does not match skills/ + catalog/)"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate registry.json from skills/.")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="library repo URL")
    parser.add_argument(
        "--commit", default=None, help="commit SHA the archive is pinned to (default: git HEAD)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="output path (default: <repo-root>/manifest/registry.json)",
    )
    parser.add_argument(
        "--repo-root", type=Path, default=REPO_ROOT, help="repo root holding skills/ (default: ..)"
    )
    parser.add_argument(
        "--schema", action="store_true", help="also write registry.schema.json next to the output"
    )
    parser.add_argument("--owner", default=DEFAULT_OWNER, help="marketplace/plugin owner name")
    parser.add_argument(
        "--check",
        action="store_true",
        help="write nothing; exit 1 if any committed artifact is stale (CI guard)",
    )
    args = parser.parse_args(argv)

    repo_root: Path = args.repo_root.resolve()
    commit: str = args.commit or _git_head(repo_root)
    # Generated manifests live under manifest/ so the repo root stays uncluttered.
    # catalog.json and the *.schema.json siblings are written next to this output
    # (via Path.with_name), so they all land in the same manifest/ directory.
    output: Path = args.output or repo_root / "manifest" / "registry.json"

    skills_dir = repo_root / "skills"

    registry = build_registry(
        skills_dir,
        repo=args.repo,
        commit=commit,
        repo_root=repo_root,
    )

    def _updated_at(skill_dir: Path) -> datetime | None:
        return _git_last_commit_dt(repo_root, skill_dir.relative_to(repo_root).as_posix())

    catalog = build_catalog(
        skills_dir,
        repo=args.repo,
        commit=commit,
        repo_root=repo_root,
        updated_at_for=_updated_at,
    )
    marketplace, plugin = build_marketplace_manifests(
        [skill.name for skill in registry.skills],
        marketplace_name=MARKETPLACE_NAME,
        plugin_name=PLUGIN_NAME,
        owner_name=args.owner,
    )

    catalog_output = output.with_name("catalog.json")
    claude_plugin = repo_root / ".claude-plugin"
    # (path, payload, normalize-volatile-fields-when-checking)
    artifacts: list[tuple[Path, object, bool]] = [
        (output, registry.model_dump(mode="json", exclude_none=True), True),
        (catalog_output, catalog.model_dump(mode="json", exclude_none=True), True),
        (claude_plugin / "plugin.json", plugin, False),
        (claude_plugin / "marketplace.json", marketplace, False),
    ]
    if args.schema:
        artifacts += [
            (output.with_name("registry.schema.json"), Registry.model_json_schema(), False),
            (output.with_name("catalog.schema.json"), Catalog.model_json_schema(), False),
        ]

    readme_path = repo_root / "README.md"
    readme_text = readme_path.read_text(encoding="utf-8")
    readme_spliced = splice_generated_block(
        readme_text,
        README_SKILLS_START,
        README_SKILLS_END,
        readme_skills_section(catalog.skills),
    )

    if args.check:
        problems = [
            problem
            for path, payload, normalize in artifacts
            if (problem := _check_json(path, payload, normalize=normalize))
        ]
        if readme_spliced != readme_text:
            problems.append(f"{readme_path}: 'Available skills' block is stale")
        if problems:
            print("generated artifacts are out of date — regenerate and commit:", file=sys.stderr)
            for problem in problems:
                print(f"  - {problem}", file=sys.stderr)
            return 1
        print(f"check OK — {len(artifacts)} artifacts + README match skills/ + catalog/")
        return 0

    for path, payload, _normalize in artifacts:
        _write_json(path, payload)
        print(f"wrote {path}")
    # Any legacy plugins/ mirror from the old layout is removed; the repo root
    # *is* the plugin (source: "."), so there is no second skill tree to drift.
    shutil.rmtree(repo_root / "plugins", ignore_errors=True)
    readme_path.write_text(readme_spliced, encoding="utf-8")
    print(f"updated {readme_path} — {len(catalog.skills)} skills, commit {commit[:12]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
