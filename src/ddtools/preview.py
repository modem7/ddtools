"""Render PDF pages to images for checking layouts by eye."""

from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image


def render_page(pdf: Path, index: int, scale: float = 0.6) -> Image.Image:
    """Render one page (0-based) to an RGB image."""
    doc = pdfium.PdfDocument(str(pdf))
    try:
        return doc[index].render(scale=scale).to_pil().convert("RGB")
    finally:
        doc.close()


def page_count(pdf: Path) -> int:
    doc = pdfium.PdfDocument(str(pdf))
    try:
        return len(doc)
    finally:
        doc.close()


def contact_sheet(
    pdf: Path, out: Path, pages: range | None = None, scale: float = 0.6, cols: int = 4
) -> Path:
    """Lay the chosen pages out in a grid (``cols`` wide) and save it as a PNG."""
    indices = list(pages if pages is not None else range(page_count(pdf)))
    images = [render_page(pdf, i, scale) for i in indices]
    w = max(im.width for im in images)
    h = max(im.height for im in images)
    cols = min(cols, len(images))
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (w * cols, h * rows), "white")
    for n, im in enumerate(images):
        sheet.paste(im, ((n % cols) * w, (n // cols) * h))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out
