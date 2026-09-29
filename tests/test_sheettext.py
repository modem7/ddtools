"""ddtools sheet-text, on a made-up campaign (Ash Vale, with Bramble and Cinder)."""

import json

import pytest
import yaml

from ddtools import sheettext as T
from ddtools.cli import main
from ddtools.config import load_character


def _source(**over):
    src = {
        "details": {"faith": "The Salt Mother", "age": None, "hair": "Short, sun-bleached"},
        "traits": {"flaws": "I carry everyone's bags and complain about it."},
        "notes": {"otherNotes": 'CATCHPHRASES\n- "Heavier than it looks."'},
        "allies": {
            "Cinder": "Cinder - tiefling warlock. Warm hands, warmer temper.",
            "Bramble": "Bramble - elf rogue. Owes me a pack mule.",
        },
    }
    return {**src, **over}


def test_allies_follow_the_party_order_and_skip_anyone_not_in_it():
    text, missing = T.allies_text(_source(), ["Bramble", "Cinder", "Dune"])
    assert text.splitlines() == [
        "Bramble - elf rogue. Owes me a pack mule.",
        "Cinder - tiefling warlock. Warm hands, warmer temper.",
    ]
    assert missing == ["Dune"]
    text, _ = T.allies_text(_source(), ["Cinder"])
    assert "Bramble" not in text, "someone who left the party drops off the sheet"


def test_party_names_skip_teammates_who_are_gone(ash):
    ch = load_character(ash)
    assert T.party_names(ch) == ["Bramble", "Cinder"]
    ch.campaign["party"][0]["status"] = "gone"
    assert T.party_names(ch) == ["Cinder"]


def test_status_compares_loosely_and_leaves_what_the_source_leaves():
    assert T.status("It’s a “deal”.\nTwo lines", 'It\'s a "deal".\r\nTwo  lines') == "up to date"
    assert T.status("38", 38) == "up to date"
    assert T.status("New text", "") == "missing"
    assert T.status("New text", None) == "missing"
    assert T.status("New text", "Old text") == "needs updating"
    assert T.status(None, "38") == "leave as is"


def test_blanks_are_found():
    assert T.blanks("Published by [publishing house], edited by [Name].") == [
        "[publishing house]",
        "[Name]",
    ]
    assert T.blanks("No blanks here.") == []


def _write(char, src, snapshot_notes=None):
    (char / T.SOURCE_FILE).write_text(yaml.safe_dump(src, allow_unicode=True), encoding="utf-8")
    snaps = sorted((char / "snapshots").glob("20*.json"))
    data = json.loads(snaps[-1].read_text(encoding="utf-8"))
    body = data.get("data", data)
    if snapshot_notes is not None:
        body.setdefault("notes", {}).update(snapshot_notes)
    snaps[-1].write_text(json.dumps(data), encoding="utf-8")


def test_report_fills_in_the_generated_parts(ash):
    _write(ash, _source())
    rep = T.report(load_character(ash))
    fields = {f["key"]: f for f in rep["fields"]}
    assert fields["allies"]["proposed"].startswith("Bramble - elf rogue")
    assert fields["age"]["status"] == "leave as is"
    assert fields["ideals"]["status"] == "not in the source", "no text given: nothing proposed"
    assert rep["missing_allies"] == []


def test_a_block_nothing_fills_is_a_problem(ash):
    _write(ash, _source(notes={"otherNotes": "{{nowhere}}"}))
    rep = T.report(load_character(ash))
    assert any("{{nowhere}}" in p for p in rep["problems"])


def test_secrets_in_the_proposed_text_are_problems(ash):
    _write(ash, _source(traits={"flaws": "Ex-smuggler, and proud of it."}))
    rep = T.report(load_character(ash))
    assert any("flaws" in p and "smuggler" in p for p in rep["problems"])


def test_secrets_on_the_live_sheet_are_reported(ash):
    _write(ash, _source(), {"enemies": "The customs men who caught me smuggler-handed."})
    rep = T.report(load_character(ash))
    live = {f["key"]: f["live_secrets"] for f in rep["fields"]}
    assert "smuggler" in live["enemies"]


def test_details_over_fifty_characters_are_problems(ash):
    _write(ash, _source(details={"hair": "Short, sun-bleached, with one braid he never explains"}))
    rep = T.report(load_character(ash))
    assert any("hair" in p and "50" in p for p in rep["problems"])


def test_cli_writes_the_paste_ready_file(ash, capsys):
    _write(ash, _source())
    assert main(["sheet-text", str(ash)]) == 0
    out = (ash / "notes" / "dndbeyond-text.md").read_text(encoding="utf-8")
    assert "## Allies" in out and "Cinder - tiefling warlock" in out
    printed = capsys.readouterr().out
    assert "notes/dndbeyond-text.md" in printed and "Allies" in printed


def test_cli_fails_on_a_leak_and_writes_nothing(ash, capsys):
    _write(ash, _source(traits={"flaws": "Once a smuggler."}))
    out = ash / "notes" / "dndbeyond-text.md"
    assert main(["sheet-text", str(ash)]) == 1
    assert not out.exists()
    assert "smuggler" in capsys.readouterr().out


@pytest.mark.parametrize("key", ["hair", "eyes", "skin"])
def test_every_short_detail_is_checked(ash, key):
    _write(ash, _source(details={key: "x" * 51}))
    assert any(key in p for p in T.report(load_character(ash))["problems"])
