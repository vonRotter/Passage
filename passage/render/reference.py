"""The appendix: printed pages the player can read, bound into the same plate.

Nothing in this game is hidden. There is no fog, no unknown, no discovery, and
every failure is meant to be a failure of attention or of planning rather than
of information (spec 3.11). That is a promise the game cannot keep by *showing*
everything at once -- a plate dense enough to carry every formula would be
unreadable -- so it keeps it here instead: an appendix, always available, that
says what every substance is, what every vessel does, and what marking any gene
would actually change.

Every page is generated from the tables in ``data/``. Nothing here is written
out by hand, so the reference cannot drift away from the game it describes: if a
reaction's stoichiometry changes, this page changes with it.

Pages are inked once and cached, like the plate.
"""

from __future__ import annotations

import pygame

from ..bio.network import Network
from ..data import genes as gene_data
from ..data import metabolites as met_data
from ..data import reactions as rxn_data
from ..data import layout
from . import ink, palette, type as typo

MARGIN = 54
TOP = 92
COLUMN = 604


def formula(atoms: dict[str, int]) -> str:
    order = ["C", "H", "N", "O", "P", "S"]
    keys = [a for a in order if a in atoms] + sorted(set(atoms) - set(order))
    return "".join(a + (str(atoms[a]) if atoms[a] > 1 else "") for a in keys)


def equation(reaction: rxn_data.Reaction) -> str:
    def side(part):
        return " + ".join(
            (f"{int(n)} " if n != 1 else "") + met_data.BY_ID[m].label
            for m, n in part.items())
    return f"{side(reaction.inputs)}  →  {side(reaction.outputs)}"


class Reference:
    """The appendix, inked a page at a time and turned with the arrow keys."""

    TITLES = ("the substances", "the reactions", "the genes", "the diet",
              "the kitchen", "what happens anyway", "the constitution",
              "specialisms")
    SUBTITLES = (
        "what is in the cell, what makes it, and what uses it up",
        "every row balances on a real atom count; water and phosphate are "
        "present where the chemistry needs them but never limit anything",
        "what marking one would change, and what it idles at if you leave it",
        "relish against damage, and what it leaves behind",
        "a number picks a diet outright · a letter asks for a change",
        "every one of these can befall a run; none of them can be prevented",
        "the genome this lineage was dealt, which no mark will change",
        "what a cell can be pushed into being, and what it gives up for it",
    )

    def __init__(self, net: Network, seed: int = 9, constitution=None) -> None:
        self.net = net
        self.constitution = constitution
        self.seed = seed
        self.page = 0
        self._pages: dict[int, pygame.Surface] = {}
        self.inkings = 0

    @property
    def count(self) -> int:
        return len(self.TITLES)

    def turn(self, step: int) -> None:
        self.page = (self.page + step) % self.count

    def surface(self) -> pygame.Surface:
        if self.page not in self._pages:
            self._pages[self.page] = self._ink(self.page)
            self.inkings += 1
        return self._pages[self.page]

    # -- the pages ------------------------------------------------------------
    def _ink(self, page: int) -> pygame.Surface:
        surface = ink.paper(layout.WINDOW, self.seed + page).copy()
        typo.caps(surface, "passage", (MARGIN, 34), 13, palette.INK, 3.0)
        typo.caps(surface, self.TITLES[page], (MARGIN, 58), 11,
                  palette.INK_FAINT, 2.4)
        typo.draw(surface, f"appendix {page + 1} of {self.count}   ·   "
                           f"left and right to turn   ·   tab to close",
                  (layout.WINDOW[0] - MARGIN, 60), 10, palette.PENCIL, 0.2,
                  align="right")
        typo.draw(surface, self.SUBTITLES[page], (MARGIN + 190, 60), 10,
                  palette.PENCIL, 0.2)
        ink.ink_line(surface, (MARGIN, 78), (layout.WINDOW[0] - MARGIN, 78),
                     0.7, 5000 + page, palette.INK, 0.55)
        [self._substances, self._reactions, self._genes, self._diet,
         self._kitchen, self._happens, self._constitution,
         self._specialisms][page](surface)
        ink.ink_line(surface, (MARGIN, 684), (layout.WINDOW[0] - MARGIN, 684),
                     0.6, 5100 + page, palette.INK, 0.4)
        return surface

    def _substances(self, surface: pygame.Surface) -> None:
        producers = {m.id: [] for m in self.net.metabolites}
        consumers = {m.id: [] for m in self.net.metabolites}
        for reaction in rxn_data.INTERNAL:
            for mid in reaction.outputs:
                producers[mid].append(reaction)
            for mid in reaction.inputs:
                consumers[mid].append(reaction)

        pooled = [m for m in met_data.METABOLITES if not m.buffered]
        half = (len(pooled) + 1) // 2
        for n, met in enumerate(pooled):
            column, row = divmod(n, half)
            x = MARGIN + column * COLUMN
            y = TOP + row * 62
            typo.draw(surface, met.label, (x, y), 12, palette.INK, 0.2)
            typo.draw(surface, formula(met.atoms), (x + 148, y), 11,
                      palette.PENCIL, 0.2)
            typo.caps(surface, met.cls.value.replace("_", " "), (x + 268, y + 2),
                      8, palette.wash_for(met.cls), 1.2)
            typo.draw(surface, f"holds {met.cap:.0f}", (x + 392, y), 10,
                      palette.PENCIL, 0.2)
            made = len(producers[met.id])
            used = len(consumers[met.id])
            note = (f"{made} step{'s' if made != 1 else ''} make it, "
                    f"{used} use it"
                    + (f" — {met.note}" if met.note else ""))
            for i, line in enumerate(_wrap(note, 10, COLUMN - 74)):
                typo.draw(surface, line, (x + 8, y + 16 + i * 13), 10,
                          palette.PENCIL, 0.2)

    def _reactions(self, surface: pygame.Surface) -> None:
        # The step is fitted to the list rather than fixed, because the list
        # grows: adding fructolysis pushed the last row off the bottom of the
        # page, and a printed page that runs off the plate is a printing fault.
        top, bottom = TOP, 668
        step = min(38.0, (bottom - top) / max(1, len(rxn_data.INTERNAL)))
        y = top
        for reaction in rxn_data.INTERNAL:
            gene = gene_data.BY_ID[reaction.enzyme]
            typo.draw(surface, reaction.label, (MARGIN, y), 12, palette.INK, 0.2)
            typo.draw(surface, gene.label, (MARGIN + 640, y), 11,
                      palette.INK, 0.2)
            typo.draw(surface, f"up to {reaction.base_rate:.1f}/s",
                      (layout.WINDOW[0] - MARGIN, y), 10, palette.PENCIL, 0.2,
                      align="right")
            typo.draw(surface, equation(reaction), (MARGIN + 10, y + 15), 10,
                      palette.PENCIL, 0.2)
            y += step

    def _genes(self, surface: pygame.Surface) -> None:
        # Fitted to the list, like the reactions page and for the same reason:
        # two more genes and the last row was printing over the bottom rule.
        half = (len(gene_data.GENES) + 1) // 2
        step = min(52.0, (668 - TOP) / max(1, half))
        for n, gene in enumerate(gene_data.GENES):
            column, row = divmod(n, half)
            x = MARGIN + column * COLUMN
            y = TOP + row * step
            typo.draw(surface, gene.label, (x, y), 12, palette.INK, 0.2)
            if gene.markable:
                typo.draw(surface, f"baseline {gene.baseline:.0%}", (x + 400, y),
                          10, palette.PENCIL, 0.2)
            else:
                typo.draw(surface, "cannot be marked", (x + 400, y), 10,
                          palette.PENCIL, 0.2)
            # the note runs under the label, so it has the whole column: the
            # baseline reading beside it is on the line above
            for i, line in enumerate(_wrap(gene.note, 10, COLUMN - 44)):
                typo.draw(surface, line, (x + 8, y + 15 + i * 13), 10,
                          palette.PENCIL, 0.2)


    def _diet(self, surface: pygame.Surface) -> None:
        from ..data import foods as food_data

        typo.draw(surface,
                  "Relish is the pleasure of eating, and it is a need rather "
                  "than a vice. A lineage that never has any builds badly, so "
                  "the question is not whether to have some but what you are "
                  "willing to pay for it.",
                  (MARGIN, TOP - 4), 11, palette.INK, 0.2)
        typo.draw(surface,
                  "Damage goes as the square of intake above the forgiven "
                  "column, so one portion of something rich is nearly free and "
                  "four are not. It never heals. Relish saturates, so past a "
                  "point more indulgence buys no more happiness — only more "
                  "damage.",
                  (MARGIN, TOP + 16), 11, palette.PENCIL, 0.2)

        head = TOP + 52
        for label, x in (("food", 0), ("enters at", 340), ("relish", 560),
                         ("harm", 640), ("forgiven", 716)):
            typo.caps(surface, label, (MARGIN + x, head), 8,
                      palette.INK_FAINT, 1.2)
        ink.ink_line(surface, (MARGIN, head + 14),
                     (layout.WINDOW[0] - MARGIN, head + 14), 0.5, 5200,
                     palette.INK, 0.4)

        y = head + 24
        for food in food_data.FOODS:
            typo.draw(surface, food.label, (MARGIN, y), 12, palette.INK, 0.2)
            enters = ", ".join(met_data.BY_ID[m].label for m in food.supplies)
            typo.draw(surface, enters, (MARGIN + 340, y), 10, palette.PENCIL, 0.2)
            typo.draw(surface, f"{food.relish:.2f}", (MARGIN + 596, y), 10,
                      palette.PENCIL, 0.0, align="right")
            harm = palette.ALARM if food.harm > 0.5 else palette.PENCIL
            typo.draw(surface, f"{food.harm:.2f}", (MARGIN + 676, y), 10,
                      harm, 0.0, align="right")
            typo.draw(surface,
                      f"{food.forgiven:.2f}" if food.forgiven else "—",
                      (MARGIN + 762, y), 10, palette.PENCIL, 0.0, align="right")
            typo.draw(surface, food.trait, (MARGIN + 8, y + 14), 10,
                      palette.INK_FAINT, 0.2)
            typo.draw(surface, food.note, (MARGIN + 8, y + 27), 10,
                      palette.PENCIL, 0.2)
            y += 46

        note = ("No diet on this page is the right one. Which of them suits a "
                "lineage depends on the constitution it was dealt, and that is "
                "printed on the next page. A cell that handles sugar badly and "
                "a cell that handles fat badly do not want the same meal.")
        for i, line in enumerate(_wrap(note, 10, layout.WINDOW[0] - MARGIN * 2)):
            typo.draw(surface, line, (MARGIN, 646 + i * 13), 10,
                      palette.PENCIL, 0.2)


    #: The page a diet is chosen from. Its own index, so the run can tell
    #: whether a number key means "adopt this diet" or "select that cell".
    KITCHEN = 4

    def _kitchen(self, surface: pygame.Surface) -> None:
        """The menu. Which diet is being eaten is drawn over this, not into it.

        Everything else in the appendix is true for the whole run and is inked
        once. This page is the one thing in it the player changes, so the page
        is the menu and the tick against the current line is an overlay.
        """
        from ..bio import kitchen as kitchen_data
        from ..data import foods as food_data

        intro = ("A diet is not a modifier on the standard broth — it is the "
                 "broth. Change it and the medium turns over at the rate "
                 "perfusion can carry: for twenty or thirty seconds the cell "
                 "eats something that is neither one diet nor the other, and "
                 "there is no way to skip that. Damage already done does not "
                 "come back either.")
        for i, line in enumerate(_wrap(intro, 11,
                                       layout.WINDOW[0] - MARGIN * 2)):
            typo.draw(surface, line, (MARGIN, TOP - 6 + i * 15), 11,
                      palette.INK, 0.2)
        typo.draw(surface,
                  "What it costs is the register. Marks placed for a gate that "
                  "has just closed are worth nothing, lifting costs more than "
                  "placing did, and the oldest marks cost the most — so a "
                  "change of diet is a bill, not a re-roll.",
                  (MARGIN, TOP + 26), 11, palette.PENCIL, 0.2)

        head = TOP + 56
        for label, x, align in (("diet", 30, "left"),
                                ("what it serves", 230, "left"),
                                ("sugar", 700, "right"),
                                ("fructose", 780, "right"),
                                ("fat", 852, "right"),
                                ("amino", 922, "right"),
                                ("relish", 1000, "right"),
                                ("harm", 1074, "right")):
            typo.caps(surface, label, (MARGIN + x, head), 8,
                      palette.INK_FAINT, 1.2, align=align)
        ink.ink_line(surface, (MARGIN, head + 14),
                     (layout.WINDOW[0] - MARGIN, head + 14), 0.5, 5300,
                     palette.INK, 0.4)

        y = head + 26
        for n, (name, diet) in enumerate(food_data.MENU.items()):
            typo.draw(surface, str(n + 1), (MARGIN, y), 11, palette.PENCIL, 0.2)
            typo.draw(surface, name, (MARGIN + 30, y), 12, palette.INK, 0.2)
            # the three largest portions and a count of the rest: the whole
            # list will not fit beside the columns, and the tail of a diet is
            # never what distinguishes it from another
            ranked = sorted(diet.items(), key=lambda kv: -kv[1])
            served = " · ".join(f"{food_data.BY_ID[f].label} {p:.2g}"
                                for f, p in ranked[:2])
            if len(ranked) > 2:
                served += f" · and {len(ranked) - 2} more"
            typo.draw(surface, served, (MARGIN + 230, y), 10, palette.PENCIL, 0.2)
            at = kitchen_data.gates(diet, self.constitution)
            for mid, x in (("glucose", 700), ("fructose", 780),
                           ("palmitate", 852), ("glutamate", 922)):
                typo.draw(surface, f"{at.get(mid, 0.0):.1f}", (MARGIN + x, y),
                          10, palette.PENCIL, 0.0, align="right")
            relish = sum(food_data.BY_ID[f].relish * p for f, p in diet.items())
            harm = sum(food_data.BY_ID[f].harm * p for f, p in diet.items())
            typo.draw(surface, f"{relish:.2f}", (MARGIN + 1000, y), 10,
                      palette.PENCIL, 0.0, align="right")
            typo.draw(surface, f"{harm:.2f}",
                      (MARGIN + 1074, y), 10,
                      palette.ALARM if harm > 1.4 else palette.PENCIL, 0.0,
                      align="right")
            y += 30

        # what you can *ask for*, as against what you can order outright
        from ..bio import life as life_mod

        y = 440
        typo.caps(surface, "or ask for a change", (MARGIN, y), 9,
                  palette.INK_FAINT, 1.6)
        ink.ink_line(surface, (MARGIN, y + 14),
                     (layout.WINDOW[0] - MARGIN, y + 14), 0.5, 5310,
                     palette.INK, 0.4)
        for i, line in enumerate(_wrap(
                "A letter nudges the diet you are on rather than replacing it "
                "— and it lands imperfectly, because nobody eats a number. "
                "What it takes out, something else fills: cut one thing "
                "without deciding what replaces it and a good part of what "
                "comes back is whatever was nearest to hand.",
                10, layout.WINDOW[0] - MARGIN * 2)):
            typo.draw(surface, line, (MARGIN, y + 24 + i * 13), 10,
                      palette.PENCIL, 0.2)
        y += 52
        rows = (len(life_mod.INTENTIONS) + 1) // 2
        for n, intention in enumerate(life_mod.INTENTIONS):
            column, row = divmod(n, rows)
            x = MARGIN + column * 588
            row_y = y + row * 32
            typo.draw(surface, chr(ord("a") + n), (x, row_y), 11,
                      palette.PENCIL, 0.2)
            typo.draw(surface, intention.label, (x + 24, row_y), 12,
                      palette.INK, 0.2)
            note = intention.note
            while typo.width(note, 10, 0.2) > 520:
                note = note.rsplit(" ", 1)[0]
            typo.draw(surface, note, (x + 32, row_y + 14), 10,
                      palette.PENCIL, 0.2)

        for i, line in enumerate(_wrap(
                "Sugar and fructose are separate columns because they are "
                "separate doors: fructose joins the pathway below PFK-1, so "
                "the brake on sugar is not on it. Relish and harm are per "
                "portion served, not per portion eaten — transport is "
                "passive, and what a cell actually takes in depends on what it "
                "can clear, so a diet that looks cheap here can still be "
                "expensive to the body holding it.",
                10, layout.WINDOW[0] - MARGIN * 2)):
            typo.draw(surface, line, (MARGIN, 640 + i * 14), 10,
                      palette.PENCIL, 0.2)

    def kitchen_row(self, n: int) -> tuple[float, float]:
        """Where the tick against diet ``n`` goes, in window pixels."""
        return (MARGIN - 14, TOP + 56 + 26 + n * 30 + 6)

    def _happens(self, surface: pygame.Surface) -> None:
        """Everything a run can bring, printed before it brings any of it.

        The list is fixed and public. What is not public is the timing, and
        that is the only thing about a run that is not knowable in advance --
        which is the point of it: a lineage configured with no room to spare is
        one that has bet on nothing happening.
        """
        from ..bio import life as life_mod
        from ..data import foods as food_data

        intro = ("None of these is a punishment for playing badly and none of "
                 "them can be prevented. They are simply a diet you did not "
                 "choose, for a while, whatever you had configured for. Three "
                 "arrive in a run, never in the first two and a half minutes "
                 "and never two at once, and each one announces itself.")
        for i, line in enumerate(_wrap(intro, 11,
                                       layout.WINDOW[0] - MARGIN * 2)):
            typo.draw(surface, line, (MARGIN, TOP - 6 + i * 15), 11,
                      palette.INK, 0.2)

        y = TOP + 44
        for event in life_mod.EVENTS:
            typo.draw(surface, event.label, (MARGIN, y), 13, palette.INK, 0.3)
            typo.draw(surface, f"{event.seconds:.0f} seconds",
                      (MARGIN + 300, y + 2), 10, palette.PENCIL, 0.2)
            brings = []
            for food, portions in event.adds.items():
                brings.append(f"{food_data.BY_ID[food].label} +{portions:g}")
            for food, factor in event.scales.items():
                brings.append(f"{food_data.BY_ID[food].label} ×{factor:g}")
            if event.everything != 1.0:
                brings.append(f"everything ×{event.everything:g}")
            listed = " · ".join(brings)
            while brings and typo.width(listed, 10, 0.2) > 690:
                brings.pop()
                listed = " · ".join(brings) + " · and more"
            typo.draw(surface, listed, (MARGIN + 430, y + 2), 10,
                      palette.PENCIL, 0.2)
            for i, line in enumerate(_wrap(event.tells, 11,
                                           layout.WINDOW[0] - MARGIN * 2 - 20)):
                typo.draw(surface, line, (MARGIN + 12, y + 20 + i * 14), 11,
                          palette.PENCIL, 0.2)
            y += 22 + 14 * max(1, len(_wrap(event.tells, 11,
                                            layout.WINDOW[0] - MARGIN * 2 - 20)))
            y += 12

        for i, line in enumerate(_wrap(
                "The night out is the one with no door. Ethanol is small and "
                "uncharged and crosses the membrane on its own, so nothing on "
                "the register keeps it out — what a lineage can do is be "
                "equipped for what it turns into, which costs one of the "
                "eight and is wasted if the night never comes.",
                10, layout.WINDOW[0] - MARGIN * 2)):
            typo.draw(surface, line, (MARGIN, 644 + i * 14), 10,
                      palette.PENCIL, 0.2)

    def _constitution(self, surface: pygame.Surface) -> None:
        from ..data import constitutions as con_data

        held = self.constitution.id if self.constitution else None
        intro = ("Marks decide what is switched on. A constitution decides "
                 "what switching it on is worth, and no amount of budget "
                 "changes it. Mostly what it decides is what this lineage "
                 "cannot clear — and a substance that sits high in a cell with "
                 "no way to be rid of it is what does the damage. So there is "
                 "no diet here that is simply correct. There is only the one "
                 "that suits the body you were handed.")
        for i, line in enumerate(_wrap(intro, 11,
                                       layout.WINDOW[0] - MARGIN * 2)):
            typo.draw(surface, line, (MARGIN, TOP - 8 + i * 15), 11,
                      palette.INK, 0.2)

        y = TOP + 40
        for con in con_data.CONSTITUTIONS:
            mine = con.id == held
            if mine:
                ink.hand_mark(surface, "tick", (MARGIN - 14, y + 6),
                              seed=ink.seed_of(con.id, 13), size=9.0)
            typo.draw(surface, con.label, (MARGIN, y), 12,
                      palette.INK if mine else palette.INK_FAINT, 0.2)
            typo.draw(surface, con.summary, (MARGIN + 250, y), 11,
                      palette.PENCIL, 0.2)
            typo.draw(surface, _effects(con), (MARGIN + 740, y), 10,
                      palette.INK_FAINT, 0.2)
            if mine:
                for i, line in enumerate(_wrap(con.counsel, 10,
                                               layout.WINDOW[0] - MARGIN * 2 - 20)):
                    typo.draw(surface, line, (MARGIN + 12, y + 17 + i * 13), 10,
                              palette.PENCIL, 0.2)
                y += 17 + 13 * len(_wrap(con.counsel, 10,
                                         layout.WINDOW[0] - MARGIN * 2 - 20))
            else:
                y += 20
            y += 8

        # The plate itself carries this, so the mark it carries it with has to
        # be named somewhere. Drawn rather than described, beside its meaning.
        ink.ink_line(surface, (MARGIN, 634), (MARGIN + 54, 634), 2.2, 811,
                     palette.INK, 0.85)
        ink.ink_curve(surface, [(MARGIN, 648), (MARGIN + 27, 648),
                                (MARGIN + 54, 648)], 1.5, 812, palette.INK,
                      0.8, broken=True)
        typo.draw(surface,
                  "A step this body runs below standard is printed on the "
                  "plate thinner and broken, like the lower of these two. The "
                  "chart is the same chart every run; the inking is not.",
                  (MARGIN + 70, 634), 10, palette.PENCIL, 0.2)

        typo.draw(surface,
                  "Nothing here is hidden: every constitution in the game is "
                  "on this page, and the one this lineage holds is ticked. "
                  "Knowing which you have is the easy half.",
                  (MARGIN, 664), 10, palette.PENCIL, 0.2)


    def _specialisms(self, surface: pygame.Surface) -> None:
        from ..data import specialisms as spec_data
        from .. import tuning

        intro = (f"A specialism is nothing but marks in bulk. What the shove "
                 f"buys is clearing the inherited pattern in one go instead of "
                 f"lifting each old mark by hand; what it costs is "
                 f"{tuning.DIFFERENTIATION_COST:g} of the same eight, on top of "
                 f"the five the new pattern holds. Every one of these has "
                 f"switched something important off, and is only viable if a "
                 f"neighbour covers the gap — which means a junction, and "
                 f"junctions are shared and lossy. Shift and a number.")
        for i, line in enumerate(_wrap(intro, 11,
                                       layout.WINDOW[0] - MARGIN * 2)):
            typo.draw(surface, line, (MARGIN, TOP - 8 + i * 15), 11,
                      palette.INK, 0.2)

        y = TOP + 56
        for n, spec in enumerate(spec_data.SPECIALISMS):
            typo.draw(surface, f"shift {n + 1}", (MARGIN, y), 10,
                      palette.INK_FAINT, 0.2)
            typo.draw(surface, spec.label, (MARGIN + 74, y), 12, palette.INK, 0.2)
            typo.draw(surface, spec.summary, (MARGIN + 280, y), 11,
                      palette.PENCIL, 0.2)
            marks = " · ".join(
                [f"{g}+" for g in spec.activate] + [f"{g}−" for g in spec.silence])
            typo.draw(surface, marks, (MARGIN + 84, y + 16), 10,
                      palette.INK_FAINT, 0.2)
            typo.draw(surface, f"needs {spec.needs}", (MARGIN + 84, y + 30), 10,
                      palette.PENCIL, 0.2)
            typo.draw(surface, f"gives {spec.gives}", (MARGIN + 84, y + 44), 10,
                      palette.PENCIL, 0.2)
            y += 68

        typo.draw(surface,
                  "Junctions form between a parent and its daughter and nowhere "
                  "else, so the shape of the lineage is the transport network. "
                  "Nothing is routed: material moves down its own gradient, and "
                  "every hop needs a fresh one, so most of what a distant cell "
                  "needs never arrives.",
                  (MARGIN, 664), 10, palette.PENCIL, 0.2)

        # The fourth verb, printed beside the third because they are the two
        # that reach past one cell: differentiating changes what a cell is,
        # fixing changes what the whole lineage is, and only one of them can be
        # taken back. The genes page has no room and this is where it belongs.
        from .. import tuning as tune
        y = 556
        ink.ink_line(surface, (MARGIN, y - 12),
                     (layout.WINDOW[0] - MARGIN, y - 12), 0.5, 5400,
                     palette.INK, 0.4)
        ink.hand_mark(surface, "tick", (MARGIN + 22, y + 12),
                      seed=5401, size=9.5)
        ink.hand_mark(surface, "box", (MARGIN + 108, y + 12), seed=5402,
                      size=13.0, aspect=8.0)
        typo.draw(surface, "a mark", (MARGIN + 40, y + 5), 11,
                  palette.PENCIL, 0.2)
        for i, line in enumerate(_wrap(
                f"Ctrl-click writes a mark into the genome, and there is no "
                f"way back from it. It leaves the budget, it never drifts, "
                f"differentiation does not clear it, and it can never be "
                f"lifted at any price. It costs {tune.FIX_COST:.0f} of biomass "
                f"and the mark has to have been held for {tune.FIX_AGE:.0f} "
                f"seconds first — a heritable change is one that persisted. "
                f"And it reaches every cell in the lineage, including the ones "
                f"it does not suit, which is the decision it is for: a feeder "
                f"and a burner do not want the same genes switched on.",
                10, layout.WINDOW[0] - MARGIN * 2 - 220)):
            typo.draw(surface, line, (MARGIN + 220, y + i * 14), 10,
                      palette.PENCIL, 0.2)


def _effects(con, width: float = 430.0) -> str:
    """The trait in shorthand, so the page is a table and not a story.

    Trimmed to the column rather than allowed to run off the paper: a thrifty
    constitution touches seven things and used to print the last of them into
    the margin and past the edge of the page.
    """
    from ..data import metabolites as met
    bits = []
    for row, factor in con.capacity.items():
        bits.append(f"{row.replace('_', ' ')} ×{factor:g}")
    for mid, factor in con.holds.items():
        bits.append(f"holds {met.BY_ID[mid].label} ×{factor:g}")
    for mid, factor in con.affinity.items():
        bits.append(f"needs {met.BY_ID[mid].label} ×{factor:g}")
    if con.absorbs:
        low = min(con.absorbs.values())
        high = max(con.absorbs.values())
        bits.append("takes up ×%g" % (low if low == high else high))
    if not bits:
        return "—"
    shown = ""
    for n, bit in enumerate(bits):
        trial = f"{shown} · {bit}" if shown else bit
        if typo.width(f"{trial} · and {len(bits) - n - 1} more", 10, 0.2) > width:
            return f"{shown} · and {len(bits) - n} more" if shown else bit
        shown = trial
    return shown


def _wrap(text: str, size: int, width: float) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if typo.width(trial, size, 0.2) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines
