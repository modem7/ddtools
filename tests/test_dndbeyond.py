import copy
import io
import json
import urllib.error
from pathlib import Path

import pytest

from ddtools import dndbeyond as ddb

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIX / name).read_text())


def test_summarise_basics():
    s = ddb.summarise(load("ddb_min.json"))
    assert s["name"] == "Fixture Hero" and s["level"] == 3
    assert s["classes"] == [
        {"name": "Warlock", "level": 2, "subclass": "The Fiend"},
        {"name": "Sorcerer", "level": 1, "subclass": None},
    ]
    assert s["stats"]["DEX"] == 20 and s["stats"]["STR"] == 8
    assert s["spells"] == {
        "Warlock": ["Eldritch Blast", "Witch Bolt"],
        "Race": ["Cure Wounds"],
        "Item": ["Call Lightning"],
    }
    assert s["options"] == ["Repelling Blast"] and s["feats"] == ["Painful Joke"]
    assert s["items"] == [
        {"name": "Torch", "magic": False, "equipped": False, "attuned": False, "quantity": 10},
        {"name": "Winged Boots", "magic": True, "equipped": True, "attuned": True, "quantity": 1},
    ]
    assert s["gold"]["gp"] == 18


def test_summarise_tolerates_missing_parts():
    data = load("ddb_min.json")
    data["spells"] = None
    data["options"] = None
    data["classes"][0]["subclassDefinition"] = None
    data["classSpells"] = [{"characterClassId": 404, "spells": None}]
    s = ddb.summarise(data)
    assert s["spells"] == {} and s["options"] == []


def test_override_stat_wins():
    data = load("ddb_min.json")
    data["overrideStats"][1]["value"] = 15
    assert ddb.summarise(data)["stats"]["DEX"] == 15


def test_diff_level_up():
    d = ddb.diff(load("ddb_min.json"), load("ddb_min_levelup.json"))
    assert d["level"] == (3, 4)
    assert d["spells_added"] == {"Warlock": ["Scorching Ray"]}
    assert d["spells_removed"] == {"Warlock": ["Witch Bolt"]}
    assert d["options_added"] == ["Agonizing Blast"]
    assert d["gold"] == {"gp": (18, 40)}


def test_diff_gold_only():
    old = load("ddb_min.json")
    new = copy.deepcopy(old)
    new["currencies"]["gp"] = 99
    d = ddb.diff(old, new)
    assert d["gold"] == {"gp": (18, 99)}
    assert not any(v for k, v in d.items() if k != "gold")


def test_parse_id():
    assert ddb.parse_id("11111111") == 11111111
    assert ddb.parse_id("https://www.dndbeyond.com/characters/11111111") == 11111111
    assert ddb.parse_id("https://www.dndbeyond.com/characters/11111111/abc") == 11111111
    with pytest.raises(ValueError):
        ddb.parse_id("not a character")


def test_fetch_ok(monkeypatch):
    body = json.dumps({"success": True, "data": {"id": 5, "name": "X"}}).encode()
    monkeypatch.setattr(ddb, "urlopen", lambda req, timeout: io.BytesIO(body))
    assert ddb.fetch_character(5)["name"] == "X"


def test_fetch_private(monkeypatch):
    def boom(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, None)

    monkeypatch.setattr(ddb, "urlopen", boom)
    with pytest.raises(ddb.DndBeyondError) as exc:
        ddb.fetch_character(5)
    assert "Public" in str(exc.value) and "5" in str(exc.value)


def test_fetch_rate_limited(monkeypatch):
    def boom(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, None)

    monkeypatch.setattr(ddb, "urlopen", boom)
    with pytest.raises(ddb.DndBeyondError) as exc:
        ddb.fetch_character(5)
    assert "429" in str(exc.value)


def test_save_snapshot_suffix(tmp_path):
    from ddtools.config import Character

    ch = Character(tmp_path, "X", "active", 1, None, None, "", {}, [])
    a = ddb.save_snapshot(ch, {"a": 1}, today="2026-09-28")
    b = ddb.save_snapshot(ch, {"a": 2}, today="2026-09-28")
    (tmp_path / "snapshots" / "party.json").write_text("[]")
    assert a.name == "2026-09-28.json" and b.name == "2026-09-28-2.json"
    assert ddb.latest_snapshots(ch) == [a, b]


def _char(tmp_path, snapshots=()):
    d = tmp_path / "Fixture_Hero"
    (d / "snapshots").mkdir(parents=True)
    (d / "character.yaml").write_text(
        "name: Fixture Hero\nlevel: 3\nupdated: 2026-09-28\ndndbeyond_id: 999\n"
        "campaign:\n  party:\n    - {name: Pal, dndbeyond_id: 777}\ndocuments: []\n",
        encoding="utf-8",
    )
    for i, name in enumerate(snapshots):
        (d / "snapshots" / f"2026-09-2{i}.json").write_text((FIX / name).read_text())
    return d


def test_cli_summary(tmp_path, capsys):
    from ddtools.cli import main

    d = _char(tmp_path, ["ddb_min.json"])
    assert main(["summary", str(d)]) == 0
    out = capsys.readouterr().out
    assert "Fixture Hero" in out and "Witch Bolt" in out and "Winged Boots" in out


def test_cli_summary_json(tmp_path, capsys):
    from ddtools.cli import main

    d = _char(tmp_path, ["ddb_min.json"])
    assert main(["summary", str(d), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["level"] == 3


def test_cli_diff_needs_two_snapshots(tmp_path, capsys):
    from ddtools.cli import main

    d = _char(tmp_path, ["ddb_min.json"])
    assert main(["diff", str(d)]) == 1
    assert "ddtools fetch" in capsys.readouterr().out


def test_cli_diff_prints_checklist(tmp_path, capsys):
    from ddtools.cli import main

    d = _char(tmp_path, ["ddb_min.json", "ddb_min_levelup.json"])
    assert main(["diff", str(d)]) == 0
    out = capsys.readouterr().out
    assert "3 → 4" in out and "Scorching Ray" in out and "character.yaml" in out


def test_cli_fetch_saves_snapshot(tmp_path, monkeypatch, capsys):
    from ddtools.cli import main

    d = _char(tmp_path)
    monkeypatch.setattr(ddb, "fetch_character", lambda cid: load("ddb_min.json"))
    assert main(["fetch", str(d)]) == 0
    from ddtools.config import load_character

    assert len(ddb.latest_snapshots(load_character(d))) == 1


def test_cli_party(tmp_path, monkeypatch, capsys):
    from ddtools.cli import main

    d = _char(tmp_path)
    monkeypatch.setattr(ddb, "fetch_character", lambda cid: load("ddb_min.json"))
    assert main(["party", str(d), "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows[0]["level"] == 3 and rows[0]["classes"][0] == "Warlock 2 (The Fiend)"


def test_fetch_non_json_body(monkeypatch):
    monkeypatch.setattr(ddb, "urlopen", lambda req, timeout: io.BytesIO(b"<html>challenge</html>"))
    with pytest.raises(ddb.DndBeyondError) as exc:
        ddb.fetch_character(5)
    assert "Character 5" in str(exc.value)


def test_fetch_connection_reset(monkeypatch):
    class Broken(io.BytesIO):
        def read(self, *a):
            raise ConnectionResetError("reset by peer")

    monkeypatch.setattr(ddb, "urlopen", lambda req, timeout: Broken())
    with pytest.raises(ddb.DndBeyondError) as exc:
        ddb.fetch_character(5)
    assert "Character 5" in str(exc.value) and "reset" in str(exc.value)


def test_fetch_403_mentions_blocking(monkeypatch):
    def boom(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, None)

    monkeypatch.setattr(ddb, "urlopen", boom)
    with pytest.raises(ddb.DndBeyondError) as exc:
        ddb.fetch_character(5)
    assert "blocking" in str(exc.value)


def test_party_entry_carries_the_sheets_gender():
    import json as _json

    data = _json.loads((Path(__file__).parent / "fixtures" / "ddb_min.json").read_text())
    body = data.get("data", data)
    assert ddb.party_entry(data)["gender"] is None
    body["gender"] = " Female "
    assert ddb.party_entry(data)["gender"] == "Female"
