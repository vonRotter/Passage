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
    """Three pages, inked once each, turned with the arrow keys."""

    TITLES = ("the substances", "the reactions", "the genes", "the diet",
              "the constitution", "specialisms")
    SUBTITLES = (
        "what is in the cell, what makes it, and what uses it up",
        "every row balances on a real atom count; water and phosphate are "
        "present where the chemistry needs them but never limit anything",
        "what marking one would change, and what it idles at if you leave it",
        "relish against damage, and what it leaves behind",
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
         self._constitution, self._specialisms][page](surface)
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
        y = TOP
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
            y += 38

    def _genes(self, surface: pygame.Surface) -> None:
        half = (len(gene_data.GENES) + 1) // 2
        for n, gene in enumerate(gene_data.GENES):
            column, row = divmod(n, half)
            x = MARGIN + column * COLUMN
            y = TOP + row * 52
            typo.draw(surface, gene.label, (x, y), 12, palette.INK, 0.2)
            if gene.markable:
                typo.draw(surface, f"baseline {gene.baseline:.0%}", (x + 400, y),
                          10, palette.PENCIL, 0.2)
            else:
                typo.draw(surface, "cannot be marked", (x + 400, y), 10,
                          palette.PENCIL, 0.2)
            for i, line in enumerate(_wrap(gene.note, 10, COLUMN - 130)):
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

        typo.draw(surface,
                  "Nothing here is hidden: every constitution in the game is "
                  "on this page, and the one this lineage holds is ticked. "
                  "Knowing which you have is the easy half.",
                  (MARGIN, 660), 10, palette.PENCIL, 0.2)


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


def _effects(con) -> str:
    """The trait in shorthand, so the page is a table and not a story."""
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
    return " · ".join(bits) if bits else "—"


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
