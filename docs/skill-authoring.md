# Authoring a skill

How to format a skill so it lands in the exact shape the installer (`askill` /
`registry.json`) and the web catalog (`catalog.json`) expect. This is the guide
for both human contributors and any AI skill-generator.

Copy-paste scaffolds live in [`templates/SKILL.md`](../templates/SKILL.md) and
[`templates/catalog.yaml`](../templates/catalog.yaml).

## The two files

A skill is split across two files, on purpose:

| File | Installed to the user? | Holds |
|------|------------------------|-------|
| `skills/<name>/SKILL.md` | **Yes** (copied verbatim, checksummed) | `name`, `description`, `version` + the workflow body |
| `catalog/<name>.yaml` | **No** (lives outside `skills/`) | all presentation/catalog metadata |

Presentation metadata (summary, tags, license, when, highlights, example) is
kept **out** of `SKILL.md` so it (a) does not dilute the `description` text the
agent matches on, and (b) is never shipped to a user's `~/.claude/skills/`.
Because `catalog/<name>.yaml` sits outside the skill folder, editing it never
changes the skill's checksum.

## Naming contract

The skill **folder name**, the `SKILL.md` `name`, and the catalog **filename**
must all be the same kebab-case string matching `^[a-z][a-z0-9-]{2,63}$`:

```
skills/re-anchor/SKILL.md   →  name: re-anchor
catalog/re-anchor.yaml
```

CI rejects a skill with no matching `catalog/<name>.yaml`, and a duplicate
`name` across skills.

## `SKILL.md` — keep it lean

Frontmatter has exactly three keys:

- **`name`** — kebab-case, equals the folder name.
- **`description`** — one long, trigger-oriented paragraph: WHAT the skill does
  AND WHEN to use it. List the concrete phrases/situations that should trigger
  it, plus explicit non-triggers ("Do not use for…"). This is the field a host
  agent matches against — it drives whether the skill fires correctly, so invest
  the most effort here.
- **`version`** — strict semver `MAJOR.MINOR.PATCH` (e.g. `0.1.0`). Not `0.1`,
  not `v0.1.0`, not `0.1.0a1`.

Body conventions: progressive disclosure — workflow in `SKILL.md`; bulky
templates/scripts in `references/` and `scripts/` (stdlib-only where possible).

## `catalog/<name>.yaml` — everything else

| Field | Required | Type / rules | Powers (design) |
|-------|----------|--------------|-----------------|
| `summary` | **yes** | one line, 10–1024 chars, no newlines | the list/hero "dek"; also the registry `description` |
| `tags` | no | list, kebab-case, ≤10 | the tag filter + counts |
| `compatible_agents` | no | list incl. `claude-code` (default `[claude-code]`) | — |
| `license` | no | SPDX id (e.g. `MIT`) | sidebar metadata |
| `when` | no | paragraph | the "When it fires" section |
| `highlights` | no | list of short bullets | the "What it does" section |
| `example` | no | object (below) | the Example trace block |

`example` shape:

```yaml
example:
  title: short label
  turns: 5            # integer ≥ 0
  tokens: 312         # integer ≥ 0
  caption: one-line context shown under the example
  trace_url: null     # optional link
  input:              # ordered list of turns
    - { kind: user, text: "…" }
  output:
    - { kind: anchor, text: "[my-skill] …" }   # `anchor` = the skill firing
    - { kind: assistant, text: "…" }
```

`kind` is one of: `user`, `tool`, `tool_out`, `assistant`, `anchor`.

## What is generated for you (never author these)

`path`, `entry`, `checksum`, and the per-skill `updated_at` (from the skill
folder's last git commit date) are computed by the generator. The catalog's
`description_long` is taken from the `SKILL.md` `description` automatically.

## Validation checklist (mirrors CI)

Run `uv run python scripts/generate_registry.py` from `installer/`. It fails
loudly if any of these are wrong:

- [ ] `skills/<name>/SKILL.md` exists with frontmatter `name` / `description` / `version`.
- [ ] `version` is strict `MAJOR.MINOR.PATCH`.
- [ ] `catalog/<name>.yaml` exists and has a `summary` (10–1024 chars, single line).
- [ ] `tags` are kebab-case and ≤10.
- [ ] `compatible_agents` (if set) includes `claude-code`.
- [ ] `example` turns use only the five allowed `kind` values.
- [ ] `name` is unique across all skills, and equals the folder + catalog filename.
