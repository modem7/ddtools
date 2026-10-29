"""The plugin hook: a repo's own package can add commands and sheet-text blocks."""

import types

import pytest

from ddtools import plugins
from ddtools.cli import main


class FakeEntryPoint:
    def __init__(self, name, module):
        self.name, self.module = name, module

    def load(self):
        if isinstance(self.module, Exception):
            raise self.module
        return self.module


def _fixture_plugin():
    def register(api):
        def configure(p):
            p.add_argument("who")

        @api.command("wave", "Wave at someone.", configure)
        def wave(args):
            print(f"Hello, {args.who}")
            return 0

        api.sheet_text_block("weather", lambda ch, names: "Sunny, for " + ", ".join(names))

    return types.SimpleNamespace(register=register)


@pytest.fixture
def clean_plugins():
    plugins.reset()
    yield
    plugins.reset()


def test_a_plugin_adds_a_command_and_a_block(clean_plugins, capsys):
    warnings = plugins.load([FakeEntryPoint("fixture", _fixture_plugin())])
    assert warnings == []
    assert main(["wave", "Ash"]) == 0
    assert "Hello, Ash" in capsys.readouterr().out
    assert plugins.blocks()["weather"](None, ["Ash", "Bramble"]) == "Sunny, for Ash, Bramble"


def test_without_the_plugin_neither_exists(clean_plugins, capsys):
    plugins.load([])
    assert "weather" not in plugins.blocks()
    with pytest.raises(SystemExit):
        main(["wave", "Ash"])


def test_a_broken_plugin_is_skipped_with_one_warning(clean_plugins):
    broken = FakeEntryPoint("broken", ImportError("no module named nowhere"))
    no_register = FakeEntryPoint("empty", types.SimpleNamespace())
    warnings = plugins.load([broken, FakeEntryPoint("fixture", _fixture_plugin()), no_register])
    assert len(warnings) == 2
    assert "broken" in warnings[0] and "no module named nowhere" in warnings[0]
    assert "empty" in warnings[1] and "register" in warnings[1]
    assert "weather" in plugins.blocks(), "the good plugin still loads"


def test_loading_twice_registers_once(clean_plugins, capsys):
    plugins.load([FakeEntryPoint("fixture", _fixture_plugin())])
    plugins.load([FakeEntryPoint("fixture", _fixture_plugin())])
    assert main(["wave", "Ash"]) == 0


def test_sheet_text_fills_plugin_blocks_and_flags_unknown_ones(clean_plugins, ash):
    import yaml

    from ddtools import sheettext as T
    from ddtools.config import load_character

    plugins.load([FakeEntryPoint("fixture", _fixture_plugin())])
    src = {"notes": {"otherNotes": "{{weather}}\n\n{{nowhere}}"}, "allies": {}}
    (ash / T.SOURCE_FILE).write_text(yaml.safe_dump(src), encoding="utf-8")
    rep = T.report(load_character(ash))
    other = next(f for f in rep["fields"] if f["key"] == "otherNotes")
    assert other["proposed"].startswith("Sunny, for Bramble, Cinder")
    assert any("{{nowhere}}" in p for p in rep["problems"])


def _named_plugin(command, help_text, block=None):
    def register(api):
        @api.command(command, help_text, lambda p: None)
        def run(args):
            print(help_text)
            return 0

        if block:
            api.sheet_text_block(block, lambda ch, names: block)

    return types.SimpleNamespace(register=register)


def test_a_plugin_cannot_replace_a_built_in_command(clean_plugins):
    from ddtools import cli
    from ddtools.registry import COMMANDS

    clash = _named_plugin("build", "Not the real build.", block="extra")
    warnings = plugins.load([FakeEntryPoint("clash", clash)])
    assert len(warnings) == 1
    assert "clash" in warnings[0] and "'build'" in warnings[0]
    assert COMMANDS.lookup("build").fn is cli.cmd_build
    assert "extra" in plugins.blocks(), "the rest of the plugin still loads"
    cli.build_parser()


def test_two_plugins_with_one_command_name_first_wins(clean_plugins, capsys):
    first = FakeEntryPoint("first", _named_plugin("wave", "From first."))
    second = FakeEntryPoint("second", _named_plugin("wave", "From second."))
    warnings = plugins.load([first, second])
    assert len(warnings) == 1 and "second" in warnings[0] and "'wave'" in warnings[0]
    assert main(["wave"]) == 0
    assert "From first." in capsys.readouterr().out


def test_reset_removes_only_plugin_commands(clean_plugins):
    from ddtools.registry import COMMANDS

    before = COMMANDS.names()
    plugins.load([FakeEntryPoint("fixture", _fixture_plugin())])
    assert "wave" in COMMANDS
    plugins.reset()
    assert COMMANDS.names() == before
    assert plugins.blocks() == {}
    assert plugins.load([FakeEntryPoint("fixture", _fixture_plugin())]) == []
    assert "wave" in COMMANDS, "load works again after reset"


def test_a_bare_api_still_works(clean_plugins):
    from ddtools.registry import COMMANDS

    api = plugins.API()
    api.command("wave", "Wave.", lambda p: None)(lambda args: 0)
    api.sheet_text_block("weather", lambda ch, names: "Sunny")
    assert "wave" in COMMANDS and "weather" in plugins.blocks()
