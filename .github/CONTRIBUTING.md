# Contributing

Thanks for considering a contribution! There are two kinds of work here: **skills** (under `skills/`) and the **`askill` CLI** (under `installer/`).

## Adding or editing a skill

A skill is split across **two files** (full guide: [docs/skill-authoring.md](../docs/skill-authoring.md), copy-paste scaffolds in [templates/](../templates/)):

- `skills/<name>/SKILL.md` — installed to the user and checksummed. Frontmatter has **exactly three keys**:

  ```yaml
  ---
  name: my-skill            # kebab-case, matches the folder name
  description: <one trigger-oriented paragraph, ≤1024 chars>
  version: 0.1.0            # strict semver MAJOR.MINOR.PATCH
  ---
  ```

- `catalog/<name>.yaml` — never installed; holds all presentation metadata (`summary`, `tags`, `compatible_agents`, `license`, `when`, `highlights`, `example`).

Guidelines:

- **`name`** is kebab-case (`^[a-z][a-z0-9-]{2,63}$`) and matches both the folder name and the catalog filename.
- **`description`** is the text a host agent matches against to decide whether to activate the skill. Make it concrete: list the phrases and situations that should trigger it, plus explicit non-triggers ("Do not use for…"). **Hard cap: 1024 characters** (the agent skills spec limit; the generator enforces it) — spend the budget on triggers, not on retelling the workflow.
- **`summary`** (in the catalog yaml) is the short, single-line blurb shown in the registry, in `askill list`/`info`, and in the README skills list. One sentence.
- **`version`** is strict semver; bump it whenever the skill folder's content changes (the checksum changes with it).
- **`tags`** are kebab-case (≤10) and should reuse the existing tag vocabulary; **`compatible_agents`** must include `claude-code`.
- **Progressive disclosure**: keep `SKILL.md` focused on the workflow; put bulky templates in `references/` and helper scripts in `scripts/` (dependency-free where possible) and reference them by relative path.
- **Mutable team data does not live in the skill folder** — installed files are checksummed and overwritten on update. Keep user-editable state in the target project (all under `.claude/` — `.claude/learning/`, `.claude/scars.md`, `.claude/onboard/topics.yaml`, `.claude/adr/config.yaml`) and ship only a template in `references/`.
- **No secrets** in skill files.

You do **not** edit `manifest/registry.json`, `manifest/catalog.json`, `.claude-plugin/*`, or the README "Available skills" block by hand — they are regenerated from the two files above by CI on merge to `main` (and locally via `installer/scripts/generate_registry.py`). CI fails a PR whose generated artifacts are stale: after changing a skill, run from `installer/`:

```bash
uv run python scripts/generate_registry.py --commit "$(git -C .. rev-parse HEAD)" --schema
```

### Eval suites

A skill's behaviour is testable: `evals/<name>/suite.yaml` declares which prompts should (and should not) activate it, plus compliance scenarios that check the agent follows its rules. Suites live outside `skills/`, so editing one never changes a skill's checksum. Full format: [docs/skill-evals-spec.md](../docs/skill-evals-spec.md).

Static validation runs on every PR and needs no API key:

```bash
cd installer
uv run python scripts/run_evals.py --validate          # every suite
uv run python scripts/run_evals.py --validate --strict # what CI runs
```

`--strict` turns version drift into a failure: **if you change a skill, re-run its suite and bump `version_tested`**, or CI blocks the PR. Skills with no suite yet are reported as `info` and do not fail the build.

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
