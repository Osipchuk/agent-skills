# ADR-0001: Unify per-skill config locations under `.claude/`

Status: Proposed
Date: 2026-08-10
Authors: Evgenii Osipchuk
Reviewers: <TODO: who must sign off>

## Context

Four of the library's seven skills read team-authored data from the *target*
repository rather than from their own installed folder: adr-capture reads a
config, onboard-our-stack reads a curated topics file, steelman-then-break reads
a scars log, learning-mode keeps a plan and a spaced-repetition log. That split
is deliberate — installed skill files are checksummed and overwritten on update,
so anything a team edits has to live outside the skill.

Three conventions had grown up independently: `.adr/config.yaml`,
`.onboard/topics.yaml`, `.claude/scars.md`, `.claude/learning/`. Half the library
already sat under `.claude/`, half did not, and every new skill would have to
re-decide. These paths are a public contract with users, so the cost of changing
them rises with the install base — which is still small.

## Decision

All per-skill team data lives under `.claude/`. `.adr/config.yaml` becomes
`.claude/adr/config.yaml`; `.onboard/topics.yaml` becomes
`.claude/onboard/topics.yaml`. The scars log and the learning directory already
conform and are unchanged.

One directory, but **two kinds of data inside it**, and they differ in who owns
them:

| | Team-owned | Developer-owned |
|---|---|---|
| Files | `.claude/scars.md`, `.claude/onboard/topics.yaml`, `.claude/adr/config.yaml` | `.claude/learning/` |
| One truth per… | repository | person |
| Reviewed in PRs | yes | no |
| Version control | commit it | gitignore it by default |

The distinction was implicit before this ADR and the unification smudged it, by
putting both kinds in one place. It is what decides whether a path belongs in
`.gitignore`: a learning plan holds one developer's goals, self-rated level and
a dated record of what they got wrong. It collides between developers — the
design has no per-user namespacing — and in a public repo it publishes more than
most people expect. A solo developer may still choose to commit it; the default
must be the safe one.

## Alternatives considered

- **Keep per-skill top-level dot-directories** — rejected: it leaves four skills
  with three conventions, scatters unrelated dot-directories across the user's
  repo root, and makes the location an open question for every future skill.
- **Defer until the library has more users** — rejected: the migration cost is
  paid by whoever has already installed the skills, and that population only
  grows. Breaking it now is the cheapest moment there will ever be.

## Consequences

- (+) One rule to document and one place to look; CONTRIBUTING states it in a
  single line.
- (+) New skills get an obvious home for team data instead of re-litigating the
  choice.
- (+) Aligns with the directory Claude Code already owns for project state.
- (−) A team that has `.onboard/topics.yaml` committed gets the cold-start path
  **silently** — the skill reports "no curated config" rather than "your config
  moved", so the failure is quiet rather than loud.
- (−) `.claude/` is widely treated as local-only, machine-specific state and is
  commonly gitignored — this repo's own `.gitignore` ignored all of it, which
  silently made the new config path untrackable. Narrowed here to
  `.claude/settings.local.json` and `.claude/*.local.json`, but every adopting
  team has the same trap waiting and we cannot fix it in their repo.

---

## Impact on installed skills

Two skills change their read path, so both take a version bump and a new
checksum, and every existing user must reinstall to get them: adr-capture
0.1.1 → 0.2.0 and onboard-our-stack 0.2.1 → 0.3.0. Users who already committed a
config at the old path keep the file but lose its effect — adr-capture falls back
to template defaults and onboard-our-stack cold-starts from the repo's own docs.
Neither says why, which is what makes this a breaking change rather than a
graceful one.

## Rollback plan

<TODO: whether backing this out means reverting the path change outright, or
shipping a compatibility read that accepts both the old and new locations — and
what signal (user reports? install telemetry we do not have?) would trigger it.>

## Open questions

- Should the two skills detect their legacy path and warn ("found
  `.onboard/topics.yaml`; it now belongs at `.claude/onboard/topics.yaml`")
  instead of silently falling back? That would turn the quiet failure above into
  a loud one for the cost of a few lines per skill.
- ~~This repo gitignores all of `.claude/`~~ — **resolved.** The blanket ignore
  contradicted what two of our own skills tell users to do (commit the topics
  file, version the scars log), so it was narrowed to the machine-local entries
  plus `.claude/learning/`, per the ownership split above. Fixing it also
  corrected learning-mode 0.2.1, which had promised its state "gets versioned in
  Git" — true only for a solo developer who opts in, and misleading everywhere
  else. The general trap remains for adopting teams: should the docs warn that a
  blanket `.claude/` ignore silently disables the curated paths?
- Does this warrant a migration note in the README, or is the install base small
  enough to skip it?
