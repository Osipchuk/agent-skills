"""Shared pytest fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

DATA_DIR = Path(__file__).parent / "data"

# A valid-format checksum (the sha256 of the empty string) reused across fixtures.
_EMPTY_SHA = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


@pytest.fixture
def data_dir() -> Path:
    """Absolute path to the tests/data directory of JSON fixtures."""
    return DATA_DIR


@pytest.fixture
def registry_payload() -> dict[str, Any]:
    """A valid registry.json manifest (two skills) as a plain dict.

    Mutate a copy per-test to build invalid cases. Mirrors the real skills so it
    can seed the committed registry.json fixture later.
    """
    return {
        "schema_version": "1.0",
        "library": {
            "name": "askill-library",
            "repo": "https://github.com/example/agent-skills",
            "generated_at": "2026-05-21T10:00:00Z",
            "commit": "0" * 40,
        },
        "skills": [
            {
                "name": "learning-mode",
                "version": "0.1.0",
                "description": "Learn-by-doing coding tutor with spaced-repetition review.",
                "path": "skills/learning-mode",
                "entry": "SKILL.md",
                "tags": ["learning", "coaching", "tdd"],
                "compatible_agents": ["claude-code"],
                "dependencies": [],
                "checksum": _EMPTY_SHA,
                "license": "MIT",
            },
            {
                "name": "article-translator",
                "version": "0.1.0",
                "description": "Translate technical articles, keeping code blocks intact.",
                "path": "skills/article-translator",
                "entry": "SKILL.md",
                "tags": ["translation", "writing"],
                "compatible_agents": ["claude-code"],
                "dependencies": [],
                "checksum": _EMPTY_SHA,
                "license": "MIT",
            },
        ],
    }


@pytest.fixture
def registry_file(tmp_path: Path, registry_payload: dict[str, Any]) -> str:
    """Write the registry payload to a temp file; return its path as a string."""
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(registry_payload))
    return str(path)
