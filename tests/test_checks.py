from ddtools.checks import (
    Secret,
    clean,
    find_future_spells,
    find_spoilers,
    load_secrets,
    load_spell_names,
)


def test_load_secrets(tmp_path):
    f = tmp_path / "secrets.txt"
    f.write_text('# comment\n\nsmuggler\n"Fox"\nCaptain’s Cargo\n', encoding="utf-8")
    assert load_secrets(f) == [
        Secret("smuggler", False),
        Secret("Fox", True),
        Secret("Captain's Cargo", False),
    ]


def test_clean_quotes_and_whitespace():
    assert clean("Captain’s  Cargo\n“x”­z") == 'Captain\'s Cargo "x"z'


def test_curly_apostrophe_matches_straight_secret():
    hits = find_spoilers(["Read Captain’s Cargo today"], [Secret("Captain's Cargo", False)])
    assert hits[0]["page"] == 1 and hits[0]["term"] == "Captain's Cargo"


def test_secret_split_across_lines():
    assert find_spoilers(["the false\n bottom is here"], [Secret("false bottom", False)])


def test_word_boundaries_and_case():
    secrets = [Secret("oath", False)]
    assert not find_spoilers(["She is oathbound to nobody"], secrets)
    assert find_spoilers(["An OATH she can’t keep"], secrets)


def test_exact_secret_is_case_sensitive():
    secrets = [Secret("Fox", True)]
    assert not find_spoilers(["a fox in the henhouse"], secrets)
    assert find_spoilers(["The Fox drops the act"], secrets)


def test_context_is_included():
    hit = find_spoilers(["x" * 60 + " smuggler " + "y" * 60], [Secret("smuggler", False)])[0]
    assert "smuggler" in hit["context"] and len(hit["context"]) < 120


KNOWN = {"Scorching Ray", "Shield", "Fireball", "Light"}
SHEET = {"Shield"}


def test_future_spell_without_level_is_flagged():
    pages = ["Her best spells (Scorching Ray, and more) love a corridor."]
    hits = find_future_spells(pages, KNOWN, SHEET, [], [], [])
    assert [h["spell"] for h in hits] == ["Scorching Ray"]


def test_level_label_allows_future_spell():
    pages = ["Later she gets Scorching Ray at level 4. Fireball (level 8+) too."]
    assert find_future_spells(pages, KNOWN, SHEET, [], [], []) == []


def test_future_section_allows_spells():
    pages = ["Right Now Shield is ready. Coming Soon 4 Scorching Ray, Fireball"]
    headings = [{"text": "Right Now", "page": 1}, {"text": "Coming Soon", "page": 1}]
    assert find_future_spells(pages, KNOWN, SHEET, headings, ["Coming Soon"], []) == []


def test_future_section_does_not_cover_earlier_text():
    pages = ["Right Now Fireball is ready. Coming Soon Scorching Ray"]
    headings = [{"text": "Right Now", "page": 1}, {"text": "Coming Soon", "page": 1}]
    hits = find_future_spells(pages, KNOWN, SHEET, headings, ["Coming Soon"], [])
    assert [h["spell"] for h in hits] == ["Fireball"]


def test_spell_on_sheet_and_ignored_are_not_flagged():
    pages = ["Shield up. A Light Domain Cleric."]
    assert find_future_spells(pages, KNOWN, SHEET, [], [], ["Light"]) == []


def test_spell_names_are_case_sensitive():
    assert (
        find_future_spells(["a light touch and a fireball-ish mood"], KNOWN, SHEET, [], [], [])
        == []
    )


def test_bundled_spell_list():
    names = load_spell_names()
    assert {
        "Fireball",
        "Scorching Ray",
        "Aganazzar's Scorcher",
        "Mind Sliver",
        "Silvery Barbs",
    } <= names
    assert len(names) > 400


def _party_char(tmp_path, text):
    import json
    from pathlib import Path

    from ddtools import pdfstyle as ps

    d = tmp_path / "Hero"
    for sub in ("pdf", "src", "snapshots"):
        (d / sub).mkdir(parents=True)
    (d / "src" / "build_h.py").write_text('S.append(P("Handout", h1))\n', encoding="utf-8")
    ps.build([ps.P("Handout", ps.h1), ps.P(text, ps.body)], d / "pdf" / "H.pdf", "H")
    (d / "secrets.txt").write_text("smuggler\n", encoding="utf-8")
    fixture = Path(__file__).parent / "fixtures" / "ddb_min.json"
    (d / "snapshots" / "2026-09-28.json").write_text(fixture.read_text())
    (d / "character.yaml").write_text(
        json.dumps(
            {"name": "Hero", "level": 3, "updated": "2026-09-28",
             "documents": [{"file": "pdf/H.pdf", "script": "src/build_h.py", "audience": "party"}]}
        ).replace('"2026-09-28"', "2026-09-28"),
        encoding="utf-8",
    )  # fmt: skip
    return d


def test_cli_check_clean(tmp_path, capsys):
    from ddtools.cli import main

    assert main(["check", str(_party_char(tmp_path, "Easy, friend. Eldritch Blast."))]) == 0
    assert "No problems" in capsys.readouterr().out


def test_cli_check_finds_spoiler_and_spell(tmp_path, capsys):
    from ddtools.cli import main

    d = _party_char(tmp_path, "Easy, smuggler. Her best spell is Fireball.")
    assert main(["check", str(d)]) == 1
    out = capsys.readouterr().out
    assert "spoiler 'smuggler'" in out and "'Fireball'" in out


def test_secret_split_across_a_page_break():
    hits = find_spoilers(
        ["all about the false", "bottom of the crate"], [Secret("false bottom", False)]
    )
    assert [h["page"] for h in hits] == [1]


def test_run_checks_uses_given_pdf_dir(tmp_path):
    from ddtools.checks import run_checks
    from ddtools.config import load_character

    d = _party_char(tmp_path, "Easy, friend.")
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    from ddtools import pdfstyle as ps

    ps.build([ps.P("Handout", ps.h1), ps.P("Easy, smuggler.", ps.body)], fresh / "H.pdf", "H")
    assert run_checks(load_character(d)) == []
    assert any("smuggler" in p for p in run_checks(load_character(d), pdf_dir=fresh))
