# Worked examples

End-to-end illustrations of the `learning-mode` skill in action. Read these when you want a concrete pattern-match for an unfamiliar situation. They are not normative — the SKILL.md rules are. Each example shows the rules applied to one realistic situation.

## Example 1: User opens a fresh FastAPI project, says "help me learn"

1. Glance at repo: `pyproject.toml` has fastapi, no tests yet, one `main.py` with a hello-world endpoint.
2. Lean onboarding: "I see this is a fresh FastAPI project — what are you trying to get better at, where would you place yourself with FastAPI right now, and do you want me to suggest practice naturally as we work, or only when you ask?"
3. After answers ("Pydantic validators specifically, comfortable with FastAPI basics, auto mode"): write `plan.md` with themes like "Pydantic field validators", "Pydantic model validators", "validation error messages", and an empty `progress.md`.
4. Suggest the first task — **atomic, with worked example planned**: "Let's build a User schema with email and password. I'll set up the model and write `validate_email` as the worked example — you write `validate_password`. Requirements: 8+ chars, at least one digit, raises `ValueError` with a clear message. Sound good?"
5. On yes: write the imports, the `User` class skeleton, the full `validate_email` body, then drop the anchor + stub for `validate_password`, then write `active-task.md`. Hand over.

Note what we did **not** do: ask the user to write "the whole schema", "all the validators", or "the User module". One atom, one example next to it.

## Example 2: User pings session start, has a learning plan, last practiced FastAPI 9 days ago

1. Silent check: `plan.md` exists, mode is `auto`, `progress.md` has `Pydantic @field_validator with type coercion` at stage 2 (interval 7 days), next_review = 2 days ago. Due.
2. User opens with "let's add a search endpoint to the users API". Respond to the actual request first, then weave in: "while we're touching the schema for the search filters, your `Pydantic @field_validator` review is due — I can write the rest of the search code, but leave the `validate_sort_order` field validator on the filters schema for you. Want to?"
3. On yes: write the route, the filter schema scaffold, one example validator (`validate_status` or similar) on the same schema, then leave the anchor + stub for `validate_sort_order`. Hand over.
4. On no: just write the endpoint as normal and don't push. The topic stays due — it'll come up next time.

## Example 3: User submits a buggy implementation

User pings "done, please review". Quick check: "how did it feel?" → "a bit fiddly, but I think it works".

Read the code. There's a bug: doesn't handle the case where the input list is empty (returns `None` instead of `[]`).

Deliver:
- "Nice work on the gather pattern — you wrapped each call cleanly and the exception handling looks right."
- "One thing to chase: what does your function return if `urls` is an empty list? Walk through it in your head."
- Don't write the fix.

Stage in `progress.md` stays the same or drops; mark "needs work" and keep the task open until they push the fix. **Anchor stays in the file** — close-out only happens when the task is genuinely done.

## Example 4: Refactor mode — confident user, existing function to improve

`plan.md` says the user is **comfortable** with asyncio. They ask: "this `fetch_all` function is slow, can you make it parallel?"

This is a refactor of existing code, and the user already knows the pattern. **Refactor mode.** No scaffold, no worked example — the existing sequential function IS the context.

Drop the anchor right above the existing function:

```python
# 🎓 LEARNING TASK: rewrite this for parallelism with asyncio.gather
# Brief: .claude/learning/active-task.md
def fetch_all(urls):
    results = []
    for url in urls:
        results.append(requests.get(url).json())
    return results
```

Brief is short (comfortable level): signature stays, must use `asyncio.gather`, must handle per-URL failures without crashing the batch, must preserve input order.

Hand over: "Anchor's above `fetch_all`. The sequential version stays as your reference until you replace it. Brief in `active-task.md`."

## Example 5: Pointer mode — polishing user, knows the pattern

`plan.md` says **polishing** for "SQL window functions". User is wiring up an analytics dashboard and says: "I want to practice that window-function ranking pattern again."

Pointer mode. Claude has nothing to teach about the shape — they know it. Just place the stub and the spec:

```python
def rank_users_by_activity(conn) -> list[dict]:
    """Return users ranked within their cohort by activity score, desc."""
    # 🎓 LEARNING TASK: implement (.claude/learning/active-task.md)
    ...
```

Brief is terse: "Return list of dicts with `user_id`, `cohort`, `activity`, `rank_in_cohort`. Cohorts come from `users.signup_month`. Ranking within cohort by activity desc, ties broken by user_id asc."

Hand over: "Stub's there. Brief in `active-task.md`. Go."

No scaffold beyond the signature, no worked example — they're polishing, not learning the shape.
