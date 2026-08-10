"""Tests for askill.evals.report — the JSON artifact and the stdout summary.

These tests are the SPEC for evals/report.py (evals spec §5.2, §8.2). The same
split as the CLI's utils/output.py: one function builds data, another renders
text, and neither decides the exit code.
"""

from __future__ import annotations

import json

from askill.evals.models import Finding
from askill.evals.report import build_validation_report, render_validation_summary


def finding(code: str, *, severity: str = "error", skill: str = "rubber-duck") -> Finding:
    return Finding(severity=severity, code=code, skill=skill, message=f"{code} happened")


# --------------------------------------------------------------------------- #
# build_validation_report — the machine-readable artifact
# --------------------------------------------------------------------------- #


def test_report_of_a_clean_run_is_ok_and_serializable() -> None:
    report = build_validation_report(["learning-mode", "rubber-duck"], [], strict=False)

    assert report["ok"] is True
    assert report["suites"] == ["learning-mode", "rubber-duck"]
    assert report["counts"] == {"error": 0, "warning": 0, "info": 0}
    json.dumps(report)  # must not raise


def test_errors_make_the_report_not_ok() -> None:
    report = build_validation_report(["rubber-duck"], [finding("no-compliance")], strict=False)

    assert report["ok"] is False
    assert report["counts"]["error"] == 1
    assert report["findings"][0]["code"] == "no-compliance"


def test_warnings_alone_stay_ok_when_not_strict() -> None:
    report = build_validation_report(
        ["rubber-duck"], [finding("version-drift", severity="warning")], strict=False
    )

    assert report["ok"] is True
    assert report["counts"]["warning"] == 1


def test_warnings_fail_the_run_under_strict() -> None:
    """CI runs --strict so a PR that edits a skill without re-checking its
    suite cannot merge (spec §8.1)."""
    report = build_validation_report(
        ["rubber-duck"], [finding("version-drift", severity="warning")], strict=True
    )

    assert report["ok"] is False


def test_info_findings_never_fail_the_run_even_under_strict() -> None:
    report = build_validation_report(
        ["rubber-duck"], [finding("no-suite", severity="info")], strict=True
    )

    assert report["ok"] is True
    assert report["counts"]["info"] == 1


# --------------------------------------------------------------------------- #
# render_validation_summary — what a human reads in CI logs
# --------------------------------------------------------------------------- #


def test_summary_of_a_clean_run_says_how_many_suites_were_checked() -> None:
    report = build_validation_report(["learning-mode", "rubber-duck"], [], strict=False)

    text = render_validation_summary(report)

    assert "2 suite(s)" in text
    assert "OK" in text


def test_summary_shows_each_finding_with_skill_and_code() -> None:
    report = build_validation_report(
        ["rubber-duck"],
        [finding("no-compliance"), finding("version-drift", severity="warning")],
        strict=False,
    )

    text = render_validation_summary(report)

    assert "rubber-duck" in text
    assert "no-compliance" in text
    assert "version-drift" in text
    assert "error" in text and "warning" in text


def test_summary_reports_zero_suites_rather_than_looking_clean() -> None:
    """An empty evals/ dir must not read as 'everything passed'."""
    report = build_validation_report([], [], strict=False)

    assert "0 suite(s)" in render_validation_summary(report)
