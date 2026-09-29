# ddtools

Build and check D&D character documents from a D&D Beyond sheet.

## TL;DR

- Each character gets a **personal guide** (player only), a **party handout** (safe to
  share), a **DM brief** (DM only) and a **party workbook** (a fillable PDF).
- They're built from Python scripts into A4 PDFs, then **checked**:
  - **spoilers:** nothing from the character's `secrets.txt` reaches a party document;
  - **spells:** nothing the character can't cast yet, unless it's labelled with its level;
  - **layout:** golden baselines catch drift.
- It reads D&D Beyond (read-only) and never writes to it.
- **Want a campaign repo?** Use the template:
  [dnd-campaign-template](https://github.com/modem7/dnd-campaign-template). Its README
  walks you through it, with or without Claude.

## Install

Python 3.12 or later, and DejaVu fonts (`sudo apt-get install fonts-dejavu-core`).

```bash
pip install "ddtools @ git+https://github.com/modem7/ddtools.git@v0.2.0"
ddtools --version
```

Every command has `--help`. Commands that report data take `--json`.

## Start a campaign repo

1. `ddtools init my-campaign --owner <your GitHub name>`: the repo's files, filled in for
   you (see **`ddtools init`** below).
2. `cd my-campaign`, then `ddtools new-character "Name" --new-campaign "Campaign"`.
3. Set `dndbeyond_id` in `Name/character.yaml`, make the character **Public** on D&D
   Beyond, and run `ddtools fetch Name`.
4. `ddtools workbook Name`: fill in the PDF, then `ddtools import-workbook filled.pdf Name`.
5. Write the documents (`ddtools blueprints` says what each one holds), then
   `ddtools build Name` and `ddtools check Name`.

## Commands

### Build and check

| Command | What it does |
|---|---|
| `ddtools build <dir> [--out DIR]` | Runs each document script listed in `<dir>/character.yaml`. Writes the PDFs (and a `.txt` copy of each) to `<dir>/pdf/`, or to `--out`. Stops at the first failing script, names it and prints its error. |
| `ddtools check <dir>` | Checks every `audience: party` document. **Spoilers:** any entry from `secrets.txt`, ignoring case and curly quotes, even if it's split across lines. **Spells:** any spell not on the latest snapshot, unless its sentence has a level label ("at level 4", "(level 8+)"), it sits under a `future_sections` heading, or it's in `spell_ignore`. Exits 1 if it finds anything. |
| `ddtools preview <dir> [--pdf NAME] [--pages A-B]` | Renders pages to `tmp/preview-<name>.png` so the layout can be checked by eye. |
| `ddtools golden update <dir>` | Rebuilds and records a new golden baseline in `tests/golden/<dir>/`. Only use it when a change was intended, and commit it with that change. |
| `ddtools golden check <dir>` | Rebuilds and compares with the baseline. Exits 1 on any difference. |
| `ddtools golden capture <dir> --from-committed` | Records a baseline from the PDFs already in `<dir>/pdf/`, without rebuilding. |

### D&D Beyond

Characters must be set to **Public** on D&D Beyond (Character Settings → Character
Privacy).

| Command | What it does |
|---|---|
| `ddtools fetch <dir>` | Saves the sheet to `<dir>/snapshots/YYYY-MM-DD.json`. With a bare id or URL, it prints the sheet instead. |
| `ddtools summary <dir \| id \| url>` | Shows level, classes, stats, spells by source, options, feats, magic items and gold. Use it to check that the documents match the sheet. |
| `ddtools party <dir>` | Fetches every party member live, with name, level and classes. |
| `ddtools diff <dir> [old new]` | Shows what changed between the two latest snapshots, with the level-up checklist when the level changed. |
| `ddtools watch [dirs…] [--issue-dir DIR]` | Compares live sheets (the character's and the party's) with the committed snapshots and `party.json`. Exits 0 for no changes, 3 for changes, 1 for an error. Gold and consumables don't count as changes. |
| `ddtools sheet-text <dir>` | Writes the text for the sheet's description and notes fields to `<dir>/notes/dndbeyond-text.md`, from `<dir>/dndbeyond.yaml`. Allies come from the party list. Says which fields need pasting, lists `[blanks]`, and shows where the live sheet gives a secret away. Refuses, writing nothing, if the new text would give one away or a detail is over 50 characters. |

### Characters and campaigns

| Command | What it does |
|---|---|
| `ddtools new-character "Name" --new-campaign "Campaign"` | Creates `Name/` (spaces become underscores) with `character.yaml`, `secrets.txt`, notes and starter build scripts for every document. |
| `ddtools new-character "Name" --campaign-from <dir>` | The same, copying the campaign (facts, rules, party) from a character in the same campaign. The new character is dropped from their own party list. |
| `ddtools workbook <dir>` | Builds the party workbook: a fillable PDF each player fills in about their character. What's specific to the campaign comes from `character.yaml` (`campaign.facts`, `campaign.workbook`, `party_summary`). |
| `ddtools import-workbook <pdf> <dir>` | Reads a filled workbook: every answer goes into `notes/sources/workbook-answers.md`, and blanks in `character.yaml` (D&D Beyond id, class summary) are filled. Never overwrites: differences are listed. |
| `ddtools blueprints [name]` | Lists the blueprints, or prints one: what each document contains, and the rules learned so far. |
| `ddtools retire <dir> --reason death\|tpk\|retired\|campaign-end [--note "…"]` | Marks the character retired and writes `RETIRED.md` (unrevealed secrets, open DM questions). Moves the folder to `archive/`. |
| `ddtools list [--json]` | Lists active and archived characters. |
| `ddtools init <dir> --owner NAME [--name --public --template --extends --funding HANDLE]` | Makes a folder a campaign repo (see below). Safe to re-run: it never touches a file someone edited, and lists what it left alone. |

### `ddtools init`

It writes a campaign repo, filled in for its owner:

| File | What |
|---|---|
| `CLAUDE.md`, `README.md` | How to work in the repo, for people and for Claude |
| `requirements.txt` | `ddtools`, pinned to this version (Renovate proposes updates) |
| `.github/workflows/ci.yml` | Build, check and golden-compare every active character; secret scan |
| `.github/workflows/dndbeyond-watch.yml` | A daily `ddtools watch` that opens an issue when a sheet changes |
| `.github/` | Settings, CODEOWNERS, issue and PR templates, auto-assign |
| Others | `renovate.json`, `.editorconfig`, `.gitattributes`, `.gitignore`, `.claude/settings.json`, MIT licence, CONTRIBUTING |

It records what it was run with in `.ddtools-init.yaml`. Run it again with other values
(say, on your copy of the template repo) and it updates the files still exactly as it
wrote them, removes ones no longer wanted (FUNDING without `--funding`), and keeps
anything you edited.

Options: `--public` (default private), `--template` (a GitHub template repository),
`--extends` (`settings.yml` extends your `.github` repo), `--funding HANDLE` (a Buy Me a
Coffee link).

## A character's folder

| Path | What |
|---|---|
| `character.yaml` | Name, level, D&D Beyond id, the campaign (facts, rules, party) and the documents to build |
| `secrets.txt` | Words that must never reach the party. One per line; case-insensitive, whole words; `"quoted"` for an exact match |
| `src/` | One build script per document, using `ddtools.pdfstyle` |
| `notes/` | Decisions, rulings, open questions, sources |
| `snapshots/` | D&D Beyond sheets (`ddtools fetch`) and `party.json` |
| `pdf/` | The built documents |

## Playbooks

### Level-up

Usually triggered by the daily watch's `dndbeyond-sync` issue.

1. `ddtools fetch <dir>`, then `ddtools diff <dir>`: read the checklist it prints.
2. Update the cheat sheet (current level only), the handout's "What They Can Do for You
   Right Now" and "Coming Soon", the DM brief's numbers and level plan, and the guide's
   level table.
3. Bump `level` and `updated` in `character.yaml`.
4. If the party's levels changed, also run
   `ddtools party <dir> --json > <dir>/snapshots/party.json`.
5. Run **Before sending a document**, then open a PR whose body says `Closes #<issue>`.

### New DM ruling

1. Add it to `campaign.rules` in `character.yaml` (`status: confirmed` or `open`; use
   `show_in` to keep a row out of a document), and quote the DM in `notes/rulings.md`.
2. Update any section that relied on the old assumption (search the `.txt` copies).
3. Run **Before sending a document**.

### When the party changes

1. Someone leaves: set their `status: gone` in `campaign.party`. They drop off the
   workbook, the allies text and `watch`.
2. Someone joins: add them to `campaign.party` with their `dndbeyond_id`, then run
   `ddtools party <dir> --json > <dir>/snapshots/party.json`.
3. Update the documents that name teammates, then run **Before sending a document**.

### Character death or TPK

1. `ddtools retire <dir> --reason death --note "How it happened"`.
2. Read `archive/<dir>/RETIRED.md`: unrevealed secrets and open questions are story
   threads the next character can pick up.
3. `ddtools new-character "New Name" --campaign-from archive/<dir>` (same campaign).
4. Set `dndbeyond_id`, run `ddtools fetch`, and write the documents following the
   blueprints (`ddtools blueprints`).
5. Tell the party: their handouts and the workbook may mention the old character.

### New campaign

1. `ddtools new-character "Name" --new-campaign "Campaign"`.
2. Fill in `campaign.facts`, `campaign.rules` and `campaign.party` in `character.yaml`, and
   put the DM's campaign guide in `reference/`.
3. For the workbook, fill in `campaign.workbook` (who it's for, the campaign line, what's
   not allowed, an example place, combat notes), then `ddtools workbook <dir>`.

### D&D Beyond text

The party can read the D&D Beyond sheet, so its description and notes follow the same
rules as a party document.

1. Change the text in `<dir>/dndbeyond.yaml`. A new teammate needs a line under `allies:`.
2. `ddtools fetch <dir>`, so the comparison uses today's sheet.
3. `ddtools sheet-text <dir>`. If it refuses, it names the field and the word: reword it.
4. Open `<dir>/notes/dndbeyond-text.md`. Paste each field marked **needs updating** or
   **missing** into D&D Beyond (Description tab, then Notes). Leave the rest.
5. Done when: `ddtools fetch <dir>`, then `ddtools sheet-text <dir>`, shows every field as
   **up to date** or **leave as is**.

### Before sending a document

1. `ddtools build <dir>` and `ddtools check <dir>`.
2. `ddtools preview <dir>`, and look at every page.
3. Reread every party document as a teammate would: could anything hint at a secret?
4. If the change was intended, run `ddtools golden update <dir>` and commit it with the
   change.

## Plugins

A campaign repo can add its own commands and D&D Beyond text blocks with a small package
of its own. Register a module in the `ddtools.plugins` entry-point group:

```toml
[project.entry-points."ddtools.plugins"]
my_plugin = "my_plugin.plugin"
```

```python
def register(api):
    def configure(parser):
        parser.add_argument("dir")

    @api.command("weather", "Today's weather for the party.", configure)
    def weather(args):
        print("Sunny")
        return 0

    # Fills {{weather}} in dndbeyond.yaml's text fields.
    api.sheet_text_block("weather", lambda ch, names: "Sunny, for " + ", ".join(names))
```

A plugin that fails to load prints one warning and is skipped; `ddtools` still runs.
Unknown top-level keys in `character.yaml` are kept in `Character.extra` for plugins.

## Development

```bash
pip install -r requirements-dev.txt
pytest
ruff check . && ruff format --check .
```

- Tests use made-up characters (`tests/conftest.py`) and `tests/fixtures/`. They never
  call D&D Beyond.
- `ddtools.pdfstyle` values set the look of every document; changing one changes every
  campaign's PDFs, and their golden tests will say so.
- To release: bump `__version__` in `src/ddtools/__init__.py`, add a `CHANGELOG.md`
  section, merge, then push the tag `vX.Y.Z`. The release workflow checks the tag matches
  and publishes the GitHub release.

## Licence

MIT. See [LICENSE](LICENSE).
