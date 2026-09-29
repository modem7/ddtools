"""``ddtools init``: make a folder a campaign repo, filled in for its owner.

The files come from ``ddtools/repo_template`` (dotfiles are stored as ``dot-<name>``).
Owner-specific values are filled in: CODEOWNERS, the autoassign assignee, the issue
templates, the security link, ``settings.yml`` and the licence. FUNDING is written only
with ``--funding``, and ``_extends: .github`` only with ``--extends``. A file that
already exists is never overwritten, so running it again only fills what's missing.
"""

from __future__ import annotations

import re
from datetime import date
from importlib.resources import files
from pathlib import Path

from ddtools import __version__


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


def init_repo(dest: Path | str, owner: str, name: str | None = None, *, public: bool = False,
              template: bool = False, extends: bool = False,
              funding: str | None = None) -> tuple[list[str], list[str]]:  # fmt: skip
    """Write the campaign repo's files into ``dest``. Returns (created, kept)."""
    dest = Path(dest)
    name = name or dest.resolve().name
    values = {
        "OWNER": owner,
        "NAME": name,
        "YEAR": str(date.today().year),
        "DDTOOLS_VERSION": __version__,
        "PRIVATE": "false" if public else "true",
        "TEMPLATE": "  is_template: true\n" if template else "",
        "EXTENDS": "_extends: .github\n" if extends else "",
        # modem7's shared Renovate preset for modem7's repos; Renovate's own for anyone else.
        "RENOVATE_PRESET": "github>modem7/renovate-config" if owner == "modem7"
        else "config:recommended",
    }  # fmt: skip
    wanted = dict(_template_files())
    if funding:
        wanted[".github/FUNDING.yml"] = f"buy_me_a_coffee: {funding}\n"
    created, kept = [], []
    for rel, text in sorted(wanted.items()):
        target = dest / rel
        if target.exists():
            kept.append(rel)
            continue
        for key, value in values.items():
            text = text.replace("{{" + key + "}}", value)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        created.append(rel)
    return created, kept
