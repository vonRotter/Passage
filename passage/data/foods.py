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
    # Fruit carries fructose in life, and it carried it here for one draft.
    # It made every diet in the game do damage, because the shunt is not
    # regulated and an unconfigured cell takes in what it cannot use — which
    # broke the axis this whole table exists to hold up: plain food costs
    # nothing. Fructose is the sweet-food door, and only that.
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
    # forgiven rose from 0.2 to 0.45 when sweets gained a gate of their own.
    # Harm is charged on intake above the threshold, and intake is attributed
    # per gate: fructose comes from nothing else, so all of it is booked to
    # sweets, where before their sugar was pooled with the wholegrain's and
    # split proportionally. The same portions now measure about twice the
    # intake, so the threshold has to move with the basis it is measured on.
    Food("sweets", "sweets, snacks and sweet baking",
         {"glucose": 1.7, "fructose": 1.7}, relish=0.95, harm=0.95,
         forgiven=0.45,
         trait="half of it fructose, which does not go past the brake",
         note="the fastest relish in the game, and half of it arrives as "
              "fructose — which joins glycolysis below PFK-1, so silencing "
              "the regulation point does not slow it at all. The damage is in "
              "the square: one portion is nearly free and four are not"),
    Food("drink", "beer, wine and spirits",
         {"ethanol": 3.0}, relish=0.72, harm=0.30, forgiven=0.25,
         trait="arrives through no door at all, and costs on the way through",
         note="ethanol needs no transporter, so nothing on the register keeps "
              "it out. What it costs is the intermediate: alcohol "
              "dehydrogenase idles high and starts making acetaldehyde "
              "immediately, and only one enzyme clears it"),
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
    "vegetables": 2.06,
    "wholegrain": 1.44,
    "legumes": 0.62,
    "fish": 0.51,
    "dairy": 0.51,
    "red_meat": 0.26,
    "sweets": 0.31,
}

#: Two diets that lose, in opposite directions, kept here because the test that
#: says moderation wins needs something to beat.
#:
#: Every diet here supplies the same total food, to within a per cent or two --
#: every one but ``SPARSE``, which is deliberately half and is the only diet
#: about *quantity*. That normalisation is not a detail, and it went wrong once:
#: ``CREAMY`` drifted eight per cent above the rest and promptly became the best
#: diet for six of the seven constitutions, which looked like a balance problem
#: with the traits and was really just the biggest dinner winning.
#: A spread of diets to choose between. None of them is right on its own -- what
#: makes one right is the constitution it is being fed to.
# Leaning on fat, which is what "low sugar" has to mean if it is to be the
# diet that tests a body's ability to *oxidise*. It used to be the
# protein-heaviest diet on the menu -- glutamate 7.2 against the standard
# diet's 4.1 -- and since biosynthesis takes glutamate straight into biomass
# without oxidising anything, every body grew perfectly well on it whatever
# its trait broke. It was the reason a lineage that cannot respire looked
# identical on every diet.
LOW_SUGAR: dict[str, float] = {
    "butter": 5.32, "fish": 1.06, "vegetables": 1.06,
}
LOW_FAT: dict[str, float] = {
    "wholegrain": 2.55, "vegetables": 1.65, "legumes": 0.95, "sweets": 0.3,
}
LOW_PROTEIN: dict[str, float] = {
    "wholegrain": 2.4, "vegetables": 1.25, "butter": 1.35, "sweets": 0.6,
}
CREAMY: dict[str, float] = {
    "dairy": 4.08, "vegetables": 1.20, "wholegrain": 0.83, "sweets": 0.28,
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


#: Asked for by name. Fish and olive oil rather than butter and red meat: fat
#: and nitrogen together, carbohydrate slowly, and very little that costs
#: anything. It is the diet the food table's own harm coefficients like best,
#: which is not a coincidence -- fish is the one rich food in the game with a
#: harm of zero.
MEDITERRANEAN: dict[str, float] = {
    "vegetables": 2.02, "fish": 1.38, "wholegrain": 1.20, "legumes": 0.92,
    "dairy": 0.46, "red_meat": 0.09,
}

MENU: dict[str, dict[str, float]] = {
    "standard": STANDARD,
    "mediterranean": MEDITERRANEAN,
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
