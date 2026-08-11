"""Pydantic v2 models for ``evals/<name>/suite.yaml`` (evals spec §4).

A suite describes what to check about ONE skill:
  - ``trigger``    — should the skill fire on this prompt? (positive/negative)
  - ``compliance`` — with the skill active, does the agent follow its rules?

Every model forbids unknown fields. That matters more here than in the manifest
models: a silently-ignored typo in an assertion key would leave the suite green
while checking nothing, which is the one failure an eval library must not have.

``tests/unit/test_evals_models.py`` is the spec.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


class _Strict(BaseModel):
    """Shared config: reject unknown keys everywhere in a suite."""

    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- #
# Assertions
#
# Each kind is its own model so pydantic validates the per-kind fields, not just
# the ``kind`` tag. ``deterministic`` tells the validator and the runner which
# assertions need no LLM — §7 requires every compliance scenario to carry at
# least one of those, so a suite can never rest entirely on a judge's opinion.
# --------------------------------------------------------------------------- #


class FileAssertion(_Strict):
    """Workspace state: a path must exist (or must not) after the run."""

    kind: Literal["file_exists", "file_absent"]
    path: str
    deterministic: Literal[True] = True


class GrepAssertion(_Strict):
    """Workspace content: a regex must be present (or absent) under a glob."""

    kind: Literal["grep"]
    glob: str
    pattern: str
    expect: Literal["present", "absent"]
    deterministic: Literal[True] = True


class TranscriptAssertion(_Strict):
    """Transcript content: a regex over what the agent actually said/did."""

    kind: Literal["transcript"]
    pattern: str
    expect: Literal["present", "absent"]
    deterministic: Literal[True] = True


class GitAssertion(_Strict):
    """Repo hygiene: the agent must not have committed (or dirtied) the tree."""

    kind: Literal["git"]
    expect: Literal["clean", "no_commits"]
    deterministic: Literal[True] = True


class JudgeAssertion(_Strict):
    """A soft criterion an LLM judge scores against ``rubric`` (phase 2)."""

    kind: Literal["judge"]
    rubric: str
    evidence: Literal["transcript", "workspace", "both"] = "both"
    deterministic: Literal[False] = False


Assertion = Annotated[
    FileAssertion | GrepAssertion | TranscriptAssertion | GitAssertion | JudgeAssertion,
    Field(discriminator="kind"),
]


# --------------------------------------------------------------------------- #
# Scenarios
# --------------------------------------------------------------------------- #


class TriggerScenario(_Strict):
    """One trigger test: does the host pick this skill for ``prompt``?

    ``covers_non_trigger`` marks a negative that was written from an explicit
    "Do NOT use for…" clause of the skill's own description. §7 requires at
    least one such negative per suite, and only the author can attest to it —
    there is no non-LLM way to derive that link from the prompt text.
    """

    id: str
    prompt: str
    fixture: str | None = None
    covers_non_trigger: bool = False


class ComplianceScenario(_Strict):
    """One compliance test: with the skill active, are its rules followed?

    Exactly one of ``prompt`` (single turn) or ``turns`` (a scripted
    conversation) must be given.
    """

    id: str
    prompt: str | None = None
    turns: list[str] | None = None
    fixture: str | None = None
    assertions: list[Assertion] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_exactly_one_input(self) -> ComplianceScenario:
        if (self.prompt is None) == (self.turns is None):
            raise ValueError("give exactly one of prompt or turns")
        return self


class TriggerBlock(_Strict):
    """The positive/negative trigger halves of a suite."""

    positive: list[TriggerScenario] = Field(default_factory=list)
    negative: list[TriggerScenario] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Suite
# --------------------------------------------------------------------------- #


class Budget(_Strict):
    """Per-scenario ceiling enforced by the harness (phase 2)."""

    max_turns: int = Field(ge=1)
    model: str


class Thresholds(_Strict):
    """Pass bar for the suite as a whole."""

    trigger_accuracy: float = Field(ge=0.0, le=1.0)
    compliance_pass_rate: float = Field(ge=0.0, le=1.0)


def _duplicates(values: Iterable[str]) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)


class Finding(_Strict):
    """One problem found by static validation (evals spec §7).

    ``error`` always fails the run. ``warning`` fails only under ``--strict``
    (which CI passes) — version drift is the motivating case: a nuisance while
    you iterate locally, a merge blocker on a PR. ``info`` never fails; it
    records coverage gaps the library has not closed yet.
    """

    severity: Literal["error", "warning", "info"]
    code: str
    skill: str
    message: str


class EvalSuite(_Strict):
    """A whole ``evals/<name>/suite.yaml``."""

    skill: str = Field(pattern=r"^[a-z][a-z0-9-]{2,63}$")
    version_tested: str
    budget: Budget
    trigger: TriggerBlock
    compliance: list[ComplianceScenario] = Field(default_factory=list)
    thresholds: Thresholds

    @model_validator(mode="after")
    def _check_version_tested(self) -> EvalSuite:
        if not _SEMVER_RE.fullmatch(self.version_tested):
            raise ValueError(
                f"version_tested must be strict MAJOR.MINOR.PATCH, got {self.version_tested!r}"
            )
        return self

    @model_validator(mode="after")
    def _check_unique_scenario_ids(self) -> EvalSuite:
        duplicates = _duplicates(scenario.id for scenario in self.scenarios())
        if duplicates:
            raise ValueError("duplicate scenario id: " + ", ".join(duplicates))
        return self

    def scenarios(self) -> list[TriggerScenario | ComplianceScenario]:
        """Every scenario in the suite, trigger tests first."""
        return [*self.trigger.positive, *self.trigger.negative, *self.compliance]
