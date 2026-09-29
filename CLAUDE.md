# CLAUDE.md

`ddtools`: build and check D&D character documents from D&D Beyond sheets. Campaign repos
(made with `ddtools init`, or from
[dnd-campaign-template](https://github.com/modem7/dnd-campaign-template)) install it.
`README.md` has every command and the playbooks.

## Rules

- **TDD.** Write the failing test first. `pytest` and `ruff check . && ruff format --check .`
  must pass before any push.
- **Tests use made-up characters** (`tests/conftest.py`, `make_campaign`) and
  `tests/fixtures/`. Never a real character's sheet, secrets or names, and never a call
  to D&D Beyond.
- **D&D Beyond is read-only.**
- **`ddtools.pdfstyle` values** set every campaign's look; a change there changes every
  PDF.
- **`ddtools init` never overwrites** a file, and the template repo must match its output
  (CI checks this).
- **Releases:** bump `__version__`, add a `CHANGELOG.md` section, merge, then tag
  `vX.Y.Z`.
- Never push to `master`: branch and open a PR.
- British English; short sentences; tables over long paragraphs.
