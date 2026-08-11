"""Aggregate scenario verdicts into suite metrics (evals spec §5.2).

Pure: verdicts in, metrics and a pass/fail out. The transport that produced the
verdicts lives elsewhere, so this module is fully unit-testable and the
threshold logic can be reasoned about without running an agent.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from askill.evals.models import Thresholds


@dataclass(frozen=True)
class ScenarioVerdict:
    """The outcome of one scenario. ``kind`` is ``trigger`` or ``compliance``."""

    scenario_id: str
    kind: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class SuiteResult:
    """One suite's metrics and whether it cleared its thresholds."""

    skill: str
    trigger_accuracy: float
    compliance_pass_rate: float
    passed: bool
    failed_ids: list[str] = field(default_factory=list)


def _rate(verdicts: Sequence[ScenarioVerdict]) -> float:
    """Share of passing verdicts; an empty category scores 1.0.

    Empty means "nothing was asked of this category here" — a suite that is
    missing a category is rejected by static validation (§7), not by scoring
    silently dividing by zero.
    """
    if not verdicts:
        return 1.0
    return sum(1 for verdict in verdicts if verdict.passed) / len(verdicts)


def score_suite(
    skill: str, verdicts: Sequence[ScenarioVerdict], *, thresholds: Thresholds
) -> SuiteResult:
    """Roll verdicts up into per-category rates and compare against thresholds."""
    trigger_accuracy = _rate([v for v in verdicts if v.kind == "trigger"])
    compliance_pass_rate = _rate([v for v in verdicts if v.kind == "compliance"])
    return SuiteResult(
        skill=skill,
        trigger_accuracy=trigger_accuracy,
        compliance_pass_rate=compliance_pass_rate,
        passed=(
            trigger_accuracy >= thresholds.trigger_accuracy
            and compliance_pass_rate >= thresholds.compliance_pass_rate
        ),
        failed_ids=[verdict.scenario_id for verdict in verdicts if not verdict.passed],
    )
