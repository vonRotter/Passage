"""M5: choosing what to eat, and what that does to the marks you had placed.

Three contracts:

* **A diet change is a recomputation, not an accumulation.** An earlier version
  added each new diet on top of the last, and a lineage that had been through
  three menus was being fed all three at once.
* **The medium turns over rather than switching.** Perfusion is rate-limited in
  both directions, so the seconds after a change are genuinely spent eating
  something that is neither diet, and the cell cannot skip them.
* **The game says what just became wrong.** The invalidation is the milestone.
  A change that silently makes four of the player's eight marks worthless,
  without saying so, is a trap rather than a decision.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np
import pytest

from passage.__main__ import build
from passage.bio import kitchen
from passage.bio.cell import Cell
from passage.bio.marks import Kind
from passage.data import constitutions, foods


def run(flow, vigour, seconds: float, lineage=None) -> None:
    from passage import tuning
    for _ in range(int(seconds * tuning.TICK_HZ)):
        flow.step()
        vigour.update(tuning.DT)


# --- the medium ------------------------------------------------------------

def test_serving_a_diet_replaces_the_last_one_rather_than_adding_to_it():
    flow, marks, vigour = build("baseline", 0)
    net = flow.net
    once = flow.target_medium.copy()

    vigour.serve(foods.STANDARD, "standard")
    assert np.allclose(flow.target_medium, once), \
        "re-serving the same diet changed the medium"

    vigour.serve(foods.ASCETIC, "plain")
    plain = flow.target_medium.copy()
    vigour.serve(foods.INDULGENT, "rich")
    vigour.serve(foods.ASCETIC, "plain")
    assert np.allclose(flow.target_medium, plain), \
        "the medium remembers diets the lineage is no longer eating"


def test_a_diet_that_drops_a_staple_clears_it_from_the_medium():
    """Not instantly. Perfusion is bounded, so this takes real seconds."""
    from passage import tuning

    flow, marks, vigour = build("baseline", 0)
    g = flow.net.mi("glucose")
    run(flow, vigour, 20.0)
    rich = float(flow.medium[g])

    vigour.serve(foods.LOW_SUGAR, "low sugar")
    run(flow, vigour, 1.0)
    just_after = float(flow.medium[g])
    run(flow, vigour, tuning.DIET_TURNOVER)
    settled = float(flow.medium[g])

    assert just_after > settled * 1.15, "the medium switched instead of turning over"
    assert settled < rich, "dropping the sugar did not lower the sugar"


def test_the_gates_a_diet_serves_are_measured_after_the_body_has_its_say():
    """A lineage that ferments its milk sugar on the way in is fed acid."""
    milk = constitutions.BY_ID["milk_intolerant"]
    creamy = {"dairy": 4.0}
    standard = kitchen.gates(creamy)
    theirs = kitchen.gates(creamy, milk)
    assert standard.get("lactate", 0.0) == 0.0
    assert theirs.get("lactate", 0.0) > 0.0
    assert theirs.get("glucose", 0.0) < standard["glucose"]


# --- the invalidation ------------------------------------------------------

def test_a_change_of_diet_names_the_marks_it_just_stranded():
    flow, marks, vigour = build("baseline", 0)
    for gene in ("glut", "pfk", "gapdh"):
        marks.place(gene, Kind.ACTIVATING)

    report = vigour.serve(foods.LOW_SUGAR, "low sugar")

    assert not report.quiet
    assert report.was == "standard" and report.now == "low sugar"
    assert set(report.stranded) >= {"glut", "pfk"}
    said = " ".join(report.lines).lower()
    assert "sugar" in said
    assert "%" in said, "the report does not say by how much"


def test_a_gate_that_opens_with_nothing_marked_for_it_is_reported_too():
    """Half the mechanic. A diet that brings fat to a lineage with no way to
    take it in is a diet that will simply sit in the medium."""
    flow, marks, vigour = build("baseline", 0)
    report = vigour.serve(foods.LOW_SUGAR, "low sugar")
    said = " ".join(report.lines).lower()
    assert "palmitate" in said
    assert "nothing is marked" in said


def test_a_change_between_two_similar_diets_says_little():
    flow, marks, vigour = build("baseline", 0)
    marks.place("glut", Kind.ACTIVATING)
    report = vigour.serve(foods.STANDARD, "standard again")
    assert report.quiet, f"nothing changed but it said {report.lines}"


def test_only_the_players_own_marks_are_named():
    """A mark inherited from a parent was not this player's bet, and blaming
    them for it is the game telling them off for something they did not do."""
    flow, marks, vigour = build("baseline", 0)
    marks.place("glut", Kind.ACTIVATING)
    marks.place("pfk", Kind.SILENCING)          # silencing sugar is not a bet on it
    report = vigour.serve(foods.LOW_SUGAR, "low sugar")
    assert "pfk" not in report.stranded
    assert "glut" in report.stranded


# --- what it costs ---------------------------------------------------------

def test_changing_diet_does_not_refund_anything():
    """Damage is permanent and the budget is not returned. The cost of a change
    is the marks it wasted, and nothing here may quietly give them back."""
    flow, marks, vigour = build("baseline", 0)
    marks.place("glut", Kind.ACTIVATING)
    run(flow, vigour, 30.0)
    damage, held = vigour.damage, marks.held

    vigour.serve(foods.ASCETIC, "plain")
    assert vigour.damage >= damage
    assert marks.held == held


def test_every_diet_on_the_menu_can_be_served_and_leaves_the_sum_closed():
    """The conservation invariant is not allowed to care what anyone is eating."""
    flow, marks, vigour = build("growing", 0)
    for name, diet in foods.MENU.items():
        vigour.serve(diet, name)
        run(flow, vigour, 4.0)
        assert float(np.abs(flow.atom_residual()).max()) < 1e-6, \
            f"{name} broke the atom balance"


# --- adoption --------------------------------------------------------------

def test_a_pathway_is_taken_up_by_marking_it_and_fades_when_the_mark_is_lifted():
    from passage.render.plate import taken_up

    flow, marks, vigour = build("baseline", 0)
    assert "palmitate" not in taken_up(marks)

    marks.place("cd36", Kind.ACTIVATING)
    assert "palmitate" in taken_up(marks)
    assert "beta_oxidation" in taken_up(marks)

    marks.lift("cd36")
    assert "palmitate" not in taken_up(marks), \
        "a pathway nobody is paying for is still printed as adopted"


def test_silencing_a_gene_is_not_adopting_its_pathway():
    from passage.render.plate import taken_up

    flow, marks, vigour = build("baseline", 0)
    marks.place("cd36", Kind.SILENCING)
    assert "palmitate" not in taken_up(marks)
