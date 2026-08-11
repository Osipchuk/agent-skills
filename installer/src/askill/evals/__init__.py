"""Eval library for the skills in this repo (evals spec).

Deterministic core only in phase 1: models, loader, assertions, scoring and
reporting. Agent/judge execution lives behind ``transport`` (phase 2), so
everything here is pure and unit-testable without an API key.
"""
