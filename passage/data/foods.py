"""What the lineage eats, what it costs, and what it is worth.

A second axis, crossing yield: **relish** -- the pleasure of eating -- against
**damage**, which the lineage carries for the rest of the run.

This is not a moralising system, and that is deliberate. Relish is a *need*: a
lineage that never has any grows badly, and the question is never whether to
have some but what you are willing to pay for it.

The shape the numbers below produce:

* plain food buys relish slowly -- you need a great deal of it -- and costs
  nothing;
* rich food buys relish cheaply, and its damage is **superlinear**, so a little
  is nearly free and a lot is ruinous;
* relish itself saturates, so past a point more indulgence buys no more
  happiness and only more damage.

So the best diet is neither abstinence nor excess, and -- once constitutions
arrive -- it is not even the same diet for every lineage. Which is the whole
point: a player has to work out what *this* genome wants, by watching it.

Provenance, for whoever tunes these numbers next: the food list and its
proportions are modelled on current Nordic public-health dietary advice. That
is where the shape came from and it is worth knowing when changing a number,
but it is scaffolding rather than subject matter, and none of it is surfaced to
the player. This is a game about a cell, not a nutrition guide, and nobody
should take a dietary decision from it.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Food:
    id: str
    label: str
    #: What one portion puts into the medium, per second, by metabolite.
    supplies: dict[str, float]
    #: Relish per unit actually eaten. Rich food is efficient at this and that is
    #: exactly why it is a trap.
    relish: float
    #: Damage coefficient. Applied to the *square* of intake, so a little costs
    #: almost nothing and a lot costs a great deal.
    harm: float
    #: Below this intake a food does no harm at all, whatever its coefficient.
    forgiven: float = 0.0
    trait: str = ""
    note: str = ""


#: Every food enters through one of the four gates the network already has:
#: glucose, palmitate, glutamate, lactate. The distinct entry points the design
#: calls for -- fibre fermented to short-chain fatty acids arriving at
#: acetyl-CoA, fructose slipping past the regulation point, ethanol with its
#: toxic intermediate -- are what M5 is for. What is here already carries the
#: relish-against-damage axis, which is the part that needed proving.
FOODS: list[Food] = [
    Food("vegetables", "vegetables, fruit and berries",
         {"glucose": 1.1, "glutamate": 0.9}, relish=0.10, harm=0.0,
         trait="bulk without density; the staple of a plain diet",
         note="bulky and slow. You need a great deal of it to be happy, and it "
              "never costs you anything"),
    Food("wholegrain", "wholegrain",
         {"glucose": 2.2}, relish=0.14, harm=0.0,
         trait="sugar released slowly rather than all at once",
         note="steady sugar without the spike, and no damage at any intake"),
    Food("legumes", "beans and lentils",
         {"glutamate": 1.6, "glucose": 0.5}, relish=0.13, harm=0.0,
         trait="nitrogen without the fat",
         note="nitrogen without the fat that comes with meat"),
    Food("fish", "fish and seafood",
         {"palmitate": 0.5, "glutamate": 1.2}, relish=0.34, harm=0.0,
         trait="fat and nitrogen together, and neither of them costly",
         note="fat and nitrogen together, and the one rich thing that costs "
              "nothing"),
    Food("dairy", "milk and dairy",
         {"glutamate": 0.8, "glucose": 0.6, "palmitate": 0.25},
         relish=0.28, harm=0.10, forgiven=0.9,
         trait="a little of everything, and a little fat with it",
         note="worth having every day; the fat is what carries the cost"),
    Food("red_meat", "red meat",
         {"glutamate": 1.5, "palmitate": 0.7}, relish=0.55, harm=0.55,
         forgiven=0.35,
         trait="dense nitrogen, carried in on saturated fat",
         note="excellent nitrogen, and a saturated fat load that is fine in "
              "small amounts and expensive in large ones"),
    Food("processed_meat", "processed meat",
         {"glutamate": 1.2, "palmitate": 0.9}, relish=0.80, harm=1.10,
         forgiven=0.15,
         trait="the most relish for the least food",
         note="the most relish for the least food, and the steepest bill. "
              "A wee bit of bacon is good for your morale and for nothing else"),
    Food("sweets", "sweets, snacks and sweet baking",
         {"glucose": 3.4}, relish=0.95, harm=0.95, forgiven=0.2,
         trait="sugar, and nothing else at all",
         note="sugar straight into glycolysis, and the fastest relish in the "
              "game. The damage is in the square, so one portion is nearly "
              "free and four are not"),
    Food("butter", "butter and saturated fat",
         {"palmitate": 1.5}, relish=0.62, harm=0.85, forgiven=0.2,
         trait="fat alone, straight past glycolysis",
         note="bypasses glycolysis entirely and lands at acetyl-CoA, which "
              "makes every glycolytic mark you own irrelevant"),
]

BY_ID: dict[str, Food] = {f.id: f for f in FOODS}

#: The opening diet: mostly plants, some fish, a little of what you like.
#: A middling diet that suits nobody in particular, which is the point: it is
#: where a run starts, not where it should end.
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
#: that more food grows more cell. The question is *what* you eat, at the same
#: amount.
#: A spread of diets to choose between. None of them is right on its own -- what
#: makes one right is the constitution it is being fed to.
LOW_SUGAR: dict[str, float] = {
    "fish": 2.2, "legumes": 1.9, "vegetables": 0.9, "butter": 0.9,
    "red_meat": 0.5,
}
LOW_FAT: dict[str, float] = {
    "wholegrain": 2.55, "vegetables": 1.65, "legumes": 0.95, "sweets": 0.3,
}
LOW_PROTEIN: dict[str, float] = {
    "wholegrain": 2.4, "vegetables": 1.25, "butter": 1.35, "sweets": 0.6,
}
CREAMY: dict[str, float] = {
    "dairy": 4.4, "vegetables": 1.3, "wholegrain": 0.9, "sweets": 0.3,
}
SPARSE: dict[str, float] = {
    "vegetables": 1.2, "wholegrain": 0.8, "legumes": 0.4, "fish": 0.35,
    "dairy": 0.25, "sweets": 0.12,
}

INDULGENT: dict[str, float] = {
    "sweets": 1.90, "processed_meat": 1.02, "butter": 0.88, "red_meat": 0.73,
    "wholegrain": 0.22,
}
ASCETIC: dict[str, float] = {
    "vegetables": 2.87, "wholegrain": 1.86, "legumes": 1.01,
}


MENU: dict[str, dict[str, float]] = {
    "standard": STANDARD,
    "low sugar": LOW_SUGAR,
    "low fat": LOW_FAT,
    "low protein": LOW_PROTEIN,
    "creamy": CREAMY,
    "sparse": SPARSE,
    "plain": ASCETIC,
    "rich": INDULGENT,
}


def supply(diet: dict[str, float]) -> float:
    """Total food a diet puts into the medium, per second. For comparing fairly."""
    return sum(portions * sum(BY_ID[food].supplies.values())
               for food, portions in diet.items())
