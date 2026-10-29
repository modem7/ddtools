"""Read and write a character's ``character.yaml``.

Build scripts call ``load_character()`` with no argument: ``ddtools build`` sets
``DDTOOLS_CHARACTER_DIR`` (and ``DDTOOLS_OUT``) before running them.
"""

from __future__ import annotations

import copy
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from dataclasses import fields as dataclass_fields
from datetime import date
from pathlib import Path
from typing import Any, Literal, NotRequired, TypedDict, cast, get_args

import yaml

from ddtools.errors import DdtoolsError

# A path argument: a Path or a plain string. Path-taking functions put what they act on
# first and any destination last: ``build_character(char_dir, out)``,
# ``import_workbook(pdf, char_dir)``.
type PathLike = str | os.PathLike[str]

Status = Literal["active", "retired"]
AUDIENCES = ("private", "party", "dm")
STATUSES: tuple[Status, ...] = get_args(Status)
FILENAME = "character.yaml"
BUILTIN_PREFIX = "ddtools:"  # a document script ddtools ships, e.g. ``ddtools:workbook``


class ConfigError(DdtoolsError):
    """character.yaml is missing or invalid. The message names the file and field."""


class Retirement(TypedDict):
    """``retired:`` in character.yaml, as ``ddtools retire`` writes it."""

    date: date
    reason: str
    note: str


class PartyMember(TypedDict):
    """One ``campaign.party`` entry. Other keys are kept for the campaign's own scripts."""

    name: str
    dndbeyond_id: NotRequired[int | None]
    status: NotRequired[str]
    summary: NotRequired[str]


@dataclass
class Document:
    file: str
    script: str
    audience: str
    future_sections: list[str] = field(default_factory=list)
    spell_ignore: list[str] = field(default_factory=list)

    @property
    def module_name(self) -> str | None:
        """``ddtools.<name>`` for a ``ddtools:<name>`` script; None for the repo's own."""
        if self.script.startswith(BUILTIN_PREFIX):
            return f"ddtools.{self.script.removeprefix(BUILTIN_PREFIX)}"
        return None

    @property
    def is_builtin(self) -> bool:
        """True for a document ddtools builds itself (``ddtools:<name>``)."""
        return self.module_name is not None

    def command(self, char_dir: PathLike) -> tuple[Path, list[str], Path]:
        """How ``ddtools build`` runs the script: ``(script, argv, cwd)``.

        ``script`` names it in errors. ddtools' own module runs with ``python -m`` from
        the character folder; a repo script runs from its own folder.
        """
        module = self.module_name
        if module is not None:
            return Path(self.script), [sys.executable, "-m", module], Path(char_dir)
        script = Path(char_dir) / self.script
        return script, [sys.executable, str(script)], script.parent

    def source(self, char_dir: PathLike) -> Path:
        """The build script's source file: ``ddtools:<name>`` is ddtools' own module.

        Raises:
            ConfigError: a ``ddtools:<name>`` script names no ddtools module.
        """
        module = self.module_name
        if module is not None:
            import importlib.util

            spec = importlib.util.find_spec(module)
            if spec is None or spec.origin is None:
                raise ConfigError(f"{self.script}: ddtools has no such document")
            return Path(spec.origin)
        return Path(char_dir) / self.script


@dataclass
class Character:
    dir: Path
    name: str
    status: Status
    level: int
    updated: date
    dndbeyond_id: int | None
    class_summary: str
    campaign: dict[str, Any]
    documents: list[Document]
    secrets_file: str = "secrets.txt"
    retired: Retirement | None = None
    # Top-level keys ddtools doesn't know (e.g. a plugin's), kept as they are on save.
    extra: dict[str, Any] = field(default_factory=dict)
    party_summary: str = ""  # one line the party knows (the workbook's own row)

    @property
    def secrets_path(self) -> Path:
        return self.dir / self.secrets_file


def _require[T](data: dict, key: str, kind: type[T], where: Path) -> T:
    if key not in data or data[key] is None:
        raise ConfigError(f"{where}: missing required field '{key}'")
    if not isinstance(data[key], kind):
        raise ConfigError(f"{where}: field '{key}' must be {kind.__name__}")
    return data[key]


KNOWN_KEYS = {
    "name", "status", "level", "updated", "dndbeyond_id", "class_summary", "party_summary",
    "campaign", "documents", "secrets_file", "retired",
}  # fmt: skip


def _document(d: dict, i: int, path: Path, base: Path) -> Document:
    """One ``documents:`` entry, checked: known fields only, the right types, and a
    script that stays inside the character folder (``ddtools:<name>`` aside)."""
    known = {f.name for f in dataclass_fields(Document)}
    for key in d:
        if key not in known:
            raise ConfigError(f"{path}: documents[{i}] has unknown field {key!r}")
    for key in ("file", "script"):
        if not isinstance(d[key], str):
            raise ConfigError(f"{path}: documents[{i}].{key} must be text")
    for key in ("future_sections", "spell_ignore"):
        value = d.get(key, [])
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ConfigError(f"{path}: documents[{i}].{key} must be a list of text")
    script = d["script"]
    if not script.startswith(BUILTIN_PREFIX) and not (base / script).resolve().is_relative_to(base):
        raise ConfigError(f"{path}: documents[{i}].script must stay inside the character folder")
    return Document(**d)


def load_character(char_dir: PathLike | None = None) -> Character:
    """Load and validate ``<char_dir>/character.yaml`` (default: ``$DDTOOLS_CHARACTER_DIR``).

    Every ``campaign.party`` entry must be a mapping with a ``name``. ``dndbeyond_id`` is
    optional here; the commands that fetch a member report it if it's missing.

    Raises:
        ConfigError: the file is missing or invalid; the message names the file and field.
    """
    if char_dir is None:
        env = os.environ.get("DDTOOLS_CHARACTER_DIR")
        if not env:
            raise ConfigError("No character folder given and DDTOOLS_CHARACTER_DIR is not set")
        char_dir = env
    base = Path(char_dir).resolve()
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
    retired = data.get("retired")
    if retired is not None and not (
        isinstance(retired, dict)
        and isinstance(retired.get("date"), date)
        and isinstance(retired.get("reason"), str)
        and isinstance(retired.get("note"), str)
    ):
        raise ConfigError(f"{path}: field 'retired' must be a mapping with date, reason and note")
    docs = []
    for i, d in enumerate(data.get("documents") or []):
        if not isinstance(d, dict) or not {"file", "script", "audience"} <= d.keys():
            raise ConfigError(f"{path}: documents[{i}] needs file, script and audience")
        if d["audience"] not in AUDIENCES:
            raise ConfigError(
                f"{path}: documents[{i}].audience must be one of {', '.join(AUDIENCES)}"
            )
        docs.append(_document(d, i, path, base))
    campaign = data.get("campaign") or {}
    if not isinstance(campaign, dict):
        raise ConfigError(f"{path}: field 'campaign' must be a mapping")
    party = campaign.get("party") or []
    if not isinstance(party, list):
        raise ConfigError(f"{path}: campaign.party must be a list")
    for i, p in enumerate(party):
        if not isinstance(p, dict) or not isinstance(p.get("name"), str) or not p["name"]:
            raise ConfigError(
                f"{path}: campaign.party[{i}] needs a name (as text: quote it if it looks "
                "like a number or yes/no)"
            )
    return Character(
        dir=base,
        name=name,
        status=cast(Status, status),
        level=level,
        updated=updated,
        dndbeyond_id=data.get("dndbeyond_id"),
        class_summary=data.get("class_summary", ""),
        campaign=campaign,
        documents=docs,
        secrets_file=data.get("secrets_file", "secrets.txt"),
        retired=retired,
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


def level_updated_label(ch: Character) -> str:
    """Footer label with level and date, e.g. ``Level 3 · updated 28 Sep 2026``."""
    return f"Level {ch.level} · updated {_day(ch.updated)}"


def updated_label(ch: Character) -> str:
    """Footer label with the date only, e.g. ``updated 28 Sep 2026``."""
    return f"updated {_day(ch.updated)}"


def output_dir(ch: Character) -> Path:
    """The folder build scripts write to: ``$DDTOOLS_OUT`` or ``<char_dir>/pdf``. Pure."""
    return Path(os.environ.get("DDTOOLS_OUT") or ch.dir / "pdf")


def output_path(ch: Character, filename: str) -> Path:
    """Where a build script writes ``filename``, in ``output_dir(ch)``.

    Not pure: it creates that folder (with parents) if it's missing, so a script can
    write straight to the path it gets.
    """
    out = output_dir(ch)
    out.mkdir(parents=True, exist_ok=True)
    return out / filename


# Old names, kept: every campaign's copied build scripts import them.
stamp = level_updated_label
date_stamp = updated_label


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


def character_dirs(root: PathLike = ".", include_archive: bool = False) -> list[Path]:
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


# One party-list change: ("set", name, fields) on a member, or ("add", name, fields).
type PartyEdit = tuple[Literal["set", "add"], str, dict[str, Any]]


def _apply_edits(party: list[dict], edits: list[PartyEdit]) -> None:
    """Make ``edits`` to the parsed party list: what the file must hold afterwards."""
    for kind, name, fields in edits:
        if kind == "set":
            next(p for p in party if p.get("name") == name).update(fields)
        else:
            party.append({"name": name, **fields})


def _block_span(lines: list[str]) -> tuple[int, int]:
    span = _party_span(lines)
    if span is None:
        raise LookupError
    return span


def _write_party(char_dir: PathLike, plan: Callable[[list[dict]], list[PartyEdit]]) -> None:
    """Make the edits ``plan(party)`` returns to character.yaml's party list, editing only
    the lines they need.

    ``plan`` gets a copy of the current party list to read; it returns edits and changes
    nothing itself. The file must then match the edits applied to the parsed list. If
    the list isn't in the usual block style, or the line edits don't give that result,
    the whole file is rewritten from the parsed data instead (losing its comments).
    """
    path = Path(char_dir) / FILENAME
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    expected = yaml.safe_load(text)
    party = expected.setdefault("campaign", {}).setdefault("party", [])
    edits = plan(copy.deepcopy(party))
    _apply_edits(party, edits)
    lines = text.split("\n")
    try:
        span = _block_span(lines)
        for kind, name, fields in edits:
            if kind == "set":
                block = _member_span(lines, span, name)
                for key, value in fields.items():
                    if block is None:
                        raise LookupError
                    _set_field(lines, block, key, value)
                    block = _member_span(lines, _block_span(lines), name)
            else:
                at = _block_span(lines)[1]
                entry = [_yaml_line("name", name, 4).replace("    name:", "    - name:", 1)]
                entry += [_yaml_line(k, v, 6) for k, v in fields.items()]
                lines[at:at] = entry
            span = _block_span(lines)
        new_text = "\n".join(lines)
        if yaml.safe_load(new_text) != expected:
            raise LookupError
    except LookupError:
        new_text = yaml.safe_dump(expected, sort_keys=False, allow_unicode=True, width=100)
    if data != expected:
        path.write_text(new_text, encoding="utf-8")


def set_party_fields(char_dir: PathLike, name: str, fields: dict) -> None:
    """Set fields on one party member (matched by ``name``).

    Raises:
        ConfigError: no party member is called ``name``.
    """

    def plan(party: list[dict]) -> list[PartyEdit]:
        member = next((p for p in party if p.get("name") == name), None)
        if member is None:
            raise ConfigError(f"{name} isn't in {FILENAME}'s party list")
        changed = {k: v for k, v in fields.items() if member.get(k) != v}
        return [("set", name, changed)] if changed else []

    _write_party(char_dir, plan)


def add_party_member(char_dir: PathLike, entry: PartyMember) -> None:
    """Append a member (``entry`` has ``name`` first) to the party list.

    Raises:
        ConfigError: ``entry`` has no ``name`` (as text), or the file is invalid.
    """
    if not isinstance(entry.get("name"), str) or not entry["name"]:
        raise ConfigError(f"{FILENAME}: a party member needs a name (as text)")

    def plan(party: list[dict]) -> list[PartyEdit]:
        fields = {k: v for k, v in entry.items() if k != "name"}
        return [("add", entry["name"], fields)]

    _write_party(char_dir, plan)


# ---- who is in the party (for the documents) ------------------------------------------


def party_member(ch: Character, name: str) -> PartyMember | None:
    """The party entry called ``name``, or whose first word is ``name`` ("Bramble" for
    "Bramble the Bold")."""
    for p in ch.campaign.get("party") or []:
        full = p.get("name", "")
        if name in (full, full.split(" ")[0]):
            return p
    return None


def is_present(ch: Character, name: str) -> bool:
    """True if ``name`` is still in the party: on the list and not gone for good."""
    p = party_member(ch, name)
    return p is not None and p.get("status", "active") != "gone"


present = is_present  # old name, kept for campaigns' own build scripts


def absent_friends(ch: Character) -> list[PartyMember]:
    """Teammates gone for good, in party-list order."""
    return [p for p in ch.campaign.get("party") or [] if p.get("status") == "gone"]


def newcomers(ch: Character, known: list[str]) -> list[PartyMember]:
    """Teammates in the party whose names the documents don't have their own text for yet."""
    return [
        p
        for p in ch.campaign.get("party") or []
        if p.get("status", "active") != "gone" and p.get("name") not in known
    ]


def set_top_level(char_dir: PathLike, key: str, value: Any) -> None:
    """Set one top-level scalar in ``character.yaml``, keeping every comment and line.

    Replaces the ``key:`` line (keeping a trailing comment) or adds it at the end; then
    checks the file still loads.
    """
    path = Path(char_dir) / FILENAME
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
        load_character(char_dir)
    except ConfigError:
        path.write_text(before, encoding="utf-8")
        raise
