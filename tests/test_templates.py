"""A freshly scaffolded character builds, and its documents follow the blueprints."""

import json
import re
from importlib.resources import files
from pathlib import Path

import pytest

from ddtools.build import build_character
from ddtools.config import load_character
from ddtools.golden import normalise
from ddtools.lifecycle import new_character
from ddtools.textdump import page_texts

FIX = Path(__file__).parent / "fixtures"
BLUEPRINT_DIR = Path(str(files("ddtools") / "blueprints"))
BLUEPRINTS = {"build_guide.py": "personal-guide", "build_party_handout.py": "party-handout",
              "build_dm_brief.py": "dm-brief"}  # fmt: skip


def blueprint_headings(name: str) -> list[str]:
    text = (BLUEPRINT_DIR / f"{name}.md").read_text(encoding="utf-8")
    sections = text.split("## Sections", 1)[1].split("\n## ", 1)[0]
    return re.findall(r"^- \[h[12]\] (.+)$", sections, re.M)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("repo")
    d = new_character("Mossy Thistlewick", root, new_campaign="Test Campaign")
    build_character(d)
    return load_character(d)


@pytest.mark.parametrize("script", sorted(BLUEPRINTS))
def test_template_follows_blueprint(built, script):
    doc = next(d for d in built.documents if d.script == f"src/{script}")
    text = normalise(" ".join(page_texts(built.dir / doc.file)))
    pos = 0
    for heading in blueprint_headings(BLUEPRINTS[script]):
        found = text.find(heading, pos)
        assert found != -1, f"'{heading}' missing or out of order in {doc.file}"
        pos = found + len(heading)


def test_new_character_documents_pass_checks(built):
    from ddtools.checks import run_checks

    snap = built.dir / "snapshots" / "2026-01-01.json"
    snap.write_text((FIX / "ddb_min.json").read_text())
    assert run_checks(built) == []
    json.loads(snap.read_text())
