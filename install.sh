#!/bin/sh
# askill bootstrap installer.
#
#   Install the CLI:        curl -fsSL .../install.sh | sh
#   Install a skill:        curl -fsSL .../install.sh | sh -s -- learning-mode
#   Install into a project: curl -fsSL .../install.sh | ASKILL_SCOPE=project sh -s -- learning-mode
#
# No arguments  -> installs the `askill` CLI persistently (uv tool install).
# Skill name(s) -> installs each skill one-shot (uvx), into ASKILL_SCOPE (default user).
set -eu

# Single source of truth for the package. askill is installed straight from git
# (it is not published as a package), so this URL is the canonical source.
PKG="git+https://github.com/Osipchuk/agent-skills#subdirectory=installer"

say() { printf '%s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

# Ensure uv is available, bootstrapping it if missing.
ensure_uv() {
    if command -v uv >/dev/null 2>&1; then
        return
    fi
    say "uv not found - installing it from https://astral.sh/uv ..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Make the freshly installed uv visible to this script session.
    if [ -f "$HOME/.local/bin/env" ]; then
        # shellcheck disable=SC1091
        . "$HOME/.local/bin/env"
    fi
    PATH="$HOME/.local/bin:$PATH"
    export PATH
    command -v uv >/dev/null 2>&1 || die "uv installation failed; install it manually: https://docs.astral.sh/uv/"
}

ensure_uv

if [ "$#" -eq 0 ]; then
    say "Installing the askill CLI ..."
    uv tool install --force "$PKG"
    say ""
    say "Done. Try:"
    say "  askill list                 # browse available skills"
    say "  askill install learning-mode  # install one"
    exit 0
fi

SCOPE="${ASKILL_SCOPE:-user}"
say "Installing skill(s) into scope '$SCOPE': $*"
for name in "$@"; do
    say ""
    say "==> $name"
    uvx --from "$PKG" askill install "$name" --scope "$SCOPE"
done
say ""
say "Done."
