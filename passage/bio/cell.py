"""A single cell: a named view onto one row of the simulation arrays.

Nothing is stored here. ``Flow`` owns every number, because the solver has to
see all cells at once to stay vectorised; a ``Cell`` is what the roster and the
plate read when they need one cell's story in words rather than in indices.

Division, inheritance and junctions arrive at M3 and M4. This class exists now
so that the rest of the code never learns to index ``flow.pools`` directly.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..data.metabolites import Class, Metabolite
from .flow import Flow


@dataclass(frozen=True)
class Cell:
    flow: Flow
    index: int

    # -- pools -------------------------------------------------------------
    @property
    def pools(self) -> np.ndarray:
        return self.flow.pools[self.index]

    def pool(self, mid: str) -> float:
        return float(self.pools[self.flow.net.mi(mid)])

    def fill(self, mid: str) -> float:
        """0..1, what the pool bar shows."""
        n = self.flow.net
        i = n.mi(mid)
        return float(np.clip(self.pools[i] / n.cap[i], 0.0, 1.0))

    # -- rates -------------------------------------------------------------
    @property
    def rates(self) -> np.ndarray:
        return self.flow.rate[self.index]

    def rate(self, row_id: str) -> float:
        return self.flow.rate_of(row_id, self.index)

    # -- the at-a-glance reads the roster needs (spec 3.11) -----------------
    def worst_metabolite(self) -> Metabolite:
        """The pooled substance this cell is nearest to running out of."""
        n = self.flow.net
        fills = np.where(n.buffered, np.inf, self.pools / n.cap)
        return n.metabolites[int(np.argmin(fills))]

    def spilling(self) -> list[Metabolite]:
        """Pools at or over capacity, which is where waste comes from."""
        n = self.flow.net
        over = (~n.buffered) & (self.pools >= n.cap * 0.999)
        return [n.metabolites[i] for i in np.flatnonzero(over)]

    def dominant_class(self) -> Class:
        """Which class of substance this cell is carrying most of, by fill.

        This is what tints the cell blob on the plate, and it is meant to be
        readable across the room without any label at all (art direction 2).
        """
        n = self.flow.net
        best, best_fill = Class.SUGARS, -1.0
        for cls in Class:
            if cls is Class.BUFFER:
                continue
            idx = [i for i, m in enumerate(n.metabolites) if m.cls is cls]
            if not idx:
                continue
            mean_fill = float(np.mean(self.pools[idx] / n.cap[idx]))
            if mean_fill > best_fill:
                best, best_fill = cls, mean_fill
        return best

    def energy_charge(self) -> float:
        """ATP as a share of the adenylate pool. The cell's headline number."""
        atp, adp = self.pool("atp"), self.pool("adp")
        total = atp + adp
        return atp / total if total > 1e-9 else 0.0

    def starving(self) -> bool:
        return self.energy_charge() < 0.15

    def __repr__(self) -> str:
        return (f"<Cell {self.index} charge={self.energy_charge():.2f} "
                f"biomass={self.pool('biomass'):.1f} "
                f"worst={self.worst_metabolite().id}>")


def cells(flow: Flow) -> list[Cell]:
    return [Cell(flow, i) for i in range(flow.n_cells)]
