# Passage

You are a lineage. One cell, a genome you did not choose, and a target you must
hit. You cannot build anything. You can only decide which parts of the genome
are switched on, which cells divide, and what each daughter becomes.

Everything you switch off stays off, in every cell that comes after.

---

## State: M6 — finished

The player marks genes on a printed register, and the plate says in plain words
what is wrong, in what quantity, and whose fault it is. On top of that, a second
axis the build spec did not have: **relish against damage**. The register is a
standing decision rather than a puzzle solved once — **you choose what to eat,
and choosing again invalidates what you configured** — and the run now ends,
with an account of itself.

All seven milestones are built. What follows is what each one turned out to be.

```
startgame.bat                              # Windows: double-click
python -m passage                          # the plate, 1280x720
python -m passage --shot page.png --grow   # one frame to a PNG, no display needed
python -m passage --shot ref.png --page 3  # a page of the appendix
python -m passage --eat "low sugar"        # start on a diet other than the default
python -m passage --shot end.png --reckoning --grow --ticks 18000
python -m passage --headless --profile growing --ticks 50000
python -m pytest                           # 193 tests
```

`space` pauses · `tab` opens the appendix (eight pages; on the kitchen page
`1`–`8` picks a diet outright and `a`–`h` asks for a change) · `d` divides the
selected cell · `shift`+`1`–`5` pushes it into a specialism · `1`–`9` or a click on the
tree selects one · left click activates a gene, right
click silences it, the same button again lifts it · **ctrl-click writes it into
the genome, for good** · `g` advances a generation. A run is fifteen minutes.

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

### Doing nothing used to beat playing

The worst thing found in this project, and it had been there from the start.

Searching for the best eight marks under several bodies and diets turned up
optima that were mostly *silencings* — shut the transporters, eat almost
nothing, build a little. Measured over a full run on the standard diet:

| plan | built | eaten | yield | vigour | score |
|---|---|---|---|---|---|
| greedy optimum | 199 | 347 | 0.573 | 39% | 0.141 |
| greedy optimum (2) | **64** | 136 | 0.468 | 50% | **0.143** |
| a normal respiring build | **437** | 1436 | 0.304 | 19% | **0.041** |
| nothing at all — no marks | 158 | 855 | 0.185 | 75% | 0.104 |

The lineage that built 64 scored better than the one that built 437, and doing
nothing at all beat a configured cell by two and a half times. A game whose
optimum is not to play it is mis-scored.

**Two faults, both real, and neither was the one I first suspected.**

*Congestion damage was charged on pool fill.* The comment above it had always
said the right thing — "a substance that sits high, **for a long time**, in a
cell **with no way to get rid of it**" — and the code measured only the first
clause. A full pool is what a working pipeline looks like, so the busier a
lineage was the more it paid: the respiring build jammed seven pools and lost
four fifths of its vigour while an unconfigured cell sat comfortable. It now
takes all three clauses: near enough to full to have no headroom, filling
faster than anything clears it, and doing so for long enough to count. The same
build now keeps 93% of its vigour and builds 742 instead of 437.

*The score had no production term.* It was yield times condition — and with
intake in the denominator and nothing counting output, the way to win was to
eat as little as possible. The opening line of this game is "a target you must
hit"; a score that never asks whether you hit it is not scoring the game. There
are now four bounded factors multiplied together — how much was built, how
cheaply, in what state, and whether the living was worth doing — and neither the
production nor the efficiency term can run away, because both saturate rather
than divide.

With both fixed, the configured build scores 0.244 against 0.082 for doing
nothing, and the starve builds come last.

### Giving the constitutions their teeth back

Correcting the congestion fault took away the only mechanism most of the traits
had, and six of the seven ended up wanting the same dinner. The fix was the one
the corrected score makes available: **a trait costs you production, and the
score now counts production.** No damage needed.

Two things had to be understood first, and both were wrong in my head.

**The capacity numbers were not binding.** Base rates on this plate sit far
above what a cell actually draws, so a multiplier only does anything once it
cuts *below* the flux the step is carrying. The respiratory chain runs at about
2.0/s and could do 15.0, so "reduced respiratory capacity" at 0.42 left a
ceiling seven times the demand and changed nothing. Measured, per trait, the
binding points:

| trait | was | flux it carries | now | production on its bad diet |
|---|---|---|---|---|
| poor sugar handling | 0.60 | 0.8 of 9.0/s | **0.06** | 0.46 of an even lineage |
| reduced respiration | 0.42 | 2.0 of 15.0/s | **0.15** | 0.54 |
| poor fat handling | 0.20 | — | 0.20 | 0.31 |
| poor nitrogen handling | — | — | affinity **5.0** | 0.75 |

The numbers look drastic and are not: 0.06 of 9.0/s is still 0.54/s against a
demand of about 0.8. They only look small because the ceilings were so far
above the floor.

**Reduced respiration was undoing itself.** It cut the chain's capacity while
*raising* the idle expression of the same gene, from a standard 0.30 to 0.45.
For any player who marks the respiratory chain the baseline never applied at
all, and for one who does not the two halves cancelled. The override is gone.

**Two traits needed restating rather than retuning.** "Poor nitrogen clearance"
was: deaminate readily, export badly, choke on your own ammonia. It has no
teeth and cannot have any, because ammonia's pool is small, so it fills, product
inhibition stops the enzyme, and the cell simply stops deaminating — which costs
it nothing, since it was not gaining from that route in the first place. A trait
whose whole cost is "you may not use a route you did not need" is not a trait.
It is now poor nitrogen *handling*: this body needs far more amino acid about
before it will build at any speed, which starves it on a protein-thin diet and
leaves it fine on a protein-rich one. That is the opposite preference from what
its old counsel advised, and the old counsel was describing a mechanism that
never worked. ("No milk tolerance" was restated for a similar reason, above.)

**And the measurement itself was wrong.** The matrix held one generic mark set
fixed across every body and every diet. That asks "which diet suits this body
given somebody else's configuration", and the game's question is "which diet
suits this body, played properly". A trait that ruins fat-burning is invisible
to a configuration that never burns fat — and the generic one never did, running
beta-oxidation at 0.02/s. Every figure below is the best of several
diet-appropriate configurations.

One confound fell out of that too: **creamy was simply the biggest dinner.** It
had drifted eight per cent above the other diets, which is most of why everybody
wanted it. All the full diets are now level to within one and a half per cent —
`sparse` excepted, which is the one diet that is *about* eating less.

**And one diet was not what its name said.** "Low sugar" was the
*protein*-heaviest diet on the menu — glutamate 7.2 against the standard diet's
4.3 — and since biosynthesis takes glutamate straight into biomass without
oxidising anything, every body grew perfectly well on it whatever its trait
broke. It is now genuinely fat-led (palmitate 8.5, glutamate 2.2), which is what
it has to be if it is to be the diet that asks whether a body can oxidise. That
one change is what let poor fat handling finally show: it scores 0.150 there
against an even lineage's 0.256.

Where it lands, each body on each diet, configured as well as it can be:

| | standard | medit. | low sugar | low fat | low protein | creamy | plain | rich | sparse | wants |
|---|---|---|---|---|---|---|---|---|---|---|
| even | 0.254 | 0.240 | **0.256** | 0.240 | 0.236 | 0.242 | 0.221 | 0.177 | 0.241 | low sugar |
| poor sugar handling | 0.123 | 0.105 | **0.207** | 0.062 | 0.098 | 0.142 | *0.010* | 0.100 | 0.198 | low sugar |
| poor fat handling | **0.252** | 0.239 | *0.150* | 0.238 | 0.178 | 0.243 | 0.220 | 0.075 | 0.238 | standard |
| reduced respiration | 0.221 | 0.211 | 0.209 | 0.204 | 0.215 | **0.223** | 0.190 | 0.147 | 0.212 | creamy |
| poor nitrogen handling | 0.225 | 0.216 | **0.238** | 0.204 | *0.175* | 0.225 | 0.195 | 0.179 | 0.198 | low sugar |
| no milk tolerance | 0.253 | 0.239 | **0.256** | 0.241 | 0.236 | *0.131* | 0.223 | 0.177 | 0.240 | low sugar |
| thrifty | **0.280** | 0.265 | 0.263 | 0.257 | 0.268 | 0.259 | 0.241 | 0.118 | 0.270 | standard |

The italics are the point: each body has a diet that costs it half its score or
worse, and it is a different diet for each. A lineage that cannot use sugar
scores 0.010 on the plainest, most wholesome diet on the menu — the one made
almost entirely of wholegrain and vegetables — and 0.207 on the one made of
butter.

### The one trait that is not about food

Reduced respiratory capacity stayed a flat tax through all of that, and the
measurements say plainly why it had to. **Every diet needs ATP.** There is no
meal that avoids the respiratory chain, so a cap on the chain scales everything
down by the same fraction whatever the lineage eats. Across five diets its
spread was 1.08 — and an even lineage's spread was also 1.08. It was not
unusually flat. It was uniformly *smaller*, and the real complaint was that it
gave the player nothing to do.

Three mechanisms were measured and rejected before the fourth worked:

- **Lean on fermentation.** The obvious answer to a broken chain, and it makes
  things worse at every setting tried: fermenting regenerates NAD+ by throwing
  the carbon away as lactate, and the score weighs yield. Raising this lineage's
  LDH and lactate export took it from 0.169 to 0.117. Fermentation is only ever
  worth it across *cells* — one lineage's waste as another's fuel — which is
  what the junction mechanic is for.
- **Prefer sugar over fat**, since sugar yields ATP at substrate level and fat
  does not. True in the flux, invisible in the score: its NADH sits pinned at
  98% on every diet, so NAD+ is the binding constraint everywhere and the
  carbon source makes no difference to it.
- **Eat less.** Under a score that counts production, eating less always loses.

What worked was to stop making it a multiplier. **The chain barely idles in this
body at all.** A configuration that does not spend one of its eight marks on the
respiratory chain scores essentially nothing — against 0.107 for an even lineage
doing exactly the same thing. Spend the mark and it runs at about four fifths of
standard on anything.

So the trait costs an eighth of the budget rather than a fifth of every score,
and that is a decision a player can find and act on. The margin names the gene,
the appendix says the chain does not idle here, and the counsel says outright
that one mark is spoken for before the run starts. It is still not a diet
preference, and it should not be: not being able to burn things is not a
complaint about what you eat.

The four tests that were marked `xfail` now pass, and nothing in the suite is
marked known-failing.

### Fructose, and the trap it makes

Every other food arrives through one of four doors — sugar, fat, amino acids,
lactate — and the plate's regulation point, PFK-1, sits on the sugar door.
Fructose is the exception, and it is the reason the door is worth thinking
about at all: fructokinase and aldolase B cleave it straight to triose, *below*
PFK-1, so the one brake a lineage has on sugar is not on it. That is textbook
biochemistry rather than a game invention, and it is drawn as what it is — a
shunt leaving the fructose pool, passing outside the regulated step, and joining
the trunk at G3P.

Half of what sweet food brings now arrives as fructose. And that produces the
sharpest decision in the game. An ordinary lineage, eating sweet, five ways:

| | built | glucose held | damage | vigour | score |
|---|---|---|---|---|---|
| do nothing | 471 | 84% | 196 | 55% | 0.123 |
| silence PFK-1 | 214 | 100% | 470 | 34% | **0.040** |
| silence PFK-1 and GLUT5 | 3 | 100% | 414 | 37% | 0.000 |
| activate PFK-1 | 473 | 63% | 154 | 61% | 0.131 |
| **silence GLUT5 only** | **558** | **23%** | **5** | **98%** | **0.270** |

The obvious move is the wrong one. Silencing the regulation point — the thing
the plate labels "the classic regulation point", the thing every instinct says
to shut — leaves you at **a third of the score of leaving it alone**: the
glucose backs up behind the closed step while the fructose keeps arriving
through a door the brake was never on. Shutting both doors is worse still in a
different way: almost nothing built at all. Marking the regulation point *up*
barely helps, because the problem was never the enzyme.

The answer is to shut the door the fructose is actually using and leave
glycolysis able to clear what does get in. It is the plan that **builds the
most**, takes essentially no damage, and finishes at full vigour — and the one
where sugar uptake goes *up*, because a cell that can process what arrives is a
cell that keeps taking it.

**And the same drawing says the opposite thing to one particular body.** Poor
sugar handling caps glycolysis at a twentieth of standard, and fructolysis is
not on that gene — so for that lineage the shunt is most of its usable carbon.
Silencing the fructose transporter, the right answer for everybody else on this
diet, starves it outright: five units built against 224 for leaving it alone.
What helps it is the move the trap warns an ordinary lineage away from, marking
the regulation point *up*, which takes it from 0.036 to 0.133. Two opposite
lessons from one shunt, which is the argument for drawing it.

None of this is hidden. The shunt is drawn joining below the regulated step, the
appendix says fructose bypasses the regulation point in the substance list, and
the gene note on aldolase B says what makes it dangerous is not speed but
position. Finding it should cost a player
one bad run, not twenty.

### What the margin says when a cell is being harmed

Building the fructose trap exposed a gap in the thing this game claims to do.
Asked what was wrong with a lineage choking to death on sugar, the margin said:

> **G3P → pyruvate is backed up behind pyruvate**
> *pyruvate → lactate is what clears it, and LDH is at 15%. Activate LDH.*

— and said exactly that whether or not the player had just made things twice as
bad. The bottleneck diagnosis answers *"why is this reaction slow"*, which is
the right question for a lineage that is merely inefficient and the wrong one
for a lineage that is being poisoned. A pool jammed at its cap does damage every
second it sits there, and nothing was reporting it.

There is now a second diagnosis beside the first, and it takes the margin
whenever there is harm being done, because a cell poisoning itself is a more
urgent fact than a step running at 60%:

> **glucose is choking this cell**
> The pool is at 100% of what it can hold (48.0 of 48.0), and everything above
> 85% is doing damage. This lineage has taken 294 of it, and damage does not
> heal.
> *It is arriving by glucose transporter (0.24/s), faster than anything here can
> use it. Silence that, or clear it: glucose → 2 G3P is what clears it, and **you
> silenced PFK-1 in generation 1. That is the cause.***

Three things it does that the flux diagnosis could not:

- **It reads the pool against this body's capacity, not the chart's.** A
  constitution that holds less of something is more easily choked by it, and
  the first version — reading the shared number — reported a cycle intermediate
  sitting chronically high and missed the pool actually at its cap.
- **It names every door.** A player told "sugar is arriving" shuts the sugar
  door and leaves the other one open, which is precisely the trap. Every route
  carrying more than a trickle is listed, and the note says outright that
  shutting one leaves the others.
- **It names the player's own mark when the player is the cause.**

**Damage is also now kept in two accounts.** Food damage is a diet the lineage
cannot afford; jam damage is a configuration that cannot clear what it is being
given — and eating *less* is the wrong answer to the second. A single total was
telling players they were eating badly when they were marking badly. Two of the
diet tests were reading that total while testing a claim about food, which is
why they had been passing for the wrong reason.

### Fixation, the one thing that cannot be undone

The fourth verb, and the only one with no way back. Everything else the player
does to this page can be reversed at a price — a mark lifted, a cell
differentiated, a diet changed. Ctrl-clicking a gene **writes the mark into the
genome**, and there is no price at which that comes off again.

What it gives: the mark leaves the budget. Eight becomes nine, in effect,
because one of them is no longer a choice being held open. It never drifts on
inheritance, differentiation does not clear it, and it is drawn in the register
at full weight inside a ruled surround rather than fading down the generations —
a fixed mark is not second-hand, because it is not being passed down. It is what
the lineage *is*.

What it takes, in three parts:

- **A mark has to be lived with first.** Ninety seconds held, which is the whole
  idea of a heritable change and also stops a player fixing eight things in the
  opening minute.
- **It costs 45 of biomass**, out of the same pool the target is counted in.
  That is a new ledger line — `written` — sitting beside `structure`: both are
  conserved, both keep the atom sum closing, and only one of them is still
  yours. Biomass spent on being two cells is still the lineage. Biomass spent
  writing the genome is gone from the score.
- **It reaches every cell.** A fixed mark is the lineage's, not this cell's.
  Every living cell gets it, every cell born after inherits it already fixed,
  and a cell that had drifted away from it or specialised out of it gets it
  back. This is the genome now, not a choice.

That last one is the decision. A feeder and a burner do not want the same genes
switched on, and fixing one of them means the other is carrying it for the rest
of the run. Fixation is how a lineage stops being able to change its mind, and
the run is fifteen minutes long, so it is also the only thing a run leaves
behind.

### The reckoning

The run ends because the clock does. That is the honest end for a game where the
whole cost structure is *later*: damage never heals, a mark held for twenty
generations is the expensive one to lift, and a lineage that burns bright is
spending something it cannot get back. None of it means anything without a bell.

The last page is not a scoreboard. The number is on it, but beside the four
things that made it and beside the one act the run could not take back:

- **the account** — built, eaten, yield, vigour, relish, each with a ruled bar
  whose length is what that factor cost. A number in a column is easy to skim
  past; a bar longer than its neighbours is not.
- **one sentence naming what decided the run.** *"Pleasure decided this run. The
  lineage was careful and the score paid for it: relish at 42% is a lineage that
  never got much out of eating, and the score counts that as a cost."* A page
  that says `0.180` and nothing else teaches nobody anything.
- **what was written into the genome**, boxed in the same hand as the register.
- **what you did** — the marks placed, lifted and fixed, in order, from the
  history every cell has been keeping all along for exactly this. The rest of
  the page is what happened; this is what the player did, which is not the same
  thing and is the half they can learn from.
- **what it ate**, totalled by food over the whole run, with a red rule against
  anything that was charging for itself. The score charges for everything
  absorbed, so a player looking at a bad yield needs to see what they were
  absorbing.
- **the lineage**, at rest. The one part of a run that is a picture of a
  decision rather than a number.

There is no failure state beyond a lineage that died out. Finishing poorly is
finishing, and the spec's own reasoning holds: a run collapsing for a reason the
player could not have fixed in time is a worse outcome than one that merely
scores badly.

The two ends of the diet axis, side by side, from the same profile and the same
number of divisions:

| | rich | low sugar |
|---|---|---|
| built | 971 | 711 |
| eaten | 4647 | 3030 |
| vigour at the bell | 33% | 100% |
| relish | 74% | 42% |
| **score** | **0.061** | **0.180** |

The rich diet built more of everything and scored a third as well, because
two-thirds of what it made was written off for the state it made it in. The
careful diet was not right either — it gave up 10% of its score to never having
enjoyed anything. Neither column is the answer; the answer is somewhere between
them and depends on the constitution you were dealt, which is the whole of the
design.

### The kitchen, and what changing your mind costs

The diet is now the player's, chosen from the appendix's kitchen page and
changed whenever they like. It is not a difficulty setting and it is not a
modifier on a standard broth: **a diet is the broth**. Living on sweets means
the culture around the cell is sugar and very little else, and every consequence
follows from that rather than from a rule saying sweets are bad. Transport is
passive, so a cell surrounded by sugar takes sugar in whether it can use it or
not. It cannot decline.

Adoption is not a fifth verb. There is no button for taking up fat; a pathway is
adopted when the player puts a mark on one of the genes that opens it, out of
the same budget of eight everything else comes from, and it fades back out if
they lift the mark. The plate prints unadopted pathways faintly from the first
second — so you can see what exists before you can use it — and inks them up, in
a second pass over the top of the faded print, when you commit.

The half that makes this a milestone rather than a menu is what a change does to
the register:

> **now eating low sugar**
> Your marks on glucose transporter, PFK-1 and GAPDH/PGK/PK were placed for
> sugar, and this diet brings 28% as much of it.
> *Palmitate arrives 5.1 times faster and nothing is marked to take it in. It
> will sit in the medium until something is.*

Three things stop the cycle becoming a flap between menus:

- **The medium turns over, it does not switch.** Perfusion is rate-limited in
  both directions, so a change takes real seconds to arrive and the old food is
  still there while it does. What the cell meets in between is a broth that is
  neither diet, and it has to eat it.
- **Damage does not reset.** Whatever the last diet did to this lineage, it
  keeps.
- **Lifting costs more than placing did, and the oldest marks cost the most.**
  A change of diet is a bill, not a re-roll.

Only the player's *own* activating marks are named. A mark inherited from a
parent was not this player's bet, and blaming them for it would be the game
telling them off for something they did not do.

#### That the configuration and the diet actually have to agree

Three mark sets against four diets, four hundred simulated seconds each, biomass
and score:

| | low fat | low sugar | plain | rich |
|---|---|---|---|---|
| **sugar-set** | 321 / 0.162 | 333 / 0.165 | 313 / 0.150 | 192 / 0.057 |
| **fat-set** | 35 / 0.073 | 263 / **0.308** | 34 / 0.068 | 258 / 0.276 |
| **mixed** | 188 / 0.145 | 279 / 0.183 | 186 / 0.136 | 227 / 0.094 |

The fat set is ruinous on a diet with no fat in it and produces the best score
in the table on one that has. The sugar set holds its output almost anywhere —
sugar is the universal fuel and the transporter idles at 0.40 whether you mark
it or not — but its score collapses on the rich diet, because output bought with
damage is output the score refuses to pay full price for. Hedging is mediocre
everywhere, which is the point of hedging.

The best cell in the table needs both halves right. That is the cycle.

#### The forced move, and how far it moved

This was written up as a fault, and it deserved to be. Every set that did well
marked the **amino acid transporter**, because nitrogen uptake — not carbon —
was what capped growth if you left it alone: glutamate sat at 3% of capacity in
a cell that had not marked `aat`, and no amount of getting the carbon side right
would move it.

The fix was not to make nitrogen cheap. It was to notice that `aat` was idling
at the default 0.15 while the other two principal transporters, `glut` and
`mct`, both idle at 0.40. That is an inconsistency rather than a balance
question — real cells express amino-acid transporters constitutively too — so
`aat` now idles at 0.40 like its neighbours.

What that bought, measured as what marking it is worth over not marking it:

| `aat` idles at | glutamate held | growth | biomass | marking it buys |
|---|---|---|---|---|
| 0.15 (was) | 5% | 0.22 | 96 | ×3.44 |
| 0.30 | 8% | 0.34 | 167 | ×1.99 |
| **0.40 (now)** | **~11%** | **~0.40** | **~204** | **×1.63** |
| 0.60 | 15% | 0.48 | 261 | ×1.27 |
| 1.00 | 22% | 0.60 | 332 | ×1.00 |

A mark that buys ×1.63 is a strong mark. A mark that buys ×3.44 is a tax.

**It is not fully fixed, and the honest reason is a different one than I
thought.** Varying only the eighth mark against a fixed seven, across five
diets and seven constitutions, `aat` is still the best answer in eleven of
twelve cases — but the margin over the runner-up is now about 14% of score
rather than a tripling, and on the rich diet the answer changes. What the sweep
actually exposed is that the runner-up is `PEPCK / FBPase` at ×1.02, and that
*ten of twelve candidate marks are within ±2% of doing nothing at all* on the
standard diet. The problem was never that `aat` is too strong. It is that most
of the register is inert unless you are eating something that needs it — fat
transport does nothing without fat, lactate transport does nothing without a
neighbour to trade with — so the eighth mark has little to compete against.

That is a design question rather than a number to tune, and it is the one I
would put to a player before touching it: should a mark that is useless on your
current diet be *visibly* useless, or should every gene do something for
everybody? The plate already argues for the first — it prints unadopted
pathways faintly — and the second would make the diet axis meaningless. So I
have left it, and written down what it costs.

### What you can ask for, and what happens anyway

Choosing a menu outright is a strange thing for a game about a body to let you
do. Nobody eats a menu. What people are given is a *direction* — eat more fish,
cut the processed meat, drink less — and what they manage is somewhere near it.
So the kitchen page now has both: the eight diets, still there and still
choosable, and eight **intentions** underneath them, keyed `a`–`h`.

An intention lands imperfectly, for two reasons, and only the second one is
interesting.

The first is that nobody eats a number. Ask to cut the fat by 60% and between
half and half again of that is what actually happens, drawn from the lineage's
own seeded stream — reproducible across a re-run of the same seed, not
predictable in advance.

The second is **substitution**. Food taken out of a diet does not leave a hole.
Something fills it, and what fills it is whatever is nearest to hand, which in
this model is sweets (0.42 of the gap), wholegrain (0.28), processed meat
(0.18), and dairy (0.12). This is the whole point of the mechanic. Nudging
"less fat" at a lineage living on the creamy diet does what it says —

| food | portions moved |
|---|---|
| dairy | **−1.10** |
| sweets | +0.30 |
| wholegrain | +0.20 |
| processed meat | +0.13 |

— and the margin answers, immediately and without being asked:

> Fructose arrives 2.1 times faster and nothing is marked to take it in. It will
> sit in the medium until something is.

The player did exactly what they were told and made the diet worse in a way that
has a name and a location on the plate. `eat_less` is the one intention with no
substitution in it, and it is the only one that lowers what the lineage has to
work with — which is the honest trade, not a free win.

#### Events

The other half is what happens to you regardless. Three events are drawn per
run from a seeded schedule, none in the first 150 seconds and none within 130
seconds of another, each announcing itself in the margin as it arrives and each
printed in the appendix from the first second. They are not a difficulty
setting and they are not unfair: a run can bring a night out, a bad three days,
a week of flu, a fortnight of deadlines, or a good stretch, and you can read all
five before anything happens.

What they are is *outside the plan*. The register you configured for a steady
diet is the register you have when the diet stops being steady.

#### The night out, and why ethanol is the right disaster

The one that has teeth is the drinking. Ethanol crosses a membrane by
diffusion; it needs no transporter, so there is no gene on the register that
keeps it out — the only lever is how much arrives, and by the time the event has
landed, that is decided. The plate now carries the route: ethanol against the
membrane in the cytosol, alcohol dehydrogenase down to **acetaldehyde**, and
aldehyde dehydrogenase crossing into the mitochondrion, which is where ALDH2
actually sits (Edenberg, 2007).

Acetaldehyde is the first metabolite in the game that is **toxic by
concentration rather than by congestion**. Every other harm in Passage comes
from a pool that cannot drain: inflow exceeds outflow, the queue lengthens, and
the cell is damaged for holding it. Acetaldehyde was perfectly flux-balanced at
94% of its cap and doing no damage at all, which is exactly wrong — the harm is
the substance, not the traffic. So `Metabolite.toxic` charges damage above a
30% share regardless of whether anything is stuck.

What that buys, measured over a 50-second night against an eight-mark lineage
on the standard diet:

| plan | cost of the night | vigour after | built | score |
|---|---|---|---|---|
| eight marks, no ALDH | 74 | 76% | 570 | 0.183 |
| eight, PFK-1 traded for ALDH | **53** | 81% | 617 | **0.219** |
| nine marks (ALDH added, not traded) | 52 | 81% | 599 | 0.204 |
| no night at all | 13 | 94% | 622 | 0.255 |

The third row is a control rather than a playable option — the budget is eight —
and it is there to show that the middle row's gain is the mark, not the removal
of PFK-1. Trading a glycolytic step for an enzyme that does nothing on most days
is a real cost paid against an event that may not come; the run where it does
not come scores worse for having paid it. That is the shape I wanted: insurance
you can decline.

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
- **Two of the three distinct entry points are still missing.** Fructose is
  built (below). Fibre fermented to short-chain fatty acids arriving at
  acetyl-CoA, and ethanol with its toxic intermediate, are not. Each would be
  a metabolite, a gene, a reaction and a place on the plate — the fructose work
  is the template for both, and the ethanol one is the more interesting because
  its damage would be in the *intermediate* rather than in the food.
- **Nitrogen uptake is still close to a forced move.** Softened, not fixed —
  see below.
- **A run is fifteen minutes and there is nothing after it.** The reckoning is
  an end, not a meta-game: no unlocks, no carry-over, nothing that turns one
  run into a campaign. That is deliberate for now — a lineage that leaves
  nothing behind except what it fixed is the whole theme — but if runs should
  chain, the genome is the obvious thing to carry, and `Lineage.fixed` is
  already the record of it.

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
- **The reaction count sits at the low end.** Eighteen chemistry steps against
  the spec's "roughly 22" — the fructose shunt and the two alcohol steps added
  three of them. Twenty-nine solver rows, because nine traffic routes with the
  medium and two reverse directions are each their own row and none of them is
  a reaction the reader has to learn. Spec open question 4 asks for 16 and 28
  to be tested at M2; the compile step is already agnostic about the count, and
  the size test now bounds the drawn chemistry rather than the solver, which is
  what the spec's concern was actually about.

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
    kitchen.py      choosing a diet, and what changing it strands
    ending.py       what a run came to, and which factor decided it
  render/
    ink.py          the six primitives: paper, line, curve, wash, leader, hand
    palette.py      the six class washes and the one alarm colour
    type.py         one face, machine-set; the hand is drawn, never typed
    plate.py        the printed page, inked once and cached
    flow_vis.py     pool washes, cell tint, the flow animation
    roster.py       the left margin
    panel.py        the right margin
    margin.py       the player's own hand: marks, notes, the diet report
    reference.py    the appendix, seven pages, inked one page at a time
    final.py        the reckoning, inked once when the bell goes
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

All seven milestones are built. What is *not* built, and was never meant to be:
dosing the medium (a fifth verb the spec forbids in as many words), a campaign
around the run, and anything that lets a player skip the seconds a decision
costs them.

---

## References

Berg, J. M., Tymoczko, J. L., Gatto, G. J., & Stryer, L. (2019). *Biochemistry*
(9th ed.). W. H. Freeman.

Edenberg, H. J. (2007). The genetics of alcohol metabolism: Role of alcohol
dehydrogenase and aldehyde dehydrogenase variants. *Alcohol Research & Health,
30*(1), 5–13.

Hinkle, P. C. (2005). P/O ratios of mitochondrial oxidative phosphorylation.
*Biochimica et Biophysica Acta (BBA) — Bioenergetics, 1706*(1–2), 1–11.
https://doi.org/10.1016/j.bbabio.2004.09.004

Nelson, D. L., & Cox, M. M. (2021). *Lehninger principles of biochemistry*
(8th ed.). Macmillan Learning.
