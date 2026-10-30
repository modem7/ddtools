"""Read-only access to D&D Beyond character sheets: fetch, summarise, diff, watch.

Characters must be set to Public on D&D Beyond for the character service to return them.
"""

from __future__ import annotations

import http.client
import json
import re
import urllib.error
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, NotRequired, TypedDict, get_args
from urllib.request import Request, urlopen

from ddtools.errors import DdtoolsError

if TYPE_CHECKING:
    from ddtools.config import Character, PathLike

API = "https://character-service.dndbeyond.com/character/v5/character/{id}"
ABILITIES = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
_SCORE_SUBTYPES = [
    "strength-score", "dexterity-score", "constitution-score",
    "intelligence-score", "wisdom-score", "charisma-score",
]  # fmt: skip
_SPELL_SOURCES = {"race": "Race", "class": "Class feature", "item": "Item", "feat": "Feat"}
LEVELUP_CHECKLIST = [
    "Cheat sheet in the personal guide: stats, slots, actions for the new level",
    "Party handout: 'What She Can Do for You Right Now' and 'Coming Soon'",
    "DM brief: 'Current Numbers' and the level plan",
    "Personal guide: level table and 'Next level' boxes",
    "character.yaml: bump `level` and `updated`",
    "Rebuild, `ddtools check`, preview every changed page, then `ddtools golden update`",
]


class DndBeyondError(DdtoolsError):
    """A sheet could not be fetched or read. The message says which character and why."""


class SnapshotError(DndBeyondError):
    """A saved sheet in ``snapshots/`` can't be read. The message names the file."""


class BadCharacterId(DdtoolsError, ValueError):
    """Text that isn't a D&D Beyond character id or URL."""


class ClassSummary(TypedDict):
    name: str
    level: int
    subclass: str | None


class ItemSummary(TypedDict):
    name: str
    magic: bool
    equipped: bool
    attuned: bool
    quantity: int


class SheetSummary(TypedDict):
    """The parts of a sheet the documents depend on (``summarise``)."""

    name: str | None
    classes: list[ClassSummary]
    level: int
    hp_base: int | None
    stats: dict[str, int]
    spells: dict[str, list[str]]  # source -> spell names
    options: list[str]
    feats: list[str]
    items: list[ItemSummary]
    gold: dict[str, int]


class PartyEntry(TypedDict):
    """One member in ``party.json`` (``party_entry``)."""

    id: int | None
    name: str | None
    level: int
    classes: list[str]
    gender: str | None


class PartyChange(TypedDict):
    """A party member whose sheet changed since ``party.json``."""

    name: str
    before: PartyEntry | None  # None: new to the baseline
    after: PartyEntry


class SheetDiff(TypedDict):
    """What changed between two sheets (``diff``); unchanged parts are empty or ``None``."""

    level: tuple[int, int] | None
    classes: tuple[list[ClassSummary], list[ClassSummary]] | None
    spells_added: dict[str, list[str]]
    spells_removed: dict[str, list[str]]
    options_added: list[str]
    options_removed: list[str]
    feats_added: list[str]
    feats_removed: list[str]
    items_added: list[str]
    items_removed: list[str]
    attunement_changed: list[str]
    stats: dict[str, tuple[int, int]]
    hp_base: tuple[int | None, int | None] | None
    gold: dict[str, tuple[int, int]]


class WatchResult(TypedDict):
    """What ``watch_character`` found for one character."""

    character: str
    dir: str  # the character's folder name
    own: SheetDiff | None  # their sheet's ``diff``, if it changed meaningfully
    party: list[PartyChange]
    errors: list[str]
    gold: NotRequired[dict[str, tuple[int, int]]]  # only when their sheet was compared


def parse_id(text: str) -> int:
    """A character id from a bare number or any ``dndbeyond.com/characters/<id>`` URL.

    Raises:
        BadCharacterId: ``text`` has no id in it (also a ``ValueError``).
    """
    text = str(text).strip()
    if text.isdigit():
        return int(text)
    m = re.search(r"dndbeyond\.com/characters/(\d+)", text)
    if not m:
        raise BadCharacterId(f"Not a D&D Beyond character id or URL: {text!r}")
    return int(m.group(1))


def fetch_character(char_id: int, timeout: float = 20) -> dict:
    """Fetch a character's sheet JSON (the ``data`` object).

    Raises:
        DndBeyondError: the sheet couldn't be fetched; the message says why.
    """
    req = Request(API.format(id=char_id), headers={"User-Agent": "ddtools/0.1"})
    try:
        with urlopen(req, timeout=timeout) as resp:  # nosec B310 - API is an https constant
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        if err.code in (401, 403, 404):
            raise DndBeyondError(
                f"Character {char_id}: HTTP {err.code}. Either the sheet is private or missing "
                "(set it to Public: Character Settings → Character Privacy), or D&D Beyond is "
                "blocking automated requests from this network."
            ) from err
        raise DndBeyondError(
            f"Character {char_id}: HTTP {err.code} from D&D Beyond"
            + (" (rate limited, try again later)" if err.code == 429 else "")
        ) from err
    except (urllib.error.URLError, TimeoutError) as err:
        raise DndBeyondError(f"Character {char_id}: could not reach D&D Beyond ({err})") from err
    except (OSError, http.client.HTTPException) as err:
        raise DndBeyondError(
            f"Character {char_id}: connection failed mid-response ({err})"
        ) from err
    except ValueError as err:
        raise DndBeyondError(
            f"Character {char_id}: D&D Beyond sent something that isn't character data "
            "(likely a block or challenge page)"
        ) from err
    data = payload.get("data") if isinstance(payload, dict) else None
    if not data:
        raise DndBeyondError(f"Character {char_id}: D&D Beyond returned no character data")
    return data


def _snapshot_key(path: Path) -> tuple[str, int]:
    """Sort key for ``YYYY-MM-DD[-N].json``: by day, then by same-day suffix."""
    parts = path.stem.split("-")
    day = "-".join(parts[:3])
    suffix = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 1
    return day, suffix


def snapshot_dir(ch: Character) -> Path:
    return Path(ch.dir) / "snapshots"


def save_snapshot(ch: Character, data: dict, today: str | None = None) -> Path:
    """Save to ``snapshots/YYYY-MM-DD.json`` (``-2``, ``-3``… if that day is taken)."""
    folder = snapshot_dir(ch)
    folder.mkdir(parents=True, exist_ok=True)
    day = today or date.today().isoformat()
    path, n = folder / f"{day}.json", 1
    while path.exists():
        n += 1
        path = folder / f"{day}-{n}.json"
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_snapshot(path: PathLike) -> Any:
    """The JSON in a saved snapshot (a sheet, or ``party.json``'s list).

    Raises:
        SnapshotError: the file is missing, unreadable or not valid JSON.
    """
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise SnapshotError(f"{path}: not found") from err
    except (OSError, UnicodeDecodeError, ValueError) as err:
        raise SnapshotError(f"{path}: can't read it as a snapshot ({err})") from err


def latest_snapshots(ch: Character, n: int = 2) -> list[Path]:
    """The newest ``n`` character snapshots, oldest first (``party.json`` excluded)."""
    files = [
        p
        for p in snapshot_dir(ch).glob("*.json")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}(-\d+)?", p.stem)
    ]
    return sorted(files, key=_snapshot_key)[-n:]


def _names(entries: Any) -> list[str]:
    return sorted(
        e["definition"]["name"]
        for e in entries or []
        if isinstance(e, dict) and e.get("definition")
    )


def _stats(data: dict) -> dict[str, int]:
    def by_id(key: str) -> dict:
        return {s["id"]: s.get("value") for s in data.get(key) or []}

    base, bonus, override = by_id("stats"), by_id("bonusStats"), by_id("overrideStats")
    mods = [m for group in (data.get("modifiers") or {}).values() for m in group or []]
    out: dict[str, int] = {}
    for i, (abbr, subtype) in enumerate(zip(ABILITIES, _SCORE_SUBTYPES, strict=True), 1):
        if override.get(i):
            out[abbr] = override[i]
            continue
        extra = sum(
            m.get("value") or 0
            for m in mods
            if m.get("type") == "bonus" and m.get("subType") == subtype
        )
        out[abbr] = (base.get(i) or 0) + (bonus.get(i) or 0) + extra
    return out


def summarise(data: dict) -> SheetSummary:
    """The parts of a sheet the documents depend on, in a stable, comparable shape."""
    classes: list[ClassSummary] = [
        {
            "name": c["definition"]["name"],
            "level": c.get("level", 0),
            "subclass": (c.get("subclassDefinition") or {}).get("name"),
        }
        for c in data.get("classes") or []
    ]
    class_names = {c["id"]: c["definition"]["name"] for c in data.get("classes") or []}
    spells: dict[str, list[str]] = {}
    for block in data.get("classSpells") or []:
        names = _names(block.get("spells"))
        if names:
            spells[class_names.get(block.get("characterClassId"), "Class")] = names
    for key, label in _SPELL_SOURCES.items():
        names = _names((data.get("spells") or {}).get(key))
        if names:
            spells[label] = sorted(set(spells.get(label, [])) | set(names))
    options = sorted(n for group in (data.get("options") or {}).values() for n in _names(group))
    items: list[ItemSummary] = sorted(
        (
            {
                "name": i["definition"]["name"],
                "magic": bool(i["definition"].get("magic")),
                "equipped": bool(i.get("equipped")),
                "attuned": bool(i.get("isAttuned")),
                "quantity": i.get("quantity", 1),
            }
            for i in data.get("inventory") or []
            if i.get("definition")
        ),
        key=lambda i: i["name"],
    )
    return {
        "name": data.get("name"),
        "classes": classes,
        "level": sum(c["level"] for c in classes),
        "hp_base": data.get("baseHitPoints"),
        "stats": _stats(data),
        "spells": spells,
        "options": options,
        "feats": _names(data.get("feats")),
        "items": items,
        "gold": dict(data.get("currencies") or {}),
    }


def class_label(c: ClassSummary) -> str:
    """``Warlock 2 (The Fiend)`` from a summarised class entry."""
    return f"{c['name']} {c['level']}" + (f" ({c['subclass']})" if c["subclass"] else "")


def party_entry(data: dict) -> PartyEntry:
    s = summarise(data)
    return {
        "id": data.get("id"),
        "name": s["name"],
        "level": s["level"],
        "classes": [class_label(c) for c in s["classes"]],
        # As the player typed it on the sheet; the ledger maps it to pronouns.
        "gender": (data.get("data", data).get("gender") or "").strip() or None,
    }


def _list_diff(old: list[str], new: list[str]) -> tuple[list[str], list[str]]:
    return sorted(set(new) - set(old)), sorted(set(old) - set(new))


def diff(old: dict, new: dict) -> SheetDiff:
    """What changed between two sheets. Unchanged parts are empty (or ``None``)."""
    a, b = summarise(old), summarise(new)
    level = (a["level"], b["level"]) if a["level"] != b["level"] else None
    classes = (a["classes"], b["classes"]) if a["classes"] != b["classes"] else None
    added: dict[str, list[str]] = {}
    removed: dict[str, list[str]] = {}
    for src in sorted(set(a["spells"]) | set(b["spells"])):
        plus, minus = _list_diff(a["spells"].get(src, []), b["spells"].get(src, []))
        if plus:
            added[src] = plus
        if minus:
            removed[src] = minus
    options_added, options_removed = _list_diff(a["options"], b["options"])
    feats_added, feats_removed = _list_diff(a["feats"], b["feats"])
    magic_a = {i["name"]: i for i in a["items"] if i["magic"]}
    magic_b = {i["name"]: i for i in b["items"] if i["magic"]}
    items_added, items_removed = _list_diff(list(magic_a), list(magic_b))
    attunement_changed = sorted(
        n
        for n in set(magic_a) & set(magic_b)
        if (magic_a[n]["attuned"], magic_a[n]["equipped"])
        != (magic_b[n]["attuned"], magic_b[n]["equipped"])
    )
    stats = {k: (a["stats"][k], b["stats"][k]) for k in ABILITIES if a["stats"][k] != b["stats"][k]}
    hp_base = (a["hp_base"], b["hp_base"]) if a["hp_base"] != b["hp_base"] else None
    gold = {
        k: (a["gold"].get(k, 0), b["gold"].get(k, 0))
        for k in ("pp", "gp", "ep", "sp", "cp")
        if a["gold"].get(k, 0) != b["gold"].get(k, 0)
    }
    return {
        "level": level,
        "classes": classes,
        "spells_added": added,
        "spells_removed": removed,
        "options_added": options_added,
        "options_removed": options_removed,
        "feats_added": feats_added,
        "feats_removed": feats_removed,
        "items_added": items_added,
        "items_removed": items_removed,
        "attunement_changed": attunement_changed,
        "stats": stats,
        "hp_base": hp_base,
        "gold": gold,
    }


# ---- watch ---------------------------------------------------------------

# Diff keys holding a plain list of names.
ListDiffKey = Literal[
    "options_added", "options_removed", "feats_added", "feats_removed",
    "items_added", "items_removed", "attunement_changed",
]  # fmt: skip
LIST_DIFFS: tuple[ListDiffKey, ...] = get_args(ListDiffKey)
_PARTY_KEYS = {"id", "name", "level", "classes"}  # what watch compares in party.json
MEANINGFUL = ("level", "classes", "spells_added", "spells_removed", *LIST_DIFFS, "stats", "hp_base")


def is_meaningful(d: SheetDiff) -> bool:
    """True if a diff has anything beyond gold/consumables worth an update session."""
    return any(d.get(k) for k in MEANINGFUL)


# What a sheet that is not the shape we expect raises when read.
_BAD_SHAPE = (KeyError, TypeError, AttributeError)


def watch_character(ch: Character, fetch: Callable[[int], dict] | None = None) -> WatchResult:
    """Compare live sheets with the committed baselines for one character and its party.

    Never raises for a fetch or a bad file: problems go into ``result["errors"]``.
    """
    fetch = fetch or fetch_character
    result: WatchResult = {
        "character": ch.name, "dir": Path(ch.dir).name, "own": None, "party": [], "errors": [],
    }  # fmt: skip
    snaps = latest_snapshots(ch, 1)
    if ch.dndbeyond_id:
        try:
            live = fetch(ch.dndbeyond_id)
            if snaps:
                d = diff(load_snapshot(snaps[-1]), live)
                result["own"] = d if is_meaningful(d) else None
                result["gold"] = d["gold"]
            else:
                result["errors"].append(f"{ch.name}: no committed snapshot to compare against")
        except DndBeyondError as err:
            result["errors"].append(f"{ch.name}: {err}")
        except _BAD_SHAPE as err:
            result["errors"].append(f"{ch.name}: unexpected sheet shape ({err!r})")
    party_file = snapshot_dir(ch) / "party.json"
    before = {}
    if party_file.exists():
        try:
            entries = load_snapshot(party_file)
            if not isinstance(entries, list) or not all(
                isinstance(p, dict) and _PARTY_KEYS <= p.keys() for p in entries
            ):
                raise SnapshotError(
                    f"{party_file}: not a list of party entries "
                    "(remake it with `ddtools party <dir> --json`)"
                )
            before = {p["id"]: p for p in entries}
        except SnapshotError as err:
            result["errors"].append(f"{ch.name}: {err}")
    for member in ch.campaign.get("party") or []:
        if member.get("status") == "gone":
            continue
        if not member.get("dndbeyond_id"):
            result["errors"].append(f"{member['name']}: no dndbeyond_id in the party list")
            continue
        try:
            now = party_entry(fetch(member["dndbeyond_id"]))
        except DndBeyondError as err:
            result["errors"].append(f"{member['name']}: {err}")
            continue
        except _BAD_SHAPE as err:
            result["errors"].append(f"{member['name']}: unexpected sheet shape ({err!r})")
            continue
        was = before.get(now["id"])
        if was is None or (was["name"], was["level"], was["classes"]) != (
            now["name"], now["level"], now["classes"],
        ):  # fmt: skip
            result["party"].append({"name": member["name"], "before": was, "after": now})
    return result


def issue_markdown(result: WatchResult) -> tuple[str, str]:
    """Title and body for the GitHub issue raised when a watch finds changes."""
    name, folder = result["character"], result["dir"]
    lines = [f"The daily D&D Beyond check found changes for **{name}**.", ""]
    own = result.get("own")
    if own:
        lines += ["## Their sheet", ""]
        if own["level"]:
            lines.append(f"- Level: {own['level'][0]} → {own['level'][1]}")
        if own["classes"]:
            lines.append(f"- Classes now: {', '.join(class_label(c) for c in own['classes'][1])}")
        spell_diffs: list[tuple[str, Literal["spells_added", "spells_removed"]]] = [
            ("Spells added", "spells_added"),
            ("Spells removed", "spells_removed"),
        ]
        for label, key in spell_diffs:
            for src, names in own[key].items():
                lines.append(f"- {label} ({src}): {', '.join(names)}")
        for list_key in LIST_DIFFS:
            if own[list_key]:
                text = ", ".join(own[list_key])
                lines.append(f"- {list_key.replace('_', ' ').capitalize()}: {text}")
        for k, (a, b) in own["stats"].items():
            lines.append(f"- {k}: {a} → {b}")
        if own["hp_base"]:
            lines.append(f"- Base HP: {own['hp_base'][0]} → {own['hp_base'][1]}")
        lines.append("")
    if result.get("gold") and (own or result["party"]):
        gold = ", ".join(f"{k} {a} → {b}" for k, (a, b) in result["gold"].items())
        lines += [f"Gold (for information): {gold}", ""]
    if result["party"]:
        lines += ["## Party", ""]
        for p in result["party"]:
            was = p["before"]
            now = p["after"]
            if was is None:
                lines.append(f"- {p['name']}: new to the baseline, level {now['level']}")
            else:
                lines.append(
                    f"- {p['name']}: level {was['level']} → {now['level']} "
                    f"({', '.join(now['classes'])})"
                )
        lines.append("")
    if own and own["level"]:
        lines += ["## Level-up checklist", ""] + [f"- [ ] {i}" for i in LEVELUP_CHECKLIST] + [""]
    lines += [
        "## Start an update session",
        "",
        "Paste this into Claude Code in the repo:",
        "",
        "```",
        f"Run `ddtools fetch {folder}` and `ddtools diff {folder}`, update {name}'s documents",
        "per the checklist (and the party's levels if they changed), run `ddtools build`,",
        "`ddtools check`, `ddtools preview`, and `ddtools golden update` if content changed",
        "intentionally, then open a PR whose body says `Closes #<this issue>`.",
        "```",
    ]
    return f"D&D Beyond changes: {name}", "\n".join(lines) + "\n"
