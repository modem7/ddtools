"""Read a filled party workbook back into the repo (``ddtools import-workbook``).

Every answer goes, verbatim and grouped by section, into
``notes/sources/workbook-answers.md``. A few answers also fill blanks in
``character.yaml`` (the D&D Beyond id and the class summary). Nothing already set is ever
overwritten: differences are listed instead. The documents themselves are written by
hand (by Claude, from the blueprints), never generated from here.
"""

from __future__ import annotations

import html
import re
from datetime import date
from pathlib import Path

from ddtools.config import load_character, set_top_level
from ddtools.dndbeyond import parse_id

ANSWERS = "notes/sources/workbook-answers.md"
_NAME = re.compile(r"^v1\.s(\d+)\.")


class NotAWorkbook(Exception):
    pass


def read_fields(pdf: Path) -> list[dict]:
    """The workbook's fields in order: ``{name, section, label, kind, value}``."""
    import pypdf

    fields = pypdf.PdfReader(str(pdf)).get_fields() or {}
    out = []
    for name, f in fields.items():
        m = _NAME.match(name)
        if not m:
            continue
        kind = "tick" if f.get("/FT") == "/Btn" else "text"
        raw = f.get("/V")
        value = str(raw) not in ("None", "/Off", "") if kind == "tick" else str(raw or "").strip()
        out.append({"name": name, "section": int(m.group(1)), "label": str(f.get("/TU") or name),
                    "kind": kind, "value": value})  # fmt: skip
    if not out:
        raise NotAWorkbook(f"{pdf}: not a ddtools workbook (it has no v1 workbook fields)")
    return out


def _titles(ch) -> dict[int, str]:
    from ddtools import workbook as W

    W.story(ch)
    return {n: html.unescape(t) for n, t in W.TITLES.items()}


def answers_markdown(ch, fields: list[dict], source: str) -> str:
    titles = _titles(ch)
    out = [f"# Workbook answers: {ch.name}", "",
           f"Imported from `{source}` on {date.today().isoformat()} by `ddtools import-workbook`.",
           "Verbatim: nothing here has been edited."]  # fmt: skip
    section = None
    for f in fields:
        if f["section"] != section:
            section = f["section"]
            title = titles.get(section, "")
            out += ["", f"## {section}. {title}" if section else f"## {title or 'Start'}"]
        if f["kind"] == "tick":
            if f["value"]:
                out.append(f"- [x] {f['label']}")
            continue
        out += ["", f"**{f['label']}**", ""]
        out.append(f["value"] if f["value"] else "*(blank)*")
    return "\n".join(out) + "\n"


def _answer(fields, prefix: str) -> str:
    return next((f["value"] for f in fields if f["name"].startswith(prefix)), "")


def import_workbook(pdf: Path, dir: Path) -> dict:
    """Import ``pdf`` into the character at ``dir``. Returns what was written, filled,
    left alone (differences) and what's still blank."""
    ch = load_character(dir)
    fields = read_fields(pdf)
    target = ch.dir / ANSWERS
    if target.exists():
        target = target.with_name(f"workbook-answers-{date.today().isoformat()}.md")
        n = 2
        while target.exists():
            target = target.with_name(f"workbook-answers-{date.today().isoformat()}-{n}.md")
            n += 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(answers_markdown(ch, fields, Path(pdf).name), encoding="utf-8")

    filled, differences = [], []
    name = _answer(fields, "v1.s1.character-name")
    if name and name != ch.name:
        differences.append(f"name: the workbook says '{name}', character.yaml says '{ch.name}'")
    link = _answer(fields, "v1.s1.d-d-beyond-link")
    if link:
        try:
            ddb = parse_id(link)
        except ValueError:
            differences.append(f"D&D Beyond link: can't read an id from '{link}'")
        else:
            if ch.dndbeyond_id is None:
                set_top_level(ch.dir, "dndbeyond_id", ddb)
                filled.append(f"dndbeyond_id: {ddb}")
            elif ch.dndbeyond_id != ddb:
                differences.append(f"dndbeyond_id: the workbook says {ddb}, "
                                   f"character.yaml says {ch.dndbeyond_id}")  # fmt: skip
    summary = _answer(fields, "v1.s1.race-class-subclass-level")
    if summary:
        if not ch.class_summary:
            set_top_level(ch.dir, "class_summary", summary)
            filled.append(f"class_summary: {summary}")
        elif ch.class_summary != summary:
            differences.append(f"class_summary: the workbook says '{summary}', "
                               f"character.yaml says '{ch.class_summary}'")  # fmt: skip
    blank = [f["label"] for f in fields if f["kind"] == "text" and not f["value"]]
    return {"answers": target, "filled": filled, "differences": differences, "blank": blank}
