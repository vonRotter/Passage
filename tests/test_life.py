"""What the lineage eats, which is not what it meant to eat.

Two mechanisms, and they are the same one seen from either side.

An **intention** is what the player asks for -- eat more fish, cut the
processed meat -- because that is the shape real dietary advice takes. It lands
imperfectly, and what it takes out something else fills. That substitution is
the whole point: a player who nudges without watching what moves in behind can
do exactly what they were told and end up eating worse.

An **event** is what happens anyway. A night out, a bad three days, a fortnight
of deadlines. Not punishments, not preventable, and not hidden -- every one is
printed in the appendix from the first second. What is not knowable is when.

The night out is the one with teeth, and it is the only food in the game that
arrives through no door at all: ethanol is small and uncharged and crosses the
membrane on its own, so nothing on the register keeps it out. What it costs is
the intermediate.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np
import pytest

from passage import tuning
from passage.__main__ import build
from passage.bio import life
from passage.bio.cell import Cell
from passage.bio.marks import Kind
from passage.bio.network import network
from passage.data import foods


# --- asking for something ----------------------------------------------------

def test_a_nudge_lands_somewhere_near_what_was_asked_for_but_not_on_it():
    """Nobody eats a number."""
    rng = np.random.default_rng(4)
    landed = []
    for _ in range(12):
        after, _ = life.aim(dict(foods.STANDARD), life.BY_ID["less_sugar"], rng)
        landed.append(after["sweets"] / foods.STANDARD["sweets"])
    assert min(landed) < max(landed) - 0.05, "the nudge is deterministic"
    assert all(0.0 < l < 1.0 for l in landed), "it should always cut, and never to nothing"


def test_what_a_nudge_takes_out_something_else_puts_back():
    """The mechanic the whole idea rests on. Cutting one thing without saying
    what replaces it lets convenience food in behind."""
    rng = np.random.default_rng(1)
    before = dict(foods.CREAMY)
    after, moved = life.aim(before, life.BY_ID["less_fat"], rng)

    assert moved["dairy"] < -0.3, "it did not actually cut the fat"
    came_back = {f: d for f, d in moved.items() if d > 0}
    assert came_back, "the gap was left as a gap, which is not how eating works"
    assert any(f in came_back for f in ("sweets", "processed_meat")), (
        f"nothing convenient filled the gap: {came_back}")
    # and the lineage is not eating meaningfully less as a result
    assert sum(after.values()) > sum(before.values()) * 0.85


def test_eating_less_is_the_one_nudge_with_no_substitution():
    rng = np.random.default_rng(2)
    before = dict(foods.STANDARD)
    after, moved = life.aim(before, life.BY_ID["eat_less"], rng)
    assert sum(after.values()) < sum(before.values()) * 0.9
    assert all(d <= 0.02 for d in moved.values()), moved


def test_asking_for_more_of_something_absent_introduces_it():
    rng = np.random.default_rng(5)
    plain = dict(foods.ASCETIC)
    assert "fish" not in plain
    after, _ = life.aim(plain, life.BY_ID["more_fish"], rng)
    assert after.get("fish", 0.0) > 0.1


# --- and what happens anyway -------------------------------------------------

def test_a_run_brings_a_few_events_spread_out_and_never_at_the_start():
    for seed in range(6):
        schedule = life.Life(seed, tuning.RUN_LENGTH).schedule
        assert len(schedule) == tuning.EVENTS_PER_RUN
        times = [t for t, _ in schedule]
        assert min(times) >= tuning.EVENT_QUIET_OPENING, (
            "a run derailed before the player has read the page is not a run")
        assert max(times) < tuning.RUN_LENGTH
        for a, b in zip(times, times[1:]):
            assert b - a >= tuning.EVENT_APART - 1e-6, "two at once"


def test_the_same_seed_brings_the_same_life():
    assert (life.Life(7).schedule == life.Life(7).schedule)
    assert life.Life(7).schedule != life.Life(8).schedule


def test_an_event_overrides_the_diet_and_gives_it_back_afterwards():
    flow, marks, vigour = build("growing", 0, diet=foods.STANDARD)
    vigour.served = "standard"
    night = life.EVENTS_BY_ID["night_out"]

    vigour.impose(life.befalls(vigour.diet, night), night.label)
    assert vigour.diet.get("drink", 0.0) > 1.0
    assert vigour.imposed == night.label

    vigour.relent()
    assert "drink" not in vigour.diet
    assert vigour.served == "standard"
    assert vigour.diet == dict(foods.STANDARD)


def test_every_event_is_printed_in_the_appendix():
    """Nothing here is a surprise in the cheap sense: the list is public, and
    only the timing is not."""
    from passage.render import reference

    assert reference.Reference.TITLES[5] == "what happens anyway"
    for event in life.EVENTS:
        assert event.tells and event.tells.endswith("."), event.id
        assert event.seconds > 20.0
        assert event.adds or event.scales or event.everything != 1.0


# --- the night out -----------------------------------------------------------

def test_ethanol_arrives_through_no_door():
    """The point of the whole event. Every other food has a transporter a
    player can silence; this one crosses the membrane on its own."""
    net = network()
    row = next(r for r in net.rows if r.id == "exchange_ethanol")
    gene = net.genes[net.gi(row.gene)]
    assert not gene.markable, "the alcohol gate must not be shuttable"
    assert gene.baseline == 1.0


def test_the_cost_of_a_drink_is_the_intermediate_not_the_ethanol():
    from passage.data import metabolites as met

    assert met.BY_ID["acetaldehyde"].toxic
    assert not met.BY_ID["ethanol"].toxic
    assert met.BY_ID["acetaldehyde"].cap < met.BY_ID["ethanol"].cap / 5
    # and exactly one reaction clears it
    from passage.data import reactions as rxn
    clears = [r for r in rxn.INTERNAL if "acetaldehyde" in r.inputs]
    assert len(clears) == 1 and clears[0].enzyme == "aldh"


def a_night(spec, budget=8, seconds=None):
    tuning.MARK_BUDGET = budget
    try:
        flow, marks, vigour = build("baseline", 0, diet=foods.STANDARD)
        for token in spec.split():
            marks.place(token[:-1], Kind.ACTIVATING)
        flow.settle()
        for _ in range(6_000):
            flow.step()
            vigour.update(tuning.DT)
        before = vigour.damage
        night = life.EVENTS_BY_ID["night_out"]
        vigour.impose(life.befalls(vigour.diet, night), night.label)
        for _ in range(int((seconds or night.seconds) * tuning.TICK_HZ)):
            flow.step()
            vigour.update(tuning.DT)
        peak = Cell(flow, 0).fill("acetaldehyde")
        vigour.relent()
        for _ in range(8_000):
            flow.step()
            vigour.update(tuning.DT)
        return vigour.damage - before, peak, flow, vigour
    finally:
        tuning.MARK_BUDGET = 8


CORE = "glut+ pfk+ gapdh+ pdh+ cs+ etc+ biosyn+ aat+"


def test_a_night_out_costs_a_lineage_that_is_not_equipped_for_it():
    cost, peak, flow, vigour = a_night(CORE)
    assert peak > 0.8, "the intermediate did not build up"
    assert cost > 30.0, "a night out cost nothing"
    assert vigour.vigour > 0.5, "and it should not be a sentence"


def test_being_equipped_for_it_is_worth_a_mark():
    """You cannot keep the alcohol out. You can be ready for what it becomes,
    and it costs one of the eight -- wasted if the night never comes, which is
    what insurance is."""
    plain = a_night(CORE)[0]
    ready = a_night("glut+ gapdh+ pdh+ cs+ etc+ biosyn+ aat+ aldh+")[0]
    assert ready < plain * 0.85, (
        f"marking the clearing enzyme should cut the bill: {ready:.0f} "
        f"against {plain:.0f}")


def test_the_medium_clears_of_alcohol_afterwards():
    """It did not, for a while: ethanol had no washout rate, so one night out
    left the bath alcoholic for the rest of the run."""
    _, _, flow, _ = a_night(CORE)
    assert float(flow.medium[flow.net.mi("ethanol")]) < 0.5
    assert Cell(flow, 0).fill("acetaldehyde") < 0.05
