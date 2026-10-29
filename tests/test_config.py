from datetime import date
from pathlib import Path

import pytest

from ddtools.config import (
    ConfigError,
    level_updated_label,
    load_character,
    output_path,
    save_character,
)

VALID = """\
name: Test Hero
status: active
level: 3
updated: 2026-09-28
dndbeyond_id: 123
class_summary: Fighter 3
campaign:
  name: Test Campaign
  rules:
    - {text: "Long rest is 7 days", status: confirmed}
  party:
    - {name: Pal, dndbeyond_id: 456, summary: Rogue}
documents:
  - {file: pdf/Guide.pdf, script: src/build_guide.py, audience: private}
  - {file: pdf/Handout.pdf, script: src/build_handout.py, audience: party,
     future_sections: [Coming Soon]}
"""


def _write(tmp_path, text=VALID):
    d = tmp_path / "Test_Hero"
    d.mkdir()
    (d / "character.yaml").write_text(text, encoding="utf-8")
    return d


def test_load_valid(tmp_path):
    ch = load_character(_write(tmp_path))
    assert ch.name == "Test Hero" and ch.level == 3 and ch.updated == date(2026, 9, 28)
    assert ch.documents[1].audience == "party"
    assert ch.documents[1].future_sections == ["Coming Soon"]
    assert ch.secrets_file == "secrets.txt"


def test_level_updated_label_format(tmp_path):
    assert level_updated_label(load_character(_write(tmp_path))) == "Level 3 · updated 28 Sep 2026"


def test_missing_level(tmp_path):
    d = _write(tmp_path, VALID.replace("level: 3\n", ""))
    with pytest.raises(ConfigError) as exc:
        load_character(d)
    assert "character.yaml" in str(exc.value) and "level" in str(exc.value)


def test_bad_audience(tmp_path):
    d = _write(tmp_path, VALID.replace("audience: party", "audience: public"))
    with pytest.raises(ConfigError) as exc:
        load_character(d)
    assert "private, party, dm" in str(exc.value)


def test_missing_file(tmp_path):
    with pytest.raises(ConfigError) as exc:
        load_character(tmp_path / "Nobody")
    assert "character.yaml" in str(exc.value)


def test_round_trip(tmp_path):
    d = _write(tmp_path)
    ch = load_character(d)
    ch.level = 4
    save_character(ch)
    again = load_character(d)
    assert again.level == 4 and again.campaign["party"][0]["name"] == "Pal"
    assert list(again.campaign) == ["name", "rules", "party"]


def test_env_dir_and_output_path(tmp_path, monkeypatch):
    d = _write(tmp_path)
    monkeypatch.setenv("DDTOOLS_CHARACTER_DIR", str(d))
    monkeypatch.setenv("DDTOOLS_OUT", str(tmp_path / "out"))
    ch = load_character()
    assert output_path(ch, "Guide.pdf") == tmp_path / "out" / "Guide.pdf"
    assert (tmp_path / "out").is_dir()


def test_rules_rows_formats_statuses(tmp_path):
    from ddtools.config import rules_rows

    ch = load_character(_write(tmp_path))
    ch.campaign["rules"] = [
        {"text": "A", "status": "confirmed"},
        {"text": "B", "status": "confirmed", "note": "campaign guide"},
        {"text": "C", "status": "open"},
        {"text": "D", "status": "assumption", "note": "Player’s working assumption"},
        {"text": "E", "status": "planned", "note": "Planned from level 5"},
    ]
    assert rules_rows(ch) == [
        ["Topic", "Status"],
        ["A", "<b>Confirmed</b>"],
        ["B", "<b>Confirmed</b> (campaign guide)"],
        ["C", "<b>Open</b>"],
        ["D", "Player’s working assumption"],
        ["E", "Planned from level 5"],
    ]


def test_rules_rows_filters_by_audience(tmp_path):
    from ddtools.config import rules_rows

    ch = load_character(_write(tmp_path))
    ch.campaign["rules"] = [
        {"text": "Everywhere", "status": "confirmed"},
        {"text": "Guide only", "status": "open", "show_in": ["private"]},
    ]
    assert [r[0] for r in rules_rows(ch, "dm")] == ["Topic", "Everywhere"]
    assert [r[0] for r in rules_rows(ch, "private")] == ["Topic", "Everywhere", "Guide only"]
    assert [r[0] for r in rules_rows(ch)] == ["Topic", "Everywhere", "Guide only"]


def test_unknown_keys_are_kept_for_plugins(tmp_path):
    d = _write(tmp_path, VALID + "page_url: https://example.com/page\n")
    ch = load_character(d)
    assert ch.extra == {"page_url": "https://example.com/page"}
    save_character(ch)
    assert load_character(d).extra == ch.extra


def test_old_build_script_names_still_work(tmp_path):
    # Every campaign's copied build scripts import these: they must keep working.
    from ddtools import config

    ch = load_character(_write(tmp_path))
    assert config.stamp(ch) == config.level_updated_label(ch) == "Level 3 · updated 28 Sep 2026"
    assert config.date_stamp(ch) == config.updated_label(ch) == "updated 28 Sep 2026"
    assert config.present is config.is_present
    assert config.is_present(ch, "Pal") and not config.is_present(ch, "Nobody")


def test_output_dir_is_pure_and_output_path_makes_the_folder(tmp_path, monkeypatch):
    from ddtools.config import output_dir

    monkeypatch.delenv("DDTOOLS_OUT", raising=False)
    ch = load_character(_write(tmp_path))
    assert output_dir(ch) == ch.dir / "pdf" and not (ch.dir / "pdf").exists()
    assert output_path(ch, "Guide.pdf") == ch.dir / "pdf" / "Guide.pdf"
    assert (ch.dir / "pdf").is_dir()


def test_statuses_come_from_the_status_type():
    from typing import get_args

    from ddtools.config import STATUSES, Status

    assert STATUSES == get_args(Status) == ("active", "retired")


def test_document_script_resolution(tmp_path):
    import sys

    from ddtools.config import Document

    own = Document(file="pdf/W.pdf", script="ddtools:workbook", audience="party")
    assert own.is_builtin and own.module_name == "ddtools.workbook"
    assert own.command(tmp_path) == (
        Path("ddtools:workbook"),
        [sys.executable, "-m", "ddtools.workbook"],
        tmp_path,
    )
    assert own.source(tmp_path).name == "workbook.py"

    repo = Document(file="pdf/G.pdf", script="src/build_guide.py", audience="private")
    script = tmp_path / "src" / "build_guide.py"
    assert not repo.is_builtin and repo.module_name is None
    assert repo.command(tmp_path) == (script, [sys.executable, str(script)], tmp_path / "src")
    assert repo.source(str(tmp_path)) == script

    missing = Document(file="pdf/X.pdf", script="ddtools:nothing_here", audience="party")
    with pytest.raises(ConfigError, match="ddtools has no such document"):
        missing.source(tmp_path)


PARTY_YAML = VALID.replace(
    "  party:\n    - {name: Pal, dndbeyond_id: 456, summary: Rogue}\n",
    "  party:\n"
    "    # the party, in seating order\n"
    "    - name: Pal\n"
    "      dndbeyond_id: 456  # their sheet\n"
    "      summary: Rogue\n",
)


def test_set_party_fields_edits_only_the_lines_it_needs(tmp_path):
    from ddtools.config import set_party_fields

    d = _write(tmp_path, PARTY_YAML)
    set_party_fields(d, "Pal", {"summary": "Elf Rogue", "status": "gone"})
    text = (d / "character.yaml").read_text(encoding="utf-8")
    assert "# the party, in seating order" in text and "456  # their sheet" in text
    assert load_character(d).campaign["party"] == [
        {"name": "Pal", "dndbeyond_id": 456, "summary": "Elf Rogue", "status": "gone"}
    ]


def test_set_party_fields_with_nothing_new_leaves_the_file(tmp_path):
    from ddtools.config import set_party_fields

    d = _write(tmp_path, PARTY_YAML)
    before = (d / "character.yaml").read_bytes()
    set_party_fields(d, "Pal", {"summary": "Rogue"})
    assert (d / "character.yaml").read_bytes() == before


def test_set_party_fields_for_a_stranger_raises_and_writes_nothing(tmp_path):
    from ddtools.config import set_party_fields

    d = _write(tmp_path, PARTY_YAML)
    before = (d / "character.yaml").read_bytes()
    with pytest.raises(ConfigError, match="Nobody isn't in"):
        set_party_fields(d, "Nobody", {"summary": "x"})
    assert (d / "character.yaml").read_bytes() == before


def test_add_party_member_keeps_comments(tmp_path):
    from ddtools.config import add_party_member

    d = _write(tmp_path, PARTY_YAML)
    add_party_member(d, {"name": "Bramble", "dndbeyond_id": 789})
    text = (d / "character.yaml").read_text(encoding="utf-8")
    assert "# the party, in seating order" in text
    assert [p["name"] for p in load_character(d).campaign["party"]] == ["Pal", "Bramble"]


def test_add_party_member_after_a_flow_style_item(tmp_path):
    from ddtools.config import add_party_member

    d = _write(tmp_path)  # VALID's one party member is written {name: ..., ...}
    add_party_member(d, {"name": "Bramble", "dndbeyond_id": 789})
    assert load_character(d).campaign["party"][1] == {"name": "Bramble", "dndbeyond_id": 789}


def test_write_party_writes_only_the_planned_edits(tmp_path):
    # The plan reads a copy: anything it changes there never reaches the file.
    from ddtools.config import _write_party

    d = _write(tmp_path, PARTY_YAML)

    def plan(party):
        party[0]["summary"] = "scribbled on the copy"
        return [("set", "Pal", {"level": 2})]

    _write_party(d, plan)
    assert load_character(d).campaign["party"] == [
        {"name": "Pal", "dndbeyond_id": 456, "summary": "Rogue", "level": 2}
    ]


def test_set_party_fields_rewrites_an_inline_party_list(tmp_path):
    # Not block style: no line edits, so the whole file is rewritten from the data.
    from ddtools.config import set_party_fields

    d = _write(tmp_path, VALID.replace(
        "  party:\n    - {name: Pal, dndbeyond_id: 456, summary: Rogue}\n",
        "  party: [{name: Pal, dndbeyond_id: 456, summary: Rogue}]\n",
    ))  # fmt: skip
    set_party_fields(d, "Pal", {"summary": "Elf Rogue"})
    assert load_character(d).campaign["party"][0]["summary"] == "Elf Rogue"
