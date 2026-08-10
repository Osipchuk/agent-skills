# Active Task

**Topic:** `<exact topic name — must match the row in progress.md if one exists>`

**Mode:** `<build | refactor | pointer>`

**Created:** `<YYYY-MM-DD>`

## What to build

`<One or two sentences in mentor tone — see SKILL.md "Brief tone". Lead with context, not imperative. The single atom: one function body, one validator, one method. Not "a feature", not "the validators" (plural).>`

## Where

- File: `<path/to/file.py>`
- Anchor: search for `🎓 LEARNING TASK` in the file

## Split

**Your atom:** `<the one thing the user writes>`

**Contract** — agreed at handoff, Claude's code calls this:

```
<signature, return type, what it raises>
```

**Claude's slice** — the rest of the feature, written while the gap is open:

- [ ] `<item — file and what it does>`
- [ ] `<item>`

Unchecked items are resumed after review. Claude does not touch the anchor file
above while the gap is open.

## Worked example to mirror

*Include this section in `build` mode only. Delete it for `refactor` or `pointer` mode.*

The same pattern, implemented by Claude, lives at:

- File: `<path/to/file.py>`
- Reference: `<e.g., validate_email at line 12>`

Read it first. Your task mirrors the same shape.

## Acceptance criteria

Self-checkable bullets, scaled to the user's level on this topic.

- **first contact**: explicit signature, expected I/O, named approach, 1–2 concrete examples in this list
- **comfortable**: signature + constraints + edge cases to think about
- **polishing**: terse — name the intent, edges are your call

- [ ] `<criterion 1>`
- [ ] `<criterion 2>`
- [ ] `<criterion 3>`
- [ ] `<criterion 4>` (optional)
- [ ] `<criterion 5>` (optional)

## Hint policy

`<Default: Claude answers focused questions but does not write the code in the gap. In build mode, the worked example next to the gap is the primary reference — read that first before asking. Adjust if the user wants more or less scaffolding.>`

## When ready

Tell Claude "ready for review" (or any variant). Claude will read the code at the anchor, ask how it felt, and review.

## Deferred (after review)

Claude's bookkeeping, not homework. Edits the feature needs *inside* the anchor
file, held back so two writers never share one file. Usually empty. Executed
during close-out.

- [ ] `<deferred edit>`
