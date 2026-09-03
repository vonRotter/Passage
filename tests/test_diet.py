"""The diet axis: glede against damage, and why moderation wins.

The design claim being tested is not "healthy food is good". It is a specific
mechanical shape, and each half of it can fail on its own:

* glede is a **need**, so a joyless diet loses to a moderate one even though it
  does no damage at all;
* damage is **superlinear**, so a small amount of something rich costs almost
  nothing and a large amount costs a great deal;
* and the difference only shows up in a score that asks what the lineage has
  **left**, because on raw output -- and even on yield -- a lineage living on
  sweets ties with one eating well. It simply burns itself down to get there.

The three diets supply the same total food. Without that, a test showing the
rich diet losing would only be showing that it was also the larger one.
"""

import pytest

from passage import tuning
from passage.__main__ import build
from passage.bio.vigour import Vigour
from passage.data import foods

#: Twenty-five simulated minutes. Long enough for damage to have arrived and
#: for the ordering to have settled; short enough that the suite stays usable.
RUN = 30_000

_CACHE: dict[tuple, tuple] = {}


def run(diet, ticks=RUN, profile="growing"):
    """A whole run on one diet. Cached, because each is a few seconds of solving."""
    key = (tuple(sorted(diet.items())), ticks, profile)
    if key not in _CACHE:
        flow, marks, vigour = build(profile, seed=0, diet=diet)
        for _ in range(ticks):
            flow.step()
            marks.update(tuning.DT)
            vigour.update(tuning.DT)
        produced = flow.pool_of("biomass")
        _CACHE[key] = (vigour, produced, vigour.score(produced))
    return _CACHE[key]


def test_the_three_diets_supply_the_same_amount_of_food():
    """Otherwise every result below is about quantity, not about quality."""
    supplies = [foods.supply(d) for d in
                (foods.STANDARD, foods.INDULGENT, foods.ASCETIC)]
    assert max(supplies) / min(supplies) < 1.06, supplies


def test_moderation_beats_both_excess_and_abstinence():
    """The whole point. A varied diet with a little of what you like wins."""
    _, _, standard = run(foods.STANDARD)
    _, _, indulgent = run(foods.INDULGENT)
    _, _, ascetic = run(foods.ASCETIC)
    assert standard > ascetic, "a joyless diet should not beat a good one"
    assert standard > indulgent, "living on sweets should not beat eating well"
    assert ascetic > indulgent, "damage should cost more than joylessness does"


def test_indulgence_wins_early_and_loses_late():
    """It has to be tempting, or the choice is not a choice.

    Sweets grow the cell faster for the first stretch of a run. What they cost
    arrives later, which is the entire point and the reason the decision is
    interesting rather than obvious.
    """
    _, early_rich, _ = run(foods.INDULGENT, ticks=9_000)
    _, early_good, _ = run(foods.STANDARD, ticks=9_000)
    assert early_rich > early_good, "indulgence must actually be tempting"

    late_rich, late_good = run(foods.INDULGENT)[2], run(foods.STANDARD)[2]
    assert late_good > late_rich


def test_a_joyless_lineage_builds_worse_than_a_happy_one():
    """Glede is a need. The first recommendation says to eat with pleasure."""
    ascetic, _, _ = run(foods.ASCETIC, ticks=9_000)
    standard, _, _ = run(foods.STANDARD, ticks=9_000)
    assert standard.glede > ascetic.glede
    assert standard.anabolic_multiplier > ascetic.anabolic_multiplier
    assert ascetic.damage == pytest.approx(0.0, abs=1e-6)


def test_damage_is_superlinear_so_a_little_is_nearly_free():
    """One portion of something rich should cost almost nothing, and four
    portions a great deal more than four times as much."""
    def damage_from(portions):
        vigour, _, _ = run({"wholegrain": 2.0, "sweets": portions}, ticks=9_000)
        return vigour.damage

    little, lots = damage_from(0.35), damage_from(1.4)
    assert little < 1.0, f"a small indulgence should be nearly free, got {little}"
    assert lots > little * 4.0, "four times the sweets must cost far more than four times"


def test_a_food_below_its_forgiven_intake_does_no_harm_at_all():
    sweets = foods.BY_ID["sweets"]
    assert sweets.forgiven > 0
    vigour, _, _ = run({"wholegrain": 3.0, "sweets": 0.1}, ticks=9_000)
    assert vigour.damage < 0.05


def test_damage_never_heals():
    """The interesting decision is the one made at the time, not the one
    unwound afterwards."""
    flow, marks, vigour = build("growing", seed=0, diet=foods.INDULGENT)
    for _ in range(9_000):
        flow.step()
        vigour.update(tuning.DT)
    harmed = vigour.damage
    assert harmed > 1.0
    vigour.diet = dict(foods.ASCETIC)
    for _ in range(9_000):
        flow.step()
        vigour.update(tuning.DT)
    assert vigour.damage >= harmed


def test_a_worn_out_lineage_pays_more_simply_to_exist():
    """How "you die earlier" is expressed in a game with no lifespan counter."""
    vigour, _, _ = run(foods.INDULGENT)
    assert vigour.vigour < 0.5
    assert vigour.upkeep_multiplier > 2.0
    assert vigour.anabolic_multiplier < 0.6


def test_the_score_depends_on_what_is_left_not_only_on_what_was_made():
    """On output alone the diets tie, which is why vigour multiplies the score
    rather than sitting beside it."""
    rich, made_rich, score_rich = run(foods.INDULGENT)
    good, made_good, score_good = run(foods.STANDARD)
    assert made_rich > made_good * 0.9, "output alone should not separate them"
    assert score_good > score_rich * 2.0, "the state left behind should"
