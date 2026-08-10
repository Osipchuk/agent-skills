"""Render validation results as JSON and as a human summary (evals spec §5.2).

Same split as the CLI's ``utils/output.py``: ``build_*`` produces plain data
(JSON-serializable, the workflow artifact), ``render_*`` turns it into the text
a human reads in CI logs. Neither exits the process — the runner script owns
the exit code (§8.2).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from askill.evals.models import Finding

_SEVERITIES = ("error", "warning", "info")


def build_validation_report(
    suites: Sequence[str], findings: Sequence[Finding], *, strict: bool
) -> dict[str, Any]:
    """The machine-readable result of a ``--validate`` run.

    ``ok`` is the whole verdict: errors always sink it, warnings sink it only
    under ``strict`` (CI), and ``info`` never does — it records coverage gaps
    the library has not closed yet, which must not block a merge.
    """
    counts = {severity: 0 for severity in _SEVERITIES}
    for finding in findings:
        counts[finding.severity] += 1

    ok = counts["error"] == 0 and (not strict or counts["warning"] == 0)
    return {
        "ok": ok,
        "strict": strict,
        "suites": list(suites),
        "counts": counts,
        "findings": [finding.model_dump() for finding in findings],
    }


def render_validation_summary(report: dict[str, Any]) -> str:
    """A few lines for stdout: the headline, then one line per finding."""
    counts = report["counts"]
    headline = (
        f"evals --validate: {'OK' if report['ok'] else 'FAILED'} — "
        f"{len(report['suites'])} suite(s), "
        f"{counts['error']} error(s), {counts['warning']} warning(s), {counts['info']} info"
    )
    lines = [headline]
    for finding in report["findings"]:
        severity, skill = finding["severity"], finding["skill"]
        lines.append(f"  [{severity}] {skill}: {finding['code']} — {finding['message']}")
    return "\n".join(lines)
