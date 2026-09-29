"""Run a character's build scripts to produce its PDFs."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from ddtools.config import load_character
from ddtools.textdump import write_text_copy


class BuildError(Exception):
    """A build script failed. ``script`` is its path, ``stderr`` its error output."""

    def __init__(self, script: Path, stderr: str):
        super().__init__(f"Build failed in {script}")
        self.script = script
        self.stderr = stderr


def build_character(dir: Path, out: Path | None = None) -> list[Path]:
    """Run every document script in order; stop at the first failure.

    PDFs go to ``out`` (default ``<dir>/pdf``), each with a ``.txt`` text copy.
    """
    ch = load_character(dir)
    # Scripts run with cwd=src/, so a relative --out must be resolved here.
    out_dir = Path(out).resolve() if out else ch.dir / "pdf"
    env = {**os.environ, "DDTOOLS_CHARACTER_DIR": str(ch.dir), "DDTOOLS_OUT": str(out_dir)}
    built = []
    for doc in ch.documents:
        # "ddtools:<name>" is a document ddtools builds itself (e.g. ddtools:workbook).
        if doc.script.startswith("ddtools:"):
            script = Path(doc.script)
            cmd, cwd = [sys.executable, "-m", f"ddtools.{doc.script.split(':', 1)[1]}"], ch.dir
        else:
            script = ch.dir / doc.script
            cmd, cwd = [sys.executable, str(script)], script.parent
        pdf = out_dir / Path(doc.file).name
        before = pdf.stat().st_mtime_ns if pdf.exists() else None
        run = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
        )
        if run.returncode != 0:
            raise BuildError(script, run.stderr.strip() or run.stdout.strip())
        if not pdf.exists() or pdf.stat().st_mtime_ns == before:
            raise BuildError(
                script,
                f"The script finished but did not write {pdf}. Check that the file name it "
                f"builds matches `{doc.file}` in character.yaml.",
            )
        write_text_copy(pdf)
        built.append(pdf)
    return built
