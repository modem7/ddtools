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
    assert "party-handout" in capsys.readouterr().err, "lists what exists"


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


def test_a_missing_folder_is_one_line_on_stderr(tmp_path, capsys):
    missing = tmp_path / "Nobody"
    assert main(["golden", "check", str(missing)]) == 1
    got = capsys.readouterr()
    assert (got.out, got.err) == ("", f"error: {missing}/character.yaml: not found\n")


# The CLI's contract, one row per subcommand: argv ("{ash}" and "{missing}" are filled in),
# the exit code, and a fragment of the stream the message goes to. Deep behaviour is tested in
# each module's own tests; this table only documents what a user sees.
_CONTRACT = [
    # (id, argv, code, stream, fragment)
    ("summary", ["summary", "{ash}"], 0, "out", "level 3"),
    ("party", ["party", "{ash}"], 0, "out", "level 3"),
    ("diff-one-snapshot", ["diff", "{ash}"], 1, "err", "Need two snapshots"),
    ("watch-changes", ["watch", "{ash}"], 3, "out", "Ash Vale"),
    ("check-unbuilt", ["check", "{ash}"], 1, "out", "not built yet"),
    ("build", ["build", "{ash}"], 0, "out", "pages)"),
    ("preview-unbuilt", ["preview", "{ash}"], 1, "err", "No matching PDFs"),
    ("golden-check", ["golden", "check", "{ash}"], 0, "out", "no golden baseline"),
    ("sheet-text-none", ["sheet-text", "{ash}"], 1, "err", "dndbeyond.yaml: not found"),
    ("workbook", ["workbook", "{ash}"], 0, "out", "Wrote"),
    ("blueprints", ["blueprints"], 0, "out", "party-handout"),
    ("blueprints-unknown", ["blueprints", "nope"], 1, "err", "No blueprint called nope"),
    ("fetch-bad-target", ["fetch", "notanid"], 1, "err", "error: Not a D&D Beyond character id"),
    ("new-character", ["new-character", "Zed Quill", "--new-campaign", "X"], 0, "out", "Created"),
    ("init", ["init", "{ash}/../repo", "--owner", "me"], 0, "out", "Created"),
    (
        "import-workbook-no-pdf",
        ["import-workbook", "{missing}.pdf", "{ash}"],
        1,
        "err",
        "not found",
    ),
    ("summary-missing", ["summary", "{missing}"], 1, "err", "error: "),
    ("party-missing", ["party", "{missing}"], 1, "err", "character.yaml: not found"),
    ("diff-missing", ["diff", "{missing}"], 1, "err", "character.yaml: not found"),
    ("watch-missing", ["watch", "{missing}"], 1, "err", "character.yaml: not found"),
    ("check-missing", ["check", "{missing}"], 1, "err", "character.yaml: not found"),
    ("build-missing", ["build", "{missing}"], 1, "err", "character.yaml: not found"),
    ("preview-missing", ["preview", "{missing}"], 1, "err", "No matching PDFs"),
    ("golden-missing", ["golden", "check", "{missing}"], 1, "err", "character.yaml: not found"),
    ("sheet-text-missing", ["sheet-text", "{missing}"], 1, "err", "character.yaml: not found"),
    ("workbook-missing", ["workbook", "{missing}"], 1, "err", "character.yaml: not found"),
    ("retire-missing", ["retire", "{missing}", "--reason", "death"], 1, "err", "character.yaml"),
]


@pytest.mark.parametrize(
    ("argv", "code", "stream", "fragment"),
    [pytest.param(*row[1:], id=row[0]) for row in _CONTRACT],
)
def test_each_subcommand_keeps_its_contract(ash, monkeypatch, capsys, argv, code, stream, fragment):
    import json
    from pathlib import Path

    from ddtools import dndbeyond

    sheet = json.loads((Path(__file__).parent / "fixtures" / "ddb_min.json").read_text("utf-8"))
    monkeypatch.setattr(dndbeyond, "fetch_character", lambda cid: sheet)
    monkeypatch.chdir(ash.parent)
    argv = [a.format(ash=ash, missing=ash.parent / "Nobody") for a in argv]
    assert main(argv) == code
    got = capsys.readouterr()
    assert fragment in (got.out if stream == "out" else got.err)
    if stream == "err" and code == 1:
        assert got.out == "" or argv[0] in ("diff", "check", "watch")


def test_preview_names_the_image_it_wrote(ash, monkeypatch, capsys):
    monkeypatch.chdir(ash.parent)
    assert main(["build", str(ash)]) == 0
    assert main(["preview", str(ash)]) == 0
    assert "preview-" in capsys.readouterr().out.splitlines()[-1]


def test_list_shows_the_active_characters(ash, monkeypatch, capsys):
    monkeypatch.chdir(ash.parent)
    assert main(["list"]) == 0
    assert "Ash Vale" in capsys.readouterr().out


@pytest.mark.parametrize(
    "argv",
    [
        ["retire", "dir"],
        ["retire", "dir", "--reason", "nonsense"],
        ["new-character"],
        ["init", "dir"],
        ["import-workbook", "only-one-argument"],
        ["no-such-command"],
    ],
    ids=lambda a: " ".join(a),
)
def test_a_bad_command_line_is_a_parse_error(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2
    assert "error:" in capsys.readouterr().err


@pytest.mark.parametrize("pages", ["x", "0", "3-1", "1-", "-2", "a-b"])
def test_a_bad_page_range_is_a_usage_error(pages, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["preview", "dir", "--pages", pages])
    assert exc.value.code == 2
    assert "--pages" in capsys.readouterr().err


def test_a_failed_build_is_one_error_with_the_script_output(tmp_path, capsys):
    import textwrap

    from ddtools.lifecycle import new_character

    d = new_character("Mossy Thistlewick", tmp_path, new_campaign="The Salt Road")
    (d / "src" / "build_guide.py").write_text(textwrap.dedent("raise SystemExit('boom in script')"))
    assert main(["build", str(d)]) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: Build failed in ") and "boom in script" in err
