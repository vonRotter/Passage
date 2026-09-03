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

    TITLES = ("the substances", "the reactions", "the genes")
    SUBTITLES = (
        "what is in the cell, what makes it, and what uses it up",
        "every row balances on a real atom count; water and phosphate are "
        "present where the chemistry needs them but never limit anything",
        "what marking one would change, and what it idles at if you leave it",
    )

    def __init__(self, net: Network, seed: int = 9) -> None:
        self.net = net
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
        [self._substances, self._reactions, self._genes][page](surface)
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
