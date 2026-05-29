"""Shared HTTP GET: one client lifecycle, redirect-following, status checking.

``registry.py`` wants the parsed JSON body and ``installer.py`` wants the raw
archive bytes — but both share the same fetch logic (use an injected client, or
spin up a short-lived ``follow_redirects=True`` one), so it lives here once
instead of being copy-pasted into each module.
"""

from __future__ import annotations

import httpx


def http_get(url: str, client: httpx.Client | None) -> httpx.Response:
    """GET ``url``, raise on a non-2xx status, and return the (buffered) response.

    When ``client`` is ``None`` a short-lived client is created with
    ``follow_redirects=True`` — GitHub 302-redirects both ``/archive/<sha>.tar.gz``
    (to codeload) and ``raw.githubusercontent.com`` URLs. Callers read ``.json()``
    or ``.content`` off the returned response.
    """
    if client is not None:
        response = client.get(url)
        response.raise_for_status()
        return response
    with httpx.Client(follow_redirects=True) as owned_client:
        response = owned_client.get(url)
        response.raise_for_status()
        return response
