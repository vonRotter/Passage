# Passage

You are a lineage. One cell, a genome you did not choose, and a target you must
hit. You cannot build anything. You can only decide which parts of the genome
are switched on, which cells divide, and what each daughter becomes.

Everything you switch off stays off, in every cell that comes after.

---

## State: M4 — specialists and transport

The player marks genes on a printed register, and the plate says in plain words
what is wrong, in what quantity, and whose fault it is. On top of that, a second
axis the build spec did not have: **relish against damage**.

```
startgame.bat                              # Windows: double-click
python -m passage                          # the plate, 1280x720
python -m passage --shot page.png --grow   # one frame to a PNG, no display needed
python -m passage --shot ref.png --page 3  # a page of the appendix
python -m passage --headless --profile growing --ticks 50000
python -m pytest                           # 130 tests
```

`space` pauses · `tab` opens the appendix (six pages) · `d` divides the selected
cell · `shift`+`1`–`5` pushes it into a specialism · `1`–`9` or a click on the
tree selects one · left click activates a gene, right
click silences it, the same button again lifts it · `g` advances a generation.

### Inheritance

A daughter does not start from a fresh page. She starts from her parent's page,
in an older hand: every mark copied, each one remembering the generation it was
originally placed in, each drawn one step fainter for every generation of
inheritance it has travelled. What the player chose and what they were handed
are different things on the register, and stay different.

Three things make dividing a decision rather than a doubling:

- **Pools are split, not copied.** Two half-stocked cells are worse at
  everything than the one they came from, and have to grow back into it.
- **It costs.** A large part of the accumulated biomass is spent becoming two
  cells — booked to the ledger as structure, so the atoms are not destroyed and
  the conservation sum still closes.
- **The configuration comes too.** Dividing a badly-set cell makes two badly-set
  cells, and the budget is spent twice over.

Copying is not perfect. A mark occasionally fails to come across — rare, logged,
and never silent, because a player who cannot see what changed has been cheated
rather than challenged. A fixed mark never drifts.

The tree is hand-ruled in the left margin in **pencil** rather than ink, because
it is a record the player is keeping rather than part of the printed plate. Each
cell is a small circle carrying its own colour, so the shape of the lineage and
the health of it are one glance rather than two. It compresses as the lineage
grows; a tree that ran off the page would be a worse record than a cramped one.

The milestone's acceptance — *the player is visibly reluctant to divide a badly
configured cell* — is a claim about a person and cannot be self-assessed. What
can be, and is: the problem really is copied, copying really does cost, and the
difference between chosen and inherited is on the page.

### Junctions, and why specialists are hard

Cells exchange metabolites through junctions, and a junction does exactly one
thing: it lets a substance move **down its concentration gradient**, at a
limited rate, never the other way. There is no routing, no logistics network,
and nothing to lay out. You create the gradients by choosing who produces what.

Junctions form between a parent and its daughter and nowhere else, so **the
shape of the lineage is the transport network**. Two properties do the rest:

- **Throughput is shared.** A cell with four junctions moves a quarter as much
  through each, so a hub that feeds four daughters feeds each of them badly.
- **Every hop costs**, because each one needs its own gradient to drive it.

Nothing declares that a distant specialist starves. It falls out of those two
facts. One feeder at the head of a chain of burners, after fifteen simulated
minutes:

| hops from the feeder | lactate | respiration | biomass |
|---|---|---|---|
| 1 | 3.96 | 1.24 | 315 |
| 2 | 2.11 | 1.00 | 291 |
| 3 | 1.37 | 0.63 | 265 |
| 4 | 1.09 | 0.63 | 264 |

And the plate says so in words, which is what makes the milestone's acceptance
reachable — *the player works out that the specialist is too many hops from its
supplier*:

> **← pyruvate → lactate is starved of lactate**
> the cell holds 1.28 of lactate and wants about 45.0 to run freely — 20% of
> the way there.
> *Cell 0 has 29.9 of lactate, 4 junctions away. Every hop needs its own
> gradient to drive it, so most of it never arrives. Put a supplier closer, or
> stop this cell needing one.*

**The conserved carriers do not travel.** A cell that could be handed ATP by a
neighbour would never need to make any, specialisation would cost nothing, and
the trade the design rests on would evaporate. Every specialist keeps its own
energy books. Palmitate does not cross either — a lipid specialist takes its own
fat in.

The pairing worth noticing is the feeder and the burner: one runs glycolysis
hard and pours out lactate, the other takes lactate in and oxidises it. One
cell's waste is the next one's fuel, and it is the only way carbon moves between
members of a lineage.

### Death

The spec left this open to be decided here, and the answer is yes — **slowly,
and with a great deal of warning**. A run collapsing for a reason the player
could not have fixed in time is a worse outcome than one that merely scores
badly; the honest failure state is finishing poorly, not dying.

A cell that has genuinely stopped — no ATP at all — announces it and counts down
for two minutes before it gives up. Recovery is three times faster than decline,
so a dip is not a sentence. What it held goes back to the medium, atom for atom.

The threshold is an *absolute* floor rather than a share of the adenylate pool,
and that matters: a lean lineage of specialists runs at a very low charge quite
happily, because upkeep saturates down as ATP falls. Culling those cells for
being frugal would make specialisation unplayable. It is a generous reading, and
it is deliberate.

### Being technical and still readable

The game's answer to "tell me what to do, in real terms, and let me look it up"
is two things.

**It diagnoses, in plain words, with numbers, and names who is to blame.** Every
reason carries four parts: what is wrong, the quantities named, what to do about
it, and — when the trail leads to a mark — the generation that mark was placed
in. For example, live from a run:

> **G3P → pyruvate is short of ADP**
> ADP and ATP are one closed pool: 0.58 against 49.4, so 99% of it is sitting as
> ATP. ADP is not made — it is what is left when ATP gets spent, and nothing
> here is spending it.
> *glucose → 2 G3P is what clears it, and PFK-1 is at 15%. Activating PFK-1
> would clear it, but all eight marks are placed. Something has to come off
> first, and lifting costs more than placing did — the oldest is glucose
> transporter, from generation 1.*

Two rules make that work. A player cannot pour anything into a cell, so a
shortage is **never** reported as a shortage — it is reported as the gene that
would fix it. And advice a player cannot act on is worse than none, so the note
changes mood when the budget is full.

**And there is somewhere to read it.** `tab` opens a four-page appendix, bound
into the same plate: every substance with its formula, capacity, and what makes
and uses it; every reaction with its full balanced stoichiometry, its gene, and
its capacity; every gene with what it encodes and what marking it would change;
and the diet. It is generated from the tables in `data/`, so it cannot drift
away from the game it describes.

`tests/test_traceability.py` takes each claim apart and holds it against the
arrays the solver used — the named metabolite really is the scarcest of that
reaction's inputs, the named product really is the fullest, the generation
matches the mark, and the amount named as wanted comes from the same saturation
curve the solver integrates.

### Relish against damage

A second scoring axis, crossing yield. **Relish** is the pleasure of eating, and
it is a *need* rather than a vice: a lineage that never has any builds badly, so
the question is never whether to have some but what you are willing to pay.

- **Relish** saturates. Past a point, more indulgence buys no more happiness.
- **Damage** has two sources. Rich food, going as the *square* of intake above a
  forgiven threshold — one portion is nearly free, four cost sixteen times as
  much. And **congestion**: a substance that simply sits high in a cell with no
  way to clear it. The second is the larger, and it is what makes a constitution
  matter.
- **Vigour** is what is left. A worn-out lineage pays triple upkeep just to
  exist and builds at forty per cent — which is how "you die earlier" is
  expressed in a game with no lifespan counter. Damage never heals.

Three diets at matched supply, over forty-five simulated minutes:

| Diet | Biomass | Yield | Relish | Vigour | **Score** |
|---|---|---|---|---|---|
| varied | 999 | 0.305 | 52% | 100% | **0.246** |
| plain | 860 | 0.265 | 35% | 100% | 0.197 |
| rich | 1030 | 0.304 | 75% | 24% | 0.065 |

Read the first three columns and the rich diet looks fine: it produced the
*most* biomass, at the same yield, and had the best time doing it. The bill only
arrives when the score asks what the lineage has **left**. That is why vigour
multiplies the score rather than sitting beside it — on output alone the two
genuinely tie, and the rich lineage simply burned itself down to get there. It
also leads for the first half of a run, deliberately: if it were not tempting
there would be no choice to make.

### The constitution — a genome you did not choose

Every run deals the lineage a **constitution**: fixed traits that change how the
same plate behaves. An enzyme with less capacity than the chart shows. A pool
that holds less before it congests. A food this body cannot take up. None of it
can be marked away — marks decide what is switched on, a constitution decides
what switching it on is *worth* — and a bottleneck that traces to one says so
plainly, because a player spending marks on a constitutional limit is losing
budget to something that was never going to move.

What it does to the game is turn diet from a preference into a diagnosis. **The
same meal nourishes one lineage and poisons another**, because a body is not
harmed by what it eats so much as by what it cannot clear. Score by
constitution and diet, forty-five simulated minutes, best in bold:

| | standard | low sugar | low fat | low protein | creamy | sparse | plain | rich |
|---|---|---|---|---|---|---|---|---|
| even | 0.215 | 0.217 | 0.164 | 0.220 | **0.225** | 0.201 | 0.154 | 0.066 |
| poor sugar handling | 0.171 | **0.216** | 0.057 | 0.131 | 0.175 | 0.197 | 0.104 | 0.040 |
| poor fat handling | **0.182** | 0.059 | 0.162 | 0.065 | 0.173 | 0.173 | 0.152 | 0.042 |
| reduced respiration | 0.195 | 0.188 | 0.167 | 0.193 | **0.202** | 0.184 | 0.154 | 0.062 |
| poor nitrogen clearance | 0.147 | 0.143 | 0.090 | **0.173** | 0.155 | 0.138 | 0.076 | 0.052 |
| no milk tolerance | **0.239** | 0.220 | 0.166 | 0.223 | 0.079 | 0.213 | 0.156 | 0.068 |
| thrifty | 0.206 | **0.223** | 0.167 | 0.203 | 0.214 | 0.204 | 0.157 | 0.063 |

Five of the six traits pick a different meal than an even constitution does, and
the mismatches are brutal: a fat-averse lineage on the fat-bearing diet scores
0.059 where an even one scores 0.217, and a milk-intolerant one on the dairy diet
scores 0.079 against its own best of 0.239. Reduced respiration is the
exception, and honestly so — it is a trait of *degree*, not of direction. It
makes everything worse without changing what to eat, which is a real kind of
trait to have.

Nothing is hidden. Every constitution is printed in the appendix and the one
this lineage holds is ticked, with what to do about it written underneath.
Knowing which you have is the easy half.

**On why more food does not buy more growth.** It looks like a bug and it is
not. The cell is **enzyme-limited**, not supply-limited: twenty times the food
moves biomass by forty per cent, because what a lineage can process is set by
the eight marks it has to spend. That is the design working — *marks are the
scarce resource, and you cannot run everything.* It also means a healthy cell
**cannot overeat**: transport is passive, so once its pools are full the
gradient closes and it stops absorbing. The cell that *can* overeat is the one
whose constitution stops a pool ever coming down. A body that regulates its
intake against one that cannot — that asymmetry is the whole diet axis.

Milk intolerance used to be the weakest trait, for a related reason: absorbing
less of one food barely matters to a lineage that was enzyme-limited anyway. It
now has a mechanism instead of a penalty — the milk sugar it cannot digest is
fermented on the way in and **arrives as acid**, into a lineage with less room
than most to hold it. A dairy-led diet congests it, and the trait went from the
quietest in the game to one of the sharpest.

---

## M1 — the plate

The build spec's M1 with the art direction's A0 and A1 folded in: the ink
primitives, the hand-placed plate, one cell, animated flow, and pool washes.
No marks and no division yet — the cell runs on whatever baseline expression it
has.

```
python -m passage                          # the plate, 1280x720
python -m passage --profile fermenting     # start from a given expression set
python -m passage --shot page.png --grow   # one frame to a PNG, no display needed
python -m passage.debug.testpage a0.png    # the A0 materials page
python -m passage --headless --ticks 50000 --trace
python -m pytest                           # 130 tests
```

`--shot` exists because the art direction cannot be checked without looking at
it, and the machine this was built on has no screen.

### What is drawn

Paper is layered numpy noise — coarse fibre, fine grain, edge darkening, and a
handful of foxing stains placed per seed. Lines are subdivided, jittered
perpendicular, and stroked two or three times at varied offset, which is what
separates a nib from a vector. Washes are a blurred, noise-modulated alpha mask
with pigment pooling at the rim, low-frequency blotching, and a ragged edge,
laid down a pixel or two out of register with the linework. That last part is
deliberate and is most of what sells the style; it is not a tolerance to be
tightened.

Jitter is seeded from a thing's identity, never from time — and never from
`hash()`, which Python randomises per process and which would have re-inked the
plate differently on every launch.

### The chart, and why it is drawn the way it is

The first version of this page was a node graph in period costume: circles for
substances, arrows between them, one line weight throughout, and a column of
boxes off to the side holding ATP, ADP, NAD+ and NADH. It rendered correctly
and it read as a flow diagram, which is to say it read as a diagram of
anything. Real biochemical charts do five things it was not doing, and each of
them is information rather than decoration.

**Cofactors ride the arrow.** There is no ATP node in a biochemical drawing.
ATP appears on a curved arrow crossing the reaction that spends it, coming in
on one side and leaving as ADP on the other. That single convention is most of
what makes a page read as chemistry — it says *this step costs energy* at the
step, rather than requiring the reader to trace a line to a box. Giving ATP a
box of its own was the single largest thing making the page generic. The
carriers are now read as ruled instruments in the right margin, where a stock
reading belongs, and the plate draws them where they act.

**Compartments are real.** Half of central metabolism happens inside the
mitochondrion and half does not, and a substance crossing that line is doing
something a substance moving within a compartment is not. The mitochondrion is
drawn with a double line, because it is a double membrane, and pyruvate's
arrow visibly crosses it.

**A cycle is drawn as a cycle.** The citric acid cycle drawn as two straight
arrows is not recognisable as one. It is a ring inside the compartment, with a
stroke leaving oxaloacetate, passing the acetyl group it condenses with, and
sweeping over the top.

**Machinery is not a step.** The respiratory chain is not a station on a
pathway; it is machinery sunk through the membrane. It is a short heavy bar
crossing the membrane, with oxygen joining it from outside on a light limb —
first drawn as an arc *along* the membrane, where it was simply lost against
the membrane's own line.

**Weight carries hierarchy.** The trunk is heavy, the branches lighter, the
side reactions lighter still, and every arrow has a head, because direction is
information. Drawing every line at one weight is most of the rest of what makes
a diagram look machine-made.

Two things were tried and taken back out. Enzyme names on the vessels are the
right convention on a poster and unreadable at 1280x720 — they collided with
the metabolite names, the cofactor labels and each other, so they live in the
gene register along the bottom, which is where the player marks them anyway.
And cofactor arcs on all fifteen reactions turned the page into soup; seven
carry one, and they are the seven that define the shape of the thing.

### The same chart, a different body

The chart's shape is fixed, and has to be: the player is meant to learn this
page permanently, and a layout that shifts between runs destroys that. So the
variation is not in where anything sits — it is in the inking.

A step this lineage runs below standard, whether from a weak enzyme or from
poor affinity for its substrate, is printed thinner and **broken**. A run with
poor sugar handling has a dashed hairline where glycolysis should be heavy; a
run with reduced respiratory capacity has it at the chain. The constitution
cannot be marked away, so it is on the page from the first second rather than
in a footnote, and the appendix prints the two line weights side by side so the
mark is named rather than guessed at.

The mark is a gap in the line, not a stroke across it, because the flow
animation already draws strokes across vessels and two marks that mean
different things must not share a shape.

### Performance

| | |
|---|---|
| Frame | 4.1 ms, including the 20 Hz chemistry — budget 16.6 ms |
| Plate inkings | 1, over any number of frames |
| Washes rebuilt | only when a pool level crosses a bucket |

The plate — paper, vessels, pool outlines, printed labels, gene register — is
inked once and blitted. Pool washes, the cell tint, the roster blob and the
saturated-pool outlines are all cached and rebuilt only when their state
actually changes. `tests/test_render.py` asserts this rather than trusting it:
an early version re-inked the roster every frame and cost 2.9 ms doing it.

### M1 acceptance — **needs your eyes**

> *A viewer can watch the chart and correctly say which reaction is the
> bottleneck, without any highlighting to help them.*

This one cannot be self-assessed. It is a claim about a person watching motion,
and this was built on a headless box against still frames. What the plate now
does is put two cues on every vessel — mark **density** and mark **speed**, both
scaling with rate — so a slow vessel is sparse *and* crawling, and a stopped one
is bare and still. Saturated pools thicken their outline and fill with their
class wash. Please run it and say whether the bottleneck is findable; if it is
not, that gets fixed before anything is built on top.

What is tested, rather than eyeballed: a stalled vessel carries no marks, a
busier vessel carries more than a quieter one, density is compressed rather
than linear (rates on the plate span two orders of magnitude), the same state
drawn twice gives identical pixels, and the plate is inked exactly once.

---

## M0 — chemistry, headless

The reaction table, the network, pools, flow solving, saturation, inhibition,
and mass balance. No rendering, and deliberately no rendering code in the
import path, so the chemistry can be trusted before anything is drawn on it.

```
python -m passage --headless                       # baseline, 10 000 ticks
python -m passage --headless --profile tuned
python -m passage --headless --profile fermenting --trace
```

`--profile` selects a hand-written expression set. These are not the game — the
game is the player choosing them with marks, which is M2. They exist so that
M0 can be inspected without a mark system.

### M0 acceptance

| Requirement | Result |
|---|---|
| Mass balances to floating-point tolerance | atom residual `4.5e-10` after 100 000 ticks, against ~2000 atoms held |
| Backpressure propagates upstream, in order | `tests/test_backpressure.py`, 5 tests |
| Numbers behave like a chemistry | see below |
| Performance | 0.35 ms/tick at 20 cells, budget 5 ms |

Marks matter, and the trade the design is built on is already visible in the
numbers. Biomass produced per unit of glucose supplied, 500 simulated seconds,
one cell:

**These numbers were superseded at M2.** The profiles they were measured on
marked twelve genes against a budget of eight, so they were configurations no
player could reach, and the chemistry they were measured against had a flaw that
M2 found: with upkeep as cheap as it was, the cell had no reason to make ATP and
eight marks bought a one per cent improvement. The current figures are in the M2
section. Kept here because the M0 acceptance was judged against them.

| Profile | Yield |
|---|---|
| `fermenting` | 0.010 |
| `etc_silenced` | 0.025 |
| `baseline` | 0.148 |
| `aerobic` | 0.168 |
| `tuned` | **0.333** |

Silencing the respiratory chain kills
the cell outright: NAD+ is fully reduced within a minute and every step that
needs it stops.

---

## The chemistry

Seventeen pooled metabolites and two buffered ones, fifteen internal reactions
(seventeen solver rows, counting the two reversibles as two directions each)
and seven exchange rows: twenty-four rows in all. Central metabolism,
simplified — glycolysis, gluconeogenesis, fermentation, the citric acid cycle,
beta-oxidation, lipogenesis, nitrogen handling, respiration, and one lumped
anabolic condensation that makes biomass.

Stoichiometry follows standard treatments of central metabolism (Berg et al.,
2019; Nelson & Cox, 2021). The respiratory chain uses a P/O ratio of 2.5 per
NADH, the consensus measured value rather than the older integer figure
(Hinkle, 2005).

Four bookkeeping simplifications, all documented in `data/metabolites.py`
rather than buried in the solver:

- **Acetyl-CoA** is carried as its acetyl moiety, hydrated to acetate. CoA is
  implicit and, being conserved wherever it appears, never affects the balance.
- **NADH is NAD+ plus two hydrogens** — the textbook `2[H]` reducing-equivalent
  notation, which bundles NADH with the proton released alongside it. FADH2 is
  folded into the same carrier.
- **Water and inorganic phosphate are buffered**: chemically real, present in
  every reaction that needs them so that balance holds exactly, never limiting,
  and never drawn on the plate. Their net flux is metered so that atom
  conservation is still checked end to end.
- **The conserved carriers do not product-inhibit.** ATP and ADP are one closed
  pool, and a reaction that makes ATP is already throttled by ADP running short
  on its own substrate side. Charging it again for the ATP piling up counts the
  energy charge twice, and the doubled grip held the whole plate in a low-flux
  equilibrium that no mark could lift. This one is a correction, not a
  convenience.

Everything else uses real formulae, and every reaction balances on a genuine
atom count. That is enforced at load and by test, and the network refuses to
build otherwise.

### The rate law

```
rate = base_rate × enzyme_level × saturation(inputs) × (1 − inhibition(outputs))
```

`saturation` is a product of Michaelis-Menten terms over the distinct input
metabolites — a curve, not a cliff. `inhibition` is driven by how full the
reaction's own product pools are, and it is what carries backpressure upstream.

Enzyme level lags expression by seconds, and expression lags its target. Nothing
in this game responds instantly.

### The medium

The medium is perfused rather than fed: held toward a target concentration in
both directions at a bounded rate. Glucose is the binding supply constraint;
waste is carried off but metered, so a player is still charged for what they
dumped. Exchange between a cell and the medium is passive and bidirectional —
net flux follows the gradient and never runs against it. There is no routing
and no pumping, which is the design's whole answer to logistics.

---

## Decisions taken at M0, for review

The build spec (§7) flags the reaction and metabolite selection as the M0
literature question. Five decisions were taken; each is reversible.

1. **Seventeen pooled metabolites, not fourteen.** Oxaloacetate and
   2-oxoglutarate were added so the citric acid cycle is two visible arcs
   rather than one opaque lump, and so glutamate has a real entry point
   (glutamate dehydrogenase, at 2-oxoglutarate) instead of an invented one.
   Biomass was added as the seventeenth — see 3.
2. **Water and phosphate are buffered rather than counted.** Strict balance
   needs them; the plate does not. Counting them among the fourteen would have
   spent two slots the player never reads.
3. **Biomass and one anabolic reaction were added.** Without a sink for ATP,
   the cell's energy charge pins at maximum, product inhibition throttles every
   ATP-producing step, and expression changes stop mattering — the chemistry
   goes quiet for a reason that is an artefact, not a design. The spec already
   requires biomass for division (§3.4); pulling it forward to M0 is what makes
   the flow numbers respond to marks at all.
4. **Cataplerosis was added** (oxaloacetate → pyruvate, the PEPCK route).
   Without an outlet, the cycle deadlocks: each intermediate is the next step's
   substrate, so product inhibition on a cyclic pool jams it solid. This is a
   real property of the rate law, not a tuning accident, and it is worth
   knowing about before the plate is drawn.
5. **Exchange is one bidirectional row per metabolite, not an uptake row and an
   export row.** Two rows on one gene spin a futile cycle: at steady state the
   cell was importing and exporting lactate simultaneously at comparable rates.
   A gradient-driven net flux is both correct and cheaper.

### Settled since M1

- **The font** is now Vollkorn (OFL) — an old-style face with warmth and some
  quirk, and it holds at the nine and ten pixel sizes most of this interface
  lives at, which EB Garamond did not.
- **Exchange stubs stay short**, as decided.
- **The cell tint** is now a *blend* of the class washes rather than a winner,
  weighted so that waste shouts and gases whisper, with energy contributing its
  charge. A working cell reads red-ochre, a choked one olive, a dead one pale
  and drained. Whether that is enough for A2's "across the room" test is still
  a question for eyes rather than for me.
- **Audio** is built: a continuous hum whose pitch follows throughput, a pen
  scratch on placing a mark, a wet tick, and a sour tone for spillover. Loops
  are cycle-aligned and their noise is synthesised in the frequency domain, so
  they repeat without a click. No audio device means no audio and no error.

### Open, wanting a decision

- **Dosing is not a verb, and I did not make it one.** "Add three parts of X"
  implies pouring something into a cell, which would be a fifth verb, and the
  spec forbids that in as many words. What is built instead is the diagnosis:
  the game tells you what is short, by how much, and which gene would fix it.
  If you want dosing to be a real action — supplementing the medium mid-run —
  say so and I will put the case for and against properly, but I am not going
  to add it quietly.
- **The diet is fixed for now.** Choosing what to eat is §3.8's adoption
  mechanic and lands at M5. The three diets exist as data and as a test; the
  player cannot yet switch between them in a run.
- **Every food enters through one of four existing gates.** The distinct entry
  points the design turns on — fibre fermented to short-chain fatty acids
  arriving at acetyl-CoA, fructose slipping past the regulation point, ethanol
  with its toxic intermediate — are what M5 is for. What is here already
  carries the relish-against-damage axis, which was the part that needed
  proving.
- **Cells cannot die yet.** A worn-out lineage pays triple upkeep and builds at
  40%, but nothing kills it. Spec open question 2 recommends death, slow and
  heavily telegraphed, and defers the decision to M4.

### Open from M0, still standing

- **Glutamate is present in the base medium at a low concentration.** Kept.
  Real culture media carry amino acids, and biosynthesis needs a nitrogen
  source from tick one. This is not the same as *adopting* amino acids as a
  fuel (§3.8), which still requires committing marks to `aat` and `gdh`.
- **Product inhibition uses the fullest product pool.** Confirmed to stand
  until M2, when bottleneck explanations have to name a cause in plain words
  and this one would have to be explained as "2-oxoglutarate is full" — true,
  but not illuminating. The alternative, driving cycle flux from the NADH/NAD+
  ratio and adenylate charge as real cells do, is more defensible and more
  work.
- **The reaction count sits at the low end.** Twenty-four solver rows against
  the spec's "roughly 22". Spec open question 4 asks for 16 and 28 to be tested
  at M2; the compile step is already agnostic about the count.

---

## Layout

```
passage/
  __main__.py       window, loop, pause, time control; --headless and --shot
  tuning.py         every constant
  data/             the biology, as plain tables
    metabolites.py  the substance list, with atom counts and classes
    reactions.py    the reaction table
    genes.py        genes and the enzymes they encode
    layout.py       the plate, placed by hand, once
    chart.ttf       Liberation Serif, OFL — a placeholder, see below
  bio/
    network.py      compiles data/ into matrices; refuses to build unbalanced
    flow.py         the solver — vectorised, no Python loop over reactions
    cell.py         a named view onto one row of the arrays
    marks.py        the mark system: cost, persistence, and the price of change
    diagnose.py     why a reaction is slow, in plain words, with numbers
    lineage.py      division, inheritance, drift, death, and the tree
    transport.py    junctions: gradients, shared throughput, and distance
    vigour.py       relish, damage, and what the lineage carries
  render/
    ink.py          the six primitives: paper, line, curve, wash, leader, hand
    palette.py      the six class washes and the one alarm colour
    type.py         one face, machine-set; the hand is drawn, never typed
    plate.py        the printed page, inked once and cached
    flow_vis.py     pool washes, cell tint, the flow animation
    roster.py       the left margin
    panel.py        the right margin
  debug/
    overlay.py      F-keys: rates, mass balance, timing
    testpage.py     the A0 materials page
tests/
```

Two departures from the layout in the build spec: `render/chart.py` is
`render/plate.py`, because the art direction supersedes §3.12 and the thing is
a plate rather than a wall chart; and `render/panel.py` was added, because the
spec puts the target and rates on the right but named no module for them.

    data/foods.py, data/constitutions.py — the diet and the genome dealt

Still to come, in milestone order: diet adoption (M5) and fixation (M6).

---

## References

Berg, J. M., Tymoczko, J. L., Gatto, G. J., & Stryer, L. (2019). *Biochemistry*
(9th ed.). W. H. Freeman.

Hinkle, P. C. (2005). P/O ratios of mitochondrial oxidative phosphorylation.
*Biochimica et Biophysica Acta (BBA) — Bioenergetics, 1706*(1–2), 1–11.
https://doi.org/10.1016/j.bbabio.2004.09.004

Nelson, D. L., & Cox, M. M. (2021). *Lehninger principles of biochemistry*
(8th ed.). Macmillan Learning.
