from ddtools.textdump import page_texts, write_text_copy


def test_page_texts_per_page(two_page_pdf):
    pages = page_texts(two_page_pdf)
    assert len(pages) == 2
    assert "Second Heading" in pages[1]
    assert "Second Heading" not in pages[0]


def test_write_text_copy(two_page_pdf):
    txt = write_text_copy(two_page_pdf)
    assert txt == two_page_pdf.with_suffix(".txt")
    content = txt.read_text(encoding="utf-8")
    assert "=== Page 2 ===" in content
    assert "More text on page two." in content
