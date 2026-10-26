import importlib

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


def test_missing_fonts(monkeypatch, tmp_path):
    import ddtools.pdfstyle as ps

    monkeypatch.setenv("DDTOOLS_FONT_DIR", str(tmp_path))
    # reload() creates a fresh FontsMissing class, so match on its base and name
    with pytest.raises(RuntimeError) as exc:
        importlib.reload(ps)
    assert type(exc.value).__name__ == "FontsMissing"
    assert "DDTOOLS_FONT_DIR" in str(exc.value)
    monkeypatch.delenv("DDTOOLS_FONT_DIR")
    importlib.reload(ps)


def test_bundled_fonts(monkeypatch):
    import ddtools.pdfstyle as ps

    monkeypatch.delenv("DDTOOLS_FONT_DIR", raising=False)
    importlib.reload(ps)
    for file in ps._FONTS.values():
        assert (ps._BUNDLED_FONT_DIR / file).is_file()
    for name, file in ps._FONTS.items():
        # the font registry is global, so check the file came from the bundled folder
        assert ps.pdfmetrics.getFont(name).face.filename == str(ps._BUNDLED_FONT_DIR / file)
