"""Deterministic assertions over a finished eval run (evals spec §4.1).

Pure functions over :class:`RunArtifacts` — the workspace directory plus the
transcript text. No LLM, no network, no subprocess: whatever needed a shell
(``git status``, running the agent) happened in the harness and arrives here as
plain data. That keeps every assertion trivially unit-testable, and it is why
§7 requires each compliance scenario to carry at least one of these.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from askill.evals.models import (
    Assertion,
    FileAssertion,
    GitAssertion,
    GrepAssertion,
    JudgeAssertion,
    TranscriptAssertion,
)


@dataclass(frozen=True)
class RunArtifacts:
    """Everything a deterministic assertion is allowed to look at.

    ``git_clean`` / ``commits`` are resolved by the harness rather than shelling
    out here, so this module never touches a subprocess.
    """

    workspace: Path
    transcript: str = ""
    git_clean: bool = True
    commits: int = 0


@dataclass(frozen=True)
class AssertionResult:
    """Outcome of one assertion, with enough detail to debug a red run."""

    passed: bool
    detail: str


def check(assertion: Assertion, run: RunArtifacts) -> AssertionResult:
    """Evaluate one deterministic assertion.

    Raises ``ValueError`` for a judge assertion: those need the transport layer
    (phase 2), and quietly passing one here would fake a green result.
    """
    if isinstance(assertion, JudgeAssertion):
        raise ValueError("judge assertions need the transport layer, not the deterministic checker")
    if isinstance(assertion, FileAssertion):
        return _check_file(assertion, run)
    if isinstance(assertion, GrepAssertion):
        return _check_grep(assertion, run)
    if isinstance(assertion, TranscriptAssertion):
        return _check_transcript(assertion, run)
    if isinstance(assertion, GitAssertion):
        return _check_git(assertion, run)
    raise ValueError(f"unsupported assertion kind: {assertion.kind!r}")  # pragma: no cover


def _resolve_inside(workspace: Path, relative: str) -> Path | None:
    """Resolve ``relative`` under ``workspace``; None if it escapes the sandbox.

    A suite is data, and data must not be able to assert on ``/etc`` just
    because someone wrote ``../..`` in a path.
    """
    target = (workspace / relative).resolve()
    root = workspace.resolve()
    return target if target == root or root in target.parents else None


def _check_file(assertion: FileAssertion, run: RunArtifacts) -> AssertionResult:
    target = _resolve_inside(run.workspace, assertion.path)
    if target is None:
        return AssertionResult(False, f"{assertion.path!r} resolves outside the workspace")

    exists = target.exists()
    if assertion.kind == "file_exists":
        return AssertionResult(exists, f"{assertion.path} {'exists' if exists else 'is missing'}")
    return AssertionResult(
        not exists, f"{assertion.path} {'still exists' if exists else 'is absent'}"
    )


def _matching_files(workspace: Path, glob: str, pattern: str) -> list[str]:
    """Workspace-relative paths of files whose text matches ``pattern``.

    Unreadable files (binaries, permission errors) are skipped rather than
    failing the run: a stray binary in a fixture should not decide an assertion.
    """
    regex = re.compile(pattern)
    hits: list[str] = []
    for path in sorted(workspace.glob(glob)):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if regex.search(text):
            hits.append(path.relative_to(workspace).as_posix())
    return hits


def _check_grep(assertion: GrepAssertion, run: RunArtifacts) -> AssertionResult:
    hits = _matching_files(run.workspace, assertion.glob, assertion.pattern)
    if assertion.expect == "present":
        detail = (
            f"matched in {', '.join(hits)}" if hits else f"no file under {assertion.glob} matched"
        )
        return AssertionResult(bool(hits), detail)
    detail = f"still matched in {', '.join(hits)}" if hits else f"absent under {assertion.glob}"
    return AssertionResult(not hits, detail)


def _check_transcript(assertion: TranscriptAssertion, run: RunArtifacts) -> AssertionResult:
    found = re.search(assertion.pattern, run.transcript) is not None
    if assertion.expect == "present":
        return AssertionResult(found, f"pattern {'found' if found else 'not found'} in transcript")
    return AssertionResult(not found, f"pattern {'found' if found else 'absent'} in transcript")


def _check_git(assertion: GitAssertion, run: RunArtifacts) -> AssertionResult:
    if assertion.expect == "clean":
        return AssertionResult(run.git_clean, "tree is clean" if run.git_clean else "tree is dirty")
    return AssertionResult(run.commits == 0, f"{run.commits} commit(s) made")
