"""Starter personal guide: every section from the ddtools blueprint personal-guide.md.

Replace each guidance note with the real content. Keep the headings (or rename them
in the blueprint too) so the document keeps the shape of the others."""

from ddtools.config import load_character, output_path, rules_rows, stamp
from ddtools.pdfstyle import *

CH = load_character()


def todo(text):
    """A guidance note: what goes in this section. Delete it once written."""
    return box([P("<b>To write:</b> " + text, small)], bg=WARN_BG)


S = []
S.append(P(CH.name, title))
S.append(P(f"Personal guide · {CH.class_summary} · Level {CH.level}", sub))
S.append(P("TL;DR", h2))
S.append(
    todo(
        'A table: current level and classes, next level\'s picks, the path after that, role, feats, table rules, the one rule that makes the build work. e.g. "Every long rest, swap your spells before breakfast".'
    )
)
S.append(PageBreak())
S.append(P("Combat Cheat Sheet", h1))
S.append(
    todo(
        'Its own printable page(s), starting on a new page, for the **current** level only. A stats grid (AC, HP, DC/attack, speed, slots and when they return, daily abilities), then any environment warning box (e.g. "the ship\'s deck is wooden: no fire").'
    )
)
S.append(P("On Your Turn", h2))
S.append(todo("Action / bonus action / reaction table: pick, numbers, when to use it."))
S.append(P("Where You're Fighting", h2))
S.append(
    todo("One row per recurring battlefield (e.g. a ship: below deck, the main deck, the rigging).")
)
S.append(P("Support &amp; Emergencies", h2))
S.append(todo('Ally down, you\'re in trouble, special enemy types; then a "Next level adds" box.'))
S.append(PageBreak())
S.append(P("Part 1 — Where You Are Now", h1))
S.append(todo("Stats table with notes on what changes at the next proficiency bump."))
S.append(P("Attack Options", h2))
S.append(todo("Cantrips/attacks table with damage now and at the next scaling level."))
S.append(P("Spells and Resources", h2))
S.append(
    todo(
        "Every spell known, from which pool, and how often it comes back. Explain unusual racial or feature spells (Mossy: her Circle of Spores features)."
    )
)
S.append(P("Reactions &amp; Passives", h2))
S.append(todo("One reaction per round; which to use when."))
S.append(P("Items You Have", h2))
S.append(todo("Items, attunement, effect; attunement slots left."))
S.append(CondPageBreak(45 * mm))
S.append(P("Part 2 — Table Rules &amp; Your Resources", h1))
S.append(
    todo(
        "The campaign's rest and house rules as they affect this build, and any routine the build depends on (e.g. a nightly routine, a weekly cycle, costs, expected yield, and running it without table friction)."
    )
)
S.append(P("Your Table's Rules", h2))
S.append(todo("Confirmed rulings, and working assumptions marked as such."))
S.append(P("Your Routine", h2))
S.append(todo("Step-by-step, in the order it has to happen."))
S.append(CondPageBreak(45 * mm))
S.append(P("Part 3 — Path to Level 10", h1))
S.append(
    todo(
        "The build the player chose (e.g. a published build guide), with your own recommendations where they differ, and why."
    )
)
S.append(P("Next Level Picks", h2))
S.append(todo("Every choice at the next level: pick and reason."))
S.append(P("Level Plan", h2))
S.append(todo("Level-by-level table of new spells/features with reasons."))
S.append(P("Feats", h2))
S.append(todo("Chosen feats and alternatives, with trade-offs."))
S.append(CondPageBreak(45 * mm))
S.append(P("Part 4 — Items &amp; Attunement", h1))
S.append(todo("Wishlist with verdicts; which items are worth the last attunement slot."))
S.append(CondPageBreak(45 * mm))
S.append(P("Part 5 — How to Play Them", h1))
S.append(
    todo(
        'Intro box: the one-line concept (Mossy: "A royal food-taster who survived, and now tastes everything the dungeon grows").'
    )
)
S.append(P("Their Story in One Breath", h2))
S.append(todo("One paragraph."))
S.append(P("Setting Details for Role-Play", h2))
S.append(
    todo(
        "Lore that gives the player things to *do* or *say* (Mossy: the royal kitchens' crest, and Lord Hallowmere's name)."
    )
)
S.append(P("Personality", h2))
S.append(todo("Traits, ideals, bonds, flaws, secret."))
S.append(P("Voice", h2))
S.append(
    todo("Situation → line table, including combat lines. Label lines for spells not yet known.")
)
S.append(P("The People in Their Life", h2))
S.append(todo("NPCs: who, what they are to the character, how to play them."))
S.append(P("At the Table: Build as Character", h2))
S.append(todo("Each mechanic explained as fiction."))
S.append(P("Their Arc", h2))
S.append(todo("Stages, and what pushes each one."))
S.append(CondPageBreak(45 * mm))
S.append(P("Part 6 — Them and the Party", h1))
S.append(todo("The part players struggle with most: give them a system."))
S.append(P("The Modes", h2))
S.append(
    todo(
        "Two or three modes, when each shows up, what it sounds like (Mossy: The Critic, The Forager, The Taster). State the golden rule (the rare mode stays rare)."
    )
)
S.append(P("Stuck? Pick a Move", h2))
S.append(todo("Go-to moves for any scene."))
S.append(P("Common Party Situations", h2))
S.append(todo("Situation → what the character does."))
S.append(P("When Someone Dies", h2))
S.append(
    todo(
        "Teammates in stages (down, not getting up, after, brought back, stays dead, funeral) and NPCs (enemy, stranger, patient, employee, key NPCs), plus the aftermath and an at-the-table note that a character death is that player's moment first."
    )
)
S.append(P("The Teammates", h2))
S.append(
    todo(
        'Per teammate: who they are to the character, how to play it. Mark unknown backstories as "still to come".'
    )
)
S.append(P("Party Tactics", h2))
S.append(todo("What the character does **now**, then what arrives with each level; combos."))
S.append(P("Fighting Where You Live", h2))
S.append(
    todo(
        "The party's recurring battlefield (e.g. the party's ship), marked as the long-term plan with a pointer back to the cheat sheet."
    )
)
S.append(P("Table Etiquette", h2))
S.append(todo("How to keep the character's bits fun for everyone."))
S.append(CondPageBreak(45 * mm))
S.append(P("Part 7 — Running Gag", h1))
S.append(
    todo(
        "A recurring bit with real detail (Mossy: star ratings for every meal, with her scoring rules, the worst-ever list, and what each teammate's cooking earns)."
    )
)
S.append(CondPageBreak(45 * mm))
S.append(P("Part 8 — Side Project", h1))
S.append(
    todo(
        "Downtime activity (Mossy: \"dungeon-safe\" mushroom jerky: recipes, stock, customers, rivals). No invented income: that's the DM's."
    )
)
S.append(PageBreak())
S.append(P("Part 9 — DM Notes", h1))
S.append(todo("Starts on a new page so it can be handed over on its own."))
S.append(P("At a Glance", h2))
S.append(P("Key NPCs", h2))
S.append(P("Arc", h2))
S.append(P("Hooks", h2))
S.append(todo("Grouped by theme (patron/god, past, party, side project)."))
S.append(P("Rules &amp; Rulings", h2))
S.append(table(rules_rows(CH, "private"), [128, 42]))

build(S, output_path(CH, f"{CH.dir.name}_Guide.pdf"), f"{CH.name} — Personal guide · {stamp(CH)}")
