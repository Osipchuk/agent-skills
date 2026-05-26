"""Fetch a skill's files from the library archive and place them on disk.

The archive is the GitHub repo tarball derived from the library's repo + pinned
commit (``<repo>/archive/<commit>.tar.gz``). We download it (with a couple of
retries, since codeload occasionally drops a connection), resolve the skill folder
by its manifest ``path`` joined onto the archive's single top-level prefix, verify
the §13.3 checksum, and copy the folder to the install target.

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
from askill.core.http import http_get
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
    return http_get(url, client).content


@contextlib.contextmanager
def extracted_archive(data: bytes) -> Iterator[Path]:
    """Extract a downloaded archive once into a temp dir; yield its root.

    Lets a caller place several skills from a single download instead of
    re-downloading the whole repo per skill.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        extracted = Path(tmpdir)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            # filter="data" blocks path-traversal / absolute members; the tarfile
            # extraction filters are always present on our 3.12+ floor.
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
    folder = _archive_root(extracted) / skill.path
    if not folder.is_dir():
        raise RegistryError(f"skill folder {skill.path!r} not found in archive")
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


def _archive_root(extracted: Path) -> Path:
    """The single ``<repo>-<sha>/`` directory a GitHub tarball unpacks into.

    The skill is resolved by its manifest ``path`` (e.g. ``skills/<name>``) joined
    onto this root, never by searching the tree for a folder named ``<name>``. The
    manifest path is exact; a name search is order-dependent and would happily match
    an unrelated or nested directory that merely shares the skill's name.

    Falls back to ``extracted`` itself when there isn't exactly one directory entry,
    so a flat/prefixless archive still resolves sensibly.
    """
    dirs = [child for child in extracted.iterdir() if child.is_dir()]
    return dirs[0] if len(dirs) == 1 else extracted
