# Contributing

## Issues

- Search existing issues before opening a new one.
- Use the provided templates for bug reports and feature requests.

## Pull Requests

- Fork the repo and create your branch from `master`.
- Keep PRs focused: one change per PR.
- Write the test first, then the change (`pytest`).
- Tests use made-up characters and `tests/fixtures/`. Never a real character, and never a
  call to D&D Beyond.
- `ruff check .` and `ruff format --check .` must be clean.
- A change to `ddtools.pdfstyle` changes every campaign's PDFs: say so in the PR.
- Update `README.md` and `CHANGELOG.md` if needed.

## Code Style

- Follow the `.editorconfig` settings (LF line endings, UTF-8, trailing newline).
- Python 3.12+, and British English in anything a player reads.
