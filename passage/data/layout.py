"""The plate, placed by hand, once, and kept forever.

This is a fixed anatomical composition, not a graph auto-layout, and that is
not a stylistic preference. The player is meant to learn this page the way a
Factorio player learns the recipe tree -- permanently -- and a layout that
shifts between runs destroys that. Nothing in this file is computed. If a
position wants changing, change the number.

Coordinates are in window pixels at 1280x720. The plate occupies the centre;
the cell roster is the left margin and the target and rates are the right.
"""

from __future__ import annotations

Point = tuple[float, float]

WINDOW: tuple[int, int] = (1280, 720)

#: The three regions of the page (spec 2).
ROSTER = (0, 0, 196, 720)          # left margin: cells, and later the lineage tree
PLATE = (196, 0, 780, 720)         # the plate itself
PANEL = (976, 0, 304, 720)         # right margin: target, rates, annotation

#: Where the printed gene register sits, ruled along the bottom of the plate.
REGISTER = (212, 574, 748, 132)

#: Every pooled metabolite that is drawn *on the chart*, as (x, y, radius).
#:
#: The composition is a reading order, not a graph. Glycolysis runs straight
#: down the left, in the cytosol, the way every textbook prints it. The
#: mitochondrion is a compartment of its own on the right, with the cycle drawn
#: as a ring inside it. Everything that trades with the medium sits against the
#: membrane, where its transporter is. The eye goes down, then right, then
#: round -- and that path is the same path the carbon takes.
#:
#: The four conserved carriers are deliberately absent. On a real biochemical
#: chart there is no ATP node: ATP rides a curved arrow across the reaction that
#: spends it. A chart that gives it a box of its own reads as a generic node
#: graph, which is exactly the failing this layout was rebuilt to fix. Their
#: stocks are read in the right margin, with the other instruments.
POOLS: dict[str, tuple[float, float, float]] = {
    # the glycolytic trunk, down the left, in the cytosol
    "glucose":      (330, 152, 24),
    "g3p":          (330, 248, 20),
    "pyruvate":     (330, 348, 22),
    "lactate":      (330, 440, 20),

    # what the lineage is for, and what it stores
    "biomass":      (404, 468, 26),
    "palmitate":    (524, 466, 21),

    # inside the mitochondrion: the crossroads, and the ring
    "acetyl":       (600, 282, 23),
    "akg":          (786, 292, 20),
    "oxaloacetate": (692, 398, 21),

    # against the membrane on the right, where respiration trades gas
    "o2":           (872, 228, 19),
    "co2":          (872, 378, 18),

    # the nitrogen corner: what the lineage may adopt, and its waste
    "glutamate":    (756, 462, 21),
    "ammonia":      (842, 434, 16),
}

#: The conserved pairs. Not chart nodes -- readings, taken in the right margin.
CARRIERS: tuple[str, ...] = ("atp", "adp", "nad", "nadh")

#: The inner compartment. Half of central metabolism happens inside the
#: mitochondrion and half does not, and a substance crossing that line is doing
#: something a substance moving within a compartment is not. Every real chart
#: draws it; leaving it out was what made this page look like a flat graph.
#: Drawn with a double line, because it is a double membrane.
MITOCHONDRION: tuple[Point, float, float] = ((692, 318), 152.0, 0.78)

#: The cell envelope. A rounded slab rather than an ellipse: a cell in a tissue
#: is pressed against its neighbours, and the flat sides are also what give the
#: interior room to hold a pathway instead of crowding it to the centre.
CELL_ENVELOPE: tuple[Point, float, float, float] = ((592, 300), 326.0, 0.638, 3.8)

#: Every reaction, as the vessel that carries it. Hand-drawn waypoints, run
#: through a spline, with an arrowhead at the far end. Direction is information.
VESSELS: dict[str, list[Point]] = {
    "glycolysis_upper":  [(330, 174), (320, 199), (330, 226)],
    "glycolysis_lower":  [(330, 270), (341, 299), (330, 326)],
    "gluconeogenesis":   [(310, 326), (274, 292), (274, 204), (310, 170)],

    "fermentation":      [(332, 372), (344, 400), (332, 418)],

    # across the mitochondrial membrane, which is a real step and looks like one
    "pdh":               [(353, 344), (430, 338), (500, 314), (577, 290)],

    # The ring. One stroke leaves oxaloacetate, passes the acetyl group it
    # condenses with, and sweeps over the top to oxoglutarate; a second brings
    # the carbon back down the right. Drawn closed, because it is a cycle, and
    # a cycle drawn as two straight arrows is not recognisable as one.
    "tca_upper":         [(678, 378), (636, 336), (616, 302), (628, 268),
                          (676, 244), (734, 252), (770, 274)],
    "tca_lower":         [(792, 314), (792, 350), (762, 384), (714, 398)],

    # The respiratory chain is not a step in a pathway, it is machinery sunk
    # through the membrane, so it is drawn as a short heavy bar crossing it
    # rather than as an arc running along it -- where, drawn as an arc, it was
    # simply lost against the membrane's own double line.
    "oxphos":            [(816, 318), (868, 318)],

    # in and out of the ring: the bowed pair the player has to keep in balance
    "anaplerosis":       [(348, 366), (444, 424), (562, 444), (666, 416)],
    "cataplerosis":      [(670, 420), (556, 464), (430, 452), (344, 374)],

    "biosynthesis":      [(582, 298), (516, 358), (452, 424), (424, 452)],

    # lipids leave and re-enter at the same carbon, by two different routes
    "lipogenesis":       [(600, 306), (592, 376), (560, 432), (542, 448)],
    "beta_oxidation":    [(546, 448), (574, 390), (596, 326), (602, 302)],

    "gdh":               [(760, 440), (778, 398), (790, 346), (788, 314)],

    # the cost of being alive: spent in the cytosol, going nowhere, and drawn
    # as a closed curl because that is exactly what it is
    "maintenance":       [(408, 222), (438, 240), (408, 258)],
}

#: What each reaction carries across itself on a curved arrow: what goes in,
#: what comes out, and which side of the vessel to draw it. This is the idiom
#: that makes the page read as biochemistry rather than as a flow diagram.
#:
#: Only the trunk carries one. Every reaction in the network uses a cofactor,
#: and drawing all fifteen turned the page into soup: at this size the labels
#: collide with the metabolite names and with each other. A real chart gets away
#: with it by being a poster. So the steps that define the shape of central
#: metabolism carry their arc, and the rest do not.
COFACTORS: dict[str, tuple[str, str, bool]] = {
    "glycolysis_upper":  ("ATP", "ADP", True),
    "glycolysis_lower":  ("NAD+", "NADH", True),
    "fermentation":      ("NADH", "NAD+", False),
    "pdh":               ("NAD+", "NADH", True),
    "tca_lower":         ("NAD+", "NADH", False),
    "oxphos":            ("ADP", "ATP", False),
    "maintenance":       ("ATP", "ADP", True),
}

#: The gases. A gas is not a station on a pathway, it is something a reaction
#: takes from the medium or lets go of, and a chart draws it as a light limb
#: joining the arrow rather than as another node in the chain. Each entry is a
#: path with a small arrowhead at its far end.
TRIBUTARIES: dict[str, list[Point]] = {
    "o2_to_chain":   [(870, 248), (874, 278), (868, 304)],
    "co2_off_ring":  [(768, 392), (812, 386), (850, 380)],
}

#: How heavily each vessel is inked. Real charts have a hierarchy: the trunk is
#: heavy, the branches lighter, the side reactions lighter still. Drawing every
#: line at one weight is most of what makes a diagram look machine-made.
WEIGHTS: dict[str, float] = {
    "glycolysis_upper": 2.3, "glycolysis_lower": 2.3, "pdh": 2.1,
    "tca_upper": 2.1, "tca_lower": 2.1, "oxphos": 2.8,
    "fermentation": 1.7, "biosynthesis": 1.7, "beta_oxidation": 1.5,
    "anaplerosis": 1.3, "cataplerosis": 1.1, "gluconeogenesis": 1.1,
    "lipogenesis": 1.1, "gdh": 1.4, "maintenance": 1.2,
}

#: Traffic with the medium: a short stub leaving each pool outward, ticked at
#: the far end. Passive and bidirectional -- the direction a player reads is the
#: flow mark travelling along it, not a printed arrowhead. Each one starts on
#: the pool and ends outside the envelope, so it visibly crosses the membrane.
EXCHANGE_STUBS: dict[str, tuple[Point, Point]] = {
    "exchange_glucose":   ((330, 128), (308, 68)),
    "exchange_lactate":   ((314, 454), (262, 488)),
    "exchange_o2":        ((891, 228), (940, 210)),
    "exchange_co2":       ((890, 378), (940, 392)),
    "exchange_ammonia":   ((858, 434), (908, 458)),
    "exchange_glutamate": ((752, 483), (726, 530)),
    "exchange_palmitate": ((516, 486), (494, 532)),
}

#: Where a leader line leaves a feature, when the margin has something to say
#: about it. Annotation lives in the margin, never in a tooltip over the plate.
LEADER_ANCHORS: dict[str, Point] = {
    "glucose": (356, 140), "g3p": (352, 248), "pyruvate": (354, 348),
    "lactate": (352, 456), "biomass": (430, 484),
    "acetyl": (622, 268), "oxaloacetate": (692, 421), "akg": (806, 292),
    "palmitate": (546, 466), "glutamate": (778, 462),
}

def envelope_depth(x: float, y: float) -> float:
    """How far out towards the membrane a point is. 1.0 is on it.

    The envelope is a superellipse, so the plain ellipse test is wrong for it:
    a point at the flat side of the slab reads as far outside under the ellipse
    formula while being comfortably inside the drawn membrane.
    """
    (cx, cy), a, squash, fullness = CELL_ENVELOPE
    b = a * squash
    return (abs((x - cx) / a) ** fullness + abs((y - cy) / b) ** fullness)


#: Where a pool's printed label sits, when directly underneath would put it
#: on top of a vessel. Hand-placed, like everything else here.
POOL_LABEL_OFFSET: dict[str, Point] = {
    "glucose": (-58, -18),
    "g3p": (40, -14),
    "pyruvate": (48, -16),
    "lactate": (-2, 2),
    "biomass": (-8, 2),
    "acetyl": (-38, -56),
    "akg": (-14, -66),
    "oxaloacetate": (-36, 16),
    "palmitate": (-6, 4),
    "glutamate": (42, -10),
    "ammonia": (16, -4),
    "co2": (0, -2),
    "o2": (0, -46),
}

#: The printed gene register, one row per gene, machine-set. The player's marks
#: go directly onto this table.
REGISTER_COLUMNS = 4
REGISTER_ROW_HEIGHT = 21.0
REGISTER_PAD = (14.0, 26.0)


def pool_centre(mid: str) -> Point:
    x, y, _ = POOLS[mid]
    return (x, y)


def pool_radius(mid: str) -> float:
    return POOLS[mid][2]


def register_cell(row: int, column: int) -> Point:
    """Top-left of one gene's row in the printed register."""
    x, y, w, _ = REGISTER
    col_w = (w - REGISTER_PAD[0] * 2) / REGISTER_COLUMNS
    return (x + REGISTER_PAD[0] + column * col_w,
            y + REGISTER_PAD[1] + row * REGISTER_ROW_HEIGHT)


def register_column_width() -> float:
    return (REGISTER[2] - REGISTER_PAD[0] * 2) / REGISTER_COLUMNS
