"""Every constant.

Nothing numeric belongs anywhere else. If a number in the simulation wants
changing, it wants changing here.
"""

# --- time -----------------------------------------------------------------
TICK_HZ = 20.0                  # flow simulation rate (spec 2)
DT = 1.0 / TICK_HZ
RENDER_HZ = 60

# --- saturation and inhibition (spec 3.2) ---------------------------------
INHIBITION_EXPONENT = 3.0       # how sharply a filling product pool bites back
INHIBITION_CEILING = 0.97       # a reaction is never quite fully stopped by product
SOLVER_PASSES = 3               # negative-pool guard iterations per tick

# --- expression and enzyme (spec 3.3) -------------------------------------
ENZYME_TAU = 4.0                # seconds for enzyme level to follow expression
EXPRESSION_TAU = 1.5            # seconds for expression to follow its mark target
BASELINE_EXPRESSION = 0.15      # what an unmarked gene drifts to

# --- marks (spec 3.3) -----------------------------------------------------
# Eight marks against eighteen markable genes. Most of the genome sits at
# baseline, running slowly, and choosing what to shut down is the whole game.
MARK_BUDGET = 8

# Removing a mark costs more than placing one and takes longer to bite. This is
# the mechanical form of the inheritance thesis and it is not to be softened for
# convenience: un-silencing a gene you silenced three generations ago has to be
# genuinely expensive.
#
# The cost is a debt against the budget that decays with time rather than a flat
# fee, so a player who thrashes their configuration is short of budget for as
# long as the thrashing lasts, and one who changes their mind once pays once.
REMOVAL_DEBT = 1.6              # budget locked the moment a mark is lifted
REMOVAL_DEBT_PER_GENERATION = 0.8   # and more, per generation the mark was held
REMOVAL_DEBT_HALFLIFE = 45.0    # seconds for that debt to fall by half
REMOVAL_SLOWDOWN = 3.2          # how much slower expression moves after removal
REMOVAL_SLOWDOWN_HALFLIFE = 20.0

# --- pools ----------------------------------------------------------------
SPILL_FRACTION = 1.0            # share of over-cap material that spills per tick
DEFAULT_POOL_CAP = 100.0

# --- carrier pools, conserved totals --------------------------------------
ADENYLATE_TOTAL = 50.0          # ATP + ADP
ADENYLATE_CHARGED = 30.0        # of which ATP at start
NICOTINAMIDE_TOTAL = 20.0       # NAD+ + NADH
NICOTINAMIDE_REDUCED = 3.0      # of which NADH at start

# --- the medium -----------------------------------------------------------
MEDIUM_VOLUME = 1.0
# The medium is perfused, not merely fed: it is held toward a target
# concentration in both directions, at a bounded rate. Substances above target
# are washed out, which is what stops carbon dioxide from backing up into the
# culture and stalling every cell in it. What washes out is metered, because a
# substance the player dumped into the medium still counts against their waste
# score even once it has left.
MEDIUM_TARGET = {
    "glucose": 55.0,
    "o2": 30.0,
    "co2": 0.0,
    "lactate": 0.0,
    "ammonia": 0.0,
    "palmitate": 0.0,
    "glutamate": 9.0,      # culture media carry amino acids. Nitrogen must not
                           # be the hard cap on growth, or no mark on the carbon
                           # side of the plate can ever change anything.
}
MEDIUM_FEED = {                 # units per second, the ceiling on perfusion
    "glucose": 8.0,             # the supply the standard medium can hold up
    "o2": 60.0,
    "co2": 60.0,
    "lactate": 3.0,
    "ammonia": 3.0,
    "palmitate": 0.6,
    "glutamate": 2.0,
}
MEDIUM_START = {
    "glucose": 55.0,
    "o2": 30.0,
}
MEDIUM_CAP = 400.0

# --- starting cell --------------------------------------------------------
CELL_START = {
    "glucose": 8.0,
    "g3p": 2.0,
    "pyruvate": 2.0,
    "oxaloacetate": 5.0,
    "acetyl": 2.0,
    "akg": 3.0,
    "o2": 10.0,
    "co2": 2.0,
}

# --- the cell's cast (art direction 2) ------------------------------------
# The tint is a blend of the six class washes, not a winner-takes-all. Blending
# is what watercolour does, it moves continuously instead of snapping between
# colours, and it lets a cell be mostly-healthy-but-a-bit-choked, which is the
# state a player most needs to catch.
#
# Waste is weighted up because a choked cell must read as choked even when the
# waste pool is a fraction of the sugar pool. Gases are weighted down because
# oxygen sits near full whenever the cell is *not* respiring, and a failing cell
# turning dusty blue would say the opposite of what is happening.
CLASS_TINT_WEIGHT = {
    "sugars": 1.0,
    "lipids": 1.0,
    "amino_acids": 0.9,
    "energy": 1.15,        # taken on charge, not fill: the pair total never moves
    "gases": 0.35,
    "waste": 3.0,
}
TINT_REFERENCE = 1.5       # total weight at which the tint is at full strength

# --- conservation tolerances ---------------------------------------------
BALANCE_TOLERANCE = 1e-9        # atom balance, per reaction, at load
CONSERVATION_TOLERANCE = 1e-6   # relative atom drift over a long run
