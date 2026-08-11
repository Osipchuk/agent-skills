"""Tests for scripts/run_evals.py — the --validate entry point (evals spec §5.1).

Exercises the script's ``main()`` the way CI does, over a temp library, and
pins the exit-code contract from the main spec §8.2: 0 success, 1 findings that
fail the run, 2 a system/usage error.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from tests.unit.test_evals_loader import valid_suite_payload, write_skill, write_suite

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "run_evals.py"


def load_script() -> ModuleType:
    """Import run_evals.py by path — it is a maintenance script, not a package."""
    spec = importlib.util.spec_from_file_location("run_evals", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_evals"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def run_evals() -> ModuleType:
    return load_script()


@pytest.fixture
def library(tmp_path: Path) -> Path:
    """A temp repo with one valid suite for one skill."""
    (tmp_path / "evals").mkdir()
    (tmp_path / "skills").mkdir()
    write_suite(tmp_path / "evals", "rubber-duck", valid_suite_payload())
    write_skill(tmp_path / "skills", "rubber-duck", "0.2.0")
    return tmp_path


def args_for(library: Path, *extra: str) -> list[str]:
    return [
        "--validate",
        "--evals-root",
        str(library / "evals"),
        "--skills-dir",
        str(library / "skills"),
        *extra,
    ]


def test_clean_library_exits_zero(run_evals: ModuleType, library: Path) -> None:
    assert run_evals.main(args_for(library)) == 0


def test_an_error_finding_exits_one(run_evals: ModuleType, library: Path) -> None:
    payload = valid_suite_payload()
    payload["compliance"] = []
    write_suite(library / "evals", "rubber-duck", payload)

    assert run_evals.main(args_for(library)) == 1


def test_version_drift_passes_locally_but_fails_under_strict(
    run_evals: ModuleType, library: Path
) -> None:
    """The §8.1 contract: editing a skill without re-checking its suite is a
    nuisance locally and a merge blocker in CI."""
    write_skill(library / "skills", "rubber-duck", version="0.9.0")

    assert run_evals.main(args_for(library)) == 0
    assert run_evals.main(args_for(library, "--strict")) == 1


def test_missing_skills_dir_is_a_system_error(run_evals: ModuleType, tmp_path: Path) -> None:
    exit_code = run_evals.main(
        [
            "--validate",
            "--evals-root",
            str(tmp_path / "evals"),
            "--skills-dir",
            str(tmp_path / "no"),
        ]
    )

    assert exit_code == 2


def test_running_without_validate_is_a_usage_error(run_evals: ModuleType, library: Path) -> None:
    """Phase 1 has no transport; the script must say so rather than exit 0 as
    if it had run the scenarios."""
    exit_code = run_evals.main(
        ["--evals-root", str(library / "evals"), "--skills-dir", str(library / "skills")]
    )

    assert exit_code == 2


def test_selecting_an_unknown_skill_is_a_usage_error(run_evals: ModuleType, library: Path) -> None:
    assert run_evals.main(args_for(library, "ghost-skill")) == 2


def test_selecting_one_skill_narrows_the_report(
    run_evals: ModuleType, library: Path, tmp_path: Path
) -> None:
    write_suite(library / "evals", "learning-mode", valid_suite_payload(skill="learning-mode"))
    write_skill(library / "skills", "learning-mode", "0.2.0")
    report_path = tmp_path / "report.json"

    run_evals.main(args_for(library, "rubber-duck", "--report", str(report_path)))

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["suites"] == ["rubber-duck"]


def test_report_file_is_written_as_json(
    run_evals: ModuleType, library: Path, tmp_path: Path
) -> None:
    report_path = tmp_path / "report.json"

    run_evals.main(args_for(library, "--report", str(report_path)))

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert report["counts"]["error"] == 0
