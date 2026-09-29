import pytest

import ddtools
from ddtools.cli import main


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert ddtools.__version__ in capsys.readouterr().out


def test_blueprints_lists_and_prints(capsys):
    assert main(["blueprints"]) == 0
    listed = capsys.readouterr().out
    for name in ("README", "personal-guide", "party-handout", "dm-brief", "party-workbook"):
        assert name in listed
    assert main(["blueprints", "party-handout"]) == 0
    assert "# Blueprint: party handout" in capsys.readouterr().out
    assert main(["blueprints", "nope"]) == 1
    assert "party-handout" in capsys.readouterr().out, "lists what exists"


def test_golden_check_compares_a_rebuild_with_the_baseline(tmp_path, monkeypatch, capsys):
    from ddtools.lifecycle import new_character

    d = new_character("Mossy Thistlewick", tmp_path, new_campaign="The Salt Road")
    monkeypatch.chdir(tmp_path)
    assert main(["golden", "check", str(d)]) == 0
    assert "no golden baseline" in capsys.readouterr().out.lower()
    assert main(["golden", "update", str(d)]) == 0
    assert main(["golden", "check", str(d)]) == 0
    assert "match" in capsys.readouterr().out.lower()
    guide = d / "src" / "build_guide.py"
    guide.write_text(guide.read_text().replace("TL;DR", "Too long", 1))
    assert main(["golden", "check", str(d)]) == 1
