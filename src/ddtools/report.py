"""Text and JSON output for the D&D Beyond commands (summary, diff, watch).

``cli`` parses the arguments; this module turns the results into what is printed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ddtools.config import PathLike
    from ddtools.dndbeyond import SheetDiff, SheetSummary


def print_json(data: Any) -> None:
    """Print ``data`` as indented JSON (dates and paths as strings)."""
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def format_summary(s: SheetSummary) -> str:
    """The ``ddtools summary`` text for a sheet summary."""
    from ddtools.dndbeyond import class_label

    lines = [
        f"{s['name']}: level {s['level']}, base HP {s['hp_base']}",
        "Classes: " + ", ".join(class_label(c) for c in s["classes"]),
        "Stats: " + ", ".join(f"{k} {v}" for k, v in s["stats"].items()),
        "Spells:",
        *[f"  {src}: {', '.join(names)}" for src, names in s["spells"].items()],
        "Options: " + (", ".join(s["options"]) or "none"),
        "Feats: " + (", ".join(s["feats"]) or "none"),
        "Magic items: " + (", ".join(
            i["name"] + (" (attuned)" if i["attuned"] else "") for i in s["items"] if i["magic"]
        ) or "none"),
        "Gold: " + ", ".join(f"{v} {k}" for k, v in s["gold"].items() if v),
    ]  # fmt: skip
    return "\n".join(lines)


def format_diff(d: SheetDiff) -> list[str]:
    """One line per change in a ``dndbeyond.diff`` result; empty if nothing changed."""
    lines = []
    if d["level"]:
        lines.append(f"Level: {d['level'][0]} → {d['level'][1]}")
    for src, names in d["spells_added"].items():
        lines.append(f"Spells added ({src}): {', '.join(names)}")
    for src, names in d["spells_removed"].items():
        lines.append(f"Spells removed ({src}): {', '.join(names)}")
    for key, label in [
        ("options_added", "Options added"), ("options_removed", "Options removed"),
        ("feats_added", "Feats added"), ("feats_removed", "Feats removed"),
        ("items_added", "Magic items added"), ("items_removed", "Magic items removed"),
        ("attunement_changed", "Attunement/equipped changed"),
    ]:  # fmt: skip
        if d[key]:
            lines.append(f"{label}: {', '.join(d[key])}")
    for k, (a, b) in d["stats"].items():
        lines.append(f"{k}: {a} → {b}")
    if d["hp_base"]:
        lines.append(f"Base HP: {d['hp_base'][0]} → {d['hp_base'][1]}")
    if d["gold"]:
        lines.append("Gold: " + ", ".join(f"{k} {a} → {b}" for k, (a, b) in d["gold"].items()))
    return lines


def diff_report(old_name: str, new_name: str, d: SheetDiff) -> str:
    """The ``ddtools diff`` text: the two snapshot names, the changes, then a level-up checklist."""
    from ddtools.dndbeyond import LEVELUP_CHECKLIST

    lines = format_diff(d)
    out = [f"{old_name} → {new_name}", "\n".join(lines) if lines else "No changes."]
    if d["level"]:
        out.append("\nLevel-up checklist:")
        out.append("\n".join(f"  [ ] {item}" for item in LEVELUP_CHECKLIST))
    return "\n".join(out)


def run_watch(
    dirs: Sequence[PathLike], as_json: bool = False, issue_dir: PathLike | None = None
) -> int:
    """Compare live sheets with the snapshots and print (and write) what changed.

    ``dirs`` empty means every character under the current folder; only active ones
    are fetched. Errors go to stderr. Returns 0 for no changes, 3 for changes, 1 for
    any error (changes are still printed and written first).
    """
    from ddtools import dndbeyond as ddb
    from ddtools.config import character_dirs, load_character
    from ddtools.errors import DdtoolsError

    try:
        chars = [load_character(d) for d in (dirs or character_dirs(Path.cwd()))]
    except DdtoolsError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    chars = [c for c in chars if c.status == "active"]
    results = [ddb.watch_character(c) for c in chars]
    errors = [e for r in results for e in r["errors"]]
    changed = [r for r in results if r["own"] or r["party"]]
    if as_json:
        print_json(results)
    for r in changed:
        title, body = ddb.issue_markdown(r)
        if issue_dir:
            out = Path(issue_dir)
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{r['dir']}.md").write_text(f"{title}\n{body}", encoding="utf-8")
        if not as_json:
            print(f"{title}\n{body}")
    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    if errors:
        return 1
    if not changed and not as_json:
        print("No changes.")
    return 3 if changed else 0
