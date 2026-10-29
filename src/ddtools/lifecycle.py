"""Create, retire and list characters."""

from __future__ import annotations

import errno
import os
import shutil
import unicodedata
from datetime import date
from pathlib import Path

import yaml

from ddtools.config import (
    FILENAME,
    Character,
    PathLike,
    character_dirs,
    load_character,
    save_character,
)
from ddtools.errors import DdtoolsError
from ddtools.secrets import load_character_secrets

TEMPLATE = Path(__file__).resolve().parent / "character_template"
REASONS = ("death", "tpk", "retired", "campaign-end")


class LifecycleError(DdtoolsError, ValueError):
    """A bad name, campaign source or retire reason (also a ``ValueError``)."""


class CharacterExists(DdtoolsError, FileExistsError):
    """The folder a character would go to is already there (also a ``FileExistsError``)."""


def slugify(name: str) -> str:
    """Folder name for a character: ASCII, apostrophes dropped, other gaps → ``_``.

    Raises:
        LifecycleError: nothing usable is left of ``name``.
    """
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    ascii_name = ascii_name.replace("'", "")
    slug = "".join(c if c.isalnum() else "_" for c in ascii_name)
    slug = "_".join(part for part in slug.split("_") if part)
    if not slug:
        raise LifecycleError(f"Can't make a folder name from {name!r}")
    return slug


def new_character(
    name: str,
    root: PathLike,
    campaign_from: PathLike | None = None,
    new_campaign: str | None = None,
) -> Path:
    """Scaffold ``<root>/<slug>/`` from the template. Give exactly one campaign source.

    All or nothing: if anything fails after the copy, the new folder is removed.

    Raises:
        LifecycleError: not exactly one campaign source, or an unusable name.
        CharacterExists: ``<root>/<slug>`` is already there.
        ConfigError: ``campaign_from`` isn't a valid character folder.
    """
    if (campaign_from is None) == (new_campaign is None):
        raise LifecycleError("Give exactly one of campaign_from or new_campaign")
    name = " ".join(name.split())
    slug = slugify(name)
    dest = Path(root) / slug
    if dest.exists():
        raise CharacterExists(f"{dest} already exists")
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
    secrets = load_character_secrets(ch)
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
    lines += [f"- {s.text}" for s in secrets] or ["- (none recorded)"]
    lines += ["", "Open DM questions:", ""]
    lines += [f"- {r}" for r in open_rules] or ["- (none)"]
    if dm_docs:
        lines += ["", f"The hooks themselves are in the DM brief: {', '.join(dm_docs)}."]
    return "\n".join(lines) + "\n"


def retire(char_dir: PathLike, reason: str, note: str, root: PathLike) -> Path:
    """Mark a character retired, write ``RETIRED.md`` and move them to ``<root>/archive/``.

    All or nothing: if saving, writing or the move fails, ``character.yaml`` and
    ``RETIRED.md`` go back to how they were, a half-copied archive folder is removed, and
    the error is raised. The one gap: across filesystems the folder is copied, then the
    original deleted. If that delete fails, the complete archived copy is kept and the
    error is raised, so part of the original may be left to delete by hand.

    Raises:
        LifecycleError: ``reason`` isn't one of ``REASONS``.
        CharacterExists: ``<root>/archive/<folder>`` is already there.
        ConfigError: ``char_dir`` isn't a valid character folder.
    """
    if reason not in REASONS:
        raise LifecycleError(f"reason must be one of {', '.join(REASONS)}")
    ch = load_character(char_dir)
    dest = Path(root) / "archive" / Path(char_dir).name
    if dest.exists():
        raise CharacterExists(f"{dest} already exists")
    cfg, notes = ch.dir / FILENAME, ch.dir / "RETIRED.md"
    old_cfg = cfg.read_bytes()
    old_notes = notes.read_bytes() if notes.exists() else None
    ch.status = "retired"
    ch.retired = {"date": date.today(), "reason": reason, "note": note}
    text = _retired_note(ch, reason, note)  # everything is worked out before any write
    copied = False
    try:
        save_character(ch)
        notes.write_text(text, encoding="utf-8")
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.rename(ch.dir, dest)
        except OSError as err:
            if err.errno != errno.EXDEV:
                raise
            shutil.copytree(ch.dir, dest, symlinks=True)
            copied = True  # the archive is complete from here on
            shutil.rmtree(ch.dir)
    except BaseException:
        if not copied:
            shutil.rmtree(dest, ignore_errors=True)  # a half-made copy, if any
            cfg.write_bytes(old_cfg)
            if old_notes is None:
                notes.unlink(missing_ok=True)
            else:
                notes.write_bytes(old_notes)
        raise
    return dest


def list_characters(root: PathLike) -> list[Character]:
    """Active characters under ``root`` and retired ones under ``root/archive``."""
    return [load_character(d) for d in character_dirs(root, include_archive=True)]
