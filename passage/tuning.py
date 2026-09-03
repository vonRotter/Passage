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

# --- division and inheritance (spec 3.4) ----------------------------------
# A cell may divide once it has accumulated enough biomass, and dividing costs a
# significant part of it, so it is always a real investment rather than a free
# doubling. The pools are split, not copied: two half-stocked cells are worse at
# everything than one full one and have to grow back into it.
DIVISION_BIOMASS = 90.0         # biomass needed before a cell can divide
DIVISION_COST = 55.0            # what dividing consumes of it
DIVISION_SHARE = 0.5            # how the parent's pools are split

# A mark occasionally fails to copy. Rare, visible, and logged -- never silent,
# because a player who cannot see what changed has been cheated rather than
# challenged.
DRIFT_CHANCE = 0.035            # per mark, per division

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

# --- relish and damage (the diet axis) -------------------------------------
# Relish is a need, not a vice: a lineage that never has any builds badly. What
# the player is choosing is not whether to have some but what to pay for it.
RELISH_HALF = 0.30           # intake-weighted pleasure at which relish reads a half
RELISH_TAU = 30.0            # seconds for relish to follow what is being eaten
RELISH_FLOOR = 0.55          # anabolic capacity of a lineage with no pleasure at all

# Damage is superlinear in intake, which is the whole mechanism: one portion of
# something rich is nearly free, four portions are not. Below a food's forgiven
# intake it does no harm at all.
DAMAGE_REFERENCE = 1.0      # the intake a harm coefficient is quoted against

# Damage has a second source, and it is the one that makes a constitution
# matter: material the cell cannot process backs up, overflows, and hurts. Which
# food does that to a lineage depends on what that lineage cannot handle, so the
# right diet stops being universal. This is mechanism rather than a table of
# which foods are bad -- the spec asks for spillover to damage the cell past a
# threshold, and this is that.
SPILL_DAMAGE = 2.4          # damage per unit of material actually spilled

# The larger source, and the truer one. Harm does not wait for a pool to
# overflow: a substance that simply *sits* high, for a long time, in a cell that
# cannot clear it, is what does the damage. Overflow is only the visible end of
# it. So damage accrues on how far a pool sits above this mark, squared, which
# means a pool at nine tenths is not nine times worse than one at a tenth -- it
# is the only one that counts at all.
CONGESTION_THRESHOLD = 0.85
CONGESTION_DAMAGE = 22.0

# How concentrated a diet makes the medium, per unit of supply rate. This is
# the number that decides whether a cell can overeat. Transport is passive, so
# the cell cannot refuse what surrounds it; set this too low and no diet can
# ever hurt anybody, because the cell simply declines to absorb what it does
# not need.
MEDIUM_RICHNESS = 11.0
DAMAGE_HALF = 240.0          # accumulated damage at which vigour reads a half
UPKEEP_PENALTY = 2.6        # how much more a worn-out lineage pays just to exist

# The score weighs three things, and the third is what makes the diet axis mean
# anything. On raw output, and even on yield, a lineage living on sweets ties
# with one eating well -- it simply burns itself to get there. What separates
# them is the state they are in at the end, so vigour is a multiplier on the
# score and not a footnote to it. Relish counts too, at a smaller weight: a
# lineage that never had any pleasure did worse, and the score should say so.
SCORE_RELISH_FLOOR = 0.6     # share of the score that does not depend on pleasure

# --- conservation tolerances ---------------------------------------------
BALANCE_TOLERANCE = 1e-9        # atom balance, per reaction, at load
CONSERVATION_TOLERANCE = 1e-6   # relative atom drift over a long run
