"""Paste-ready text for a character's D&D Beyond description and notes fields.

The source is ``<dir>/dndbeyond.yaml``. Allies are generated (one line per party member
still in the party, in party order), and any ``{{name}}`` is filled by a plugin that
provides it. The result is compared with the latest snapshot and checked against
``secrets.txt``: a D&D Beyond sheet can be read by the party.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from ddtools.checks import find_spoilers, load_secrets

SOURCE_FILE = "dndbeyond.yaml"
OUTPUT_FILE = "notes/dndbeyond-text.md"
DETAIL_LIMIT = 50  # D&D Beyond cuts hair, eyes, skin and the like off at 50 characters

# (section, D&D Beyond key, label), in the order D&D Beyond shows them.
FIELDS: list[tuple[str, str, str]] = [
    ("details", "faith", "Faith"),
    ("details", "gender", "Gender"),
    ("details", "age", "Age"),
    ("details", "height", "Height"),
    ("details", "weight", "Weight"),
    ("details", "hair", "Hair"),
    ("details", "eyes", "Eyes"),
    ("details", "skin", "Skin"),
    ("traits", "personalityTraits", "Personality Traits"),
    ("traits", "ideals", "Ideals"),
    ("traits", "bonds", "Bonds"),
    ("traits", "flaws", "Flaws"),
    ("traits", "appearance", "Appearance"),
    ("notes", "organizations", "Organizations"),
    ("notes", "allies", "Allies"),
    ("notes", "enemies", "Enemies"),
    ("notes", "backstory", "Backstory"),
    ("notes", "otherNotes", "Other Notes"),
    ("notes", "personalPossessions", "Personal Possessions"),
]
SECTION_TITLES = {"details": "Character Details", "traits": "Traits", "notes": "Notes"}


class SheetTextError(Exception):
    pass


def load_source(dir: Path | str) -> dict:
    path = Path(dir) / SOURCE_FILE
    if not path.is_file():
        raise SheetTextError(f"{path}: not found (see tools/README.md, “D&D Beyond text”)")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def party_names(ch) -> list[str]:
    """Party members still in the party, in order."""
    party = ch.campaign.get("party") or []
    return [m["name"] for m in party if m.get("status", "active") != "gone"]


def allies_text(src: dict, names: list[str]) -> tuple[str, list[str]]:
    """One Allies line per party member, and the members who have no line yet."""
    lines = src.get("allies") or {}
    text = "\n".join(lines[n].strip() for n in names if n in lines)
    return text, [n for n in names if n not in lines]


def _norm(value) -> str:
    text = "" if value is None else str(value)
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("–", "-"), ("—", "-")):
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip()


def status(proposed, live) -> str:
    if proposed is None:
        return "leave as is"
    if not _norm(live):
        return "missing"
    return "up to date" if _norm(proposed) == _norm(live) else "needs updating"


def blanks(text: str | None) -> list[str]:
    return re.findall(r"\[[^\]\n]+\]", text or "")


def live_fields(data: dict) -> dict[str, object]:
    body = data.get("data", data)
    out = {}
    for section, key, _ in FIELDS:
        where = body if section == "details" else body.get(section) or {}
        out[key] = where.get(key)
    return out


def _latest_snapshot(ch) -> tuple[str | None, dict]:
    from ddtools import dndbeyond as ddb

    snaps = ddb.latest_snapshots(ch, 1)
    if not snaps:
        return None, {}
    return snaps[-1].name, json.loads(snaps[-1].read_text(encoding="utf-8"))


def _terms(text: str, secrets) -> list[str]:
    return sorted({h["term"] for h in find_spoilers([text], secrets)}) if text else []


# {{name}}: a generated block, filled by a plugin (ddtools itself has none).
BLOCK = re.compile(r"\{\{(\w+)\}\}")


def _block_filler(ch, names: list[str]):
    """A function that fills every {{name}} in a text: (filled text, what went wrong)."""
    from ddtools import plugins

    plugins.load()
    providers = plugins.blocks()
    made: dict[str, str] = {}

    def fill(text: str) -> tuple[str, list[str]]:
        problems = []

        def one(m):
            name = m.group(1)
            if name not in providers:
                problems.append(f"nothing fills {{{{{name}}}}}")
                return m.group(0)
            if name not in made:
                try:
                    made[name] = providers[name](ch, names)
                except Exception as err:  # a plugin's failure is reported, never fatal
                    problems.append(f"{{{{{name}}}}} failed: {err}")
                    return m.group(0)
            return made[name]

        return BLOCK.sub(one, text).strip(), problems

    return fill


def report(ch) -> dict:
    """Every field: proposed text, live text, status, blanks and secrets; plus problems."""
    src = load_source(ch.dir)
    names = party_names(ch)
    allies, missing = allies_text(src, names)
    fill = _block_filler(ch, names)
    secrets = load_secrets(ch.secrets_path) if ch.secrets_path.is_file() else []
    snapshot, data = _latest_snapshot(ch)
    live = live_fields(data) if data else {}
    fields, problems = [], []
    for section, key, label in FIELDS:
        given = src.get(section) or {}
        if key == "allies":
            proposed = allies or None
        elif key in given:
            proposed = given[key]
            proposed = None if proposed is None else str(proposed).strip()
        else:
            proposed = None
        if proposed and BLOCK.search(proposed):
            proposed, failed = fill(proposed)
            problems += [f"{key}: {why}" for why in failed]
        if key == "allies" or key in given:
            state = status(proposed, live.get(key)) if data else "no snapshot"
        else:
            state = "not in the source"
        if section == "details" and proposed and len(proposed) > DETAIL_LIMIT:
            problems.append(f"{key}: {len(proposed)} characters, D&D Beyond keeps {DETAIL_LIMIT}")
        for term in _terms(proposed or "", secrets):
            problems.append(f'{key}: says "{term}" (secrets.txt), and the party can read the sheet')
        fields.append({
            "section": section, "key": key, "label": label, "proposed": proposed,
            "live": live.get(key), "status": state, "blanks": blanks(proposed),
            "live_secrets": _terms(_norm(live.get(key)), secrets),
        })  # fmt: skip
    return {"fields": fields, "problems": problems, "missing_allies": missing,
            "snapshot": snapshot}  # fmt: skip


def render(ch, rep: dict) -> str:
    """The paste-ready file: what to change first, then every field's text."""
    out = [
        f"# {ch.name}: D&D Beyond text",
        "",
        f"Made by `ddtools sheet-text` from `{SOURCE_FILE}`, compared with the sheet snapshot "
        f"`{rep['snapshot'] or 'none'}`. Don't edit this file: edit `{SOURCE_FILE}` and run it "
        "again.",
        "",
        "## TL;DR",
        "",
    ]
    todo = [f for f in rep["fields"] if f["status"] in ("needs updating", "missing")]
    if todo:
        out.append("Paste these into D&D Beyond: " + ", ".join(f"**{f['label']}**" for f in todo)
                   + ". Everything else is up to date or left as it is.")  # fmt: skip
    else:
        out.append("Nothing to paste: the sheet matches.")
    leaks = [f for f in rep["fields"] if f["live_secrets"]]
    if leaks:
        out += ["", "**The live sheet gives secrets away** (the party can read it):", "",
                "| Field | Words from secrets.txt |", "|---|---|"]  # fmt: skip
        out += [f"| {f['label']} | {', '.join(f['live_secrets'])} |" for f in leaks]
    found = [(f["label"], b) for f in rep["fields"] for b in f["blanks"]]
    if found or rep["missing_allies"]:
        out += ["", "## Blanks", ""]
        out += [f"- {label}: {b}" for label, b in found]
        out += [f"- Allies: no line for **{n}** yet (add one under `allies:`)"
                for n in rep["missing_allies"]]  # fmt: skip
    section = None
    for f in rep["fields"]:
        if f["section"] != section:
            section = f["section"]
            out += ["", f"## {SECTION_TITLES[section]}"]
        if f["section"] == "details":
            if f == next(x for x in rep["fields"] if x["section"] == "details"):
                out += ["", "| Field | Paste | Status |", "|---|---|---|"]
            value = "(leave as is)" if f["proposed"] is None else f["proposed"]
            out.append(f"| **{f['label']}** | {value} | {f['status']} |")
            continue
        out += ["", f"### {f['label']}", "", f"Status: {f['status']}."]
        if f["proposed"] is not None:
            out += ["", "```text", f["proposed"], "```"]
    return "\n".join(out) + "\n"


def write(ch, rep: dict) -> Path:
    path = ch.dir / OUTPUT_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(ch, rep), encoding="utf-8")
    return path
