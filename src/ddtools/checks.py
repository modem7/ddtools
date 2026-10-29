"""Checks for shareable (``audience: party``) documents: spoilers and future spells."""

from __future__ import annotations

import re
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

from ddtools.dndbeyond import latest_snapshots, load_snapshot, summarise
from ddtools.golden import Heading, headings_from_script, locate_headings
from ddtools.secrets import (
    _flatten,
    _page_of,
    clean,
    find_spoilers,
    load_character_secrets,
)
from ddtools.textdump import page_texts

if TYPE_CHECKING:
    from ddtools.config import Character, PathLike

_LEVEL_LABEL = re.compile(r"\blevels?\s*\d+\+?|\bat level\b", re.IGNORECASE)
_SENTENCE_END = re.compile(r"[.!?•\n]")


class FutureSpellHit(TypedDict):
    """A spell named as if current, but not on the sheet."""

    page: int
    spell: str
    sentence: str


def load_spell_names() -> set[str]:
    """The bundled list of 5e spell names."""
    text = resources.files("ddtools").joinpath("data/spells.txt").read_text(encoding="utf-8")
    return {clean(line) for line in text.splitlines() if line and not line.startswith("#")}


def snapshot_spell_names(data: dict) -> set[str]:
    """All spells on a D&D Beyond sheet, from every source."""
    return {clean(n) for names in summarise(data)["spells"].values() for n in names}


def _future_ranges(
    flat: str, page_starts: list[int], headings: list[Heading], future: list[str]
) -> list[tuple[int, int]]:
    """Character ranges of ``flat`` that sit under a heading listed in ``future``."""
    located = []
    for h in headings:
        page = h.get("page")
        if page is None:
            continue
        pos = flat.find(clean(h["text"]), page_starts[page - 1])
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
    headings: list[Heading],
    future_sections: list[str],
    ignore: list[str],
) -> list[FutureSpellHit]:
    """Spells named as if current that aren't on the sheet: ``{page, spell, sentence}``.

    Allowed: the sentence has a level label ("at level 4", "(level 8+)"), or the
    mention sits under a heading in ``future_sections``, or the spell is in ``ignore``.
    """
    skip = sheet | {clean(i) for i in ignore}
    candidates = sorted(known - skip, key=len, reverse=True)
    if not candidates:
        return []
    spell_re = re.compile(r"(?<![\w'-])(" + "|".join(map(re.escape, candidates)) + r")(?![\w'-])")
    flat, page_starts = _flatten(pages, "\n")
    future = _future_ranges(flat, page_starts, headings, future_sections)
    hits: list[FutureSpellHit] = []
    for m in spell_re.finditer(flat):
        if any(a <= m.start() < b for a, b in future):
            continue
        before = [e.end() for e in _SENTENCE_END.finditer(flat, 0, m.start())]
        start = before[-1] if before else 0
        after = _SENTENCE_END.search(flat, m.end())
        sentence = flat[start : after.start() if after else len(flat)].strip()
        if _LEVEL_LABEL.search(sentence):
            continue
        hits.append(
            {"page": _page_of(m.start(), page_starts), "spell": m.group(1), "sentence": sentence}
        )
    return hits


def run_checks(ch: Character, pdf_dir: PathLike | None = None) -> list[str]:
    """All problems in a character's party documents, as readable lines (empty = clean).

    ``pdf_dir`` checks PDFs built elsewhere (e.g. CI's fresh build) instead of ``<char_dir>/pdf``.

    Raises:
        SnapshotError: the latest snapshot can't be read.
        ConfigError: a document's ``ddtools:`` script doesn't exist.
    """
    problems = []
    secrets = load_character_secrets(ch)
    snaps = latest_snapshots(ch, 1)
    sheet = snapshot_spell_names(load_snapshot(snaps[-1])) if snaps else None
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
        for spell in find_future_spells(
            pages, known, sheet, headings, doc.future_sections, doc.spell_ignore
        ):
            problems.append(
                f"{doc.file} p{spell['page']}: '{spell['spell']}' isn't on the sheet and has no "
                f"level label: “{spell['sentence']}”"
            )
    return problems
