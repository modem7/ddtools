"""Plugins: a repo's own package can add commands and sheet-text blocks to ddtools.

A plugin is any installed package with an entry point in the ``ddtools.plugins`` group,
pointing at a module with ``register(api)``. ddtools knows nothing else about it.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

ENTRY_GROUP = "ddtools.plugins"

# A sheet-text block: (character, names of the party still in it) -> text for {{name}}.
Block = Callable[[object, list[str]], str]

_blocks: dict[str, Block] = {}
_commands: list[str] = []
_loaded = False


class API:
    """What a plugin's ``register(api)`` may use."""

    def command(self, name: str, help: str, configure):
        """Decorator adding ``ddtools <name>``, like ddtools' own commands."""
        from ddtools import cli

        def wrap(fn):
            if name not in _commands:
                cli.command(name, help, configure)(fn)
                _commands.append(name)
            return fn

        return wrap

    def sheet_text_block(self, name: str, fn: Block) -> None:
        """Fill ``{{name}}`` in a character's dndbeyond.yaml text."""
        _blocks[name] = fn


def _installed() -> list:
    from importlib.metadata import entry_points

    return list(entry_points(group=ENTRY_GROUP))


def load(eps: Iterable | None = None) -> list[str]:
    """Load the plugins once (``eps``: entry points, for tests). Returns warnings."""
    global _loaded
    if _loaded:
        return []
    _loaded = True
    warnings = []
    for ep in _installed() if eps is None else eps:
        try:
            module = ep.load()
            register = getattr(module, "register", None)
            if register is None:
                raise AttributeError("it has no register(api)")
            register(API())
        except Exception as err:  # a broken plugin must never stop ddtools
            warnings.append(f"plugin {ep.name} skipped: {err}")
    return warnings


def blocks() -> dict[str, Block]:
    return dict(_blocks)


def reset() -> None:
    """Forget every plugin (tests only)."""
    global _loaded
    from ddtools import cli

    cli._COMMANDS[:] = [c for c in cli._COMMANDS if c[0] not in _commands]
    _commands.clear()
    _blocks.clear()
    _loaded = False
