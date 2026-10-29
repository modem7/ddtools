import pypdfium2 as pdfium
import pytest


def test_build_small_pdf(tmp_path):
    from ddtools import pdfstyle as ps

    out = tmp_path / "small.pdf"
    story = [
        ps.P("Hello", ps.h1),
        ps.table([["a", "b"], ["1", "2"]], [80, 90]),
        ps.box([ps.P("x", ps.small)]),
        ps.Field("Name", 1),
        ps.Ticks(["One", "Two"]),
        ps.code(["line one", "line two"]),
    ]
    ps.build(story, out, "Test — Doc")
    assert out.exists()
    assert len(pdfium.PdfDocument(out)) == 1


def test_todo_is_a_guidance_box():
    from ddtools import pdfstyle as ps

    assert isinstance(ps.todo("Say who you are."), ps.Table)
    assert "todo" in ps.__all__


def test_missing_fonts(monkeypatch, tmp_path):
    import ddtools.pdfstyle as ps

    monkeypatch.setenv("DDTOOLS_FONT_DIR", str(tmp_path))
    monkeypatch.setattr(ps, "_fonts_ready", False)
    with pytest.raises(ps.FontsMissing) as exc:
        ps.ensure_fonts()
    assert "DDTOOLS_FONT_DIR" in str(exc.value)
    assert not ps._fonts_ready


def test_importing_pdfstyle_needs_the_fonts(tmp_path):
    import os
    import subprocess
    import sys

    env = {**os.environ, "DDTOOLS_FONT_DIR": str(tmp_path)}
    run = subprocess.run(
        [sys.executable, "-c", "import ddtools.pdfstyle"], env=env, capture_output=True, text=True
    )
    assert run.returncode != 0 and "FontsMissing" in run.stderr


def test_bundled_fonts(monkeypatch):
    import ddtools.pdfstyle as ps

    monkeypatch.delenv("DDTOOLS_FONT_DIR", raising=False)
    monkeypatch.setattr(ps, "_fonts_ready", False)
    ps.ensure_fonts()
    assert ps._fonts_ready
    for file in ps._FONTS.values():
        assert (ps._BUNDLED_FONT_DIR / file).is_file()


def test_two_builds_of_one_story_name_their_fields_alike(tmp_path):
    import pypdf

    from ddtools import pdfstyle as ps

    def names(out):
        story = [ps.Field("Name", 1), ps.Ticks(["One", "Two"])]
        ps.build(story, out, "Test")
        return list(pypdf.PdfReader(out).get_fields())

    assert names(tmp_path / "a.pdf") == names(tmp_path / "b.pdf")
