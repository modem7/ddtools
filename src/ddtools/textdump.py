"""Extract the text of a PDF, page by page."""

from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium


def page_texts(pdf: Path) -> list[str]:
    """Return the text of every page, in order, with line endings normalised to ``\\n``."""
    doc = pdfium.PdfDocument(str(pdf))
    try:
        return [
            doc[i].get_textpage().get_text_range().replace("\r\n", "\n").replace("\r", "\n")
            for i in range(len(doc))
        ]
    finally:
        doc.close()


def write_text_copy(pdf: Path) -> Path:
    """Write ``X.txt`` next to ``X.pdf`` with a separator line before each page."""
    pdf = Path(pdf)
    parts = [f"=== Page {n} ===\n\n{text.strip()}\n" for n, text in enumerate(page_texts(pdf), 1)]
    out = pdf.with_suffix(".txt")
    out.write_text("\n".join(parts), encoding="utf-8")
    return out
