# Contributing

Thanks for considering a contribution! There are two kinds of work here: **skills** (under `skills/`) and the **`askill` CLI** (under `installer/`).

## Adding or editing a skill

A skill is a folder `skills/<name>/` containing at least a `SKILL.md`:

```yaml
---
name: my-skill            # kebab-case, matches the folder name
description: <one paragraph — what it does AND when it should trigger>
---

# My Skill

Instructions for the agent…
```

Guidelines:

- **`name`** is kebab-case (`^[a-z][a-z0-9-]{2,63}$`) and matches the folder name.
- **`description`** is the text a host agent matches against to decide whether to activate the skill. Make it concrete: list the phrases and situations that should trigger it, plus explicit non-triggers ("Do not use for…").
- **Progressive disclosure**: keep `SKILL.md` focused on the workflow; put bulky templates in `references/` and helper scripts in `scripts/` (dependency-free where possible) and reference them by relative path.
- **No secrets** in skill files.

## Developing askill

```bash
cd installer
uv sync
uv run pytest                     # unit + integration tests
uv run ruff check . && uv run ruff format .
uv run mypy src/askill            # strict on the core/ package
```

Architecture:

- `src/askill/core/` — pure, deterministic, strictly-typed logic (models, registry loading, scope resolution, state, checksum, install). The only I/O is isolated behind functions that take their source as an argument.
- `src/askill/commands/` — thin Typer commands: parse arguments, call core, hand the result to `utils/output`.
- `utils/output.py` owns the human-vs-`--json` decision; commands never branch on it.

Please add tests for new behavior (unit for core, integration via Typer's `CliRunner` for commands) and keep `pytest`, `ruff`, and `mypy` green.

## Pull requests

- Keep skill changes and CLI changes in separate, focused PRs where possible.
- Describe what the change does and why.
