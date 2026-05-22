"""Deterministic skill-folder checksums (spec §13.3).

A skill's checksum is the SHA-256 of a tar archive of its folder, built
deterministically so the same content always yields the same digest: file
entries sorted by name, fixed mtime (epoch), zeroed owner/group, and a fixed
mode — the spirit of ``tar --sort=name --mtime='1970-01-01' --owner=0
--group=0``. The registry generator and the installer both call this function,
so they agree by construction (we do not need to byte-match GNU tar).
"""

from __future__ import annotations

import hashlib
import io
import tarfile
from pathlib import Path


def skill_checksum(folder: Path) -> str:
    """Return ``sha256:<hex>`` for a skill folder, computed deterministically."""
    digest = hashlib.sha256(_deterministic_tar_bytes(folder)).hexdigest()
    return f"sha256:{digest}"


def _deterministic_tar_bytes(folder: Path) -> bytes:
    files = sorted(p for p in folder.rglob("*") if p.is_file())
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for path in files:
            data = path.read_bytes()
            info = tarfile.TarInfo(name=path.relative_to(folder).as_posix())
            info.size = len(data)
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()
