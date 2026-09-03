"""Division, inheritance, differentiation, and the tree they make.

**Inheritance is the hook no factory game has.** Marks persist through division
and across generations, so late in a run the player is working inside a
configuration they built four generations ago for a target that no longer
exists. Un-silencing is expensive on purpose. You inherit your own past
optimisation, mistakes included.

Three things follow from that and all three are here:

*Marks copy.* A daughter starts life with everything its parent had switched on
and switched off. Not a fresh page -- the parent's page, in an older hand.

*Copying is not perfect.* A mark occasionally fails to come across. Drift is
rare, it is logged, and it is never silent: a player who cannot see what changed
has been cheated rather than challenged.

*Dividing costs.* Pools are split rather than duplicated and a large part of the
accumulated biomass is spent, so two daughters are, for a while, worse at
everything than the one cell they came from. That is what makes the player stop
and think about whether they want two of *this* cell -- which is the whole
acceptance test for this milestone.

Damage is not tracked here. It belongs to the lineage rather than the cell,
because what a body carries is carried by everything that comes after it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .. import tuning
from .cell import Cell
from .flow import Flow
from ..data import specialisms as spec_data
from .marks import Debt, Kind, Mark, Marks
from .network import Network
from .transport import Junctions


@dataclass
class Member:
    """One cell in the lineage: where it sits, and where it came from."""

    index: int
    marks: Marks
    parent: int | None = None
    born: int = 1                    # the generation it divided into being
    children: list[int] = field(default_factory=list)
    specialism: str | None = None
    alive: bool = True
    failing: float = 0.0             # seconds spent with no energy at all
    died: int | None = None          # the generation it gave up in

    @property
    def depth(self) -> int:
        return 0 if self.parent is None else -1   # filled in by the Lineage


@dataclass
class Drift:
    """A mark that failed to copy. Logged so it can be shown, never silent."""

    generation: int
    cell: int
    gene: str
    kind: Kind


class Lineage:
    """Every cell, its marks, and the tree of who came from whom."""

    def __init__(self, flow: Flow, marks: Marks, seed: int = 0,
                 net: Network | None = None) -> None:
        self.net = net or flow.net
        self.flow = flow
        self.rng = np.random.default_rng(seed)
        self.generation = marks.generation
        self.members: list[Member] = [Member(index=0, marks=marks)]
        self.junctions = Junctions(self.net)
        self.drifted: list[Drift] = []
        self.divisions = 0

    # -- reading ------------------------------------------------------------
    def __len__(self) -> int:
        return len(self.members)

    @property
    def living(self) -> list[Member]:
        return [m for m in self.members if m.alive]

    def marks_of(self, index: int) -> Marks:
        return self.members[index].marks

    def depth_of(self, index: int) -> int:
        depth, member = 0, self.members[index]
        while member.parent is not None:
            depth += 1
            member = self.members[member.parent]
        return depth

    def cells(self) -> list[Cell]:
        return [Cell(self.flow, m.index) for m in self.members if m.alive]

    def can_divide(self, index: int) -> bool:
        return (self.members[index].alive
                and self.flow.pool_of("biomass", index) >= tuning.DIVISION_BIOMASS)

    def why_not_divide(self, index: int) -> str:
        """In plain words, because a greyed-out button explains nothing."""
        have = self.flow.pool_of("biomass", index)
        if have >= tuning.DIVISION_BIOMASS:
            return ""
        return (f"needs {tuning.DIVISION_BIOMASS:.0f} biomass to divide and has "
                f"{have:.0f}")

    # -- the one thing it does ----------------------------------------------
    def divide(self, index: int) -> int | None:
        """Split a cell. The daughter inherits the marks, and the debts.

        Everything the parent had switched on, the daughter has switched on --
        one generation older, drawn in a fainter hand. What it does not inherit
        is the budget already spent: a mark held by both cells costs both of
        them, which is how a lineage runs out of room to think.
        """
        if not self.can_divide(index):
            return None
        parent = self.members[index]
        daughter_index = self.flow.divide(index, tuning.DIVISION_SHARE)

        # The biomass spent is not destroyed: it becomes the two cells. Booked
        # as structure so that the conservation sum still closes.
        for cell in (index, daughter_index):
            self.flow.commit(cell, "biomass", tuning.DIVISION_COST * 0.5)

        daughter_marks = Marks(self.flow, daughter_index, self.net)
        daughter_marks.generation = self.generation
        for gene, mark in parent.marks.marks.items():
            if self._drifts(mark):
                self.drifted.append(Drift(self.generation, daughter_index,
                                          gene, mark.kind))
                continue
            daughter_marks.marks[gene] = Mark(
                gene=gene, kind=mark.kind, generation=mark.generation,
                inherited=mark.inherited + 1, fixed=mark.fixed, age=mark.age)
        daughter_marks._apply()

        # The parent's own marks stay its own. A mark does not become
        # second-hand because the cell holding it divided -- only the copy that
        # travelled is inherited, and only that copy fades.

        # A junction forms between parent and daughter, and only there. The
        # tree *is* the transport network, which is why the shape of it is a
        # decision and not a picture of one.
        self.junctions.add(index, daughter_index)

        member = Member(index=daughter_index, marks=daughter_marks,
                        parent=index, born=self.generation)
        parent.children.append(daughter_index)
        self.members.append(member)
        self.divisions += 1
        return daughter_index

    def _drifts(self, mark: Mark) -> bool:
        """A fixed mark never drifts. Everything else might, rarely."""
        if mark.fixed:
            return False
        return bool(self.rng.random() < tuning.DRIFT_CHANCE)

    # -- differentiation (spec 3.5) -----------------------------------------
    def differentiate(self, index: int, bundle: dict[str, Kind]) -> int:
        """Place a bundle of marks, within the budget. The budget is the budget.

        Returns how many were actually placed, which may be fewer than asked
        for.
        """
        marks = self.members[index].marks
        placed = 0
        for gene, kind in bundle.items():
            if marks.place(gene, kind):
                placed += 1
        return placed

    def specialise(self, index: int, specialism: str) -> bool:
        """Push a cell wholesale into a specialism, for one flat charge.

        The inherited configuration is cleared rather than lifted mark by mark:
        that is what the player is paying for. What they are *not* escaping is
        the cost -- a flat charge against the same eight marks, on top of the
        marks the new pattern itself holds. A fixed mark is not cleared, because
        nothing clears a fixed mark.
        """
        spec = spec_data.BY_ID[specialism]
        marks = self.members[index].marks
        wanted = len(spec.activate) + len(spec.silence)
        if marks.budget - tuning.DIFFERENTIATION_COST < wanted:
            return False

        for gene in list(marks.marks):
            if not marks.marks[gene].fixed:
                del marks.marks[gene]
        marks.debts.append(Debt(gene=f"differentiate:{specialism}",
                                amount=tuning.DIFFERENTIATION_COST,
                                generation=self.generation))
        for gene in spec.activate:
            marks.place(gene, Kind.ACTIVATING)
        for gene in spec.silence:
            marks.place(gene, Kind.SILENCING)
        marks.history.append(f"g{self.generation}: became a {spec.label}")
        self.members[index].specialism = specialism
        marks._apply()
        return True

    # -- time ---------------------------------------------------------------
    def advance_generation(self) -> None:
        self.generation += 1
        for member in self.members:
            member.marks.generation = self.generation

    def update(self, dt: float) -> None:
        for member in self.members:
            member.marks.update(dt)
        self.junctions.step(self.flow, dt)
        self._fail(dt)

    # -- death, slowly and with warning -------------------------------------
    def _fail(self, dt: float) -> None:
        """Track how long each cell has had nothing left, and end it if it lasts.

        A cell running lean is not a cell dying. What kills is having genuinely
        stopped -- no ATP at all -- for long enough that it was never coming
        back. Recovery is faster than decline, so a cell that dips and recovers
        is not quietly condemned by it.
        """
        atp = self.net.mi("atp")
        for member in self.members:
            if not member.alive:
                continue
            if self.flow.pools[member.index, atp] < tuning.DEATH_ATP:
                member.failing += dt
                if member.failing >= tuning.DEATH_PATIENCE:
                    self.kill(member.index)
            else:
                member.failing = max(
                    0.0, member.failing - dt * tuning.DEATH_RECOVERY)

    def kill(self, index: int) -> None:
        """A cell stops. What it held goes back to the medium, atom for atom."""
        member = self.members[index]
        if not member.alive:
            return
        member.alive = False
        member.died = self.generation
        n = self.net
        released = self.flow.pools[index].copy()
        self.flow.pools[index] = 0.0
        self.flow.medium += np.where(n.buffered, 0.0, released)
        self.junctions.drop_cell(index)

    def failing_for(self, index: int) -> float:
        return self.members[index].failing

    def doom(self, index: int) -> str:
        """What the margin says about a cell that is running out of time."""
        member = self.members[index]
        if not member.alive:
            return f"stopped in generation {member.died}"
        if member.failing <= 0.5:
            return ""
        left = tuning.DEATH_PATIENCE - member.failing
        return f"no energy at all for {member.failing:.0f}s — {left:.0f}s left"

    @property
    def dead(self) -> list[Member]:
        return [m for m in self.members if not m.alive]

    def hops_to_supplier(self, index: int, mid: str) -> tuple[int | None, int | None]:
        """Which living cell holds most of a substance, and how far away it is.

        The answer the acceptance test wants a player to reach on their own:
        *this cell is starving because it is three junctions from the only cell
        making what it needs.*
        """
        i = self.net.mi(mid)
        best, best_held = None, self.flow.pools[index, i]
        for member in self.living:
            held = self.flow.pools[member.index, i]
            if held > best_held * 1.5:
                best, best_held = member.index, held
        if best is None:
            return None, None
        return best, self.junctions.hops(index, best)

    # -- what the margin draws ----------------------------------------------
    def tree(self) -> list[tuple[int, int, int | None]]:
        """(index, depth, parent) for every cell, in birth order."""
        return [(m.index, self.depth_of(m.index), m.parent) for m in self.members]

    def biomass(self) -> float:
        """Everything the lineage has built, including what it spent on being
        more than one cell. The score is about the lineage, not a cell."""
        total = sum(self.flow.pool_of("biomass", m.index) for m in self.living)
        return total + float(self.flow.ledger.structure[self.net.mi("biomass")])

    def inherited_marks(self, index: int) -> int:
        return sum(1 for m in self.members[index].marks.marks.values()
                   if m.inherited > 0)

    def placed_marks(self, index: int) -> int:
        return sum(1 for m in self.members[index].marks.marks.values()
                   if m.inherited == 0)
