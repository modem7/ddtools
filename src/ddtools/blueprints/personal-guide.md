# Blueprint: personal guide

## Purpose and audience

The player's own playbook: how the build works, what to do on each turn, how to
level, and above all **how to play the character**, especially in party scenes,
which is where players most often get stuck. Only the player reads it
(`audience: private`), so it may contain every secret.

## Never include

- Anything that would be embarrassing if it leaked *and* isn't needed to play: the
  guide is still a file that can be shared by accident. Secrets are fine; other
  players' private information is not.
- Material from outside the campaign's allowed sources (check `campaign.facts`).

## Sections

- [h2] TL;DR
  A table: current level and classes, next level's picks, the path after that, role,
  feats, table rules, the one rule that makes the build work (e.g. "Every long rest,
  swap your spells before breakfast").
- [h1] Combat Cheat Sheet
  Its own printable page(s), starting on a new page, for the **current** level only.
  A stats grid (AC, HP, DC/attack, speed, slots and when they return, daily abilities),
  then any environment warning box (e.g. "the ship's deck is wooden: no fire").
- [h2] On Your Turn
  Action / bonus action / reaction table: pick, numbers, when to use it.
- [h2] Where You're Fighting
  One row per recurring battlefield (e.g. a ship: below deck, the main deck, the rigging,
  boarding).
- [h2] Support & Emergencies
  Ally down, you're in trouble, special enemy types; then a "Next level adds" box.
- [h1] Part 1 — Where You Are Now
  Stats table with notes on what changes at the next proficiency bump.
- [h2] Attack Options
  Cantrips/attacks table with damage now and at the next scaling level.
- [h2] Spells and Resources
  Every spell known, from which pool, and how often it comes back. Explain unusual
  racial or feature spells (Mossy: her Circle of Spores features).
- [h2] Reactions & Passives
  One reaction per round; which to use when.
- [h2] Items You Have
  Items, attunement, effect; attunement slots left.
- [h1] Part 2 — Table Rules & Your Resources
  The campaign's rest and house rules as they affect this build, and any routine the
  build depends on (e.g. a nightly routine, a weekly cycle, costs, expected yield, and
  "running it without table friction").
- [h2] Your Table's Rules
  Confirmed rulings, and working assumptions marked as such.
- [h2] Your Routine
  Step-by-step, in the order it has to happen.
- [h1] Part 3 — Path to Level 10
  The build the player chose (e.g. a published build guide), with your own recommendations
  where they differ, and why.
- [h2] Next Level Picks
  Every choice at the next level: pick and reason.
- [h2] Level Plan
  Level-by-level table of new spells/features with reasons.
- [h2] Feats
  Chosen feats and alternatives, with trade-offs.
- [h1] Part 4 — Items & Attunement
  Wishlist with verdicts; which items are worth the last attunement slot.
- [h1] Part 5 — How to Play Them
  Intro box: the one-line concept (Mossy: "A royal food-taster who survived, and now
  tastes everything the dungeon grows").
- [h2] Their Story in One Breath
  One paragraph.
- [h2] Setting Details for Role-Play
  Lore that gives the player things to *do* or *say* (Mossy: the royal kitchens' crest,
  and Lord Hallowmere's name).
- [h2] Personality
  Traits, ideals, bonds, flaws, secret.
- [h2] Voice
  Situation → line table, including combat lines. Label lines for spells not yet known.
- [h2] The People in Their Life
  NPCs: who, what they are to the character, how to play them.
- [h2] At the Table: Build as Character
  Each mechanic explained as fiction.
- [h2] Their Arc
  Stages, and what pushes each one.
- [h1] Part 6 — Them and the Party
  The part players struggle with most: give them a system.
- [h2] The Modes
  Two or three modes, when each shows up, what it sounds like (Mossy: The Critic,
  The Forager, The Taster). State the golden rule (the rare mode stays rare).
- [h2] Stuck? Pick a Move
  Go-to moves for any scene.
- [h2] Common Party Situations
  Situation → what the character does.
- [h2] When Someone Dies
  Teammates in stages (down, not getting up, after, brought back, stays dead,
  funeral) and NPCs (enemy, stranger, patient, employee, key NPCs), plus the aftermath
  and an at-the-table note that a character death is that player's moment first.
- [h2] The Teammates
  Per teammate: who they are to the character, how to play it. Mark unknown
  backstories as "still to come".
- [h2] Party Tactics
  What the character does **now**, then what arrives with each level; combos.
- [h2] Fighting Where You Live
  The party's recurring battlefield (e.g. the party's ship), marked as the long-term
  plan with a pointer back to the cheat sheet.
- [h2] Table Etiquette
  How to keep the character's bits fun for everyone.
- [h1] Part 7 — Running Gag
  A recurring bit with real detail (Mossy: star ratings for every meal, with her
  scoring rules, the worst-ever list, and what each teammate's cooking earns).
- [h1] Part 8 — Side Project
  Downtime activity (Mossy: "dungeon-safe" mushroom jerky: recipes, stock, customers,
  rivals). No invented income: that's the DM's.
- [h1] Part 9 — DM Notes
  Starts on a new page so it can be handed over on its own.
- [h2] At a Glance
- [h2] Key NPCs
- [h2] Arc
- [h2] Hooks
  Grouped by theme (patron/god, past, party, side project).
- [h2] Rules & Rulings
  Generated from `campaign.rules`.

## Rules learned

- The cheat sheet is for the **current** level and is updated at every level-up
  (see `ddtools diff` checklist).
- The build's source (e.g. a forum build) is followed, but your recommendations
  override it where you have reasons, and the reasons are written down.
- Damage/support priorities come from the player, not from what the class is
  "supposed" to do.
- Also apply every rule in [README.md](README.md).

## QA checklist

- [ ] Every spell on the cheat sheet and in Part 1 is on the sheet (`ddtools summary`).
- [ ] Future spells are labelled with their level everywhere else.
- [ ] Voice lines and catchphrases don't use words from `secrets.txt` that the party could
      hear at the table (a character with a secret alias never says it aloud).
- [ ] Rules & Rulings matches `character.yaml`.
- [ ] Cheat sheet prints on its own pages; Part 9 starts on a new page.
