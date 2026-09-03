"""Differentiation directions: preset mark bundles a daughter can be pushed into.

Not a class system with names and portraits. A specialism here is nothing but a
bulk mark operation, and a cell heavily marked toward one pathway *is* a
specialist whether or not this shortcut was used to get there. What the preset
buys is the shove: it clears the inherited configuration wholesale and writes a
different one, for one flat cost instead of the per-mark price of lifting each
old mark by hand.

**The trade always bites.** Every specialism below is a cell that has switched
something important off. A feeder cannot burn what it makes. A burner cannot
make what it burns. Each is only viable if something else covers the gap, and
covering the gap means a junction, and junctions are shared and lossy. Every
specialist you create is a new transport requirement, and transport is where
your efficiency goes to die.

The pairing worth noticing is the feeder and the burner. One runs glycolysis
hard and pours out lactate; the other takes lactate in and oxidises it. That is
a real arrangement between real cells -- one tissue's waste is the next one's
fuel -- and here it is the only way a lineage moves carbon between its members,
because the conserved carriers do not cross a junction.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Specialism:
    id: str
    label: str
    #: Genes to activate and genes to silence. Everything else goes to baseline.
    activate: tuple[str, ...] = ()
    silence: tuple[str, ...] = ()
    summary: str = ""
    needs: str = ""                 # what it cannot supply for itself
    gives: str = ""                 # what it produces in surplus


#: Five marks each, which is what fits: the budget is eight and the shove costs
#: two and a half of it. What a bundle leaves *out* is deliberate -- every one
#: of these has a weakness left at baseline for the player to find and pay to
#: fix, once the cost of the shove has decayed.
SPECIALISMS: list[Specialism] = [
    Specialism(
        "feeder", "glycolytic feeder",
        activate=("glut", "pfk", "gapdh", "ldh"),
        silence=("cs",),
        summary="runs glycolysis hard and pours the lactate out",
        needs="nothing much, but it wastes most of what it eats",
        gives="lactate, which is fuel to anything that can oxidise it",
    ),
    Specialism(
        "burner", "oxidative burner",
        activate=("mct", "ldh", "pdh", "etc"),
        silence=("pfk",),
        summary="takes lactate in and burns it properly",
        needs="lactate, from a feeder it is close enough to reach",
        gives="a great deal of ATP, which it cannot share",
    ),
    Specialism(
        "builder", "anabolic builder",
        activate=("biosyn", "aat", "cs", "etc"),
        silence=("fas",),
        summary="turns carbon and nitrogen into cell material and little else",
        needs="acetyl and glutamate, fed to it",
        gives="biomass, which is what the target is counted in",
    ),
    Specialism(
        "clearer", "waste handler",
        activate=("amt", "gdh", "mct", "etc"),
        silence=("fas",),
        summary="takes the nitrogen and the lactate off everybody else",
        needs="somewhere to put what it clears",
        gives="room. A lineage without one silts up",
    ),
    Specialism(
        "storer", "fat store",
        activate=("fas", "glut", "pfk", "gapdh"),
        silence=("acad",),
        summary="banks surplus carbon as fat it cannot pass on",
        needs="acetyl, in surplus",
        gives="nothing, until the lineage is short and it burns it back",
    ),
]

BY_ID: dict[str, Specialism] = {s.id: s for s in SPECIALISMS}
