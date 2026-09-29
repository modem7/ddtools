"""``ddtools init``: make a folder a campaign repo, filled in for its owner.

The files come from ``ddtools/repo_template`` (dotfiles are stored as ``dot-<name>``).
Owner-specific values are filled in: CODEOWNERS, the autoassign assignee, the issue
templates, the security link, ``settings.yml`` and the licence. FUNDING is written only
with ``--funding``, and ``_extends: .github`` only with ``--extends``.

What it was run with is kept in ``.ddtools-init.yaml``. Run again with other values (a
friend's copy of the template repo, say), it replaces the files still exactly as it
wrote them, removes the ones no longer wanted, and never touches a file someone edited.
Missing files are always filled in.
"""

from __future__ import annotations

import re
from datetime import date
from importlib.resources import files
from pathlib import Path

import yaml

from ddtools import __version__

MARKER = ".ddtools-init.yaml"


def _template_files():
    root = files("ddtools") / "repo_template"
    stack = [(root, "")]
    while stack:
        folder, rel = stack.pop()
        for entry in folder.iterdir():
            name = re.sub(r"^dot-", ".", entry.name)
            path = f"{rel}{name}"
            if entry.is_dir():
                stack.append((entry, f"{path}/"))
            elif not entry.name.endswith((".pyc", ".pyo")):
                yield path, entry.read_text(encoding="utf-8")


def _render(opts: dict) -> dict[str, str]:
    """Every file ``init`` writes for these options, with its text."""
    values = {
        "OWNER": opts["owner"],
        "NAME": opts["name"],
        "YEAR": str(opts["year"]),
        "DDTOOLS_VERSION": opts["version"],
        "PRIVATE": "false" if opts["public"] else "true",
        "TEMPLATE": "  is_template: true\n" if opts["template"] else "",
        "EXTENDS": "_extends: .github\n" if opts["extends"] else "",
        # modem7's shared Renovate preset for modem7's repos; Renovate's own for anyone else.
        "RENOVATE_PRESET": "github>modem7/renovate-config" if opts["owner"] == "modem7"
        else "config:recommended",
    }  # fmt: skip
    out = {}
    for rel, text in _template_files():
        for key, value in values.items():
            text = text.replace("{{" + key + "}}", value)
        out[rel] = text
    if opts["funding"]:
        out[".github/FUNDING.yml"] = f"buy_me_a_coffee: {opts['funding']}\n"
    return out


def _previous(dest: Path) -> dict | None:
    try:
        old = yaml.safe_load((dest / MARKER).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    return old if isinstance(old, dict) else None


def init_repo(dest: Path | str, owner: str, name: str | None = None, *, public: bool = False,
              template: bool = False, extends: bool = False,
              funding: str | None = None) -> dict[str, list[str]]:  # fmt: skip
    """Write the campaign repo's files into ``dest``.

    Returns ``{created, updated, removed, kept, edited}``, each a list of paths: ``kept``
    were there before ``init`` ever ran, ``edited`` were changed since it last did.
    """
    dest = Path(dest)
    opts = {"owner": owner, "name": name or dest.resolve().name, "public": public,
            "template": template, "extends": extends, "funding": funding,
            "version": __version__, "year": date.today().year}  # fmt: skip
    wanted = _render(opts)
    old = _previous(dest)
    before = _render({**opts, **old}) if old else {}
    done: dict[str, list[str]] = {
        k: [] for k in ("created", "updated", "removed", "kept", "edited")
    }
    for rel in sorted(set(wanted) | set(before)):
        target = dest / rel
        text = wanted.get(rel)
        if not target.exists():
            if text is not None:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
                done["created"].append(rel)
            continue
        current = target.read_text(encoding="utf-8")
        if current == text:
            continue
        if rel in before and current == before[rel]:  # still exactly as init wrote it
            if text is None:
                target.unlink()
                done["removed"].append(rel)
            else:
                target.write_text(text, encoding="utf-8")
                done["updated"].append(rel)
        elif text is not None or rel in before:
            done["edited" if rel in before else "kept"].append(rel)
    (dest / MARKER).write_text(yaml.safe_dump(opts, sort_keys=False), encoding="utf-8")
    return done
