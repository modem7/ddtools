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
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

from PIL import Image, ImageChops, ImageStat

from ddtools.preview import render_page
from ddtools.textdump import page_texts

if TYPE_CHECKING:
    from ddtools.config import Character

SCALE = 0.35
THRESHOLD = 0.98

_STAMPS = [
    re.compile(r"Level \d+ · updated \d{1,2} [A-Z][a-z]{2} \d{4}"),
    re.compile(r"updated \d{1,2} [A-Z][a-z]{2} \d{4}"),
]
_HEADING = re.compile(r'P\(\s*"((?:[^"\\]|\\.)*)"\s*,\s*(h1|h2)\s*\)')
_SECTION = re.compile(r'\bsection\(\s*(\d+)\s*,\s*"((?:[^"\\]|\\.)*)"')
# ``_Section(N, "Name", mins, builder, …)``: the workbook's table of sections.
_SECTION_TUPLE = re.compile(r'\b_Section\(\s*(\d+)\s*,\s*"((?:[^"\\]|\\.)*)"\s*,\s*\d+\s*,\s*(\w+)')
_TAG = re.compile(r"<[^>]+>")
_BASELINE_KEYS = ("pages", "headings", "texts")


class Heading(TypedDict):
    """A heading and the (1-based) page it lands on; None if it wasn't found."""

    level: str
    text: str
    page: int | None


class Baseline(TypedDict):
    """A golden baseline's JSON."""

    pages: int
    headings: list[Heading]
    texts: list[str]


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

    Recognises ``P("…", h1|h2)``, the old workbook's ``section(N, "Name", …)`` and
    the new one's ``_Section(N, "Name", mins, builder, …)``, each rendered as
    ``"N. Name"``. A ``_Section`` heading goes where ``def builder(`` is, since the
    section table comes after the builders. f-string headings are skipped.
    """
    source = Path(script).read_text(encoding="utf-8")
    found: list[tuple[int, str, str]] = []
    for m in _HEADING.finditer(source):
        found.append((m.start(), m.group(2), _plain(m.group(1))))
    for m in _SECTION.finditer(source):
        found.append((m.start(), "h1", f"{m.group(1)}. {_plain(m.group(2))}"))
    for m in _SECTION_TUPLE.finditer(source):
        builder = re.search(rf"^def {re.escape(m.group(3))}\(", source, re.MULTILINE)
        at = builder.start() if builder else m.start()
        found.append((at, "h1", f"{m.group(1)}. {_plain(m.group(2))}"))
    return [(level, text) for _, level, text in sorted(found)]


def locate_headings(pages: list[str], headings: list[tuple[str, str]]) -> list[Heading]:
    """Find the (1-based) page each heading lands on, searching forward so repeats map in order."""
    flat = [_collapse(p) for p in pages]
    result: list[Heading] = []
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


def capture(pdf: Path, script: Path, dest: Path, name: str | None = None) -> Baseline:
    """Record a baseline for ``pdf`` (headings taken from ``script``) into ``dest``."""
    name = name or Path(pdf).stem
    pages = page_texts(pdf)
    data: Baseline = {
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
    """Compare a PDF with its baseline. Returns human-readable problems (empty = matches).

    A missing, unreadable or incomplete baseline (its JSON or a page image) is a problem
    in the list, not an exception.
    """
    name = name or Path(pdf).stem
    base_file = Path(baseline) / f"{name}.json"
    if not base_file.exists():
        return [f"{name}: no baseline at {base_file} (run `ddtools golden update`)"]
    redo = "(run `ddtools golden update`)"
    try:
        base = json.loads(base_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as err:
        return [f"{name}: can't read the baseline {base_file} ({err}) {redo}"]
    missing = [k for k in _BASELINE_KEYS if not isinstance(base, dict) or k not in base]
    if missing:
        return [f"{name}: baseline {base_file} has no {', '.join(missing)} {redo}"]
    if not all(isinstance(h, dict) and {"text", "page"} <= h.keys() for h in base["headings"]):
        return [f"{name}: baseline {base_file} has a heading with no text or page {redo}"]
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
    for i, (was_text, page) in enumerate(zip(base["texts"], pages, strict=False), 1):
        got_text = normalise(page)
        if was_text != got_text:
            diff = difflib.unified_diff(
                was_text.split(". "), got_text.split(". "), "baseline", "rebuilt", lineterm="", n=0
            )
            problems.append(f"{name}: text differs on page {i}:\n" + "\n".join(list(diff)[:20]))
    for i in range(min(len(pages), base["pages"])):
        png = Path(baseline) / name / f"page-{i + 1:02d}.png"
        try:
            with Image.open(png) as img:
                was = img.convert("L")
        except OSError as err:
            problems.append(f"{name}: can't read the baseline image {png} ({err}) {redo}")
            continue
        score = similarity(was, _render(pdf, i))
        if score < threshold:
            problems.append(f"{name}: page {i + 1} looks different (similarity {score:.3f})")
    return problems


# ---- per character (what `ddtools golden` runs) --------------------------


def record_character(ch: Character, dest: Path, rebuild: bool) -> int:
    """Capture a baseline for every document, from a fresh build or the committed PDFs.

    Prints one line per document (and a warning per heading not found). Returns 1 if
    the build fails, else 0.
    """
    from ddtools.build import BuildError, build_character

    with tempfile.TemporaryDirectory() as tmp:
        pdf_dir = ch.dir / "pdf"
        if rebuild:
            pdf_dir = Path(tmp)
            try:
                build_character(ch.dir, pdf_dir)
            except BuildError as err:
                print(f"Build failed in {err.script}:\n{err.stderr}")
                return 1
        for doc in ch.documents:
            stem = Path(doc.file).stem
            data = capture(pdf_dir / f"{stem}.pdf", doc.source(ch.dir), dest, name=stem)
            print(f"{stem}: {data['pages']} pages, {len(data['headings'])} headings")
            for h in data["headings"]:
                if h["page"] is None:
                    print(f"  warning: heading not found in PDF text: {h['text']}")
    return 0


def check_character(ch: Character, dest: Path) -> int:
    """Rebuild into a temporary folder and compare every document with its baseline.

    Prints one line per document. Returns 1 if the build fails or anything differs.
    No baseline folder yet is not a failure.
    """
    from ddtools.build import BuildError, build_character

    if not dest.is_dir():
        print(
            f"{ch.name}: no golden baseline yet. "
            f"Record one with `ddtools golden update {ch.dir.name}`."
        )
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        try:
            build_character(ch.dir, Path(tmp))
        except BuildError as err:
            print(f"Build failed in {err.script}:\n{err.stderr}")
            return 1
        failed = False
        for doc in ch.documents:
            stem = Path(doc.file).stem
            problems = compare(Path(tmp) / f"{stem}.pdf", doc.source(ch.dir), dest)
            print(
                f"{stem}: " + ("matches" if not problems else "\n  ".join(["differs", *problems]))
            )
            failed = failed or bool(problems)
    return 1 if failed else 0
