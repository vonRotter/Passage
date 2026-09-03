"""The left margin: the cell roster, and later the lineage tree.

Every cell, its dominant pathway, its worst-off metabolite, and whether it is
starving or spilling (spec 3.11). At M1 there is one cell, so this is mostly a
frame waiting for M3 -- but the frame is what tells the player that a lineage is
the unit, not a cell.

The tree, when it arrives, is hand-ruled in pencil rather than ink, with each
cell a small circle carrying its dominant class colour.
"""

from __future__ import annotations

import pygame

from ..bio.cell import Cell
from ..data import layout
from . import ink, palette, type as typo


#: One drawn blob per (class, selected) pair, inked once. Only the text under
#: it changes from frame to frame, and text is cheap.
_STAMPS: dict[tuple, pygame.Surface] = {}
SIDE = 68


def _stamp(colour, strength: float, selected: bool, slot: int) -> pygame.Surface:
    key = (colour, round(strength, 2), selected, slot)
    layer = _STAMPS.get(key)
    if layer is None:
        layer = pygame.Surface((SIDE, SIDE + 18), pygame.SRCALPHA)
        shape = ink.blob((SIDE / 2, SIDE / 2), 22, seed=900 + slot * 5,
                         wobble=0.13)
        ink.wash(layer, shape, colour, seed=910 + slot * 5,
                 strength=0.35 + strength * 0.75)
        ink.ink_curve(layer, shape, 1.5 if selected else 0.9,
                      seed=920 + slot * 5, closed=True,
                      alpha=1.0 if selected else 0.55)
        if selected:
            ink.hand_mark(layer, "underline", (SIDE / 2, SIDE / 2 + 30),
                          seed=930 + slot, size=24, colour=palette.PENCIL)
        _STAMPS[key] = layer
    return layer


def draw(surface: pygame.Surface, cells: list[Cell], selected: int) -> None:
    x, y, w, _ = layout.ROSTER
    top = 76
    for i, cell in enumerate(cells):
        cy = top + i * 92
        weights, strength = cell.cast()
        surface.blit(_stamp(palette.blend(weights), strength, i == selected, i % 8),
                     (int(x + 46 - SIDE / 2), int(cy + 26 - SIDE / 2)))

        typo.caps(surface, cell.dominant_pathway(), (x + 82, cy + 12), 9,
                  palette.INK_FAINT, 1.1)
        worst = cell.worst_metabolite()
        state = ("starving" if cell.starving()
                 else "spilling" if cell.spilling() else "running")
        typo.draw(surface, state, (x + 82, cy + 28), 11, palette.INK, 0.2)
        typo.draw(surface, f"low: {worst.label}", (x + 82, cy + 44), 9,
                  palette.PENCIL, 0.2)
