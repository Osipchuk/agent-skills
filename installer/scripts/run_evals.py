"""Run the skill eval suites under ``evals/`` (evals spec §5.1).

Maintenance / CI script — *not* part of the ``askill`` CLI surface. Run from
``installer/``::

    uv run python scripts/run_evals.py --validate            # every suite
    uv run python scripts/run_evals.py --validate rubber-duck
    uv run python scripts/run_evals.py --validate --strict   # what CI runs
    uv run python scripts/run_evals.py --validate --json --report out.json

Phase 1 implements ``--validate`` only: static checks with no LLM, no network
and no API key, which is what runs on every PR (§8.1). Executing scenarios
against a real agent needs the transport layer and lands in phase 2; asking for
it here is a usage error rather than a silent exit 0 that ran nothing.

Exit codes follow the main spec §8.2: ``0`` all good, ``1`` findings that fail
the run, ``2`` a system or usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from askill.evals.loader import validate_library
from askill.evals.report import build_validation_report, render_validation_summary

# scripts/ -> installer/ -> <repo root>
REPO_ROOT = Path(__file__).resolve().parents[2]


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and run skill eval suites.")
    parser.add_argument("skills", nargs="*", help="only these skills (default: all suites)")
    parser.add_argument(
        "--validate", action="store_true", help="static validation only (no LLM calls)"
    )
    parser.add_argument(
        "--strict", action="store_true", help="treat warnings as failures; CI passes this"
    )
    parser.add_argument("--json", action="store_true", help="print the JSON report instead")
    parser.add_argument("--report", type=Path, help="write the JSON report to this path")
    parser.add_argument("--evals-root", type=Path, default=REPO_ROOT / "evals")
    parser.add_argument("--skills-dir", type=Path, default=REPO_ROOT / "skills")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if not args.validate:
        print(
            "run_evals.py: only --validate is implemented (phase 1). Running scenarios "
            "against an agent needs the transport layer (evals spec §5.2).",
            file=sys.stderr,
        )
        return 2
    if not args.skills_dir.is_dir():
        print(f"run_evals.py: no skills directory at {args.skills_dir}", file=sys.stderr)
        return 2

    suites, findings = validate_library(args.evals_root, skills_dir=args.skills_dir)

    if args.skills:
        selected = set(args.skills)
        unknown = selected - set(suites)
        if unknown:
            print(f"run_evals.py: no suite for {', '.join(sorted(unknown))}", file=sys.stderr)
            return 2
        suites = [name for name in suites if name in selected]
        findings = [finding for finding in findings if finding.skill in selected]

    report = build_validation_report(suites, findings, strict=args.strict)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2) if args.json else render_validation_summary(report))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
