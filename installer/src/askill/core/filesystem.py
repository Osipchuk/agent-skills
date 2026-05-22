"""Filesystem helpers: atomic text writes and directory-tree copy/remove.

Atomic write = write to a sibling ``.tmp`` then ``os.replace`` (atomic on the
same filesystem), so a crash never leaves a half-written installed.json
(spec §10.2).
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def atomic_write_text(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` atomically, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def copy_tree(src: Path, dest: Path) -> None:
    """Copy directory tree ``src`` → ``dest``, replacing ``dest`` if present."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)


def remove_tree(path: Path) -> None:
    """Remove a directory tree if it exists (no error when absent)."""
    if path.exists():
        shutil.rmtree(path)
