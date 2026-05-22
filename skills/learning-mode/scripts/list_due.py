#!/usr/bin/env python3
"""
list_due.py — Read a progress.md file and print topics whose next_review date
is today or earlier. Zero external dependencies (stdlib only).

Usage:
    python3 list_due.py <path/to/progress.md> [--today YYYY-MM-DD] [--json]

Output (default, human-readable):
    Each due topic on its own line:
        <topic>  (stage N, due since YYYY-MM-DD)

Output (--json):
    A JSON array of objects with keys: topic, stage, last_practice, next_review,
    last_outcome, notes, overdue_days.

Exit codes:
    0 — script ran (regardless of whether any topics were due)
    1 — file not found or could not be parsed
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

# Stage -> days for the next interval after a successful review at this stage.
STAGE_INTERVALS_DAYS = {0: 1, 1: 3, 2: 7, 3: 14, 4: 30, 5: 60, 6: 120}


def parse_progress(path: Path) -> list[dict]:
    """
    Parse progress.md and return one dict per topic row.

    Expected format is a markdown table with the columns:
        Topic | Stage | Last practice | Next review | Last outcome | Notes

    The header row and the separator row (---) are skipped. Empty / malformed
    rows are skipped silently.
    """
    text = path.read_text(encoding="utf-8")
    rows: list[dict] = []

    # Match lines that look like table rows: start and end with |.
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        # Strip the outer pipes and split.
        cells = [c.strip() for c in line[1:-1].split("|")]
        if len(cells) < 4:
            continue
        # Skip the header row.
        if cells[0].lower() == "topic":
            continue
        # Skip the separator row (cells made of dashes and colons).
        if all(re.fullmatch(r":?-+:?", c) for c in cells if c):
            continue

        # Pad to 6 columns so we don't crash on shorter rows.
        while len(cells) < 6:
            cells.append("")

        topic, stage_s, last_practice, next_review, last_outcome, notes = cells[:6]
        # Strip backticks that some users add for code-styling.
        topic = topic.strip("` ")
        try:
            stage = int(stage_s)
        except ValueError:
            # Row's stage column isn't a number — skip rather than guess.
            continue

        rows.append(
            {
                "topic": topic,
                "stage": stage,
                "last_practice": last_practice,
                "next_review": next_review,
                "last_outcome": last_outcome,
                "notes": notes,
            }
        )

    return rows


def filter_due(rows: list[dict], today: dt.date) -> list[dict]:
    """Return rows whose next_review is on or before today, sorted most-overdue first."""
    due = []
    for r in rows:
        try:
            nr = dt.date.fromisoformat(r["next_review"])
        except ValueError:
            # Malformed date — skip, don't crash.
            continue
        if nr <= today:
            r["overdue_days"] = (today - nr).days
            due.append(r)
    due.sort(key=lambda r: r["overdue_days"], reverse=True)
    return due


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="List due topics from progress.md")
    parser.add_argument("path", help="Path to progress.md")
    parser.add_argument(
        "--today",
        default=None,
        help="Override today's date for testing (YYYY-MM-DD). Defaults to system today.",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output JSON instead of human-readable text."
    )
    args = parser.parse_args(argv)

    path = Path(args.path)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        return 1

    try:
        rows = parse_progress(path)
    except Exception as e:  # noqa: BLE001
        print(f"Error parsing {path}: {e}", file=sys.stderr)
        return 1

    today = (
        dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    )

    due = filter_due(rows, today)

    if args.json:
        print(json.dumps(due, indent=2, ensure_ascii=False))
        return 0

    if not due:
        print("No topics due for review.")
        return 0

    print(f"{len(due)} topic(s) due as of {today.isoformat()}:")
    for r in due:
        overdue = r["overdue_days"]
        when = "due today" if overdue == 0 else f"overdue by {overdue}d"
        print(f"  - {r['topic']}  (stage {r['stage']}, {when})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
