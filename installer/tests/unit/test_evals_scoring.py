"""Tests for askill.evals.scoring — verdicts to metrics to pass/fail.

These tests are the SPEC for evals/scoring.py (evals spec §4, §5.4). Pure
aggregation: no I/O, no LLM. The thresholds question it answers is "did this
suite clear its own bar", which is what the runner's exit code reports.
"""

from __future__ import annotations

from askill.evals.models import Thresholds
from askill.evals.scoring import ScenarioVerdict, score_suite

STRICT = Thresholds(trigger_accuracy=1.0, compliance_pass_rate=1.0)


def verdict(scenario_id: str, *, kind: str = "trigger", passed: bool = True) -> ScenarioVerdict:
    return ScenarioVerdict(scenario_id=scenario_id, kind=kind, passed=passed, detail="")


def test_all_green_clears_a_strict_bar() -> None:
    result = score_suite(
        "rubber-duck",
        [verdict("a"), verdict("b"), verdict("c", kind="compliance")],
        thresholds=STRICT,
    )

    assert result.passed
    assert result.trigger_accuracy == 1.0
    assert result.compliance_pass_rate == 1.0


def test_one_failed_trigger_sinks_a_strict_suite() -> None:
    result = score_suite(
        "rubber-duck",
        [verdict("a"), verdict("b", passed=False), verdict("c", kind="compliance")],
        thresholds=STRICT,
    )

    assert not result.passed
    assert result.trigger_accuracy == 0.5


def test_metrics_are_tracked_separately_per_kind() -> None:
    result = score_suite(
        "learning-mode",
        [
            verdict("t1"),
            verdict("t2", passed=False),
            verdict("c1", kind="compliance"),
            verdict("c2", kind="compliance"),
        ],
        thresholds=STRICT,
    )

    assert result.trigger_accuracy == 0.5
    assert result.compliance_pass_rate == 1.0


def test_a_lowered_threshold_lets_a_partial_failure_through() -> None:
    lenient = Thresholds(trigger_accuracy=0.5, compliance_pass_rate=1.0)

    result = score_suite(
        "rubber-duck",
        [verdict("a"), verdict("b", passed=False), verdict("c", kind="compliance")],
        thresholds=lenient,
    )

    assert result.passed


def test_an_empty_category_scores_one_rather_than_dividing_by_zero() -> None:
    """A suite with no compliance scenarios must not crash the runner. Static
    validation is what rejects that suite; scoring just must not explode."""
    result = score_suite("rubber-duck", [verdict("a"), verdict("b")], thresholds=STRICT)

    assert result.compliance_pass_rate == 1.0
    assert result.passed


def test_failed_scenarios_are_listed_for_the_report() -> None:
    result = score_suite(
        "rubber-duck",
        [verdict("a"), verdict("b", passed=False), verdict("c", kind="compliance", passed=False)],
        thresholds=STRICT,
    )

    assert result.failed_ids == ["b", "c"]
