"""The workbook's form field names, shared by the builder and ``import-workbook``.

A field is named ``v1.s<section>.<label slug>``. Tick boxes add ``.<n>`` for each option.
No reportlab here, so reading a workbook back doesn't need it.
"""

from __future__ import annotations

import re

VERSION = "v1"

# Section number -> title, as plain text. 0 is the cover. workbook.SECTIONS holds the same
# titles as markup; a test keeps the two in step.
SECTION_TITLES: dict[int, str] = {
    0: "Start",
    1: "The Basics",
    2: "The One-Line Pitch",
    3: "Backstory",
    4: "What You Want From Your Character",
    5: "Build & Levelling",
    6: "Skills & What You’re Good At",
    7: "Personality & Voice",
    8: "The People in Your Life",
    9: "You and the Party",
    10: "Running Gags & Side Projects",
    11: "In Combat",
    12: "Hooks, Secrets & Limits",
    13: "Questions for the DM",
}
_NAME = re.compile(rf"^{VERSION}\.s(\d+)\.")


def field_key(section: int, label: str) -> str:
    """The stable name of a write-in field: its section and its label, as a slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:48].rstrip("-")
    return f"{VERSION}.s{section}.{slug}"


def section_of(name: str) -> int | None:
    """The section a field name belongs to, or None if it isn't a workbook field."""
    m = _NAME.match(name)
    return int(m.group(1)) if m else None
