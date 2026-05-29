# CLAUDE.md

Guidance for Claude Code working in this repo: **how to work here** first, then **how the project is built**. The working principles are adapted from Andrej Karpathy's skills CLAUDE.md ([multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)); merge with anything more specific a task demands.

**Tradeoff:** these principles bias toward caution over speed. For a trivial task, use judgment.

## Working principles

### 1. Think before coding
Don't assume, don't hide confusion, surface tradeoffs. State your assumptions; if several readings are possible, present them instead of silently picking one. If a simpler path exists, say so. If something is unclear, stop and name it — a clarifying question before the work beats a rewrite after it.

### 2. Simplicity first
Minimum code that solves the problem, nothing speculative. No abstraction for a single caller, no configurability nobody asked for, no error handling for impossible states. This repo already has a small, clean deterministic core — match that bar, don't gold-plate past it. If you wrote 200 lines and 50 would do, rewrite it.

### 3. Surgical changes
Touch only what the task needs. Don't "improve" adjacent code, comments, or formatting; don't refactor what isn't broken; match the surrounding style even if you'd write it differently. Remove only the imports/vars/functions *your* change orphaned — flag pre-existing dead code, don't delete it unasked. Every changed line should trace to the request.

### 4. Verify, don't assert
Turn the task into a check and loop until it passes. "Fix the bug" → write the failing test first, then make it pass. Before claiming done, actually run it: `uv run pytest && uv run ruff check . && uv run mypy src` from `installer/`. Generated artifacts (below) have their own check — regenerate and diff, don't eyeball.

Two repo-specific habits fall out of these:
- **The deterministic Core is the product.** Keep logic pure in `core/`; isolate side effects (I/O, network, prompts) at the edges. `cli.py`/`commands/` only parse args and call Core; the human-vs-JSON decision lives in `utils/output.py`, not in commands.
- **Generated files are never hand-edited.** Change the generator, run it, commit the output — see "Generated artifacts" below.

## What this repo is

A library of reusable **skills** for AI agents (Claude Code first), plus a CLI installer (`askill`), a generated registry, and a Claude Code plugin marketplace.

1. [skills-library-spec.md](skills-library-spec.md) — the authoritative design doc (v1.1, **in Russian**) for the `askill` CLI, `registry.json` manifest, and repo layout. Source of truth for the *target* system; mirror its terminology when discussing the design.
2. Example skills under [skills/](skills/): [learning-mode](skills/learning-mode/), [article-translator](skills/article-translator/), [toxic-senior-reviewer](skills/toxic-senior-reviewer/).
3. [installer/](installer/) — the `askill` package (uv, src-layout). **Built:** the deterministic core (pydantic models, registry loading from path/URL, scope resolution, read+write state, §13.3 checksum, archive install), the commands `list`/`info`/`install`/`uninstall`/`wizard`, registry/catalog + marketplace generation with CI, and the `install.sh` bootstrap. **Not yet built:** `update`/`outdated`/`search`/`validate`/`self-update`.
4. [registry.json](registry.json) (lean installer manifest) + [catalog.json](catalog.json) (rich web/presentation manifest) — auto-generated from the skills and committed by CI on merge to `main`.

## Authoring skills (what the examples actually do)

Each skill is split across two files (full guide: [docs/skill-authoring.md](docs/skill-authoring.md), scaffolds in [templates/](templates/)):

- `skills/<name>/SKILL.md` — **installed to the user, checksummed.** Frontmatter is the real Claude Code format plus a pinned version — exactly three keys:

  ```yaml
  ---
  name: learning-mode          # kebab-case; matches the folder name
  description: <one long paragraph — what it does AND when to trigger it>
  version: 0.1.0               # strict semver
  ---
  ```

  The `description` does the heavy lifting: long and trigger-oriented (the phrases/situations that should activate the skill, plus explicit non-triggers — "Do not use for…"), because that text is what a host agent matches against. Keep presentation metadata OUT of here.

- `catalog/<name>.yaml` — **never installed** (it lives outside `skills/`, so the installer doesn't copy it and it doesn't affect the checksum). Holds all presentation/catalog metadata: `summary` (the short "dek" → registry `description`), `tags`, `compatible_agents`, `license`, and the web-detail fields `when`, `highlights`, `example`.

Skills use **progressive disclosure**: `SKILL.md` holds the workflow and instructions; bulky templates and helper scripts live in `references/` and `scripts/` subfolders and are pulled in on demand (see `skills/learning-mode/SKILL.md`, which references `scripts/list_due.py` and `references/*-template.md`). Helper scripts should be stdlib-only / dependency-free where possible (as `list_due.py` is).

Editing a skill changes its checksum (it's the SHA-256 of `skills/<name>/`); editing its `catalog/<name>.yaml` does not. After either, regenerate the manifests.

### Layout

Skills follow the spec's §5 layout — `skills/<name>/` with `scripts/`+`references/` subdirs — and `registry.json`'s `path`/`entry` resolve to real files. The generator reads `SKILL.md` (name/description/version) and `catalog/<name>.yaml` (everything else). When adding or fixing a skill, keep its internal path references consistent with where its files actually live. There is **no duplicated skill tree**: the repo root *is* the Claude Code plugin (`source: "."`), so `skills/` is both the canonical source and the plugin's skills dir.

## Target architecture (from the spec)

The deterministic core, scope/state, checksum + archive install, the `list`/`info`/`install`/`uninstall`/`wizard` commands, and the marketplace are built; `update`/`search`/etc. are still planned.

- **CLI `askill`** — two layers: a **Core** (`src/askill/core/`, `commands/`) that is non-interactive, deterministic, and `--json`-able, and a **Wizard** (TTY-only) that is a thin wrapper *over* Core.
- **`registry.json` + `catalog.json`** at the repo root: auto-generated, validated against `registry.schema.json` / `catalog.schema.json`. `askill` installs from `registry.json`; web clients render `catalog.json` over HTTPS — see [docs/blog-catalog-integration.md](docs/blog-catalog-integration.md).
- **Clients never parse skill folders directly** — installers read `registry.json`; GUIs/IDEs/web read `catalog.json`, or call `askill … --json`.
- **Two install tracks.** Humans: `install.sh` (uvx/`uv tool install` from git). The agent path: the Claude Code plugin marketplace (`.claude-plugin/marketplace.json` → `/plugin install skills@askill`), which is the trusted route when `curl|sh` / `uvx` are blocked by Claude Code permissions.
- **Archive install** resolves a skill by its manifest `path` joined onto the GitHub tarball's single top-level prefix — never by searching the tree for a folder named `<name>` (`core/installer.py`).
- **Scope resolution** (install target): explicit `--scope` → `.claude/` in cwd → project-root env var → default `user`. `user` → `~/.claude/skills/`, `project` → `<root>/.claude/skills/`; each scope keeps its own `.installed.json`.
- **Exit codes:** `0` success, `1` user error, `2` system error, `3` conflict.

## Generated artifacts — never hand-edited

`registry.json`, `catalog.json`, `registry.schema.json`, `catalog.schema.json`, and `.claude-plugin/{marketplace,plugin}.json` are produced by [installer/scripts/generate_registry.py](installer/scripts/generate_registry.py) (from each `SKILL.md` + `catalog/<name>.yaml`), committed by CI on merge to `main`, and marked `linguist-generated` in [.gitattributes](.gitattributes). To change any of them, edit the generator and run it — don't touch the output:

```bash
cd installer
uv run python scripts/generate_registry.py --commit "$(git -C .. rev-parse HEAD)" --schema
```

## Tooling

Spec §4.1: Python 3.12+, **uv** (packaging), **Typer** (CLI), **Rich**, **questionary** (wizard), **pydantic v2** (models in `core/models.py`), **httpx**, **PyYAML**, **ruff** (lint+format), **mypy** (strict on `core/`), **pytest** + **pytest-httpx**. Commands, run from `installer/`:

```bash
uv sync
uv run pytest                 # uv run pytest tests/unit/test_x.py::test_y for one test
uv run ruff check . && uv run ruff format .
uv run mypy src
```

Integration tests use Typer's `CliRunner` against a mocked HTTP registry; core modules target >80% coverage.
