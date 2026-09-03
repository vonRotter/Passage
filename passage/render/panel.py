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
         elapsed: float, vigour=None, lineage=None) -> None:
    x = layout.PANEL[0] + 18
    right = layout.WINDOW[0] - 20

    constitution = getattr(flow, "constitution", None)
    if constitution is not None:
        typo.caps(surface, "constitution", (x, 44), 9, palette.INK_FAINT, 1.6)
        typo.draw(surface, constitution.label, (x, 58), 11, palette.INK, 0.2)

    typo.caps(surface, "target", (x, 86), 9, palette.INK_FAINT, 1.6)
    built = lineage.biomass() if lineage is not None else cell.pool("biomass")
    typo.draw(surface, "biomass", (x, 102), 13, palette.INK, 0.3)
    typo.draw(surface, f"{built:.0f}", (right, 102), 13, palette.INK, 0.0,
              align="right")
    if lineage is not None and len(lineage.living) > 1:
        typo.draw(surface, f"{len(lineage.living)} cells · "
                           f"{cell.pool('biomass'):.0f} in this one",
                  (x, 118), 9, palette.PENCIL, 0.2)

    _carriers(surface, cell, x, right)

    typo.caps(surface, "rates", (x, 200), 9, palette.INK_FAINT, 1.6)
    ink.ink_line(surface, (x, 214), (right, 214), 0.5, 71, palette.INK, 0.4)
    for i, (row_id, label) in enumerate(WATCH):
        y = 224 + i * 18
        typo.draw(surface, label, (x, y), 11, palette.INK, 0.2)
        try:
            rate = flow.rate_of(row_id, cell.index)
        except KeyError:
            rate = 0.0
        typo.draw(surface, f"{rate:6.2f}", (right, y), 11,
                  palette.INK if abs(rate) > 1e-3 else palette.INK_FAINT,
                  0.0, align="right")

    typo.caps(surface, "ledger", (x, 348), 9, palette.INK_FAINT, 1.6)
    ink.ink_line(surface, (x, 360), (right, 360), 0.5, 72, palette.INK, 0.4)
    net = flow.net
    used = float(flow.ledger.supplied[net.mi("glucose")])
    waste = float(flow.ledger.spilled.sum())
    rows = [("glucose used", f"{used:.1f}"),
            ("waste spilled", f"{waste:.1f}"),
            ("yield", f"{cell.pool('biomass') / used:.3f}" if used > 1e-6 else "--"),
            ("elapsed", f"{elapsed:.0f}s")]
    if vigour is not None:
        rows = [("food eaten", f"{sum(vigour.eaten.values()):.0f}"),
                ("relish", f"{vigour.relish:.0%}"),
                ("vigour", f"{vigour.vigour:.0%}"),
                ("score", f"{vigour.score(built):.3f}")]
    for i, (label, value) in enumerate(rows):
        y = 370 + i * 18
        typo.draw(surface, label, (x, y), 11, palette.INK, 0.2)
        typo.draw(surface, value, (right, y), 11, palette.INK, 0.0, align="right")

    if paused:
        typo.caps(surface, "paused", (right - 54, 566), 11, palette.INK, 2.4)
    typo.draw(surface, "space pause · tab ref · d divide · shift 1-5 specialise · 1-9 cell",
              (x, 704), 9, palette.PENCIL, 0.2)


def _carriers(surface: pygame.Surface, cell: Cell, x: float,
              right: float) -> None:
    """The two conserved pairs, read as instruments.

    They are deliberately not on the chart. ATP has no node in a biochemical
    drawing -- it rides a curved arrow across the reaction that spends it, and
    that is how the plate draws it. But a stock still has to be readable, and a
    reading belongs in the margin with the other numbers, ruled, and plainly
    not part of the cell.

    Each pair is read against its partner rather than against a maximum. How
    much ATP there is means nothing on its own: the pair is closed, the two
    always sum to the same number, and what the cell can actually do depends
    only on which side of the pair the pool is sitting.
    """
    typo.caps(surface, "carriers", (x, 128), 9, palette.INK_FAINT, 1.6)
    rows = (("energy charge", "atp", "adp"),
            ("reducing power", "nadh", "nad"))
    for i, (label, loaded, spent) in enumerate(rows):
        y = 144 + i * 24
        total = cell.pool(loaded) + cell.pool(spent)
        share = cell.pool(loaded) / total if total > 1e-9 else 0.0
        low = share < 0.2 if loaded == "atp" else False
        typo.draw(surface, label, (x, y), 11, palette.INK, 0.2)
        typo.draw(surface, f"{share:.0%}", (right, y), 11,
                  palette.ALARM if low else palette.INK, 0.0, align="right")
        # the ruled bar: how much of the closed pair sits on the loaded side
        bar_x, bar_w = x + 106, right - x - 146
        ink.ink_line(surface, (bar_x, y + 14), (bar_x + bar_w, y + 14), 0.5,
                     74 + i, palette.INK, 0.2)
        if share > 0.01:
            ink.ink_line(surface, (bar_x, y + 14),
                         (bar_x + bar_w * share, y + 14), 2.2, 76 + i,
                         palette.ALARM if low else palette.INK, 0.55)
