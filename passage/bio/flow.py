"""Rate solving, pools, saturation, inhibition -- vectorised.

Every quantity here is an array over all cells at once. There is no Python
loop over reactions or over cells anywhere in ``step``; that is a hard rule
(spec 2), because it is the only thing that keeps twenty cells at 20 Hz cheap
enough for the rendering budget to matter.

The rate law, per reaction, per cell::

    rate = base_rate x enzyme_level x saturation(inputs) x (1 - inhibition(outputs))

``saturation`` is a product of Michaelis-Menten terms over the distinct input
metabolites -- a curve, not a cliff. ``inhibition`` is driven by how full the
reaction's *own product* pools are, and it is what makes backpressure travel
upstream. A reaction three steps downstream that stops will fill its inputs,
which inhibits the step feeding it, which fills *its* inputs, and so on until
the stall is visible at the top of the pathway. That propagation is the whole
reason a bottleneck is findable rather than merely fatal.

Pools are amounts; cell volume is 1, so an amount is also a concentration.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .. import tuning
from .network import Network, network


@dataclass
class Ledger:
    """Where every atom came from and went. The conservation test reads this."""

    supplied: np.ndarray        # (M,) fed into the medium from outside
    removed: np.ndarray         # (M,) washed out of the medium by perfusion
    buffer_net: np.ndarray      # (M,) net drawn from the buffered pools
    spilled: np.ndarray         # (M,) over-cap material, lost as waste
    initial_atoms: np.ndarray   # (A,) atoms present when the run began


class Flow:
    """The simulation state for a whole lineage plus the medium it sits in."""

    def __init__(self, n_cells: int = 1, net: Network | None = None,
                 seed: int = 0) -> None:
        self.net = net or network()
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        n = self.net
        self.n_cells = n_cells

        self.pools = np.zeros((n_cells, n.n_metabolites))
        for mid, amount in tuning.CELL_START.items():
            self.pools[:, n.mi(mid)] = amount
        self.pools[:, n.mi("atp")] = tuning.ADENYLATE_CHARGED
        self.pools[:, n.mi("adp")] = tuning.ADENYLATE_TOTAL - tuning.ADENYLATE_CHARGED
        self.pools[:, n.mi("nadh")] = tuning.NICOTINAMIDE_REDUCED
        self.pools[:, n.mi("nad")] = tuning.NICOTINAMIDE_TOTAL - tuning.NICOTINAMIDE_REDUCED

        self.medium = np.zeros(n.n_metabolites)
        for mid, amount in tuning.MEDIUM_START.items():
            self.medium[n.mi(mid)] = amount

        self.feed = np.zeros(n.n_metabolites)
        for mid, rate in tuning.MEDIUM_FEED.items():
            self.feed[n.mi(mid)] = rate
        self.target_medium = np.zeros(n.n_metabolites)
        self.perfused = np.zeros(n.n_metabolites)
        for mid, level in tuning.MEDIUM_TARGET.items():
            self.target_medium[n.mi(mid)] = level
            self.perfused[n.mi(mid)] = 1.0

        # expression is what the marks ask for; enzyme is what the cell has
        # managed to build so far. Nothing in this game responds instantly.
        self.target = np.tile(n.baseline, (n_cells, 1))
        self.expression = self.target.copy()
        self.enzyme = self.expression.copy()
        # Per-gene multiplier on how slowly expression follows its target. A
        # gene whose mark was just lifted moves more sluggishly than one being
        # marked for the first time (spec 3.3).
        self.relax_scale = np.ones((n_cells, n.n_genes))

        # A per-cell, per-reaction multiplier on capacity. Nothing in the
        # chemistry writes to it; it is where the diet's consequences land.
        self.rate_scale = np.ones((n_cells, n.n_internal))
        self.rate = np.zeros((n_cells, n.n_internal))
        self.x_rate = np.zeros((n_cells, n.n_exchange))
        self.spill_rate = np.zeros((n_cells, n.n_metabolites))
        self.saturation = np.ones((n_cells, n.n_internal))
        self.inhibition = np.zeros((n_cells, n.n_internal))

        self.ticks = 0
        self._dt = tuning.DT
        self.ledger = Ledger(
            supplied=np.zeros(n.n_metabolites),
            removed=np.zeros(n.n_metabolites),
            buffer_net=np.zeros(n.n_metabolites),
            spilled=np.zeros(n.n_metabolites),
            initial_atoms=self._atoms(self.pools.sum(axis=0) + self.medium),
        )

    # -- helpers -----------------------------------------------------------
    def _atoms(self, amounts: np.ndarray) -> np.ndarray:
        return amounts @ self.net.atoms

    def _mm(self, conc: np.ndarray) -> np.ndarray:
        """Michaelis-Menten availability, 0..1. Buffered substrates read 1."""
        n = self.net
        mm = conc / (n.km + np.maximum(conc, 0.0))
        return np.where(n.buffered[None, :], 1.0, np.clip(mm, 0.0, 1.0))

    def _fill(self, conc: np.ndarray) -> np.ndarray:
        n = self.net
        fill = np.clip(conc / n.cap, 0.0, 1.0)
        return np.where(n.buffered[None, :], 0.0, fill)

    # -- the tick ----------------------------------------------------------
    def step(self, dt: float | None = None) -> None:
        dt = tuning.DT if dt is None else dt
        self._dt = dt

        self._solve_internal(dt)
        self._solve_exchange(dt)
        self._perfuse(dt)
        self._spill()
        self._relax(dt)
        self.ticks += 1

    def _solve_internal(self, dt: float) -> None:
        n = self.net
        mm = self._mm(self.pools)                       # (C, M)
        fill = self._fill(self.pools)

        # product of MM terms over the distinct inputs of each row
        sat = np.prod(np.where(n.mask_in[None, :, :], mm[:, None, :], 1.0), axis=2)
        # the fullest product pool sets the backpressure
        inh = np.max(np.where(n.mask_out[None, :, :],
                              fill[:, None, :] ** tuning.INHIBITION_EXPONENT,
                              0.0), axis=2)
        inh = np.clip(inh, 0.0, 1.0) * tuning.INHIBITION_CEILING

        rate = (n.base_rate[None, :] * self.rate_scale
                * self.enzyme[:, n.row_gene] * sat * (1.0 - inh))
        rate = self._limit(rate, n.s_in, self.pools, dt)

        delta = rate @ n.s_net * dt                     # (C, M)
        self.pools += np.where(n.buffered[None, :], 0.0, delta)
        self.ledger.buffer_net -= np.where(n.buffered, delta.sum(axis=0), 0.0)

        self.rate, self.saturation, self.inhibition = rate, sat, inh

    def _limit(self, rate: np.ndarray, s_in: np.ndarray,
               pools: np.ndarray, dt: float) -> np.ndarray:
        """Scale rates down so no pool is driven below zero.

        A few passes of proportional back-off. Exact enough that the
        conservation test passes to floating-point tolerance, and cheap:
        it is three broadcasts over a matrix of a few thousand entries.
        """
        n = self.net
        available = np.maximum(pools, 0.0)
        for _ in range(tuning.SOLVER_PASSES):
            demand = rate @ s_in * dt                              # (C, M)
            with np.errstate(divide="ignore", invalid="ignore"):
                headroom = np.where(demand > 1e-12, available / demand, np.inf)
            headroom = np.where(n.buffered[None, :], np.inf, headroom)
            factor = np.min(np.where(n.mask_in[None, :, :],
                                     headroom[:, None, :], np.inf), axis=2)
            factor = np.clip(np.where(np.isfinite(factor), factor, 1.0), 0.0, 1.0)
            if np.all(factor > 1.0 - 1e-12):
                break
            rate = rate * factor
        return rate

    def _solve_exchange(self, dt: float) -> None:
        """Traffic between each cell and the shared medium, down the gradient.

        Nothing is routed and nothing is pumped. A substance moves because one
        side holds more of it than the other, and the transporter's expression
        sets only how fast. That is the design's entire answer to logistics
        (spec 3.6): you create gradients by choosing who produces what, and the
        gradients do the rest.

        Flux is driven by the difference of the two Michaelis-Menten terms
        rather than by the raw difference in amount, so a transporter that is
        already saturated on both sides stops mattering -- which is why a
        starving specialist cannot be rescued by simply piling more into the
        medium.
        """
        n = self.net
        idx = n.x_metabolite
        cell_conc = self.pools[:, idx]                              # (C, X)
        med_conc = np.broadcast_to(self.medium[idx], cell_conc.shape)
        km = n.km[idx][None, :]

        drive = (med_conc / (km + med_conc)) - (cell_conc / (km + cell_conc))
        rate = n.x_base_rate[None, :] * self.enzyme[:, n.x_gene] * drive
        moved = rate * dt                                           # + into cell

        # never take more than the source holds. Cells draw independently from
        # one shared medium, so the medium side is rationed across all of them.
        from_cell = np.maximum(-moved, 0.0)
        from_cell = np.minimum(from_cell, np.maximum(cell_conc, 0.0))
        from_medium = np.maximum(moved, 0.0)
        demand = from_medium.sum(axis=0)
        avail = np.maximum(self.medium[idx], 0.0)
        with np.errstate(divide="ignore", invalid="ignore"):
            share = np.where(demand > 1e-12, np.minimum(1.0, avail / demand), 1.0)
        from_medium = from_medium * share[None, :]

        flux = from_medium - from_cell                              # into the cell

        # scatter-add: exchange rows are keyed by metabolite, and a plain
        # fancy-index assignment would drop a repeat.
        into_cells = np.zeros_like(self.pools)
        np.add.at(into_cells, (slice(None), idx), flux)
        self.pools += into_cells

        into_medium = np.zeros(n.n_metabolites)
        np.add.at(into_medium, idx, -flux.sum(axis=0))
        self.medium += into_medium

        self.x_rate = flux / dt if dt > 0 else np.zeros_like(flux)

    def _perfuse(self, dt: float) -> None:
        """Hold the medium toward its target, in both directions, at a bounded rate.

        A chemostat rather than a firehose. If the lineage eats faster than
        perfusion can replace, the medium genuinely runs down and supply becomes
        the constraint; if it dumps waste faster than perfusion can carry it
        off, the medium fouls and every cell in it feels the gradient close.
        """
        gap = self.target_medium - self.medium
        limit = self.feed * dt
        delta = np.clip(gap, -limit, limit) * self.perfused
        self.medium += delta
        self.ledger.supplied += np.maximum(delta, 0.0)
        self.ledger.removed += np.maximum(-delta, 0.0)

    def _spill(self) -> None:
        """A pool at its cap that keeps receiving loses the excess as waste.

        The spilled material is not deleted -- it is booked into the ledger, so
        the conservation invariant still closes and the score can charge for it
        (spec 3.7).
        """
        n = self.net
        over = np.maximum(self.pools - n.cap[None, :], 0.0)
        over = np.where(n.buffered[None, :], 0.0, over) * tuning.SPILL_FRACTION
        self.pools -= over
        self.ledger.spilled += over.sum(axis=0)
        # A pool merely sitting at its cap is not spilling. Only material
        # actually being lost counts, because the alarm colour marks spillover
        # and damage and nothing else in the game is ever allowed to use it.
        self.spill_rate = over / max(self._dt, 1e-9)

        med_over = np.maximum(self.medium - tuning.MEDIUM_CAP, 0.0)
        med_over = np.where(n.buffered, 0.0, med_over)
        self.medium -= med_over
        self.ledger.spilled += med_over

        np.clip(self.pools, 0.0, None, out=self.pools)
        np.clip(self.medium, 0.0, None, out=self.medium)

    def _relax(self, dt: float) -> None:
        """Expression follows its target; enzyme follows expression. Both lag.

        Nothing in this game responds instantly, and that lag is what makes
        regulation a decision rather than a switch.
        """
        a = 1.0 - np.exp(-dt / (tuning.EXPRESSION_TAU * self.relax_scale))
        self.expression += (self.target - self.expression) * a
        b = 1.0 - np.exp(-dt / tuning.ENZYME_TAU)
        self.enzyme += (self.expression - self.enzyme) * b

    # -- inspection --------------------------------------------------------
    def settle(self) -> None:
        """Snap expression and enzyme to whatever the marks currently ask for.

        A run begins with a cell that is already expressing its opening marks,
        not with one that has to build every enzyme from scratch while paying
        full upkeep. Without this the first fifteen seconds kill the cell before
        any enzyme exists to save it, which is an artificial death that teaches
        the player nothing. At M3 this is simply true: a daughter inherits its
        parent's enzyme state along with its marks.
        """
        self.expression[:] = self.target
        self.enzyme[:] = self.target

    def rate_of(self, row_id: str, cell: int = 0) -> float:
        n = self.net
        i = n.ri(row_id)
        if n.rows[i].exchange:
            return float(self.x_rate[cell, i - n.n_internal])
        return float(self.rate[cell, i])

    def pool_of(self, mid: str, cell: int = 0) -> float:
        return float(self.pools[cell, self.net.mi(mid)])

    def set_expression(self, gene_id: str, level: float,
                       cell: int | slice = slice(None), immediate: bool = False) -> None:
        g = self.net.gi(gene_id)
        self.target[cell, g] = level
        if immediate:
            self.expression[cell, g] = level
            self.enzyme[cell, g] = level

    def throughput(self, cell: int | slice = slice(None)) -> float:
        """Total internal traffic, in units per second. What the hum tracks.

        Upkeep is left out: it runs whether or not the factory is working, and
        counting it would put a floor under the hum that hides exactly the slow
        stall a player is meant to hear coming.
        """
        n = self.net
        keep = np.array([row.reaction != "maintenance"
                         for row in n.rows[:n.n_internal]])
        return float(np.abs(self.rate[cell][..., keep]).sum())

    def atom_residual(self) -> np.ndarray:
        """Atoms currently held, minus atoms that ever entered. Should be zero."""
        held = self._atoms(self.pools.sum(axis=0) + self.medium
                           + self.ledger.spilled + self.ledger.removed)
        entered = (self.ledger.initial_atoms
                   + self._atoms(self.ledger.supplied)
                   + self._atoms(self.ledger.buffer_net))
        return held - entered
