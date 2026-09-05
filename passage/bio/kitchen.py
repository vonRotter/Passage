"""Choosing what to eat, and living with what that does to your marks.

Adoption is the fifth thing a run turns on, and it is not a fifth *verb*: the
player still only marks, divides, differentiates and fixes. What changes here is
the medium the lineage sits in. A diet is not a modifier on the standard broth,
it *is* the broth, and every consequence follows from that rather than from a
rule saying one food is good and another bad.

The reason this is a milestone of its own is the second half: **changing what
you eat invalidates what you configured**. A lineage set up to run on sugar has
its marks on the glucose transporter, on PFK and on GAPDH, and every one of
those marks is worth exactly nothing the moment the sugar stops arriving. The
budget is eight. Lifting a mark costs more than placing it did, and the oldest
marks cost the most, so a change of diet is not a free re-roll -- it is a bill.

Three things keep the cycle honest and stop it becoming a flap between menus:

* **The medium turns over, it does not switch.** Perfusion is rate-limited in
  both directions, so a change takes real seconds to arrive and the old food is
  still around while it does. What you meet in between is a medium that is
  neither one diet nor the other.
* **Damage does not reset.** Whatever the last diet did to this lineage, it
  keeps.
* **The game says what just became wrong**, in the same plain words it uses for
  a bottleneck, because a player who cannot see what changed has been cheated
  rather than challenged.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..data import foods as food_data
from ..data import metabolites as met_data


#: Which gate each markable gene serves. A gene is listed here only if a change
#: in what arrives at that gate changes whether the mark was worth placing --
#: the genes in the middle of the plate serve every diet and appear nowhere.
SERVES: dict[str, str] = {
    "glut": "glucose",
    "pfk": "glucose",
    "gapdh": "glucose",
    "cd36": "palmitate",
    "acad": "palmitate",
    "aat": "glutamate",
    "gdh": "glutamate",
    "mct": "lactate",
}

#: What each gate is called when the margin has to talk about it in words.
GATE_WORDS: dict[str, str] = {
    "glucose": "sugar",
    "palmitate": "fat",
    "glutamate": "amino acids",
    "lactate": "lactate",
}

#: Below this share of the old supply, a gate has meaningfully closed.
CLOSED = 0.55
#: Above this multiple of the old supply, a gate has meaningfully opened.
OPENED = 1.8
#: A gate supplying less than this is not worth remarking on either way.
NEGLIGIBLE = 0.15


@dataclass
class Upset:
    """What a change of diet did to the configuration the player was holding."""

    was: str
    now: str
    #: One line per gate that changed enough to matter, worst first.
    lines: list[str] = field(default_factory=list)
    #: Marks that were placed for a gate that has just closed.
    stranded: list[str] = field(default_factory=list)

    @property
    def quiet(self) -> bool:
        return not self.lines


def gates(diet: dict[str, float], constitution=None) -> dict[str, float]:
    """What a diet actually delivers at each gate, per second.

    Measured after the body has had its say: a lineage that absorbs a quarter of
    what dairy offers is fed a quarter of it, and a lineage that ferments its
    milk sugar on the way in is fed acid instead of sugar.
    """
    out: dict[str, float] = {}
    for food_id, portions in diet.items():
        food = food_data.BY_ID[food_id]
        taken = portions
        if constitution is not None:
            taken *= constitution.absorbs.get(food_id, 1.0)
            swap = constitution.redirects.get(food_id, {})
        else:
            swap = {}
        for mid, amount in food.supplies.items():
            lands = swap.get(mid, mid)
            out[lands] = out.get(lands, 0.0) + amount * taken
    return out


def _held(marks, gate: str) -> list[str]:
    """The player's own activating marks serving one gate. Not the inherited
    ones: a mark that came down from a parent was not this player's bet."""
    return [gene for gene, mark in marks.marks.items()
            if SERVES.get(gene) == gate
            and mark.kind.value == "activating"]


def upset(was: str, now: str, before: dict[str, float], after: dict[str, float],
          marks=None) -> Upset:
    """What just became wrong, in plain words, worst first.

    Only the gates a player could act on are reported. A diet that changes the
    fat supply by a third is not news; a diet that ends it while four marks are
    committed to taking fat in is the whole of the milestone.
    """
    report = Upset(was=was, now=now)
    ranked: list[tuple[float, str, list[str]]] = []

    for gate in ("glucose", "palmitate", "glutamate", "lactate"):
        old, new = before.get(gate, 0.0), after.get(gate, 0.0)
        if max(old, new) < NEGLIGIBLE:
            continue
        word = GATE_WORDS[gate]
        mine = _held(marks, gate) if marks is not None else []
        label = met_data.BY_ID[gate].label

        if old > NEGLIGIBLE and new < old * CLOSED:
            share = new / old if old > 0 else 0.0
            if mine:
                names = _names(marks, mine)
                line = (f"{names} {'was' if len(mine) == 1 else 'were'} placed "
                        f"for {word}, and this diet brings "
                        f"{_share(share)} as much of it.")
                weight = 2.0 + len(mine)
                ranked.append((weight, line, mine))
            else:
                ranked.append((1.0, f"{_cap(label)} drops to {_share(share)} of "
                                    f"what it was. Nothing on the register is "
                                    f"committed to it.", []))
        elif new > NEGLIGIBLE and new > old * OPENED:
            if mine:
                ranked.append((0.9, f"{_cap(label)} arrives "
                                    f"{new / max(old, 1e-6):.1f} times faster, "
                                    f"and the register is already set to take "
                                    f"it.", []))
            else:
                ranked.append((1.6, f"{_cap(label)} arrives {_times(old, new)} "
                                    f"and nothing is marked to take it in. It "
                                    f"will sit in the medium until something "
                                    f"is.", []))

    ranked.sort(key=lambda row: -row[0])
    report.lines = [line for _, line, _ in ranked]
    report.stranded = [gene for _, _, genes in ranked for gene in genes]
    return report


def _cap(text: str) -> str:
    """Sentence case. The substance labels are lower case on the plate, where
    they are captions; at the head of a sentence that reads as a slip."""
    return text[:1].upper() + text[1:]


def _names(marks, genes: list[str]) -> str:
    labels = [marks.net.genes[marks.net.gi(g)].label for g in genes]
    if len(labels) == 1:
        return f"Your mark on {labels[0]}"
    if len(labels) == 2:
        return f"Your marks on {labels[0]} and {labels[1]}"
    return f"Your marks on {', '.join(labels[:-1])} and {labels[-1]}"


def _share(share: float) -> str:
    if share < 0.02:
        return "none"
    return f"{share:.0%}"


def _times(old: float, new: float) -> str:
    if old < NEGLIGIBLE:
        return "for the first time"
    return f"{new / old:.1f} times faster"
