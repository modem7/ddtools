"""The secrets file: what the party must not read, and finding it in text.

A character's ``secrets.txt`` lists one secret per line. This module loads it and finds
those secrets in page text. It imports no PDF code, so ``sheettext`` and ``lifecycle``
can use it without pulling in rendering.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from ddtools.config import Character, PathLike

_QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "­": None})


@dataclass(frozen=True)
class Secret:
    text: str
    exact: bool


class SpoilerHit(TypedDict):
    """A secret found in a document."""

    page: int
    term: str
    context: str  # the text around it, ±40 characters


def clean(text: str) -> str:
    """Straighten quotes, drop soft hyphens and collapse whitespace."""
    return re.sub(r"\s+", " ", text.translate(_QUOTES)).strip()


def load_secrets(path: PathLike) -> list[Secret]:
    """One entry per line; ``#`` comments and blanks ignored; ``"quoted"`` = exact match."""
    secrets = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        exact = len(line) > 1 and line[0] == line[-1] == '"'
        text = clean(line[1:-1] if exact else line)
        if text:  # '""' alone would match everywhere
            secrets.append(Secret(text, exact))
    return secrets


def _pattern(secret: Secret) -> re.Pattern:
    words = r"\s+".join(re.escape(w) for w in secret.text.split())
    return re.compile(rf"(?<!\w){words}(?!\w)", 0 if secret.exact else re.IGNORECASE)


def flatten(pages: list[str], sep: str = " ") -> tuple[str, list[int]]:
    """All pages cleaned and joined with ``sep``, plus each page's start offset."""
    starts: list[int] = []
    flat = ""
    for page in pages:
        starts.append(len(flat))
        flat += clean(page) + sep
    return flat, starts


def page_of(offset: int, starts: list[int]) -> int:
    return max(i for i, start in enumerate(starts) if start <= offset) + 1


def find_spoilers(pages: list[str], secrets: list[Secret]) -> list[SpoilerHit]:
    """Every occurrence of a secret: ``{page, term, context}`` (context is ±40 characters).

    Pages are scanned as one text, so a secret split across a page break is still found
    (reported on the page where it starts).
    """
    flat, starts = flatten(pages)
    hits: list[SpoilerHit] = []
    for secret in secrets:
        for m in _pattern(secret).finditer(flat):
            ctx = flat[max(0, m.start() - 40) : m.end() + 40].strip()
            hits.append({"page": page_of(m.start(), starts), "term": secret.text, "context": ctx})
    return sorted(hits, key=lambda h: h["page"])


def load_character_secrets(ch: Character) -> list[Secret]:
    """The character's secrets; a missing secrets file means there are none."""
    return load_secrets(ch.secrets_path) if ch.secrets_path.is_file() else []
