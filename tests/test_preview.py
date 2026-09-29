from PIL import Image

from ddtools.preview import contact_sheet, render_page


def test_render_page(two_page_pdf):
    img = render_page(two_page_pdf, 0, scale=0.5)
    assert img.width > 100 and img.height > img.width


def test_contact_sheet_width(two_page_pdf, tmp_path):
    out = contact_sheet(two_page_pdf, tmp_path / "sheet.png", scale=0.4, cols=2)
    page = render_page(two_page_pdf, 0, scale=0.4)
    sheet = Image.open(out)
    assert sheet.width == 2 * page.width
    assert sheet.height == page.height


def test_cli_preview_writes_sheet(two_page_pdf, tmp_path, monkeypatch, capsys):
    from ddtools.cli import main

    char = tmp_path / "Some_One"
    (char / "pdf").mkdir(parents=True)
    two_page_pdf.rename(char / "pdf" / "Doc.pdf")
    monkeypatch.chdir(tmp_path)
    assert main(["preview", str(char), "--pages", "2-2"]) == 0
    out = tmp_path / "tmp" / "preview-Doc.png"
    assert out.exists()
    assert str(out) in capsys.readouterr().out
