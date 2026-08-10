"""Tests for askill.evals.asserts — the deterministic assertions (evals spec §4.1).

These tests are the SPEC for evals/asserts.py. Each assertion is a pure
function over a finished run: the workspace directory plus the transcript text.
No LLM is involved, which is exactly why these carry the weight in a suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from askill.evals.asserts import RunArtifacts, check
from askill.evals.models import (
    FileAssertion,
    GitAssertion,
    GrepAssertion,
    JudgeAssertion,
    TranscriptAssertion,
)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / ".claude" / "learning").mkdir(parents=True)
    (tmp_path / ".claude" / "learning" / "active-task.md").write_text("brief", encoding="utf-8")
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "models.py").write_text(
        "# 🎓 LEARNING TASK: write validate_password\ndef validate_password(v): ...\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("nothing to see", encoding="utf-8")
    return tmp_path


def artifacts(workspace: Path, *, transcript: str = "", git_clean: bool = True, commits: int = 0):
    return RunArtifacts(
        workspace=workspace, transcript=transcript, git_clean=git_clean, commits=commits
    )


# --------------------------------------------------------------------------- #
# file_exists / file_absent
# --------------------------------------------------------------------------- #


def test_file_exists_passes_when_the_file_is_there(workspace: Path) -> None:
    assertion = FileAssertion(kind="file_exists", path=".claude/learning/active-task.md")

    result = check(assertion, artifacts(workspace))

    assert result.passed


def test_file_exists_fails_and_says_what_was_missing(workspace: Path) -> None:
    assertion = FileAssertion(kind="file_exists", path=".claude/learning/plan.md")

    result = check(assertion, artifacts(workspace))

    assert not result.passed
    assert "plan.md" in result.detail


def test_file_absent_passes_when_the_file_is_gone(workspace: Path) -> None:
    assertion = FileAssertion(kind="file_absent", path=".claude/learning/plan.md")

    assert check(assertion, artifacts(workspace)).passed


def test_file_absent_fails_when_the_file_lingers(workspace: Path) -> None:
    assertion = FileAssertion(kind="file_absent", path=".claude/learning/active-task.md")

    assert not check(assertion, artifacts(workspace)).passed


def test_file_path_escaping_the_workspace_is_refused(workspace: Path) -> None:
    """A suite must not be able to assert on the machine outside its sandbox."""
    assertion = FileAssertion(kind="file_exists", path="../../etc/passwd")

    result = check(assertion, artifacts(workspace))

    assert not result.passed
    assert "outside the workspace" in result.detail


# --------------------------------------------------------------------------- #
# grep
# --------------------------------------------------------------------------- #


def test_grep_present_finds_the_anchor_under_a_glob(workspace: Path) -> None:
    assertion = GrepAssertion(
        kind="grep", glob="**/*.py", pattern="🎓 LEARNING TASK", expect="present"
    )

    result = check(assertion, artifacts(workspace))

    assert result.passed
    assert "app/models.py" in result.detail


def test_grep_present_fails_when_no_file_matches_the_pattern(workspace: Path) -> None:
    assertion = GrepAssertion(
        kind="grep", glob="**/*.md", pattern="LEARNING TASK", expect="present"
    )

    assert not check(assertion, artifacts(workspace)).passed


def test_grep_absent_passes_when_the_anchor_was_cleaned_up(workspace: Path) -> None:
    assertion = GrepAssertion(
        kind="grep", glob="**/*.md", pattern="🎓 LEARNING TASK", expect="absent"
    )

    assert check(assertion, artifacts(workspace)).passed


def test_grep_absent_fails_and_names_the_offending_file(workspace: Path) -> None:
    assertion = GrepAssertion(kind="grep", glob="**/*.py", pattern="LEARNING TASK", expect="absent")

    result = check(assertion, artifacts(workspace))

    assert not result.passed
    assert "app/models.py" in result.detail


def test_grep_skips_binary_files_instead_of_crashing(workspace: Path) -> None:
    (workspace / "blob.py").write_bytes(b"\xff\xfe\x00binary")
    assertion = GrepAssertion(
        kind="grep", glob="**/*.py", pattern="LEARNING TASK", expect="present"
    )

    assert check(assertion, artifacts(workspace)).passed


# --------------------------------------------------------------------------- #
# transcript
# --------------------------------------------------------------------------- #


def test_transcript_present_matches_a_regex(workspace: Path) -> None:
    assertion = TranscriptAssertion(kind="transcript", pattern=r"active-task\.md", expect="present")

    run = artifacts(workspace, transcript="Brief is in .claude/learning/active-task.md")

    assert check(assertion, run).passed


def test_transcript_absent_catches_a_forbidden_offer(workspace: Path) -> None:
    assertion = TranscriptAssertion(
        kind="transcript", pattern=r"(?i)shall i commit", expect="absent"
    )

    run = artifacts(workspace, transcript="Shall I commit this for you?")

    assert not check(assertion, run).passed


# --------------------------------------------------------------------------- #
# git
# --------------------------------------------------------------------------- #


def test_git_clean_fails_when_the_tree_was_dirtied(workspace: Path) -> None:
    assertion = GitAssertion(kind="git", expect="clean")

    assert not check(assertion, artifacts(workspace, git_clean=False)).passed


def test_git_no_commits_fails_when_the_agent_committed(workspace: Path) -> None:
    assertion = GitAssertion(kind="git", expect="no_commits")

    result = check(assertion, artifacts(workspace, commits=2))

    assert not result.passed
    assert "2" in result.detail


def test_git_no_commits_passes_on_an_untouched_history(workspace: Path) -> None:
    assertion = GitAssertion(kind="git", expect="no_commits")

    assert check(assertion, artifacts(workspace, commits=0)).passed


# --------------------------------------------------------------------------- #
# judge
# --------------------------------------------------------------------------- #


def test_judge_assertions_are_not_checkable_here(workspace: Path) -> None:
    """Phase 1 has no transport. Routing a judge assertion into the
    deterministic checker is a programming error, not a failed assertion."""
    assertion = JudgeAssertion(kind="judge", rubric="The tone is warm.")

    with pytest.raises(ValueError, match="judge"):
        check(assertion, artifacts(workspace))
