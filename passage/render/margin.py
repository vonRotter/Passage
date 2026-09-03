"""Annotation: the diagnosis, out on a leader line, in the margin.

The plate never carries a floating tooltip. When the game has something to say
about a feature, it rules a leader line from that feature out to the margin and
writes the note there, the way the reference plate does. That is not only a
style rule -- a note pinned to the edge of the page can be read while still
looking at the thing it describes, which a box hovering over the drawing
cannot.

Three registers of text, and the difference between them is the point:

* the **headline** in ink, because it is what the plate is telling you;
* the **detail** in pencil, with the numbers named;
* the **remedy** in pencil, indented, because it is advice rather than fact.

The player's own marks on the register are drawn, not typed, by
``ink.hand_mark`` -- so the contrast between the machine-set plate and the hand
over it holds even here.
"""

from __future__ import annotations

import pygame

from ..bio.diagnose import Reason
from ..bio.marks import Kind, Marks
from ..data import layout
from . import ink, palette, type as typo
from .interact import gene_rows

MARGIN_X = layout.PANEL[0] + 18
MARGIN_WIDTH = layout.WINDOW[0] - MARGIN_X - 22
NOTE_TOP = 512
NOTE_BOTTOM = 690


def wrap(text: str, size: int, width: float) -> list[str]:
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


def annotate(surface: pygame.Surface, reason: Reason, anchor: tuple[float, float],
             seed: int = 0) -> None:
    """Rule a leader from the feature to the margin, and write the note there."""
    y = NOTE_TOP
    ink.leader(surface, anchor, (MARGIN_X - 8, y + 4), seed=seed,
               colour=palette.INK, alpha=0.7)

    for line in wrap(reason.headline, 12, MARGIN_WIDTH):
        typo.draw(surface, line, (MARGIN_X, y), 12, palette.INK, 0.2)
        y += 16
    y += 4
    for line in wrap(reason.detail, 11, MARGIN_WIDTH):
        if y > NOTE_BOTTOM:
            return
        typo.draw(surface, line, (MARGIN_X, y), 11, palette.PENCIL, 0.2)
        y += 14
    if reason.remedy:
        y += 6
        for line in wrap(reason.remedy, 11, MARGIN_WIDTH - 10):
            if y > NOTE_BOTTOM:
                typo.draw(surface, "…", (MARGIN_X + 10, y), 11, palette.PENCIL)
                return
            typo.draw(surface, line, (MARGIN_X + 10, y), 11, palette.PENCIL, 0.2)
            y += 14


def budget(surface: pygame.Surface, marks: Marks) -> None:
    """What the player has spent, and what lifting a mark is still costing them."""
    x, right = MARGIN_X, layout.WINDOW[0] - 22
    typo.caps(surface, "marks", (x, 448), 9, palette.INK_FAINT, 1.6)
    ink.ink_line(surface, (x, 462), (right, 462), 0.5, 73, palette.INK, 0.4)
    typo.draw(surface, "placed", (x, 470), 11, palette.INK, 0.2)
    typo.draw(surface, f"{marks.held:.0f} of {marks.budget:.0f}", (right, 470), 11,
              palette.INK, 0.0, align="right")
    if marks.owed > 0.05:
        typo.draw(surface, "owed for lifting", (x, 486), 11, palette.ALARM, 0.2)
        typo.draw(surface, f"{marks.owed:.1f}", (right, 486), 11, palette.ALARM,
                  0.0, align="right")
    else:
        typo.draw(surface, "generation", (x, 486), 11, palette.PENCIL, 0.2)
        typo.draw(surface, f"{marks.generation}", (right, 486), 11, palette.PENCIL,
                  0.0, align="right")


class RegisterHand:
    """The player's marks, drawn onto the printed register and kept.

    Every mark is a small drawing, and drawing one is a handful of jittered
    strokes. Re-inking eighteen of them sixty times a second would be the same
    mistake the cached plate exists to avoid, so each is stamped once per
    (kind, fade) and blitted after that.
    """

    def __init__(self, net) -> None:
        self.net = net
        self.rows = gene_rows(net)
        self._stamps: dict[tuple, pygame.Surface] = {}

    def _stamp(self, gene: str, kind: Kind, fade: float) -> pygame.Surface:
        key = (gene, kind, round(fade, 2))
        layer = self._stamps.get(key)
        if layer is None:
            side = 34
            layer = pygame.Surface((side, side), pygame.SRCALPHA)
            centre = (side / 2, side / 2)
            ink.hand_mark(layer, "circle" if kind is Kind.SILENCING else "tick",
                          centre, seed=ink.seed_of(gene, 11), size=9.5, fade=fade)
            self._stamps[key] = layer
        return layer

    def draw(self, surface: pygame.Surface, marks: Marks) -> None:
        for gene, mark in marks.marks.items():
            rect = self.rows.get(gene)
            if rect is None:
                continue
            fade = min(0.68, mark.inherited * 0.17)
            stamp = self._stamp(gene, mark.kind, fade)
            surface.blit(stamp, (int(rect[0] - 12), int(rect[1] + rect[3] / 2 - 17)))

    def draw_debt(self, surface: pygame.Surface, marks: Marks) -> None:
        """A gene still in debt for being un-marked keeps a struck-out ghost."""
        for debt in marks.debts:
            rect = self.rows.get(debt.gene)
            if rect is None or debt.amount < 0.1:
                continue
            fade = 0.45 + 0.25 * (1.0 - min(1.0, debt.amount / 2.0))
            stamp = self._stamp(debt.gene, Kind.SILENCING, fade)
            surface.blit(stamp, (int(rect[0] - 12), int(rect[1] + rect[3] / 2 - 17)))
