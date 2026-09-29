import pytest


@pytest.fixture
def two_page_pdf(tmp_path):
    """A small two-page PDF built with the shared style library."""
    from ddtools import pdfstyle as ps

    out = tmp_path / "two.pdf"
    story = [
        ps.P("First Heading", ps.h1),
        ps.P("Some body text.", ps.body),
        ps.PageBreak(),
        ps.P("Second Heading", ps.h1),
        ps.P("More text on page two.", ps.body),
    ]
    ps.build(story, out, "Test Doc · Level 3 · updated 28 Sep 2026")
    return out


def make_campaign(root):
    """A made-up campaign repo: Ash Vale in "The Salt Road", with Bramble and Cinder.

    Package tests use this, never a real character. Returns Ash's folder.
    """
    import shutil
    from pathlib import Path

    import yaml

    from ddtools.lifecycle import new_character

    d = new_character("Ash Vale", root, new_campaign="The Salt Road")
    cfg = d / "character.yaml"
    data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    data["dndbeyond_id"] = 11111111
    data["party_summary"] = "Human Fighter. Carries everyone's luggage and complains"
    data["campaign"].update(
        setting="A salt-flat caravan road between three trading towns",
        facts=[{"label": "Rests", "text": "Standard"}, {"label": "Levelling", "text": "Milestone"}],
        rules=[
            {"text": "Flanking is off", "status": "confirmed"},
            {"text": "Who runs the salt guild?", "status": "open"},
        ],
        party=[
            {"name": "Bramble", "dndbeyond_id": 22222222, "summary": "Elf Rogue"},
            {"name": "Cinder", "dndbeyond_id": 33333333, "summary": "Tiefling Warlock"},
        ],
    )
    cfg.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    (d / "secrets.txt").write_text("# Ash's secrets\nsmuggler\n", encoding="utf-8")
    fixture = Path(__file__).parent / "fixtures" / "ddb_min.json"
    shutil.copy(fixture, d / "snapshots" / "2026-01-01.json")
    return d


@pytest.fixture
def ash(tmp_path):
    """Ash Vale's folder, in a made-up campaign repo at tmp_path."""
    return make_campaign(tmp_path)
