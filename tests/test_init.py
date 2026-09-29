"""ddtools init: a campaign repo with the repo standard, filled in for its owner."""

import re
from pathlib import Path

import yaml

from ddtools import __version__
from ddtools.cli import main
from ddtools.config import load_character  # noqa: F401  (the repo's characters load)

STANDARD = [
    ".github/settings.yml", ".github/CODEOWNERS", ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml", ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/config.yml", ".github/workflows/autoassign.yml",
    ".github/workflows/ci.yml", ".github/workflows/dndbeyond-watch.yml", "renovate.json",
    ".editorconfig", ".gitattributes", ".gitignore", ".wakatime-project",
    ".claude/settings.json", "LICENSE", "CONTRIBUTING.md", "README.md", "CLAUDE.md",
    "requirements.txt", "archive/.gitkeep",
]  # fmt: skip


def _all_text(root):
    return "\n".join(p.read_text(encoding="utf-8") for p in root.rglob("*") if p.is_file())


def test_a_friends_repo_is_theirs(tmp_path, capsys):
    repo = tmp_path / "my-campaign"
    assert main(["init", str(repo), "--owner", "ash-vale"]) == 0
    for rel in STANDARD:
        assert (repo / rel).is_file(), rel
    assert (repo / ".github/CODEOWNERS").read_text().strip() == "* @ash-vale"
    assert "assignees: ash-vale" in (repo / ".github/workflows/autoassign.yml").read_text()
    settings = yaml.safe_load((repo / ".github/settings.yml").read_text())
    assert settings["repository"]["name"] == "my-campaign"
    assert settings["repository"]["private"] is True
    assert "_extends" not in settings, "no .github repo assumed"
    assert not (repo / ".github/FUNDING.yml").exists()
    assert "github.com/ash-vale/my-campaign/security" in (
        repo / ".github/ISSUE_TEMPLATE/config.yml").read_text()  # fmt: skip
    assert f"ddtools.git@v{__version__}" in (repo / "requirements.txt").read_text()
    text = _all_text(repo)
    assert "modem7" not in text.replace("github.com/modem7/ddtools", ""), "nothing of modem7's"
    assert not re.search(r"\{\{[A-Z_]+\}\}", text), "every placeholder is filled"
    assert "Copyright (c)" in (repo / "LICENSE").read_text() and "ash-vale" in (
        repo / "LICENSE").read_text()  # fmt: skip


def test_the_template_repo_options(tmp_path):
    repo = tmp_path / "dnd-campaign-template"
    assert main(["init", str(repo), "--owner", "modem7", "--public", "--template",
                 "--extends", "--funding", "modem7"]) == 0  # fmt: skip
    settings = yaml.safe_load((repo / ".github/settings.yml").read_text())
    assert settings["_extends"] == ".github"
    assert settings["repository"]["private"] is False
    assert settings["repository"]["is_template"] is True
    assert (repo / ".github/FUNDING.yml").read_text().strip() == "buy_me_a_coffee: modem7"
    assert "github>modem7/renovate-config" in (repo / "renovate.json").read_text()


def test_rerunning_fills_blanks_and_keeps_everything(tmp_path, capsys):
    repo = tmp_path / "my-campaign"
    repo.mkdir()
    (repo / "README.md").write_text("My own readme\n")
    assert main(["init", str(repo), "--owner", "ash-vale"]) == 0
    out = capsys.readouterr().out
    assert (repo / "README.md").read_text() == "My own readme\n"
    assert "Kept README.md" in out
    before = _all_text(repo)
    assert main(["init", str(repo), "--owner", "someone-else"]) == 0
    assert _all_text(repo) == before, "a second run changes nothing"


def test_a_new_repo_builds_a_character(tmp_path, monkeypatch):
    repo = tmp_path / "my-campaign"
    main(["init", str(repo), "--owner", "ash-vale"])
    monkeypatch.chdir(repo)
    assert main(["new-character", "Mossy Thistlewick", "--new-campaign", "The Salt Road"]) == 0
    assert main(["build", str(repo / "Mossy_Thistlewick")]) == 0
    fixture = Path(__file__).parent / "fixtures" / "ddb_min.json"
    (repo / "Mossy_Thistlewick" / "snapshots" / "2026-01-01.json").write_text(fixture.read_text())
    assert main(["check", str(repo / "Mossy_Thistlewick")]) == 0
