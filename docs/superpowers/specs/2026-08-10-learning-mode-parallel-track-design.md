# learning-mode: parallel track — design

**Date:** 2026-08-10
**Status:** approved (pending written-spec review)
**Skill:** [`skills/learning-mode`](../../../skills/learning-mode/SKILL.md), version 0.1.1 → 0.2.0

## Goal

Today, when `learning-mode` hands a chunk off, the agent goes idle: it drops the
anchor, points at the brief, and ends its turn. The relevant instruction is
[SKILL.md:220](../../../skills/learning-mode/SKILL.md#L220) — *"Then **stop writing for that
specific gap**. … Continue helping with other parts of the feature normally **if
asked**."* Read as written, the agent stops on everything and waits to be asked.
The session stalls at the speed of the slowest writer (the human), and the human
feels like they're holding up the work.

Target behaviour: the handoff becomes an explicit **division of labour**. The human
takes their atom; the agent takes the rest of the same feature and writes it in
the same turn, so the repo has moved forward by the time the human comes back for
review.

## Key constraint: Claude Code is turn-based

The agent cannot write code while the human types — the agent's turn ends and the
human speaks next. So "parallel" cannot be specified as *"keep working while the
user works"*; instructions in that shape ask for something the runtime does not
offer, and the agent will either idle anyway or hallucinate concurrency.

What is actually available is **ordering inside one turn**: don't end the turn on
the handoff. Hand off first, then do your own slice, then yield. The human's
experience is the intended one — they leave to solve their atom and return to a
repo that advanced — and the spec stays honest about the mechanism.

This is why the change lands as *steps in the task lifecycle*, not as a mode flag.

## Decisions

- **Agent's slice = the rest of the same feature** (not just test scaffolding
  around the gap, and not arbitrary session work). The handoff is a split of one
  real piece of work: the human's atom plus everything else the feature needs.
- **The file holding the anchor is off-limits in full** until review closes. Not
  "off-limits outside the anchor" — the whole file. Two writers in one file means
  the human's unsaved editor buffer can silently clobber the agent's edits, or
  vice versa. Edits the feature genuinely needs in that file are deferred, in
  writing, to after review.
- **Scope = exactly the declared list.** The agent announces its slice at handoff
  time and does precisely that, then stops. Finished early ≠ take on more. The
  human must be able to predict what they'll find when they return.
- **No `parallel_work` toggle in `plan.md`.** The new behaviour is the default; a
  human who wants the agent to wait says so in words. Configuration nobody asked
  for is exactly what this repo's CLAUDE.md warns against.

## Design

### 1. Handoff becomes a declared split

The lifecycle changes from `pick → handoff → wait → review → close out` to
`pick → split → handoff → my slice → review → close out`.

Order **inside the turn** is normative:

1. Write the anchor and `active-task.md`. The human is unblocked immediately and
   never waits on the agent's own work.
2. State the split in one line in chat ("you take `validate_password`; I'll take
   the route, the repository call, and a failing test for your gap").
3. Do the slice.
4. Close the turn with a short summary.

The split is also persisted in `active-task.md` (new `## Split` section) so a
session restart, `/clear`, or next-day resume recovers who owns what.

### 2. Contract first

Because the agent's code will *call* the human's gap, the gap's signature and
return contract are fixed at handoff time and recorded in `active-task.md`. The
agent writes call sites against that contract. It does not write the body.

If the human later wants a different signature, that's a conversation — not a
silent divergence.

### 3. Boundaries — four hard rules

1. **Anchor file is untouchable** until the review closes. Feature work that
   needs that file goes into a new `## Deferred (after review)` list in
   `active-task.md`, and is executed during close-out.
2. **Anti-spoiler.** If a piece of the agent's slice requires writing the same
   technique the human is currently practising — elsewhere in the codebase — the
   agent does not write it. Otherwise the human returns to find a finished model
   answer to their own exercise, and the exercise is dead. Defer it, or offer it
   as the follow-up task.
3. **A failing test against the gap is allowed and encouraged.** It is not a
   spoiler; it is the target. The implementation is not.
4. **Declared scope only.** No extra items, no opportunistic refactors of
   neighbouring code. A human who returns to an unrecognisable repo has lost the
   context they needed for their own task.

### 4. Review pre-empts progress

The moment the human says "ready" (or asks a question about the gap), the agent
drops its slice where it stands and switches to review. Review beats feature
progress, always. Unfinished slice items stay as unchecked entries in
`active-task.md` and are picked up after the review resolves.

### 5. When there is nothing to parallelise

Two cases. Some gaps genuinely block the whole feature. And some practice units
have no feature at all behind them — a topic surfaced from the spaced-repetition
log in an otherwise idle session is a pure exercise, so there is no "rest of the
work" to divide. Both land here: the agent says so
plainly — "without your piece the feature can't move; I'm parked" — and does
**not** invent work to look busy (no adjacent refactors, no docs written for
occupancy). The failing test and type definitions are almost always available;
that is the floor, not a springboard.

### 6. End-of-turn summary

Two to four lines: what was written and where, plus two explicit statements —
*your gap is untouched* and *you don't have to read my code before doing your
task*. The second matters: without it the human treats the agent's output as
required reading and the handoff gets heavier, not lighter.

## Files to change

| File | Change |
|------|--------|
| `skills/learning-mode/SKILL.md` | Mental model (two tracks); lifecycle line; handoff artifacts (third artifact: the declared split); replace "While the user works" (L222–226) with the boundary/anti-spoiler/scope/pre-emption rules; rewrite "Handing it over" (drop *"stop writing … if asked"*); close-out gains the `## Deferred` step; "Resuming a task" recovers the split; new edge cases (nothing to parallelise; human rewrites the agent's code). Version → `0.2.0`. |
| `skills/learning-mode/references/active-task-template.md` | Add `## Split` (your atom / my slice, plus the gap's contract) and `## Deferred (after review)`. |
| `skills/learning-mode/references/worked-examples.md` | Update the examples that currently show the agent ending its turn on the handoff — as written they'd contradict the new rules. |
| `catalog/learning-mode.yaml` | Highlights / example mention that the agent ships its half instead of idling. Does not affect the skill checksum. |
| `manifest/{registry,catalog}.json`, `.claude-plugin/*` | Regenerate via `installer/scripts/generate_registry.py` (never hand-edited). |

## Non-goals

- No `parallel_work` config knob (see Decisions).
- No new state file for the agent's track — the split lives and dies with
  `active-task.md`.
- No change to spaced repetition, the review rubric, onboarding, or topic naming.
- No attempt to make the agent literally concurrent with the human's typing.

## Verification

Documentation-only change to a skill, so the checks are structural, not test-suite:

- `grep` `SKILL.md` for the old wait-instruction wording — none must remain.
- Every rule in "Boundaries" is stated once, in one place, not restated in three
  sections with drifting wording.
- `active-task-template.md` has a section for every field `SKILL.md` claims the
  brief "must contain".
- `worked-examples.md` contains no example whose agent turn ends at the handoff.
- Regenerate the manifests and confirm the only diff is `learning-mode`'s version
  and checksum: `cd installer && uv run python scripts/generate_registry.py --commit "$(git -C .. rev-parse HEAD)" --schema`.

## Assumption

The change lands on the current `chore/consolidate-tags` branch, on top of the
existing uncommitted edit to `learning-mode/SKILL.md` (description rewrite +
version bump to 0.1.1). No separate branch.
