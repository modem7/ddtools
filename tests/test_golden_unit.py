from ddtools import pdfstyle as ps
from ddtools.golden import capture, compare, headings_from_script, locate_headings, normalise

SCRIPT = """
S.append(P("Part 1 — Where You Are", h1))
S.append(P("Items &amp; Attunement", h2))
S.append(P("<i>Captain’s Cargo</i> (Secret)", h2))
S.append(P(f"{num}. {name}", h1))
S += section(14, "Hand It to Claude", 2, "why", skip=None)
S.append(P("Just body text", body))
"""


def test_normalise_replaces_stamps():
    text = "Guide · Level 3 · updated 28 Sep 2026  Page 4\nWorkbook · updated 27 Sep 2026"
    out = normalise(text)
    assert "28 Sep" not in out and "27 Sep" not in out
    assert out.count("<STAMP>") == 2
    assert "  " not in out


def test_headings_from_script(tmp_path):
    script = tmp_path / "build_x.py"
    script.write_text(SCRIPT, encoding="utf-8")
    assert headings_from_script(script) == [
        ("h1", "Part 1 — Where You Are"),
        ("h2", "Items & Attunement"),
        ("h2", "Captain’s Cargo (Secret)"),
        ("h1", "14. Hand It to Claude"),
    ]


def test_locate_headings_handles_repeats():
    pages = ["Intro Her Arc text", "other", "Later Her Arc again"]
    found = locate_headings(pages, [("h1", "Intro"), ("h2", "Her Arc"), ("h2", "Her Arc")])
    assert [h["page"] for h in found] == [1, 1, 3]


def test_locate_headings_wrapped_line():
    pages = ["Part 2 — Long Rests &\nthe Morning Routine"]
    found = locate_headings(pages, [("h1", "Part 2 — Long Rests & the Morning Routine")])
    assert found[0]["page"] == 1


def _doc(path, extra_page=False):
    story = [ps.P("Heading One", ps.h1), ps.P("Body text here.", ps.body)]
    if extra_page:
        story += [ps.PageBreak(), ps.P("Extra", ps.body)]
    ps.build(story, path, "Doc · Level 3 · updated 28 Sep 2026")
    return path


def test_compare_identical_and_extra_page(tmp_path):
    script = tmp_path / "build_doc.py"
    script.write_text('S.append(P("Heading One", h1))\n', encoding="utf-8")
    base = tmp_path / "golden"
    capture(_doc(tmp_path / "Doc.pdf"), script, base)
    assert (base / "Doc.json").exists() and (base / "Doc" / "page-01.png").exists()
    (tmp_path / "again").mkdir()
    assert compare(_doc(tmp_path / "again" / "Doc.pdf"), script, base) == []
    problems = compare(_doc(tmp_path / "x.pdf", extra_page=True), script, base, name="Doc")
    assert any("page count" in p for p in problems)


def test_compare_reports_text_change(tmp_path):
    script = tmp_path / "build_doc.py"
    script.write_text('S.append(P("Heading One", h1))\n', encoding="utf-8")
    base = tmp_path / "golden"
    capture(_doc(tmp_path / "Doc.pdf"), script, base)
    changed = tmp_path / "changed.pdf"
    ps.build([ps.P("Heading One", ps.h1), ps.P("Different words.", ps.body)], changed, "Doc")
    problems = compare(changed, script, base, name="Doc")
    assert any("text differs on page 1" in p for p in problems)


def test_cli_golden_capture_from_committed(tmp_path, monkeypatch):
    from ddtools.cli import main

    char = tmp_path / "Some_One"
    (char / "src").mkdir(parents=True)
    (char / "pdf").mkdir()
    (char / "src" / "build_doc.py").write_text('S.append(P("Heading One", h1))\n', encoding="utf-8")
    (char / "character.yaml").write_text(
        "name: Some One\nlevel: 1\nupdated: 2026-09-28\ndocuments:\n"
        "  - {file: pdf/Doc.pdf, script: src/build_doc.py, audience: private}\n",
        encoding="utf-8",
    )
    _doc(char / "pdf" / "Doc.pdf")
    monkeypatch.chdir(tmp_path)
    assert main(["golden", "capture", str(char), "--from-committed"]) == 0
    assert (tmp_path / "tests" / "golden" / "Some_One" / "Doc.json").exists()


# The workbook's headings as recorded before the restructure (origin/master's parser
# on origin/master's workbook.py). A baseline recorded then must still match.
MASTER_WORKBOOK_HEADINGS = [
    ("h2", "The Short Version"),
    ("h2", "Progress Tracker"),
    ("h1", "1. The Basics"),
    ("h1", "2. The One-Line Pitch"),
    ("h1", "3. Backstory"),
    ("h1", "4. What You Want From Your Character"),
    ("h1", "5. Build & Levelling"),
    ("h1", "6. Skills & What You’re Good At"),
    ("h1", "7. Personality & Voice"),
    ("h1", "8. The People in Your Life"),
    ("h1", "9. You and the Party"),
    ("h1", "10. Running Gags & Side Projects"),
    ("h1", "11. In Combat"),
    ("h1", "12. Hooks, Secrets & Limits"),
    ("h1", "13. Questions for the DM"),
    ("h2", "Campaign Facts (so Claude gets them right)"),
    ("h1", "14. Hand It to Claude"),
    ("h2", "First: What Claude Needs (one time, 2 minutes)"),
    ("h2", "Then: Paste the Prompt"),
    ("h2", "One More: All Three PDFs at Once"),
    ("h2", "Useful Follow-Ups"),
]

SECTIONS_SCRIPT = """
def _cover(wb):
    out.append(P("Cover", h2))


def _a(wb):
    out.append(P("Inside A", h2))


def _b(wb):
    out.append(P("Inside B", h2))


def _end(wb):
    out.append(P("The End", h1))


SECTIONS = [
    _Section(1, "A &amp; One", 3, _a, why="w"),
    _Section(
        2,
        "B",
        5,
        _b,
        why="w",
    ),
]
"""


def test_headings_from_script_reads_section_tuples_in_build_order(tmp_path):
    script = tmp_path / "build_x.py"
    script.write_text(SECTIONS_SCRIPT, encoding="utf-8")
    assert headings_from_script(script) == [
        ("h2", "Cover"),
        ("h1", "1. A & One"),
        ("h2", "Inside A"),
        ("h1", "2. B"),
        ("h2", "Inside B"),
        ("h1", "The End"),
    ]


def _workbook_doc(char_dir):
    from ddtools.config import load_character

    ch = load_character(char_dir)
    return ch, next(d for d in ch.documents if d.script == "ddtools:workbook")


def test_workbook_headings_match_the_pre_restructure_list(ash):
    _, doc = _workbook_doc(ash)
    assert headings_from_script(doc.source(ash)) == MASTER_WORKBOOK_HEADINGS


def test_a_pre_restructure_workbook_baseline_still_matches(ash, tmp_path):
    import json

    from ddtools.textdump import page_texts
    from ddtools.workbook import build_workbook

    ch, doc = _workbook_doc(ash)
    pdf = build_workbook(ch)
    script = doc.source(ash)
    base = tmp_path / "golden"
    capture(pdf, script, base)
    # Swap in the headings a pre-restructure ddtools would have recorded.
    old = locate_headings(page_texts(pdf), MASTER_WORKBOOK_HEADINGS)
    assert all(h["page"] is not None for h in old)
    path = base / f"{pdf.stem}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["headings"] = old
    path.write_text(json.dumps(data), encoding="utf-8")
    assert compare(pdf, script, base) == []
