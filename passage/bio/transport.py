"""Junctions, and why specialists are hard.

Cells exchange metabolites through junctions, and a junction does one thing:
it lets a substance move **down its concentration gradient**, at a limited rate,
and never the other way. There is no routing here, no logistics network, and
nothing for the player to lay out. You create the gradients by choosing who
produces what, and the junctions do the rest.

Two properties carry the whole of the design's answer to "moving things where
they are needed".

**Throughput is shared.** A cell with four junctions moves a quarter as much
through each. So a hub that feeds four daughters feeds each of them badly, and
the shape of the lineage is a real decision rather than a picture of one.

**Every hop costs.** Material moving along a chain of cells drops a little of
its concentration at each junction, because each hop needs its own gradient to
drive it. A specialist several hops from its supplier starves, and nothing had
to be written down to make that true -- it falls out of gradients and sharing.

**The conserved carriers do not travel.** A cell that could be handed ATP by a
neighbour would never need to make any, specialisation would cost nothing, and
the trade the whole design rests on would evaporate. Every specialist keeps its
own energy books. Palmitate does not travel either, on the same principle: a
lipid specialist has to take its own fat in.
"""

from __future__ import annotations

import numpy as np

from .. import tuning
from .flow import Flow
from .network import Network


class Junctions:
    """Every connection in the lineage, and the traffic across them.

    Junctions form automatically between a parent and its daughters at
    division. Nothing else creates one, which means the tree *is* the network.
    """

    def __init__(self, net: Network) -> None:
        self.net = net
        self.edges: list[tuple[int, int]] = []
        self.mobile = np.flatnonzero(net.travels)
        self.flux = np.zeros((0, len(self.mobile)))

    # -- shape --------------------------------------------------------------
    def __len__(self) -> int:
        return len(self.edges)

    def add(self, a: int, b: int) -> None:
        pair = (min(a, b), max(a, b))
        if pair not in self.edges:
            self.edges.append(pair)

    def drop_cell(self, index: int) -> None:
        """A dead cell's junctions go with it, and its neighbours gain rate."""
        self.edges = [e for e in self.edges if index not in e]

    def degree(self, index: int) -> int:
        return sum(1 for a, b in self.edges if a == index or b == index)

    def neighbours(self, index: int) -> list[int]:
        return [b if a == index else a for a, b in self.edges
                if index in (a, b)]

    def hops(self, source: int, target: int) -> int | None:
        """How many junctions apart two cells are. ``None`` if unconnected."""
        seen, frontier, distance = {source}, [source], 0
        while frontier:
            if target in frontier:
                return distance
            nxt = [n for cell in frontier for n in self.neighbours(cell)
                   if n not in seen]
            seen.update(nxt)
            frontier = nxt
            distance += 1
        return None

    def capacity(self) -> np.ndarray:
        """Per-junction rate, after sharing. The busier end sets the limit."""
        if not self.edges:
            return np.zeros(0)
        degrees = np.array([[self.degree(a), self.degree(b)]
                            for a, b in self.edges], dtype=np.float64)
        share = 1.0 / np.maximum(degrees, 1.0) ** tuning.JUNCTION_SHARE
        return tuning.JUNCTION_RATE * share.min(axis=1)

    # -- the tick -----------------------------------------------------------
    def step(self, flow: Flow, dt: float) -> None:
        """Move everything one step down its gradient, and no further.

        Driven by the difference of Michaelis-Menten terms rather than of raw
        amounts, exactly as the membrane is: a junction between two cells that
        are both replete moves nothing, however much they hold.
        """
        if not self.edges:
            self.flux = np.zeros((0, len(self.mobile)))
            return
        m = self.mobile
        a = np.array([e[0] for e in self.edges])
        b = np.array([e[1] for e in self.edges])

        conc_a = flow.pools[np.ix_(a, m)]
        conc_b = flow.pools[np.ix_(b, m)]
        km_a = flow.km[np.ix_(a, m)]
        km_b = flow.km[np.ix_(b, m)]
        drive = (conc_a / (km_a + np.maximum(conc_a, 0.0))
                 - conc_b / (km_b + np.maximum(conc_b, 0.0)))

        moved = self.capacity()[:, None] * drive * dt

        # never take more than the giving end actually holds. Several junctions
        # can draw on the same cell at once, so each is rationed against its
        # share of that cell's total demand.
        moved = self._ration(flow, a, b, m, moved)

        flat_m = np.tile(m, len(self.edges))
        np.add.at(flow.pools, (np.repeat(a, len(m)), flat_m), -moved.ravel())
        np.add.at(flow.pools, (np.repeat(b, len(m)), flat_m), moved.ravel())
        np.clip(flow.pools, 0.0, None, out=flow.pools)
        self.flux = moved / max(dt, 1e-9)

    def _ration(self, flow: Flow, a, b, m, moved: np.ndarray) -> np.ndarray:
        """Scale flows down so no cell is asked for more than it has."""
        demand = np.zeros_like(flow.pools)
        np.add.at(demand, (np.repeat(a, len(m)), np.tile(m, len(a))),
                  np.maximum(moved, 0.0).ravel())
        np.add.at(demand, (np.repeat(b, len(m)), np.tile(m, len(b))),
                  np.maximum(-moved, 0.0).ravel())
        with np.errstate(divide="ignore", invalid="ignore"):
            allowed = np.where(demand > 1e-12,
                               np.minimum(1.0, flow.pools / demand), 1.0)
        scale_a = allowed[np.ix_(a, m)]
        scale_b = allowed[np.ix_(b, m)]
        return np.where(moved > 0, moved * scale_a, moved * scale_b)

    # -- what the margin says ------------------------------------------------
    def traffic(self, index: int) -> float:
        """Total material crossing this cell's junctions, per second."""
        if not self.edges:
            return 0.0
        total = 0.0
        for i, (a, b) in enumerate(self.edges):
            if index in (a, b):
                total += float(np.abs(self.flux[i]).sum())
        return total
