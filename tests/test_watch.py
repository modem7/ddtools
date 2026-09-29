import copy
import json
from pathlib import Path

import pytest

from ddtools import dndbeyond as ddb
from ddtools.cli import main

FIX = Path(__file__).parent / "fixtures"
OWN = json.loads((FIX / "ddb_min.json").read_text())


def _pal(level=3):
    pal = copy.deepcopy(OWN)
    pal["id"], pal["name"] = 777, "Pal"
    pal["classes"] = [{"id": 1, "level": level, "definition": {"name": "Rogue"}}]
    return pal


@pytest.fixture
def char(tmp_path, monkeypatch):
    d = tmp_path / "Fixture_Hero"
    (d / "snapshots").mkdir(parents=True)
    (d / "character.yaml").write_text(
        "name: Fixture Hero\nlevel: 3\nupdated: 2026-09-28\ndndbeyond_id: 999\n"
        "campaign:\n  party:\n    - {name: Pal, dndbeyond_id: 777}\ndocuments: []\n",
        encoding="utf-8",
    )
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


def test_no_changes(char, monkeypatch, tmp_path):
    _serve(monkeypatch, OWN, _pal())
    assert main(["watch", str(char), "--issue-dir", str(tmp_path / "issues")]) == 0
    assert not list((tmp_path / "issues").glob("*.md")) if (tmp_path / "issues").exists() else True


def test_own_spell_added(char, monkeypatch, tmp_path):
    own = copy.deepcopy(OWN)
    own["classSpells"][0]["spells"].append({"definition": {"name": "Hex"}})
    _serve(monkeypatch, own, _pal())
    assert main(["watch", str(char), "--issue-dir", str(tmp_path / "issues")]) == 3
    body = (tmp_path / "issues" / "Fixture_Hero.md").read_text()
    assert body.splitlines()[0] == "D&D Beyond changes: Fixture Hero"
    assert "Hex" in body and "ddtools fetch" in body


def test_party_level_up(char, monkeypatch, tmp_path):
    _serve(monkeypatch, OWN, _pal(level=4))
    assert main(["watch", str(char), "--issue-dir", str(tmp_path / "issues")]) == 3
    body = (tmp_path / "issues" / "Fixture_Hero.md").read_text()
    assert "Pal" in body and "3 → 4" in body


def test_gold_only_is_not_a_change(char, monkeypatch, tmp_path):
    own = copy.deepcopy(OWN)
    own["currencies"]["gp"] = 500
    _serve(monkeypatch, own, _pal())
    assert main(["watch", str(char), "--issue-dir", str(tmp_path / "issues")]) == 0


def test_fetch_error_exits_1(char, monkeypatch, capsys):
    _serve(monkeypatch, OWN, ddb.DndBeyondError("Character 777: HTTP 429 from D&D Beyond"))
    assert main(["watch", str(char)]) == 1
    out = capsys.readouterr()
    assert "Pal" in out.out + out.err and "429" in out.out + out.err


def test_level_up_includes_checklist(char, monkeypatch, tmp_path):
    own = json.loads((FIX / "ddb_min_levelup.json").read_text())
    _serve(monkeypatch, own, _pal())
    main(["watch", str(char), "--issue-dir", str(tmp_path / "issues")])
    body = (tmp_path / "issues" / "Fixture_Hero.md").read_text()
    assert "Level-up checklist" in body and "Gold" in body


def test_subclass_change_is_reported(char, monkeypatch, tmp_path):
    own = copy.deepcopy(OWN)
    own["classes"][1]["subclassDefinition"] = {"name": "Clockwork Soul"}
    _serve(monkeypatch, own, _pal())
    assert main(["watch", str(char), "--issue-dir", str(tmp_path / "issues")]) == 3
    assert "Clockwork Soul" in (tmp_path / "issues" / "Fixture_Hero.md").read_text()


def test_changes_are_written_even_when_another_sheet_errors(char, monkeypatch, tmp_path):
    own = copy.deepcopy(OWN)
    own["classSpells"][0]["spells"].append({"definition": {"name": "Hex"}})
    _serve(monkeypatch, own, ddb.DndBeyondError("Character 777: HTTP 403"))
    assert main(["watch", str(char), "--issue-dir", str(tmp_path / "issues")]) == 1
    assert "Hex" in (tmp_path / "issues" / "Fixture_Hero.md").read_text()
