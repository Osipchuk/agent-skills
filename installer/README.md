# askill

CLI installer for the agent-skills library. See [../docs/skills-library-spec.md](../docs/skills-library-spec.md) for the full design.

This package is built incrementally. Sub-project 1 (current): the deterministic core (pydantic models, registry loading, scope resolution, read-only state) plus the read-only `list` and `info` commands.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy src/askill
```
