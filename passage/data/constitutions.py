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
    #: Multipliers on a food's *forgiven* intake -- how much of it this body can
    #: take before it costs anything. Below 1 is a lower tolerance.
    #:
    #: Separate from ``handles`` because they are different complaints and only
    #: one of them was expressible. ``handles`` scales the damage above the
    #: threshold, so for a food whose threshold nobody reaches it multiplies
    #: zero: dairy is forgiven up to 0.9 and a heavy dairy diet delivers 1.3, so
    #: a body that "pays more for milk" paid more for almost nothing. A low
    #: tolerance is the honest shape of the complaint anyway -- it is not that
    #: milk is more toxic to you, it is that you can take less of it.
    tolerates: dict[str, float] = field(default_factory=dict)
    #: Multipliers on what a food actually delivers into the medium.
    absorbs: dict[str, float] = field(default_factory=dict)
    #: What a food turns into for this body instead of what it is for everyone
    #: else, as ``{food: {from metabolite: to metabolite}}``. Sugar this lineage
    #: cannot digest does not simply fail to arrive -- it is fermented on the
    #: way in and arrives as acid.
    redirects: dict[str, dict[str, str]] = field(default_factory=dict)
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
        # 0.06, not 0.6. The number looks drastic and is not: base rates on
        # this plate sit far above what a cell actually draws, so a multiplier
        # only *binds* once it cuts below the flux the step is carrying. With
        # PFK-1 marked, glycolysis_upper can do 9.0/s and the cell wants about
        # 0.8/s; at 0.6 the ceiling was still ten times the demand and the
        # trait did nothing at all. At 0.06 the ceiling is 0.54/s and a
        # sugar-led diet builds less than half what an even body builds on it.
        capacity={"glycolysis_upper": 0.06},
        handles={"sweets": 1.8},
        holds={"glucose": 0.8, "fructose": 0.75},
        counsel="Glycolysis itself is the ceiling here, so mark PFK-1 up: "
                "this is the one body in the game that gains by pushing the "
                "regulation point rather than shutting it. Do not shut the "
                "fructose transporter either — fructose joins below the "
                "crippled step and is most of the carbon this lineage can "
                "actually use, so closing that door starves it. What it "
                "really wants is less food, not different food.",
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
        # As above: the chain runs at about 2.0/s and could do 15.0, so 0.42
        # was never the constraint. 0.15 puts the ceiling at 2.25/s, just
        # inside what a respiring cell wants, and it builds a little over half.
        #
        # The baseline override on `etc` is gone. It raised the idle to 0.45
        # against a standard 0.30 while the capacity was meant to be cutting
        # the same step down -- the trait was quietly undoing itself, and for a
        # player who marks the respiratory chain at all the baseline never
        # applied in the first place.
        capacity={"oxphos": 0.15},
        holds={"acetyl": 0.55, "pyruvate": 0.6},
        baseline={"ldh": 0.25},
        counsel="Everything this lineage eats and cannot burn becomes damage, "
                "so it wants less food rather than different food — and it "
                "will lean on fermentation whether you ask it to or not.",
    ),

    Constitution(
        "nitrogen_poor", "poor nitrogen handling",
        "it takes more amino acid to build the same cell, and what it strips "
        "it cannot send out",
        # This trait used to be clearance alone: deaminate readily, export
        # badly, and choke on your own ammonia. It had no teeth. Ammonia's pool
        # is small, so it fills, product inhibition stops GDH, and the cell
        # simply stops deaminating -- which costs it nothing, because it was
        # not gaining from GDH in the first place. A trait whose whole cost is
        # "you may not use a route you did not need" is not a trait.
        #
        # What bites in a game scored on what you *build* is a worse rate on
        # the nitrogen the cell actually consumes. Biosynthesis needs glutamate
        # for every unit of biomass; this body needs far more of it about to
        # run at the same speed. The clearance problem stays, because it is
        # what makes a protein-heavy diet uncomfortable rather than simply
        # better -- but the preference it produces is the opposite of what the
        # old counsel said, and the counsel was describing a mechanism that
        # never worked.
        affinity={"glutamate": 5.0},
        capacity={"exchange_ammonia": 0.14, "gdh": 1.5},
        holds={"ammonia": 0.09},
        baseline={"amt": 0.10, "gdh": 0.55},
        counsel="Nitrogen is the problem here, and the answer is more of it "
                "rather than less: this lineage needs a great deal of amino "
                "acid about before it will build at any speed. A diet thin in "
                "protein starves it. What it strips it still cannot send out, "
                "so give it the nitrogen and leave glutamate dehydrogenase "
                "alone.",
    ),

    Constitution(
        "milk_intolerant", "no milk tolerance",
        "milk sugar this lineage cannot take in, and cannot take much of",
        # This trait used to redirect milk sugar to lactate, on the reasoning
        # that undigested sugar ferments on the way in and arrives as acid. It
        # reads well and it was backwards: lactate joins the pathway at
        # pyruvate, *after* the two ATP glycolysis spends getting there, so the
        # redirect handed this lineage a cheaper route than everyone else's. It
        # built half again as much on a dairy diet as an even lineage did. What
        # had been hiding that was a congestion rule charging for pool fill,
        # which is a different fault and is fixed elsewhere; with the fill rule
        # corrected, being lactose intolerant was simply an advantage.
        #
        # So it is what it plainly is instead: most of the milk sugar never
        # arrives, and the little that does is tolerated badly. Sound in the
        # fiction, and it costs this body only when it actually drinks milk.
        absorbs={"dairy": 0.45},
        tolerates={"dairy": 0.06},
        handles={"dairy": 6.0},
        holds={"lactate": 0.3},
        counsel="Most of what milk offers this lineage never gets in, and the "
                "little that does is tolerated badly — a dairy-led diet costs "
                "it a quarter of its score and gives it less than it gives "
                "anyone else. On any other diet the trait is invisible. Take "
                "the fat and the nitrogen from somewhere else.",
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
