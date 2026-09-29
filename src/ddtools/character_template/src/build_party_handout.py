"""Starter party handout: every section from the ddtools blueprint party-handout.md.

Replace each guidance note with the real content. Keep the headings (or rename them
in the blueprint too) so the document keeps the shape of the others."""

from ddtools.config import load_character, output_path, stamp
from ddtools.pdfstyle import *

CH = load_character()


def todo(text):
    """A guidance note: what goes in this section. Delete it once written."""
    return box([P("<b>To write:</b> " + text, small)], bg=WARN_BG)


S = []
S.append(P(CH.name, title))
S.append(P(f"Party handout · {CH.class_summary} · Level {CH.level}", sub))
S.append(P("What You'll Notice About Them", h2))
S.append(
    todo(
        "A two-column table of visible traits. Open the page with the title, a one-line subtitle and an intro box built only from the public backstory."
    )
)
S.append(P("A Note From the Player", h2))
S.append(
    todo(
        "Out of character, three bullets: they're built to be played against; they have growing to do and the party can be part of it; if a bit stops being fun, say so. Nothing that explains away the character's act."
    )
)
S.append(P("Easy Ways to Play Off Them", h2))
S.append(todo("Things teammates can do or ask to start a scene."))
S.append(P("Running Gag", h2))
S.append(
    todo(
        "The public face of the character's bit (Mossy: her star ratings for every meal the party eats, read out loud)."
    )
)
S.append(CondPageBreak(45 * mm))
S.append(P("In a Fight", h1))
S.append(todo("Role in one sentence."))
S.append(P("What They Can Do for You Right Now", h2))
S.append(todo('Only current abilities, as "what it means for you".'))
S.append(P("Coming Soon", h2))
S.append(todo("Level → what the party gets. The spell check allows future spells here only."))
S.append(P("Working Together", h2))
S.append(todo("One tactical bullet per teammate, plus the party's recurring battlefield."))

build(
    S,
    output_path(CH, f"{CH.dir.name}_Party_Handout.pdf"),
    f"{CH.name} — Party handout · {stamp(CH)}",
)
