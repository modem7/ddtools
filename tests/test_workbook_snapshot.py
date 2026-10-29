"""The workbook's output, pinned: field names and order, labels, section titles, pages, text.

A change to the workbook's wording or layout must update ``fixtures/workbook_snapshot.json``
on purpose. Regenerate it with ``DDTOOLS_UPDATE_SNAPSHOT=1 pytest tests/test_workbook_snapshot.py``.
"""

import datetime
import json
import os
from pathlib import Path

import pypdf
import pytest
import yaml

from ddtools import workbook as W
from ddtools.config import load_character
from ddtools.lifecycle import new_character

SNAPSHOT = Path(__file__).parent / "fixtures" / "workbook_snapshot.json"


@pytest.fixture
def mossy(tmp_path):
    """Mossy with every ``campaign.workbook`` option set, so every branch is drawn."""
    d = new_character("Mossy Thistlewick", tmp_path, new_campaign="The Salt Road")
    cfg = d / "character.yaml"
    data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    data["updated"] = datetime.date(2026, 9, 28)
    data["party_summary"] = "Gnome Spores Druid. Forages mushrooms, feeds everyone"
    data["dndbeyond_id"] = 11111111
    data["campaign"]["facts"] = [
        {"label": "Rests", "text": "Standard"},
        {"label": "Levelling", "text": "Milestone"},
    ]
    data["campaign"]["party"] = [
        {"name": "Ash Vale", "dndbeyond_id": 22222222, "summary": "Human Fighter"},
        {"name": "Bramble", "dndbeyond_id": 33333333, "summary": "Elf Rogue", "status": "gone"},
        {"name": "Cinder Moss", "dndbeyond_id": 44444444, "summary": "Tiefling Warlock"},
    ]
    data["campaign"]["workbook"] = {
        "audience": "the Salt Road party",
        "campaign_line": "The Salt Road, a caravan campaign",
        "battlefield": "the salt flats",
        "not_allowed": "no homebrew races",
        "example_place": "Brinemarket",
        "combat_notes": ["Flanking is on.", "Potions are a bonus action."],
    }
    cfg.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return d


def _snapshot(pdf, ch):
    reader = pypdf.PdfReader(pdf)
    fields = reader.get_fields() or {}
    from ddtools.workbook_import import answers_markdown, read_fields

    headings = [
        line
        for line in answers_markdown(ch, read_fields(pdf), "x.pdf").splitlines()
        if line.startswith("## ")
    ]
    return {
        "pages": len(reader.pages),
        "fields": [[n, str(f.get("/FT")), str(f.get("/TU"))] for n, f in fields.items()],
        "headings": headings,
        "text": [" ".join(p.extract_text().split()) for p in reader.pages],
    }


def test_the_workbook_matches_its_snapshot(mossy):
    ch = load_character(mossy)
    got = _snapshot(W.build_workbook(ch), ch)
    if os.environ.get("DDTOOLS_UPDATE_SNAPSHOT"):
        SNAPSHOT.write_text(json.dumps(got, indent=1, ensure_ascii=False) + "\n", "utf-8")
    want = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert got["pages"] == want["pages"]
    assert got["fields"] == want["fields"], "field names, order and labels are stable"
    assert got["headings"] == want["headings"], "the import's section titles are stable"
    assert got["text"] == want["text"]


def test_every_section_title_is_in_the_workbook(mossy):
    ch = load_character(mossy)
    text = " ".join(_snapshot(W.build_workbook(ch), ch)["text"])
    want = json.loads(SNAPSHOT.read_text(encoding="utf-8"))["headings"]
    for h in want:
        num, _, name = h[3:].partition(". ")
        if name:
            assert f"{num}. {name}" in text
