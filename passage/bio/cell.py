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

from .. import tuning
from ..data import reactions as rxn_data
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
        return float(np.clip(self.pools[i] / self.flow.cap[self.index, i], 0.0, 1.0))

    # -- rates -------------------------------------------------------------
    @property
    def rates(self) -> np.ndarray:
        return self.flow.rate[self.index]

    def rate(self, row_id: str) -> float:
        return self.flow.rate_of(row_id, self.index)

    # -- the at-a-glance reads the roster needs (spec 3.11) -----------------
    def worst_metabolite(self) -> Metabolite:
        """The substance this cell is nearest to running out of, *and uses*.

        Restricted to inputs of reactions the cell is actually running. A food
        source the lineage has not adopted sits at zero forever, and reporting
        that as the cell's problem would be true and useless.
        """
        n = self.flow.net
        rates = np.abs(self.rates)
        # Relative to this cell's own busiest reaction, not to an absolute
        # number: a reaction ticking over at a thousandth of the traffic is not
        # what the cell is short of, whatever its substrate pool reads.
        floor = rates.max() * 0.05
        # A starved *reverse* reaction is not the cell's problem: lactate being
        # scarce because the cell is busy making it is not a shortage.
        running = (rates >= max(floor, 1e-6)) & ~n.is_reverse
        wanted = n.mask_in[running].any(axis=0) if running.any() else ~n.buffered
        wanted = wanted & ~n.buffered
        if not wanted.any():
            wanted = ~n.buffered
        fills = np.where(wanted, self.pools / self.flow.cap[self.index], np.inf)
        return n.metabolites[int(np.argmin(fills))]

    def spilling(self) -> list[Metabolite]:
        """Pools actually losing material over the cap, worst first.

        Not pools that merely sit full: a saturated oxygen pool or a fully
        charged adenylate pool is a healthy cell, and marking either with the
        alarm colour would make that colour mean nothing.
        """
        n = self.flow.net
        rate = self.flow.spill_rate[self.index]
        idx = np.flatnonzero(rate > 1e-4)
        return [n.metabolites[i] for i in idx[np.argsort(-rate[idx])]]

    def class_reads(self) -> dict[Class, float]:
        """How strongly each class registers, 0..1. What tints the cell.

        Fill, except for the energy carriers. ATP+ADP and NAD+NADH are closed
        pools whose totals never move, so their mean fill is a constant and
        would win every comparison for ever, tinting every cell arterial red
        regardless of what it was doing. What actually varies -- and what a
        player means by "this cell has energy" -- is the charge.
        """
        n = self.flow.net
        reads: dict[Class, float] = {}
        for cls in Class:
            if cls is Class.BUFFER:
                continue
            if cls is Class.ENERGY:
                reads[cls] = self.energy_charge()
                continue
            idx = [i for i, m in enumerate(n.metabolites) if m.cls is cls]
            if idx:
                reads[cls] = float(np.mean(self.pools[idx]
                                          / self.flow.cap[self.index, idx]))
        return reads

    def cast(self) -> tuple[dict[Class, float], float]:
        """What tints the cell, as a set of weights and an overall strength.

        A blend, not a winner. Meant to be readable across the room without a
        label (art direction 2): a healthy working cell is ochre and red, a
        choked one pulls grey-green, and a dying one goes pale because there is
        very little of anything left to colour it.

        Returns the weight per class and a 0..1 strength for the whole tint.
        """
        weights = {}
        for cls, read in self.class_reads().items():
            w = tuning.CLASS_TINT_WEIGHT.get(cls.value, 1.0) * read
            if w > 1e-4:
                weights[cls] = w
        total = sum(weights.values())
        if total <= 1e-4:
            return {}, 0.0
        strength = min(1.0, total / tuning.TINT_REFERENCE)
        return {c: w / total for c, w in weights.items()}, strength

    def dominant_class(self) -> Class:
        """The single class the cast leans on most. For labels, not for colour."""
        weights, _ = self.cast()
        return max(weights, key=weights.get) if weights else Class.SUGARS

    def dominant_pathway(self) -> str:
        """What this cell is mostly doing, named the way a person would say it."""
        best, best_flux = "idle", 0.0
        for name, rows in rxn_data.PATHWAYS.items():
            if name == "upkeep":
                continue           # every cell does this; it says nothing
            flux = sum(abs(self.flow.rate_of(r, self.index)) for r in rows)
            if flux > best_flux:
                best, best_flux = name, flux
        return best if best_flux > 1e-3 else "idle"

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
