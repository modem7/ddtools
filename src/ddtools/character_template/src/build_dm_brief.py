"""Starter dm brief: every section from the ddtools blueprint dm-brief.md.

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
S.append(P(f"DM brief · {CH.class_summary} · Level {CH.level}", sub))
S.append(P("At a Glance", h2))
S.append(
    todo(
        'Table: concept, at the table, underneath, role, build, the player\'s goals (including what the player finds hard, so hooks give the character something to react to). Open with a "How to use this" box: ideas not requests; "Secret" marks what the party doesn\'t know.'
    )
)
S.append(P("What the Party Knows", h2))
S.append(
    todo(
        "What the party has read, and a box on how the party sees the character, including what the player wants to reveal in play (so NPCs don't give it away)."
    )
)
S.append(P("What the Party Doesn't Know (Secret)", h2))
S.append(todo("Table: secret, detail, good reveal moment."))
S.append(CondPageBreak(45 * mm))
S.append(P("Their Story", h1))
S.append(todo("One paragraph."))
S.append(P("Key NPCs", h2))
S.append(todo("NPC, role, what they want from the character."))
S.append(P("Setting Details Worth Using", h2))
S.append(todo("Lore the DM can pull on."))
S.append(P("Their Arc", h2))
S.append(todo("Stage, what it looks like, what pushes it."))
S.append(P("Lines &amp; Limits", h2))
S.append(todo("What the player would rather avoid; `[placeholder]` until they say."))
S.append(CondPageBreak(45 * mm))
S.append(P("Hooks", h1))
S.append(
    todo(
        'Grouped by theme; mark party-sensitive groups "(Secret)". Include any rule the player follows that the DM can use (Mossy: she never admits a meal was good).'
    )
)
S.append(CondPageBreak(45 * mm))
S.append(P("Mechanics", h1))
S.append(todo("How the build affects the table."))
S.append(P("Current Numbers", h2))
S.append(todo("Stats grid for the current level."))
S.append(P("Level Plan", h2))
S.append(todo("What the DM will see at each level, and a loot wishlist."))
S.append(P("Rules &amp; Rulings", h2))
S.append(table(rules_rows(CH, "dm"), [128, 42]))
S.append(P("Blanks for You to Fill", h2))
S.append(todo("Names and details the DM owns."))

build(S, output_path(CH, f"{CH.dir.name}_DM_Brief.pdf"), f"{CH.name} — DM brief · {stamp(CH)}")
