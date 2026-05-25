# One-command skill install — design

**Date:** 2026-05-25
**Status:** approved (pending written-spec review)

## Goal

Make installing a skill from this library a single command, matching the UX of
`npx skills@latest add <org>/<repo>` (the [mattpocock/skills](https://github.com/mattpocock/skills)
reference). Today installation requires cloning the repo, `cd installer`,
`uv sync`, and `uv run askill install … --registry ../registry.json --scope user`
— four steps and a mandatory flag. We want one command, in the terminal *or* via
a coding agent.

## Key insight

The install **engine is already done and is stronger than the reference's**:
[`installer/src/askill/core/installer.py`](../../../installer/src/askill/core/installer.py)
downloads the repo tarball at a pinned commit, locates `skills/<name>`, verifies
a sha256 checksum, and copies it into the target scope. The gap is purely
**delivery/bootstrap**, not the engine.

`uvx` (`uv tool run`) is the Python analog of `npx`: it fetches and runs a package
ephemerally. uv can install directly from a git repo with a subdirectory, so this
works **today, with no PyPI release**.

## Decisions

- **Distribution:** git-based (`uv` installs from `git+…#subdirectory=installer`).
  No PyPI release now. The package source is kept in a single variable so a later
  PyPI swap is a one-line change (git URL → `askill`).
- **`install.sh` behavior:** no argument → install the CLI persistently; one or
  more skill names → install each skill directly (one-shot).
- **Agent path:** a copy-paste prompt block in the README (no AGENTS.md, no
  meta-skill).
- **Scope:** skill installs default to `--scope user` (`~/.claude/skills/`).

## Package source (single source of truth)

```
git+https://github.com/Osipchuk/agent-skills#subdirectory=installer
```

The package is `askill` (hatchling, src-layout under `installer/`); its console
script is `askill` ([`installer/pyproject.toml`](../../../installer/pyproject.toml)).
`uv tool install` / `uvx --from` both accept the `#subdirectory=` fragment.

## Components

### 0. Default registry (core change)

[`installer/src/askill/commands/__init__.py`](../../../installer/src/askill/commands/__init__.py):

```python
DEFAULT_REGISTRY = "https://raw.githubusercontent.com/Osipchuk/agent-skills/main/registry.json"
```

(currently `"registry.json"`). Update the adjacent comment.

- Makes `askill install <name>` / `list` / `info` work with no `--registry`.
- Reproducible: the registry's `library.commit` is pinned, so pulling the
  registry from `main` still installs the archive at the fixed commit.
- Dev workflow unaffected — local runs and tests pass `--registry ../registry.json`
  explicitly. **Before editing, confirm no test asserts the old default value.**

### 1. `install.sh` (repo root, POSIX `sh`)

Served from `https://raw.githubusercontent.com/Osipchuk/agent-skills/main/install.sh`.

Single source-of-truth variable at the top:

```sh
PKG="git+https://github.com/Osipchuk/agent-skills#subdirectory=installer"
```

Logic:

1. **Bootstrap uv** — if `command -v uv` fails, install via
   `curl -LsSf https://astral.sh/uv/install.sh | sh`, then prepend `~/.local/bin`
   to `PATH` for the current script session (and source `"$HOME/.local/bin/env"`
   if present) so the following commands find `uv`.
2. **No arguments** → `uv tool install "$PKG"`; print a hint (`askill list`,
   `askill install <name>`).
3. **One or more names** → for each: `uvx --from "$PKG" askill install "$name" --scope user`.

Constraints: `#!/bin/sh`, `set -e`, no bashisms (`command -v`, `[ "$#" -eq 0 ]`,
`for name in "$@"`), friendly echo output. Must run correctly when piped to `sh`.

Usage:

```bash
# install the CLI:
curl -fsSL https://raw.githubusercontent.com/Osipchuk/agent-skills/main/install.sh | sh
# install a skill directly:
curl -fsSL https://raw.githubusercontent.com/Osipchuk/agent-skills/main/install.sh | sh -s -- learning-mode
```

### 2. Agent prompt (README block)

Copy-paste block telling an agent the exact command to run:

> **Install via your coding agent.** Tell Claude Code / Cursor / etc.:
> > *Install the `learning-mode` skill from the agent-skills library by running:*
> > `uvx --from "git+https://github.com/Osipchuk/agent-skills#subdirectory=installer" askill install learning-mode --scope user`
>
> The agent runs the command; the skill lands in `~/.claude/skills/`.

### 3. README updates

- New **Quick install** section at the top with the two `curl | sh` commands.
- **Install via your agent** subsection with the prompt block above.
- **Available skills** section — one brief line per skill (sourced from the
  registry `description`):
  - `article-translator` — translate long-form articles/prose between languages
    while preserving voice, structure, and formatting.
  - `learning-mode` — turn a Claude Code session into a learn-by-doing tutorial
    with a spaced-repetition review log.
  - `toxic-senior-reviewer` — code review in the voice of a blunt senior dev:
    sharp criticism only, curt approval when the code is actually good.
- Existing `git clone … uv sync …` instructions move under **From source /
  Development**.
- Roadmap: check off "One-line bootstrap (`curl … | sh`)".

## Testing

- `install.sh`: run `shellcheck` if available; manual smoke test in a clean
  directory (both no-arg and `-s -- learning-mode` forms).
- Core change: run the existing `pytest` suite to confirm nothing depended on the
  old default registry value.
- No new network-install integration tests.

## Non-goals (YAGNI)

- PyPI publish now (only keep the `PKG` variable swappable).
- Interactive skill picker / per-agent selection (the reference's prompts).
- Windows `.ps1` installer.
- `AGENTS.md` / `llms.txt` / a meta-skill for the agent path.

## Future (cheap follow-ups)

- Publish `askill` to PyPI → swap `PKG` to `askill`, giving
  `uvx askill install <name>` and `uv tool install askill`.
- Auto-generate the README skill list from the registry.
