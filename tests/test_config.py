from datetime import date

import pytest

from ddtools.config import ConfigError, load_character, output_path, save_character, stamp

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


def test_stamp_format(tmp_path):
    assert stamp(load_character(_write(tmp_path))) == "Level 3 · updated 28 Sep 2026"


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
