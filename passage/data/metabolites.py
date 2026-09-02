"""The substance list.

Sixteen pooled metabolites plus two buffered ones. Each carries an atom count,
which is what the mass-balance invariant is checked against (spec 3.1).

Two bookkeeping simplifications, both deliberate and both documented here
rather than hidden in the solver:

* ``acetyl`` stands for acetyl-CoA, represented by its acetyl moiety hydrated
  to acetate (C2H4O2). Coenzyme A is implicit and, being conserved on every
  reaction that touches it, never appears in the balance.
* ``nadh`` is ``nad`` plus two hydrogens. This is the textbook ``2[H]``
  reducing-equivalent notation: it bundles NADH with the proton released
  alongside it. FADH2 is folded into the same carrier.

Everything else uses real formulae.

``BUFFER`` metabolites (water, inorganic phosphate) are chemically real and
appear in the reaction table so that balance holds exactly, but they are not
drawn on the plate and are never limiting. Their net flux is metered so that
atom conservation can still be checked end to end.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Class(Enum):
    """The six taxonomic classes of the art direction, plus the buffer."""

    SUGARS = "sugars"
    LIPIDS = "lipids"
    AMINO_ACIDS = "amino_acids"
    ENERGY = "energy"
    GASES = "gases"
    WASTE = "waste"
    BUFFER = "buffer"


@dataclass(frozen=True)
class Metabolite:
    id: str
    label: str
    atoms: dict[str, int]
    cls: Class
    cap: float = 100.0
    km: float = 5.0
    buffered: bool = False
    note: str = ""

    @property
    def mass(self) -> int:
        """Total atom count. Used only for reporting, never for chemistry."""
        return sum(self.atoms.values())


def _m(id, label, atoms, cls, **kw):
    return Metabolite(id=id, label=label, atoms=atoms, cls=cls, **kw)


METABOLITES: list[Metabolite] = [
    # --- sugars: the glycolytic backbone -------------------------------
    _m("glucose", "glucose", {"C": 6, "H": 12, "O": 6}, Class.SUGARS, cap=60.0, km=5.0),
    _m("g3p", "G3P", {"C": 3, "H": 7, "O": 6, "P": 1}, Class.SUGARS, cap=30.0, km=3.0,
       note="midpoint of glycolysis; fructose enters here, bypassing regulation"),
    _m("pyruvate", "pyruvate", {"C": 3, "H": 4, "O": 3}, Class.SUGARS, cap=30.0, km=3.0),
    _m("oxaloacetate", "oxaloacetate", {"C": 4, "H": 4, "O": 5}, Class.SUGARS,
       cap=60.0, km=1.0, note="TCA acceptor; drains without anaplerosis"),

    # --- lipids ---------------------------------------------------------
    _m("acetyl", "acetyl-CoA", {"C": 2, "H": 4, "O": 2}, Class.LIPIDS, cap=40.0, km=2.0,
       note="acetyl moiety only; CoA implicit"),
    _m("palmitate", "palmitate", {"C": 16, "H": 32, "O": 2}, Class.LIPIDS, cap=30.0, km=2.0),

    # --- amino acids ----------------------------------------------------
    _m("akg", "2-oxoglutarate", {"C": 5, "H": 6, "O": 5}, Class.AMINO_ACIDS, cap=60.0, km=1.0,
       note="cycle intermediates need headroom: cap them tight and the cycle "
            "jams solid on its own product inhibition"),
    _m("glutamate", "glutamate", {"C": 5, "H": 9, "N": 1, "O": 4}, Class.AMINO_ACIDS,
       cap=30.0, km=3.0),
    _m("biomass", "biomass", {"C": 9, "H": 13, "N": 1, "O": 6}, Class.AMINO_ACIDS,
       cap=100.0, km=10.0,
       note="one lumped unit of new cell material; what division is paid for in"),

    # --- energy carriers: two conserved pairs ---------------------------
    _m("atp", "ATP", {"C": 10, "H": 16, "N": 5, "O": 13, "P": 3}, Class.ENERGY,
       cap=50.0, km=2.0),
    _m("adp", "ADP", {"C": 10, "H": 15, "N": 5, "O": 10, "P": 2}, Class.ENERGY,
       cap=50.0, km=2.0),
    _m("nad", "NAD+", {"C": 21, "H": 26, "N": 7, "O": 14, "P": 2}, Class.ENERGY,
       cap=20.0, km=1.0),
    _m("nadh", "NADH", {"C": 21, "H": 28, "N": 7, "O": 14, "P": 2}, Class.ENERGY,
       cap=20.0, km=1.0),

    # --- gases ----------------------------------------------------------
    _m("o2", "oxygen", {"O": 2}, Class.GASES, cap=30.0, km=1.0),
    _m("co2", "carbon dioxide", {"C": 1, "O": 2}, Class.GASES, cap=30.0, km=0.5,
       note="also the carboxylation substrate; vent it too hard and anaplerosis starves"),

    # --- waste ----------------------------------------------------------
    _m("lactate", "lactate", {"C": 3, "H": 6, "O": 3}, Class.WASTE, cap=80.0),
    _m("ammonia", "ammonia", {"N": 1, "H": 3}, Class.WASTE, cap=25.0, km=2.0),

    # --- buffered: real chemistry, never limiting, never drawn ----------
    _m("water", "water", {"H": 2, "O": 1}, Class.BUFFER, buffered=True),
    _m("phosphate", "Pi", {"H": 3, "O": 4, "P": 1}, Class.BUFFER, buffered=True),
]

BY_ID: dict[str, Metabolite] = {m.id: m for m in METABOLITES}

#: Conserved carrier pairs. Their summed pool must not drift.
CARRIER_PAIRS: tuple[tuple[str, str], ...] = (("atp", "adp"), ("nadh", "nad"))

POOLED: list[Metabolite] = [m for m in METABOLITES if not m.buffered]
