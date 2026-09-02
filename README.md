# Passage

You are a lineage. One cell, a genome you did not choose, and a target you must
hit. You cannot build anything. You can only decide which parts of the genome
are switched on, which cells divide, and what each daughter becomes.

Everything you switch off stays off, in every cell that comes after.

---

## State: M1 — the plate

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
python -m pytest                           # 59 tests
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

| Profile | Biomass | Glucose used | Yield |
|---|---|---|---|
| `fermenting` | 6.0 | 590.4 | 0.010 |
| `etc_silenced` | 0.8 | 29.6 | 0.025 |
| `baseline` | 14.5 | 97.5 | 0.148 |
| `aerobic` | 17.0 | 101.1 | 0.168 |
| `tuned` | 35.3 | 106.2 | **0.333** |

A thirty-three-fold spread in yield between the best and worst configuration,
on a fixed network, with no content unlocked and nothing hidden. Fermentation
burns five and a half times the glucose for a sixth of the growth, which is the
trade a player is meant to discover rather than be told. Silencing the respiratory chain kills
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

Three bookkeeping simplifications, all documented in `data/metabolites.py`
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

### Open at M1, wanting a decision

- **The font is a placeholder.** `data/chart.ttf` is Liberation Serif, which is
  OFL-licensed and therefore safe to ship, and which is a transitional serif
  that reads as machine-set. The art direction asks for "a plain old-style
  serif or a clean grotesque — something that could plausibly be letterpress",
  and a genuine old-style face would be better. Swapping it is a one-file
  change.
- **Exchange stubs stop short of the membrane.** They were originally drawn all
  the way out through the cell envelope, which is more truthful, but the
  envelope is far from most pools and the stubs became the loudest lines on the
  page for the least information. They are now short ticked stubs. If crossing
  the membrane matters to you, the alternative is a smaller envelope that hugs
  the pool cluster more tightly.
- **The cell tint reads "energy" for every living cell.** The conserved carrier
  pairs sit at a constant total, so class fill was a constant and tinted
  everything arterial red; energy now contributes its *charge* instead, which
  varies properly. But charge is high whenever the cell is alive at all, so it
  still wins. Calibrating this is A2's job — "a player can tell a healthy cell
  from a choked one across the room" — and it wants doing there rather than
  guessed at now.
- **No audio yet.** The build spec's M1 does not ask for it; the art direction
  does. The pen scratch and the division tick have nothing to attach to until
  M2 and M3, but the continuous hum tracking throughput is the art direction's
  "most useful instrument in the game" and would be useful the moment there is
  a bottleneck to hear. Recommend building the hum at M2 with the marks, and
  the rest at their milestones.

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
