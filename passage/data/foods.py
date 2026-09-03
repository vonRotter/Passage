"""What the lineage eats, what it costs, and what it is worth.

A second axis, crossing the yield axis: **glede** -- the pleasure of eating --
against **damage**, which is what the lineage carries for the rest of the run.

This is not a moralising system, and that is deliberate, because the guidelines
it is drawn from are not moralising either. The first of the seven Norwegian
dietary recommendations is *"Ha et variert kosthold, velg mest mat fra
planteriket og spis med glede"* -- have a varied diet, choose mostly food from
the plant kingdom, and **eat with pleasure** (Helsedirektoratet, 2024). Pleasure
is inside the advice, not opposed to it. So glede here is a *need*: a lineage
that never has any grows badly, and the question is never whether to have some
but what you are willing to pay for it.

The shape that falls out of the numbers below is the shape of the guidelines:

* wholesome food buys glede slowly -- you need a great deal of it -- and costs
  nothing;
* rich food buys glede cheaply, and its damage is **superlinear**, so a little
  is nearly free and a lot is ruinous;
* glede itself saturates, so past a point more indulgence buys no more
  happiness and only more damage.

Which means the optimum is neither abstinence nor excess. It is mostly plants
and fish with a bit of what you like, arrived at by playing rather than by being
told -- which is the only way a game can say anything about this honestly.

**This is a game, not dietary advice.** The numbers are chosen to make a
metabolic toy behave the way the guidelines describe at a population level. No
one should take a nutrition decision from them.

Quantities and the seven recommendations: Helsedirektoratet. (2024, August 15).
*Kostrådene*. https://www.helsedirektoratet.no/faglige-rad/kostradene-og-naeringsstoffer
Nordic Council of Ministers. (2023). *Nordic nutrition recommendations 2023:
Integrating environmental aspects*. https://doi.org/10.6027/nord2023-003
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Food:
    id: str
    label: str
    #: What one portion puts into the medium, per second, by metabolite.
    supplies: dict[str, float]
    #: Glede per unit actually eaten. Rich food is efficient at this and that is
    #: exactly why it is a trap.
    glede: float
    #: Damage coefficient. Applied to the *square* of intake, so a little costs
    #: almost nothing and a lot costs a great deal.
    harm: float
    #: Below this intake a food does no harm at all, whatever its coefficient.
    forgiven: float = 0.0
    guideline: str = ""
    note: str = ""


#: Every food enters through one of the four gates the network already has:
#: glucose, palmitate, glutamate, lactate. The distinct entry points the design
#: calls for -- fibre fermented to short-chain fatty acids arriving at
#: acetyl-CoA, fructose slipping past the regulation point, ethanol with its
#: toxic intermediate -- are what M5 is for. What is here already carries the
#: glede-against-damage axis, which is the part that needed proving.
FOODS: list[Food] = [
    Food("vegetables", "vegetables, fruit and berries",
         {"glucose": 1.1, "glutamate": 0.9}, glede=0.10, harm=0.0,
         guideline="fruit, berries or vegetables at every meal; 500-800 g a day",
         note="bulky and slow. You need a great deal of it to be happy, and it "
              "never costs you anything"),
    Food("wholegrain", "wholegrain",
         {"glucose": 2.2}, glede=0.14, harm=0.0,
         guideline="wholegrain at several meals every day",
         note="steady sugar without the spike, and no damage at any intake"),
    Food("legumes", "beans and lentils",
         {"glutamate": 1.6, "glucose": 0.5}, glede=0.13, harm=0.0,
         guideline="fish, beans and lentils more often than red meat",
         note="nitrogen without the fat that comes with meat"),
    Food("fish", "fish and seafood",
         {"palmitate": 0.5, "glutamate": 1.2}, glede=0.34, harm=0.0,
         guideline="fish and seafood more often than red meat",
         note="fat and nitrogen together, and the one rich thing that costs "
              "nothing"),
    Food("dairy", "milk and dairy",
         {"glutamate": 0.8, "glucose": 0.6, "palmitate": 0.25},
         glede=0.28, harm=0.10, forgiven=0.9,
         guideline="dairy daily; choose the lower-fat ones",
         note="worth having every day; the fat is what carries the cost"),
    Food("red_meat", "red meat",
         {"glutamate": 1.5, "palmitate": 0.7}, glede=0.55, harm=0.55,
         forgiven=0.35,
         guideline="at most about 350 g of red meat a week",
         note="excellent nitrogen, and a saturated fat load that is fine in "
              "small amounts and expensive in large ones"),
    Food("processed_meat", "processed meat",
         {"glutamate": 1.2, "palmitate": 0.9}, glede=0.80, harm=1.10,
         forgiven=0.15,
         guideline="eat as little processed meat as possible",
         note="the most glede for the least food, and the steepest bill. "
              "A wee bit of bacon is good for your morale and for nothing else"),
    Food("sweets", "sweets, snacks and sweet baking",
         {"glucose": 3.4}, glede=0.95, harm=0.95, forgiven=0.2,
         guideline="limit sweets, snacks and sweet baked goods; drink water",
         note="sugar straight into glycolysis, and the fastest glede in the "
              "game. The damage is in the square, so one portion is nearly "
              "free and four are not"),
    Food("butter", "butter and saturated fat",
         {"palmitate": 1.5}, glede=0.62, harm=0.85, forgiven=0.2,
         guideline="choose the lower-fat dairy; limit saturated fat",
         note="bypasses glycolysis entirely and lands at acetyl-CoA, which "
              "makes every glycolytic mark you own irrelevant"),
]

BY_ID: dict[str, Food] = {f.id: f for f in FOODS}

#: The opening diet: mostly plants, some fish, a little of what you like.
#: Deliberately already close to the guidelines, because the interesting
#: question is what the player changes it *to* when a target starts to bite.
STANDARD: dict[str, float] = {
    "vegetables": 2.0,
    "wholegrain": 1.4,
    "legumes": 0.6,
    "fish": 0.5,
    "dairy": 0.5,
    "red_meat": 0.25,
    "sweets": 0.3,
}

#: Two diets that lose, in opposite directions, kept here because the test that
#: says moderation wins needs something to beat.
#:
#: All three supply the same total food. That normalisation is not a detail: a
#: comparison where the rich diet also happens to be the larger one proves only
#: that more food grows more cell, which is not what the guidelines are about.
#: They are about *what* you eat, at the same amount.
INDULGENT: dict[str, float] = {
    "sweets": 1.90, "processed_meat": 1.02, "butter": 0.88, "red_meat": 0.73,
    "wholegrain": 0.22,
}
ASCETIC: dict[str, float] = {
    "vegetables": 2.87, "wholegrain": 1.86, "legumes": 1.01,
}


def supply(diet: dict[str, float]) -> float:
    """Total food a diet puts into the medium, per second. For comparing fairly."""
    return sum(portions * sum(BY_ID[food].supplies.values())
               for food, portions in diet.items())
