"""Golden-document baselines: record what a PDF looks like, then check a rebuild matches.

A baseline for ``<name>.pdf`` is ``<dest>/<name>.json`` (page count, headings and
the page each lands on, normalised page text) plus ``<dest>/<name>/page-NN.png``
(small greyscale renders compared by similarity, not exact bytes).
"""

from __future__ import annotations

import difflib
import html
import json
import re
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from ddtools.preview import render_page
from ddtools.textdump import page_texts

SCALE = 0.35
THRESHOLD = 0.98

_STAMPS = [
    re.compile(r"Level \d+ · updated \d{1,2} [A-Z][a-z]{2} \d{4}"),
    re.compile(r"updated \d{1,2} [A-Z][a-z]{2} \d{4}"),
]
_HEADING = re.compile(r'P\(\s*"((?:[^"\\]|\\.)*)"\s*,\s*(h1|h2)\s*\)')
_SECTION = re.compile(r'\bsection\(\s*(\d+)\s*,\s*"((?:[^"\\]|\\.)*)"')
_TAG = re.compile(r"<[^>]+>")


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalise(text: str) -> str:
    """Replace footer stamps with ``<STAMP>`` and collapse whitespace."""
    for pattern in _STAMPS:
        text = pattern.sub("<STAMP>", text)
    return _collapse(text)


def _plain(markup: str) -> str:
    return _collapse(html.unescape(_TAG.sub("", markup)))


def headings_from_script(script: Path) -> list[tuple[str, str]]:
    """Every h1/h2 heading in a build script, in source order.

    Recognises ``P("…", h1|h2)`` and the workbook's ``section(N, "Name", …)``
    (rendered as ``"N. Name"``). f-string headings don't match and are skipped.
    """
    source = Path(script).read_text(encoding="utf-8")
    found: list[tuple[int, str, str]] = []
    for m in _HEADING.finditer(source):
        found.append((m.start(), m.group(2), _plain(m.group(1))))
    for m in _SECTION.finditer(source):
        found.append((m.start(), "h1", f"{m.group(1)}. {_plain(m.group(2))}"))
    return [(level, text) for _, level, text in sorted(found)]


def locate_headings(pages: list[str], headings: list[tuple[str, str]]) -> list[dict]:
    """Find the (1-based) page each heading lands on, searching forward so repeats map in order."""
    flat = [_collapse(p) for p in pages]
    result = []
    page, offset = 0, 0
    for level, text in headings:
        hit = None
        for i in range(page, len(flat)):
            start = offset if i == page else 0
            pos = flat[i].find(text, start)
            if pos != -1:
                hit, page, offset = i, i, pos + len(text)
                break
        result.append({"level": level, "text": text, "page": None if hit is None else hit + 1})
    return result


def _render(pdf: Path, index: int) -> Image.Image:
    return render_page(pdf, index, SCALE).convert("L")


def capture(pdf: Path, script: Path, dest: Path, name: str | None = None) -> dict:
    """Record a baseline for ``pdf`` (headings taken from ``script``) into ``dest``."""
    name = name or Path(pdf).stem
    pages = page_texts(pdf)
    data = {
        "pages": len(pages),
        "headings": locate_headings(pages, headings_from_script(script)),
        "texts": [normalise(p) for p in pages],
    }
    dest = Path(dest)
    img_dir = dest / name
    img_dir.mkdir(parents=True, exist_ok=True)
    for old in img_dir.glob("page-*.png"):
        old.unlink()
    for i in range(len(pages)):
        _render(pdf, i).save(img_dir / f"page-{i + 1:02d}.png", optimize=True)
    (dest / f"{name}.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return data


def similarity(a: Image.Image, b: Image.Image) -> float:
    """1.0 for identical greyscale images, lower as they differ (mean absolute difference)."""
    if a.size != b.size:
        return 0.0
    return 1 - ImageStat.Stat(ImageChops.difference(a, b)).mean[0] / 255


def compare(
    pdf: Path, script: Path, baseline: Path, threshold: float = THRESHOLD, name: str | None = None
) -> list[str]:
    """Compare a PDF with its baseline. Returns human-readable problems (empty = matches)."""
    name = name or Path(pdf).stem
    base_file = Path(baseline) / f"{name}.json"
    if not base_file.exists():
        return [f"{name}: no baseline at {base_file} (run `ddtools golden update`)"]
    base = json.loads(base_file.read_text(encoding="utf-8"))
    pages = page_texts(pdf)
    problems: list[str] = []
    if len(pages) != base["pages"]:
        problems.append(f"{name}: page count {len(pages)}, baseline {base['pages']}")
    now = locate_headings(pages, headings_from_script(script))
    for was, got in zip(base["headings"], now, strict=False):
        if (was["text"], was["page"]) != (got["text"], got["page"]):
            problems.append(
                f"{name}: heading '{was['text']}' was on page {was['page']}, "
                f"now '{got['text']}' on page {got['page']}"
            )
    if len(now) != len(base["headings"]):
        problems.append(f"{name}: {len(now)} headings, baseline {len(base['headings'])}")
    for i, (was, got) in enumerate(zip(base["texts"], pages, strict=False), 1):
        got = normalise(got)
        if was != got:
            diff = difflib.unified_diff(
                was.split(". "), got.split(". "), "baseline", "rebuilt", lineterm="", n=0
            )
            problems.append(f"{name}: text differs on page {i}:\n" + "\n".join(list(diff)[:20]))
    for i in range(min(len(pages), base["pages"])):
        png = Path(baseline) / name / f"page-{i + 1:02d}.png"
        score = similarity(Image.open(png).convert("L"), _render(pdf, i))
        if score < threshold:
            problems.append(f"{name}: page {i + 1} looks different (similarity {score:.3f})")
    return problems
