# Changelog

## Unreleased

- **Changed:** the runtime dependencies now have version bounds: at least the versions
  ddtools is tested with, and below the next major version.

  | Package | Range |
  |---|---|
  | pillow | `>=13.0.0,<14` |
  | pypdf | `>=6.21.4,<7` |
  | pypdfium2 | `>=5.14.0,<6` |
  | PyYAML | `>=6.0.3,<7` |
  | reportlab | `>=5.1.0,<6` |

- **Changed:** the text of `summary`, `diff` and `watch` is now made in `ddtools.report`,
  and `golden`'s capture and check runs are `ddtools.golden.record_character` and
  `check_character`. `cli.py` only parses and dispatches. The output is unchanged.

- **Changed:** the DejaVu fonts now come with the package, so `fonts-dejavu-core` no
  longer needs installing. `DDTOOLS_FONT_DIR` still overrides them.
- **Changed:** `retire` and `import-workbook` are all or nothing. If a write or the move
  fails, `character.yaml`, `RETIRED.md` and the answers file go back to how they were.
- **Changed:** ddtools' errors share one base, `ddtools.errors.DdtoolsError`. A missing
  character folder, a bad snapshot or baseline file, a party member with no name or
  `dndbeyond_id`, or a missing workbook PDF now gives a message naming the file, not a
  traceback. A party member's `name` must be text: write `name: "1984"` (or `"No"`) in
  quotes, or `load_character` reports which `campaign.party` entry is wrong.
- **Changed:** clearer names in `ddtools.config` for build scripts. The old names still
  work, so existing build scripts need no change.

  | Old | New |
  |---|---|
  | `stamp(ch)` | `level_updated_label(ch)` |
  | `date_stamp(ch)` | `updated_label(ch)` |
  | `present(ch, name)` | `is_present(ch, name)` |

- **New:** `ddtools.config.output_dir(ch)` gives the output folder without creating it.
  `output_path` still creates it.
- **Changed:** parameters called `dir` or `ch_dir` are now `char_dir`. This only matters
  if you pass them by keyword: `load_character`, `build_character`, `retire`,
  `import_workbook`, `set_top_level`, `set_party_fields`, `add_party_member` and
  `sheettext.load_source`.
- **Changed:** `ddtools.workbook` is split into one function per section. The workbook
  PDF is the same. `section_titles(ch)` gives the section titles without building it,
  and `ddtools.workbook_fields` has the field names (`field_key`, `section_of`) for the
  workbook and `import-workbook`. `field_key` now takes the section too:
  `field_key(section, label)`. It still imports from `ddtools.workbook`. `TITLES`,
  `VERSION`, `field`, `ticks`, `section` and `prompts` are gone from `ddtools.workbook`.
- **Fixed:** a plugin command named like a built-in one (say `build`) no longer stops
  every command with an argparse error. It is skipped with a warning, as is a name an
  earlier plugin already took. The first one wins, and the rest of the plugin loads.
  Before, a clash between two plugins was skipped without a word.
- **New:** `ddtools.registry` holds the command list. `Registry` has `register`,
  `unregister`, `lookup` and `reset`; `COMMANDS` is the one `ddtools` uses.
  `ddtools.cli.command` still works, and `ddtools.cli.unregister` removes a command.
  Registering a taken name directly raises `DuplicateCommandError`.
- **Changed:** `ddtools.plugins` no longer imports `ddtools.cli`. The private
  `ddtools.cli._COMMANDS` list is gone; use `ddtools.registry.COMMANDS`.
- **Changed:** `ddtools.sheettext.status` is now `field_status`. The old name still works.

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
