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
