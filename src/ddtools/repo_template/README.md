# {{NAME}}

D&D characters and their campaign documents, built with
[ddtools](https://github.com/modem7/ddtools).

Each character gets a **personal guide** (player only), a **party handout** (safe to
share), a **DM brief** (DM only) and the **party workbook**. They're built from Python
scripts, checked for spoilers and for spells the character doesn't have yet, and compared
against golden baselines so layouts don't drift.

## Start here

1. Connect this repo to Claude (claude.ai/code), and say: **set up this repo**.
   Claude installs `ddtools`, fills in your GitHub name, and asks about your character.
2. Set your character to **Public** on D&D Beyond (Character Settings → Character
   Privacy), so `ddtools` can read the sheet.
3. Print or open the workbook Claude makes (`ddtools workbook`), and fill it in. Nothing
   is required: skip anything.
4. Give Claude the filled-in PDF and say: **import my workbook and write my documents**.
5. Read everything, ask for changes, and share only the party handout with your party.

## Doing it yourself

```bash
pip install -r requirements.txt
ddtools new-character "Name" --new-campaign "Campaign"
ddtools workbook Name
ddtools import-workbook filled.pdf Name
ddtools build Name && ddtools check Name
```

DejaVu fonts are required (`sudo apt-get install fonts-dejavu-core`). Every command:
`ddtools --help`.

## Layout

| Path | What |
|---|---|
| `<Character>/` | A character: `character.yaml`, build scripts in `src/`, notes, snapshots, PDFs |
| `archive/` | Retired characters (`ddtools retire`) |
| `tests/golden/` | Golden baselines (`ddtools golden update`) |
