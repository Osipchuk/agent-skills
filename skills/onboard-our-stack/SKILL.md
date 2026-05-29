---
name: onboard-our-stack
description: 'Build a newcomer''s mental model of THIS codebase by walking a curated, topic-scoped reading list and then synthesizing how the pieces fit together. Reads a repo-local .onboard/topics.yaml that maps each subsystem to its load-bearing files (in the order they make sense), its gotchas, and the ADRs that explain the why. Use this whenever someone asks how the team''s own system works — "explain our auth flow", "how does our orchestrator route between agents", "walk me through our RAG pipeline", "I''m new, how does our X work", "where does Y live in our code" — even if they don''t say the word "onboard". Do NOT use for: generic programming or public-library questions ("how does OAuth work in general", "how do Postgres GIN indexes work"), debugging a specific error or stack trace, writing or modifying code, or a repo that has no .onboard/topics.yaml. This skill teaches an existing system; it does not generate documentation or code.'
version: 0.1.0
---

# onboard-our-stack

Teach a newcomer how *this* system works by following a curated reading list,
not by guessing or summarizing the whole repo. The institutional knowledge —
which few files out of hundreds are load-bearing, and in what order they make
sense — lives in `.onboard/topics.yaml`, the single source of truth. Never
invent the reading list.

## Workflow

1. **Locate the config.** Read `.onboard/topics.yaml` from the repo root. If it
   is missing, stop and tell the user the skill isn't configured yet; point them
   at `references/topics.example.yaml` to bootstrap it. Do not improvise a
   reading list from a blind repo scan — a guessed model is worse than none.

2. **Match the topic.** Map the question to a topic by key or by its
   `one_liner`. If nothing matches, list the available topic keys and ask which
   one. If several match, pick the closest and say which you chose and why.

3. **Read in order.** Open each path in `read_in_order` in the given order — the
   order encodes the mental model. If a path is missing, the config is stale:
   warn the user, name the missing file, read what remains, and flag the gap
   rather than papering over it.

4. **Synthesize, don't dump.** Lead with the topic's `one_liner`, then explain
   how the parts connect, following the file order. Surface every
   `watch_out_for` item explicitly. Cite files by path. Point to the listed
   ADR(s) for rationale ("read ADR-00xx first if you want the why"). This is
   orientation — a mental model — not a line-by-line code walk.

5. **Close.** Offer the nearest adjacent topic as a next step.

## Maintaining the config

`.onboard/topics.yaml` is PR-able and lives next to the code, so it is reviewed
as the system changes. Run `scripts/check_topics.py` in CI to fail the build if
any referenced path stops resolving — stale reading lists teach a wrong model,
which is the main failure mode for this skill. See
`references/topics.example.yaml` for the schema and a worked example.
