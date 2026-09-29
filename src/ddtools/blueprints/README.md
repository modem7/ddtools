# Document blueprints

How to write each document type a character gets. Print one with
`ddtools blueprints <name>`; `ddtools blueprints` lists them. Examples use Mossy
Thistlewick, a made-up gnome Circle of Spores druid (a former royal food-taster), never a
real character.

| Blueprint | Audience | Template |
|---|---|---|
| [personal-guide.md](personal-guide.md) | the player only (`audience: private`) | `src/build_guide.py` from `ddtools new-character` |
| [party-handout.md](party-handout.md) | the whole party (`audience: party`) | `src/build_party_handout.py` from `ddtools new-character` |
| [dm-brief.md](dm-brief.md) | the DM only (`audience: dm`) | `src/build_dm_brief.py` from `ddtools new-character` |
| [party-workbook.md](party-workbook.md) | the whole party (`audience: party`) | built by `ddtools workbook` (`script: ddtools:workbook`) |

Each blueprint's `## Sections` list is machine-read: every line `- [h1] Heading`
or `- [h2] Heading` is a heading the template must contain, in that order
(ddtools' template tests check it). Guidance sits indented under each line.

## Rules for every document

These were learned the hard way on real documents. They apply everywhere.

**Layout and wording**

- A4, the shared `ddtools.pdfstyle` look, footer stamp from `character.yaml`.
- A TL;DR or short summary first. Clear headings and the same structure in every section.
- Short sentences. One idea per bullet. Tables instead of long paragraphs.
- Bold the key words. Explain jargon the first time it appears. British English.
- Never describe *why* the layout is like this inside a shared document; just follow the rules.
- Keep a page's heading with its content (`keepWithNext`), avoid a heading or one line
  stranded at the bottom of a page, and avoid big empty gaps. Tighten wording before
  adding pages. Page count is not a target: a new character has less to say, and the
  golden test's page count only flags that an existing document's layout moved.

**Accuracy**

- Spells and abilities must match the D&D Beyond sheet (`ddtools summary <dir>`).
  Anything the character doesn't have yet is labelled with the level they get it
  ("Scorching Ray at level 4", "(level 8+)") or sits in a "Coming Soon" section.
- Numbers (prices, rewards, damage) scale to the party's level and what they actually carry
  (`ddtools party <dir>`), and say that they rise with level.
- A rule the DM hasn't confirmed is a **working assumption**, marked as such, and goes
  on the DM's question list (`campaign.rules` with `status: open`).
- Don't invent what the DM decides (income, prices set by rolls, NPC names): leave a
  `[placeholder]` and list it under "Blanks for You to Fill".

**Secrets**

- Every secret goes in `secrets.txt`. `audience: party` documents must pass
  `ddtools check` — that includes the workbook.
- No hints either: examples, catchphrases, jokes, section titles and "out of
  character" notes must not point at a secret. (A catchphrase that is really a secret
  alias gives the alias away; a note that a character's cowardice "is just an act"
  gives away that they're secretly brave.)
- Examples in shared documents use a made-up character, never a party member.
- The party handout describes only what the party already knows (e.g. the short
  backstory they've read). The DM brief says explicitly what the party knows and
  what it doesn't.

## Before sending any document

1. `ddtools build <dir>` and `ddtools check <dir>`.
2. `ddtools preview <dir>` and look at **every** page.
3. Read the party documents as a teammate would: could anything hint at a secret?
4. If the change was intentional, `ddtools golden update <dir>` and commit it with the change.
