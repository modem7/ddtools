"""Checks for shareable (``audience: party``) documents: spoilers and future spells."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from ddtools.dndbeyond import latest_snapshots, summarise
from ddtools.golden import headings_from_script, locate_headings
from ddtools.textdump import page_texts

_QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "­": None})
_LEVEL_LABEL = re.compile(r"\blevels?\s*\d+\+?|\bat level\b", re.IGNORECASE)
_SENTENCE_END = re.compile(r"[.!?•\n]")


@dataclass(frozen=True)
class Secret:
    text: str
    exact: bool


def clean(text: str) -> str:
    """Straighten quotes, drop soft hyphens and collapse whitespace."""
    return re.sub(r"\s+", " ", text.translate(_QUOTES)).strip()


def load_secrets(path: Path) -> list[Secret]:
    """One entry per line; ``#`` comments and blanks ignored; ``"quoted"`` = exact match."""
    secrets = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        exact = len(line) > 1 and line[0] == line[-1] == '"'
        secrets.append(Secret(clean(line[1:-1] if exact else line), exact))
    return secrets


def _pattern(secret: Secret) -> re.Pattern:
    words = r"\s+".join(re.escape(w) for w in secret.text.split())
    return re.compile(rf"(?<!\w){words}(?!\w)", 0 if secret.exact else re.IGNORECASE)


def _flatten(pages: list[str]) -> tuple[str, list[int]]:
    """All pages cleaned and joined with a space, plus each page's start offset."""
    starts, flat = [], ""
    for page in pages:
        starts.append(len(flat))
        flat += clean(page) + " "
    return flat, starts


def _page_of(offset: int, starts: list[int]) -> int:
    return max(i for i, start in enumerate(starts) if start <= offset) + 1


def find_spoilers(pages: list[str], secrets: list[Secret]) -> list[dict]:
    """Every occurrence of a secret: ``{page, term, context}`` (context is ±40 characters).

    Pages are scanned as one text, so a secret split across a page break is still found
    (reported on the page where it starts).
    """
    flat, starts = _flatten(pages)
    hits = []
    for secret in secrets:
        for m in _pattern(secret).finditer(flat):
            ctx = flat[max(0, m.start() - 40) : m.end() + 40].strip()
            hits.append({"page": _page_of(m.start(), starts), "term": secret.text, "context": ctx})
    return sorted(hits, key=lambda h: h["page"])


def load_spell_names() -> set[str]:
    """The bundled list of 5e spell names."""
    text = resources.files("ddtools").joinpath("data/spells.txt").read_text(encoding="utf-8")
    return {clean(line) for line in text.splitlines() if line and not line.startswith("#")}


def snapshot_spell_names(data: dict) -> set[str]:
    """All spells on a D&D Beyond sheet, from every source."""
    return {clean(n) for names in summarise(data)["spells"].values() for n in names}


def _future_ranges(flat: str, page_starts: list[int], headings: list[dict], future: list[str]):
    """Character ranges of ``flat`` that sit under a heading listed in ``future``."""
    located = []
    for h in headings:
        if h.get("page") is None:
            continue
        pos = flat.find(clean(h["text"]), page_starts[h["page"] - 1])
        if pos != -1:
            located.append((pos, clean(h["text"])))
    located.sort()
    wanted = {clean(f) for f in future}
    ranges = []
    for i, (pos, text) in enumerate(located):
        if text in wanted:
            end = located[i + 1][0] if i + 1 < len(located) else len(flat)
            ranges.append((pos, end))
    return ranges


def find_future_spells(
    pages: list[str],
    known: set[str],
    sheet: set[str],
    headings: list[dict],
    future_sections: list[str],
    ignore: list[str],
) -> list[dict]:
    """Spells named as if current that aren't on the sheet: ``{page, spell, sentence}``.

    Allowed: the sentence has a level label ("at level 4", "(level 8+)"), or the
    mention sits under a heading in ``future_sections``, or the spell is in ``ignore``.
    """
    skip = sheet | {clean(i) for i in ignore}
    candidates = sorted(known - skip, key=len, reverse=True)
    if not candidates:
        return []
    spell_re = re.compile(r"(?<![\w'-])(" + "|".join(map(re.escape, candidates)) + r")(?![\w'-])")
    flat_pages = [clean(p) for p in pages]
    page_starts, flat = [], ""
    for p in flat_pages:
        page_starts.append(len(flat))
        flat += p + "\n"
    future = _future_ranges(flat, page_starts, headings, future_sections)
    hits = []
    for m in spell_re.finditer(flat):
        if any(a <= m.start() < b for a, b in future):
            continue
        before = [e.end() for e in _SENTENCE_END.finditer(flat, 0, m.start())]
        start = before[-1] if before else 0
        after = _SENTENCE_END.search(flat, m.end())
        sentence = flat[start : after.start() if after else len(flat)].strip()
        if _LEVEL_LABEL.search(sentence):
            continue
        page = max(i for i, s in enumerate(page_starts) if s <= m.start()) + 1
        hits.append({"page": page, "spell": m.group(1), "sentence": sentence})
    return hits


def run_checks(ch, pdf_dir: Path | None = None) -> list[str]:
    """All problems in a character's party documents, as readable lines (empty = clean).

    ``pdf_dir`` checks PDFs built elsewhere (e.g. CI's fresh build) instead of ``<dir>/pdf``.
    """
    problems = []
    secrets = load_secrets(ch.secrets_path) if ch.secrets_path.exists() else []
    snaps = latest_snapshots(ch, 1)
    sheet = (
        snapshot_spell_names(json.loads(snaps[-1].read_text(encoding="utf-8"))) if snaps else None
    )
    known = load_spell_names()
    for doc in ch.documents:
        if doc.audience != "party":
            continue
        pdf = Path(pdf_dir) / Path(doc.file).name if pdf_dir else ch.dir / doc.file
        if not pdf.exists():
            problems.append(f"{doc.file}: not built yet (run `ddtools build`)")
            continue
        pages = page_texts(pdf)
        for hit in find_spoilers(pages, secrets):
            problems.append(
                f"{doc.file} p{hit['page']}: spoiler '{hit['term']}' in “…{hit['context']}…”"
            )
        if sheet is None:
            problems.append(f"{doc.file}: spell check skipped, no snapshot (run `ddtools fetch`)")
            continue
        headings = locate_headings(pages, headings_from_script(doc.source(ch.dir)))
        for hit in find_future_spells(
            pages, known, sheet, headings, doc.future_sections, doc.spell_ignore
        ):
            problems.append(
                f"{doc.file} p{hit['page']}: '{hit['spell']}' isn't on the sheet and has no "
                f"level label: “{hit['sentence']}”"
            )
    return problems
