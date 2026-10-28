import pytest

from ddtools.config import load_character
from ddtools.lifecycle import list_characters, new_character, retire, slugify

from conftest import make_campaign


def test_slugify():
    assert slugify("Ash Vale") == "Ash_Vale"
    assert slugify("  Brindle O'Hare ") == "Brindle_OHare"
    assert slugify("Zoë Quill") == "Zoe_Quill"
    assert slugify("../x") == "x"
    with pytest.raises(ValueError):
        slugify("  ../  ")


@pytest.fixture
def repo(tmp_path):
    make_campaign(tmp_path)
    return tmp_path


def test_new_character_from_campaign(repo):
    d = new_character("Mossy Thistlewick", repo, campaign_from=repo / "Ash_Vale")
    assert d == repo / "Mossy_Thistlewick"
    ch = load_character(d)
    ash = load_character(repo / "Ash_Vale")
    assert ch.name == "Mossy Thistlewick" and ch.level == 1 and ch.status == "active"
    assert ch.campaign["rules"] == ash.campaign["rules"]
    assert {d.audience for d in ch.documents} == {"private", "party", "dm"}
    assert (d / "src" / "build_guide.py").exists() and (d / "secrets.txt").exists()


def test_new_character_drops_itself_from_party(repo):
    d = new_character("Bramble", repo, campaign_from=repo / "Ash_Vale")
    assert "Bramble" not in [p["name"] for p in load_character(d).campaign["party"]]


def test_new_character_new_campaign(repo):
    d = new_character("Zoë Quill", repo, new_campaign="Curse of Strahd")
    ch = load_character(d)
    assert d.name == "Zoe_Quill" and ch.campaign["name"] == "Curse of Strahd"
    assert ch.campaign["party"] == [] and ch.campaign["rules"] == []


def test_new_character_needs_exactly_one_campaign_source(repo):
    with pytest.raises(ValueError):
        new_character("X", repo)
    with pytest.raises(ValueError):
        new_character("X", repo, campaign_from=repo / "Ash_Vale", new_campaign="Y")


def test_new_character_refuses_existing(repo):
    new_character("Mossy", repo, new_campaign="C")
    with pytest.raises(FileExistsError):
        new_character("Mossy", repo, new_campaign="C")


def test_retire(repo):
    dest = retire(repo / "Ash_Vale", "death", "Fell off the wagon", repo)
    assert dest == repo / "archive" / "Ash_Vale" and not (repo / "Ash_Vale").exists()
    ch = load_character(dest)
    assert ch.status == "retired" and ch.retired["reason"] == "death"
    note = (dest / "RETIRED.md").read_text()
    assert "death" in note and "Fell off the wagon" in note
    assert "smuggler" in note and "salt guild" in note


def test_retire_note_skips_indented_comments(repo):
    (repo / "Ash_Vale" / "secrets.txt").write_text(
        "  # an indented comment\nsmuggler\n", encoding="utf-8"
    )
    note = (retire(repo / "Ash_Vale", "death", "", repo) / "RETIRED.md").read_text()
    assert "smuggler" in note and "indented comment" not in note


def test_retire_refuses_existing_archive(repo):
    (repo / "archive" / "Ash_Vale").mkdir(parents=True)
    with pytest.raises(FileExistsError):
        retire(repo / "Ash_Vale", "tpk", "", repo)


def test_retire_rejects_unknown_reason(repo):
    with pytest.raises(ValueError):
        retire(repo / "Ash_Vale", "bored", "", repo)


def test_list_characters(repo):
    new_character("Mossy", repo, new_campaign="C")
    retire(repo / "Mossy", "retired", "", repo)
    names = {(c.name, c.status) for c in list_characters(repo)}
    assert names == {("Ash Vale", "active"), ("Mossy", "retired")}


def test_cli_new_retire_list(repo, monkeypatch, capsys):
    import json

    from ddtools.cli import main

    monkeypatch.chdir(repo)
    assert main(["new-character", "Mossy Thistlewick", "--campaign-from", "Ash_Vale"]) == 0
    assert (repo / "Mossy_Thistlewick" / "character.yaml").exists()
    assert main(["new-character", "Mossy Thistlewick", "--new-campaign", "X"]) == 1
    assert main(["retire", "Mossy_Thistlewick", "--reason", "tpk", "--note", "Dragon"]) == 0
    capsys.readouterr()
    assert main(["list", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert {"name": "Mossy Thistlewick", "dir": "archive/Mossy_Thistlewick", "level": 1,
            "campaign": "The Salt Road", "status": "retired"} in rows  # fmt: skip


@pytest.mark.parametrize(
    "name, slug",
    [("Brindle: The Bold", "Brindle_The_Bold"), ("No", "No"), ("#hash", "hash"),
     ('"Lucky" Pete', "Lucky_Pete")],
)  # fmt: skip
def test_new_character_awkward_names(repo, name, slug):
    d = new_character(name, repo, new_campaign="C")
    assert d.name == slug and load_character(d).name == name


def test_new_character_failure_leaves_no_folder(repo, monkeypatch):
    import ddtools.lifecycle as lc

    def boom(*a, **k):
        raise RuntimeError("disk full")

    monkeypatch.setattr(lc, "save_character", boom)
    monkeypatch.setattr(lc.yaml, "safe_dump", boom)
    with pytest.raises(RuntimeError):
        new_character("Mossy", repo, new_campaign="C")
    assert not (repo / "Mossy").exists()


def _state(d):
    notes = d / "RETIRED.md"
    return (d / "character.yaml").read_bytes(), notes.read_bytes() if notes.exists() else None


@pytest.mark.parametrize("where", ["save", "note", "rename", "copy"])
def test_retire_failure_leaves_character_as_it_was(repo, monkeypatch, where):
    import errno

    import ddtools.lifecycle as lc

    ash = repo / "Ash_Vale"
    before = _state(ash)

    def boom(*a, **k):
        raise OSError("disk full")

    def half_copy(src, dst, **k):
        (dst / "partial").mkdir(parents=True)
        raise OSError("disk full")

    if where == "save":
        monkeypatch.setattr(lc, "save_character", boom)
    elif where == "note":
        monkeypatch.setattr(lc, "_retired_note", lambda *a: "note\n")
        real_write = lc.Path.write_text
        monkeypatch.setattr(lc.Path, "write_text", lambda self, *a, **k: (
            boom() if self.name == "RETIRED.md" else real_write(self, *a, **k)))  # fmt: skip
    elif where == "rename":
        monkeypatch.setattr(lc.os, "rename", boom)
    else:  # another filesystem: the copy fails part-way
        monkeypatch.setattr(lc.os, "rename", lambda *a: (_ for _ in ()).throw(
            OSError(errno.EXDEV, "cross-device link")))  # fmt: skip
        monkeypatch.setattr(lc.shutil, "copytree", half_copy)
    with pytest.raises(OSError):
        retire(ash, "death", "", repo)
    assert _state(ash) == before
    assert load_character(ash).status == "active"
    assert not (repo / "archive" / "Ash_Vale").exists()


def test_retire_failure_keeps_an_existing_retired_note(repo, monkeypatch):
    import ddtools.lifecycle as lc

    ash = repo / "Ash_Vale"
    (ash / "RETIRED.md").write_text("my own notes\n", encoding="utf-8")
    monkeypatch.setattr(lc.os, "rename", lambda *a: (_ for _ in ()).throw(OSError("busy")))
    with pytest.raises(OSError):
        retire(ash, "death", "", repo)
    assert (ash / "RETIRED.md").read_text(encoding="utf-8") == "my own notes\n"


def test_retire_across_filesystems(repo, monkeypatch):
    import errno

    import ddtools.lifecycle as lc

    monkeypatch.setattr(lc.os, "rename", lambda *a: (_ for _ in ()).throw(
        OSError(errno.EXDEV, "cross-device link")))  # fmt: skip
    dest = retire(repo / "Ash_Vale", "death", "", repo)
    assert not (repo / "Ash_Vale").exists() and load_character(dest).status == "retired"


def test_lifecycle_errors_are_ddtools_errors(repo):
    from ddtools.errors import DdtoolsError

    with pytest.raises(DdtoolsError):
        retire(repo / "Ash_Vale", "bored", "", repo)
    with pytest.raises(DdtoolsError):
        new_character("Ash Vale", repo, new_campaign="C")
