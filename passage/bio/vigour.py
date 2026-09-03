"""Relish and damage: what the lineage gets out of eating, and what it carries.

The second axis of the game, crossing yield. It has three moving parts and they
pull against each other on purpose.

**Relish** is pleasure, and it is a *need*. A lineage with none of it runs its
anabolism at a fraction of capacity -- it survives, it does not thrive. Relish
saturates, so past a point more indulgence buys no more of it.

**Damage** is what rich food costs, and it goes as the *square* of intake above
a forgiven threshold. One portion of something is nearly free. Four portions of
the same thing cost sixteen times as much. This is the entire mechanism, and it
is why the answer is never abstinence and never excess.

**Vigour** is what is left. It falls as damage accumulates, and a worn-out
lineage pays more upkeep simply to exist -- which is how "you die earlier" is
expressed in a game with no lifespan counter. It spends a larger and larger
share of everything it makes on staying alive, until it cannot.

None of this is reversible. Damage does not heal, because the interesting
decision is the one made at the time and not the one unwound afterwards.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .. import tuning
from ..data import foods as food_data
from .flow import Flow
from .network import Network


@dataclass
class Bite:
    """One food's contribution over the last stretch, for reporting."""

    food: str
    intake: float
    relish: float
    harm: float


class Vigour:
    """The diet, and what it is doing to the lineage.

    Intake is measured from what the cell *actually takes up*, not from what is
    offered, because you are not harmed by food you did not eat. Where several
    foods enter through the same gate -- and most sugar does -- the flux is
    attributed to each in proportion to what it supplies.
    """

    def __init__(self, flow: Flow, diet: dict[str, float] | None = None,
                 net: Network | None = None) -> None:
        self.net = net or flow.net
        self.flow = flow
        self.diet = dict(diet if diet is not None else food_data.STANDARD)
        self.relish = 0.0
        self.damage = 0.0
        self.offered = 0.0
        self.spilling = 0.0
        self.congestion = 0.0
        self.congested: list[str] = []
        self.eaten: dict[str, float] = {f: 0.0 for f in self.diet}
        self.last: list[Bite] = []
        self.apply_diet()

    # -- the medium the diet makes -------------------------------------------
    def apply_diet(self) -> None:
        """Write the diet into the medium it feeds.

        A diet is not a modifier on the standard medium -- it *is* the medium.
        Choosing to live on sweets means the culture around the cell is sugar
        and very little else, and every consequence follows from that rather
        than from a rule that says sweets are bad.

        The concentration matters as much as the rate. Transport is passive, so
        a cell surrounded by sugar takes sugar in whether it can use it or not:
        it cannot decline. That is what makes a diet able to hurt a body at all,
        and it is why the same meal is harmless to one lineage and poison to
        another.

        How much of a food actually arrives depends on the body: a lineage with
        no milk tolerance gets a quarter of what dairy offers, and is charged
        for the rest anyway.
        """
        n = self.net
        for food_id, portions in self.diet.items():
            food = food_data.BY_ID[food_id]
            taken = portions * self._absorbs(food_id)
            swap = self._redirects(food_id)
            for mid, amount in food.supplies.items():
                i = n.mi(swap.get(mid, mid))
                self.flow.feed[i] += amount * taken
                self.flow.target_medium[i] += amount * taken * tuning.MEDIUM_RICHNESS
                self.flow.perfused[i] = 1.0

    def _absorbs(self, food_id: str) -> float:
        c = getattr(self.flow, "constitution", None)
        return 1.0 if c is None else c.absorbs.get(food_id, 1.0)

    def _redirects(self, food_id: str) -> dict[str, str]:
        """What a food turns into for this body, if not what it is for others."""
        c = getattr(self.flow, "constitution", None)
        return {} if c is None else c.redirects.get(food_id, {})

    def _handles(self, food_id: str) -> float:
        """How much this body pays for a food, relative to a standard one."""
        c = getattr(self.flow, "constitution", None)
        return 1.0 if c is None else c.handles.get(food_id, 1.0)

    def _shares(self) -> dict[str, dict[str, float]]:
        """How much of each metabolite's supply each food is responsible for."""
        totals: dict[str, float] = {}
        for food_id, portions in self.diet.items():
            taken = portions * self._absorbs(food_id)
            swap = self._redirects(food_id)
            for mid, amount in food_data.BY_ID[food_id].supplies.items():
                lands = swap.get(mid, mid)
                totals[lands] = totals.get(lands, 0.0) + amount * taken
        out: dict[str, dict[str, float]] = {}
        for food_id, portions in self.diet.items():
            taken = portions * self._absorbs(food_id)
            swap = self._redirects(food_id)
            out[food_id] = {
                mid: (amount * taken / totals[swap.get(mid, mid)]
                      if totals[swap.get(mid, mid)] > 1e-9 else 0.0)
                for mid, amount in food_data.BY_ID[food_id].supplies.items()}
        return out

    # -- the tick -------------------------------------------------------------
    def update(self, dt: float, cell: int | None = None) -> None:
        """Relish and damage are the *lineage's*, not one cell's.

        Intake is totalled across every cell, because the lineage as a whole is
        what ate. Congestion and pleasure are averaged, because they describe a
        condition rather than a quantity: four cells all choking is a sick
        lineage, one cell choking out of four is a lineage with a problem in it.
        Totalling those instead would make growing the lineage a punishment.
        """
        n = self.net
        cells = range(self.flow.n_cells) if cell is None else (cell,)
        count = max(1, len(list(cells)) if cell is None else 1)
        shares = self._shares()
        pleasure, harm_rate = 0.0, 0.0
        self.last = []

        for food_id, share in shares.items():
            food = food_data.BY_ID[food_id]
            intake = 0.0
            swap = self._redirects(food_id)
            for mid, portion in share.items():
                k = self._exchange_index(swap.get(mid, mid))
                if k is None:
                    continue
                for c in cells:
                    taken = float(self.flow.x_rate[c, k])
                    if taken > 0:                 # only what came *in* is eaten
                        intake += taken * portion
            self.eaten[food_id] = self.eaten.get(food_id, 0.0) + intake * dt
            intake /= count                       # per cell, for relish and harm

            relish = food.relish * intake
            over = max(0.0, intake - food.forgiven)
            harm = (food.harm * self._handles(food_id)
                    * (over / tuning.DAMAGE_REFERENCE) ** 2)
            pleasure += relish
            harm_rate += harm
            if intake > 1e-4:
                self.last.append(Bite(food_id, intake, relish, harm))

        # The second source of damage, and the one that makes a constitution
        # matter at all. A lineage is not harmed by what it eats so much as by
        # what it cannot clear: a substance that sits high, for a long time, in
        # a cell with no way to get rid of it. Overflow is only the visible end
        # of that, so both are counted and the sitting counts for more.
        #
        # This is why the same meal is nourishing to one lineage and poison to
        # another, and why there is no diet that is simply correct.
        rows = list(cells)
        spilling = float(self.flow.spill_rate[rows].sum()) / count
        self.spilling = spilling

        fills = np.clip(self.flow.pools[rows] / self.flow.cap[rows], 0.0, 1.0)
        fills = np.where(n.congests & ~n.buffered, fills, 0.0)
        over = np.maximum(fills - tuning.CONGESTION_THRESHOLD, 0.0)
        congestion = float((over ** 2).sum()) / count
        self.congestion = congestion
        self.congested = [n.metabolites[i].id
                          for i in np.flatnonzero(over.max(axis=0) > 1e-6)]

        harm_rate += (tuning.SPILL_DAMAGE * spilling
                      + tuning.CONGESTION_DAMAGE * congestion)

        self.offered += food_data.supply(self.diet) * dt
        want = pleasure / (pleasure + tuning.RELISH_HALF)
        self.relish += (want - self.relish) * (1.0 - math.exp(-dt / tuning.RELISH_TAU))
        self.damage += harm_rate * dt
        self.apply()

    def _exchange_index(self, mid: str) -> int | None:
        n = self.net
        hits = np.flatnonzero(n.x_metabolite == n.mi(mid))
        return int(hits[0]) if hits.size else None

    # -- what it does to the cell ---------------------------------------------
    @property
    def vigour(self) -> float:
        """1.0 for a lineage that has taken no damage, falling from there."""
        return 1.0 / (1.0 + self.damage / tuning.DAMAGE_HALF)

    @property
    def upkeep_multiplier(self) -> float:
        return 1.0 + tuning.UPKEEP_PENALTY * (1.0 - self.vigour)

    @property
    def anabolic_multiplier(self) -> float:
        """What the lineage can build, given how it feels and what it carries.

        Relish sets the ceiling and damage pulls it down. A lineage eating well
        and undamaged builds at full rate; one living on sweets is *happier* and
        builds worse anyway, because the damage is in the machinery that does
        the building. Good for your mental health, and not for your RNA.
        """
        mood = tuning.RELISH_FLOOR + (1.0 - tuning.RELISH_FLOOR) * self.relish
        return mood * math.sqrt(self.vigour)

    def apply(self, cell: int | None = None) -> None:
        """What the lineage carries, it carries in every cell of itself."""
        n = self.net
        rows = slice(None) if cell is None else cell
        self.flow.rate_scale[rows, n.ri("maintenance")] = self.upkeep_multiplier
        self.flow.rate_scale[rows, n.ri("biosynthesis")] = self.anabolic_multiplier

    # -- the score -------------------------------------------------------------
    def score(self, produced: float) -> float:
        """What the run was worth: what you built, per unit eaten, weighted by
        the state you left the lineage in and whether the living was worth doing.

        Vigour is a *multiplier*, not a footnote, and it has to be. Measured on
        output alone -- or even on yield -- a lineage living on sweets ties with
        one eating well; it just burns itself down to get there. The difference
        only shows up when the score asks what is left at the end.

        The denominator is food **absorbed**, and that is right, though it took
        a wrong turn to be sure of it. Charging for food *offered* instead
        punishes a lineage for being given a large meal it had no way to use,
        which is not a failing.

        The reason more food does not simply buy more growth is worth stating,
        because it looks like a bug and is not: the cell is **enzyme-limited**,
        not supply-limited. Twenty times the food moves biomass by forty per
        cent, because what the lineage can process is set by the eight marks it
        has to spend, and marks are the scarce resource. A healthy cell also
        cannot overeat -- transport is passive, so once its pools are full the
        gradient closes and it stops absorbing. A cell with a constitution that
        cannot clear something is the one that *can* overeat, because its pools
        never come down. That asymmetry is the diet axis, and it is deliberate.
        """
        eaten = sum(self.eaten.values())
        if eaten <= 1e-9:
            return 0.0
        mood = (tuning.SCORE_RELISH_FLOOR
                + (1.0 - tuning.SCORE_RELISH_FLOOR) * self.relish)
        return (produced / eaten) * self.vigour * mood

    # -- reporting -------------------------------------------------------------
    def summary(self) -> str:
        """One line naming what is actually doing the harm."""
        worst = max(self.last, key=lambda b: b.harm, default=None)
        eating = worst.harm if worst else 0.0
        backing_up = (tuning.CONGESTION_DAMAGE * self.congestion
                      + tuning.SPILL_DAMAGE * self.spilling)
        if backing_up > eating and backing_up > 1e-3:
            names = ", ".join(
                self.net.metabolites[self.net.mi(m)].label
                for m in self.congested[:2]) or "waste"
            return f"the damage is {names} sitting where it cannot be cleared"
        if eating < 1e-4:
            return "nothing here is costing you anything"
        return f"most of the damage is {food_data.BY_ID[worst.food].label}"
