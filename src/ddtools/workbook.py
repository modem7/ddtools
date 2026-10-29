"""The party workbook: a fillable PDF that any player fills in and hands to Claude.

Built from the character's campaign in ``character.yaml``: the party (still in it), the
campaign facts, and ``campaign.workbook`` (audience, campaign_line, battlefield,
not_allowed, example_place, combat_notes). The character's own row uses ``party_summary``.
Form fields have stable, versioned names (``v1.s<section>.<label>``, see
``ddtools.workbook_fields``) so a filled workbook can be read back by
``ddtools import-workbook``.

The workbook is a cover, the numbered sections in ``SECTIONS`` (each a heading plus a
builder function), and a closing "Hand It to Claude" section.

Run as a document script: ``script: ddtools:workbook`` in ``character.yaml``.
"""

from __future__ import annotations

import html
import textwrap
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple

from ddtools.config import Character, is_present, load_character, output_path, updated_label
from ddtools.pdfstyle import (
    ACCENT,
    MUTED,
    WARN_BG,
    CondPageBreak,
    Field,
    Flowable,
    KeepTogether,
    P,
    PageBreak,
    ParagraphStyle,
    Spacer,
    Table,
    Ticks,
    bl,
    body,
    box,
    build,
    code,
    colors,
    h1,
    h2,
    mm,
    small,
    sub,
    table,
    title,
)
from ddtools.workbook_fields import field_key

FILE = "Party_Character_Guide_Workbook.pdf"

NUMBERS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]


step = ParagraphStyle("step", parent=body, fontName="DVB", textColor=ACCENT, spaceAfter=2)
EX_BG = colors.HexColor("#f5f0ea")
EX_EDGE = MUTED


@dataclass
class _Workbook:
    """What the section builders need: the character, its campaign's workbook options and
    teammates, and the number of the section being built (it names the form fields)."""

    ch: Character
    options: dict[str, Any]  # campaign.workbook
    party: list[dict[str, Any]]  # teammates still in the party
    section: int = 0

    @classmethod
    def of(cls, ch: Character) -> _Workbook:
        party = [p for p in ch.campaign.get("party") or [] if is_present(ch, p["name"])]
        return cls(ch, ch.campaign.get("workbook") or {}, party)

    @property
    def first(self) -> str:
        """The character's first name."""
        return self.ch.name.split(" ")[0]

    def field(self, label: str, lines: int = 3) -> Field:
        return Field(label, lines, key=field_key(self.section, label))

    def ticks(self, options: Sequence[str], cols: int = 3, **kw: float) -> Ticks:
        return Ticks(options, cols, key=field_key(self.section, options[0]), **kw)


class _Section(NamedTuple):
    """A numbered section: its heading, and the function that builds the rest."""

    num: int
    name: str  # Paragraph markup, e.g. "Build &amp; Levelling"
    mins: int
    build: Callable[[_Workbook], list[Flowable]]
    why: str
    skip: str | None = None


def example(t: str) -> Table:
    return box([P("<b>Example (Mossy):</b> " + t, small)], bg=EX_BG, edge=EX_EDGE)


def _heading(s: _Section) -> list[Flowable]:
    out = [CondPageBreak(70 * mm), P(f"{s.num}. {s.name}", h1)]
    tag = f"<font color='#5b544c'><b>Time:</b> about {s.mins} min"
    if s.skip:
        tag += f"  ·  Skip if: {s.skip}"
    tag += "</font>"
    out += [P(tag, small), Spacer(1, 3), P("<b>Why:</b> " + s.why, body)]
    return out


def _cover(wb: _Workbook) -> list[Flowable]:
    """The cover: how it works, the ground rules, the short version, the tracker."""
    out: list[Flowable] = []
    out.append(P("Your Character Guide", title))
    out.append(
        P(
            f"A workbook for {wb.options.get('audience', 'your party')} · Fill it in, hand it to Claude, get back your own guide: "
            "levelling plan, combat cheat sheet, role-play help and DM notes.",
            sub,
        )
    )

    out.append(
        box(
            [
                P("<b>How this works, in 3 steps</b>", body),
                P(
                    "<b>1.</b> Fill in what you can. Type straight into the boxes, or print it and write.",
                    small,
                ),
                P(
                    "<b>2.</b> Give it to Claude (claude.ai) with your <b>D&amp;D Beyond link</b>, and paste the prompt from the last page.",
                    small,
                ),
                P(
                    "<b>3.</b> Claude builds your guide. Ask it for changes until you like it. Come back and update it when you level up.",
                    small,
                ),
            ]
        )
    )
    out.append(Spacer(1, 6))
    out.append(
        box(
            [
                P("<b>The ground rules</b>", body),
                P(
                    "• <b>Nothing here is required.</b> Skip any box. Claude will work with whatever you give it and ask about the gaps.",
                    small,
                ),
                P(
                    "• <b>Bullet points and half-sentences are fine.</b> “grumpy, loves cheese, hates boats” is a perfectly good answer.",
                    small,
                ),
                P(
                    "• <b>No order needed.</b> Start wherever you like. Come back later. Do it over several sittings.",
                    small,
                ),
                P(
                    "• <b>Stuck on a box?</b> Leave it blank and write “help me with this” instead. That’s a great thing to give Claude.",
                    small,
                ),
            ],
            bg=WARN_BG,
        )
    )

    out.append(P("The Short Version", h2))
    out.append(
        P("Only got 10 minutes? Do these three and you’ll already get a useful guide:", body)
    )
    out.append(
        table(
            [
                ["", "Do this", "Section"],
                ["☐", "Paste your D&amp;D Beyond link (and set the character to Public)", "1"],
                ["☐", "Paste your backstory, even a rough one", "3"],
                ["☐", "Tick what you want from your character, and what you find hard", "4"],
            ],
            [8, 132, 30],
        )
    )

    out.append(P("Progress Tracker", h2))
    out.append(
        P("Tick sections off as you go. Tick “skipped” too: skipping is a valid choice.", small)
    )
    out.append(Spacer(1, 3))
    out.append(
        table(
            [
                ["", "Section", "Time", "", "Section", "Time"],
                ["☐", "1. The basics", "3 min", "☐", "8. The people in your life", "5 min"],
                ["☐", "2. The one-line pitch", "3 min", "☐", "9. You and the party", "10 min"],
                [
                    "☐",
                    "3. Backstory",
                    "5 min",
                    "☐",
                    "10. Running gags &amp; side projects",
                    "5 min",
                ],
                ["☐", "4. What you want", "5 min", "☐", "11. In combat", "5 min"],
                [
                    "☐",
                    "5. Build &amp; levelling",
                    "5 min",
                    "☐",
                    "12. Hooks, secrets &amp; limits",
                    "5 min",
                ],
                [
                    "☐",
                    "6. Skills &amp; what you’re good at",
                    "3 min",
                    "☐",
                    "13. Questions for the DM",
                    "3 min",
                ],
                [
                    "☐",
                    "7. Personality &amp; voice",
                    "10 min",
                    "☐",
                    "14. Hand it to Claude",
                    "2 min",
                ],
            ],
            [7, 57, 21, 7, 57, 21],
        )
    )

    out.append(Spacer(1, 6))
    out.append(
        box(
            [
                P(
                    f"<b>What you get back.</b> The same kind of guide {wb.first}’s player has: a quick-start summary, a <b>combat cheat sheet</b> for "
                    "your current level, a levelling plan, <b>how to play your character</b> (especially in party scenes), your relationships "
                    "with each teammate, and a <b>DM notes</b> section with story hooks. You can also ask for a short <b>party handout</b> "
                    "(no spoilers) and a separate <b>DM brief</b>.",
                    small,
                )
            ]
        )
    )
    return out


def _basics(wb: _Workbook) -> list[Flowable]:
    out: list[Flowable] = []
    out.append(wb.field("Character name", 1))
    out.append(wb.field("Player name (and what to call you)", 1))
    out.append(
        wb.field(
            "Race / class / subclass / level  (e.g. “Human Gunslinger, High Roller, level 3”)", 1
        )
    )
    out.append(wb.field("D&D Beyond link  (e.g. https://www.dndbeyond.com/characters/12345678)", 1))
    out.append(Spacer(1, 4))
    out.append(
        box(
            [
                P("<b>Make your character readable first</b>", body),
                P(
                    "On D&amp;D Beyond: open your character → <b>Manage</b> (or the gear icon) → <b>Character Settings</b> → "
                    "<b>Character Privacy</b> → <b>Public</b>. Without this, Claude can’t open the link. "
                    "It only makes the sheet viewable, not editable.",
                    small,
                ),
            ],
            bg=WARN_BG,
        )
    )
    return out


def _pitch(wb: _Workbook) -> list[Flowable]:
    out: list[Flowable] = []
    out.append(P("Try one of these formulas:", body))
    out.extend(
        bl(
            [
                "<b>[Famous character] meets [another famous character].</b>",
                "<b>A [adjective] [role] who wants [goal] but [problem].</b>",
                "<b>[Character] if they were [job / situation].</b>",
            ]
        )
    )
    out.append(wb.field("Your pitch", 2))
    out.append(
        box(
            [
                P(
                    "<b>Meet Mossy Thistlewick</b>, our made-up example character for this workbook (she’s not in the party). "
                    "A gnome Circle of Spores Druid: a former royal food-taster, now a dungeon mushroom forager.",
                    small,
                )
            ]
        )
    )
    out.append(Spacer(1, 3))
    out.append(
        example(
            "“<i>Mary Poppins meets Gordon Ramsay</i>”: a cheerful, bossy nanny type who judges everyone’s cooking."
        )
    )
    return out


def _backstory(wb: _Workbook) -> list[Flowable]:
    out: list[Flowable] = []
    out.extend(
        bl(
            [
                "Paste your backstory as it is. Long, short, or bullet points.",
                "If you have two versions (a short one the party knows and a longer private one), paste both and say which is which.",
                "Unfinished? That’s fine. Write what you know and put “TBD” on the rest.",
            ]
        )
    )
    out.append(wb.field("Backstory (or where to find it, e.g. “it’s on my D&D Beyond sheet”)", 9))
    out.append(wb.field("What the rest of the party already knows about you", 2))
    out.append(wb.field("What the party doesn’t know yet (secrets). Goes in your DM notes only", 3))
    out.append(
        example(
            "The party knows she was sacked from the royal kitchens after a lord was poisoned at a banquet. "
            "They don’t know that she was the one who poisoned him, or why."
        )
    )
    return out


def _wants(wb: _Workbook) -> list[Flowable]:
    out: list[Flowable] = []
    out.append(P("In combat, I mostly want to… <font color='#5b544c'>(tick any)</font>", step))
    out.append(
        wb.ticks(
            [
                "Deal big damage",
                "Hit lots of enemies at once",
                "Heal and protect",
                "Tank / hold the line",
                "Control the battlefield",
                "Buff my allies",
                "Be sneaky / scout",
                "Be the face in talks",
                "Solve puzzles / utility",
                "Be hard to kill",
                "Do cool stunts",
                "Not sure yet",
            ]
        )
    )
    out.append(
        P(
            "I find these hard… <font color='#5b544c'>(tick any. This is the most useful box in the workbook)</font>",
            step,
        )
    )
    out.append(
        wb.ticks(
            [
                "Knowing what to say in party chat",
                "Talking to NPCs",
                "Deciding what to do on my turn",
                "Remembering my abilities",
                "Keeping track of resources",
                "Staying in character",
                "Knowing when to speak up",
                "Picking spells / feats",
                "Rules and edge cases",
                "Remembering the story so far",
                "Making decisions quickly",
                "Nothing in particular",
            ],
            cols=2,
        )
    )
    out.append(
        wb.field(
            "Anything else you want from this character (a story arc, a vibe, a moment you’re hoping for)",
            3,
        )
    )
    out.append(
        example(
            "Control first, support second. Wants a slow arc about forgiving herself. Finds talking to NPCs the hardest part, so the guide gives her "
            "“go-to moves” to use when she’s stuck."
        )
    )
    return out


def _build_and_levelling(wb: _Workbook) -> list[Flowable]:
    out: list[Flowable] = []
    out.append(
        wb.ticks(
            [
                "Suggest a plan for me",
                "I have a plan, check it",
                "I have a guide/video I’m following",
                "Keep it simple",
                "Optimise hard",
                "Flavour over power",
            ],
            cols=3,
        )
    )
    out.append(wb.field("Your plan, or a link / name of the build you’re following", 3))
    out.append(wb.field("Choices you’re unsure about (spells, feats, multiclassing, items)", 2))
    out.append(
        example(
            "Following a Spores Druid build from a YouTube guide. Unsure whether to take War Caster or Resilient (CON) first."
        )
    )
    return out


def _skills(wb: _Workbook) -> list[Flowable]:
    out: list[Flowable] = []
    out.append(
        wb.field(
            "Your top 3 skills or tools, and when they matter  (e.g. “Stealth: scouting ahead”)", 3
        )
    )
    out.append(wb.field("Things only you in the party can do", 2))
    out.append(wb.field("Things you’re bad at (useful for funny or dramatic moments)", 2))
    return out


def _personality(wb: _Workbook) -> list[Flowable]:
    out: list[Flowable] = []
    out.append(
        table(
            [
                ["", "Prompt", "Example (Mossy)"],
                [
                    "<b>Trait</b>",
                    "Something people notice within five minutes",
                    "Tastes everything first, including things she really shouldn’t",
                ],
                [
                    "<b>Ideal</b>",
                    "What they believe in",
                    "“Nobody fights well on an empty stomach.”",
                ],
                [
                    "<b>Bond</b>",
                    "Who or what they’d fight for",
                    "Old Mother Cap, the talking mushroom who taught her magic",
                ],
                [
                    "<b>Flaw</b>",
                    "What gets them in trouble",
                    "Can’t resist fixing other people’s food, or lives",
                ],
            ],
            [18, 72, 80],
        )
    )
    out.append(wb.field("Traits, ideals, bonds, flaws", 4))
    out.append(wb.field("How they talk (accent, speed, favourite words, nicknames for people)", 2))
    out.append(wb.field("2–3 catchphrases or things they’d say", 2))
    out.append(Spacer(1, 3))
    out.append(
        box(
            [
                P(
                    "<b>Idea to steal: “modes”.</b> Most characters switch between a few modes. Name 2–3 and write when each one shows up. "
                    "When you’re stuck in a scene, just pick the mode that fits.",
                    small,
                ),
                P(
                    "Mossy has <b>Nanny</b> (default: bossy and caring), <b>The Critic</b> (any time food is involved) and <b>Quiet Mossy</b> "
                    "(rare: something scares her, and the chatter stops).",
                    small,
                ),
            ]
        )
    )
    out.append(wb.field("Your character’s modes (optional)", 3))
    return out


def _people(wb: _Workbook) -> list[Flowable]:
    out: list[Flowable] = []
    out.append(
        wb.field(
            "Family, mentors, rivals, enemies, patrons, gods, exes, debts. Name + one line on each",
            5,
        )
    )
    out.append(
        example(
            "<b>Lord Hallowmere</b>, the noble who was poisoned (and survived). <b>Chef Barrow</b>, her old boss, who fired her. "
            "<b>Old Mother Cap</b>, the talking mushroom who taught her druid magic."
        )
    )
    return out


def _party(wb: _Workbook) -> list[Flowable]:
    out: list[Flowable] = []
    out.append(
        P(
            "Your teammates. Their D&amp;D Beyond links are included so Claude can read their sheets too.",
            body,
        )
    )
    out.append(
        table(
            [
                ["Character", "What we know", "D&amp;D Beyond"],
                [
                    f"<b>{wb.ch.name}</b>",
                    wb.ch.party_summary,
                    f"dndbeyond.com/characters/{wb.ch.dndbeyond_id}",
                ],
                *[
                    [
                        f"<b>{p['name']}</b>",
                        p.get("summary", ""),
                        f"dndbeyond.com/characters/{p['dndbeyond_id']}",
                    ]
                    for p in wb.party
                ],
            ],
            [34, 86, 50],
        )
    )
    out.append(Spacer(1, 4))
    out.append(P("For each teammate (skip yourself), answer any of these:", body))
    out.extend(
        bl(
            [
                "What do you <b>think of them</b>? (Trust, annoyed by, impressed by, protective of, suspicious of…)",
                "What would you <b>tease them about</b>? What would you <b>ask them</b>?",
                "What could you <b>do together</b> in a fight? (Combos, protecting each other, covering weaknesses)",
            ]
        )
    )
    for who in [wb.first] + [p["name"].split(" ")[0] for p in wb.party]:
        out.append(wb.field(who, 2))
    out.append(Spacer(1, 3))
    out.append(
        example(
            "Mossy treats her party’s barbarian like a child who needs feeding: she packs them labelled lunches, "
            "and takes it personally when they eat monster meat instead."
        )
    )
    return out


def _running_gags(wb: _Workbook) -> list[Flowable]:
    out: list[Flowable] = []
    out.append(wb.field("A habit, an object, a catchphrase or a bit you keep coming back to", 3))
    out.append(wb.field("Something they do in downtime (a job, a hobby, a scheme, a project)", 3))
    out.append(
        example(
            "<b>The star ratings</b>: she rates every meal the party eats out of five, out loud, including the ones cooked by enemies. "
            "<b>In downtime</b> she sells “dungeon-safe” mushroom jerky."
        )
    )
    return out


def _combat(wb: _Workbook) -> list[Flowable]:
    out: list[Flowable] = []
    out.append(wb.field("What do you usually do on your turn right now?", 2))
    out.append(
        wb.field(
            "What do you use your bonus action and reaction for? (or “I always forget I have them”)",
            2,
        )
    )
    out.append(wb.field("Situations where you’re not sure what to do", 2))
    for note in wb.options.get("combat_notes") or []:
        out.append(Spacer(1, 3))
        out.append(box([P(note, small)], bg=WARN_BG))
    return out


def _hooks(wb: _Workbook) -> list[Flowable]:
    out: list[Flowable] = []
    out.append(
        wb.field("Story moments you’d love to see (a reunion, a rival, a reveal, a big choice)", 3)
    )
    out.append(
        wb.field(
            "Where you’d like the character to end up (redemption, revenge, power, home, a surprise)",
            2,
        )
    )
    out.append(
        wb.field(
            "Things you’d rather avoid in your character’s story (topics, situations, anything)", 2
        )
    )
    out.append(
        example(
            f"Would love: Lord Hallowmere turning up in {wb.options.get('example_place', 'town')}, and a teammate finding out a big secret from her past."
        )
    )
    return out


def _dm_questions(wb: _Workbook) -> list[Flowable]:
    out: list[Flowable] = []
    out.append(
        wb.field(
            "Anything you’re unsure about (house rules, how a feature works here, anything unclear)",
            3,
        )
    )
    out.append(Spacer(1, 3))
    out.append(P("Campaign Facts (so Claude gets them right)", h2))
    out.append(
        table(
            [
                ["", ""],
                *[[f"<b>{f['label']}</b>", f["text"]] for f in wb.ch.campaign.get("facts") or []],
            ],
            [30, 140],
            header=False,
        )
    )
    return out


def _hand_it_to_claude(wb: _Workbook) -> list[Flowable]:
    """The last section: what Claude needs, the prompts to paste, and follow-ups."""
    n = 1 + len(wb.party)
    links = NUMBERS[n] if n < len(NUMBERS) else str(n)
    out: list[Flowable] = []
    out.append(PageBreak())
    out.append(P("14. Hand It to Claude", h1))
    out.append(P("First: What Claude Needs (one time, 2 minutes)", h2))
    out.append(
        P("These are the only things used to make the guides. No plugins or extra add-ons.", body)
    )
    out.append(
        table(
            [
                ["Claude needs to…", "What to do"],
                [
                    "<b>Read your character</b>",
                    "Set your D&amp;D Beyond character to <b>Public</b> (section 1) and include the link",
                ],
                [
                    "<b>Open links and look up lore</b>",
                    "<b>Claude chat:</b> Settings → Capabilities → turn on <b>web search</b>. <b>Claude Code:</b> nothing to do",
                ],
                [
                    "<b>Make and check the PDF</b>",
                    "<b>Claude chat:</b> Settings → Capabilities → turn on <b>code execution and file creation</b>. <b>Claude Code:</b> nothing to do",
                ],
                [
                    "<b>Know the house rules</b>",
                    "Attach the <b>campaign’s character creation guide</b> (PDF) if you have it. Ask the DM for a copy if not",
                ],
            ],
            [44, 126],
        )
    )
    out.append(P("Then: Paste the Prompt", h2))
    out.append(
        P(
            "Start a new chat in Claude (or a new Claude Code session), attach this filled-in PDF (or paste your answers), and copy in the prompt below. "
            "Change anything in [brackets].",
            body,
        )
    )
    out.append(Spacer(1, 3))
    out.append(
        code(
            [
                *textwrap.wrap(
                    f"I play [character name] in {wb.options.get('campaign_line', 'a D&D 5e campaign')}. "
                    "I've attached my filled-in character workbook.",
                    73,
                ),
                "",
                "My character: https://www.dndbeyond.com/characters/[your ID]",
                "(If you can't open that page, try:",
                " https://character-service.dndbeyond.com/character/v5/character/[your ID] )",
                "",
                "My party (read their sheets too):",
                f" {wb.ch.name:<20}https://www.dndbeyond.com/characters/{wb.ch.dndbeyond_id}",
                *[
                    f" {p['name']:<20}https://www.dndbeyond.com/characters/{p['dndbeyond_id']}"
                    for p in wb.party
                ],
                "",
                "Please make me a character guide as a PDF, with:",
                " 1. A one-page summary of who my character is and where I am now",
                " 2. A combat cheat sheet for my current level (action, bonus action,",
                *(
                    [f"    reaction), including where I'm fighting on {wb.options['battlefield']}"]
                    if wb.options.get("battlefield")
                    else ["    reaction)"]
                ),
                " 3. A levelling plan for the next few levels, with reasons",
                " 4. How to play my character: personality, voice, example lines,",
                "    and go-to moves for when I'm stuck in a scene",
                " 5. My relationship with each teammate, with ideas for scenes",
                " 6. Party tactics: combos and how we cover each other",
                " 7. DM notes: key NPCs, story hooks, my secrets, open questions",
                "",
                "How to build it:",
                " - Read my sheet, and the campaign guide if I've attached it. Where",
                "   they disagree, follow my sheet and list it as a question for the DM.",
                " - Only use content the campaign allows"
                + (f" ({wb.options['not_allowed']})." if wb.options.get("not_allowed") else "."),
                " - Give your own recommendations with reasons, even if they differ",
                "   from any build guide I mention.",
                " - If a rule is unclear, write your assumption and mark it 'check with",
                "   DM'. Don't invent things the DM decides: leave [placeholders].",
                " - Look up setting lore only where it helps role-play or DM hooks.",
                "",
                "Layout:",
                " - A4, clear headings, and the same structure in every section.",
                " - A TL;DR at the top. Short sentences, one idea per bullet, tables",
                "   instead of long paragraphs, bold key words, plain language.",
                "   Explain any jargon the first time it appears.",
                " - Put the combat cheat sheet on its own page(s) so I can print it.",
                " - British English.",
                " - Before giving me the PDF, render each page and check for cut-off",
                "   text, headings stranded at the bottom of a page, and big gaps.",
                "",
                "Ask me about anything missing before you guess.",
            ]
        )
    )
    out.append(Spacer(1, 6))
    out.append(
        KeepTogether(
            [
                P("One More: All Three PDFs at Once", h2),
                P(
                    f"Want the full set, like {wb.first}’s player has? Use this after the main prompt (or instead of it):",
                    body,
                ),
                Spacer(1, 3),
                code(
                    [
                        "Using my workbook and the D&D Beyond links, create THREE separate PDFs,",
                        "all in the same style:",
                        "",
                        " 1. PERSONAL GUIDE: everything, for me. Summary, combat cheat sheet,",
                        "    levelling plan, how to play my character, teammates, tactics,",
                        "    DM notes and open questions.",
                        "",
                        " 2. PARTY HANDOUT (2-3 pages): safe to share with the group. Who my",
                        "    character is (only what the party already knows), what they can",
                        "    do for the party, and easy ways to play off them. Leave out my",
                        "    secrets, DM notes and anything that would spoil a future story",
                        "    moment between characters.",
                        "",
                        " 3. DM BRIEF: for my DM. What the party knows vs what they don't,",
                        "    my secrets, key NPCs, my arc, story hooks, what I want from the",
                        "    character, things I'd rather avoid, and my open rules questions.",
                        "",
                        "In the party handout, no hints either: examples, catchphrases and",
                        "jokes mustn't point at a secret. Follow the same build and layout",
                        "rules as above.",
                        "",
                        "Before you start, tell me which of my details you're treating as",
                        "secret, so I can check nothing spoilery ends up in the party handout.",
                    ]
                ),
            ]
        )
    )
    out.append(CondPageBreak(80 * mm))
    out.append(P("Useful Follow-Ups", h2))
    out.append(P("Once you have your guide, you can ask Claude for more. Copy any of these:", body))
    out.append(
        table(
            [
                ["Ask for", "Prompt"],
                [
                    "<b>A party overview</b>",
                    f"“Read all {links} D&amp;D Beyond links and give me a party overview: who does what, gaps we have, and combos between us.”",
                ],
                [
                    "<b>A party handout</b>",
                    "“Make a 2-page handout I can share with my party. Nothing from my secrets or DM notes.”",
                ],
                [
                    "<b>A DM brief</b>",
                    "“Make a separate brief for my DM with my hooks, secrets, arc and open rules questions.”",
                ],
                [
                    "<b>Help in the moment</b>",
                    "“My character just [situation]. Give me three things they might say.”",
                ],
                [
                    "<b>Level-up</b>",
                    "“I just hit level [X]. Update my cheat sheet and levelling plan.”",
                ],
                [
                    "<b>After a session</b>",
                    "“Here’s what happened last session: […]. Update my guide and suggest new hooks.”",
                ],
                [
                    "<b>A teammate scene</b>",
                    "“Give me an in-character conversation starter between my character and [teammate].”",
                ],
            ],
            [36, 134],
        )
    )
    out.append(Spacer(1, 6))
    out.append(
        box(
            [
                P(
                    "<b>Keep this workbook.</b> When your character changes (new level, big story moment, new backstory reveal), "
                    "update the relevant box and ask Claude to update your guide. Small, frequent updates are easier than one big one.",
                    small,
                )
            ]
        )
    )
    return out


# The numbered sections, in order. "Hand It to Claude" (14) follows them and has no fields.
SECTIONS = [
    _Section(
        1,
        "The Basics",
        3,
        _basics,
        why="the character sheet does most of the work. Claude can read your D&amp;D Beyond character directly, "
        "so it knows your stats, spells, items and features without you typing them out.",
    ),
    _Section(
        2,
        "The One-Line Pitch",
        3,
        _pitch,
        why="one sentence gives Claude (and you) a compass. Every time you’re unsure what your character would do, "
        "you can check it against this.",
        skip="you really can’t think of one. Claude can suggest a few from your backstory.",
    ),
    _Section(
        3,
        "Backstory",
        5,
        _backstory,
        why="this is where DM hooks and role-play ideas come from. Even a messy paragraph gives Claude a lot to work with.",
    ),
    _Section(
        4,
        "What You Want From Your Character",
        5,
        _wants,
        why="a guide should be built around what <i>you</i> find fun and what you find hard, "
        "not just what’s mathematically strongest.",
    ),
    _Section(
        5,
        "Build &amp; Levelling",
        5,
        _build_and_levelling,
        why="Claude can plan your next levels, check your choices against the house rules, and turn it all "
        "into a one-page cheat sheet.",
        skip="you’d rather Claude suggest a plan from scratch. Just tick the first box.",
    ),
    _Section(
        6,
        "Skills &amp; What You’re Good At",
        3,
        _skills,
        why="most of the game isn’t combat. Knowing your best skills tells you when to step forward.",
    ),
    _Section(
        7,
        "Personality &amp; Voice",
        10,
        _personality,
        why="this becomes the “how to play them” part of your guide: ready-made lines and reactions "
        "you can reach for mid-session.",
        skip="you’d rather describe the vibe and let Claude write the rest.",
    ),
    _Section(
        8,
        "The People in Your Life",
        5,
        _people,
        why="NPCs are the DM’s easiest hooks. Every name you give is a story waiting to happen.",
        skip="your backstory already covers it.",
    ),
    _Section(
        9,
        "You and the Party",
        10,
        _party,
        why="party scenes are where most people get stuck. A clear idea of how you feel about each "
        "teammate gives you something to say.",
    ),
    _Section(
        10,
        "Running Gags &amp; Side Projects",
        5,
        _running_gags,
        why="a recurring bit gives you something to do in every scene without having to "
        "think of something new.",
        skip="nothing comes to mind. These often appear on their own after a few sessions.",
    ),
    _Section(
        11,
        "In Combat",
        5,
        _combat,
        why="your cheat sheet will list your best move for each situation, so you’re not scrolling through "
        "your sheet when it’s your turn.",
    ),
    _Section(
        12,
        "Hooks, Secrets &amp; Limits",
        5,
        _hooks,
        why="this becomes the DM notes section. It helps the DM give your character "
        "story moments you’ll actually enjoy.",
    ),
    _Section(
        13,
        "Questions for the DM",
        3,
        _dm_questions,
        why="writing down rules questions stops them getting lost, and the guide can track the answers.",
        skip="you have none. You can always add them later.",
    ),
]


def section_titles(ch: Character) -> dict[int, str]:
    """Section number -> title, as plain text (0 is the cover, "Start"). Builds nothing."""
    return {0: "Start"} | {s.num: html.unescape(s.name) for s in SECTIONS}


def story(ch: Character) -> list[Flowable]:
    """The workbook's flowables, for a character."""
    wb = _Workbook.of(ch)
    out = _cover(wb)
    for s in SECTIONS:
        wb.section = s.num
        out += _heading(s)
        out += s.build(wb)
    out += _hand_it_to_claude(wb)
    return out


def build_workbook(ch: Character | None = None) -> Path:
    """Write the workbook PDF for ``ch`` (default: the character being built)."""
    ch = ch or load_character()
    out = output_path(ch, FILE)
    build(story(ch), out, f"Your Character Guide — Workbook · {updated_label(ch)}")
    return out


if __name__ == "__main__":
    build_workbook()
