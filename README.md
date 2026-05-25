# agent-skills

A library of reusable **skills** for AI coding agents — plus **`askill`**, a small CLI that installs them into your agent's environment.

A *skill* is a self-contained folder (a `SKILL.md` plus optional scripts and references) that teaches an agent a repeatable workflow. This repo collects skills under [`skills/`](skills/), describes them in a manifest ([`registry.json`](registry.json)), and ships an installer so any agent — Claude Code first — can pull a skill into `~/.claude/skills/` with one command.

> **Status: early, under active development.** The `askill` core and the `list` / `info` / `install` / `uninstall` commands are implemented and well-tested, and a one-line installer is live. The remaining commands (`update`, `outdated`, `search`, `validate`, `wizard`, `self-update`) and a PyPI release are on the [roadmap](#roadmap).

## Quick install

One command — in your terminal **or** via your agent. You don't need anything but `curl`; the script installs [uv](https://docs.astral.sh/uv/) if it's missing.

**In your terminal:**

```bash
# install a skill straight away (user scope -> ~/.claude/skills/):
curl -fsSL https://raw.githubusercontent.com/Osipchuk/agent-skills/main/install.sh | sh -s -- learning-mode

# into the current project instead (-> <cwd>/.claude/skills/):
curl -fsSL https://raw.githubusercontent.com/Osipchuk/agent-skills/main/install.sh | ASKILL_SCOPE=project sh -s -- learning-mode

# or install the askill CLI once, then drive it yourself:
curl -fsSL https://raw.githubusercontent.com/Osipchuk/agent-skills/main/install.sh | sh
askill list
askill install learning-mode
```

**Via your coding agent** (Claude Code, Cursor, …) — tell it (replace `<skill>` with the name you want, e.g. `toxic-senior-reviewer`):

> Install the `<skill>` skill from the agent-skills library by running this exact command, substituting the skill name I asked for:
> `uvx --from "git+https://github.com/Osipchuk/agent-skills#subdirectory=installer" askill install <skill> --scope user`

The agent runs the command and the skill lands in `~/.claude/skills/`. To install into the current project instead, ask it to add `--scope project`.

> **Note:** in Claude Code's default permission mode the agent may refuse this, since `uvx` runs code from a remote repo and writes into your `~/.claude`. That refusal is expected — run the command yourself in a terminal instead. (A trusted, first-class Claude Code plugin install is in the works.)

## Available skills

- **[`learning-mode`](skills/learning-mode/)** — turn a Claude Code session into a learn-by-doing tutorial with a spaced-repetition review log.
- **[`article-translator`](skills/article-translator/)** — translate long-form articles and prose between languages while preserving the author's voice, structure, and formatting.
- **[`toxic-senior-reviewer`](skills/toxic-senior-reviewer/)** — code review in the voice of a blunt senior dev: sharp criticism only, curt approval when the code is actually good.

## askill CLI

Once installed, `askill` reads its skills from the published [`registry.json`](registry.json) by default — no `--registry` flag needed:

```bash
askill list                          # all skills in the manifest
askill list --json                   # machine-readable
askill info learning-mode
askill install learning-mode --scope user
askill uninstall learning-mode --scope user
```

Implemented: `list`, `info`, `install`, `uninstall` — with `--scope user|project`, `--json` everywhere, deterministic checksum verification, and the conflict handling from the spec (already-installed no-op, version conflicts, `--force`, `--dry-run`, `--no-checksum`). Exit codes: `0` ok, `1` user error, `2` system error, `3` conflict.

## From source (development)

Run it from a clone with [uv](https://docs.astral.sh/uv/), pointing at the local manifest:

```bash
git clone https://github.com/Osipchuk/agent-skills
cd agent-skills/installer
uv sync

uv run askill list   --registry ../registry.json
uv run askill install learning-mode --registry ../registry.json --scope user
uv run pytest
```

## Authoring a skill

A skill is a folder `skills/<name>/` with a `SKILL.md` whose frontmatter carries `name`, a trigger-oriented `description`, and a pinned `version`. Bulky helpers live in `scripts/` and `references/` and are pulled in on demand (progressive disclosure). Presentation metadata (summary, tags, etc.) lives in `catalog/<name>.yaml`. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full format and a checklist.

## Roadmap

- [x] One-line bootstrap (`curl … | sh`) and a default published registry
- [ ] `update`, `outdated`, `search`, `validate`
- [ ] Interactive `wizard`, `self-update`
- [ ] PyPI release (turns the install into `uvx askill install <name>`)
- [ ] Multi-agent adapters (Codex, Cursor)

## Contributing

Contributions of skills and CLI improvements are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE).
