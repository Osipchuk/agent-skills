"""askill command-line interface.

Thin Typer layer: parses arguments and delegates to ``askill.core`` and
``askill.utils``. Commands live in ``askill.commands`` and are registered here.
"""

from __future__ import annotations

import sys

import typer

from askill import __version__
from askill.commands import DEFAULT_REGISTRY
from askill.commands.info import show_info
from askill.commands.install import install
from askill.commands.list import list_skills
from askill.commands.uninstall import uninstall
from askill.commands.wizard import _wizard, run_wizard

app = typer.Typer(
    name="askill",
    help="Install and manage agent skills from the library.",
    add_completion=False,
)

app.command("list")(list_skills)
app.command("info")(show_info)
app.command("install")(install)
app.command("uninstall")(uninstall)
app.command("wizard")(run_wizard)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the askill version and exit.",
    ),
) -> None:
    """askill — agent skills installer."""
    if ctx.invoked_subcommand is not None:
        return
    # No subcommand: launch the interactive wizard on a real TTY; otherwise (pipes,
    # CI, --help) fall back to showing help, matching the old no_args_is_help.
    if sys.stdin.isatty() and sys.stdout.isatty():
        _wizard(DEFAULT_REGISTRY, None, False)
    else:
        typer.echo(ctx.get_help())
