# Interactive wizard + Claude Code plugin marketplace — design

**Date:** 2026-05-25
**Status:** draft (pending user review)

## Goal

Make installing skills genuinely convenient on two surfaces, after real use exposed
that typing `askill install <name> --registry … --scope …` and the `uvx`/`curl|sh`
agent path are both awkward:

1. **Terminal (human):** one command launches an **interactive wizard** — a
   checklist of skills (checkboxes), a scope picker, Enter → installed. No typing
   names. (The original vision; the spec's planned `questionary` wizard layer.)
2. **Claude Code (the agent):** a **native plugin marketplace**, so
   `/plugin install …@askill` works as a trusted, first-class op — not gated by the
   remote-code-execution / self-modification permission classifier that blocks
   `uvx`/`curl|sh`.

Both coexist with the existing `askill` CLI + `registry.json` (terminal/non-Claude
agents). Already shipped this session: the post-install restart hint.

## Decisions

- **Marketplace name:** `askill` (the CLI brand). `agent-skills` is **reserved** by
  Anthropic and cannot be used.
- **Granularity:** one bundled plugin named `skills` — `/plugin install skills@askill`
  installs the whole library. (Skills are model-invoked by description, so having all
  loaded is cheap; granular per-skill picking is served by the wizard on the terminal.)
- **Plugin tree is generated** from canonical `skills/` and committed by CI — same
  pattern as `registry.json` / `catalog.json`. No hand-maintenance, no drift.
- **Plugin content is copied** (not symlinked) into the plugin dir — robust and
  unambiguous (plugins are copied to a cache on install and can't reference files
  outside their dir).
- **Plugin version:** omit `version` in `plugin.json` → Claude Code uses the git
  commit SHA, so every push is a new version and auto-updates just work.

---

## Component 1 — Interactive wizard (`askill`)

**Entry points** (TTY only; the wizard is a thin layer over Core, per spec §4.1):
- `askill wizard` — explicit.
- `askill` with no subcommand **and** a TTY → launches the wizard.
- Non-TTY with no subcommand → print help (unchanged). `--json` is N/A for the wizard.

**Flow** (using `questionary`):
1. Load the registry (default registry URL; `--registry` override honored).
2. `questionary.checkbox` — list every skill as `name — summary`, with an
   `(installed)` marker for ones already present in the resolved scope's state.
3. `questionary.select` — scope: `user` or `project`. Default chosen from cwd:
   `project` if a `.claude/` dir exists in cwd/ancestors, else `user`.
4. Confirm summary → for each checked skill, call the **existing** install Core
   (`fetch_and_place` + state write) — reusing all current checksum/conflict logic.
5. Print a per-skill result table and, if Core reports `skills_dir_created`, the
   restart hint (already implemented).

**Code:**
- New `commands/wizard.py` (thin Typer command) + bare-invoke wiring in `cli.py`.
- A small Core helper `core/` function returning "installable skills + installed
  status" so the wizard stays declarative and testable; the wizard module itself
  only does questionary I/O.
- Add `questionary` to `pyproject.toml` dependencies.

**Testing:** Core helper unit-tested directly. The questionary I/O layer is kept
thin; test it by monkeypatching questionary prompts to return canned selections and
asserting Core install is called with the right names/scope (no real TTY).

---

## Component 2 — Claude Code plugin marketplace

**Generated layout (committed):**
```
.claude-plugin/
  marketplace.json            # marketplace "askill", one plugin entry
plugins/
  skills/
    .claude-plugin/
      plugin.json             # name "skills", description, author; NO version (git SHA)
    skills/
      learning-mode/…         # copied from /skills/learning-mode
      article-translator/…
      toxic-senior-reviewer/…
```

`marketplace.json`:
```json
{
  "name": "askill",
  "owner": { "name": "Evgenii Osipchuk" },
  "plugins": [
    {
      "name": "skills",
      "source": "./plugins/skills",
      "description": "<library dek from catalog>",
      "keywords": ["skills", "claude-code"]
    }
  ]
}
```

`plugins/skills/.claude-plugin/plugin.json`:
```json
{
  "name": "skills",
  "description": "Reusable agent skills: learning-mode, article-translator, toxic-senior-reviewer.",
  "author": { "name": "Evgenii Osipchuk" }
}
```

After install, skills are namespaced `/skills:learning-mode`, etc. (model-invocation
still works by description.)

**Generation:** extend `installer/scripts/generate_registry.py` (already produces
registry+catalog) to also emit `marketplace.json` + the `plugins/skills/` tree by
copying each `skills/<name>/` into `plugins/skills/skills/<name>/`. Validate with
`claude plugin validate .` in CI when available.

**CI:** extend the existing generate-and-commit workflow to also write
`.claude-plugin/` and `plugins/`.

**Install UX (docs):**
```
/plugin marketplace add Osipchuk/agent-skills
/plugin install skills@askill
```
(or non-interactive: `claude plugin marketplace add Osipchuk/agent-skills` then
`claude plugin install skills@askill`).

---

## Component 3 — README

- New **"Install in Claude Code (plugin)"** section with the two `/plugin` commands;
  note it's the trusted path that avoids the `uvx` permission block.
- Update the existing agent-prompt note ("plugin install is in the works") to link
  this section.
- Wizard becomes the headline terminal command: `uvx --from "git+…#subdirectory=installer" askill`
  → interactive checklist.

---

## Testing & non-goals

- **Tests:** wizard Core helper (unit) + wizard selection→install (mocked
  questionary); generator emits valid `marketplace.json`/`plugin.json` and copies
  skills (unit); `sh -n`/existing suites stay green; `claude plugin validate .`
  smoke check.
- **Non-goals:** per-skill plugins (chose bundle); publishing to the community
  marketplace; a Windows `.ps1`; changing the existing `install`/`list`/`info`/
  `uninstall` behavior.

## Build order

1. Wizard (Core helper → command → questionary wiring → tests → README headline).
2. Marketplace generator (emit marketplace.json + plugins/ → tests → run generator →
   commit artifacts → CI wiring → README plugin section → `claude plugin validate`).

Each lands on the existing `feat/skills-catalog-manifest` branch / PR #1, or a fresh
branch if preferred.
