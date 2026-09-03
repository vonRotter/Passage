# Passage

You are a lineage. One cell, a genome you did not choose, and a target you must
hit. You cannot build anything. You can only decide which parts of the genome
are switched on, which cells divide, and what each daughter becomes.

Everything you switch off stays off, in every cell that comes after.

---

## State: M2 — the marks gate, plus the diet axis

The player marks genes on a printed register, and the plate says in plain words
what is wrong, in what quantity, and whose fault it is. On top of that, a second
axis the build spec did not have: **glede against damage**.

```
startgame.bat                              # Windows: double-click
python -m passage                          # the plate, 1280x720
python -m passage --shot page.png          # one frame to a PNG, no display needed
python -m passage --shot ref.png --page 3  # a page of the appendix
python -m passage --headless --profile growing --ticks 50000
python -m pytest                           # 92 tests
```

`space` pauses · `tab` opens the appendix · left click activates a gene, right
click silences it, the same button again lifts it · `g` advances a generation.

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

### Glede against damage

A second scoring axis, crossing yield. Not in the original spec; added because
it is a better idea than anything the spec had for making the *choice of food*
matter beyond its entry point.

The design is anchored on something worth noticing: the first of the seven
Norwegian dietary recommendations is *"Ha et variert kosthold, velg mest mat fra
planteriket og **spis med glede**"* — eat with pleasure (Helsedirektoratet,
2024). Pleasure is inside the advice, not opposed to it. So **glede is a need**:
a lineage with none of it grows badly. The question is never whether to have
some, but what you are willing to pay.

Three parts, pulling against each other:

- **Glede** saturates. Past a point, more indulgence buys no more happiness.
- **Damage** goes as the *square* of intake above a forgiven threshold. One
  portion of something rich is nearly free; four cost sixteen times as much. It
  never heals.
- **Vigour** is what is left. A worn-out lineage pays more upkeep simply to
  exist, and builds worse — good for your mental health, and not for your RNA.

Three diets, all supplying the **same total food**, over forty-five simulated
minutes:

| Diet | Biomass | Yield | Glede | Vigour | **Score** |
|---|---|---|---|---|---|
| standard — mostly plants, some fish, a little of what you like | 999 | 0.305 | 52% | 100% | **0.246** |
| ascetic — plants and grain only | 860 | 0.265 | 35% | 100% | 0.197 |
| indulgent — sweets, processed meat, butter | 1030 | 0.304 | 75% | 24% | 0.065 |

Read the first three columns and indulgence looks fine: it produced the *most*
biomass, at the same yield, and had by far the best time doing it. It is only
when the score asks what the lineage has **left** that the bill arrives. That is
why vigour multiplies the score rather than sitting beside it — and it is the
honest shape, because on output alone the two diets genuinely tie. The sweets
lineage just burned itself down to get there.

Indulgence also wins *early* — ahead on biomass for the first half of a run —
and that is deliberate. If it were not tempting there would be no choice to
make.

The normalisation matters: without matching the total food, a result showing the
rich diet losing would only show that it was also the larger one. `foods.supply`
exists so the test can assert it.

**This is a game, not dietary advice.** The numbers are chosen to make a
metabolic toy behave the way the guidelines describe at a population level.

---

## M1 — the plate

The build spec's M1 with the art direction's A0 and A1 folded in: the ink
primitives, the hand-placed plate, one cell, animated flow, and pool washes.
No marks and no division yet — the cell runs on whatever baseline expression it
has.

```
python -m passage                          # the plate, 1280x720
python -m passage --profile fermenting     # start from a given expression set
python -m passage --shot page.png          # one frame to a PNG, no display needed
python -m passage.debug.testpage a0.png    # the A0 materials page
python -m passage --headless --ticks 50000 --trace
python -m pytest                           # 92 tests
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
  carries the glede-against-damage axis, which was the part that needed
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

Still to come, in milestone order: `bio/marks.py`, `bio/lineage.py`,
`bio/transport.py`, and audio.

---

## References

Berg, J. M., Tymoczko, J. L., Gatto, G. J., & Stryer, L. (2019). *Biochemistry*
(9th ed.). W. H. Freeman.

Hinkle, P. C. (2005). P/O ratios of mitochondrial oxidative phosphorylation.
*Biochimica et Biophysica Acta (BBA) — Bioenergetics, 1706*(1–2), 1–11.
https://doi.org/10.1016/j.bbabio.2004.09.004

Nelson, D. L., & Cox, M. M. (2021). *Lehninger principles of biochemistry*
(8th ed.). Macmillan Learning.
