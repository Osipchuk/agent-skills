"""Load and validate the registry manifest (spec §6).

``load_registry`` is the single I/O entry point for the manifest: it accepts a
local filesystem path or an http(s) URL, and returns a validated ``Registry``.
Every failure mode (missing file, bad JSON, network error, schema violation) is
surfaced as a ``RegistryError`` with a human-readable message.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
from pydantic import ValidationError

from askill.core.models import Registry
from askill.utils.errors import RegistryError


def load_registry(source: str, *, client: httpx.Client | None = None) -> Registry:
    """Load and validate registry.json from a local path or an http(s) URL.

    ``client`` lets callers (and tests) inject a configured ``httpx.Client``;
    when omitted a short-lived one is created for URL sources.
    """
    try:
        if source.startswith(("http://", "https://")):
            data: object = _fetch_url(source, client)
        else:
            data = json.loads(Path(source).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistryError(f"registry file not found: {source}") from exc
    except json.JSONDecodeError as exc:
        raise RegistryError(f"registry is not valid JSON: {exc}") from exc
    except httpx.HTTPError as exc:
        raise RegistryError(f"failed to fetch registry from {source}: {exc}") from exc

    try:
        return Registry.model_validate(data)
    except ValidationError as exc:
        raise RegistryError(f"registry failed validation:\n{exc}") from exc


def _fetch_url(url: str, client: httpx.Client | None) -> object:
    if client is not None:
        response = client.get(url)
        response.raise_for_status()
        return response.json()
    with httpx.Client() as owned_client:
        response = owned_client.get(url)
        response.raise_for_status()
        return response.json()
