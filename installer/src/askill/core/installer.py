"""Fetch a skill's files from the library archive and place them on disk.

The archive is the GitHub repo tarball derived from the library's repo + pinned
commit (``<repo>/archive/<commit>.tar.gz``). We download it (with a couple of
retries, since codeload occasionally drops a connection), locate the skill folder
(``skills/<name>``) regardless of the archive's top-level prefix, verify the
§13.3 checksum, and copy the folder to the install target.

The archive is the *whole* repo at one commit, so a multi-skill install should
download it once and place many — see ``download_archive`` + ``extracted_archive``
+ ``place_skill`` (used by the wizard). ``fetch_and_place`` is the one-shot
convenience used by ``askill install``.
"""

from __future__ import annotations

import contextlib
import io
import tarfile
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path

import httpx

from askill.core.checksum import skill_checksum
from askill.core.filesystem import copy_tree
from askill.core.models import Library, RegistrySkill
from askill.utils.errors import ChecksumError, RegistryError

_DOWNLOAD_RETRIES = 2
_RETRY_BACKOFF_S = 0.5


def archive_url(library: Library) -> str:
    """GitHub repo-archive URL for the library's pinned commit."""
    return f"{library.repo}/archive/{library.commit}.tar.gz"


def download_archive(
    library: Library,
    *,
    client: httpx.Client | None = None,
    retries: int = _DOWNLOAD_RETRIES,
) -> bytes:
    """Download the library archive, retrying transient transport failures.

    GitHub's codeload endpoint occasionally disconnects without a response; a
    couple of retries with a short backoff turns those blips into success instead
    of a hard failure.
    """
    url = archive_url(library)
    for attempt in range(retries + 1):
        try:
            return _get(url, client)
        except httpx.TransportError as exc:
            # Transient (connection drop, timeout, "server disconnected"): retry.
            if attempt < retries:
                time.sleep(_RETRY_BACKOFF_S * (attempt + 1))
                continue
            raise RegistryError(f"failed to download skill archive from {url}: {exc}") from exc
        except httpx.HTTPError as exc:
            # Permanent (e.g. 404 / status error): no point retrying.
            raise RegistryError(f"failed to download skill archive from {url}: {exc}") from exc
    raise AssertionError("unreachable")  # pragma: no cover


def _get(url: str, client: httpx.Client | None) -> bytes:
    if client is not None:
        response = client.get(url)
        response.raise_for_status()
        return response.content
    # follow_redirects: GitHub 302-redirects /archive/<sha>.tar.gz to codeload.github.com.
    with httpx.Client(follow_redirects=True) as owned_client:
        response = owned_client.get(url)
        response.raise_for_status()
        return response.content


@contextlib.contextmanager
def extracted_archive(data: bytes) -> Iterator[Path]:
    """Extract a downloaded archive once into a temp dir; yield its root.

    Lets a caller place several skills from a single download instead of
    re-downloading the whole repo per skill.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        extracted = Path(tmpdir)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            tar.extractall(extracted, filter="data")
        yield extracted


def place_skill(
    extracted: Path,
    skill: RegistrySkill,
    target: Path,
    *,
    verify_checksum: bool = True,
) -> None:
    """Locate ``skill`` in an extracted archive, verify it, and copy it to ``target``."""
    folder = _find_skill_folder(extracted, skill.name)
    if folder is None:
        raise RegistryError(f"skill folder 'skills/{skill.name}' not found in archive")
    if verify_checksum:
        actual = skill_checksum(folder)
        if actual != skill.checksum:
            raise ChecksumError(
                f"checksum mismatch for {skill.name}: expected {skill.checksum}, got {actual}"
            )
    copy_tree(folder, target)


def fetch_and_place(
    skill: RegistrySkill,
    library: Library,
    target: Path,
    *,
    verify_checksum: bool = True,
    client: httpx.Client | None = None,
) -> None:
    """Download the library archive, verify the skill, and copy it to ``target``."""
    data = download_archive(library, client=client)
    with extracted_archive(data) as extracted:
        place_skill(extracted, skill, target, verify_checksum=verify_checksum)


def _find_skill_folder(extracted: Path, name: str) -> Path | None:
    for path in extracted.rglob(name):
        if path.is_dir() and path.parent.name == "skills":
            return path
    return None
