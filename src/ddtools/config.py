"""Read and write a character's ``character.yaml``.

Build scripts call ``load_character()`` with no argument: ``ddtools build`` sets
``DDTOOLS_CHARACTER_DIR`` (and ``DDTOOLS_OUT``) before running them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

AUDIENCES = ("private", "party", "dm")
STATUSES = ("active", "retired")
FILENAME = "character.yaml"


class ConfigError(Exception):
    """character.yaml is missing or invalid. The message names the file and field."""


@dataclass
class Document:
    file: str
    script: str
    audience: str
    future_sections: list[str] = field(default_factory=list)
    spell_ignore: list[str] = field(default_factory=list)

    def source(self, char_dir: Path) -> Path:
        """The build script's source file: ``ddtools:<name>`` is ddtools' own module."""
        if self.script.startswith("ddtools:"):
            import importlib.util

            spec = importlib.util.find_spec(f"ddtools.{self.script.split(':', 1)[1]}")
            if spec is None or spec.origin is None:
                raise ConfigError(f"{self.script}: ddtools has no such document")
            return Path(spec.origin)
        return Path(char_dir) / self.script


@dataclass
class Character:
    dir: Path
    name: str
    status: str
    level: int
    updated: date
    dndbeyond_id: int | None
    class_summary: str
    campaign: dict[str, Any]
    documents: list[Document]
    secrets_file: str = "secrets.txt"
    retired: dict | None = None
    # Top-level keys ddtools doesn't know (e.g. a plugin's), kept as they are on save.
    extra: dict[str, Any] = field(default_factory=dict)
    party_summary: str = ""  # one line the party knows (the workbook's own row)

    @property
    def secrets_path(self) -> Path:
        return self.dir / self.secrets_file


def _require(data: dict, key: str, kind: type, where: Path):
    if key not in data or data[key] is None:
        raise ConfigError(f"{where}: missing required field '{key}'")
    if not isinstance(data[key], kind):
        raise ConfigError(f"{where}: field '{key}' must be {kind.__name__}")
    return data[key]


KNOWN_KEYS = {
    "name", "status", "level", "updated", "dndbeyond_id", "class_summary", "party_summary",
    "campaign", "documents", "secrets_file", "retired",
}  # fmt: skip


def load_character(dir: Path | str | None = None) -> Character:
    """Load and validate ``<dir>/character.yaml`` (default: ``$DDTOOLS_CHARACTER_DIR``)."""
    if dir is None:
        env = os.environ.get("DDTOOLS_CHARACTER_DIR")
        if not env:
            raise ConfigError("No character folder given and DDTOOLS_CHARACTER_DIR is not set")
        dir = env
    base = Path(dir).resolve()
    path = base / FILENAME
    if not path.is_file():
        raise ConfigError(f"{path}: not found")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as err:
        raise ConfigError(f"{path}: not valid YAML ({err})") from err
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: must be a mapping of fields")

    name = _require(data, "name", str, path)
    level = _require(data, "level", int, path)
    updated = _require(data, "updated", date, path)
    status = data.get("status", "active")
    if status not in STATUSES:
        raise ConfigError(f"{path}: field 'status' must be one of {', '.join(STATUSES)}")
    docs = []
    for i, d in enumerate(data.get("documents") or []):
        if not isinstance(d, dict) or not {"file", "script", "audience"} <= d.keys():
            raise ConfigError(f"{path}: documents[{i}] needs file, script and audience")
        if d["audience"] not in AUDIENCES:
            raise ConfigError(
                f"{path}: documents[{i}].audience must be one of {', '.join(AUDIENCES)}"
            )
        docs.append(Document(**d))
    return Character(
        dir=base,
        name=name,
        status=status,
        level=level,
        updated=updated,
        dndbeyond_id=data.get("dndbeyond_id"),
        class_summary=data.get("class_summary", ""),
        campaign=data.get("campaign") or {},
        documents=docs,
        secrets_file=data.get("secrets_file", "secrets.txt"),
        retired=data.get("retired"),
        extra={k: v for k, v in data.items() if k not in KNOWN_KEYS},
        party_summary=data.get("party_summary", ""),
    )


def save_character(ch: Character) -> None:
    """Write ``character.yaml`` back, keeping field order."""
    data = {
        "name": ch.name,
        "status": ch.status,
        "level": ch.level,
        "updated": ch.updated,
        "dndbeyond_id": ch.dndbeyond_id,
        "class_summary": ch.class_summary,
        **({"party_summary": ch.party_summary} if ch.party_summary else {}),
        "campaign": ch.campaign,
        "documents": [
            {k: v for k, v in vars(d).items() if v or k in ("file", "script", "audience")}
            for d in ch.documents
        ],  # fmt: skip
        "secrets_file": ch.secrets_file,
        "retired": ch.retired,
        **ch.extra,
    }
    text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)
    (ch.dir / FILENAME).write_text(text, encoding="utf-8")


def _day(d: date) -> str:
    return f"{d.day} {d.strftime('%b %Y')}"


def stamp(ch: Character) -> str:
    """Footer stamp, e.g. ``Level 3 · updated 28 Sep 2026``."""
    return f"Level {ch.level} · updated {_day(ch.updated)}"


def date_stamp(ch: Character) -> str:
    """Date-only stamp, e.g. ``updated 28 Sep 2026``."""
    return f"updated {_day(ch.updated)}"


def output_path(ch: Character, filename: str) -> Path:
    """Where a build script writes ``filename``: ``$DDTOOLS_OUT`` or ``<dir>/pdf``."""
    out = Path(os.environ.get("DDTOOLS_OUT") or ch.dir / "pdf")
    out.mkdir(parents=True, exist_ok=True)
    return out / filename


def rules_rows(ch: Character, audience: str | None = None) -> list[list[str]]:
    """Rows for a Rules & Rulings table (header first) from ``campaign.rules``.

    A rule with ``show_in: [...]`` appears only in documents for those audiences.
    """
    rows = [["Topic", "Status"]]
    for rule in ch.campaign.get("rules") or []:
        if audience and "show_in" in rule and audience not in rule["show_in"]:
            continue
        status, note = rule.get("status", "open"), rule.get("note")
        if status in ("confirmed", "open"):
            cell = f"<b>{status.capitalize()}</b>" + (f" ({note})" if note else "")
        else:
            cell = note or status.capitalize()
        rows.append([rule["text"], cell])
    return rows


def character_dirs(root: Path | str = ".", include_archive: bool = False) -> list[Path]:
    """Character folders (containing character.yaml) directly under ``root``."""
    root = Path(root)
    found = sorted(p.parent for p in root.glob(f"*/{FILENAME}"))
    if include_archive:
        found += sorted(p.parent for p in (root / "archive").glob(f"*/{FILENAME}"))
    return found


# ---- the party list, edited in place (keeping character.yaml's comments) --------------


def _yaml_line(key: str, value, indent: int) -> str:
    text = yaml.safe_dump({key: value}, allow_unicode=True, width=10**6, sort_keys=False)
    return " " * indent + text.rstrip("\n")


def _party_span(lines: list[str]) -> tuple[int, int] | None:
    """Line range of the block-style ``campaign.party`` list items, or None."""
    try:
        start = lines.index("  party:") + 1
    except ValueError:
        return None
    end = start
    while end < len(lines) and (not lines[end].strip() or lines[end].startswith("    ")):
        end += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return start, end


def _member_span(lines: list[str], span: tuple[int, int], name: str) -> tuple[int, int] | None:
    starts = [i for i in range(*span) if lines[i].startswith("    - ")]
    for n, i in enumerate(starts):
        if yaml.safe_load(lines[i][6:]) == {"name": name}:
            return i, starts[n + 1] if n + 1 < len(starts) else span[1]
    return None


def _set_field(lines: list[str], block: tuple[int, int], key: str, value) -> None:
    start, end = block
    new = _yaml_line(key, value, 6)
    for i in range(start + 1, end):
        if lines[i].startswith(f"      {key}:"):
            j = i + 1
            while j < end and lines[j].startswith("        "):
                j += 1
            lines[i:j] = [new]
            return
    last = end
    while last > start + 1 and not lines[last - 1].strip():
        last -= 1
    lines.insert(last, new)


def _write_party(ch_dir: Path, mutate) -> None:
    """Apply ``mutate(party)`` to character.yaml's party list, editing only the lines it needs.

    Falls back to rewriting the whole file only if the list isn't in the usual block style.
    The result is always re-read and checked against what ``mutate`` asked for.
    """
    path = Path(ch_dir) / FILENAME
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    expected = yaml.safe_load(text)
    party = expected.setdefault("campaign", {}).setdefault("party", [])
    edits = mutate(party)
    lines = text.split("\n")
    span = _party_span(lines)
    try:
        if span is None:
            raise LookupError
        for kind, name, fields in edits:
            if kind == "set":
                block = _member_span(lines, span, name)
                if block is None:
                    raise LookupError
                for key, value in fields.items():
                    _set_field(lines, block, key, value)
                    block = _member_span(lines, _party_span(lines), name)
            else:
                at = _party_span(lines)[1]
                entry = [_yaml_line("name", name, 4).replace("    name:", "    - name:", 1)]
                entry += [_yaml_line(k, v, 6) for k, v in fields.items()]
                lines[at:at] = entry
            span = _party_span(lines)
        new_text = "\n".join(lines)
        if yaml.safe_load(new_text) != expected:
            raise LookupError
    except LookupError:
        new_text = yaml.safe_dump(expected, sort_keys=False, allow_unicode=True, width=100)
    if data != expected:
        path.write_text(new_text, encoding="utf-8")


def set_party_fields(ch_dir: Path, name: str, fields: dict) -> None:
    """Set fields on one party member (matched by ``name``)."""

    def mutate(party):
        member = next((p for p in party if p.get("name") == name), None)
        if member is None:
            raise ConfigError(f"{name} isn't in {FILENAME}'s party list")
        changed = {k: v for k, v in fields.items() if member.get(k) != v}
        member.update(changed)
        return [("set", name, changed)] if changed else []

    _write_party(ch_dir, mutate)


def add_party_member(ch_dir: Path, entry: dict) -> None:
    """Append a member (``entry`` has ``name`` first) to the party list."""

    def mutate(party):
        party.append(dict(entry))
        fields = {k: v for k, v in entry.items() if k != "name"}
        return [("add", entry["name"], fields)]

    _write_party(ch_dir, mutate)


# ---- who is in the party (for the documents) ------------------------------------------


def party_member(ch: Character, name: str) -> dict | None:
    """The party entry called ``name``, or whose first word is ``name`` ("Bramble" for
    "Bramble the Bold")."""
    for p in ch.campaign.get("party") or []:
        full = p.get("name", "")
        if name in (full, full.split(" ")[0]):
            return p
    return None


def present(ch: Character, name: str) -> bool:
    """True if ``name`` is still in the party: on the list and not gone for good."""
    p = party_member(ch, name)
    return p is not None and p.get("status", "active") != "gone"


def absent_friends(ch: Character) -> list[dict]:
    """Teammates gone for good, in party-list order."""
    return [p for p in ch.campaign.get("party") or [] if p.get("status") == "gone"]


def newcomers(ch: Character, known: list[str]) -> list[dict]:
    """Teammates in the party whose names the documents don't have their own text for yet."""
    return [
        p
        for p in ch.campaign.get("party") or []
        if p.get("status", "active") != "gone" and p.get("name") not in known
    ]


def set_top_level(ch_dir: Path, key: str, value) -> None:
    """Set one top-level scalar in ``character.yaml``, keeping every comment and line.

    Replaces the ``key:`` line (keeping a trailing comment) or adds it at the end; then
    checks the file still loads.
    """
    path = Path(ch_dir) / FILENAME
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    new = _yaml_line(key, value, 0).rstrip("\n")
    for i, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            comment = line.split("  #", 1)[1].rstrip("\n") if "  #" in line else ""
            lines[i] = f"{new}  #{comment}\n" if comment else f"{new}\n"
            break
    else:
        lines.append(f"{new}\n")
    before = path.read_text(encoding="utf-8")
    path.write_text("".join(lines), encoding="utf-8")
    try:
        load_character(ch_dir)
    except ConfigError:
        path.write_text(before, encoding="utf-8")
        raise
