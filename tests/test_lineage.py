"""Division and inheritance.

**Inheritance is the hook no factory game has.** A daughter starts life with
everything its parent had switched on and switched off -- not a fresh page, the
parent's page, in an older hand. Late in a run the player is working inside a
configuration built four generations ago for a target that no longer exists.

The milestone's acceptance is a claim about a person: *the player is visibly
reluctant to divide a badly configured cell, because they understand they are
copying the problem.* That cannot be asserted, but the three things it rests on
can be:

* the problem really is copied -- marks come across whole;
* copying really does cost -- pools are split rather than duplicated, and a
  large part of the accumulated biomass is spent;
* and the difference between what was chosen and what was inherited is on the
  page, because a player who cannot see it has nothing to be reluctant about.
"""

import numpy as np
import pytest

from passage import tuning
from passage.__main__ import build
from passage.bio.lineage import Lineage
from passage.bio.marks import Kind


def grown(ticks=24_000, every=1_200, profile="growing", seed=0):
    flow, marks, vigour = build(profile, seed)
    lineage = Lineage(flow, marks, seed=seed)
    for tick in range(ticks):
        flow.step()
        lineage.update(tuning.DT)
        vigour.update(tuning.DT)
        if tick % every == 0:
            for member in list(lineage.living):
                if lineage.divide(member.index) is not None:
                    break
    return flow, lineage, vigour


# --- the problem is copied ---------------------------------------------------

def test_a_daughter_inherits_the_whole_configuration():
    flow, marks, _ = build("growing", 0)
    lineage = Lineage(flow, marks, seed=1)
    flow.pools[0, flow.net.mi("biomass")] = tuning.DIVISION_BIOMASS * 2
    parent_marks = dict(marks.marks)

    daughter = lineage.divide(0)
    assert daughter is not None
    copied = lineage.marks_of(daughter).marks
    for gene, mark in parent_marks.items():
        assert gene in copied, f"{gene} did not come across"
        assert copied[gene].kind is mark.kind
        assert copied[gene].generation == mark.generation, \
            "a copy remembers the generation the original was placed in"


def test_inherited_marks_are_marked_inherited_and_placed_ones_are_not():
    """The visual difference between what you chose and what you were handed
    rests entirely on this bookkeeping."""
    flow, marks, _ = build("growing", 0)
    lineage = Lineage(flow, marks, seed=1)
    flow.pools[0, flow.net.mi("biomass")] = tuning.DIVISION_BIOMASS * 2
    daughter = lineage.divide(0)

    assert lineage.placed_marks(0) == len(marks.marks), \
        "a mark does not become second-hand because the cell holding it divided"
    assert lineage.inherited_marks(0) == 0
    assert lineage.placed_marks(daughter) == 0
    assert lineage.inherited_marks(daughter) == len(lineage.marks_of(daughter).marks)
    for mark in lineage.marks_of(daughter).marks.values():
        assert mark.inherited == 1


def test_a_daughters_marks_are_her_own_afterwards():
    flow, marks, _ = build("growing", 0)
    lineage = Lineage(flow, marks, seed=1)
    flow.pools[0, flow.net.mi("biomass")] = tuning.DIVISION_BIOMASS * 2
    daughter = lineage.divide(0)

    lineage.marks_of(daughter).lift("etc")
    assert marks.of("etc") is not None, "the parent kept its own mark"
    assert lineage.marks_of(daughter).of("etc") is None


def test_a_grandchild_is_two_generations_of_hand_away():
    """A mark inherited from four generations back should look like something
    somebody else wrote a long time ago."""
    flow, marks, _ = build("growing", 0)
    lineage = Lineage(flow, marks, seed=1)
    biomass = flow.net.mi("biomass")
    flow.pools[0, biomass] = tuning.DIVISION_BIOMASS * 4
    child = lineage.divide(0)
    flow.pools[child, biomass] = tuning.DIVISION_BIOMASS * 4
    grandchild = lineage.divide(child)

    depths = {m.gene: m.inherited
              for m in lineage.marks_of(grandchild).marks.values()}
    assert depths and all(d == 2 for d in depths.values()), depths


# --- drift ---------------------------------------------------------------------

def test_drift_is_rare_and_always_logged():
    """Rare, visible, and never silent: a player who cannot see what changed
    has been cheated rather than challenged."""
    flow, lineage, _ = grown()
    assert lineage.divisions >= 4
    copied = lineage.divisions * len(lineage.marks_of(0).marks)
    assert len(lineage.drifted) <= copied * 0.25, "drift should be rare"
    for drift in lineage.drifted:
        assert drift.gene in flow.net.g_index
        assert 0 < drift.cell < flow.n_cells
        # a logged drift means that gene really is missing from that daughter
        assert drift.gene not in lineage.marks_of(drift.cell).marks


def test_a_fixed_mark_never_drifts():
    flow, marks, _ = build("growing", 0)
    lineage = Lineage(flow, marks, seed=7)
    for mark in marks.marks.values():
        mark.fixed = True
    biomass = flow.net.mi("biomass")
    for _ in range(30):
        flow.pools[:, biomass] = tuning.DIVISION_BIOMASS * 2
        lineage.divide(0)
    assert lineage.drifted == []


# --- copying costs -------------------------------------------------------------

def test_dividing_needs_biomass_and_spends_it():
    flow, marks, _ = build("growing", 0)
    lineage = Lineage(flow, marks, seed=1)
    biomass = flow.net.mi("biomass")

    flow.pools[0, biomass] = tuning.DIVISION_BIOMASS * 0.5
    assert lineage.divide(0) is None, "cannot divide without the biomass"
    assert "biomass to divide" in lineage.why_not_divide(0)

    flow.pools[0, biomass] = tuning.DIVISION_BIOMASS
    before = flow.pools[0, biomass]
    daughter = lineage.divide(0)
    after = flow.pools[0, biomass] + flow.pools[daughter, biomass]
    assert after == pytest.approx(before - tuning.DIVISION_COST, abs=1e-6)


def test_pools_are_split_not_duplicated():
    """Two half-stocked cells are worse at everything than one full one, and
    that is what makes dividing a decision."""
    flow, marks, _ = build("growing", 0)
    for _ in range(2_000):
        flow.step()
    lineage = Lineage(flow, marks, seed=1)
    flow.pools[0, flow.net.mi("biomass")] = tuning.DIVISION_BIOMASS * 2

    before = flow.pools[0].copy()
    daughter = lineage.divide(0)
    total = flow.pools[0] + flow.pools[daughter]
    biomass = flow.net.mi("biomass")
    for i, met in enumerate(flow.net.metabolites):
        if i == biomass or met.buffered:
            continue
        assert total[i] == pytest.approx(before[i], abs=1e-6), met.id
        assert flow.pools[0, i] < before[i] * 0.9 or before[i] < 1e-6


def test_atoms_survive_division():
    """Biomass spent on dividing is not destroyed -- it becomes the cells."""
    flow, lineage, _ = grown()
    residual = np.abs(flow.atom_residual())
    scale = max(flow.ledger.initial_atoms.sum(), 1.0)
    assert (residual / scale).max() < tuning.CONSERVATION_TOLERANCE
    assert flow.ledger.structure.sum() == pytest.approx(
        lineage.divisions * tuning.DIVISION_COST, rel=1e-6)


# --- the tree ------------------------------------------------------------------

def test_the_lineage_is_a_tree():
    flow, lineage, _ = grown()
    assert len(lineage.members) == lineage.divisions + 1
    seen = {0}
    for member in lineage.members[1:]:
        assert member.parent in seen, "a cell must come from one that existed"
        assert member.index in lineage.members[member.parent].children
        seen.add(member.index)
    assert lineage.depth_of(0) == 0
    assert all(lineage.depth_of(m.index) > 0 for m in lineage.members[1:])


def test_every_cell_runs_its_own_chemistry():
    """Division grows every per-cell array. Missing one would leave a daughter
    reading her parent's numbers."""
    flow, lineage, _ = grown()
    for name in flow.PER_CELL:
        assert getattr(flow, name).shape[0] == flow.n_cells, name
    assert flow.n_cells == len(lineage.members)


def test_the_score_is_the_lineages_not_one_cells():
    flow, lineage, vigour = grown()
    assert len(lineage.living) > 3
    assert lineage.biomass() > flow.pool_of("biomass", 0) * 2
    assert vigour.score(lineage.biomass()) > vigour.score(flow.pool_of("biomass", 0))


def test_differentiation_is_a_bulk_mark_operation_bounded_by_budget():
    """Not a class system with names and portraits -- simply marks in bulk, and
    the budget is still the budget."""
    flow, marks, _ = build("baseline", 0)
    lineage = Lineage(flow, marks, seed=1)
    bundle = {"pfk": Kind.ACTIVATING, "gapdh": Kind.ACTIVATING,
              "ldh": Kind.ACTIVATING, "mct": Kind.ACTIVATING,
              "cs": Kind.SILENCING, "ogdh": Kind.SILENCING,
              "etc": Kind.SILENCING, "acad": Kind.SILENCING,
              "fas": Kind.SILENCING, "gdh": Kind.SILENCING}
    placed = lineage.differentiate(0, bundle)
    assert placed == tuning.MARK_BUDGET, "should spend the budget and stop"
    assert marks.held == tuning.MARK_BUDGET
