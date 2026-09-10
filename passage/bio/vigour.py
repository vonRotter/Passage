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
        self.food_damage = 0.0          # what the diet cost
        self.jam_damage = 0.0           # what the configuration cost
        self.offered = 0.0
        self.spilling = 0.0
        self.congestion = 0.0
        self.congested: list[str] = []
        self.eaten: dict[str, float] = {f: 0.0 for f in self.diet}
        self.last: list[Bite] = []
        #: (exchange rows -> metabolites), so a tick can total what crossed the
        #: membrane without looping in Python over the exchange table.
        self._x_gate = np.zeros((self.net.n_exchange, self.net.n_metabolites))
        self._x_gate[np.arange(self.net.n_exchange), self.net.x_metabolite] = 1.0
        #: How stuck each substance has been lately, smoothed. A jam has to
        #: last to be one.
        self._jam = np.zeros(self.net.n_metabolites)
        self.served = "standard"
        #: What the player is aiming at, as against what is actually arriving.
        #: An event overrides the second without touching the first, so when it
        #: passes the lineage goes back to the diet it meant to be on.
        self.intended: dict[str, float] = {}
        self.intended_name = "standard"
        self.imposed = None
        self.changes = 0
        #: The broth before any diet was written into it. Kept so that serving a
        #: different diet is a recomputation rather than an accumulation -- an
        #: earlier version added each diet on top of the last, and a lineage
        #: that had been through three menus was being fed all three.
        self._base = (self.flow.feed.copy(), self.flow.target_medium.copy(),
                      self.flow.perfused.copy())
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

    def impose(self, diet: dict[str, float], label: str):
        """Something is happening to this lineage. It eats this for now."""
        if self.imposed is None:
            self.intended = dict(self.diet)
            self.intended_name = self.served
        self.imposed = label
        return self.serve(diet, label, aiming=False)

    def relent(self):
        """The event has passed. Back to what the lineage meant to eat."""
        if self.imposed is None:
            return None
        self.imposed = None
        return self.serve(dict(self.intended), self.intended_name)

    def serve(self, diet: dict[str, float], name: str = "", aiming: bool = True):
        """Change what the lineage eats, from now on.

        The medium is not swapped. Perfusion is rate-limited in both directions,
        so writing a new target starts a turnover the cell lives through: the old
        food drains at the rate the broth can carry it off and the new food
        arrives at the rate it can be supplied. For a diet that drops a staple
        that is twenty or thirty seconds of a medium which is neither one thing
        nor the other, and the cell has to eat it.

        Returns what this change did to the configuration the player is holding,
        for the margin to say out loud.
        """
        from . import kitchen

        before = kitchen.gates(self.diet, getattr(self.flow, "constitution", None))
        was = self.served
        self.flow.feed[:], self.flow.target_medium[:], self.flow.perfused[:] = (
            self._base[0].copy(), self._base[1].copy(), self._base[2].copy())
        self.diet = dict(diet)
        self.served = name or "a diet of your own"
        if aiming:
            self.intended = dict(diet)
            self.intended_name = self.served
        self.changes += 1
        for food in self.diet:
            self.eaten.setdefault(food, 0.0)
        self.apply_diet()
        after = kitchen.gates(self.diet, getattr(self.flow, "constitution", None))
        return kitchen.upset(was, self.served, before, after, self.marks)

    #: Set by the run so that a diet change can name the marks it just stranded.
    marks = None

    def _absorbs(self, food_id: str) -> float:
        c = getattr(self.flow, "constitution", None)
        return 1.0 if c is None else c.absorbs.get(food_id, 1.0)

    def _redirects(self, food_id: str) -> dict[str, str]:
        """What a food turns into for this body, if not what it is for others."""
        c = getattr(self.flow, "constitution", None)
        return {} if c is None else c.redirects.get(food_id, {})

    def _tolerates(self, food_id: str) -> float:
        """How much of a food this body takes before it starts to cost."""
        c = getattr(self.flow, "constitution", None)
        return 1.0 if c is None else c.tolerates.get(food_id, 1.0)

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
            over = max(0.0, intake - food.forgiven * self._tolerates(food_id))
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

        # A full pool is not the same thing as a stuck one, and for a long
        # while this counted them as the same. It charged for *fill*, so the
        # busier a lineage was the more it paid: a configured, respiring cell
        # jammed seven pools and lost four fifths of its vigour, while a cell
        # with no marks at all sat comfortable. Doing nothing scored better
        # than playing, which is the plainest possible statement that a rule
        # is wrong.
        #
        # What the comment above always said, now measured: a substance does
        # damage when the cell has *no way to be rid of it*. A pool carrying a
        # great deal that leaves as fast as it arrives is a working pipeline.
        # A pool that is filling faster than anything consumes it is the jam.
        produced = self.flow.rate[rows] @ n.s_out
        consumed = self.flow.rate[rows] @ n.s_in
        traded = self.flow.x_rate[rows] @ self._x_gate
        inflow = produced + np.maximum(traded, 0.0)
        # Sending something out is not as good as using it. A cell that can
        # only be rid of a substance by flushing it into the medium is coping
        # rather than metabolising, and the difference is the whole of what a
        # constitution does: milk sugar that arrives as acid leaves again, and
        # counting that as cleanly cleared left the trait with no mechanism.
        outflow = consumed + tuning.EXPORT_CLEARS * np.maximum(-traded, 0.0)
        stuck = np.clip(1.0 - outflow / (inflow + 1e-9), 0.0, 1.0)

        # "for a long time", which the comment always claimed and the code did
        # not do either. Near a steady state the flux balance oscillates about
        # zero from tick to tick, so an instantaneous reading flickers: the
        # plate's alarm colour would blink and the margin would lose the pool
        # it was explaining mid-sentence. Smoothed over a couple of seconds, a
        # jam has to persist to count, which is what was meant.
        now = (over ** tuning.CONGESTION_POWER
               * (tuning.JAM_FLOOR + (1.0 - tuning.JAM_FLOOR) * stuck)
               ).sum(axis=0) / count

        # and the substances that are harmful by concentration rather than by
        # being stuck, which the rule above cannot see: a pool of poison that
        # clears exactly as fast as it arrives is still a pool of poison.
        poison = np.maximum(fills - tuning.TOXIC_THRESHOLD, 0.0) ** 2
        poison = np.where(n.toxic, poison, 0.0).sum(axis=0) / count
        now = now + poison * (tuning.TOXIC_DAMAGE / tuning.CONGESTION_DAMAGE)
        keep = math.exp(-dt / tuning.JAM_TAU)
        self._jam = self._jam * keep + now * (1.0 - keep)

        congestion = float(self._jam.sum())
        self.congestion = congestion
        self.congested = [n.metabolites[i].id
                          for i in np.flatnonzero(self._jam > 1e-5)]

        jam_rate = (tuning.SPILL_DAMAGE * spilling
                    + tuning.CONGESTION_DAMAGE * congestion)

        self.offered += food_data.supply(self.diet) * dt
        want = pleasure / (pleasure + tuning.RELISH_HALF)
        self.relish += (want - self.relish) * (1.0 - math.exp(-dt / tuning.RELISH_TAU))
        # Kept apart because they call for opposite corrections. Damage from
        # food is a diet the lineage cannot afford; damage from a jam is a
        # configuration that cannot clear what it is being given, and eating
        # *less* would be the wrong answer to it. A single total told the
        # player they were eating badly when they were marking badly.
        self.food_damage += harm_rate * dt
        self.jam_damage += jam_rate * dt
        self.damage += (harm_rate + jam_rate) * dt
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
        """What the run was worth: what you built, how cheaply, and in what state.

        Four terms, each bounded, multiplied together.

        **Production** is first, and for a long time it was absent. The score
        was yield times condition, which sounds reasonable and is not: with
        intake in the denominator and nothing counting output, the way to win
        was to eat as little as possible. Measured over a full run, a lineage
        that built 64 units scored 0.143 and one that built 742 scored 0.041,
        and doing nothing at all beat a configured, respiring cell by two and a
        half times. A game whose optimum is not to play it is mis-scored.

        **Efficiency** is the old yield term, now saturating rather than
        dividing. As a bare ratio it ran away as intake fell; bounded, it still
        rewards getting more from less and can no longer be won by fasting.

        The denominator is food **absorbed**, and that is right, though it took
        a wrong turn to be sure of it. Charging for food *offered* instead
        punishes a lineage for being given a large meal it had no way to use,
        which is not a failing.

        **Vigour** is what the diet left behind, and it is a multiplier rather
        than a footnote: measured on output alone a lineage living on sweets
        ties with one eating well, because it simply burns itself to get there.
        **Relish** counts too, at a smaller weight, because a lineage that never
        got anything out of eating did worse and the score should say so.

        The reason more food does not simply buy more growth is worth stating,
        because it looks like a bug and is not: the cell is **enzyme-limited**,
        not supply-limited. What a lineage can process is set by the eight marks
        it has to spend, and marks are the scarce resource. A healthy cell also
        cannot overeat -- transport is passive, so once its pools are full the
        gradient closes and it stops absorbing. A cell with a constitution that
        cannot clear something is the one that *can* overeat, because its pools
        never come down. That asymmetry is the diet axis, and it is deliberate.
        """
        eaten = sum(self.eaten.values())
        if eaten <= 1e-9 or produced <= 0.0:
            return 0.0
        built = produced / (produced + tuning.SCORE_TARGET)
        yields = produced / eaten
        efficiency = yields / (yields + tuning.SCORE_YIELD_HALF)
        mood = (tuning.SCORE_RELISH_FLOOR
                + (1.0 - tuning.SCORE_RELISH_FLOOR) * self.relish)
        return built * efficiency * self.vigour * mood
