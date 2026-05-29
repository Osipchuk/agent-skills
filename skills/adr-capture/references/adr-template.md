# ADR template

Base structure is MADR (Markdown Any Decision Records). The sections below the
`---` are the team's **mandatory** additions for a regulated/closed-contour
environment — the skill must leave a `<TODO: ...>` for any of them the
conversation did not cover, and must never invent their content.

Filename: `<NNNN>-<slug>.md` (e.g. `0042-vector-store.md`).

```markdown
# ADR-<NNNN>: <Title>

Status: Proposed        <!-- Proposed | Accepted | Superseded by ADR-XXXX -->
Date: <YYYY-MM-DD>
Authors: <names>
Reviewers: <TODO: who must sign off>

## Context

<The forces at play: the problem, constraints, and what made a decision
necessary now. 2-5 sentences.>

## Decision

<The choice, stated plainly in one or two sentences.>

## Alternatives considered

- **<Option A>** — rejected: <why>.
- **<Option B>** — rejected: <why>.

## Consequences

- (+) <positive consequence>
- (+) <positive consequence>
- (−) <cost / risk accepted>

---
<!-- Mandatory in this org. Do not delete a heading; fill it or leave the TODO. -->

## Regulatory impact

<TODO: which regulation(s) this touches; whether a control owner must review.>

## Data classification

<TODO: classification of any data this decision touches (public / internal /
confidential / restricted) and where it is processed or stored.>

## Security review status

<TODO: required / not required; ticket link if raised.>

## Rollback plan

<TODO: how to back this out, and the trigger that would make us.>

## Open questions

- <unresolved item>
```
