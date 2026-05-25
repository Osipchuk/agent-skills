"""Unit tests for the Claude Code plugin marketplace manifest builder.

The library is distributed to Claude Code as ONE bundled plugin (named `skills`)
inside a marketplace (named `askill`). `version` is intentionally omitted from
plugin.json so Claude Code falls back to the git commit SHA for updates.
"""

from __future__ import annotations

from askill.core.manifest import build_marketplace_manifests


def test_marketplace_lists_single_bundled_plugin() -> None:
    marketplace, _plugin = build_marketplace_manifests(
        ["learning-mode", "article-translator", "toxic-senior-reviewer"],
        marketplace_name="askill",
        plugin_name="skills",
        owner_name="Evgenii Osipchuk",
    )
    assert marketplace["name"] == "askill"
    assert marketplace["owner"] == {"name": "Evgenii Osipchuk"}
    plugins = marketplace["plugins"]
    assert isinstance(plugins, list) and len(plugins) == 1
    entry = plugins[0]
    assert entry["name"] == "skills"
    # Relative-path source must start with ./ and point at the generated plugin dir.
    assert entry["source"] == "./plugins/skills"


def test_plugin_manifest_omits_version_for_git_sha_updates() -> None:
    _marketplace, plugin = build_marketplace_manifests(
        ["learning-mode"],
        marketplace_name="askill",
        plugin_name="skills",
        owner_name="Evgenii Osipchuk",
    )
    assert plugin["name"] == "skills"
    assert plugin["author"] == {"name": "Evgenii Osipchuk"}
    # No pinned version -> Claude Code uses the commit SHA, so every push updates.
    assert "version" not in plugin


def test_plugin_description_names_the_bundled_skills() -> None:
    _marketplace, plugin = build_marketplace_manifests(
        ["learning-mode", "toxic-senior-reviewer"],
        marketplace_name="askill",
        plugin_name="skills",
        owner_name="Evgenii Osipchuk",
    )
    assert "learning-mode" in plugin["description"]
    assert "toxic-senior-reviewer" in plugin["description"]
