"""The party workbook, built by ddtools for any campaign."""

import pypdf
import pytest
import yaml

from ddtools import workbook as W
from ddtools.cli import main
from ddtools.config import load_character
from ddtools.lifecycle import new_character


@pytest.fixture
def mossy(tmp_path):
    d = new_character("Mossy Thistlewick", tmp_path, new_campaign="The Salt Road")
    cfg = d / "character.yaml"
    data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    data["party_summary"] = "Gnome Spores Druid. Forages mushrooms, feeds everyone"
    data["dndbeyond_id"] = 11111111
    data["campaign"]["facts"] = [{"label": "Rests", "text": "Standard"}]
    data["campaign"]["party"] = [
        {"name": "Ash Vale", "dndbeyond_id": 22222222, "summary": "Human Fighter"},
        {"name": "Bramble", "dndbeyond_id": 33333333, "summary": "Elf Rogue", "status": "gone"},
    ]
    cfg.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return d


def _text(pdf):
    return " ".join(" ".join(p.extract_text() for p in pypdf.PdfReader(pdf).pages).split())


def test_the_workbook_is_built_from_the_campaign(mossy):
    out = W.build_workbook(load_character(mossy))
    text = _text(out)
    assert "A workbook for your party" in text, "no audience given: a plain default"
    assert "Mossy Thistlewick" in text and "Gnome Spores Druid" in text
    assert "Ash Vale" in text and "Bramble" not in text, "a teammate who's gone isn't listed"
    assert "Rests Standard" in text
    assert "in a D&D 5e campaign." in text
    assert "Read all two D&D Beyond links" in text
    assert "Remember the" not in text and "Not allowed" not in text, "no campaign specifics"


def test_every_field_has_a_stable_versioned_name_and_its_label(mossy):
    out = W.build_workbook(load_character(mossy))
    fields = pypdf.PdfReader(out).get_fields()
    names = list(fields)
    assert names and all(n.startswith("v1.s") for n in names)
    assert len(names) == len(set(names))
    name = next(n for n in names if n.startswith("v1.s1.character-name"))
    assert fields[name].get("/TU") == "Character name"
    again = pypdf.PdfReader(W.build_workbook(load_character(mossy))).get_fields()
    assert list(again) == names, "the same workbook gets the same names"


def test_ddtools_workbook_writes_it(mossy, capsys):
    assert main(["workbook", str(mossy)]) == 0
    assert (mossy / "pdf" / W.FILE).exists()
    assert W.FILE in capsys.readouterr().out
