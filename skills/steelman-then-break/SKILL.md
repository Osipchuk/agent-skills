---
name: steelman-then-break
description: 'Pressure-test a design proposal or technology choice in two separated passes: first the strongest possible case FOR it (steelman — argue the best version, even stronger than the author put it), then a rigorous case AGAINST it (red-team — name the anti-pattern, lead with what breaks first, cite the team''s prior scars), then finish with a calibrated verdict. Use this when the user asks to "review this proposal", "should we go with X", "steelman X", "challenge/red-team this design", or is choosing between an architecture, library, or framework. The value is the forced second pass that design discussions skip because nobody volunteers to be the contrarian. Do NOT use for: factual lookups, code review of existing code, requests for a single recommendation with no analysis wanted, or emotional venting. Critical calibration: if there is no substantive case against, say so plainly — manufactured objections destroy the skill''s signal.'
version: 0.1.0
---

# steelman-then-break

Most design discussions die at "this seems good, ship it" because being the
contrarian is socially expensive. This skill is a depersonalized contrarian: it
makes the strongest case for the proposal, then the strongest case against, then
calls it. The forced separation is the discipline — no on-the-other-hand hedging
inside either pass.

## Workflow

1. **Restate the target** in one sentence so it's unambiguous what is being
   evaluated. If the proposal is too vague to break, ask for the one missing
   detail first.

2. **Pass 1 — Steelman.** The strongest case *for*, including benefits the
   author may have missed. No "but", no caveats in this section. If the best
   version of the argument differs from what was written, argue the best
   version, not the literal one.

3. **Pass 2 — Break.** The strongest case *against*. Lead with what breaks
   first. Name the failure mode or anti-pattern explicitly. When a relevant
   precedent exists in `references/scars.md` (the team's catalogued past
   failures), cite it — arguing from the team's own evidence is the point. End
   each objection with the concrete signal that would tell you it's biting.

4. **Verdict.** Calibrated, not reflexively negative. State the single most
   important deciding factor, your actual call, and what new information would
   flip it. You must be willing to conclude "the steelman holds; proceed; here
   are the marginal risks to monitor."

## Calibration

Reflexive contrarianism is the failure mode that kills this skill. If Pass 2 has
no substantive content, write "I can't find a real case against this" rather than
padding with weak objections. A skill that always finds something wrong gets
ignored, and then it's worse than useless.

`references/scars.md` is where the team logs patterns that failed before, so the
Break pass argues from evidence instead of generic risk. Keep it updated; an
empty scars file just means the Break pass leans on named anti-patterns instead.
