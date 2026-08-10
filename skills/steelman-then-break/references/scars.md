# Scars

Copy this file to `.claude/scars.md` at your project's repo root and replace the
example with real entries. It stays in YOUR repo — versioned and edited by the
team, independent of the installed skill (whose files are checksummed and
overwritten on update).

Patterns this team adopted and later regretted. The Break pass of
`steelman-then-break` cites these so objections argue from our own evidence, not
generic risk. Add an entry whenever you unwind something; delete nothing.

Format per entry:

```
## <short pattern name>
- When: <YYYY-MM, project>
- We adopted: <what>
- What broke: <the failure, concretely>
- Cost: <time / incidents / migration effort>
- Lesson: <the generalizable rule>
```

---

<!-- Example entry — replace with real ones. -->

## Premature framework adoption (orchestration)
- When: 2024-Q3, <project>
- We adopted: a graph-based agent framework to "clean up" our orchestration.
- What broke: debugging moved from stack traces to graph state; the framework's
  pre-1.0 API churned twice and forced two rewrites.
- Cost: ~11 months until we unwound it back to plain async + a queue.
- Lesson: a framework only pays off when it solves our *hard* part. Ours was the
  queue, auth, and audit — none of which the framework touched.
