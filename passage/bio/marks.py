"""The mark system: cost, persistence, and what it costs to change your mind.

Marks are the scarce resource. Eight of them against eighteen markable genes,
so most of the genome sits at baseline running slowly, and choosing what to
shut down is the whole game. A mark does one of two things:

===========  ==========================  ======
Mark         Effect                      Cost
===========  ==========================  ======
Activating   expression rises toward 1   1 mark
Silencing    expression falls toward 0   1 mark
Unmarked     drifts to a low baseline    free
===========  ==========================  ======

**Removing a mark costs more than placing one, and takes longer to take
effect.** That asymmetry is the mechanical form of the inheritance thesis and
it is deliberately not softened: un-silencing a gene you silenced three
generations ago has to hurt. It is charged as a debt against the budget that
decays with time, and as a temporary slowdown on how fast that gene's
expression can move.

Every mark remembers the generation it was placed in, because a bottleneck
that traces back to a mark must be able to name that generation in plain words
(spec 3.11). Inheritance and drift arrive at M3; the fields they need are here
already so that nothing has to be retrofitted.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from .. import tuning
from .network import Network, network


class Kind(Enum):
    ACTIVATING = "activating"
    SILENCING = "silencing"


@dataclass
class Mark:
    """One mark on one gene, and where it came from."""

    gene: str
    kind: Kind
    generation: int                 # the generation it was placed in
    inherited: int = 0              # generations of inheritance; 0 is freshly placed
    fixed: bool = False             # M6: permanent, and free of the budget
    age: float = 0.0                # seconds held, for the removal cost

    @property
    def target(self) -> float:
        return 1.0 if self.kind is Kind.ACTIVATING else 0.0

    @property
    def costs_budget(self) -> bool:
        return not self.fixed


@dataclass
class Debt:
    """What is still owed for lifting a mark. Decays; never quite free."""

    gene: str
    amount: float
    generation: int


class Marks:
    """The marks on one cell, and the budget they draw from.

    Owns nothing about chemistry. It writes expression targets into the flow and
    that is the whole of its influence.
    """

    def __init__(self, flow, cell: int = 0, net: Network | None = None) -> None:
        self.net = net or network()
        self.flow = flow
        self.cell = cell
        self.generation = 1
        self.marks: dict[str, Mark] = {}
        self.debts: list[Debt] = []
        self.history: list[str] = []
        self._apply()

    # -- budget -------------------------------------------------------------
    @property
    def budget(self) -> float:
        return float(tuning.MARK_BUDGET)

    @property
    def held(self) -> float:
        return sum(1.0 for m in self.marks.values() if m.costs_budget)

    @property
    def owed(self) -> float:
        return sum(d.amount for d in self.debts)

    @property
    def spent(self) -> float:
        return self.held + self.owed

    @property
    def free(self) -> float:
        return self.budget - self.spent

    def can_place(self) -> bool:
        return self.free >= 1.0 - 1e-9

    # -- the two things a player can do -------------------------------------
    def place(self, gene: str, kind: Kind) -> bool:
        """Mark a gene. Replacing one kind with the other is a lift and a place."""
        g = self.net.genes[self.net.gi(gene)]
        if not g.markable:
            return False
        existing = self.marks.get(gene)
        if existing is not None:
            if existing.kind is kind:
                return False
            if existing.fixed:
                return False
            self.lift(gene)
        if not self.can_place():
            return False
        self.marks[gene] = Mark(gene=gene, kind=kind, generation=self.generation)
        self.history.append(f"g{self.generation}: {kind.value} {gene}")
        self._apply()
        return True

    def lift(self, gene: str) -> bool:
        """Take a mark off. This is the expensive direction, on purpose."""
        mark = self.marks.get(gene)
        if mark is None or mark.fixed:
            return False
        held_for = max(0, self.generation - mark.generation) + mark.inherited
        amount = (tuning.REMOVAL_DEBT
                  + tuning.REMOVAL_DEBT_PER_GENERATION * held_for)
        del self.marks[gene]
        self.debts.append(Debt(gene=gene, amount=amount,
                               generation=self.generation))
        # and it takes longer to take effect than placing it did
        self.flow.relax_scale[self.cell, self.net.gi(gene)] = tuning.REMOVAL_SLOWDOWN
        self.history.append(f"g{self.generation}: lifted {gene} "
                            f"(placed g{mark.generation}, debt {amount:.1f})")
        self._apply()
        return True

    def toggle(self, gene: str, kind: Kind) -> bool:
        """What a click does: mark it, or take the same mark off again."""
        existing = self.marks.get(gene)
        if existing is not None and existing.kind is kind:
            return self.lift(gene)
        return self.place(gene, kind)

    # -- time ---------------------------------------------------------------
    def advance_generation(self) -> None:
        self.generation += 1
        for mark in self.marks.values():
            mark.inherited = mark.inherited        # division does this at M3

    def update(self, dt: float) -> None:
        """Decay the debts and the slowdown. Called with simulated seconds."""
        for mark in self.marks.values():
            mark.age += dt
        if self.debts:
            keep = 0.5 ** (dt / tuning.REMOVAL_DEBT_HALFLIFE)
            for debt in self.debts:
                debt.amount *= keep
            self.debts = [d for d in self.debts if d.amount > 0.02]
        scale = self.flow.relax_scale[self.cell]
        moving = scale > 1.0
        if moving.any():
            keep = 0.5 ** (dt / tuning.REMOVAL_SLOWDOWN_HALFLIFE)
            scale[moving] = 1.0 + (scale[moving] - 1.0) * keep

    # -- what the flow sees --------------------------------------------------
    def _apply(self) -> None:
        for i, gene in enumerate(self.net.genes):
            mark = self.marks.get(gene.id)
            self.flow.target[self.cell, i] = (mark.target if mark
                                              else gene.baseline)

    # -- inspection ----------------------------------------------------------
    def of(self, gene: str) -> Mark | None:
        return self.marks.get(gene)

    def debt_on(self, gene: str) -> float:
        return sum(d.amount for d in self.debts if d.gene == gene)

    def describe(self, gene: str) -> str:
        """One line, in plain words, about what the player has done to this gene."""
        mark = self.marks.get(gene)
        if mark is None:
            debt = self.debt_on(gene)
            if debt > 0.05:
                return (f"unmarked; still owes {debt:.1f} of budget for being "
                        f"lifted, and is slow to come back")
            baseline = self.net.genes[self.net.gi(gene)].baseline
            return f"unmarked, idling at its baseline of {baseline:.0%}"
        where = (f"generation {mark.generation}" if mark.inherited == 0
                 else f"generation {mark.generation}, inherited "
                      f"{mark.inherited} generation"
                      f"{'s' if mark.inherited != 1 else ''} ago")
        fixed = ", fixed and permanent" if mark.fixed else ""
        return f"{mark.kind.value}, placed in {where}{fixed}"
