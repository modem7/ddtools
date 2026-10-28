"""The error contract: every reported error is a DdtoolsError, and bad files give messages."""

import json

import pytest

from ddtools import dndbeyond as ddb
from ddtools.cli import main
from ddtools.config import ConfigError, load_character
from ddtools.errors import DdtoolsError

from conftest import make_campaign


def test_domain_errors_share_the_base():
    from ddtools.build import BuildError
    from ddtools.lifecycle import CharacterExists, LifecycleError
    from ddtools.pdfstyle import FontsMissing
    from ddtools.sheettext import SheetTextError
    from ddtools.workbook_import import NotAWorkbook

    for cls in (ConfigError, BuildError, ddb.DndBeyondError, ddb.SnapshotError, SheetTextError,
                NotAWorkbook, FontsMissing, LifecycleError, CharacterExists,
                ddb.BadCharacterId):  # fmt: skip
        assert issubclass(cls, DdtoolsError), cls
    # Existing callers that catch the stdlib types still work.
    assert issubclass(LifecycleError, ValueError) and issubclass(CharacterExists, FileExistsError)
    assert issubclass(ddb.BadCharacterId, ValueError) and issubclass(FontsMissing, RuntimeError)


def test_parse_id_raises_a_ddtools_error():
    with pytest.raises(ddb.BadCharacterId):
        ddb.parse_id("not an id")


def _yaml(tmp_path, party):
    d = tmp_path / "Hero"
    d.mkdir()
    (d / "character.yaml").write_text(
        f"name: Hero\nlevel: 1\nupdated: 2026-09-28\ncampaign:\n  party: {party}\n",
        encoding="utf-8",
    )
    return d


@pytest.mark.parametrize("party", ["[{dndbeyond_id: 5}]", "[Bramble]", "{name: X}", "[{name: ''}]"])
def test_bad_party_member_is_a_config_error(tmp_path, party):
    with pytest.raises(ConfigError) as exc:
        load_character(_yaml(tmp_path, party))
    assert "campaign.party" in str(exc.value)


def test_party_without_id_is_reported(tmp_path, monkeypatch, capsys):
    d = _yaml(tmp_path, "[{name: Bramble}]")
    monkeypatch.setattr(ddb, "fetch_character", lambda cid: pytest.fail("no fetch"))
    assert main(["party", str(d)]) == 1
    assert "no dndbeyond_id for Bramble" in capsys.readouterr().out


def test_watch_reports_party_member_without_id(tmp_path, monkeypatch):
    d = _yaml(tmp_path, "[{name: Bramble}]")
    monkeypatch.setattr(ddb, "fetch_character", lambda cid: pytest.fail("no fetch"))
    result = ddb.watch_character(load_character(d))
    assert result["errors"] == ["Bramble: no dndbeyond_id in the party list"]


def test_load_snapshot_names_the_file(tmp_path):
    bad = tmp_path / "2026-01-01.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ddb.SnapshotError) as exc:
        ddb.load_snapshot(bad)
    assert str(bad) in str(exc.value)
    with pytest.raises(ddb.SnapshotError) as exc:
        ddb.load_snapshot(tmp_path / "gone.json")
    assert "gone.json: not found" in str(exc.value)


def test_cli_reports_bad_snapshots(tmp_path, monkeypatch, capsys):
    ash = make_campaign(tmp_path)
    (ash / "snapshots" / "2026-02-01.json").write_text("{oops", encoding="utf-8")
    assert main(["summary", str(ash)]) == 1
    assert "2026-02-01.json" in capsys.readouterr().out
    assert main(["diff", str(ash)]) == 1
    assert "2026-02-01.json" in capsys.readouterr().out
    assert main(["diff", str(ash), "nope-a.json", "nope-b.json"]) == 1
    assert "nope-a.json: not found" in capsys.readouterr().out
    assert main(["check", str(ash)]) == 1
    assert "2026-02-01.json" in capsys.readouterr().out


@pytest.mark.parametrize("entry", [{"name": "x"}, {"id": 777}, "Bramble"])
def test_watch_reports_bad_snapshot_and_party_file(tmp_path, monkeypatch, entry):
    ash = make_campaign(tmp_path)
    (ash / "snapshots" / "2026-02-01.json").write_text("{oops", encoding="utf-8")
    (ash / "snapshots" / "party.json").write_text(json.dumps([entry]), encoding="utf-8")
    sheet = json.loads((ash / "snapshots" / "2026-01-01.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(ddb, "fetch_character", lambda cid: {**sheet, "id": cid})
    errors = ddb.watch_character(load_character(ash))["errors"]
    assert any("2026-02-01.json" in e for e in errors)
    assert any("party.json: not a list of party entries" in e for e in errors)


def test_cli_reports_missing_character_folder(tmp_path, capsys):
    missing = str(tmp_path / "Nobody")
    for argv in (["party", missing], ["golden", "check", missing], ["workbook", missing],
                 ["retire", missing, "--reason", "tpk"], ["fetch", "not-an-id"],
                 ["watch", missing]):  # fmt: skip
        assert main(argv) == 1, argv
        got = capsys.readouterr()
        assert (got.out + got.err).strip(), argv


def test_cli_list_reports_a_broken_character(tmp_path, monkeypatch, capsys):
    _yaml(tmp_path, "[{dndbeyond_id: 5}]")
    monkeypatch.chdir(tmp_path)
    assert main(["list"]) == 1
    assert "campaign.party[0] needs a name" in capsys.readouterr().out


def _baseline(tmp_path):
    from ddtools import pdfstyle as ps
    from ddtools.golden import capture

    script = tmp_path / "build_doc.py"
    script.write_text('S.append(P("Heading One", h1))\n', encoding="utf-8")
    pdf = tmp_path / "Doc.pdf"
    ps.build([ps.P("Heading One", ps.h1)], pdf, "Doc · Level 3 · updated 28 Sep 2026")
    capture(pdf, script, tmp_path / "golden")
    return pdf, script, tmp_path / "golden"


def test_compare_reports_broken_baselines(tmp_path):
    from ddtools.golden import compare

    pdf, script, base = _baseline(tmp_path)
    (base / "Doc" / "page-01.png").unlink()
    assert any("can't read the baseline image" in p for p in compare(pdf, script, base))
    (base / "Doc.json").write_text(json.dumps({"pages": 1}), encoding="utf-8")
    assert compare(pdf, script, base) == [
        f"Doc: baseline {base / 'Doc.json'} has no headings, texts (run `ddtools golden update`)"
    ]
    (base / "Doc.json").write_text(
        json.dumps({"pages": 1, "headings": [{"text": "x"}], "texts": []}), encoding="utf-8"
    )
    assert "a heading with no text or page" in compare(pdf, script, base)[0]
    (base / "Doc.json").write_text("{nope", encoding="utf-8")
    assert "can't read the baseline" in compare(pdf, script, base)[0]
