# Blueprint: party workbook

Built by `ddtools workbook <dir>` (or `script: ddtools:workbook` in `character.yaml`)
from the campaign: the party still in it, `campaign.facts`, and `campaign.workbook`
(audience, campaign_line, battlefield, not_allowed, example_place, combat_notes). A
filled one comes back with `ddtools import-workbook <pdf> <dir>`.

## Purpose and audience

A blank, fillable workbook (`audience: party`) that lets every other player produce
their own guide, handout and DM brief with Claude. Typeable on screen (form fields)
and printable (ruled boxes).

## Never include

- Any real character's secrets. **All examples use a made-up character** who isn't in
  the party (the workbook uses Mossy Thistlewick, a gnome Circle of Spores druid).
- Mentions of why it is laid out the way it is.
- Tools or add-ons that weren't actually used to make the documents.

## Sections

- [h2] The Short Version
  Title, "how this works in 3 steps", ground rules (nothing required, bullets are
  fine, any order, "help me with this" is a valid answer), then the minimum three
  things.
- [h2] Progress Tracker
  Tick boxes for every section, with time estimates; skipping counts.
- [h1] 1. The Basics
  Name, player, class line, D&D Beyond link, and how to set the character to Public.
- [h1] 2. The One-Line Pitch
  Formulas and an example.
- [h1] 3. Backstory
  Paste as-is; what the party knows vs secrets.
- [h1] 4. What You Want From Your Character
  Tick boxes for combat role and "I find these hard".
- [h1] 5. Build & Levelling
- [h1] 6. Skills & What You're Good At
- [h1] 7. Personality & Voice
  Includes the "modes" idea.
- [h1] 8. The People in Your Life
- [h1] 9. You and the Party
  The party table with D&D Beyond links, and one box per teammate.
- [h1] 10. Running Gags & Side Projects
- [h1] 11. In Combat
  Includes the party's recurring battlefield.
- [h1] 12. Hooks, Secrets & Limits
- [h1] 13. Questions for the DM
- [h2] Campaign Facts (so Claude gets them right)
  From `campaign.facts`.
- [h1] 14. Hand It to Claude
- [h2] First: What Claude Needs (one time, 2 minutes)
  Public sheet, web search, file creation, the campaign guide.
- [h2] Then: Paste the Prompt
  The main prompt, including the build rules and layout rules as plain instructions.
- [h2] One More: All Three PDFs at Once
  Personal guide, party handout (no hints) and DM brief.
- [h2] Useful Follow-Ups

## Rules learned

- Every section follows the same pattern: time estimate, when it's fine to skip,
  one-line "why", prompts, boxes, one example.
- Also apply every rule in [README.md](README.md).

## QA checklist

- [ ] `ddtools check <dir>` passes (the workbook is a party document).
- [ ] No real character appears in any example.
- [ ] Party links are current (`ddtools party <dir>`).
