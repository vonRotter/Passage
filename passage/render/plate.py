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
from ..data import layout, reactions as rxn_data
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
                 adopted: frozenset[str] = frozenset(),
                 constitution=None) -> None:
        self.net = net or network()
        self.seed = seed
        self.adopted = adopted
        self.constitution = constitution
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

    def constricted(self, row_id: str) -> float:
        """How far below standard this body runs this step. 1.0 is standard.

        The plate is the same plate every run -- it has to be, or nobody could
        ever learn it -- but the body reading it is not the same body. This is
        what makes one run's page differ from another's without a single
        coordinate moving: the shape is printed, the constitution is inked.
        """
        con = self.constitution
        if con is None:
            return 1.0
        weakest = con.capacity.get(row_id, 1.0)
        reaction = rxn_data.BY_ID.get(row_id.removesuffix("_back"))
        if reaction is not None:
            # poor affinity for a substrate constricts the step just as surely
            # as a weak enzyme does, and the player has to see both
            for mid, factor in con.affinity.items():
                if factor > 1.0 and mid in reaction.inputs:
                    weakest = min(weakest, 1.0 / factor)
        return weakest

    # -- the one-time inking ------------------------------------------------
    def _ink_plate(self) -> pygame.Surface:
        self.inkings += 1
        page = ink.paper(layout.WINDOW, self.seed).copy()
        self._rule_margins(page)
        self._draw_envelope(page)
        self._draw_compartment(page)
        self._draw_vessels(page)
        self._draw_tributaries(page)
        self._draw_pools(page)
        self._draw_register(page)
        self._draw_headings(page)
        return page

    def _draw_compartment(self, page: pygame.Surface) -> None:
        """The mitochondrion: a double line, because it is a double membrane."""
        centre, radius, squash = layout.MITOCHONDRION
        shape = ink.blob(centre, radius, seed=31, squash=squash, wobble=0.075,
                         steps=44)
        ink.membrane(page, shape, seed=32, colour=palette.INK, alpha=0.6)
        typo.caps(page, "mitochondrion",
                  (centre[0] + radius * 0.34, centre[1] - radius * squash + 14),
                  8, palette.INK_FAINT, 2.0, align="centre")

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
        centre, radius, squash, fullness = layout.CELL_ENVELOPE
        shape = ink.blob(centre, radius, seed=21, squash=squash, wobble=0.06,
                         steps=64, fullness=fullness)
        ink.ink_curve(page, shape, 1.1, seed=22, closed=True,
                      colour=palette.INK, alpha=0.42)
        # the space the exchange stubs run out into, which is otherwise unnamed
        typo.caps(page, "the medium", (222, 96), 8, palette.INK_FAINT, 2.0)

    def _draw_vessels(self, page: pygame.Surface) -> None:
        """Every reaction: the vessel, its arrowhead, its cofactor, its enzyme.

        Weight carries hierarchy — the trunk heavy, the side reactions light —
        because drawing every line the same is most of what makes a diagram look
        machine-made rather than drawn.
        """
        for i, (row_id, points) in enumerate(layout.VESSELS.items()):
            fade = self.faded(row_id)
            colour = palette.fade(palette.INK, fade)
            narrow = self.constricted(row_id)
            weight = (layout.WEIGHTS.get(row_id, 1.5) * (1.0 - fade * 0.45)
                      * (0.42 + 0.58 * narrow))
            alpha = (1.0 - fade * 0.45) * (0.60 + 0.40 * narrow)
            ink.ink_curve(page, points, weight, seed=1000 + i * 7, colour=colour,
                          alpha=alpha, broken=narrow < 0.92)

            path = _vessel_path(row_id)
            end, before = path[-1], path[-4 if len(path) > 4 else 0]
            ink.arrowhead(page, end, (end[0] - before[0], end[1] - before[1]),
                          5.0 + weight, seed=1100 + i * 7, colour=colour,
                          alpha=alpha, weight=weight * 0.6)

            self._draw_cofactor(page, row_id, path, i, colour, alpha)

        # The one printed enzyme name on the plate. Upkeep is the only vessel
        # that does not run between two pools -- it is a curl spending ATP on
        # nothing -- so without a word it reads as an inking mistake.
        typo.caps(page, "upkeep", (398, 206), 8, palette.INK_FAINT, 1.6)

    def _draw_tributaries(self, page: pygame.Surface) -> None:
        """The gases joining the arrows they belong to.

        Oxygen and carbon dioxide are not stations on a pathway; they are taken
        from and given back to the medium by one step. Drawn as light limbs, so
        they read as something joining the chain rather than as another link
        in it.
        """
        for i, (name, points) in enumerate(layout.TRIBUTARIES.items()):
            path = ink.spline(points, step=5.0)
            ink.ink_curve(page, points, 0.9, seed=1400 + i * 11,
                          colour=palette.INK, alpha=0.55)
            end, before = path[-1], path[-3]
            ink.arrowhead(page, end, (end[0] - before[0], end[1] - before[1]),
                          4.6, seed=1450 + i * 11, colour=palette.INK,
                          alpha=0.55, weight=0.7)

    def _draw_cofactor(self, page: pygame.Surface, row_id: str,
                       path: list[ink.Point], i: int, colour, alpha) -> None:
        carried = layout.COFACTORS.get(row_id)
        if carried is None:
            return
        goes_in, comes_out, flip = carried
        mid = len(path) // 2
        at = path[mid]
        ahead = path[min(mid + 2, len(path) - 1)]
        heading = (ahead[0] - at[0], ahead[1] - at[1])
        # The arc has to fit on the arrow it crosses. A short step drawn with a
        # full-sized arc puts its labels over the metabolites at either end.
        span = float(arclength(path)[-1])
        radius = max(9.0, min(19.0, span * 0.30))
        label_in, label_out = ink.cofactor_arc(
            page, at, heading, radius, seed=1200 + i * 7, colour=colour,
            alpha=alpha * 0.85, flip=flip)
        for text, where in ((goes_in, label_in), (comes_out, label_out)):
            typo.draw(page, text, where, 9, palette.INK_FAINT, 0.5,
                      align="centre")

    # Enzyme names are deliberately not on the vessels. Every chart puts them
    # there and it is the right convention on a poster; at this size they
    # collided with the metabolite names, the cofactor labels and each other.
    # They are set in the gene register along the bottom instead, which is
    # where the player marks them anyway, and the margin names one when asked.

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
