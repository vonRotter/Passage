"""What a run came to, and what it was worth.

A run ends because the clock does. That is the honest end for a game where the
whole cost structure is *later*: damage never heals, a mark held for twenty
generations costs the most to lift, and a lineage that burns bright is spending
something it cannot get back. None of that means anything without a bell.

The reckoning is not a single number. A score is the compression of the run and
the player needs to be able to decompress it, so this reads out the four things
the score is made of and says which one it was that decided the outcome. A page
that says "0.184" and nothing else teaches nobody anything.

There is no failure state here beyond a lineage that died. Finishing poorly is
finishing, and the spec's own reasoning holds: a run collapsing for a reason the
player could not have fixed in time is a worse outcome than one that merely
scores badly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .. import tuning


@dataclass
class Line:
    """One row of the reckoning: what it was, what it read, what it did."""

    label: str
    value: str
    note: str = ""
    weight: float = 0.0          # how much this line moved the score, 0 to 1


class Ending:
    """The state of a lineage at the bell, and an account of how it got there."""

    def __init__(self, lineage, vigour, elapsed: float, flow) -> None:
        self.lineage = lineage
        self.vigour = vigour
        self.elapsed = elapsed
        self.flow = flow
        self.built = lineage.biomass()
        self.eaten = sum(vigour.eaten.values())
        self.score = vigour.score(self.built)
        self.extinct = not lineage.living
        self.written = float(flow.ledger.written[flow.net.mi("biomass")])

    # -- the account ---------------------------------------------------------
    def yields(self) -> float:
        return self.built / self.eaten if self.eaten > 1e-9 else 0.0

    def mood(self) -> float:
        return (tuning.SCORE_RELISH_FLOOR
                + (1.0 - tuning.SCORE_RELISH_FLOOR) * self.vigour.relish)

    def lines(self) -> list[Line]:
        """The four factors, and how far each of them was from its best.

        ``weight`` is what each factor cost, as a share of the score it would
        have had at full marks on that factor alone. It is what turns the number
        into a sentence: not "you scored 0.18" but "you scored 0.18 and it was
        the vigour that took it".
        """
        y, v, m = self.yields(), self.vigour.vigour, self.mood()
        return [
            Line("built", f"{self.built:.0f}",
                 f"{len(self.lineage.members)} cells, "
                 f"{len(self.lineage.living)} of them alive at the bell"),
            Line("eaten", f"{self.eaten:.0f}",
                 f"on {self.vigour.served}"),
            Line("yield", f"{y:.3f}", "built per unit eaten", 0.0),
            Line("vigour", f"{v:.0%}",
                 "what the diet left the lineage in", 1.0 - v),
            Line("relish", f"{self.vigour.relish:.0%}",
                 "a lineage that never enjoyed anything did worse",
                 1.0 - m),
        ]

    def decided_by(self) -> str:
        """The one sentence a player should take away."""
        if self.extinct:
            return ("The lineage died before the bell. Whatever else was right, "
                    "nothing survived to be counted.")
        v, m = self.vigour.vigour, self.mood()
        if v < 0.65 and (1.0 - v) > (1.0 - m):
            return (f"Damage decided this run. The lineage built "
                    f"{self.built:.0f} and finished at {v:.0%} vigour, so "
                    f"{(1.0 - v):.0%} of what it made was written off for the "
                    f"state it made it in.")
        if m < 0.78:
            return (f"Pleasure decided this run. The lineage was careful and "
                    f"the score paid for it: relish at "
                    f"{self.vigour.relish:.0%} is a lineage that never got "
                    f"much out of eating, and the score counts that as a cost.")
        if self.yields() < 0.2:
            return (f"Yield decided this run. The lineage ate "
                    f"{self.eaten:.0f} and built {self.built:.0f} of it, so "
                    f"most of what arrived was never turned into anything.")
        return (f"Nothing went badly wrong. The lineage built "
                f"{self.built:.0f} at {self.vigour.vigour:.0%} vigour and "
                f"{self.vigour.relish:.0%} relish, which is a run that got "
                f"the balance about right.")

    def written_in(self) -> list[tuple[str, str]]:
        """What the lineage carries in its genome now, and what it cost."""
        net = self.lineage.net
        return [(net.genes[net.gi(gene)].label, kind.value)
                for gene, kind in self.lineage.fixed.items()]

    def epitaph(self) -> str:
        """The line about fixation, which is the run's one irreversible act."""
        n = len(self.lineage.fixed)
        if not n:
            return ("Nothing was fixed. Every mark this lineage carried was "
                    "still a choice at the bell, and every one of them died "
                    "with it.")
        return (f"{n} mark{'s' if n != 1 else ''} written into the genome, at "
                f"{self.written:.0f} of biomass. That is what a lineage leaves: "
                f"not what it built, which is counted and then gone, but what "
                f"it stopped being able to change its mind about.")
