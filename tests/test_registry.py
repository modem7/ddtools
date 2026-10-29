"""The command registry: shared by cli and plugins, with no import cycle."""

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ddtools import cli, registry
from ddtools.registry import Command, DuplicateCommandError, Registry

SRC = Path(registry.__file__).parent


def _configure(p):
    p.add_argument("who")


def _handler(args):
    return 0


def test_register_and_lookup():
    reg = Registry()
    cmd = reg.register("wave", "Wave.", _configure, _handler)
    assert cmd == Command("wave", "Wave.", _configure, _handler)
    assert reg.lookup("wave") is cmd
    assert reg.lookup("nowhere") is None
    assert "wave" in reg and len(reg) == 1


def test_iteration_keeps_registration_order():
    reg = Registry()
    for name in ("c", "a", "b"):
        reg.register(name, name, _configure, _handler)
    assert [c.name for c in reg] == ["c", "a", "b"]
    assert reg.names() == ["c", "a", "b"]


def test_a_duplicate_name_raises_and_keeps_the_first():
    reg = Registry()
    reg.register("wave", "First.", _configure, _handler)
    with pytest.raises(DuplicateCommandError, match="wave"):
        reg.register("wave", "Second.", _configure, _handler)
    assert reg.lookup("wave").help == "First."


def test_unregister_removes_and_returns_the_command():
    reg = Registry()
    reg.register("wave", "Wave.", _configure, _handler)
    assert reg.unregister("wave").name == "wave"
    assert reg.lookup("wave") is None
    assert reg.unregister("wave") is None, "unknown names are ignored"


def test_reset_forgets_everything():
    reg = Registry()
    reg.register("a", "A.", _configure, _handler)
    reg.register("b", "B.", _configure, _handler)
    reg.reset()
    assert len(reg) == 0


def test_the_decorator_registers_and_returns_the_function():
    reg = Registry()

    @reg.command("wave", "Wave.", _configure)
    def wave(args):
        return 0

    assert reg.lookup("wave").fn is wave


def test_a_configure_may_return_a_value():
    reg = Registry()
    reg.command("x", "X.", lambda p: p.add_argument("--json", action="store_true"))(_handler)
    assert reg.lookup("x") is not None


def test_cli_uses_the_shared_registry():
    assert cli.command is registry.command
    assert registry.COMMANDS.lookup("build").fn is cli.cmd_build
    assert "build" in cli.build_parser().format_help()


def _imports(path: Path) -> set[str]:
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            found.update(f"{node.module}.{a.name}" for a in node.names)
    return found


def test_plugins_and_registry_never_import_cli():
    assert "ddtools.cli" not in _imports(SRC / "plugins.py")
    assert "ddtools.cli" not in _imports(SRC / "registry.py")
    assert "ddtools.plugins" not in _imports(SRC / "registry.py")


def test_importing_plugins_does_not_load_cli():
    code = "import sys, ddtools.plugins; print('ddtools.cli' in sys.modules)"
    env = {**os.environ, "PYTHONPATH": str(SRC.parent)}
    run = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, check=True
    )
    assert run.stdout.strip() == "False"
