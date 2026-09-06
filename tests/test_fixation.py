"""M6: fixation, and the run coming to an end.

Fixation is the fourth verb and the only one with no way back. Everything else
the player does to this page can be undone at a price; this cannot be undone at
any price, and the tests here are mostly about that being true rather than
nearly true.

The three contracts:

* **A fixed mark is the lineage's, not a cell's.** Every living cell gets it and
  every cell born after inherits it already fixed -- including the ones it does
  not suit, which is the decision the verb is for.
* **It costs the target.** Biomass spent writing the genome is conserved but is
  no longer counted as built, or the verb is free once its gates are passed.
* **The run ends, and the ending accounts for itself.** A score with no
  explanation teaches nobody anything.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np
import pytest

from passage import tuning
from passage.__main__ import build
from passage.bio.ending import Ending
from passage.bio.lineage import Lineage
from passage.bio.marks import Kind


def settled(profile: str = "growing", seconds: float = 500.0, seed: int = 0):
    flow, marks, vigour = build(profile, seed)
    lineage = Lineage(flow, marks, seed=seed)
    for _ in range(int(seconds * tuning.TICK_HZ)):
        flow.step()
        lineage.update(tuning.DT)
        vigour.update(tuning.DT)
    return flow, lineage, vigour


# --- the gates -------------------------------------------------------------

def test_a_mark_has_to_be_lived_with_before_it_can_be_fixed():
    flow, marks, vigour = build("growing", 0)
    lineage = Lineage(flow, marks, seed=0)
    why = lineage.fix(0, "pdh")
    assert why, "a mark placed a moment ago was fixable"
    assert "lived with" in why
    assert "s more" in why, "it does not say how much longer"


def test_a_lineage_that_has_built_nothing_cannot_afford_to_fix():
    flow, lineage, vigour = settled(seconds=120.0)
    why = lineage.fix(0, "pdh")
    assert "biomass" in why


def test_refusing_says_why_rather_than_failing_silently():
    flow, lineage, vigour = settled()
    assert lineage.fix(0, "ldh").startswith("there is no mark")
    assert lineage.fix(0, "pdh") == ""
    assert "already fixed" in lineage.fix(0, "pdh")


# --- what it does ----------------------------------------------------------

def test_fixing_hands_the_mark_back_to_the_budget():
    flow, lineage, vigour = settled()
    marks = lineage.marks_of(0)
    before = marks.held
    assert lineage.fix(0, "pdh") == ""
    assert marks.held == before - 1
    assert marks.of("pdh").fixed


def test_a_fixed_mark_cannot_be_lifted_or_replaced_at_any_price():
    flow, lineage, vigour = settled()
    marks = lineage.marks_of(0)
    lineage.fix(0, "pdh")
    assert marks.lift("pdh") is False
    assert marks.place("pdh", Kind.SILENCING) is False
    assert marks.toggle("pdh", Kind.ACTIVATING) is False
    assert marks.of("pdh").kind is Kind.ACTIVATING


def test_fixing_reaches_every_cell_including_ones_that_did_not_want_it():
    """The point of the verb. A feeder and a burner do not want the same genes
    switched on, and fixing one means the other is carrying it too."""
    flow, lineage, vigour = settled()
    daughter = lineage.divide(0)
    assert daughter is not None
    other = lineage.marks_of(daughter)
    other.lift("pdh")
    assert other.of("pdh") is None

    assert lineage.fix(0, "pdh") == ""
    assert other.of("pdh") is not None, "the genome did not reach every cell"
    assert other.of("pdh").fixed


def test_a_cell_born_after_a_fixation_inherits_it_already_fixed():
    flow, lineage, vigour = settled()
    lineage.fix(0, "pdh")
    daughter = lineage.divide(0)
    assert daughter is not None
    mark = lineage.marks_of(daughter).of("pdh")
    assert mark is not None and mark.fixed
    assert lineage.marks_of(daughter).lift("pdh") is False


def test_differentiation_does_not_clear_a_fixed_mark():
    flow, lineage, vigour = settled()
    lineage.fix(0, "pdh")
    daughter = lineage.divide(0)
    assert lineage.specialise(daughter, "feeder")
    assert lineage.marks_of(daughter).of("pdh").fixed


def test_a_fixed_mark_never_drifts():
    """Whatever is in the genome survives every division, however many.

    Only what was actually fixed: each fixation is charged, so a lineage runs
    out of biomass to write with long before it runs out of marks to write --
    which is itself the constraint, and the first draft of this test did not
    know it.
    """
    flow, lineage, vigour = settled(seconds=900.0)
    for gene in list(lineage.marks_of(0).marks):
        lineage.fix(0, gene)
    fixed = {g for g, m in lineage.marks_of(0).marks.items() if m.fixed}
    assert fixed, "nothing could be afforded, so this proves nothing"
    assert len(fixed) < len(lineage.marks_of(0).marks), \
        "every mark was affordable; the cost is not biting"

    for _ in range(6):
        born = lineage.divide(0)
        if born is None:
            break
        carried = {g for g, m in lineage.marks_of(born).marks.items() if m.fixed}
        assert carried >= fixed, "a fixed mark drifted"


# --- what it costs ---------------------------------------------------------

def test_fixing_costs_the_target_and_the_atoms_still_close():
    flow, lineage, vigour = settled()
    before = lineage.biomass()
    assert lineage.fix(0, "pdh") == ""
    assert lineage.biomass() == pytest.approx(before - tuning.FIX_COST, abs=1e-6)
    assert float(np.abs(flow.atom_residual()).max()) < 1e-6, \
        "writing the genome lost atoms"


def test_what_was_written_is_conserved_rather_than_destroyed():
    flow, lineage, vigour = settled()
    i = flow.net.mi("biomass")
    lineage.fix(0, "pdh")
    assert float(flow.ledger.written[i]) == pytest.approx(tuning.FIX_COST,
                                                          abs=1e-6)


# --- the ending ------------------------------------------------------------

def test_the_ending_says_which_factor_decided_the_run():
    flow, lineage, vigour = settled()
    end = Ending(lineage, vigour, 900.0, flow)
    said = end.decided_by()
    assert said.endswith(".") and len(said) > 40
    assert any(word in said.lower()
               for word in ("damage", "pleasure", "yield", "died", "balance"))


def test_the_ending_accounts_for_the_score_rather_than_only_printing_it():
    flow, lineage, vigour = settled()
    end = Ending(lineage, vigour, 900.0, flow)
    labels = [line.label for line in end.lines()]
    assert labels == ["built", "eaten", "yield", "vigour", "relish"]
    # every factor that cost something says how much
    for line in end.lines():
        assert 0.0 <= line.weight <= 1.0


def test_an_extinct_lineage_is_reported_as_such_and_not_as_a_bad_score():
    flow, lineage, vigour = settled(seconds=120.0)
    for member in list(lineage.living):
        lineage.kill(member.index)
    end = Ending(lineage, vigour, 900.0, flow)
    assert end.extinct
    assert "died" in end.decided_by()


def test_the_epitaph_distinguishes_a_lineage_that_fixed_nothing():
    flow, lineage, vigour = settled()
    end = Ending(lineage, vigour, 900.0, flow)
    assert "Nothing was fixed" in end.epitaph()
    lineage.fix(0, "pdh")
    assert "Nothing was fixed" not in Ending(lineage, vigour, 900.0,
                                             flow).epitaph()


def test_the_reckoning_page_inks_without_a_display():
    import pygame

    from passage.render.final import Final

    pygame.init()
    pygame.display.set_mode((1, 1))
    flow, lineage, vigour = settled()
    lineage.fix(0, "pdh")
    page = Final(Ending(lineage, vigour, 900.0, flow))
    surface = page.surface()
    assert surface.get_size() == (1280, 720)
    assert page.surface() is surface, "the reckoning was inked twice"
