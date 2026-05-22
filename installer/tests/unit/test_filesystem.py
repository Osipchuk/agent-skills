"""Tests for askill.core.filesystem — atomic writes and tree copy/remove."""

from __future__ import annotations

from pathlib import Path

from askill.core.filesystem import atomic_write_text, copy_tree, remove_tree


def test_atomic_write_creates_parents(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "state.json"
    atomic_write_text(target, "hello")
    assert target.read_text() == "hello"
    assert not (target.parent / (target.name + ".tmp")).exists()


def test_atomic_write_overwrites(tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    atomic_write_text(target, "one")
    atomic_write_text(target, "two")
    assert target.read_text() == "two"


def test_copy_tree_and_replace(tmp_path: Path) -> None:
    src = tmp_path / "src"
    (src / "sub").mkdir(parents=True)
    (src / "SKILL.md").write_text("x")
    (src / "sub" / "f.py").write_text("y")
    dest = tmp_path / "dest"
    copy_tree(src, dest)
    assert (dest / "SKILL.md").read_text() == "x"
    assert (dest / "sub" / "f.py").read_text() == "y"

    (src / "SKILL.md").write_text("z")
    copy_tree(src, dest)  # replaces existing dest
    assert (dest / "SKILL.md").read_text() == "z"


def test_remove_tree(tmp_path: Path) -> None:
    directory = tmp_path / "d"
    directory.mkdir()
    (directory / "f").write_text("x")
    remove_tree(directory)
    assert not directory.exists()
    remove_tree(directory)  # no error when already absent
