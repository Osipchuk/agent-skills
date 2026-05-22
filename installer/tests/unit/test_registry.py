"""Tests for askill.core.registry.load_registry — local path and http(s) URL."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from pytest_httpx import HTTPXMock

from askill.core.models import Registry
from askill.core.registry import load_registry
from askill.utils.errors import RegistryError

URL = "https://example.com/registry.json"


def test_load_local_valid(tmp_path: Path, registry_payload: dict[str, Any]) -> None:
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(registry_payload))
    reg = load_registry(str(path))
    assert isinstance(reg, Registry)
    assert {s.name for s in reg.skills} == {"learning-mode", "article-translator"}


def test_load_local_missing(tmp_path: Path) -> None:
    with pytest.raises(RegistryError):
        load_registry(str(tmp_path / "nope.json"))


def test_load_local_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{ not valid json")
    with pytest.raises(RegistryError):
        load_registry(str(path))


def test_load_local_schema_invalid(tmp_path: Path, registry_payload: dict[str, Any]) -> None:
    # introduce a duplicate skill name → model validation fails → RegistryError
    registry_payload["skills"][1]["name"] = registry_payload["skills"][0]["name"]
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(registry_payload))
    with pytest.raises(RegistryError):
        load_registry(str(path))


def test_load_url_valid(httpx_mock: HTTPXMock, registry_payload: dict[str, Any]) -> None:
    httpx_mock.add_response(url=URL, json=registry_payload)
    reg = load_registry(URL)
    assert len(reg.skills) == 2


def test_load_url_404(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=URL, status_code=404)
    with pytest.raises(RegistryError):
        load_registry(URL)


def test_load_url_connect_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(httpx.ConnectError("boom"), url=URL)
    with pytest.raises(RegistryError):
        load_registry(URL)
