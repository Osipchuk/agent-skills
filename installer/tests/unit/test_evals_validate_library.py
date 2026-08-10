"""Tests for askill.evals.loader.validate_library — the whole-library sweep.

These tests are the SPEC for what ``run_evals.py --validate`` does across every
suite at once (evals spec §7, §8.1): validate each suite, keep going after a
broken one, and record which skills have no suite yet.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from askill.evals.loader import validate_library
from tests.unit.test_evals_loader import valid_suite_payload, write_skill, write_suite


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "evals").mkdir()
    (tmp_path / "skills").mkdir()
    return tmp_path


def codes(findings: list) -> list[str]:
    return [finding.code for finding in findings]


def test_clean_library_reports_its_suites_and_no_findings(repo: Path) -> None:
    write_suite(repo / "evals", "rubber-duck", valid_suite_payload())
    write_skill(repo / "skills", "rubber-duck", "0.2.0")

    suites, findings = validate_library(repo / "evals", skills_dir=repo / "skills")

    assert suites == ["rubber-duck"]
    assert findings == []


def test_a_skill_without_a_suite_is_info_not_a_failure(repo: Path) -> None:
    """Phase 1 ships suites for two of seven skills. Missing coverage must be
    visible without blocking every merge until the backlog is done."""
    write_suite(repo / "evals", "rubber-duck", valid_suite_payload())
    write_skill(repo / "skills", "rubber-duck", "0.2.0")
    write_skill(repo / "skills", "learning-mode", "0.2.0")

    _suites, findings = validate_library(repo / "evals", skills_dir=repo / "skills")

    assert codes(findings) == ["no-suite"]
    assert findings[0].severity == "info"
    assert findings[0].skill == "learning-mode"


def test_an_unparseable_suite_becomes_a_finding_rather_than_an_exception(repo: Path) -> None:
    """One broken suite must not hide the state of all the others."""
    write_suite(repo / "evals", "rubber-duck", "skill: [unclosed\n")
    write_skill(repo / "skills", "rubber-duck", "0.2.0")
    write_suite(repo / "evals", "learning-mode", valid_suite_payload(skill="learning-mode"))
    write_skill(repo / "skills", "learning-mode", "0.2.0")

    suites, findings = validate_library(repo / "evals", skills_dir=repo / "skills")

    assert suites == ["learning-mode", "rubber-duck"]
    assert codes(findings) == ["unloadable"]
    assert findings[0].skill == "rubber-duck"


def test_findings_from_several_suites_are_all_reported(repo: Path) -> None:
    payload = valid_suite_payload(skill="learning-mode")
    payload["compliance"] = []
    write_suite(repo / "evals", "learning-mode", payload)
    write_skill(repo / "skills", "learning-mode", "0.2.0")
    write_suite(repo / "evals", "rubber-duck", valid_suite_payload())
    write_skill(repo / "skills", "rubber-duck", version="0.9.0")

    _suites, findings = validate_library(repo / "evals", skills_dir=repo / "skills")

    assert set(codes(findings)) == {"no-compliance", "version-drift"}


def test_empty_evals_dir_reports_every_skill_as_uncovered(repo: Path) -> None:
    write_skill(repo / "skills", "rubber-duck", "0.2.0")

    suites, findings = validate_library(repo / "evals", skills_dir=repo / "skills")

    assert suites == []
    assert codes(findings) == ["no-suite"]
