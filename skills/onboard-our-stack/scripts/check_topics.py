#!/usr/bin/env python3
"""Fail CI if .onboard/topics.yaml is malformed or references paths that no
longer exist.

Stale reading lists make onboard-our-stack teach a wrong mental model, which is
worse than having no skill. Run this in CI on every PR.

Usage:
    python scripts/check_topics.py [--config .onboard/topics.yaml] [--root .]

Exit codes: 0 = OK, 1 = stale/invalid references, 2 = config problem.
Requires PyYAML — the one deviation from the library's stdlib-only convention,
because topics.yaml is YAML; the script exits with a clear install hint when
it's missing (`pip install pyyaml`), and CI images typically have it.
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


def extract_topics(data: dict) -> tuple[dict, list]:
    """Support both the nested form ({onboarding_path, topics}) and the legacy
    flat form (top level is the topics map)."""
    if "topics" in data and isinstance(data["topics"], dict):
        return data["topics"], list(data.get("onboarding_path", []) or [])
    topics = {k: v for k, v in data.items() if k != "onboarding_path"}
    return topics, list(data.get("onboarding_path", []) or [])


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
        print("check_topics: top level must be a mapping", file=sys.stderr)
        return 2

    topics, path = extract_topics(data)

    stale: list[str] = []
    malformed: list[str] = []
    bad_path: list[str] = []

    for topic, body in topics.items():
        if not isinstance(body, dict) or not REQUIRED_KEYS <= body.keys():
            missing = REQUIRED_KEYS - body.keys() if isinstance(body, dict) else REQUIRED_KEYS
            malformed.append(f"{topic}: missing {missing}")
            continue
        paths = list(body.get("read_in_order", [])) + list(body.get("adrs", []) or [])
        for rel in paths:
            # placeholder slots like "<handler>" are template markers, skip them
            if rel.strip().startswith("<"):
                continue
            if not (root / rel).exists():
                stale.append(f"{topic}: {rel}")

    for key in path:
        if key not in topics:
            bad_path.append(f"onboarding_path references unknown topic '{key}'")

    for label, items in (("Malformed topics", malformed),
                         ("Stale references (path missing)", stale),
                         ("Broken onboarding_path", bad_path)):
        if items:
            print(f"{label}:", file=sys.stderr)
            for i in items:
                print(f"  - {i}", file=sys.stderr)

    if malformed or stale or bad_path:
        return 1
    print(f"check_topics: OK — {len(topics)} topic(s), {len(path)} in path, all paths resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
