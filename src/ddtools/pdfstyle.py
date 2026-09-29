"""Shared PDF look for character documents.

Styles, colours and helpers are copied exactly from the original build
scripts: the golden tests depend on them producing identical pages. Change
them only together with a reviewed ``ddtools golden update``.
"""

from __future__ import annotations

import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    CondPageBreak,
    Flowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

__all__ = [
    "A4", "mm", "colors", "ParagraphStyle", "Paragraph", "Spacer", "Table", "TableStyle",
    "PageBreak", "KeepTogether", "CondPageBreak", "Preformatted", "Flowable",
    "SimpleDocTemplate", "pdfmetrics", "TTFont",
    "ACCENT", "EMBER", "INK", "MUTED", "RULE", "HEAD_BG", "NOTE_BG", "WARN_BG", "FIELD_BG",
    "body", "small", "smallb", "title", "sub", "h1", "h2", "bullet", "mono",
    "P", "bl", "table", "box", "code", "Field", "Ticks", "make_footer", "build",
    "FontsMissing",
]  # fmt: skip

DEFAULT_FONT_DIR = "/usr/share/fonts/truetype/dejavu/"
_FONTS = {
    "DV": "DejaVuSans.ttf",
    "DVB": "DejaVuSans-Bold.ttf",
    "DVS": "DejaVuSerif.ttf",
    "DVSB": "DejaVuSerif-Bold.ttf",
    "DVM": "DejaVuSansMono.ttf",
}


class FontsMissing(RuntimeError):
    """The DejaVu fonts the documents are designed around are not installed."""


def _register_fonts() -> None:
    font_dir = Path(os.environ.get("DDTOOLS_FONT_DIR", DEFAULT_FONT_DIR))
    missing = [f for f in _FONTS.values() if not (font_dir / f).is_file()]
    if missing:
        raise FontsMissing(
            f"DejaVu fonts not found in {font_dir} (missing {', '.join(missing)}). "
            "Install fonts-dejavu-core or set DDTOOLS_FONT_DIR."
        )
    for name, file in _FONTS.items():
        pdfmetrics.registerFont(TTFont(name, str(font_dir / file)))
    pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic="DV", boldItalic="DVB")


_register_fonts()

ACCENT = colors.HexColor("#8a2a12")
EMBER = colors.HexColor("#c4561d")
INK = colors.HexColor("#1e1b18")
MUTED = colors.HexColor("#5b544c")
RULE = colors.HexColor("#d8cfc4")
HEAD_BG = colors.HexColor("#f3e7dc")
NOTE_BG = colors.HexColor("#fbf3ea")
WARN_BG = colors.HexColor("#fdeee6")
FIELD_BG = colors.HexColor("#fffdf9")

body = ParagraphStyle("body", fontName="DV", fontSize=9.5, leading=13, textColor=INK, spaceAfter=4)
small = ParagraphStyle("small", parent=body, fontSize=8.6, leading=11.6, spaceAfter=0)
smallb = ParagraphStyle("smallb", parent=small, fontName="DVB")
title = ParagraphStyle(
    "title", fontName="DVSB", fontSize=26, leading=30, textColor=ACCENT, spaceAfter=4
)
sub = ParagraphStyle(
    "sub", fontName="DV", fontSize=10.5, leading=14, textColor=MUTED, spaceAfter=12
)
h1 = ParagraphStyle(
    "h1", fontName="DVSB", fontSize=17, leading=21, textColor=ACCENT,
    spaceBefore=14, spaceAfter=8, keepWithNext=1,
)  # fmt: skip
h2 = ParagraphStyle(
    "h2", fontName="DVSB", fontSize=12.5, leading=16, textColor=INK,
    spaceBefore=8, spaceAfter=4, keepWithNext=1,
)  # fmt: skip
bullet = ParagraphStyle("bullet", parent=body, leftIndent=12, bulletIndent=2, spaceAfter=3)
mono = ParagraphStyle("mono", fontName="DVM", fontSize=7.6, leading=9.8, textColor=INK)


def P(t, s=body):
    return Paragraph(t, s)


def bl(items):
    return [Paragraph(i, bullet, bulletText="•") for i in items]


def table(rows, widths, header=True):
    data = [
        [P(c, smallb if (header and r == 0) else small) for c in row] for r, row in enumerate(rows)
    ]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0)
    st = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        st += [
            ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, ACCENT),
        ]
    t.setStyle(TableStyle(st))
    return t


def box(paras, bg=NOTE_BG, edge=EMBER):
    t = Table([[paras]], colWidths=[170 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("LINEBEFORE", (0, 0), (0, -1), 3, edge),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return t


def code(lines):
    """A copyable monospace block (prompts, commands)."""
    t = Table([[Preformatted("\n".join(lines), mono)]], colWidths=[170 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f1ec")),
                ("BOX", (0, 0), (-1, -1), 0.6, RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


_field_counter = [0]


def _field_id(prefix):
    _field_counter[0] += 1
    return f"{prefix}_{_field_counter[0]}"


class Field(Flowable):
    """A write-in area: ruled lines for printing, plus a fillable text box for typing."""

    def __init__(self, label=None, lines=3, width=170 * mm, key=None):
        super().__init__()
        self.label, self.lines, self.w, self.key = label, lines, width, key
        self.lh = 6.2 * mm
        self.h = self.lines * self.lh + (4.2 * mm if label else 0) + 2 * mm

    def wrap(self, aw, ah):
        return self.w, self.h

    def draw(self) -> None:
        c = self.canv
        top = self.h - 2 * mm
        if self.label:
            c.setFont("DVB", 8)
            c.setFillColor(MUTED)
            c.drawString(0, self.h - 3.8 * mm, self.label)
            top -= 4.2 * mm
        boxh = self.lines * self.lh
        c.setFillColor(FIELD_BG)
        c.setStrokeColor(RULE)
        c.setLineWidth(0.6)
        c.rect(0, top - boxh, self.w, boxh, fill=1, stroke=1)
        c.setStrokeColor(colors.HexColor("#ece4da"))
        c.setLineWidth(0.4)
        for i in range(1, self.lines):
            y = top - i * self.lh
            c.line(3 * mm, y, self.w - 3 * mm, y)
        c.acroForm.textfield(
            name=self.key or _field_id("f"), tooltip=self.label or None,
            x=0, y=top - boxh, width=self.w, height=boxh,
            borderWidth=0, fillColor=None, textColor=INK, fontName="Helvetica",
            fontSize=9 if self.lines > 1 else 10,
            fieldFlags="multiline" if self.lines > 1 else "", forceBorder=False, relative=True,
        )  # fmt: skip


class Ticks(Flowable):
    """Tick boxes in columns: click on screen or tick with a pen."""

    def __init__(self, options, cols=3, width=170 * mm, key=None):
        super().__init__()
        self.opts, self.cols, self.w, self.key = options, cols, width, key
        self.rh = 6 * mm
        self.rows = (len(options) + cols - 1) // cols
        self.h = self.rows * self.rh + 1 * mm

    def wrap(self, aw, ah):
        return self.w, self.h

    def draw(self):
        c = self.canv
        cw = self.w / self.cols
        for i, o in enumerate(self.opts):
            r, col = divmod(i, self.cols)
            x, y = col * cw, self.h - (r + 1) * self.rh
            c.acroForm.checkbox(
                name=f"{self.key}.{i}" if self.key else _field_id("t"), tooltip=o,
                x=x, y=y + 0.8 * mm, size=10, borderColor=MUTED,
                fillColor=FIELD_BG, buttonStyle="check", borderWidth=0.6, forceBorder=True,
                relative=True,
            )  # fmt: skip
            c.setFont("DV", 8.4)
            c.setFillColor(INK)
            c.drawString(x + 5.5 * mm, y + 1.8 * mm, o)


def make_footer(label):
    def footer(c, d):
        c.saveState()
        c.setFont("DV", 7.5)
        c.setFillColor(MUTED)
        c.drawString(20 * mm, 12 * mm, label)
        c.drawRightString(190 * mm, 12 * mm, f"Page {d.page}")
        c.restoreState()

    return footer


def build(story, path, label, author=""):
    """Build an A4 document with the standard margins and footer."""
    doc = SimpleDocTemplate(
        str(path), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=20 * mm, title=label, author=author,
    )  # fmt: skip
    f = make_footer(label)
    doc.build(story, onFirstPage=f, onLaterPages=f)
