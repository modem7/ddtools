"""Run a character's build scripts to produce its PDFs."""

from __future__ import annotations

import os
import subprocess  # nosec B404 - running the character's own build scripts is the job
from pathlib import Path

from ddtools.config import PathLike, load_character
from ddtools.errors import DdtoolsError
from ddtools.textdump import write_text_copy


class BuildError(DdtoolsError):
    """A build script failed. ``script`` is its path, ``stderr`` its error output."""

    def __init__(self, script: Path, stderr: str):
        super().__init__(f"Build failed in {script}:\n{stderr}")
        self.script = script
        self.stderr = stderr


def build_character(char_dir: PathLike, out: PathLike | None = None) -> list[Path]:
    """Run every document script in order; stop at the first failure.

    PDFs go to ``out`` (default ``<char_dir>/pdf``), each with a ``.txt`` text copy.

    Raises:
        ConfigError: character.yaml is missing or invalid (from ``load_character``).
        BuildError: a script exits non-zero or does not write its PDF.
    """
    ch = load_character(char_dir)
    # Scripts run with cwd=src/, so a relative --out must be resolved here.
    out_dir = Path(out).resolve() if out else ch.dir / "pdf"
    env = {**os.environ, "DDTOOLS_CHARACTER_DIR": str(ch.dir), "DDTOOLS_OUT": str(out_dir)}
    built = []
    for doc in ch.documents:
        script, cmd, cwd = doc.command(ch.dir)
        pdf = out_dir / Path(doc.file).name
        pdf.unlink(missing_ok=True)
        run = subprocess.run(  # nosec B603 - an argument list, no shell
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
        )
        if run.returncode != 0:
            raise BuildError(script, run.stderr.strip() or run.stdout.strip())
        if not pdf.exists():
            raise BuildError(
                script,
                f"The script finished but did not write {pdf}. Check that the file name it "
                f"builds matches `{doc.file}` in character.yaml.",
            )
        write_text_copy(pdf)
        built.append(pdf)
    return built
