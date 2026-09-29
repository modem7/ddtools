import textwrap

import pytest

from ddtools.build import BuildError, build_character
from ddtools.cli import main

GOOD = textwrap.dedent(
    """
    from ddtools.config import load_character, output_path, stamp
    from ddtools.pdfstyle import P, build, h1

    CH = load_character()
    build([P("Hello", h1)], output_path(CH, "Doc.pdf"), stamp(CH))
    """
)


def _character(tmp_path, script_body):
    d = tmp_path / "Test_Hero"
    (d / "src").mkdir(parents=True)
    (d / "src" / "build_doc.py").write_text(script_body, encoding="utf-8")
    (d / "character.yaml").write_text(
        "name: Test Hero\nlevel: 2\nupdated: 2026-09-28\ndocuments:\n"
        "  - {file: pdf/Doc.pdf, script: src/build_doc.py, audience: private}\n",
        encoding="utf-8",
    )
    return d


def test_build_writes_pdf_and_text(tmp_path):
    d = _character(tmp_path, GOOD)
    out = build_character(d)
    assert out == [d / "pdf" / "Doc.pdf"]
    assert (d / "pdf" / "Doc.txt").exists()


def test_build_to_other_dir(tmp_path):
    d = _character(tmp_path, GOOD)
    out = build_character(d, tmp_path / "elsewhere")
    assert out == [tmp_path / "elsewhere" / "Doc.pdf"]
    assert not (d / "pdf").exists()


def test_failing_script_raises(tmp_path):
    d = _character(tmp_path, "raise RuntimeError('boom in script')\n")
    with pytest.raises(BuildError) as exc:
        build_character(d)
    assert exc.value.script.name == "build_doc.py"
    assert "boom in script" in exc.value.stderr


def test_cli_build_failure_exit_code(tmp_path, capsys):
    d = _character(tmp_path, "raise RuntimeError('boom in script')\n")
    assert main(["build", str(d)]) == 1
    out = capsys.readouterr().out
    assert "Build failed in" in out and "boom in script" in out


def test_script_that_writes_nothing_is_an_error(tmp_path):
    d = _character(tmp_path, "print('forgot to build')\n")
    (d / "pdf").mkdir()
    (d / "pdf" / "Doc.pdf").write_bytes(b"%PDF-stale")
    with pytest.raises(BuildError) as exc:
        build_character(d)
    assert "did not write" in exc.value.stderr and "Doc.pdf" in exc.value.stderr


def test_relative_out_dir(tmp_path, monkeypatch):
    d = _character(tmp_path, GOOD)
    monkeypatch.chdir(tmp_path)
    out = build_character(d, "rel/out")
    assert out == [(tmp_path / "rel" / "out" / "Doc.pdf").resolve()]
    assert out[0].exists() and not (d / "src" / "rel").exists()
