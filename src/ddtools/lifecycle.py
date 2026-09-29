"""Create, retire and list characters."""

from __future__ import annotations

import shutil
import unicodedata
from datetime import date
from pathlib import Path

import yaml

from ddtools.config import FILENAME, Character, character_dirs, load_character, save_character

TEMPLATE = Path(__file__).resolve().parent / "character_template"
REASONS = ("death", "tpk", "retired", "campaign-end")


def slugify(name: str) -> str:
    """Folder name for a character: ASCII, apostrophes dropped, other gaps → ``_``."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    ascii_name = ascii_name.replace("'", "")
    slug = "".join(c if c.isalnum() else "_" for c in ascii_name)
    slug = "_".join(part for part in slug.split("_") if part)
    if not slug:
        raise ValueError(f"Can't make a folder name from {name!r}")
    return slug


def new_character(
    name: str,
    root: Path,
    campaign_from: Path | None = None,
    new_campaign: str | None = None,
) -> Path:
    """Scaffold ``<root>/<slug>/`` from the template. Give exactly one campaign source."""
    if (campaign_from is None) == (new_campaign is None):
        raise ValueError("Give exactly one of campaign_from or new_campaign")
    name = " ".join(name.split())
    slug = slugify(name)
    dest = Path(root) / slug
    if dest.exists():
        raise FileExistsError(f"{dest} already exists")
    if campaign_from is not None:
        campaign = load_character(campaign_from).campaign
        campaign = {**campaign, "party": [
            p for p in campaign.get("party") or [] if p.get("name") != name
        ]}  # fmt: skip
    else:
        campaign = {"name": new_campaign, "setting": "", "facts": [], "rules": [], "party": []}

    shutil.copytree(TEMPLATE, dest, ignore=shutil.ignore_patterns("__pycache__"))
    try:
        for empty in ("snapshots", "notes/sources"):  # kept in git by an empty .gitkeep
            (dest / empty).mkdir(parents=True, exist_ok=True)
            (dest / empty / ".gitkeep").touch()
        readme = dest / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8").replace("__NAME__", name).replace("__SLUG__", slug),
            encoding="utf-8",
        )
        # Only the slug goes into the YAML as text (it's always [A-Za-z0-9_]); the name is
        # set on the parsed data so ':', '#', quotes or "No" can't break or retype it.
        cfg = dest / FILENAME
        data = yaml.safe_load(cfg.read_text(encoding="utf-8").replace("__SLUG__", slug))
        data.update(name=name, updated=date.today(), campaign=campaign)
        cfg.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100), encoding="utf-8"
        )
        load_character(dest)  # validate what we wrote
    except BaseException:
        shutil.rmtree(dest, ignore_errors=True)
        raise
    return dest


def _retired_note(ch: Character, reason: str, note: str) -> str:
    secrets = []
    if ch.secrets_path.exists():
        secrets = [
            line.strip()
            for line in ch.secrets_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
    open_rules = [r["text"] for r in ch.campaign.get("rules") or [] if r.get("status") == "open"]
    dm_docs = [d.file for d in ch.documents if d.audience == "dm"]
    lines = [
        f"# {ch.name}: retired",
        "",
        f"- **Date:** {date.today().isoformat()}",
        f"- **Reason:** {reason}",
        f"- **Final level:** {ch.level} ({ch.class_summary})",
        f"- **Campaign:** {ch.campaign.get('name', '')}",
    ]
    if note:
        lines.append(f"- **Note:** {note}")
    lines += ["", "## Threads that could carry into the next character's story", ""]
    lines += ["Secrets that were never revealed:", ""]
    lines += [f"- {s}" for s in secrets] or ["- (none recorded)"]
    lines += ["", "Open DM questions:", ""]
    lines += [f"- {r}" for r in open_rules] or ["- (none)"]
    if dm_docs:
        lines += ["", f"The hooks themselves are in the DM brief: {', '.join(dm_docs)}."]
    return "\n".join(lines) + "\n"


def retire(dir: Path, reason: str, note: str, root: Path) -> Path:
    """Mark a character retired, write ``RETIRED.md`` and move them to ``<root>/archive/``."""
    if reason not in REASONS:
        raise ValueError(f"reason must be one of {', '.join(REASONS)}")
    ch = load_character(dir)
    dest = Path(root) / "archive" / Path(dir).name
    if dest.exists():
        raise FileExistsError(f"{dest} already exists")
    ch.status = "retired"
    ch.retired = {"date": date.today(), "reason": reason, "note": note}
    save_character(ch)
    (ch.dir / "RETIRED.md").write_text(_retired_note(ch, reason, note), encoding="utf-8")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(ch.dir), dest)
    return dest


def list_characters(root: Path) -> list[Character]:
    """Active characters under ``root`` and retired ones under ``root/archive``."""
    return [load_character(d) for d in character_dirs(root, include_archive=True)]
