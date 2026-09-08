"""Fructose, and why it has a gate of its own.

Every other food in this game arrives through one of four doors — sugar, fat,
amino acids, lactate — and the plate's regulation point sits on the sugar door.
Fructose is the exception that makes the door worth thinking about: it is
cleaved to triose *below* PFK-1, so the one brake a lineage has on sugar is not
on it.

That produces the game's sharpest trap, and these tests are what keep it sharp:

* the obvious move — silencing the regulation point — makes a sugar-averse
  lineage eating sweet food **worse off**, because the fructose keeps coming;
* the answer is to shut the transporter the fructose is actually using, which
  leaves glycolysis able to clear what does get in.

Nothing about it is hidden. The shunt is drawn on the plate joining below the
regulated step, the appendix says so in words, and the constitution's counsel
names the trap outright. Discovering it should take a player one bad run, not
twenty.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np
import pytest

from passage import tuning
from passage.__main__ import build
from passage.bio.cell import Cell
from passage.bio.marks import Kind
from passage.bio.network import network

#: Sweet enough to hurt, and otherwise unremarkable.
SWEET = {"sweets": 2.2, "wholegrain": 1.0, "vegetables": 1.0, "legumes": 0.6}
CORE = ["gapdh", "pdh", "cs", "etc", "biosyn", "aat"]


def run(marks_wanted, diet=None, constitution=None, seconds=400.0):
    flow, marks, vigour = build("baseline", 0, diet=diet,
                                constitution=constitution)
    for gene, kind in marks_wanted:
        marks.place(gene, kind)
    flow.settle()
    for _ in range(int(seconds * tuning.TICK_HZ)):
        flow.step()
        vigour.update(tuning.DT)
    return flow, marks, vigour, Cell(flow, 0)


# --- the chemistry ---------------------------------------------------------

def test_fructolysis_balances_and_joins_below_the_regulation_point():
    net = network()
    row = next(r for r in net.rows if r.id == "fructolysis")
    assert row.gene == "aldob", "the shunt is on the regulated gene"

    from passage.data import reactions as rxn
    made = rxn.BY_ID["fructolysis"]
    assert set(made.outputs) & {"g3p"}, "fructose must arrive at the triose"
    assert "glucose" not in made.inputs and "glucose" not in made.outputs
    # and it is the same trade as the regulated route, atom for atom
    glyc = rxn.BY_ID["glycolysis_upper"]
    assert made.outputs["g3p"] == glyc.outputs["g3p"]
    assert made.inputs["atp"] == glyc.inputs["atp"]


def test_silencing_the_regulation_point_does_not_touch_the_shunt():
    """The whole claim, at the level of the solver."""
    core = [(g, Kind.ACTIVATING) for g in CORE]
    open_, _, _, _ = run(core, diet=SWEET)
    shut, _, _, _ = run(core + [("pfk", Kind.SILENCING)], diet=SWEET)

    assert shut.rate_of("glycolysis_upper") < open_.rate_of("glycolysis_upper") * 0.6
    assert shut.rate_of("fructolysis") > open_.rate_of("fructolysis") * 0.9, \
        "the brake reached the shunt, which is the one thing it must not do"


# --- the trap --------------------------------------------------------------

def test_shutting_the_front_door_leaves_a_sugar_averse_lineage_worse_off():
    core = [(g, Kind.ACTIVATING) for g in CORE]
    whole = tuning.RUN_LENGTH
    nothing = run(core, SWEET, "sugar_averse", seconds=whole)
    front = run(core + [("pfk", Kind.SILENCING)], SWEET, "sugar_averse",
                seconds=whole)

    assert front[2].damage > nothing[2].damage, \
        "silencing the regulation point is supposed to be a trap here"
    assert front[2].vigour < nothing[2].vigour
    # and it costs more than it looks: a fifth of the score of leaving it alone
    assert front[2].score(front[3].pool("biomass")) < \
        nothing[2].score(nothing[3].pool("biomass")) * 0.4


def test_shutting_the_door_the_fructose_uses_is_the_answer():
    # over a whole run, because this is a claim about the score and the score
    # counts what was built: at four hundred seconds the two are still level
    # and the answer has not had time to pay for itself
    core = [(g, Kind.ACTIVATING) for g in CORE]
    whole = tuning.RUN_LENGTH
    nothing = run(core, SWEET, "sugar_averse", seconds=whole)
    back = run(core + [("glut5", Kind.SILENCING)], SWEET, "sugar_averse",
               seconds=whole)

    assert back[0].rate_of("exchange_fructose") < 0.02, "fructose still arriving"
    assert back[2].damage < nothing[2].damage * 0.2
    assert back[2].score(back[3].pool("biomass")) > \
        nothing[2].score(nothing[3].pool("biomass")) * 1.4, \
        "the answer does not pay enough to be worth finding"
    assert back[2].damage < 1.0, "the right answer should cost nothing at all"
    # and it is the one plan where *more* sugar comes in, which is the point:
    # a cell that can process what arrives keeps taking it
    assert back[0].rate_of("exchange_glucose") > \
        nothing[0].rate_of("exchange_glucose")


def test_shutting_both_doors_starves_rather_than_saves():
    """Because the lesson is not 'block everything'. A lineage that shuts the
    front door as well has nothing left to build with."""
    core = [(g, Kind.ACTIVATING) for g in CORE]
    both = run(core + [("pfk", Kind.SILENCING), ("glut5", Kind.SILENCING)],
               SWEET, "sugar_averse")
    back = run(core + [("glut5", Kind.SILENCING)], SWEET, "sugar_averse")
    assert both[3].pool("biomass") < back[3].pool("biomass") * 0.2


# --- it is on the page -----------------------------------------------------

def test_the_shunt_is_drawn_joining_below_the_regulated_step():
    from passage.data import layout

    assert "fructose" in layout.POOLS
    assert "fructolysis" in layout.VESSELS
    assert "exchange_fructose" in layout.EXCHANGE_STUBS

    # it must end at G3P, not at glucose: a shunt drawn into the top of the
    # pathway would be a picture of the opposite of what the chemistry does
    end = layout.VESSELS["fructolysis"][-1]
    g3p = layout.pool_centre("g3p")
    glucose = layout.pool_centre("glucose")
    assert np.hypot(end[0] - g3p[0], end[1] - g3p[1]) < 40
    assert np.hypot(end[0] - glucose[0], end[1] - glucose[1]) > 80


def test_the_report_treats_fructose_as_a_gate_of_its_own():
    from passage.bio import kitchen
    from passage.data import foods

    assert kitchen.SERVES["glut5"] == "fructose"
    rich = kitchen.gates(foods.INDULGENT)
    assert rich.get("fructose", 0.0) > 0.5, "the rich diet carries no fructose"

    flow, marks, vigour = build("baseline", 0, diet=foods.INDULGENT)
    vigour.served = "rich"
    marks.place("glut5", Kind.ACTIVATING)
    report = vigour.serve(foods.ASCETIC, "plain")
    assert "glut5" in report.stranded, "dropping the sweets stranded nothing"


# --- and the game says so --------------------------------------------------

def test_the_margin_leads_with_the_poisoning_not_a_flux_problem():
    """The gap this closed.

    The bottleneck diagnosis answers "why is this reaction slow". Asked of a
    lineage that is choking, it reported a flux problem three steps downstream
    and said nothing about the damage — identical advice whether or not the
    player had just made things worse. A cell poisoning itself is a more urgent
    fact than a reaction at 60%, and the margin now says so first.
    """
    from passage.bio.diagnose import Diagnostician

    core = [(g, Kind.ACTIVATING) for g in CORE]
    flow, marks, vigour, cell = run(core, SWEET, "sugar_averse")
    doctor = Diagnostician(flow.net)

    hurt = doctor.choking(flow, marks, vigour, 0)
    assert hurt is not None, "a choking cell reported nothing wrong"
    # whichever pool it names, it must be one that is genuinely over the line
    # on *this* cell's capacity, and it must say so with the numbers
    i = flow.net.mi(hurt.metabolite)
    fill = float(flow.pools[0, i] / flow.cap[0, i])
    assert fill > tuning.CONGESTION_THRESHOLD
    assert f"{fill:.0%}" in hurt.detail
    assert "choking" in hurt.headline
    assert "damage does not heal" in hurt.detail
    # it outranks every flux reason, so wherever the two are read together
    # the poisoning is what a player sees
    for flux in doctor.bottlenecks(flow, marks, 0, 4):
        assert hurt.severity > flux.severity


def test_the_pool_is_read_against_this_body_rather_than_the_chart():
    """A constitution that holds less of something is more easily choked by it.

    Reading the shared chart capacity instead of the cell's own hid exactly the
    lineages this diagnosis exists for: a pool sitting at its own cap read as
    comfortable, because the chart's cap for it was larger.
    """
    from passage.bio.diagnose import Diagnostician

    core = [(g, Kind.ACTIVATING) for g in CORE]
    flow, marks, vigour, cell = run(core + [("pfk", Kind.SILENCING)],
                                    SWEET, "sugar_averse")
    i = flow.net.mi("glucose")
    assert float(flow.cap[0, i]) < float(flow.net.cap[i]), \
        "this constitution is meant to hold less glucose"
    assert float(flow.pools[0, i]) / float(flow.cap[0, i]) > 0.98
    # against the chart's number this pool would read as merely full-ish, and
    # something else would have been reported instead
    assert float(flow.pools[0, i]) / float(flow.net.cap[i]) < 0.85

    hurt = Diagnostician(flow.net).choking(flow, marks, vigour, 0)
    assert hurt.metabolite == "glucose"


def test_it_names_the_players_own_silencing_as_the_cause():
    from passage.bio.diagnose import Diagnostician

    core = [(g, Kind.ACTIVATING) for g in CORE]
    flow, marks, vigour, cell = run(core + [("pfk", Kind.SILENCING)],
                                    SWEET, "sugar_averse")
    hurt = Diagnostician(flow.net).choking(flow, marks, vigour, 0)
    assert "you silenced" in hurt.remedy
    assert "That is the cause" in hurt.remedy


def test_nothing_is_choking_a_healthy_lineage():
    core = [(g, Kind.ACTIVATING) for g in CORE]
    flow, marks, vigour, cell = run(core + [("glut5", Kind.SILENCING)],
                                    {"wholegrain": 1.4, "legumes": 0.9,
                                     "vegetables": 1.2}, "even")
    from passage.bio.diagnose import Diagnostician
    hurt = Diagnostician(flow.net).choking(flow, marks, vigour, 0)
    assert hurt is None or hurt.share < 0.99


def test_the_rates_panel_shows_the_shunt_beside_the_regulated_route():
    """You cannot learn the trap from a number you cannot see."""
    from passage.render.panel import WATCH

    watched = [row for row, _ in WATCH]
    assert "glycolysis_upper" in watched and "fructolysis" in watched
