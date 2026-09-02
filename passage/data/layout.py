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

#: Every pooled metabolite, as (x, y, radius). Organelle-like forms inside the
#: cell, each filled with its class wash to a level proportional to fill.
POOLS: dict[str, tuple[float, float, float]] = {
    # the glycolytic trunk, running down the left of the plate
    "glucose":      (312, 182, 27),
    "g3p":          (312, 262, 23),
    "pyruvate":     (312, 342, 25),
    "lactate":      (238, 412, 22),

    # the crossroads, and the cycle below it
    "acetyl":       (404, 404, 25),
    "oxaloacetate": (404, 494, 22),
    "akg":          (536, 516, 22),

    # gases, across the empty top of the plate
    "co2":          (470, 150, 20),
    "o2":           (556, 172, 21),

    # what the lineage may adopt later, drawn faintly until it does.
    # Palmitate sits close to acetyl-CoA because that is where it enters; the
    # short vessel and the long bypassed trunk are the same statement.
    "palmitate":    (632, 326, 23),
    "glutamate":    (700, 478, 23),
    "ammonia":      (768, 506, 18),

    # the target
    "biomass":      (296, 458, 30),

    # the two conserved carrier pairs, ruled down the right of the plate
    "atp":          (884, 262, 24),
    "adp":          (884, 330, 22),
    "nadh":         (804, 398, 22),
    "nad":          (884, 398, 22),
}

#: Every reaction, as the vessel that carries it. Hand-drawn waypoints, run
#: through a spline. Vessels are curves, never straight lines.
VESSELS: dict[str, list[Point]] = {
    "glycolysis_upper":  [(312, 211), (304, 226), (312, 239)],
    "glycolysis_lower":  [(312, 287), (320, 306), (312, 317)],
    "gluconeogenesis":   [(290, 284), (262, 262), (262, 220), (288, 193)],

    "fermentation":      [(292, 360), (268, 386), (256, 396)],
    "pdh":               [(330, 358), (368, 382), (384, 392)],

    # the citric acid cycle, drawn as a ring so that it reads as one
    "tca_upper":         [(408, 430), (422, 478), (478, 522), (513, 518)],
    "tca_lower":         [(532, 538), (492, 558), (438, 546), (406, 517)],

    # in and out of the cycle: the pair the player has to keep in balance,
    # bowed apart so that neither hides the other
    "anaplerosis":       [(322, 366), (356, 420), (390, 470)],
    "cataplerosis":      [(384, 506), (322, 462), (294, 372)],

    # lipids bypass glycolysis entirely and enter at acetyl-CoA. The vessel
    # sweeping past the whole glycolytic trunk without touching it is the
    # point, not an accident of placement (spec 3.8).
    "beta_oxidation":    [(612, 340), (548, 374), (470, 394), (430, 398)],
    "lipogenesis":       [(428, 384), (486, 358), (556, 334), (612, 314)],

    "gdh":               [(678, 486), (614, 506), (558, 514)],
    "biosynthesis":      [(382, 414), (344, 436), (320, 448)],

    "oxphos":            [(826, 398), (846, 414), (862, 398)],
    "maintenance":       [(886, 286), (906, 308), (886, 306)],
}

#: Traffic with the medium: a short stub leaving each pool outward, ticked at
#: the far end. Deliberately short rather than run all the way out through the
#: envelope -- the membrane is a long way from most pools, and a stub that
#: reached it would be the loudest line on the page for the least information.
#: Passive and bidirectional: the direction a player reads is the flow mark
#: travelling along it, not a printed arrowhead.
EXCHANGE_STUBS: dict[str, tuple[Point, Point]] = {
    "exchange_glucose":   ((312, 153), (306, 92)),
    "exchange_co2":       ((466, 128), (456, 74)),
    "exchange_o2":        ((558, 149), (566, 92)),
    "exchange_lactate":   ((216, 408), (166, 396)),
    "exchange_palmitate": ((650, 310), (706, 256)),
    "exchange_glutamate": ((722, 484), (796, 460)),
    "exchange_ammonia":   ((782, 518), (846, 542)),
}

#: Where a leader line leaves a feature, when the margin has something to say
#: about it. Annotation lives in the margin, never in a tooltip over the plate.
LEADER_ANCHORS: dict[str, Point] = {
    "glucose": (334, 168), "g3p": (332, 250), "pyruvate": (334, 328),
    "acetyl": (424, 392), "oxaloacetate": (386, 512), "akg": (554, 530),
    "lactate": (246, 430), "biomass": (312, 480), "palmitate": (726, 254),
    "glutamate": (712, 460), "atp": (904, 248), "nadh": (790, 414),
}

#: The cell envelope: everything on the plate is inside one cell, and this is
#: its outline. A soft rounded form -- at this scale nothing has anatomy.
CELL_ENVELOPE: tuple[Point, float, float] = ((566, 330), 372.0, 0.608)

#: Where a pool's printed label sits, when directly underneath would put it
#: on top of a vessel. Hand-placed, like everything else here.
POOL_LABEL_OFFSET: dict[str, Point] = {
    "g3p": (-46, -4),
    "oxaloacetate": (-6, 8),
    "pyruvate": (-52, -4),
    "biomass": (-4, 6),
    "akg": (10, 8),
    "nad": (0, 4),
    "atp": (-50, -30),
    "adp": (-50, -30),
    "nadh": (-2, 4),
    "palmitate": (-4, 6),
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
