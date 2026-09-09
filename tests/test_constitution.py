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

**How these are measured matters, and it went wrong once.** An earlier version
held one generic mark set fixed across every body and every diet, and concluded
that the constitutions did nothing. They did: the question it was asking was
"which diet suits this body given somebody else's configuration", and the game's
question is "which diet suits this body, played properly". A trait that ruins
fat-burning is invisible to a configuration that never burns fat. Every score
below is therefore the best of a handful of diet-appropriate configurations,
which is slower and is the only reading that means anything.
"""

import pytest

from passage import tuning
from passage.__main__ import build
from passage.data import constitutions, foods

TICKS = 12_000
_CACHE: dict[tuple, float] = {}

#: One configuration per way carbon can come in, because which of them is worth
#: playing is exactly what a constitution changes.
CONFIGS = {
    "carb":    "glut+ pfk+ gapdh+ pdh+ cs+ etc+ biosyn+ aat+",
    "fat":     "cd36+ acad+ pdh+ cs+ etc+ biosyn+ aat+ ogdh+",
    "protein": "aat+ gdh+ amt+ pdh+ cs+ etc+ biosyn+ ogdh+",
}

#: A cheap slice of the menu that still spans the routes carbon can take in,
#: plus the one diet that is about eating *less* rather than differently.
MENU = ("standard", "low sugar", "low fat", "low protein", "sparse")


def played(constitution: str, diet_name: str, config: str,
           ticks: int = TICKS) -> float:
    """One body, one diet, one configuration, scored over a run."""
    from passage.bio.marks import Kind

    key = (constitution, diet_name, config, ticks)
    if key not in _CACHE:
        flow, marks, vigour = build("baseline", 0, diet=foods.MENU[diet_name],
                                    constitution=constitution)
        for token in CONFIGS[config].split():
            marks.place(token[:-1],
                        Kind.ACTIVATING if token[-1] == "+" else Kind.SILENCING)
        flow.settle()
        for _ in range(ticks):
            flow.step()
            marks.update(tuning.DT)
            vigour.update(tuning.DT)
        _CACHE[key] = vigour.score(flow.pool_of("biomass"))
    return _CACHE[key]


def run(constitution: str, diet_name: str, ticks: int = TICKS) -> float:
    """What this body can get out of this diet, configured as well as it can be."""
    return max(played(constitution, diet_name, c, ticks) for c in CONFIGS)


def best_diet(constitution: str, menu=MENU) -> str:
    return max(menu, key=lambda d: run(constitution, d))


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
    whole idea, stated as four pairs, with the measured margins beside them."""
    mismatches = [("sugar_averse", "low fat"),        # sugar it cannot use
                  ("fat_averse", "rich"),             # fat it cannot burn
                  ("nitrogen_poor", "low protein"),   # too little of what it needs
                  ("milk_intolerant", "creamy")]      # milk it cannot take in
    for constitution, diet in mismatches:
        theirs = run(constitution, diet)
        standard = run("even", diet)
        assert theirs < standard * 0.8, (
            f"{diet} should cost a {constitution} lineage much more than an "
            f"even one: {theirs:.3f} against {standard:.3f}")


def test_a_trait_is_quiet_on_a_diet_that_does_not_provoke_it():
    """The other half of the claim, and the one that stops a constitution being
    a flat tax. A body that handles milk badly and is not drinking milk should
    be indistinguishable from anyone else."""
    for constitution, harmless in [("milk_intolerant", "low sugar"),
                                   ("nitrogen_poor", "low sugar"),
                                   ("fat_averse", "low fat")]:
        theirs = run(constitution, harmless)
        standard = run("even", harmless)
        assert theirs > standard * 0.9, (
            f"{harmless} should cost a {constitution} lineage almost nothing: "
            f"{theirs:.3f} against {standard:.3f}")


def test_milk_intolerance_still_bites():
    """It was once the marginal case, and then for a while it was an outright
    advantage: redirecting milk sugar to lactate put the carbon into the
    pathway below the two ATP glycolysis spends reaching it. It is now the
    plainer thing -- most of the milk does not arrive -- and a dairy-led diet
    costs it about half its score."""
    assert run("milk_intolerant", "creamy") < run("even", "creamy") * 0.7
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
                                ("fat_averse", "rich")]:
        right = best_diet(constitution, MENU + ("rich",))
        assert run(constitution, right) > run(constitution, wrong) * 1.6


# --- the mechanism underneath -------------------------------------------------

def test_the_cost_is_in_what_the_body_cannot_build_with():
    """Not in what it ate, and no longer in damage either.

    This used to assert that a mismatched diet showed up as congestion damage.
    That mechanism was measuring pool *fill*, which is also what a busy cell
    looks like, and correcting it took the teeth out of every trait that leant
    on it. What replaced it is simpler and needs no damage at all: a body that
    cannot run a step converts less of what it eats into cell, and the score
    counts what was built.
    """
    from passage.bio.marks import Kind

    def built(constitution, diet_name):
        flow, marks, vigour = build("baseline", 0, diet=foods.MENU[diet_name],
                                    constitution=constitution)
        for token in CONFIGS["carb"].split():
            marks.place(token[:-1], Kind.ACTIVATING)
        flow.settle()
        for _ in range(TICKS):
            flow.step()
            vigour.update(tuning.DT)
        return flow.pool_of("biomass"), vigour

    theirs, their_vigour = built("sugar_averse", "low fat")
    standard, even_vigour = built("even", "low fat")

    assert theirs < standard * 0.6, "the trait does not cost production"

    # and it is the body, not the meal: an even lineage on the same food is
    # barely touched, which is the whole claim these tests exist for
    assert even_vigour.damage < their_vigour.damage * 0.1
    assert even_vigour.vigour > 0.95


def test_reduced_respiration_costs_a_mark_rather_than_a_meal():
    """The one trait that is not about food, and the fix for it being a flat tax.

    Every diet in this game needs ATP, so a cap on the respiratory chain scales
    everything down by the same fraction whatever the lineage eats: measured
    across five diets its spread was 1.08, and an even lineage's was also 1.08.
    The complaint was never really that it was flat. It was that it gave the
    player nothing to do.

    So the chain barely idles here, and the trait is a mark instead: one of the
    eight is spoken for before the run starts. Spend it and this body is nearly
    ordinary; leave it and nothing else matters.
    """
    from passage.bio.marks import Kind

    def score(constitution, config):
        flow, marks, vigour = build("baseline", 0, diet=foods.STANDARD,
                                    constitution=constitution)
        for token in config.split():
            marks.place(token[:-1], Kind.ACTIVATING)
        flow.settle()
        for _ in range(TICKS):
            flow.step()
            vigour.update(tuning.DT)
        return vigour.score(flow.pool_of("biomass"))

    with_chain = "glut pfk gapdh pdh cs etc biosyn aat".replace(" ", "+ ") + "+"
    without = "glut pfk gapdh pdh cs ogdh biosyn aat".replace(" ", "+ ") + "+"

    theirs_marked = score("slow_burner", with_chain)
    theirs_not = score("slow_burner", without)
    even_not = score("even", without)

    assert theirs_not < even_not * 0.1, (
        "leaving the chain unmarked should be ruinous for this body and merely "
        f"poor for anyone else: {theirs_not:.3f} against {even_not:.3f}")
    assert theirs_marked > theirs_not * 10, "the mark must be the answer"
    assert theirs_marked > score("even", with_chain) * 0.75, (
        "having spent the mark, this body should be nearly ordinary")


def test_a_charged_cell_is_not_a_congested_one():
    """ATP at ninety-nine per cent is health. Counting it as congestion made
    every lineage sick for being alive."""
    flow, marks, vigour = build("growing", 0, diet=foods.LOW_SUGAR)
    for _ in range(TICKS):
        flow.step()
        vigour.update(tuning.DT)
    assert "atp" not in vigour.congested
    assert "o2" not in vigour.congested
    assert "biomass" not in vigour.congested
