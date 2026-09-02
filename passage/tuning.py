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
    "glucose": 25.0,
    "o2": 30.0,
    "co2": 0.0,
    "lactate": 0.0,
    "ammonia": 0.0,
    "palmitate": 0.0,
    "glutamate": 3.0,      # culture media carry amino acids; adopting them as
                           # a fuel is a different matter entirely (spec 3.8)
}
MEDIUM_FEED = {                 # units per second, the ceiling on perfusion
    "glucose": 1.6,             # the binding supply constraint
    "o2": 60.0,
    "co2": 60.0,
    "lactate": 3.0,
    "ammonia": 3.0,
    "palmitate": 0.6,
    "glutamate": 0.6,
}
MEDIUM_START = {
    "glucose": 25.0,
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

# --- conservation tolerances ---------------------------------------------
BALANCE_TOLERANCE = 1e-9        # atom balance, per reaction, at load
CONSERVATION_TOLERANCE = 1e-6   # relative atom drift over a long run
