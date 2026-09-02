"""The palette. Warm, aged, low saturation. Nothing in this game is bright.

Colour here is taxonomic, not decorative (art direction 2). Six metabolite
classes, six washes, and the mapping is fixed forever because the player learns
it permanently: a cell choked with waste and a cell starving for sugar must be
tellable apart across the room, before a single word is read.

One alarm colour, used only for spillover and damage, and used nowhere else.
"""

from __future__ import annotations

from ..data.metabolites import Class

RGB = tuple[int, int, int]

# --- the substrate --------------------------------------------------------
PAPER: RGB = (233, 224, 202)        # warm cream
PAPER_EDGE: RGB = (198, 184, 158)   # darker and slightly stained toward the edges
FOXING: RGB = (166, 132, 92)        # the small rust-brown stains of age
INK: RGB = (46, 38, 30)             # sepia-black; the colour of iron gall ink
INK_FAINT: RGB = (120, 106, 88)     # unadopted pathways, printed but quiet
PENCIL: RGB = (112, 104, 92)        # the player's own working notes

# --- the functional palette -----------------------------------------------
CLASS_WASH: dict[Class, RGB] = {
    Class.SUGARS:      (186, 140, 74),    # warm ochre; the staple, and edible
    Class.LIPIDS:      (214, 194, 126),   # pale butter-yellow; dense, slow, stored
    Class.AMINO_ACIDS: (180, 124, 122),   # muted rose; the building material
    Class.ENERGY:      (162, 58, 46),     # arterial red; the live one
    Class.GASES:       (134, 156, 172),   # pale dusty blue, venous blue's cousin
    Class.WASTE:       (126, 134, 106),   # grey-green, and it should read unpleasant
}

#: Spillover and damage. Sourer and deeper than the waste wash, and the only
#: place in the game this colour is ever allowed to appear.
ALARM: RGB = (88, 118, 54)


def wash_for(cls: Class) -> RGB:
    return CLASS_WASH.get(cls, INK_FAINT)


def fade(colour: RGB, amount: float, toward: RGB = PAPER) -> RGB:
    """Mix a colour toward the paper. 0 is untouched, 1 is gone.

    Inherited marks fade one step per generation of inheritance, to a floor
    (art direction 5), and unadopted pathways sit permanently faded. Nothing is
    ever hidden; things are merely quiet.
    """
    a = max(0.0, min(1.0, amount))
    return tuple(int(round(c + (t - c) * a)) for c, t in zip(colour, toward))
