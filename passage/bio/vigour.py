"""Glede and damage: what the lineage gets out of eating, and what it carries.

The second axis of the game, crossing yield. It has three moving parts and they
pull against each other on purpose.

**Glede** is pleasure, and it is a *need*. A lineage with none of it runs its
anabolism at a fraction of capacity -- it survives, it does not thrive. Glede
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
    glede: float
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
        self.glede = 0.0
        self.damage = 0.0
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
        """
        n = self.net
        for food_id, portions in self.diet.items():
            food = food_data.BY_ID[food_id]
            for mid, amount in food.supplies.items():
                i = n.mi(mid)
                self.flow.feed[i] += amount * portions
                self.flow.target_medium[i] += amount * portions * 6.0
                self.flow.perfused[i] = 1.0

    def _shares(self) -> dict[str, dict[str, float]]:
        """How much of each metabolite's supply each food is responsible for."""
        totals: dict[str, float] = {}
        for food_id, portions in self.diet.items():
            for mid, amount in food_data.BY_ID[food_id].supplies.items():
                totals[mid] = totals.get(mid, 0.0) + amount * portions
        out: dict[str, dict[str, float]] = {}
        for food_id, portions in self.diet.items():
            out[food_id] = {
                mid: (amount * portions / totals[mid]) if totals[mid] > 1e-9 else 0.0
                for mid, amount in food_data.BY_ID[food_id].supplies.items()}
        return out

    # -- the tick -------------------------------------------------------------
    def update(self, dt: float, cell: int = 0) -> None:
        n = self.net
        shares = self._shares()
        pleasure, harm_rate = 0.0, 0.0
        self.last = []

        for food_id, share in shares.items():
            food = food_data.BY_ID[food_id]
            intake = 0.0
            for mid, portion in share.items():
                k = self._exchange_index(mid)
                if k is None:
                    continue
                taken = float(self.flow.x_rate[cell, k])
                if taken > 0:                     # only what came *in* is eaten
                    intake += taken * portion
            self.eaten[food_id] = self.eaten.get(food_id, 0.0) + intake * dt

            glede = food.glede * intake
            over = max(0.0, intake - food.forgiven)
            harm = food.harm * (over / tuning.DAMAGE_REFERENCE) ** 2
            pleasure += glede
            harm_rate += harm
            if intake > 1e-4:
                self.last.append(Bite(food_id, intake, glede, harm))

        want = pleasure / (pleasure + tuning.GLEDE_HALF)
        self.glede += (want - self.glede) * (1.0 - math.exp(-dt / tuning.GLEDE_TAU))
        self.damage += harm_rate * dt
        self.apply(cell)

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

        Glede sets the ceiling and damage pulls it down. A lineage eating well
        and undamaged builds at full rate; one living on sweets is *happier* and
        builds worse anyway, because the damage is in the machinery that does
        the building. Good for your mental health, and not for your RNA.
        """
        mood = tuning.GLEDE_FLOOR + (1.0 - tuning.GLEDE_FLOOR) * self.glede
        return mood * math.sqrt(self.vigour)

    def apply(self, cell: int = 0) -> None:
        n = self.net
        self.flow.rate_scale[cell, n.ri("maintenance")] = self.upkeep_multiplier
        self.flow.rate_scale[cell, n.ri("biosynthesis")] = self.anabolic_multiplier

    # -- the score -------------------------------------------------------------
    def score(self, produced: float) -> float:
        """What the run was worth: what you built, per unit eaten, weighted by
        the state you left the lineage in and whether the living was worth doing.

        Vigour is a *multiplier*, not a footnote, and it has to be. Measured on
        output alone -- or even on yield -- a lineage living on sweets ties with
        one eating well; it just burns itself down to get there. The difference
        only shows up when the score asks what is left at the end.
        """
        eaten = sum(self.eaten.values())
        if eaten <= 1e-9:
            return 0.0
        mood = tuning.SCORE_GLEDE_FLOOR + (1.0 - tuning.SCORE_GLEDE_FLOOR) * self.glede
        return (produced / eaten) * self.vigour * mood

    # -- reporting -------------------------------------------------------------
    def summary(self) -> str:
        worst = max(self.last, key=lambda b: b.harm, default=None)
        if worst is None or worst.harm < 1e-4:
            return "nothing here is costing you anything"
        label = food_data.BY_ID[worst.food].label
        return f"most of the damage is {label}"
