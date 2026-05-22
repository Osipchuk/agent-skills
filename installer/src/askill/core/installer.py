"""Fetch a skill's files from the library archive and place them on disk.

The archive is the GitHub repo tarball derived from the library's repo + pinned
commit (``<repo>/archive/<commit>.tar.gz``). We download it, locate the skill
folder (``skills/<name>``) regardless of the archive's top-level prefix, verify
the §13.3 checksum, and copy the folder to the install target.
"""

from __future__ import annotations

import io
import tarfile
import tempfile
from pathlib import Path

import httpx

from askill.core.checksum import skill_checksum
from askill.core.filesystem import copy_tree
from askill.core.models import Library, RegistrySkill
from askill.utils.errors import ChecksumError, RegistryError


def archive_url(library: Library) -> str:
    """GitHub repo-archive URL for the library's pinned commit."""
    return f"{library.repo}/archive/{library.commit}.tar.gz"


def fetch_and_place(
    skill: RegistrySkill,
    library: Library,
    target: Path,
    *,
    verify_checksum: bool = True,
    client: httpx.Client | None = None,
) -> None:
    """Download the library archive, verify the skill, and copy it to ``target``."""
    data = _download(archive_url(library), client)
    with tempfile.TemporaryDirectory() as tmpdir:
        extracted = Path(tmpdir)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            tar.extractall(extracted, filter="data")
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


def _download(url: str, client: httpx.Client | None) -> bytes:
    try:
        if client is not None:
            response = client.get(url)
            response.raise_for_status()
            return response.content
        with httpx.Client() as owned_client:
            response = owned_client.get(url)
            response.raise_for_status()
            return response.content
    except httpx.HTTPError as exc:
        raise RegistryError(f"failed to download skill archive from {url}: {exc}") from exc


def _find_skill_folder(extracted: Path, name: str) -> Path | None:
    for path in extracted.rglob(name):
        if path.is_dir() and path.parent.name == "skills":
            return path
    return None
