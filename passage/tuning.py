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

# --- fixation (M6) ---------------------------------------------------------
# Fixing a mark writes it into the genome: it leaves the budget, it can never
# be lifted, it never drifts, differentiation does not clear it, and every cell
# in the lineage carries it -- including the ones that would rather not.
#
# The two costs are what stop it being a free mark. A mark has to have been
# *lived with* before it can be fixed, which is the whole idea of a heritable
# change and also stops a player fixing eight things in the first ten seconds;
# and it is paid for in biomass, out of the same pool the target is counted in,
# so fixing early costs a larger share of a smaller lineage.
FIX_AGE = 90.0               # simulated seconds a mark must be held first
FIX_COST = 45.0              # biomass, booked to the ledger as structure
FIX_MINIMUM_BIOMASS = 60.0   # below this the lineage cannot afford to fix at all

# --- the run ---------------------------------------------------------------
# A run ends because the clock does. Everything in this game that costs, costs
# *later* -- damage never heals, an old mark is the expensive one to lift, a
# lineage that burns bright is spending something it cannot get back -- and
# none of that means anything without a bell.
RUN_LENGTH = 900.0           # simulated seconds; the sim runs at real time

# --- intentions and events -------------------------------------------------
# A nudge is a direction, not a dial. What lands is somewhere between half and
# half again of what was asked for, and part of whatever was taken out comes
# back as whatever is nearest to hand.
INTENTION_LANDS = (0.5, 1.5)
INTENTION_SUBSTITUTES = (0.45, 0.95)
INTENTION_INTRODUCES = 0.35   # portions, when a nudge asks for more of nothing

EVENTS_PER_RUN = 3
EVENT_QUIET_OPENING = 150.0   # nothing happens before this: a run derailed
                              # before the player has read the page is not a run
EVENT_QUIET_ENDING = 60.0
EVENT_APART = 130.0           # they arrive one at a time

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

# Differentiation clears the inherited configuration wholesale and writes a new
# one. That is worth paying for as a single large charge rather than as the
# per-mark price of lifting each old mark by hand -- but it is still a charge,
# and it still comes out of the same eight.
DIFFERENTIATION_COST = 2.5

# --- junctions (spec 3.6) -------------------------------------------------
# Cells exchange metabolites down the concentration gradient, never against it.
# There is no routing and no logistics network: you create the gradients by
# choosing who produces what, and the junctions do the rest.
#
# Throughput is limited and *shared* -- a cell with many junctions moves less
# through each of them. That is what makes the shape of the lineage matter:
# a hub that feeds four daughters feeds each of them a quarter as well, and a
# specialist several hops from its supplier starves, because every hop is
# another gradient that has to be paid for.
JUNCTION_RATE = 9.0             # units a second through an unshared junction
JUNCTION_SHARE = 1.0            # exponent on 1/degree; 1 is a straight split

# --- death (spec open question 2, decided at M4) --------------------------
# Yes, cells can die -- but slowly and with a great deal of warning, because a
# run collapsing for a reason the player could not have fixed in time is a worse
# outcome than one that merely scores badly. The honest failure state is
# finishing with a poor score, not dying.
#
# The threshold is an *absolute* floor rather than a share of the adenylate
# pool, and deliberately low. A lean lineage of specialists runs at a very low
# charge quite happily, because upkeep saturates down as ATP falls; that is
# generous, and it is what stops a working configuration being killed for being
# frugal. Death is for a cell that has genuinely stopped, not one running thin.
DEATH_ATP = 0.15                # units of ATP, out of an adenylate pool of 50
DEATH_PATIENCE = 120.0          # seconds below it before a cell gives up
DEATH_RECOVERY = 3.0            # how much faster it recovers than it declines

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
    "ethanol": 0.0,        # listed at zero so the medium is *held* at zero:
                           # what puts ethanol in the bath is a diet, and what
                           # takes it out again is perfusion, which only runs
                           # for substances named here.
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
    "ethanol": 5.0,             # so a night out washes out again. Without a
                                # baseline here the bath stays alcoholic for
                                # the rest of the run, which it did.
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
# A pool does harm when the cell cannot be rid of what is in it. Two things
# have to be true: it must be near enough to full to have no headroom left, and
# it must be filling faster than anything is clearing it. Charging for fill
# alone -- which this did for a long time -- charges a lineage for having a
# working factory, and made doing nothing score better than playing.
CONGESTION_THRESHOLD = 0.92
CONGESTION_POWER = 3.0
JAM_FLOOR = 0.25             # what a full-but-flowing pool still costs

# Some substances are harmful by *concentration* rather than by being stuck.
# Acetaldehyde is the case the rest of the model gets wrong: it pins at its cap
# and clears exactly as fast as it arrives, so the jam rule reads it as a
# working pipeline, which it is -- a working pipeline full of poison. For these
# the fill alone is the damage, from a much lower threshold.
TOXIC_THRESHOLD = 0.30
TOXIC_DAMAGE = 1.5
# At 1.5 an unprepared lineage pays about 74 of damage for one night out and
# finishes at 76% vigour -- a real dent it cannot undo, and not a sentence.
# Trading PFK-1 for aldehyde dehydrogenase cuts that to 53 and scores better
# overall, which is the decision: you cannot keep the alcohol out, because it
# needs no transporter, but you can be equipped for it, at the price of a mark
# you would rather have spent on ordinary metabolism -- and if the run never
# brings a night out, that mark was wasted. Which is what insurance is.
JAM_TAU = 2.5                # seconds; how long a pool must stay stuck to count
EXPORT_CLEARS = 0.5          # how well flushing a substance counts against using it
CONGESTION_DAMAGE = 300.0

# How concentrated a diet makes the medium, per unit of supply rate. This is
# the number that decides whether a cell can overeat. Transport is passive, so
# the cell cannot refuse what surrounds it; set this too low and no diet can
# ever hurt anybody, because the cell simply declines to absorb what it does
# not need.
MEDIUM_RICHNESS = 11.0
# How long the margin holds a change of diet, which is also roughly how long
# the medium takes to turn over at the perfusion rates above. The number is not
# a timer on a mechanic -- nothing stops when it runs out -- it is how long the
# player is told that what they are looking at is a transition.
DIET_TURNOVER = 30.0
DAMAGE_HALF = 240.0          # accumulated damage at which vigour reads a half
UPKEEP_PENALTY = 2.6        # how much more a worn-out lineage pays just to exist

# The score weighs three things, and the third is what makes the diet axis mean
# anything. On raw output, and even on yield, a lineage living on sweets ties
# with one eating well -- it simply burns itself to get there. What separates
# them is the state they are in at the end, so vigour is a multiplier on the
# score and not a footnote to it. Relish counts too, at a smaller weight: a
# lineage that never had any pleasure did worse, and the score should say so.
SCORE_RELISH_FLOOR = 0.6     # share of the score that does not depend on pleasure

# ...and the first thing it weighs is how much was built, which for a long time
# it did not weigh at all. The score was yield times condition, so a lineage
# that produced 64 units efficiently beat one that produced 742, and refusing
# to eat beat playing. The opening line of this game is "a target you must
# hit"; a score that does not count whether you hit it is not scoring the game.
#
# Both terms saturate rather than divide, so neither can run away: doubling a
# small output matters, doubling a large one matters less, and driving intake
# towards zero no longer sends the ratio to infinity.
SCORE_TARGET = 420.0         # biomass at which the production term reads a half
SCORE_YIELD_HALF = 0.30      # yield at which the efficiency term reads a half

# --- conservation tolerances ---------------------------------------------
BALANCE_TOLERANCE = 1e-9        # atom balance, per reaction, at load
CONSERVATION_TOLERANCE = 1e-6   # relative atom drift over a long run
