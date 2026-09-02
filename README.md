# Passage

You are a lineage. One cell, a genome you did not choose, and a target you must
hit. You cannot build anything. You can only decide which parts of the genome
are switched on, which cells divide, and what each daughter becomes.

Everything you switch off stays off, in every cell that comes after.

---

## State: M0 — chemistry, headless

The reaction table, the network, pools, flow solving, saturation, inhibition,
and mass balance. No rendering, and deliberately no rendering code in the
import path, so the chemistry can be trusted before anything is drawn on it.

```
python -m passage                        # baseline expression, 10 000 ticks
python -m passage --profile tuned
python -m passage --profile fermenting --trace
python -m pytest                         # 42 tests
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

### Open, wanting a decision

- **Glutamate is present in the base medium at a low concentration.** Real
  culture media carry amino acids, and biosynthesis needs a nitrogen source
  from tick one. This is not the same as *adopting* amino acids as a fuel
  (§3.8), which still requires committing marks to `aat` and `gdh`. Flagged
  because it touches the diet-expansion design.
- **Product inhibition uses the fullest product pool.** For a linear pathway
  this is right. For a cycle it is what caused decision 4, and it means cycle
  intermediates need generous caps or they gridlock. An alternative — driving
  cycle flux from the NADH/NAD+ ratio and adenylate charge, as real cells do —
  would be more defensible and more work. Recommend revisiting at M2, when
  bottleneck explanations have to name a cause in plain words and this one
  would have to be explained as "2-oxoglutarate is full", which is true but
  not illuminating.
- **The reaction count sits at the low end.** Twenty-four solver rows against
  the spec's "roughly 22". Spec open question 4 asks for 16 and 28 to be tested
  at M2; the compile step is already agnostic about the count.

---

## Layout

```
passage/
  __main__.py       M0: the headless runner. Becomes the window at M1.
  tuning.py         every constant
  data/             the biology, as plain tables
    metabolites.py  the substance list, with atom counts and classes
    reactions.py    the reaction table
    genes.py        genes and the enzymes they encode
  bio/
    network.py      compiles data/ into matrices; refuses to build unbalanced
    flow.py         the solver — vectorised, no Python loop over reactions
    cell.py         a named view onto one row of the arrays
tests/
```

Still to come, in milestone order: `bio/marks.py`, `bio/lineage.py`,
`bio/transport.py`, `render/`, `debug/`.

---

## References

Berg, J. M., Tymoczko, J. L., Gatto, G. J., & Stryer, L. (2019). *Biochemistry*
(9th ed.). W. H. Freeman.

Hinkle, P. C. (2005). P/O ratios of mitochondrial oxidative phosphorylation.
*Biochimica et Biophysica Acta (BBA) — Bioenergetics, 1706*(1–2), 1–11.
https://doi.org/10.1016/j.bbabio.2004.09.004

Nelson, D. L., & Cox, M. M. (2021). *Lehninger principles of biochemistry*
(8th ed.). Macmillan Learning.
