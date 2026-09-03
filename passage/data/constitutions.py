"""The genome you did not choose.

Every run deals the lineage a **constitution**: a handful of fixed traits that
change how the same plate behaves. A gene that idles higher or lower than
standard. An enzyme with less capacity than the chart says. A transporter with
poorer affinity. A food that this body handles badly, and another it handles
better than most.

None of it can be marked away. That is the whole point, and it is what makes
the game's opening line true rather than decorative: you are working a genome
you did not choose. Marks decide what is switched on. A constitution decides
what switching it on is *worth*, and no amount of budget changes that.

What it does to the game is turn diet from a preference into a diagnosis. There
is no best diet, because the diets are not competing on their own merits -- they
are competing against a body. A lineage that cannot clear ammonia is poisoned by
the meal that suits a lineage that cannot handle sugar. The player has to work
out which one they are holding, and then eat around it.

Nothing here is hidden. The constitution is printed in the appendix from the
first second, as everything else in this game is. The work is not finding out
what you have; it is working out what to do about it.

The traits are drawn loosely from real, well-described metabolic variation --
impaired glucose handling, reduced fatty-acid oxidation, poor urea-cycle
clearance, lactase non-persistence, differences in respiratory-chain capacity --
and then simplified until they fit on one line. They are named for what they do
rather than for any condition, because a game mechanic should not pretend to be
a diagnosis.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Constitution:
    id: str
    label: str
    #: One line, the player reads this and nothing else at first.
    summary: str
    #: Multipliers on reaction capacity, by row id. Below 1 is a weaker enzyme.
    capacity: dict[str, float] = field(default_factory=dict)
    #: Multipliers on a metabolite's Michaelis constant. Above 1 is *worse*
    #: affinity: the cell needs more of it around to work at the same rate.
    affinity: dict[str, float] = field(default_factory=dict)
    #: Multipliers on how much of a metabolite the cell can hold.
    holds: dict[str, float] = field(default_factory=dict)
    #: Overrides on what an unmarked gene idles at.
    baseline: dict[str, float] = field(default_factory=dict)
    #: Multipliers on a food's damage. Above 1 means this body pays more for it.
    handles: dict[str, float] = field(default_factory=dict)
    #: Multipliers on what a food actually delivers into the medium.
    absorbs: dict[str, float] = field(default_factory=dict)
    #: What the player should end up doing about it. Written down because
    #: nothing in this game is hidden -- but they still have to act on it.
    counsel: str = ""


CONSTITUTIONS: list[Constitution] = [
    Constitution(
        "even", "an even constitution",
        "nothing marked either way",
        counsel="No trait pulls this lineage anywhere. A varied diet suits it, "
                "and no diet suits it especially well.",
    ),

    Constitution(
        "sugar_averse", "poor sugar handling",
        "sugar arrives faster than this lineage can use it",
        # Sugar crosses the membrane as readily as it does for anyone -- that
        # is exactly the trouble. What is missing is the capacity to *use* it,
        # so it arrives, sits, fills the cell, and overflows.
        capacity={"glycolysis_upper": 0.6},
        holds={"glucose": 0.8},
        handles={"sweets": 1.8},
        counsel="Sugar that cannot be burnt is sugar that sits in the cell "
                "doing damage. Take the carbon in as fat and as amino acids "
                "instead, and take what sugar you do eat slowly.",
    ),

    Constitution(
        "fat_averse", "poor fat handling",
        "fatty acids come in but are oxidised badly",
        capacity={"beta_oxidation": 0.2},
        holds={"palmitate": 0.34},
        handles={"butter": 1.6},
        counsel="Fat this lineage cannot burn simply accumulates. Lead with "
                "carbohydrate, keep the saturated fat low, and let glycolysis "
                "carry the load that beta-oxidation cannot.",
    ),

    Constitution(
        "slow_burner", "reduced respiratory capacity",
        "the respiratory chain runs at little over half the usual rate",
        capacity={"oxphos": 0.42},
        holds={"acetyl": 0.55, "pyruvate": 0.6},
        baseline={"etc": 0.45, "ldh": 0.25},
        counsel="Everything this lineage eats and cannot burn becomes damage, "
                "so it wants less food rather than different food — and it "
                "will lean on fermentation whether you ask it to or not.",
    ),

    Constitution(
        "nitrogen_poor", "poor nitrogen clearance",
        "ammonia is made faster than it can be sent out",
        # The nitrogen has to actually move for the trait to bite, so this
        # lineage also deaminates more readily than most: it strips amino
        # groups whether or not it has anywhere to put them.
        capacity={"exchange_ammonia": 0.14, "gdh": 1.5},
        holds={"ammonia": 0.09},
        baseline={"amt": 0.10, "gdh": 0.55},
        counsel="Amino acids are the problem here, not sugar or fat. Nitrogen "
                "this lineage takes in has nowhere to go, so keep the protein "
                "low and take the carbon in some other form.",
    ),

    Constitution(
        "milk_intolerant", "no milk tolerance",
        "milk passes through unused, and lactate clears slowly",
        absorbs={"dairy": 0.2},
        handles={"dairy": 3.2},
        holds={"lactate": 0.45},
        capacity={"exchange_lactate": 0.4},
        counsel="This lineage gets almost nothing out of dairy and pays for it "
                "anyway, and it clears lactate slowly on top — so anything that "
                "pushes it toward fermentation costs twice. Take the fat and "
                "the nitrogen from somewhere else, and keep the sugar load low "
                "enough that glycolysis never has to overflow.",
    ),

    Constitution(
        "thrifty", "a thrifty constitution",
        "builds well on very little, and hoards what it does not need",
        # It takes up a third more of everything, which is the whole trouble
        # when there is plenty: it cannot leave anything on the plate.
        capacity={"biosynthesis": 1.25, "lipogenesis": 1.5},
        affinity={"glucose": 0.7, "glutamate": 0.8},
        holds={"glucose": 0.62, "palmitate": 0.6, "glutamate": 0.7},
        absorbs={f: 1.7 for f in ("vegetables", "wholegrain", "legumes", "fish",
                                  "dairy", "red_meat", "processed_meat",
                                  "sweets", "butter")},
        counsel="This lineage is very good at getting everything out of a "
                "small amount of food, which is exactly the problem when there "
                "is a lot of it. Eat less than you think you need.",
    ),
]

BY_ID: dict[str, Constitution] = {c.id: c for c in CONSTITUTIONS}
DEFAULT = "even"


def dealt(seed: int) -> Constitution:
    """The constitution a given seed hands you. Fixed for the run, like the chart."""
    import numpy as np

    others = [c for c in CONSTITUTIONS if c.id != "even"]
    return others[int(np.random.default_rng(seed).integers(len(others)))]
