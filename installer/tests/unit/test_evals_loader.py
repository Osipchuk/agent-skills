"""Tests for askill.evals.loader — load and statically validate suites.

These tests are the SPEC for evals/loader.py (evals spec §5.2, §7). Everything
here runs with no LLM and no network: this is the cheap gate that runs on every
PR, so it must catch a suite that has drifted from its skill.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from askill.evals.loader import SuiteError, discover_suites, load_suite, validate_suite

# --------------------------------------------------------------------------- #
# Fixtures on disk
# --------------------------------------------------------------------------- #


def valid_suite_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "skill": "rubber-duck",
        "version_tested": "0.2.0",
        "budget": {"max_turns": 6, "model": "claude-sonnet-4-6"},
        "trigger": {
            "positive": [
                {"id": "think-through", "prompt": "Help me think through this."},
                {"id": "sounding-board", "prompt": "Be my sounding board."},
            ],
            "negative": [
                {
                    "id": "just-tell-me",
                    "prompt": "Just tell me the fix.",
                    "covers_non_trigger": True,
                },
                {"id": "write-code", "prompt": "Write the retry decorator."},
            ],
        },
        "compliance": [
            {
                "id": "one-question-per-turn",
                "prompt": "I'm stuck on this bug.",
                "assertions": [
                    {"kind": "transcript", "pattern": r"\?", "expect": "present"},
                    {"kind": "judge", "rubric": "Asks at most one question."},
                ],
            }
        ],
        "thresholds": {"trigger_accuracy": 1.0, "compliance_pass_rate": 1.0},
    }
    base.update(overrides)
    return base


def write_suite(evals_root: Path, name: str, payload: dict[str, Any] | str) -> Path:
    """Create ``evals/<name>/suite.yaml``; ``payload`` may be raw text."""
    suite_dir = evals_root / name
    suite_dir.mkdir(parents=True, exist_ok=True)
    text = payload if isinstance(payload, str) else yaml.safe_dump(payload, sort_keys=False)
    (suite_dir / "suite.yaml").write_text(text, encoding="utf-8")
    return suite_dir


def write_skill(skills_dir: Path, name: str, version: str = "0.2.0") -> Path:
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    front = yaml.safe_dump(
        {"name": name, "description": "x" * 60, "version": version}, sort_keys=False
    )
    (skill_dir / "SKILL.md").write_text(f"---\n{front}---\n\n# {name}\n", encoding="utf-8")
    return skill_dir


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "evals").mkdir()
    (tmp_path / "skills").mkdir()
    return tmp_path


def codes(findings: list[Any]) -> list[str]:
    return [finding.code for finding in findings]


# --------------------------------------------------------------------------- #
# load_suite
# --------------------------------------------------------------------------- #


def test_loads_a_valid_suite(repo: Path) -> None:
    suite_dir = write_suite(repo / "evals", "rubber-duck", valid_suite_payload())

    suite = load_suite(suite_dir)

    assert suite.skill == "rubber-duck"
    assert len(suite.trigger.negative) == 2


def test_raises_when_suite_file_is_missing(repo: Path) -> None:
    (repo / "evals" / "ghost").mkdir()

    with pytest.raises(SuiteError, match="suite.yaml"):
        load_suite(repo / "evals" / "ghost")


def test_raises_on_malformed_yaml(repo: Path) -> None:
    suite_dir = write_suite(repo / "evals", "rubber-duck", "skill: [unclosed\n")

    with pytest.raises(SuiteError):
        load_suite(suite_dir)


def test_raises_on_schema_violation_naming_the_suite(repo: Path) -> None:
    """A typo'd key must fail loudly — silently ignoring it would leave the
    suite green while checking less than the author wrote."""
    payload = valid_suite_payload()
    payload["assertions_typo"] = []
    suite_dir = write_suite(repo / "evals", "rubber-duck", payload)

    with pytest.raises(SuiteError, match="rubber-duck"):
        load_suite(suite_dir)


def test_discovers_suite_directories_sorted(repo: Path) -> None:
    write_suite(repo / "evals", "rubber-duck", valid_suite_payload())
    write_suite(repo / "evals", "learning-mode", valid_suite_payload(skill="learning-mode"))
    (repo / "evals" / "not-a-suite").mkdir()

    found = discover_suites(repo / "evals")

    assert [path.name for path in found] == ["learning-mode", "rubber-duck"]


# --------------------------------------------------------------------------- #
# validate_suite — the §7 minimum-coverage checks
# --------------------------------------------------------------------------- #


def test_valid_suite_produces_no_findings(repo: Path) -> None:
    suite_dir = write_suite(repo / "evals", "rubber-duck", valid_suite_payload())
    write_skill(repo / "skills", "rubber-duck", "0.2.0")

    findings = validate_suite(suite_dir, skills_dir=repo / "skills")

    assert findings == []


def test_flags_skill_name_not_matching_the_folder(repo: Path) -> None:
    suite_dir = write_suite(repo / "evals", "rubber-duck", valid_suite_payload(skill="steelman"))
    write_skill(repo / "skills", "rubber-duck")

    findings = validate_suite(suite_dir, skills_dir=repo / "skills")

    assert "name-mismatch" in codes(findings)
    assert all(finding.severity == "error" for finding in findings)


def test_flags_version_drift_as_a_warning(repo: Path) -> None:
    """The skill moved on without the suite being re-checked. Warning locally;
    the runner promotes it to a failure under --strict (CI)."""
    suite_dir = write_suite(repo / "evals", "rubber-duck", valid_suite_payload())
    write_skill(repo / "skills", "rubber-duck", version="0.3.0")

    findings = validate_suite(suite_dir, skills_dir=repo / "skills")

    assert codes(findings) == ["version-drift"]
    assert findings[0].severity == "warning"
    assert "0.3.0" in findings[0].message


def test_flags_a_missing_skill(repo: Path) -> None:
    suite_dir = write_suite(repo / "evals", "rubber-duck", valid_suite_payload())

    findings = validate_suite(suite_dir, skills_dir=repo / "skills")

    assert "no-skill" in codes(findings)


def test_flags_too_few_positive_triggers(repo: Path) -> None:
    payload = valid_suite_payload()
    payload["trigger"]["positive"] = payload["trigger"]["positive"][:1]
    suite_dir = write_suite(repo / "evals", "rubber-duck", payload)
    write_skill(repo / "skills", "rubber-duck")

    findings = validate_suite(suite_dir, skills_dir=repo / "skills")

    assert "too-few-positive" in codes(findings)


def test_flags_too_few_negative_triggers(repo: Path) -> None:
    payload = valid_suite_payload()
    payload["trigger"]["negative"] = payload["trigger"]["negative"][:1]
    suite_dir = write_suite(repo / "evals", "rubber-duck", payload)
    write_skill(repo / "skills", "rubber-duck")

    findings = validate_suite(suite_dir, skills_dir=repo / "skills")

    assert "too-few-negative" in codes(findings)


def test_flags_negatives_that_never_cover_a_declared_non_trigger(repo: Path) -> None:
    payload = valid_suite_payload()
    for scenario in payload["trigger"]["negative"]:
        scenario["covers_non_trigger"] = False
    suite_dir = write_suite(repo / "evals", "rubber-duck", payload)
    write_skill(repo / "skills", "rubber-duck")

    findings = validate_suite(suite_dir, skills_dir=repo / "skills")

    assert "no-non-trigger-case" in codes(findings)


def test_flags_a_suite_with_no_compliance_scenario(repo: Path) -> None:
    payload = valid_suite_payload()
    payload["compliance"] = []
    suite_dir = write_suite(repo / "evals", "rubber-duck", payload)
    write_skill(repo / "skills", "rubber-duck")

    findings = validate_suite(suite_dir, skills_dir=repo / "skills")

    assert "no-compliance" in codes(findings)


def test_flags_a_compliance_scenario_resting_only_on_a_judge(repo: Path) -> None:
    """A scenario with nothing but judge assertions can drift with the judge's
    mood; §4.1 wants deterministic checks to carry the weight."""
    payload = valid_suite_payload()
    payload["compliance"][0]["assertions"] = [{"kind": "judge", "rubric": "feels right"}]
    suite_dir = write_suite(repo / "evals", "rubber-duck", payload)
    write_skill(repo / "skills", "rubber-duck")

    findings = validate_suite(suite_dir, skills_dir=repo / "skills")

    assert "judge-only" in codes(findings)
    assert "one-question-per-turn" in findings[0].message


def test_flags_a_fixture_reference_that_does_not_resolve(repo: Path) -> None:
    payload = valid_suite_payload()
    payload["compliance"][0]["fixture"] = "with-due-topic"
    suite_dir = write_suite(repo / "evals", "rubber-duck", payload)
    write_skill(repo / "skills", "rubber-duck")

    findings = validate_suite(suite_dir, skills_dir=repo / "skills")

    assert "missing-fixture" in codes(findings)


def test_accepts_a_fixture_reference_that_resolves(repo: Path) -> None:
    payload = valid_suite_payload()
    payload["compliance"][0]["fixture"] = "with-due-topic"
    suite_dir = write_suite(repo / "evals", "rubber-duck", payload)
    (suite_dir / "fixtures" / "with-due-topic").mkdir(parents=True)
    write_skill(repo / "skills", "rubber-duck")

    findings = validate_suite(suite_dir, skills_dir=repo / "skills")

    assert findings == []
