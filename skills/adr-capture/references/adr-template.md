# ADR template

Base structure is MADR (Markdown Any Decision Records). Below the `---` sits the
team's **mandatory** set, declared in `mandatory_sections` in
`.claude/adr/config.yaml`.

With no config, the default is deliberately minimal: **`Rollback plan` only**.
It is the section humans skip most often and it is meaningful for almost any
decision. Anything heavier — regulatory impact, data classification, security
review — is a real requirement for some teams and pure noise for others, so it
is opt-in rather than a default that produces TODOs nobody will ever fill. A
regulated team's set is shown as a commented example below.

Whatever the set, the rule is the same: leave a `<TODO: ...>` for any mandatory
section the conversation did not cover, and never invent their content.

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
<!-- The team's mandatory set, from mandatory_sections in
     .claude/adr/config.yaml. Do not delete a configured heading; fill it or
     leave the TODO. Default when there is no config: Rollback plan only. -->

## Rollback plan

<TODO: how to back this out, and the trigger that would make us.>

## Open questions

- <unresolved item>
```

## Heavier sets are opt-in

A regulated or closed-contour team would declare something like this in
`.claude/adr/config.yaml`, and the skill would then require all four headings:

```yaml
mandatory_sections:
  - Regulatory impact          # which regulation(s); who signs off?
  - Data classification        # public / internal / confidential / restricted
  - Security review status     # required or not; ticket link if raised
  - Rollback plan
```

A product team might instead pick `Cost impact` and `Rollback plan`; a library
like this one picks `Impact on installed skills` and `Rollback plan`. The set is
the team's call — the skill only enforces whatever they declared.
