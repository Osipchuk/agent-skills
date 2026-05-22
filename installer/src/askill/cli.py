"""askill command-line interface.

Thin Typer layer: parses arguments and delegates to ``askill.core`` and
``askill.utils``. Commands live in ``askill.commands`` and are registered here.
"""

from __future__ import annotations

import typer

from askill import __version__
from askill.commands.info import show_info
from askill.commands.install import install
from askill.commands.list import list_skills
from askill.commands.uninstall import uninstall

app = typer.Typer(
    name="askill",
    help="Install and manage agent skills from the library.",
    no_args_is_help=True,
    add_completion=False,
)

app.command("list")(list_skills)
app.command("info")(show_info)
app.command("install")(install)
app.command("uninstall")(uninstall)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the askill version and exit.",
    ),
) -> None:
    """askill — agent skills installer."""
