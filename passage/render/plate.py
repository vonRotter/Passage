"""The plate: the printed page, rendered once and cached.

Paper, the cell envelope, every vessel, every pool outline, the printed labels
and the gene register are drawn one time into a surface and blitted whole. The
only per-frame work is the pool washes and the flow animation, which live in
``flow_vis.py``. If the plate is being re-inked every frame, that is a bug, and
``Plate.inkings`` is there so a test can say so.

Unadopted pathways -- the parts of the plate serving food the lineage has not
taken up -- are printed at very low contrast, as though the ink had faded. They
are legible if the player looks and invisible if they do not. Nothing is ever
hidden; things are merely quiet.
"""

from __future__ import annotations

import numpy as np
import pygame

from ..bio.network import Network, network
from ..data import layout
from ..data.metabolites import Class
from . import ink, palette, type as typo


#: Pools and vessels that only matter once a food source has been adopted.
#: Drawn faintly from the first second so the player can see what exists before
#: they can use it (spec 3.1).
UNADOPTED_POOLS = {"palmitate", "glutamate", "ammonia"}
UNADOPTED_VESSELS = {"beta_oxidation", "lipogenesis", "gdh"}
UNADOPTED_STUBS = {"exchange_palmitate", "exchange_glutamate", "exchange_ammonia"}


class Plate:
    """The printed page. Immutable until the network itself changes."""

    def __init__(self, net: Network | None = None, seed: int = 4,
                 adopted: frozenset[str] = frozenset()) -> None:
        self.net = net or network()
        self.seed = seed
        self.adopted = adopted
        self.inkings = 0                 # how many times the plate was drawn
        self.surface = self._ink_plate()

    # -- what the flow layer needs to know ---------------------------------
    def vessel_path(self, row_id: str) -> list[ink.Point]:
        return _vessel_path(row_id)

    def faded(self, key: str) -> float:
        """0 for full printed weight, up to 0.72 for an unadopted pathway."""
        if key in self.adopted:
            return 0.0
        if key in UNADOPTED_POOLS or key in UNADOPTED_VESSELS or key in UNADOPTED_STUBS:
            return 0.62
        return 0.0

    # -- the one-time inking ------------------------------------------------
    def _ink_plate(self) -> pygame.Surface:
        self.inkings += 1
        page = ink.paper(layout.WINDOW, self.seed).copy()
        self._rule_margins(page)
        self._draw_envelope(page)
        self._draw_vessels(page)
        self._draw_pools(page)
        self._draw_register(page)
        self._draw_headings(page)
        return page

    def _rule_margins(self, page: pygame.Surface) -> None:
        rx, _, rw, _ = layout.ROSTER
        px, _, pw, _ = layout.PANEL
        ink.ink_line(page, (rx + rw, 30), (rx + rw, 690), 0.6, 11, palette.INK, 0.45)
        ink.ink_line(page, (px, 30), (px, 690), 0.6, 12, palette.INK, 0.45)
        top = layout.REGISTER[1] - 12
        ink.ink_line(page, (layout.PLATE[0] + 16, top),
                     (layout.PLATE[0] + layout.PLATE[2] - 16, top),
                     0.7, 13, palette.INK, 0.5)

    def _draw_envelope(self, page: pygame.Surface) -> None:
        centre, radius, squash = layout.CELL_ENVELOPE
        shape = ink.blob(centre, radius, seed=21, squash=squash, wobble=0.09,
                         steps=52)
        ink.ink_curve(page, shape, 1.5, seed=22, closed=True,
                      colour=palette.INK, alpha=0.7)

    def _draw_vessels(self, page: pygame.Surface) -> None:
        for i, (row_id, points) in enumerate(layout.VESSELS.items()):
            fade = self.faded(row_id)
            colour = palette.fade(palette.INK, fade)
            weight = 2.0 - fade * 1.0
            ink.ink_curve(page, points, weight, seed=1000 + i * 7, colour=colour,
                          alpha=1.0 - fade * 0.45)
        for i, (row_id, (a, b)) in enumerate(layout.EXCHANGE_STUBS.items()):
            fade = self.faded(row_id)
            colour = palette.fade(palette.INK, fade)
            ink.ink_line(page, a, b, 1.3 - fade * 0.5, seed=2000 + i * 7,
                         colour=colour, alpha=0.85 - fade * 0.4)

    def _draw_pools(self, page: pygame.Surface) -> None:
        for i, (mid, (x, y, r)) in enumerate(layout.POOLS.items()):
            fade = self.faded(mid)
            colour = palette.fade(palette.INK, fade)
            shape = ink.blob((x, y), r, seed=ink.seed_of(mid, 3), wobble=0.11)
            ink.ink_curve(page, shape, 1.1 - fade * 0.4, seed=ink.seed_of(mid, 31),
                          colour=colour, closed=True, alpha=1.0 - fade * 0.45)
            label = self.net.metabolites[self.net.mi(mid)].label
            dx, dy = layout.POOL_LABEL_OFFSET.get(mid, (0.0, 0.0))
            typo.caps(page, label, (x + dx, y + r + 6 + dy), 9,
                      palette.fade(palette.INK_FAINT, fade * 0.6),
                      spacing=1.1, align="centre")

    def _draw_register(self, page: pygame.Surface) -> None:
        x, y, w, h = layout.REGISTER
        typo.caps(page, "gene register", (x, y + 6), 10, palette.INK, 2.0)
        typo.draw(page, "left click activates · right click silences · "
                       "again to lift, which costs more",
                  (x + 132, y + 6), 10, palette.PENCIL, 0.2)
        markable = [g for g in self.net.genes if g.markable]
        rows = (len(markable) + layout.REGISTER_COLUMNS - 1) // layout.REGISTER_COLUMNS
        col_w = layout.register_column_width()
        for n, gene in enumerate(markable):
            column, row = divmod(n, rows)
            gx, gy = layout.register_cell(row, column)
            typo.draw(page, gene.label, (gx + 18, gy), 11, palette.INK, 0.2)
            # the ruled box the player's mark goes into
            ink.ink_line(page, (gx, gy + 13), (gx + col_w - 20, gy + 13),
                         0.5, 4000 + n, palette.INK, 0.28)

    def _draw_headings(self, page: pygame.Surface) -> None:
        typo.caps(page, "passage", (18, 26), 13, palette.INK, 3.0)
        typo.caps(page, "central metabolism", (layout.PLATE[0] + 16, 26), 11,
                  palette.INK, 2.6)
        typo.caps(page, "lineage", (18, 52), 9, palette.INK_FAINT, 1.6)
        typo.caps(page, "the cell", (layout.PANEL[0] + 18, 26), 11,
                  palette.INK, 2.6)


_PATHS: dict[str, list[ink.Point]] = {}


def _vessel_path(row_id: str) -> list[ink.Point]:
    """The smoothed centre line of a vessel, computed once and kept."""
    if row_id not in _PATHS:
        if row_id in layout.VESSELS:
            _PATHS[row_id] = ink.spline(layout.VESSELS[row_id], step=5.0)
        else:
            a, b = layout.EXCHANGE_STUBS[row_id]
            _PATHS[row_id] = ink.spline([a, b], step=5.0)
    return _PATHS[row_id]


def arclength(path: list[ink.Point]) -> np.ndarray:
    pts = np.asarray(path, dtype=np.float32)
    seg = np.hypot(*(pts[1:] - pts[:-1]).T)
    return np.concatenate([[0.0], np.cumsum(seg)])
