"""The right margin: the target, the rates, and the annotation.

Numbers live here. The plate carries no numerals except the printed ones that
were always part of it, so anything the player needs to read as a figure is in
this column, attached to the plate by a leader line when it refers to something
in particular.

Bottleneck explanations will land here too, in the margin, in plain words
(spec 3.11) -- that is M2, once there are marks to blame.
"""

from __future__ import annotations

from ..bio.cell import Cell
from ..bio.flow import Flow
from ..data import layout
from . import ink, palette, type as typo

import pygame

#: The handful of rates worth a printed row. Everything else is on the plate.
WATCH = [
    ("exchange_glucose", "glucose in"),
    ("glycolysis_upper", "glycolysis"),
    ("pdh", "into the cycle"),
    ("oxphos", "respiration"),
    ("fermentation", "fermentation"),
    ("biosynthesis", "growth"),
    ("maintenance", "upkeep"),
]


def draw(surface: pygame.Surface, flow: Flow, cell: Cell, paused: bool,
         elapsed: float) -> None:
    x = layout.PANEL[0] + 18
    right = layout.WINDOW[0] - 20

    typo.caps(surface, "target", (x, 62), 9, palette.INK_FAINT, 1.6)
    typo.draw(surface, "biomass", (x, 78), 13, palette.INK, 0.3)
    typo.draw(surface, f"{cell.pool('biomass'):.1f}", (right, 78), 13,
              palette.INK, 0.0, align="right")

    typo.caps(surface, "energy charge", (x, 108), 9, palette.INK_FAINT, 1.6)
    charge = cell.energy_charge()
    typo.draw(surface, f"{charge:.0%}", (right, 104), 13,
              palette.INK if charge > 0.2 else palette.ALARM, 0.0, align="right")

    typo.caps(surface, "rates", (x, 146), 9, palette.INK_FAINT, 1.6)
    ink.ink_line(surface, (x, 160), (right, 160), 0.5, 71, palette.INK, 0.4)
    for i, (row_id, label) in enumerate(WATCH):
        y = 170 + i * 20
        typo.draw(surface, label, (x, y), 11, palette.INK, 0.2)
        try:
            rate = flow.rate_of(row_id, cell.index)
        except KeyError:
            rate = 0.0
        typo.draw(surface, f"{rate:6.2f}", (right, y), 11,
                  palette.INK if abs(rate) > 1e-3 else palette.INK_FAINT,
                  0.0, align="right")

    typo.caps(surface, "ledger", (x, 336), 9, palette.INK_FAINT, 1.6)
    ink.ink_line(surface, (x, 350), (right, 350), 0.5, 72, palette.INK, 0.4)
    net = flow.net
    used = float(flow.ledger.supplied[net.mi("glucose")])
    waste = float(flow.ledger.spilled.sum())
    rows = [("glucose used", f"{used:.1f}"),
            ("waste spilled", f"{waste:.1f}"),
            ("yield", f"{cell.pool('biomass') / used:.3f}" if used > 1e-6 else "--"),
            ("elapsed", f"{elapsed:.0f}s")]
    for i, (label, value) in enumerate(rows):
        y = 360 + i * 20
        typo.draw(surface, label, (x, y), 11, palette.INK, 0.2)
        typo.draw(surface, value, (right, y), 11, palette.INK, 0.0, align="right")

    if paused:
        typo.caps(surface, "paused", (x, 464), 11, palette.INK, 2.4)
        ink.hand_mark(surface, "underline", (x + 34, 482), seed=88, size=36,
                      colour=palette.PENCIL)
    typo.draw(surface, "space  pause     f1  rates     f2  balance",
              (x, 668), 9, palette.PENCIL, 0.2)
