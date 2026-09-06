"""The last page: what the run came to, printed like the rest of the appendix.

Deliberately not a scoreboard. The number is there, but it is set beside the
four things that made it and beside the one act the run could not take back, so
the page reads as an account of a lineage rather than a result screen. The
plate taught the player to read a page; the ending is a page.
"""

from __future__ import annotations

import pygame

from .. import tuning
from ..data import layout
from . import ink, palette, roster, type as typo

MARGIN = 54
TOP = 100


def _wrap(text: str, size: int, width: float) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if typo.width(trial, size, 0.2) <= width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _in_words(net, entry: str) -> str:
    """The history keeps gene ids; a printed page wants the printed name."""
    for gene in net.genes:
        entry = entry.replace(f" {gene.id}", f" {gene.label}")
        if entry.endswith(f" {gene.id},"):
            entry = entry[:-len(gene.id) - 1] + gene.label + ","
    return entry


class Final:
    """Inked once, when the bell goes, and blitted after that."""

    def __init__(self, ending, seed: int = 77) -> None:
        self.ending = ending
        self.seed = seed
        self._page: pygame.Surface | None = None

    def surface(self) -> pygame.Surface:
        if self._page is None:
            self._page = self._ink()
        return self._page

    def _ink(self) -> pygame.Surface:
        e = self.ending
        page = ink.paper(layout.WINDOW, self.seed).copy()
        typo.caps(page, "passage", (MARGIN, 34), 13, palette.INK, 3.0)
        typo.caps(page, "the reckoning", (MARGIN, 58), 11, palette.INK_FAINT, 2.4)
        typo.draw(page, f"{e.elapsed / 60:.0f} minutes  ·  "
                        f"generation {e.lineage.generation}  ·  "
                        f"{e.lineage.divisions} divisions",
                  (layout.WINDOW[0] - MARGIN, 60), 10, palette.PENCIL, 0.2,
                  align="right")
        ink.ink_line(page, (MARGIN, 78), (layout.WINDOW[0] - MARGIN, 78), 0.7,
                     7000, palette.INK, 0.55)

        self._score(page)
        self._account(page)
        self._genome(page)
        self._ate(page)
        self._tree(page)
        self._did(page)

        ink.ink_line(page, (MARGIN, 668), (layout.WINDOW[0] - MARGIN, 668), 0.6,
                     7001, palette.INK, 0.4)
        typo.draw(page, "escape to close  ·  the run is over and nothing here "
                        "can be changed, which is rather the point",
                  (MARGIN, 682), 10, palette.PENCIL, 0.2)
        return page

    # -- the number, and what decided it -------------------------------------
    def _score(self, page: pygame.Surface) -> None:
        e = self.ending
        typo.caps(page, "score", (MARGIN, TOP), 9, palette.INK_FAINT, 1.6)
        typo.draw(page, f"{e.score:.3f}", (MARGIN, TOP + 20), 34,
                  palette.ALARM if e.extinct else palette.INK, 0.0)

        for i, line in enumerate(_wrap(e.decided_by(), 12, 400)):
            typo.draw(page, line, (MARGIN + 230, TOP + 14 + i * 17), 12,
                      palette.INK, 0.2)

    # -- the four factors, ruled ---------------------------------------------
    def _account(self, page: pygame.Surface) -> None:
        y = TOP + 90
        typo.caps(page, "the account", (MARGIN, y), 9, palette.INK_FAINT, 1.6)
        ink.ink_line(page, (MARGIN, y + 14), (MARGIN + 606, y + 14), 0.5, 7010,
                     palette.INK, 0.4)
        y += 28
        for n, line in enumerate(self.ending.lines()):
            typo.draw(page, line.label, (MARGIN, y), 12, palette.INK, 0.2)
            typo.draw(page, line.value, (MARGIN + 200, y), 12, palette.INK,
                      0.0, align="right")
            typo.draw(page, line.note, (MARGIN + 224, y + 1), 10,
                      palette.PENCIL, 0.2)
            # what this factor took, drawn rather than stated: a short rule
            # whose length is the loss. A number in a column is easy to skim
            # past; a bar that is longer than its neighbours is not.
            if line.weight > 0.01:
                ink.ink_line(page, (MARGIN + 452, y + 7),
                             (MARGIN + 452 + 120 * min(1.0, line.weight),
                              y + 7), 2.2, 7020 + n, palette.ALARM, 0.55)
                typo.draw(page, f"−{line.weight:.0%}", (MARGIN + 600, y), 10,
                          palette.ALARM, 0.0, align="right")
            y += 24

    # -- what it leaves ------------------------------------------------------
    def _genome(self, page: pygame.Surface) -> None:
        e = self.ending
        y = TOP + 244
        typo.caps(page, "written into the genome", (MARGIN, y), 9,
                  palette.INK_FAINT, 1.6)
        ink.ink_line(page, (MARGIN, y + 14), (MARGIN + 606, y + 14), 0.5, 7030,
                     palette.INK, 0.4)
        y += 28
        written = e.written_in()
        if not written:
            typo.draw(page, "—", (MARGIN, y), 12, palette.PENCIL, 0.2)
            y += 22
        for n, (label, kind) in enumerate(written):
            ink.hand_mark(page, "box", (MARGIN + 132, y + 6),
                          seed=ink.seed_of(label, 23), size=11.0,
                          aspect=10.4, colour=palette.INK)
            typo.draw(page, label, (MARGIN + 16, y), 12, palette.INK, 0.2)
            typo.draw(page, kind, (MARGIN + 268, y + 1), 10, palette.PENCIL, 0.2)
            y += 26

        y = max(y + 14, TOP + 340)
        for i, line in enumerate(_wrap(e.epitaph(), 11, 590)):
            typo.draw(page, line, (MARGIN, y + i * 15), 11, palette.PENCIL, 0.2)

    # -- what the player did -------------------------------------------------
    def _did(self, page: pygame.Surface) -> None:
        """The run as a list of decisions, in the order they were taken.

        The rest of this page is what happened. This is what the player did,
        which is not the same thing and is the half they can learn from. It is
        the marks' own history, which every cell has been keeping all along for
        exactly this.
        """
        e = self.ending
        y = TOP + 410
        typo.caps(page, "what you did", (MARGIN, y), 9, palette.INK_FAINT, 1.6)
        ink.ink_line(page, (MARGIN, y + 14), (MARGIN + 606, y + 14), 0.5, 7070,
                     palette.INK, 0.4)
        y += 26

        seen: set[str] = set()
        done: list[str] = []
        for member in e.lineage.members:
            for entry in member.marks.history:
                if entry not in seen:
                    seen.add(entry)
                    done.append(entry)
        if not done:
            typo.draw(page, "nothing. The lineage ran on the genes it was "
                            "handed, at the levels they idle at.",
                      (MARGIN, y), 11, palette.PENCIL, 0.2)
            return

        # the tail, because the last things done are the ones still in mind
        room = 7
        if len(done) > room:
            typo.draw(page, f"…{len(done) - room} earlier", (MARGIN, y), 10,
                      palette.INK_FAINT, 0.2)
            y += 16
            done = done[-room:]
        net = e.lineage.net
        for entry in done:
            generation, _, what = entry.partition(": ")
            typo.draw(page, generation, (MARGIN, y), 10, palette.INK_FAINT, 0.2)
            colour = (palette.ALARM if what.startswith("lifted")
                      else palette.INK if what.startswith("fixed")
                      else palette.PENCIL)
            typo.draw(page, _in_words(net, what), (MARGIN + 32, y), 11,
                      colour, 0.2)
            y += 16

    # -- what it ate ---------------------------------------------------------
    def _ate(self, page: pygame.Surface) -> None:
        """Where the food actually went, by food, over the whole run.

        The score charges for everything absorbed, so a player looking at a bad
        yield needs to see what they were absorbing. This is the only place in
        the game that totals it.
        """
        from ..data import foods as food_data

        e = self.ending
        x0, y = 700, TOP
        typo.caps(page, "what it ate", (x0, y), 9, palette.INK_FAINT, 1.6)
        ink.ink_line(page, (x0, y + 14), (layout.WINDOW[0] - MARGIN, y + 14),
                     0.5, 7050, palette.INK, 0.4)
        y += 28
        ranked = sorted(e.vigour.eaten.items(), key=lambda kv: -kv[1])
        total = sum(v for _, v in ranked) or 1.0
        for n, (food_id, amount) in enumerate(ranked):
            if amount < 0.5:
                continue
            food = food_data.BY_ID[food_id]
            typo.draw(page, food.label, (x0, y), 11, palette.INK, 0.2)
            typo.draw(page, f"{amount:.0f}", (x0 + 320, y), 11, palette.PENCIL,
                      0.0, align="right")
            share = amount / total
            ink.ink_line(page, (x0 + 336, y + 7),
                         (x0 + 336 + 170 * share, y + 7), 2.2, 7060 + n,
                         palette.ALARM if food.harm > 0.5 else palette.INK,
                         0.45)
            y += 20
        typo.draw(page, "a rule in red is a food that was charging for itself",
                  (x0, y + 8), 10, palette.PENCIL, 0.2)

    # -- the lineage, as it finished -----------------------------------------
    def _tree(self, page: pygame.Surface) -> None:
        """The tree, redrawn at the right of the page rather than in the margin.

        It is the one part of the run that is a picture of a decision rather
        than a number, and the reckoning is the only place it is ever seen at
        rest. Cropped to what the tree actually occupies: the roster is sized
        for a margin that runs the height of the window, and blitting all of
        that would put a column of empty paper on the page.
        """
        e = self.ending
        x0, y0 = 700, TOP + 244
        typo.caps(page, "the lineage", (x0, y0), 9, palette.INK_FAINT, 1.6)
        ink.ink_line(page, (x0, y0 + 14), (layout.WINDOW[0] - MARGIN, y0 + 14),
                     0.5, 7040, palette.INK, 0.4)
        panel = pygame.Surface((layout.ROSTER[2], layout.ROSTER[3]),
                               pygame.SRCALPHA)
        roster.draw(panel, e.lineage, -1)
        where = roster.positions(e.lineage).values()
        top = max(0, int(min(y for _, y in where)) - 18)
        bottom = min(layout.ROSTER[3] - 200, int(max(y for _, y in where)) + 22)
        # and never so tall that it runs over the two lines beneath it
        room = 616 - (y0 + 22)
        page.blit(panel, (x0 - 6, y0 + 22),
                  pygame.Rect(0, top, layout.ROSTER[2],
                              max(40, min(bottom - top, room))))

        y = min(626, y0 + 34 + (bottom - top))
        typo.draw(page, f"{len(e.lineage.living)} alive of "
                        f"{len(e.lineage.members)}",
                  (x0, y), 10, palette.PENCIL, 0.2)
        lost = len(e.lineage.drifted)
        if lost:
            typo.draw(page, f"{lost} mark{'s' if lost != 1 else ''} lost to "
                            f"drift on the way down",
                      (x0, y + 15), 10, palette.PENCIL, 0.2)
