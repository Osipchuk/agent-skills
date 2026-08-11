"""Load ``evals/<name>/suite.yaml`` and statically validate it (evals spec §7).

This is the cheap gate: no LLM, no network, no subprocess. It answers one
question — "is this suite still a meaningful test of its skill?" — and it is
what runs on every PR (§8.1).

The checks it can make are exactly the mechanical ones. Whether a negative
trigger really corresponds to a "Do NOT use for…" clause is a judgment only the
author can make, so the suite declares it (``covers_non_trigger``) and this
module verifies the declaration exists.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from askill.core.manifest import parse_frontmatter
from askill.evals.models import EvalSuite, Finding

SUITE_FILENAME = "suite.yaml"

# §7 minimum coverage.
_MIN_POSITIVE = 2
_MIN_NEGATIVE = 2


class SuiteError(Exception):
    """A suite file is missing, unparseable, or violates the schema."""


def discover_suites(evals_root: Path) -> list[Path]:
    """Every ``<evals_root>/*/`` that contains a suite file, sorted by name."""
    if not evals_root.is_dir():
        return []
    return [child for child in sorted(evals_root.iterdir()) if (child / SUITE_FILENAME).is_file()]


def load_suite(suite_dir: Path) -> EvalSuite:
    """Parse and schema-validate ``<suite_dir>/suite.yaml``.

    Raises :class:`SuiteError` (never a bare pydantic/yaml error) so callers can
    report every broken suite uniformly instead of dying on the first one.
    """
    path = suite_dir / SUITE_FILENAME
    if not path.is_file():
        raise SuiteError(f"{suite_dir.name}: missing {SUITE_FILENAME}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise SuiteError(f"{suite_dir.name}: {SUITE_FILENAME} is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise SuiteError(f"{suite_dir.name}: {SUITE_FILENAME} must be a YAML mapping")
    try:
        return EvalSuite.model_validate(data)
    except ValidationError as exc:
        raise SuiteError(
            f"{suite_dir.name}: {SUITE_FILENAME} does not match the schema: {exc}"
        ) from exc


def _skill_version(skills_dir: Path, name: str) -> str | None:
    """The ``version`` from ``skills/<name>/SKILL.md``, or None if absent."""
    skill_md = skills_dir / name / "SKILL.md"
    if not skill_md.is_file():
        return None
    front = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    version = front.get("version")
    return version if isinstance(version, str) else None


def validate_suite(suite_dir: Path, *, skills_dir: Path) -> list[Finding]:
    """Run the §7 checks against one suite. Empty list means it is in good shape.

    Findings are returned rather than raised: one run should report everything
    wrong across the library, not stop at the first problem.
    """
    suite = load_suite(suite_dir)
    findings: list[Finding] = []
    folder = suite_dir.name

    if suite.skill != folder:
        findings.append(
            Finding(
                severity="error",
                code="name-mismatch",
                skill=folder,
                message=f"suite declares skill {suite.skill!r} but lives in evals/{folder}/",
            )
        )

    findings.extend(_version_findings(suite, folder, skills_dir))
    findings.extend(_coverage_findings(suite, folder))
    findings.extend(_fixture_findings(suite, folder, suite_dir))
    return findings


def validate_library(evals_root: Path, *, skills_dir: Path) -> tuple[list[str], list[Finding]]:
    """Validate every suite under ``evals_root``; return ``(suite names, findings)``.

    A suite that will not even load becomes an ``unloadable`` finding rather
    than an exception — one broken file must not hide the state of the rest.
    Skills with no suite are reported as ``info``: coverage the library has yet
    to build is worth seeing, but it must not block merges while the backlog
    is being worked through.
    """
    findings: list[Finding] = []
    names: list[str] = []

    for suite_dir in discover_suites(evals_root):
        names.append(suite_dir.name)
        try:
            findings.extend(validate_suite(suite_dir, skills_dir=skills_dir))
        except SuiteError as exc:
            findings.append(
                Finding(severity="error", code="unloadable", skill=suite_dir.name, message=str(exc))
            )

    covered = set(names)
    for skill_dir in sorted(skills_dir.iterdir()) if skills_dir.is_dir() else []:
        if (skill_dir / "SKILL.md").is_file() and skill_dir.name not in covered:
            findings.append(
                Finding(
                    severity="info",
                    code="no-suite",
                    skill=skill_dir.name,
                    message=f"no evals/{skill_dir.name}/suite.yaml yet",
                )
            )
    return names, findings


def _version_findings(suite: EvalSuite, folder: str, skills_dir: Path) -> list[Finding]:
    """Compare ``version_tested`` against the skill's actual version."""
    actual = _skill_version(skills_dir, suite.skill)
    if actual is None:
        return [
            Finding(
                severity="error",
                code="no-skill",
                skill=folder,
                message=f"no skills/{suite.skill}/SKILL.md for this suite",
            )
        ]
    if actual != suite.version_tested:
        return [
            Finding(
                severity="warning",
                code="version-drift",
                skill=folder,
                message=(
                    f"suite was written against {suite.version_tested}, "
                    f"but the skill is now {actual} — re-run the suite and bump version_tested"
                ),
            )
        ]
    return []


def _coverage_findings(suite: EvalSuite, folder: str) -> list[Finding]:
    """The §7 minimum: enough triggers both ways, and real compliance checks."""
    findings: list[Finding] = []

    if len(suite.trigger.positive) < _MIN_POSITIVE:
        findings.append(
            Finding(
                severity="error",
                code="too-few-positive",
                skill=folder,
                message=f"needs at least {_MIN_POSITIVE} positive trigger tests",
            )
        )
    if len(suite.trigger.negative) < _MIN_NEGATIVE:
        findings.append(
            Finding(
                severity="error",
                code="too-few-negative",
                skill=folder,
                message=f"needs at least {_MIN_NEGATIVE} negative trigger tests",
            )
        )
    elif not any(scenario.covers_non_trigger for scenario in suite.trigger.negative):
        findings.append(
            Finding(
                severity="error",
                code="no-non-trigger-case",
                skill=folder,
                message=(
                    "no negative declares covers_non_trigger — at least one must come "
                    "from the skill description's own 'Do NOT use for…' clause"
                ),
            )
        )

    if not suite.compliance:
        findings.append(
            Finding(
                severity="error",
                code="no-compliance",
                skill=folder,
                message="needs at least one compliance scenario",
            )
        )
    for scenario in suite.compliance:
        if not any(assertion.deterministic for assertion in scenario.assertions):
            findings.append(
                Finding(
                    severity="error",
                    code="judge-only",
                    skill=folder,
                    message=(
                        f"compliance scenario {scenario.id!r} has only judge assertions; "
                        "it needs at least one deterministic check"
                    ),
                )
            )
    return findings


def _fixture_findings(suite: EvalSuite, folder: str, suite_dir: Path) -> list[Finding]:
    """Every ``fixture:`` must resolve to ``<suite_dir>/fixtures/<id>/``."""
    findings: list[Finding] = []
    for scenario in suite.scenarios():
        fixture = scenario.fixture
        if fixture is None:
            continue
        if not (suite_dir / "fixtures" / fixture).is_dir():
            findings.append(
                Finding(
                    severity="error",
                    code="missing-fixture",
                    skill=folder,
                    message=f"scenario {scenario.id!r} references missing fixture {fixture!r}",
                )
            )
    return findings
