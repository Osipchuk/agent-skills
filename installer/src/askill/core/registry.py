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

from askill.core.http import http_get
from askill.core.models import Registry
from askill.utils.errors import RegistryError, UserError


def load_registry(source: str, *, client: httpx.Client | None = None) -> Registry:
    """Load and validate registry.json from a local path or an https URL.

    Plain ``http://`` is rejected: a MITM on the registry fetch could swap both
    the archive host and the checksums that vouch for it. Use a local file path
    for offline/testing work.

    ``client`` lets callers (and tests) inject a configured ``httpx.Client``;
    when omitted a short-lived one is created for URL sources.
    """
    if source.startswith("http://"):
        raise UserError(
            f"plain-HTTP registry URLs are not allowed (the whole trust chain rides "
            f"on this fetch): use https:// or a local file path, got {source}"
        )
    try:
        if source.startswith("https://"):
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
    return http_get(url, client).json()
