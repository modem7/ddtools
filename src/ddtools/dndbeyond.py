"""Read-only access to D&D Beyond character sheets: fetch, summarise, diff, watch.

Characters must be set to Public on D&D Beyond for the character service to return them.
"""

from __future__ import annotations

import http.client
import json
import re
import urllib.error
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

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


class DndBeyondError(Exception):
    """A sheet could not be fetched. The message says which character and why."""


def parse_id(text: str) -> int:
    """A character id from a bare number or any ``dndbeyond.com/characters/<id>`` URL."""
    text = str(text).strip()
    if text.isdigit():
        return int(text)
    m = re.search(r"dndbeyond\.com/characters/(\d+)", text)
    if not m:
        raise ValueError(f"Not a D&D Beyond character id or URL: {text!r}")
    return int(m.group(1))


def fetch_character(char_id: int, timeout: float = 20) -> dict:
    """Fetch a character's sheet JSON (the ``data`` object)."""
    req = Request(API.format(id=char_id), headers={"User-Agent": "ddtools/0.1"})
    try:
        with urlopen(req, timeout=timeout) as resp:
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


def snapshot_dir(ch) -> Path:
    return Path(ch.dir) / "snapshots"


def save_snapshot(ch, data: dict, today: str | None = None) -> Path:
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


def latest_snapshots(ch, n: int = 2) -> list[Path]:
    """The newest ``n`` character snapshots, oldest first (``party.json`` excluded)."""
    files = [
        p
        for p in snapshot_dir(ch).glob("*.json")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}(-\d+)?", p.stem)
    ]
    return sorted(files, key=_snapshot_key)[-n:]


def _names(entries) -> list[str]:
    return sorted(
        e["definition"]["name"]
        for e in entries or []
        if isinstance(e, dict) and e.get("definition")
    )


def _stats(data: dict) -> dict[str, int]:
    def by_id(key):
        return {s["id"]: s.get("value") for s in data.get(key) or []}

    base, bonus, override = by_id("stats"), by_id("bonusStats"), by_id("overrideStats")
    mods = [m for group in (data.get("modifiers") or {}).values() for m in group or []]
    out = {}
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


def summarise(data: dict) -> dict:
    """The parts of a sheet the documents depend on, in a stable, comparable shape."""
    classes = [
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
    items = sorted(
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


def class_label(c: dict) -> str:
    """``Warlock 2 (The Fiend)`` from a summarised class entry."""
    return f"{c['name']} {c['level']}" + (f" ({c['subclass']})" if c["subclass"] else "")


def party_entry(data: dict) -> dict:
    s = summarise(data)
    return {
        "id": data.get("id"),
        "name": s["name"],
        "level": s["level"],
        "classes": [class_label(c) for c in s["classes"]],
        # As the player typed it on the sheet; the ledger maps it to pronouns.
        "gender": (data.get("data", data).get("gender") or "").strip() or None,
    }


def _list_diff(old: list, new: list) -> tuple[list, list]:
    return sorted(set(new) - set(old)), sorted(set(old) - set(new))


def diff(old: dict, new: dict) -> dict:
    """What changed between two sheets. Unchanged parts are empty (or ``None``)."""
    a, b = summarise(old), summarise(new)
    out: dict = {"level": (a["level"], b["level"]) if a["level"] != b["level"] else None}
    out["classes"] = (a["classes"], b["classes"]) if a["classes"] != b["classes"] else None
    added, removed = {}, {}
    for src in sorted(set(a["spells"]) | set(b["spells"])):
        plus, minus = _list_diff(a["spells"].get(src, []), b["spells"].get(src, []))
        if plus:
            added[src] = plus
        if minus:
            removed[src] = minus
    out["spells_added"], out["spells_removed"] = added, removed
    out["options_added"], out["options_removed"] = _list_diff(a["options"], b["options"])
    out["feats_added"], out["feats_removed"] = _list_diff(a["feats"], b["feats"])
    magic_a = {i["name"]: i for i in a["items"] if i["magic"]}
    magic_b = {i["name"]: i for i in b["items"] if i["magic"]}
    out["items_added"], out["items_removed"] = _list_diff(list(magic_a), list(magic_b))
    out["attunement_changed"] = sorted(
        n
        for n in set(magic_a) & set(magic_b)
        if (magic_a[n]["attuned"], magic_a[n]["equipped"])
        != (magic_b[n]["attuned"], magic_b[n]["equipped"])
    )
    out["stats"] = {
        k: (a["stats"][k], b["stats"][k]) for k in ABILITIES if a["stats"][k] != b["stats"][k]
    }
    out["hp_base"] = (a["hp_base"], b["hp_base"]) if a["hp_base"] != b["hp_base"] else None
    out["gold"] = {
        k: (a["gold"].get(k, 0), b["gold"].get(k, 0))
        for k in ("pp", "gp", "ep", "sp", "cp")
        if a["gold"].get(k, 0) != b["gold"].get(k, 0)
    }
    return out


# ---- watch ---------------------------------------------------------------

MEANINGFUL = (
    "level", "classes", "spells_added", "spells_removed", "options_added", "options_removed",
    "feats_added", "feats_removed", "items_added", "items_removed", "attunement_changed",
    "stats", "hp_base",
)  # fmt: skip


def is_meaningful(d: dict) -> bool:
    """True if a diff has anything beyond gold/consumables worth an update session."""
    return any(d.get(k) for k in MEANINGFUL)


def watch_character(ch, fetch=None) -> dict:
    """Compare live sheets with the committed baselines for one character and its party."""
    fetch = fetch or fetch_character
    result: dict = {"character": ch.name, "dir": Path(ch.dir).name, "own": None, "party": []}
    result["errors"] = []
    snaps = latest_snapshots(ch, 1)
    if ch.dndbeyond_id:
        try:
            live = fetch(ch.dndbeyond_id)
            if snaps:
                d = diff(json.loads(snaps[-1].read_text(encoding="utf-8")), live)
                result["own"] = d if is_meaningful(d) else None
                result["gold"] = d["gold"]
            else:
                result["errors"].append(f"{ch.name}: no committed snapshot to compare against")
        except DndBeyondError as err:
            result["errors"].append(f"{ch.name}: {err}")
    party_file = snapshot_dir(ch) / "party.json"
    before = {}
    if party_file.exists():
        before = {p["id"]: p for p in json.loads(party_file.read_text(encoding="utf-8"))}
    for member in ch.campaign.get("party") or []:
        if member.get("status") == "gone":
            continue
        try:
            now = party_entry(fetch(member["dndbeyond_id"]))
        except DndBeyondError as err:
            result["errors"].append(f"{member['name']}: {err}")
            continue
        was = before.get(now["id"])
        if was is None or (was["name"], was["level"], was["classes"]) != (
            now["name"], now["level"], now["classes"],
        ):  # fmt: skip
            result["party"].append({"name": member["name"], "before": was, "after": now})
    return result


def issue_markdown(result: dict) -> tuple[str, str]:
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
        for label, key in [("Spells added", "spells_added"), ("Spells removed", "spells_removed")]:
            for src, names in own[key].items():
                lines.append(f"- {label} ({src}): {', '.join(names)}")
        for key in MEANINGFUL[4:11]:
            if own[key]:
                lines.append(f"- {key.replace('_', ' ').capitalize()}: {', '.join(own[key])}")
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
