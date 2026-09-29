# Changelog

## 0.2.0

The first public release.

- **Commands:** `build`, `check`, `preview`, `golden` (`update`, `check`, `capture`),
  `fetch`, `summary`, `party`, `diff`, `watch`, `sheet-text`, `new-character`, `retire`,
  `list`.
- **New:** `ddtools workbook` builds the party workbook for any campaign, from
  `character.yaml`. Form fields have stable, versioned names (`v1.s<section>.<label>`).
- **New:** `ddtools import-workbook` reads a filled workbook into the notes and fills
  blanks in `character.yaml`. It never overwrites.
- **New:** `ddtools blueprints` prints what each document contains, and the rules learned
  so far.
- **New:** `ddtools init` makes a folder a campaign repo, filled in for its owner. Run on
  a copy of the template repo, it makes the copy yours: files still exactly as the
  template had them follow your name; anything edited is kept.
- **New:** plugins. The `ddtools.plugins` entry-point group can add commands and
  D&D Beyond text blocks.
- New characters get the party workbook, and the character template ships inside the
  package.
