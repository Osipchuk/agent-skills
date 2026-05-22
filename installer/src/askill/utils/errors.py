"""Error types and process exit codes (spec §8.2).

Every askill failure is an ``AskillError`` carrying a human-readable message
and the exit code the CLI should return. The cli layer catches these and maps
``exit_code`` to ``typer.Exit``; core/command code just raises the right type.
"""

from __future__ import annotations

EXIT_OK = 0
EXIT_USER = 1
EXIT_SYSTEM = 2
EXIT_CONFLICT = 3


class AskillError(Exception):
    """Base class for all askill errors."""

    exit_code: int = EXIT_SYSTEM

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UserError(AskillError):
    """Bad input from the user (unknown skill, invalid flag value, ...)."""

    exit_code = EXIT_USER


class RegistryError(AskillError):
    """The registry could not be fetched, parsed, or validated."""

    exit_code = EXIT_SYSTEM


class StateError(AskillError):
    """The installed.json state file is present but unreadable/invalid."""

    exit_code = EXIT_SYSTEM


class ChecksumError(AskillError):
    """A downloaded skill's checksum did not match the registry value."""

    exit_code = EXIT_SYSTEM


class ConflictError(AskillError):
    """An install/uninstall conflict (reserved for later sub-projects)."""

    exit_code = EXIT_CONFLICT
