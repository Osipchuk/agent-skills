#!/usr/bin/env python3
"""Fail CI if .onboard/topics.yaml references paths that no longer exist.

Stale reading lists make onboard-our-stack teach a wrong mental model, which is
worse than having no skill. Run this in CI on every PR.

Usage:
    python scripts/check_topics.py [--config .onboard/topics.yaml] [--root .]

Exit codes: 0 = all paths resolve, 1 = stale references, 2 = config problem.
Requires PyYAML (ships in essentially every Python environment).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("check_topics: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

REQUIRED_KEYS = {"one_liner", "read_in_order"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=".onboard/topics.yaml")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    config = (root / args.config).resolve()
    if not config.is_file():
        print(f"check_topics: config not found: {config}", file=sys.stderr)
        return 2

    try:
        data = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        print(f"check_topics: cannot parse {config}: {exc}", file=sys.stderr)
        return 2

    if not isinstance(data, dict):
        print("check_topics: top level must be a mapping of topics", file=sys.stderr)
        return 2

    stale: list[str] = []
    malformed: list[str] = []

    for topic, body in data.items():
        if not isinstance(body, dict) or not REQUIRED_KEYS <= body.keys():
            malformed.append(f"{topic}: missing {REQUIRED_KEYS - body.keys() if isinstance(body, dict) else REQUIRED_KEYS}")
            continue
        paths = list(body.get("read_in_order", [])) + list(body.get("adrs", []) or [])
        for rel in paths:
            if not (root / rel).exists():
                stale.append(f"{topic}: {rel}")

    if malformed:
        print("Malformed topics:", file=sys.stderr)
        for m in malformed:
            print(f"  - {m}", file=sys.stderr)
    if stale:
        print("Stale references (path no longer exists):", file=sys.stderr)
        for s in stale:
            print(f"  - {s}", file=sys.stderr)

    if malformed or stale:
        return 1
    print(f"check_topics: OK — {len(data)} topic(s), all paths resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
