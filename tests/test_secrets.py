from ddtools.config import load_character
from ddtools.secrets import Secret, load_character_secrets

CHARACTER = "name: Hero\nlevel: 1\nupdated: 2026-09-28\ncampaign: {}\ndocuments: []\n"


def _hero(tmp_path):
    d = tmp_path / "Hero"
    d.mkdir()
    (d / "character.yaml").write_text(CHARACTER, encoding="utf-8")
    return d


def test_a_missing_secrets_file_means_no_secrets(tmp_path):
    assert load_character_secrets(load_character(_hero(tmp_path))) == []


def test_a_folder_called_secrets_txt_is_not_read(tmp_path):
    d = _hero(tmp_path)
    (d / "secrets.txt").mkdir()
    assert load_character_secrets(load_character(d)) == []


def test_the_secrets_file_is_read(tmp_path):
    d = _hero(tmp_path)
    (d / "secrets.txt").write_text('# note\nSmuggler\n"Exact Name"\n', encoding="utf-8")
    assert load_character_secrets(load_character(d)) == [
        Secret("Smuggler", False),
        Secret("Exact Name", True),
    ]


def test_the_module_pulls_in_no_pdf_code():
    import subprocess
    import sys

    code = (
        "import sys, ddtools.secrets; "
        "print('pypdfium2' in sys.modules or 'reportlab' in sys.modules)"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"
