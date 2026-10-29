"""Plugins: a repo's own package can add commands and sheet-text blocks to ddtools.

A plugin is any installed package with an entry point in the ``ddtools.plugins`` group,
pointing at a module with ``register(api)``. ddtools knows nothing else about it.

Commands go into ``ddtools.registry.COMMANDS``. A name that is already taken (by ddtools
or by an earlier plugin) is skipped with a warning; the first one wins.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any

from ddtools.registry import COMMANDS, Configure, DuplicateCommandError, Handler, Registry

if TYPE_CHECKING:
    from ddtools.config import Character

ENTRY_GROUP = "ddtools.plugins"

# A sheet-text block: (character, names of the party still in it) -> text for {{name}}.
Block = Callable[["Character", list[str]], str]


class Host:
    """Everything the loaded plugins added: their commands, blocks and warnings."""

    def __init__(self, registry: Registry = COMMANDS) -> None:
        self.registry = registry
        self.blocks: dict[str, Block] = {}
        self.commands: list[str] = []
        self.warnings: list[str] = []
        self.loaded = False

    def load(self, eps: Iterable[Any] | None = None) -> list[str]:
        """Load the plugins once (``eps``: entry points, for tests).

        Returns the warnings on the first call and ``[]`` after, so a caller that prints
        them (``build_parser``) prints each once; ``self.warnings`` keeps them all.
        """
        if self.loaded:
            return []
        self.loaded = True
        self.warnings = []
        for ep in _installed() if eps is None else eps:
            try:
                module = ep.load()
                register = getattr(module, "register", None)
                if register is None:
                    raise AttributeError("it has no register(api)")
                register(API(ep.name, self))
            except Exception as err:  # a broken plugin must never stop ddtools
                self.warnings.append(f"plugin {ep.name} skipped: {err}")
        return list(self.warnings)

    def reset(self) -> None:
        """Forget every plugin: remove only the commands they added."""
        for name in self.commands:
            self.registry.unregister(name)
        self.commands.clear()
        self.blocks.clear()
        self.warnings = []
        self.loaded = False


_host = Host()


class API:
    """What a plugin's ``register(api)`` may use."""

    def __init__(self, plugin: str = "", host: Host | None = None) -> None:
        self._plugin = plugin
        self._host = _host if host is None else host

    def command(self, name: str, help: str, configure: Configure) -> Callable[[Handler], Handler]:
        """Decorator adding ``ddtools <name>``, like ddtools' own commands.

        If ``name`` is taken, the command is skipped with a warning and the function is
        returned unchanged.
        """
        host = self._host

        def wrap(fn: Handler) -> Handler:
            try:
                host.registry.register(name, help, configure, fn)
            except DuplicateCommandError:
                who = f"plugin {self._plugin}" if self._plugin else "plugin"
                host.warnings.append(f"{who}: command {name!r} already exists, skipped")
            else:
                host.commands.append(name)
            return fn

        return wrap

    def sheet_text_block(self, name: str, fn: Block) -> None:
        """Fill ``{{name}}`` in a character's dndbeyond.yaml text."""
        self._host.blocks[name] = fn


def _installed() -> list[Any]:
    from importlib.metadata import entry_points

    return list(entry_points(group=ENTRY_GROUP))


def load(eps: Iterable[Any] | None = None) -> list[str]:
    """Load the plugins once (``eps``: entry points, for tests).

    Returns the warnings on the first call and ``[]`` after.
    """
    return _host.load(eps)


def blocks() -> dict[str, Block]:
    return dict(_host.blocks)


def reset() -> None:
    """Forget every plugin (tests only)."""
    _host.reset()
