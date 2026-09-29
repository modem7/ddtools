# CLAUDE.md

Read this at the start of every session in this repo.

## What this is

D&D characters and their documents: for each character, a personal guide (player
only), a party handout (shared with the party), a DM brief (DM only) and the party
workbook, built with `ddtools` (installed from `requirements.txt`). Run the commands
yourself (`ddtools summary`, `ddtools check`, …) rather than telling the user to.

Every command and playbook: `ddtools --help`, and the `ddtools` README
(https://github.com/modem7/ddtools).

## First session in a new copy of this repo ("set up this repo")

1. `pip install -r requirements.txt`.
2. `ddtools init . --owner <their GitHub name>`: it fills in the owner-specific files
   and keeps everything that's already there. Open a PR with the result.
3. Ask for their character's name and campaign, then
   `ddtools new-character "<Name>" --new-campaign "<Campaign>"`.
4. `ddtools workbook <dir>`: they fill it in (on screen or on paper).
5. `ddtools import-workbook <filled.pdf> <dir>`: it fills in their D&D Beyond id. Then
   `ddtools fetch <dir>` (the sheet must be Public) and write the documents (below).

## Rules that bind every change

- **Decisions are binding.** `<Character>/notes/decisions.md` records every choice the
  player made and why. Don't undo one without asking. Add new decisions there.
- **Follow the blueprints.** `ddtools blueprints` lists them and `ddtools blueprints <name>`
  prints one. Read `ddtools blueprints README` before writing.
- **Secrets never reach the party.** Anything in `secrets.txt`, or anything hinting at
  it, stays out of `audience: party` documents: examples, catchphrases, jokes and
  out-of-character notes included. Add a secret to `secrets.txt` when you write it.
  Examples in shared documents use a made-up character.
- **Spells match the sheet.** Check `ddtools summary <dir>` before writing about
  abilities. Anything not on the sheet is labelled with the level it arrives
  ("at level 4") or sits under "Coming Soon". `ddtools check` enforces this for
  party documents.
- **Formatting:** A4 via `ddtools.pdfstyle`; a TL;DR or summary first; the same
  structure in every section; short sentences; one idea per bullet; tables instead of
  long paragraphs; bold key words; explain jargon once. Page count is not a target.
  Never write inside a shared document why it is laid out this way.
- **Don't invent what the DM decides.** Unconfirmed rules are working assumptions,
  marked as such. Unknown names and amounts are `[placeholders]` listed under "Blanks".
- **Rules & Rulings come from `character.yaml`** (`campaign.rules`); quote the DM's
  words in `notes/rulings.md`.

## Before handing over any document

1. `ddtools build <dir>` and `ddtools check <dir>` (must pass).
2. `ddtools preview <dir>` and look at every page image.
3. Reread party documents as a teammate would, hunting for hints.
4. `ddtools golden check <dir>`. If it differs, work out whether the change was
   intended. Intended: `ddtools golden update <dir>` and commit it with the change. Not
   intended: fix the cause, never the baseline.

## Git

- Never push to the default branch: branch and open a PR.
- D&D Beyond is read-only: `ddtools` only reads public character sheets.
