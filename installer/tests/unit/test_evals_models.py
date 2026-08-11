"""Tests for askill.evals.models — the pydantic schema of ``evals/<name>/suite.yaml``.

These tests are the SPEC for evals/models.py (evals spec §4). Every model
forbids unknown fields, so a typo in a suite fails loudly instead of being
silently ignored — a silently-dropped assertion would make a suite pass while
testing nothing.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from askill.evals.models import (
    Budget,
    ComplianceScenario,
    EvalSuite,
    Thresholds,
    TriggerBlock,
    TriggerScenario,
)


def valid_suite_dict(**overrides: Any) -> dict[str, Any]:
    """A minimal-but-complete valid suite payload; override per-test."""
    base: dict[str, Any] = {
        "skill": "learning-mode",
        "version_tested": "0.2.0",
        "budget": {"max_turns": 8, "model": "claude-sonnet-4-6"},
        "trigger": {
            "positive": [
                {"id": "coach-me", "prompt": "Coach me on decorators."},
                {"id": "teach-me", "prompt": "Teach me pytest fixtures."},
            ],
            "negative": [
                {"id": "just-ship", "prompt": "Write it for me.", "covers_non_trigger": True},
                {"id": "factual", "prompt": "What does functools.wraps do?"},
            ],
        },
        "compliance": [
            {
                "id": "handoff-leaves-gap",
                "prompt": "Teach me validators.",
                "assertions": [{"kind": "file_exists", "path": ".claude/learning/active-task.md"}],
            }
        ],
        "thresholds": {"trigger_accuracy": 1.0, "compliance_pass_rate": 1.0},
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# EvalSuite
# --------------------------------------------------------------------------- #


def test_accepts_a_complete_valid_suite() -> None:
    suite = EvalSuite.model_validate(valid_suite_dict())

    assert suite.skill == "learning-mode"
    assert suite.version_tested == "0.2.0"
    assert len(suite.trigger.positive) == 2
    assert len(suite.compliance) == 1


def test_rejects_unknown_top_level_key() -> None:
    with pytest.raises(ValidationError):
        EvalSuite.model_validate(valid_suite_dict(judge_model="haiku"))


def test_rejects_non_kebab_skill_name() -> None:
    with pytest.raises(ValidationError):
        EvalSuite.model_validate(valid_suite_dict(skill="Learning_Mode"))


def test_rejects_loose_version_tested() -> None:
    with pytest.raises(ValidationError):
        EvalSuite.model_validate(valid_suite_dict(version_tested="0.2"))


def test_rejects_duplicate_scenario_ids_across_the_whole_suite() -> None:
    """Ids must be unique suite-wide: the report keys results by id, so a
    duplicate would silently overwrite another scenario's verdict."""
    payload = valid_suite_dict()
    payload["compliance"][0]["id"] = "coach-me"  # already a positive trigger id

    with pytest.raises(ValidationError, match="duplicate scenario id"):
        EvalSuite.model_validate(payload)


# --------------------------------------------------------------------------- #
# Budget / Thresholds
# --------------------------------------------------------------------------- #


def test_budget_rejects_non_positive_max_turns() -> None:
    with pytest.raises(ValidationError):
        Budget.model_validate({"max_turns": 0, "model": "claude-sonnet-4-6"})


def test_thresholds_reject_a_rate_above_one() -> None:
    with pytest.raises(ValidationError):
        Thresholds.model_validate({"trigger_accuracy": 1.5, "compliance_pass_rate": 1.0})


# --------------------------------------------------------------------------- #
# Trigger scenarios
# --------------------------------------------------------------------------- #


def test_trigger_scenario_defaults_covers_non_trigger_to_false() -> None:
    scenario = TriggerScenario.model_validate({"id": "x", "prompt": "hello"})

    assert scenario.covers_non_trigger is False
    assert scenario.fixture is None


def test_trigger_block_rejects_an_unknown_key() -> None:
    with pytest.raises(ValidationError):
        TriggerBlock.model_validate({"positive": [], "negative": [], "maybe": []})


# --------------------------------------------------------------------------- #
# Compliance scenarios and their assertions
# --------------------------------------------------------------------------- #


def test_compliance_scenario_accepts_a_multi_turn_script() -> None:
    scenario = ComplianceScenario.model_validate(
        {
            "id": "closeout",
            "turns": ["Teach me validators.", "{{submit: user fills the stub}}", "Done, review."],
            "assertions": [{"kind": "file_absent", "path": ".claude/learning/active-task.md"}],
        }
    )

    assert scenario.turns is not None
    assert len(scenario.turns) == 3
    assert scenario.prompt is None


def test_compliance_scenario_requires_a_prompt_or_turns() -> None:
    with pytest.raises(ValidationError, match="prompt.*turns"):
        ComplianceScenario.model_validate(
            {"id": "x", "assertions": [{"kind": "git", "expect": "clean"}]}
        )


def test_compliance_scenario_rejects_both_prompt_and_turns() -> None:
    """Ambiguous input: the harness would have to guess which one to run."""
    with pytest.raises(ValidationError, match="prompt.*turns"):
        ComplianceScenario.model_validate(
            {
                "id": "x",
                "prompt": "one shot",
                "turns": ["a", "b"],
                "assertions": [{"kind": "git", "expect": "clean"}],
            }
        )


def test_compliance_scenario_requires_at_least_one_assertion() -> None:
    with pytest.raises(ValidationError):
        ComplianceScenario.model_validate({"id": "x", "prompt": "hi", "assertions": []})


def test_grep_assertion_parses_into_its_own_type() -> None:
    scenario = ComplianceScenario.model_validate(
        {
            "id": "x",
            "prompt": "hi",
            "assertions": [
                {"kind": "grep", "glob": "**/*.py", "pattern": "LEARNING TASK", "expect": "present"}
            ],
        }
    )

    assertion = scenario.assertions[0]
    assert assertion.kind == "grep"
    assert assertion.glob == "**/*.py"
    assert assertion.expect == "present"


def test_judge_assertion_defaults_evidence_to_both() -> None:
    scenario = ComplianceScenario.model_validate(
        {
            "id": "x",
            "prompt": "hi",
            "assertions": [{"kind": "judge", "rubric": "The assistant must not write the body."}],
        }
    )

    assert scenario.assertions[0].evidence == "both"


def test_rejects_an_unknown_assertion_kind() -> None:
    with pytest.raises(ValidationError):
        ComplianceScenario.model_validate(
            {"id": "x", "prompt": "hi", "assertions": [{"kind": "vibes", "rubric": "feels right"}]}
        )


def test_rejects_a_grep_assertion_missing_its_glob() -> None:
    """The discriminated union must validate per-kind fields, not just the tag."""
    with pytest.raises(ValidationError):
        ComplianceScenario.model_validate(
            {
                "id": "x",
                "prompt": "hi",
                "assertions": [{"kind": "grep", "pattern": "x", "expect": "present"}],
            }
        )


def test_rejects_an_invalid_grep_expectation() -> None:
    with pytest.raises(ValidationError):
        ComplianceScenario.model_validate(
            {
                "id": "x",
                "prompt": "hi",
                "assertions": [{"kind": "grep", "glob": "**/*", "pattern": "x", "expect": "maybe"}],
            }
        )


def test_deterministic_flag_separates_judge_from_the_rest() -> None:
    """--validate requires each compliance scenario to carry at least one
    deterministic assertion; the models expose which kinds those are."""
    scenario = ComplianceScenario.model_validate(
        {
            "id": "x",
            "prompt": "hi",
            "assertions": [
                {"kind": "judge", "rubric": "tone is right"},
                {"kind": "file_exists", "path": "a.md"},
            ],
        }
    )

    assert [a.deterministic for a in scenario.assertions] == [False, True]
