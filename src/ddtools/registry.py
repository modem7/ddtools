"""The command registry: every ``ddtools <name>`` subcommand, built-in or from a plugin.

``cli`` and ``plugins`` both use this module, so neither needs the other's internals.
It imports nothing from ddtools.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterator
from dataclasses import dataclass

# Adds a command's arguments. Any return value is ignored (so a lambda calling
# ``p.add_argument`` is fine).
Configure = Callable[[argparse.ArgumentParser], object]
# Runs a command and returns its exit code.
Handler = Callable[[argparse.Namespace], int]


class DuplicateCommandError(ValueError):
    """A command name is already registered."""


@dataclass(frozen=True)
class Command:
    name: str
    help: str
    configure: Configure
    fn: Handler


class Registry:
    """Commands by name, kept in the order they were registered."""

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def register(self, name: str, help: str, configure: Configure, fn: Handler) -> Command:
        """Add a command. Raises ``DuplicateCommandError`` if ``name`` is taken."""
        if name in self._commands:
            raise DuplicateCommandError(f"command {name!r} already exists")
        cmd = Command(name, help, configure, fn)
        self._commands[name] = cmd
        return cmd

    def command(self, name: str, help: str, configure: Configure) -> Callable[[Handler], Handler]:
        """Decorator form of ``register``: returns the function unchanged."""

        def wrap(fn: Handler) -> Handler:
            self.register(name, help, configure, fn)
            return fn

        return wrap

    def unregister(self, name: str) -> Command | None:
        """Remove a command and return it, or ``None`` if it was not registered."""
        return self._commands.pop(name, None)

    def lookup(self, name: str) -> Command | None:
        return self._commands.get(name)

    def reset(self) -> None:
        """Forget every command."""
        self._commands.clear()

    def names(self) -> list[str]:
        return list(self._commands)

    def __iter__(self) -> Iterator[Command]:
        return iter(list(self._commands.values()))

    def __contains__(self, name: object) -> bool:
        return name in self._commands

    def __len__(self) -> int:
        return len(self._commands)


# The one registry ddtools' parser is built from.
COMMANDS = Registry()
command = COMMANDS.command
unregister = COMMANDS.unregister
