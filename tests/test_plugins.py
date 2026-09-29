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
