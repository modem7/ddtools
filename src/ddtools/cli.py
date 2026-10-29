"""Command-line entry point. Subcommands register themselves via ``command``.

The commands live in ``ddtools.registry``; ``command`` and ``unregister`` are its
helpers, re-exported here. This module parses arguments and dispatches; the output
of summary, diff and watch is in ``ddtools.report``, and golden's in ``ddtools.golden``.
"""

from __future__ import annotations

import argparse

from ddtools import __version__, plugins
from ddtools.registry import COMMANDS, Configure, Handler, command, unregister
from ddtools.report import print_json as _print_json

__all__ = ["Configure", "Handler", "build_parser", "command", "main", "unregister"]


def build_parser() -> argparse.ArgumentParser:
    import sys

    for warning in plugins.load():
        print(f"warning: {warning}", file=sys.stderr)
    parser = argparse.ArgumentParser(
        prog="ddtools", description="Build and check D&D character documents."
    )
    parser.add_argument("--version", action="version", version=f"ddtools {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    for cmd in COMMANDS:
        p = sub.add_parser(cmd.name, help=cmd.help, description=cmd.help)
        cmd.configure(p)
        p.set_defaults(func=cmd.fn)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args)


def _page_range(text: str | None) -> range | None:
    """Parse ``A-B`` or ``A`` (1-based, inclusive) into a 0-based range."""
    if not text:
        return None
    first, _, last = text.partition("-")
    return range(int(first) - 1, int(last or first))


def _preview_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("dir", help="character folder (its PDFs are in <dir>/pdf)")
    p.add_argument("--pdf", help="only this PDF (file name, with or without .pdf)")
    p.add_argument("--pages", help="page range, e.g. 2-3 (default: all pages)")


@command("preview", "Render PDF pages to a contact-sheet PNG in tmp/.", _preview_args)
def cmd_preview(args: argparse.Namespace) -> int:
    from pathlib import Path

    from ddtools.preview import contact_sheet

    pdfs = sorted((Path(args.dir) / "pdf").glob("*.pdf"))
    if args.pdf:
        want = args.pdf.removesuffix(".pdf")
        pdfs = [p for p in pdfs if p.stem == want]
    if not pdfs:
        print(f"No matching PDFs in {Path(args.dir) / 'pdf'}")
        return 1
    for pdf in pdfs:
        out = Path.cwd() / "tmp" / f"preview-{pdf.stem}.png"
        print(contact_sheet(pdf, out, pages=_page_range(args.pages)))
    return 0


def _golden_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "action",
        choices=["capture", "update", "check"],
        help="capture or update a baseline, or check a rebuild against it",
    )
    p.add_argument("dir", help="character folder")
    p.add_argument(
        "--from-committed",
        action="store_true",
        help="capture from the PDFs already in <dir>/pdf instead of rebuilding",
    )


@command("golden", "Record golden baselines for a character's documents.", _golden_args)
def cmd_golden(args: argparse.Namespace) -> int:
    from pathlib import Path

    from ddtools import golden
    from ddtools.config import load_character
    from ddtools.errors import DdtoolsError

    try:
        ch = load_character(args.dir)
    except DdtoolsError as err:
        print(err)
        return 1
    dest = Path.cwd() / "tests" / "golden" / ch.dir.name
    if args.action == "check":
        return golden.check_character(ch, dest)
    if args.action == "capture" and not args.from_committed:
        print("`golden capture` needs --from-committed (use `golden update` to rebuild first).")
        return 2
    return golden.record_character(ch, dest, rebuild=args.action == "update")


def _build_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("dir", help="character folder")
    p.add_argument("--out", help="write PDFs here instead of <dir>/pdf")


@command("build", "Build a character's PDFs (and .txt copies) from its scripts.", _build_args)
def cmd_build(args: argparse.Namespace) -> int:
    from ddtools.build import BuildError, build_character
    from ddtools.errors import DdtoolsError
    from ddtools.preview import page_count

    try:
        for pdf in build_character(args.dir, args.out):
            print(f"{pdf}  ({page_count(pdf)} pages)")
    except BuildError as err:
        print(f"Build failed in {err.script}:\n{err.stderr}")
        return 1
    except DdtoolsError as err:
        print(err)
        return 1
    return 0


# ---- D&D Beyond ----------------------------------------------------------


def _target_args(p: argparse.ArgumentParser, json_flag: bool = True) -> None:
    p.add_argument("target", help="character folder, D&D Beyond id or URL")
    if json_flag:
        p.add_argument("--json", action="store_true", help="machine-readable output")


def _dir_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("dir", help="character folder")
    p.add_argument("--json", action="store_true", help="machine-readable output")


def _is_dir(target: str) -> bool:
    from pathlib import Path

    return (Path(target) / "character.yaml").is_file()


@command(
    "fetch",
    "Download a D&D Beyond sheet (into <dir>/snapshots/, or to stdout).",
    lambda p: _target_args(p, False),
)
def cmd_fetch(args: argparse.Namespace) -> int:
    from ddtools import dndbeyond as ddb
    from ddtools.config import load_character
    from ddtools.errors import DdtoolsError

    try:
        if _is_dir(args.target):
            ch = load_character(args.target)
            if not ch.dndbeyond_id:
                print(f"{ch.dir / 'character.yaml'}: no dndbeyond_id set")
                return 1
            print(ddb.save_snapshot(ch, ddb.fetch_character(ch.dndbeyond_id)))
        else:
            _print_json(ddb.fetch_character(ddb.parse_id(args.target)))
    except DdtoolsError as err:
        print(err)
        return 1
    return 0


@command("summary", "Summarise a sheet: level, stats, spells by source, items, gold.", _target_args)
def cmd_summary(args: argparse.Namespace) -> int:
    from ddtools import dndbeyond as ddb
    from ddtools.config import load_character
    from ddtools.errors import DdtoolsError
    from ddtools.report import format_summary

    try:
        if _is_dir(args.target):
            snaps = ddb.latest_snapshots(load_character(args.target), 1)
            if not snaps:
                print(f"No snapshots yet: run `ddtools fetch {args.target}` first.")
                return 1
            data = ddb.load_snapshot(snaps[-1])
        else:
            data = ddb.fetch_character(ddb.parse_id(args.target))
    except DdtoolsError as err:
        print(err)
        return 1
    s = ddb.summarise(data)
    _print_json(s) if args.json else print(format_summary(s))
    return 0


@command("party", "Fetch every party member live: name, level, classes.", _dir_args)
def cmd_party(args: argparse.Namespace) -> int:
    from ddtools import dndbeyond as ddb
    from ddtools.config import load_character
    from ddtools.errors import DdtoolsError

    try:
        ch = load_character(args.dir)
    except DdtoolsError as err:
        print(err)
        return 1
    members = [p for p in ch.campaign.get("party") or [] if p.get("status") != "gone"]
    no_id = [p["name"] for p in members if not p.get("dndbeyond_id")]
    if no_id:
        print(f"{ch.dir / 'character.yaml'}: no dndbeyond_id for {', '.join(no_id)}")
        return 1
    rows = []
    for member in members:
        try:
            rows.append(ddb.party_entry(ddb.fetch_character(member["dndbeyond_id"])))
        except ddb.DndBeyondError as err:
            print(f"{member['name']}: {err}")
            return 1
    if args.json:
        _print_json(rows)
    else:
        for r in rows:
            print(f"{r['name']}: level {r['level']} — {', '.join(r['classes'])}")
    return 0


def _diff_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("dir", help="character folder")
    p.add_argument("files", nargs="*", help="two snapshot files to compare (default: latest two)")
    p.add_argument("--json", action="store_true", help="machine-readable output")


@command(
    "diff", "What changed between the two latest snapshots (+ level-up checklist).", _diff_args
)
def cmd_diff(args: argparse.Namespace) -> int:
    from pathlib import Path

    from ddtools import dndbeyond as ddb
    from ddtools.config import load_character
    from ddtools.errors import DdtoolsError
    from ddtools.report import diff_report

    try:
        files = [Path(f) for f in args.files] or ddb.latest_snapshots(load_character(args.dir))
        if len(files) < 2:
            print(f"Need two snapshots to compare: run `ddtools fetch {args.dir}` first.")
            return 1
        old, new = (ddb.load_snapshot(f) for f in files[-2:])
    except DdtoolsError as err:
        print(err)
        return 1
    d = ddb.diff(old, new)
    _print_json(d) if args.json else print(diff_report(files[-2].name, files[-1].name, d))
    return 0


def _watch_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("dirs", nargs="*", help="character folders (default: every active character)")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--issue-dir", help="write <folder>.md issue text per changed character here")


@command(
    "watch",
    "Compare live D&D Beyond sheets with committed snapshots. Exit 0 none, 3 changes, 1 error.",
    _watch_args,
)
def cmd_watch(args: argparse.Namespace) -> int:
    from ddtools.report import run_watch

    return run_watch(args.dirs, as_json=args.json, issue_dir=args.issue_dir)


def _check_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("dir", help="character folder")
    p.add_argument("--pdf-dir", help="check the PDFs in this folder instead of <dir>/pdf")


@command(
    "check",
    "Check party documents for spoilers and spells not on the sheet. Exit 1 on problems.",
    _check_args,
)
def cmd_check(args: argparse.Namespace) -> int:
    from ddtools.checks import run_checks
    from ddtools.config import load_character
    from ddtools.errors import DdtoolsError

    try:
        problems = run_checks(load_character(args.dir), pdf_dir=args.pdf_dir)
    except DdtoolsError as err:
        print(err)
        return 1
    for p in problems:
        print(p)
    if not problems:
        print("No problems found in party documents.")
    return 1 if problems else 0


# ---- lifecycle -----------------------------------------------------------


def _new_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("name", help='character name, e.g. "Mossy Thistlewick"')
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--campaign-from", help="existing character folder in the same campaign")
    src.add_argument("--new-campaign", help="name of a new campaign")


@command("new-character", "Create a character folder from the templates.", _new_args)
def cmd_new_character(args: argparse.Namespace) -> int:
    from pathlib import Path

    from ddtools.errors import DdtoolsError
    from ddtools.lifecycle import new_character

    try:
        d = new_character(
            args.name,
            Path.cwd(),
            campaign_from=Path(args.campaign_from) if args.campaign_from else None,
            new_campaign=args.new_campaign,
        )
    except DdtoolsError as err:
        print(err)
        return 1
    print(f"Created {d}. Next: set dndbeyond_id in {d.name}/character.yaml, then `ddtools fetch`.")
    return 0


def _retire_args(p: argparse.ArgumentParser) -> None:
    from ddtools.lifecycle import REASONS

    p.add_argument("dir", help="character folder")
    p.add_argument("--reason", required=True, choices=REASONS)
    p.add_argument("--note", default="", help="a line for the record, e.g. how they died")


@command("retire", "Retire a character: write RETIRED.md and move them to archive/.", _retire_args)
def cmd_retire(args: argparse.Namespace) -> int:
    from pathlib import Path

    from ddtools.errors import DdtoolsError
    from ddtools.lifecycle import retire

    try:
        dest = retire(Path(args.dir), args.reason, args.note, Path.cwd())
    except (DdtoolsError, OSError) as err:  # OSError: a failed write or move, rolled back
        print(err)
        return 1
    print(f"Retired to {dest}. Read {dest / 'RETIRED.md'} for threads to carry forward.")
    return 0


@command(
    "list",
    "List active and archived characters.",
    lambda p: p.add_argument("--json", action="store_true", help="machine-readable output"),
)
def cmd_list(args: argparse.Namespace) -> int:
    from pathlib import Path

    from ddtools.errors import DdtoolsError
    from ddtools.lifecycle import list_characters

    root = Path.cwd()
    try:
        chars = list_characters(root)
    except DdtoolsError as err:
        print(err)
        return 1
    rows = [
        {
            "name": c.name,
            "dir": c.dir.relative_to(root.resolve()).as_posix(),
            "level": c.level,
            "campaign": c.campaign.get("name", ""),
            "status": c.status,
        }
        for c in chars
    ]
    if args.json:
        _print_json(rows)
    else:
        for r in rows:
            print(f"{r['name']:<24} level {r['level']:<3} {r['status']:<8} {r['campaign']}")
    return 0


def _sheet_text_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("dir", help="character folder (its text is in <dir>/dndbeyond.yaml)")


@command(
    "sheet-text",
    "Write the D&D Beyond description and notes text (to notes/dndbeyond-text.md).",
    _sheet_text_args,
)
def cmd_sheet_text(args: argparse.Namespace) -> int:
    from ddtools import sheettext as T
    from ddtools.config import load_character
    from ddtools.errors import DdtoolsError

    try:
        ch = load_character(args.dir)
        rep = T.report(ch)
    except DdtoolsError as err:
        print(err)
        return 1
    if rep["problems"]:
        print("Not written, fix these in " + T.SOURCE_FILE + " first:\n  "
              + "\n  ".join(rep["problems"]))  # fmt: skip
        return 1
    path = T.write(ch, rep)
    for f in rep["fields"]:
        leak = f" (live sheet leaks: {', '.join(f['live_secrets'])})" if f["live_secrets"] else ""
        print(f"{f['label']}: {f['status']}{leak}")
    for name in rep["missing_allies"]:
        print(f"warning: no Allies line for {name}")
    print(f"Wrote {path}")
    return 0


def _workbook_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("dir", help="character folder (the campaign is in its character.yaml)")


@command("workbook", "Build the party workbook (a fillable PDF) from the campaign.", _workbook_args)
def cmd_workbook(args: argparse.Namespace) -> int:
    from ddtools.config import load_character
    from ddtools.errors import DdtoolsError
    from ddtools.textdump import write_text_copy

    try:
        from ddtools.workbook import build_workbook  # registers the fonts, so can raise

        ch = load_character(args.dir)
        out = build_workbook(ch)
    except DdtoolsError as err:
        print(err)
        return 1
    write_text_copy(out)
    print(f"Wrote {out}")
    return 0


def _import_workbook_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("pdf", help="the filled-in workbook PDF")
    p.add_argument("dir", help="character folder")


@command(
    "import-workbook",
    "Read a filled workbook into the notes, and fill blanks in character.yaml.",
    _import_workbook_args,
)
def cmd_import_workbook(args: argparse.Namespace) -> int:
    from pathlib import Path

    from ddtools.errors import DdtoolsError
    from ddtools.workbook_import import import_workbook

    try:
        got = import_workbook(Path(args.pdf), Path(args.dir))
    except (DdtoolsError, OSError) as err:  # OSError: a failed write, already rolled back
        print(err)
        return 1
    print(f"Wrote {got['answers']}")
    for line in got["filled"]:
        print(f"Filled in character.yaml: {line}")
    for line in got["differences"]:
        print(f"Left alone (check it): {line}")
    if got["blank"]:
        print(f"Still blank ({len(got['blank'])}): " + "; ".join(got["blank"]))
    return 0


def _blueprints_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("name", nargs="?", help="a blueprint (e.g. party-handout); none lists them")


@command("blueprints", "List the document blueprints, or print one.", _blueprints_args)
def cmd_blueprints(args: argparse.Namespace) -> int:
    from importlib.resources import files

    folder = files("ddtools") / "blueprints"
    names = sorted(p.name[:-3] for p in folder.iterdir() if p.name.endswith(".md"))
    if not args.name:
        print("\n".join(names))
        return 0
    name = args.name.removesuffix(".md")
    if name not in names:
        print(f"No blueprint called {name}. There are: {', '.join(names)}")
        return 1
    print((folder / f"{name}.md").read_text(encoding="utf-8"))
    return 0


def _init_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("dir", help="the repo folder (created if missing)")
    p.add_argument("--owner", required=True, help="the GitHub user or organisation that owns it")
    p.add_argument("--name", help="the repo's name (default: the folder's name)")
    p.add_argument("--public", action="store_true", help="a public repo (default: private)")
    p.add_argument("--template", action="store_true", help="mark it a GitHub template repository")
    p.add_argument("--extends", action="store_true",
                   help="settings.yml extends the owner's .github repo")  # fmt: skip
    p.add_argument("--funding", help="a Buy Me a Coffee handle for FUNDING.yml")


@command("init", "Make a folder a campaign repo, filled in for its owner.", _init_args)
def cmd_init(args: argparse.Namespace) -> int:
    from ddtools.init import init_repo

    done = init_repo(args.dir, args.owner, args.name, public=args.public,
                     template=args.template, extends=args.extends,
                     funding=args.funding)  # fmt: skip
    for rel in done["created"]:
        print(f"Created {rel}")
    for rel in done["updated"]:
        print(f"Updated {rel}")
    for rel in done["removed"]:
        print(f"Removed {rel}")
    for rel in done["kept"]:
        print(f"Kept {rel} (already there)")
    for rel in done["edited"]:
        print(f"Kept {rel} (edited)")
    return 0
