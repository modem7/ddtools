"""ddtools import-workbook: a filled workbook comes back into the repo, and nothing is lost."""

import pypdf
import pytest

from ddtools import workbook as W
from ddtools.cli import main
from ddtools.config import load_character
from ddtools.lifecycle import new_character


@pytest.fixture
def mossy(tmp_path):
    d = new_character("Mossy Thistlewick", tmp_path, new_campaign="The Salt Road")
    return d


def _fill(pdf, out, values, ticks=()):
    reader = pypdf.PdfReader(pdf)
    writer = pypdf.PdfWriter(clone_from=reader)
    for page in writer.pages:
        writer.update_page_form_field_values(page, values, auto_regenerate=False)
        for name in ticks:
            writer.update_page_form_field_values(page, {name: "/Yes"}, auto_regenerate=False)
    with open(out, "wb") as f:
        writer.write(f)
    return out


def _filled(mossy, tmp_path, extra=None):
    blank = W.build_workbook(load_character(mossy))
    names = [n for n, f in pypdf.PdfReader(blank).get_fields().items() if f.get("/FT") == "/Tx"]
    values = {n: f"answer for {n}" for n in names}
    for n in names:
        if n.startswith("v1.s1.d-d-beyond-link"):
            values[n] = "https://www.dndbeyond.com/characters/44444444"
        if n.startswith("v1.s1.race-class-subclass-level"):
            values[n] = "Gnome Circle of Spores Druid, level 2"
        if n.startswith("v1.s1.character-name"):
            values[n] = "Mossy Thistlewick"
    values.update(extra or {})
    boxes = [n for n, f in pypdf.PdfReader(blank).get_fields().items() if f.get("/FT") == "/Btn"]
    return _fill(blank, tmp_path / "filled.pdf", values, ticks=boxes[:2]), values, boxes


def test_every_answer_comes_back_verbatim(mossy, tmp_path, capsys):
    filled, values, boxes = _filled(mossy, tmp_path)
    assert main(["import-workbook", str(filled), str(mossy)]) == 0
    notes = (mossy / "notes" / "sources" / "workbook-answers.md").read_text(encoding="utf-8")
    for v in values.values():
        assert v in notes
    tooltips = pypdf.PdfReader(filled).get_fields()
    for name in boxes[:2]:
        assert f"[x] {tooltips[name]['/TU']}" in notes, "ticked boxes are listed by their label"
    assert "## 1. The Basics" in notes
    assert "## 5. Build & Levelling" in notes and "&amp;" not in notes


def test_blanks_in_character_yaml_are_filled_and_nothing_is_overwritten(mossy, tmp_path, capsys):
    cfg = mossy / "character.yaml"
    cfg.write_text("# Mossy's sheet: keep this comment\n" + cfg.read_text(encoding="utf-8"),
                   encoding="utf-8")  # fmt: skip
    filled, _, _ = _filled(mossy, tmp_path)
    assert main(["import-workbook", str(filled), str(mossy)]) == 0
    ch = load_character(mossy)
    assert ch.dndbeyond_id == 44444444
    assert ch.class_summary == "Gnome Circle of Spores Druid, level 2"
    text = (mossy / "character.yaml").read_text(encoding="utf-8")
    assert "# Mossy's sheet: keep this comment" in text, "comments are kept"

    filled2, _, _ = _filled(mossy, tmp_path, {
        next(n for n in pypdf.PdfReader(filled).get_fields() if n.startswith("v1.s1.d-d-beyond")):
            "https://www.dndbeyond.com/characters/55555555",
    })  # fmt: skip
    assert main(["import-workbook", str(filled2), str(mossy)]) == 0
    out = capsys.readouterr().out
    assert load_character(mossy).dndbeyond_id == 44444444, "never overwritten"
    assert "55555555" in out and "44444444" in out, "the difference is listed"


def test_it_says_what_is_still_blank(mossy, tmp_path, capsys):
    blank = W.build_workbook(load_character(mossy))
    assert main(["import-workbook", str(blank), str(mossy)]) == 0
    out = capsys.readouterr().out
    assert "Still blank" in out and "Character name" in out


def test_a_pdf_that_is_not_a_workbook_is_refused(mossy, tmp_path, capsys):
    from reportlab.pdfgen import canvas

    other = tmp_path / "other.pdf"
    c = canvas.Canvas(str(other))
    c.drawString(10, 10, "hello")
    c.save()
    assert main(["import-workbook", str(other), str(mossy)]) == 1
    assert "not a ddtools workbook" in capsys.readouterr().out
    assert not (mossy / "notes" / "sources" / "workbook-answers.md").exists()


def test_an_earlier_import_is_kept(mossy, tmp_path, capsys):
    filled, _, _ = _filled(mossy, tmp_path)
    main(["import-workbook", str(filled), str(mossy)])
    main(["import-workbook", str(filled), str(mossy)])
    files = sorted((mossy / "notes" / "sources").glob("workbook-answers*.md"))
    assert len(files) == 2
