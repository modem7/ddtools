"""Exact output of summary, diff, watch and golden, so a refactor can't change a byte."""

import copy
import json
from pathlib import Path

import pytest

from ddtools import dndbeyond as ddb
from ddtools import pdfstyle as ps
from ddtools.build import BuildError
from ddtools.cli import main

FIX = Path(__file__).parent / "fixtures"
OWN = json.loads((FIX / "ddb_min.json").read_text())
YAML = (
    "name: Fixture Hero\nlevel: 3\nupdated: 2026-09-28\ndndbeyond_id: 999\n"
    "campaign:\n  party:\n    - {name: Pal, dndbeyond_id: 777}\ndocuments: []\n"
)


def _run(capsys, argv):
    code = main(argv)
    out = capsys.readouterr()
    return code, out.out, out.err


def _char(tmp_path, snapshots):
    d = tmp_path / "Fixture_Hero"
    (d / "snapshots").mkdir(parents=True)
    (d / "character.yaml").write_text(YAML, encoding="utf-8")
    for i, name in enumerate(snapshots):
        (d / "snapshots" / f"2026-09-2{i}.json").write_text((FIX / name).read_text())
    return d


# ---- summary and diff ----------------------------------------------------

SUMMARY = """\
Fixture Hero: level 3, base HP 15
Classes: Warlock 2 (The Fiend), Sorcerer 1
Stats: STR 8, DEX 20, CON 13, INT 12, WIS 13, CHA 17
Spells:
  Warlock: Eldritch Blast, Witch Bolt
  Race: Cure Wounds
  Item: Call Lightning
Options: Repelling Blast
Feats: Painful Joke
Magic items: Winged Boots (attuned)
Gold: 4 cp, 19 sp, 18 gp
"""

DIFF_LEVELUP = """\
2026-09-20.json → 2026-09-21.json
Level: 3 → 4
Spells added (Warlock): Scorching Ray
Spells removed (Warlock): Witch Bolt
Options added: Agonizing Blast
Gold: gp 18 → 40

Level-up checklist:
  [ ] Cheat sheet in the personal guide: stats, slots, actions for the new level
  [ ] Party handout: 'What She Can Do for You Right Now' and 'Coming Soon'
  [ ] DM brief: 'Current Numbers' and the level plan
  [ ] Personal guide: level table and 'Next level' boxes
  [ ] character.yaml: bump `level` and `updated`
  [ ] Rebuild, `ddtools check`, preview every changed page, then `ddtools golden update`
"""


def test_summary_text(tmp_path, capsys):
    d = _char(tmp_path, ["ddb_min.json"])
    assert _run(capsys, ["summary", str(d)]) == (0, SUMMARY, "")


def test_summary_json(tmp_path, capsys):
    d = _char(tmp_path, ["ddb_min.json"])
    want = json.dumps(ddb.summarise(OWN), indent=2, ensure_ascii=False, default=str) + "\n"
    assert _run(capsys, ["summary", str(d), "--json"]) == (0, want, "")


def test_diff_level_up(tmp_path, capsys):
    d = _char(tmp_path, ["ddb_min.json", "ddb_min_levelup.json"])
    assert _run(capsys, ["diff", str(d)]) == (0, DIFF_LEVELUP, "")


def test_diff_no_changes(tmp_path, capsys):
    d = _char(tmp_path, ["ddb_min.json", "ddb_min.json"])
    assert _run(capsys, ["diff", str(d)]) == (
        0,
        "2026-09-20.json → 2026-09-21.json\nNo changes.\n",
        "",
    )


def test_diff_json(tmp_path, capsys):
    d = _char(tmp_path, ["ddb_min.json", "ddb_min_levelup.json"])
    new = json.loads((FIX / "ddb_min_levelup.json").read_text())
    want = json.dumps(ddb.diff(OWN, new), indent=2, ensure_ascii=False, default=str) + "\n"
    assert _run(capsys, ["diff", str(d), "--json"]) == (0, want, "")


# ---- watch ---------------------------------------------------------------


def _pal(level=3):
    pal = copy.deepcopy(OWN)
    pal["id"], pal["name"] = 777, "Pal"
    pal["classes"] = [{"id": 1, "level": level, "definition": {"name": "Rogue"}}]
    return pal


@pytest.fixture
def watched(tmp_path, monkeypatch):
    d = tmp_path / "Fixture_Hero"
    (d / "snapshots").mkdir(parents=True)
    (d / "character.yaml").write_text(YAML, encoding="utf-8")
    (d / "snapshots" / "2026-09-28.json").write_text(json.dumps(OWN))
    (d / "snapshots" / "party.json").write_text(json.dumps([ddb.party_entry(_pal())]))
    monkeypatch.chdir(tmp_path)
    return d


def _serve(monkeypatch, own, pal):
    def fake(cid):
        if isinstance(pal, Exception) and cid == 777:
            raise pal
        return own if cid == 999 else pal

    monkeypatch.setattr(ddb, "fetch_character", fake)


def _with_hex():
    own = copy.deepcopy(OWN)
    own["classSpells"][0]["spells"].append({"definition": {"name": "Hex"}})
    return own


WATCH_HEX = """\
D&D Beyond changes: Fixture Hero
The daily D&D Beyond check found changes for **Fixture Hero**.

## Their sheet

- Spells added (Warlock): Hex

## Start an update session

Paste this into Claude Code in the repo:

```
Run `ddtools fetch Fixture_Hero` and `ddtools diff Fixture_Hero`, update Fixture Hero's documents
per the checklist (and the party's levels if they changed), run `ddtools build`,
`ddtools check`, `ddtools preview`, and `ddtools golden update` if content changed
intentionally, then open a PR whose body says `Closes #<this issue>`.
```

"""
WATCH_ERR = "error: Pal: Character 777: HTTP 403\n"


def test_watch_no_changes_exits_0(watched, monkeypatch, capsys):
    _serve(monkeypatch, OWN, _pal())
    assert _run(capsys, ["watch", str(watched)]) == (0, "No changes.\n", "")


def test_watch_changes_exit_3(watched, monkeypatch, capsys, tmp_path):
    _serve(monkeypatch, _with_hex(), _pal())
    issues = tmp_path / "issues"
    assert _run(capsys, ["watch", str(watched), "--issue-dir", str(issues)]) == (3, WATCH_HEX, "")
    assert (issues / "Fixture_Hero.md").read_text(encoding="utf-8") == WATCH_HEX.removesuffix("\n")


def test_watch_error_exits_1(watched, monkeypatch, capsys, tmp_path):
    _serve(monkeypatch, _with_hex(), ddb.DndBeyondError("Character 777: HTTP 403"))
    issues = tmp_path / "issues"
    code, out, err = _run(capsys, ["watch", str(watched), "--issue-dir", str(issues)])
    assert (code, out, err) == (1, WATCH_HEX, WATCH_ERR)
    assert (issues / "Fixture_Hero.md").read_text(encoding="utf-8") == WATCH_HEX.removesuffix("\n")


def _no_diff(**changed):
    empty = {"level": None, "classes": None, "spells_added": {}, "spells_removed": {}}
    lists = ("options", "feats", "items")
    empty |= {f"{k}_{s}": [] for k in lists for s in ("added", "removed")}
    empty |= {"attunement_changed": [], "stats": {}, "hp_base": None, "gold": {}}
    return empty | changed


WATCH_JSON = [
    {
        "character": "Fixture Hero",
        "dir": "Fixture_Hero",
        "own": _no_diff(spells_added={"Warlock": ["Hex"]}),
        "party": [],
        "errors": [],
        "gold": {},
    }
]


def test_watch_json(watched, monkeypatch, capsys):
    _serve(monkeypatch, _with_hex(), _pal())
    code, out, err = _run(capsys, ["watch", str(watched), "--json"])
    assert (code, err) == (3, "")
    assert out == json.dumps(WATCH_JSON, indent=2, ensure_ascii=False) + "\n"


def test_watch_json_no_changes(watched, monkeypatch, capsys):
    _serve(monkeypatch, OWN, _pal())
    code, out, err = _run(capsys, ["watch", str(watched), "--json"])
    assert (code, err) == (0, "")
    assert "No changes." not in out and json.loads(out)[0]["own"] is None


def test_watch_bad_folder_goes_to_stderr(tmp_path, capsys):
    missing = tmp_path / "Nobody"
    want = f"error: {missing}/character.yaml: not found\n"
    assert _run(capsys, ["watch", str(missing)]) == (1, "", want)


# ---- golden --------------------------------------------------------------


def _doc(path, words="Body text here."):
    story = [ps.P("Heading One", ps.h1), ps.P(words, ps.body)]
    ps.build(story, path, "Doc · Level 3 · updated 28 Sep 2026")
    return path


@pytest.fixture
def golden_char(tmp_path, monkeypatch):
    char = tmp_path / "Some_One"
    (char / "src").mkdir(parents=True)
    (char / "pdf").mkdir()
    (char / "src" / "build_doc.py").write_text('S.append(P("Heading One", h1))\n', encoding="utf-8")
    (char / "character.yaml").write_text(
        "name: Some One\nlevel: 1\nupdated: 2026-09-28\ndocuments:\n"
        "  - {file: pdf/Doc.pdf, script: src/build_doc.py, audience: private}\n",
        encoding="utf-8",
    )
    _doc(char / "pdf" / "Doc.pdf")
    monkeypatch.chdir(tmp_path)
    return char


def _fake_build(monkeypatch, words="Body text here.", fail=False):
    import ddtools.build

    def fake(char_dir, out=None):
        if fail:
            raise BuildError(Path("src/build_doc.py"), "boom")
        return [_doc(Path(out) / "Doc.pdf", words)]

    monkeypatch.setattr(ddtools.build, "build_character", fake)


def test_golden_check_no_baseline(golden_char, capsys):
    want = "Some One: no golden baseline yet. Record one with `ddtools golden update Some_One`.\n"
    assert _run(capsys, ["golden", "check", str(golden_char)]) == (0, want, "")


def test_golden_capture_needs_from_committed(golden_char, capsys):
    want = "`golden capture` needs --from-committed (use `golden update` to rebuild first).\n"
    assert _run(capsys, ["golden", "capture", str(golden_char)]) == (2, want, "")


def test_golden_capture_and_update(golden_char, monkeypatch, capsys):
    want = "Doc: 1 pages, 1 headings\n"
    assert _run(capsys, ["golden", "capture", str(golden_char), "--from-committed"]) == (
        0,
        want,
        "",
    )
    _fake_build(monkeypatch)
    assert _run(capsys, ["golden", "update", str(golden_char)]) == (0, want, "")


def test_golden_capture_warns_on_missing_heading(golden_char, capsys):
    (golden_char / "src" / "build_doc.py").write_text(
        'S.append(P("Heading One", h1))\nS.append(P("Not There", h2))\n', encoding="utf-8"
    )
    want = "Doc: 1 pages, 2 headings\n  warning: heading not found in PDF text: Not There\n"
    assert _run(capsys, ["golden", "capture", str(golden_char), "--from-committed"]) == (
        0,
        want,
        "",
    )


def test_golden_check_matches_and_differs(golden_char, monkeypatch, capsys):
    _run(capsys, ["golden", "capture", str(golden_char), "--from-committed"])
    _fake_build(monkeypatch)
    assert _run(capsys, ["golden", "check", str(golden_char)]) == (0, "Doc: matches\n", "")
    _fake_build(monkeypatch, "Different words.")
    assert _run(capsys, ["golden", "check", str(golden_char)]) == (1, GOLDEN_DIFFERS, "")


GOLDEN_DIFFERS = """\
Doc: differs
  Doc: text differs on page 1:
--- baseline
+++ rebuilt
@@ -1 +1 @@
-Doc · <STAMP> Page 1 Heading One Body text here.
+Doc · <STAMP> Page 1 Heading One Different words.
"""


@pytest.mark.parametrize("action", ["check", "update"])
def test_golden_build_failure(golden_char, monkeypatch, capsys, action):
    _run(capsys, ["golden", "capture", str(golden_char), "--from-committed"])
    _fake_build(monkeypatch, fail=True)
    want = "Build failed in src/build_doc.py:\nboom\n"
    assert _run(capsys, ["golden", action, str(golden_char)]) == (1, want, "")


def test_golden_bad_folder(tmp_path, capsys):
    missing = tmp_path / "Nobody"
    want = f"{missing}/character.yaml: not found\n"
    assert _run(capsys, ["golden", "check", str(missing)]) == (1, want, "")
