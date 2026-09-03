"""Junctions, specialists, and why distance costs.

The milestone's acceptance is that a player builds a specialist, watches it
starve, and works out *for themselves* that it is too many junction hops from
its supplier. What that rests on is tested here:

* material moves **down** the gradient and never against it, so nothing is
  routed and nothing is pumped;
* throughput is **shared**, so a hub feeding four daughters feeds each badly;
* and every hop costs, so the concentration falls along a chain and the far end
  genuinely starves.

None of that is written down as a rule anywhere. It falls out of gradients and
sharing, which is the point: the shape of the lineage *is* the logistics
network, and the player shapes it by choosing which cells divide.
"""

import numpy as np
import pytest

from passage import tuning
from passage.__main__ import build
from passage.bio.lineage import Lineage
from passage.data import specialisms


def lineage_of(size, ticks=3_000, seed=5, profile="growing"):
    """A chain of `size` cells, parent to daughter, settled."""
    flow, marks, vigour = build(profile, seed)
    lineage = Lineage(flow, marks, seed=seed)
    biomass = flow.net.mi("biomass")
    for _ in range(ticks):
        flow.step(); lineage.update(tuning.DT); vigour.update(tuning.DT)
    chain, tail = [0], 0
    for _ in range(size - 1):
        flow.pools[tail, biomass] = 500
        tail = lineage.divide(tail)
        chain.append(tail)
    return flow, lineage, vigour, chain


def settle(flow, lineage, vigour, ticks):
    for _ in range(ticks):
        flow.step(); lineage.update(tuning.DT); vigour.update(tuning.DT)


# --- the shape of the network -------------------------------------------------

def test_junctions_form_only_between_a_parent_and_its_daughter():
    """The tree *is* the network. Nothing else makes a connection."""
    flow, lineage, _, chain = lineage_of(5)
    assert len(lineage.junctions) == len(chain) - 1
    for a, b in lineage.junctions.edges:
        assert lineage.members[b].parent == a or lineage.members[a].parent == b


def test_throughput_is_shared_between_a_cells_junctions():
    """A hub that feeds four daughters feeds each of them a quarter as well."""
    flow, marks, vigour = build("growing", 0)
    lineage = Lineage(flow, marks, seed=1)
    flow.pools[0, flow.net.mi("biomass")] = 3_000
    for _ in range(4):
        lineage.divide(0)

    assert lineage.junctions.degree(0) == 4
    hub = lineage.junctions.capacity()
    assert np.allclose(hub, tuning.JUNCTION_RATE / 4)

    lone, marks2, _ = build("growing", 0)
    solo = Lineage(lone, marks2, seed=1)
    lone.pools[0, lone.net.mi("biomass")] = 3_000
    solo.divide(0)
    assert solo.junctions.capacity()[0] > hub[0] * 3


def test_the_conserved_carriers_never_cross_a_junction():
    """A cell handed ATP by a neighbour would never need to make any, and
    specialisation would cost nothing."""
    net = build("growing", 0)[0].net
    for mid in ("atp", "adp", "nad", "nadh", "biomass", "palmitate"):
        assert not net.travels[net.mi(mid)], mid
    for mid in ("glucose", "pyruvate", "lactate", "glutamate"):
        assert net.travels[net.mi(mid)], mid


# --- the physics ---------------------------------------------------------------

def test_material_only_ever_moves_downhill():
    flow, lineage, _, chain = lineage_of(3)
    net = flow.net
    lactate = net.mi("lactate")
    flow.pools[chain[0], lactate] = 60.0
    flow.pools[chain[1], lactate] = 5.0
    flow.pools[chain[2], lactate] = 1.0

    before = flow.pools[:, lactate].copy()
    lineage.junctions.step(flow, tuning.DT)
    after = flow.pools[:, lactate]
    assert after[chain[0]] < before[chain[0]], "the full cell gives"
    assert after[chain[2]] > before[chain[2]], "the empty one receives"


def test_transport_moves_material_without_creating_or_losing_any():
    flow, lineage, vigour, chain = lineage_of(5)
    net = flow.net
    flow.pools[chain[0], net.mi("lactate")] = 70.0
    before = flow.pools[:, net.travels].sum(axis=0).copy()
    for _ in range(200):
        lineage.junctions.step(flow, tuning.DT)
    after = flow.pools[:, net.travels].sum(axis=0)
    assert np.allclose(before, after, atol=1e-9)


def test_a_junction_between_two_replete_cells_moves_nothing():
    """Driven by the difference of saturation terms, as the membrane is: two
    cells that are both full have nothing to say to each other."""
    flow, lineage, _, chain = lineage_of(2)
    lactate = flow.net.mi("lactate")
    flow.pools[:, lactate] = 60.0
    before = flow.pools[:, lactate].copy()
    lineage.junctions.step(flow, tuning.DT)
    assert np.allclose(flow.pools[:, lactate], before, atol=1e-6)


# --- the acceptance mechanism ---------------------------------------------------

def test_a_specialist_starves_the_further_it_is_from_its_supplier():
    """One feeder at the head of a chain of burners. The far end goes short.

    Nothing declares this. It falls out of the fact that every hop needs its own
    gradient to drive it, so the concentration decays along the chain.
    """
    flow, lineage, vigour, chain = lineage_of(5)
    lineage.specialise(chain[0], "feeder")
    for cell in chain[1:]:
        lineage.specialise(cell, "burner")
    flow.settle()
    settle(flow, lineage, vigour, 18_000)

    lactate = [flow.pool_of("lactate", c) for c in chain[1:]]
    assert lactate == sorted(lactate, reverse=True), (
        f"lactate should fall with distance from the feeder: {lactate}")
    assert lactate[0] > lactate[-1] * 1.8, (
        f"and fall meaningfully, not just detectably: {lactate}")
    assert flow.rate_of("oxphos", chain[1]) > flow.rate_of("oxphos", chain[-1])


def test_the_diagnosis_names_the_supplier_and_the_distance():
    """The sentence a player needs to reach the conclusion themselves."""
    from passage.bio.diagnose import Diagnostician

    flow, lineage, vigour, chain = lineage_of(5)
    lineage.specialise(chain[0], "feeder")
    for cell in chain[1:]:
        lineage.specialise(cell, "burner")
    flow.settle()
    settle(flow, lineage, vigour, 12_000)

    far = chain[-1]
    reason = Diagnostician(flow.net).of(
        flow, lineage.marks_of(far), "fermentation_rev", far, lineage)
    assert reason.metabolite == "lactate"
    assert "junctions away" in reason.remedy
    assert f"Cell {chain[0]}" in reason.remedy


# --- differentiation -------------------------------------------------------------

def test_a_specialism_clears_what_came_before_and_charges_for_it():
    flow, marks, _ = build("growing", 0)
    lineage = Lineage(flow, marks, seed=1)
    assert marks.held == tuning.MARK_BUDGET

    assert lineage.specialise(0, "burner")
    spec = specialisms.BY_ID["burner"]
    assert set(marks.marks) == set(spec.activate) | set(spec.silence)
    assert marks.owed >= tuning.DIFFERENTIATION_COST
    assert marks.free < 1.0, "the shove should leave almost nothing spare"
    assert lineage.members[0].specialism == "burner"


def test_a_specialism_that_will_not_fit_is_refused_rather_than_half_placed():
    flow, marks, _ = build("growing", 0)
    lineage = Lineage(flow, marks, seed=1)
    before = dict(marks.marks)
    huge = specialisms.Specialism("huge", "too much",
                                  activate=tuple(g.id for g in flow.net.genes
                                                 if g.markable)[:8])
    specialisms.BY_ID["huge"] = huge
    try:
        assert lineage.specialise(0, "huge") is False
        assert marks.marks == before, "a refusal must not disturb anything"
    finally:
        del specialisms.BY_ID["huge"]


def test_every_specialism_fits_the_budget():
    for spec in specialisms.SPECIALISMS:
        wanted = len(spec.activate) + len(spec.silence)
        assert wanted + tuning.DIFFERENTIATION_COST <= tuning.MARK_BUDGET, spec.id
        assert spec.needs and spec.gives, f"{spec.id} does not say what it trades"


# --- death ------------------------------------------------------------------------

def test_death_is_slow_and_announced_long_before_it_happens():
    """A run collapsing for a reason the player could not have fixed in time is
    worse than one that merely scores badly."""
    flow, marks, vigour = build("starved", 0)
    lineage = Lineage(flow, marks, seed=1)
    warned = False
    for tick in range(int(tuning.DEATH_PATIENCE * tuning.TICK_HZ) + 4_000):
        flow.step(); lineage.update(tuning.DT); vigour.update(tuning.DT)
        if lineage.doom(0) and lineage.members[0].alive:
            warned = True
            assert "left" in lineage.doom(0)
        if not lineage.members[0].alive:
            break
    assert warned, "death must be telegraphed before it lands"
    assert not lineage.members[0].alive
    assert lineage.members[0].failing >= tuning.DEATH_PATIENCE


def test_a_dead_cell_gives_everything_back():
    flow, marks, vigour = build("starved", 0)
    lineage = Lineage(flow, marks, seed=1)
    for _ in range(2_000):
        flow.step(); lineage.update(tuning.DT); vigour.update(tuning.DT)
    before = np.abs(flow.atom_residual()).max()
    lineage.kill(0)
    assert np.abs(flow.atom_residual()).max() == pytest.approx(before, abs=1e-6)
    assert flow.pools[0].sum() == pytest.approx(0.0, abs=1e-9)


def test_a_dead_cells_junctions_go_with_it_and_the_survivors_gain():
    flow, lineage, _, chain = lineage_of(4)
    assert lineage.junctions.degree(chain[1]) == 2
    narrow = lineage.junctions.capacity().min()
    lineage.kill(chain[1])
    assert lineage.junctions.degree(chain[1]) == 0
    assert all(chain[1] not in edge for edge in lineage.junctions.edges)
    if len(lineage.junctions):
        assert lineage.junctions.capacity().min() >= narrow


def test_a_lean_cell_is_not_a_dying_one():
    """Specialists run at a very low charge quite happily. Killing them for
    being frugal would make specialisation unplayable."""
    flow, lineage, vigour, chain = lineage_of(3)
    lineage.specialise(chain[0], "feeder")
    for cell in chain[1:]:
        lineage.specialise(cell, "burner")
    flow.settle()
    settle(flow, lineage, vigour, 18_000)
    assert all(m.alive for m in lineage.members), \
        "a working lineage of specialists must not be culled for running lean"
