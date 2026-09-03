"""The genome you did not choose, and why it changes what to eat.

The claim under test is the one that makes the whole idea worth having: **there
is no diet that is simply correct**. Which one suits a lineage depends on the
constitution it was dealt, and a meal that nourishes one body is poison to
another.

That claim can fail in two directions and both are checked. It fails if a
constitution makes no difference -- if every lineage wants the same dinner, the
trait is decoration. And it fails if a constitution makes *only* a difference of
degree -- if it drags every score down without changing their order, the player
has nothing to work out.

The mechanism being verified underneath is congestion: a lineage is not harmed
by what it eats so much as by what it cannot clear. Feed a body a substance it
has no way to be rid of and the pool sits high, damage accrues, vigour falls,
and upkeep climbs. That is what makes the answer depend on the body.
"""

import pytest

from passage import tuning
from passage.__main__ import build
from passage.data import constitutions, foods

TICKS = 12_000
_CACHE: dict[tuple, tuple] = {}


def run(constitution: str, diet_name: str, ticks: int = TICKS):
    key = (constitution, diet_name, ticks)
    if key not in _CACHE:
        flow, marks, vigour = build("growing", 0, diet=foods.MENU[diet_name],
                                    constitution=constitution)
        for _ in range(ticks):
            flow.step()
            marks.update(tuning.DT)
            vigour.update(tuning.DT)
        _CACHE[key] = (vigour, vigour.score(flow.pool_of("biomass")))
    return _CACHE[key]


#: A cheap slice of the menu that still spans the three routes carbon can take
#: in. The full eight-diet sweep says the same thing and takes four minutes.
MENU = ("standard", "low sugar", "low fat", "low protein")


def best_diet(constitution: str, menu=MENU) -> str:
    return max(menu, key=lambda d: run(constitution, d)[1])


# --- the traits are real -----------------------------------------------------

def test_every_constitution_is_declared_coherently():
    net = build("baseline", 0)[0].net
    for con in constitutions.CONSTITUTIONS:
        for row in con.capacity:
            assert row in [r.id for r in net.rows], f"{con.id}: no row {row}"
        for mid in list(con.affinity) + list(con.holds):
            assert mid in net.m_index, f"{con.id}: no metabolite {mid}"
        for gene in con.baseline:
            assert gene in net.g_index, f"{con.id}: no gene {gene}"
        for food in list(con.handles) + list(con.absorbs):
            assert food in foods.BY_ID, f"{con.id}: no food {food}"
        if con.id != constitutions.DEFAULT:
            assert con.counsel, f"{con.id} says nothing about what to do"


def test_a_constitution_cannot_be_marked_away():
    """The point of the whole thing. Marks decide what is switched on; a
    constitution decides what switching it on is worth."""
    flow, marks, _ = build("growing", 0, constitution="slow_burner")
    net = flow.net
    limited = float(flow.capacity[0, net.ri("oxphos")])
    assert limited < 0.6
    # Express the gene as hard as the game allows and the ceiling does not move.
    flow.set_expression("etc", 1.0, immediate=True)
    for _ in range(2_000):
        flow.step()
    assert flow.enzyme[0, net.gi("etc")] > 0.95, "the gene is fully expressed"
    assert flow.capacity[0, net.ri("oxphos")] == pytest.approx(limited)
    assert flow.rate_of("oxphos") <= net.base_rate[net.ri("oxphos")] * limited * 1.01, \
        "full expression must not lift a constitutional ceiling"


# --- and they change what to eat ---------------------------------------------

def test_the_wrong_diet_hurts_only_the_body_it_is_wrong_for():
    """A meal that nourishes one lineage is poison to another. This is the
    whole idea, stated as four pairs."""
    mismatches = [("sugar_averse", "low fat"),      # sugar it cannot use
                  ("fat_averse", "low sugar"),      # fat it cannot burn
                  ("nitrogen_poor", "low sugar")]   # protein it cannot clear
    for constitution, diet in mismatches:
        theirs = run(constitution, diet)[1]
        standard = run("even", diet)[1]
        assert theirs < standard * 0.8, (
            f"{diet} should cost a {constitution} lineage much more than an "
            f"even one: {theirs:.3f} against {standard:.3f}")


def test_milk_intolerance_is_the_weakest_trait_but_still_bites():
    """Recorded as its own test because it is the marginal case.

    Absorbing less of a food is a feeble lever compared with being unable to
    clear one: it means less nourishment rather than active harm, and the score
    is a ratio, so eating less of something is only mildly bad. The trait wants
    a mechanism -- undigested sugar fermented to lactate the lineage then cannot
    clear -- and that needs a metabolite the network does not yet carry.
    """
    theirs = run("milk_intolerant", "creamy")[1]
    standard = run("even", "creamy")[1]
    assert theirs < standard, "a dairy diet must still cost a milk-intolerant lineage"
    assert best_diet("milk_intolerant", MENU + ("creamy",)) != "creamy"


def test_at_least_half_the_constitutions_want_a_different_dinner():
    """If every lineage wants the same meal, the trait is decoration."""
    normal = best_diet("even")
    others = ["sugar_averse", "fat_averse", "nitrogen_poor", "thrifty"]
    differing = [c for c in others if best_diet(c) != normal]
    assert len(differing) >= len(others) // 2, (
        f"only {differing} chose differently from an even constitution "
        f"(which wants {normal})")


def test_a_matched_diet_recovers_most_of_what_a_mismatched_one_costs():
    """There has to be something to *do* about it, or the trait is a sentence
    rather than a problem."""
    for constitution, wrong in [("sugar_averse", "low fat"),
                                ("fat_averse", "low sugar")]:
        right = best_diet(constitution)
        # Damage accumulates and never heals, so the gap keeps widening after
        # the ten simulated minutes this is measured over.
        assert run(constitution, right)[1] > run(constitution, wrong)[1] * 1.6


# --- the mechanism underneath -------------------------------------------------

def test_the_harm_is_what_cannot_be_cleared_not_what_was_eaten():
    """Congestion, not calories. An even lineage on the same food is fine."""
    theirs, _ = run("sugar_averse", "low fat")
    standard, _ = run("even", "low fat")
    assert theirs.damage > standard.damage * 5.0
    assert "glucose" in theirs.congested
    assert not standard.congested
    assert "cannot be cleared" in theirs.summary()


def test_a_charged_cell_is_not_a_congested_one():
    """ATP at ninety-nine per cent is health. Counting it as congestion made
    every lineage sick for being alive."""
    vigour, _ = run("even", "low sugar")
    assert "atp" not in vigour.congested
    assert "o2" not in vigour.congested
    assert "biomass" not in vigour.congested
