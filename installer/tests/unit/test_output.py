"""Tests for askill.utils.output — the JSON-vs-human switch."""

from __future__ import annotations

import json
from typing import Any

import pytest

from askill.core.models import RegistrySkill
from askill.utils.output import render_skill_info, render_skill_list


def _skills(registry_payload: dict[str, Any]) -> list[RegistrySkill]:
    return [RegistrySkill(**s) for s in registry_payload["skills"]]


def test_render_list_json(
    capsys: pytest.CaptureFixture[str], registry_payload: dict[str, Any]
) -> None:
    render_skill_list(_skills(registry_payload), None, json_mode=True)
    out = json.loads(capsys.readouterr().out)
    assert [row["name"] for row in out] == ["learning-mode", "article-translator"]
    assert all(row["installed"] is None for row in out)


def test_render_list_human_has_names(
    capsys: pytest.CaptureFixture[str], registry_payload: dict[str, Any]
) -> None:
    render_skill_list(_skills(registry_payload), None, json_mode=False)
    out = capsys.readouterr().out
    assert "learning-mode" in out
    assert "article-translator" in out


def test_render_info_json(
    capsys: pytest.CaptureFixture[str], registry_payload: dict[str, Any]
) -> None:
    skill = _skills(registry_payload)[0]
    render_skill_info(skill, None, json_mode=True)
    out = json.loads(capsys.readouterr().out)
    assert out["name"] == "learning-mode"
    assert out["installed"] is None
