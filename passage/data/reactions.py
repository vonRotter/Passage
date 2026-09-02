"""The reaction table.

Every row balances on atom count. That is a hard invariant, checked at load
and by ``tests/test_balance.py``; a reaction that creates matter silently
corrupts every efficiency number in the game.

Reactions come in two kinds:

``INTERNAL``
    chemistry inside a cell.
``EXCHANGE``
    traffic across the cell boundary, between a cell and the shared medium.
    An exchange row moves one metabolite in one direction and so balances
    trivially, but it still carries a gene, a rate, and saturation.

Several rows are deliberate lumps of a longer real sequence -- the payoff half
of glycolysis, the second arc of the TCA cycle, the respiratory chain, seven
turns of beta-oxidation. Each lump is noted. The stoichiometry of the lump is
the true net stoichiometry of the steps it replaces.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Reaction:
    id: str
    label: str
    inputs: dict[str, float]
    outputs: dict[str, float]
    enzyme: str
    base_rate: float
    reversible: bool = False
    reverse_ratio: float = 0.25
    exchange: bool = False
    note: str = ""


def _r(id, label, inputs, outputs, enzyme, base_rate, **kw):
    return Reaction(id=id, label=label, inputs=inputs, outputs=outputs,
                    enzyme=enzyme, base_rate=base_rate, **kw)


INTERNAL: list[Reaction] = [
    # --- glycolysis -----------------------------------------------------
    _r("glycolysis_upper", "glucose → 2 G3P",
       {"glucose": 1, "atp": 2}, {"g3p": 2, "adp": 2},
       "pfk", 3.0,
       note="hexokinase through aldolase; two ATP invested, no return yet"),
    _r("glycolysis_lower", "G3P → pyruvate",
       {"g3p": 1, "adp": 2, "phosphate": 1, "nad": 1},
       {"pyruvate": 1, "atp": 2, "nadh": 1, "water": 1},
       "gapdh", 6.0,
       note="GAPDH through pyruvate kinase; the substrate-level payoff"),
    _r("gluconeogenesis", "2 G3P → glucose",
       {"g3p": 2, "water": 2}, {"glucose": 1, "phosphate": 2},
       "fbpase", 1.0,
       note="the reverse route, on its own enzyme; PFK is not reversible"),

    # --- fermentation ---------------------------------------------------
    _r("fermentation", "pyruvate → lactate",
       {"pyruvate": 1, "nadh": 1}, {"lactate": 1, "nad": 1},
       "ldh", 7.0, reversible=True, reverse_ratio=0.15,
       note="the only way to regenerate NAD+ without oxygen"),

    # --- entry to the cycle ---------------------------------------------
    _r("pdh", "pyruvate → acetyl-CoA",
       {"pyruvate": 1, "nad": 1, "water": 1},
       {"acetyl": 1, "co2": 1, "nadh": 1},
       "pdh", 6.0,
       note="irreversible; carbon that passes here cannot go back to sugar"),

    # --- the citric acid cycle, in two arcs ------------------------------
    _r("tca_upper", "acetyl + OAA → 2-oxoglutarate",
       {"acetyl": 1, "oxaloacetate": 1, "nad": 1},
       {"akg": 1, "co2": 1, "nadh": 1},
       "cs", 6.0,
       note="citrate synthase, aconitase, isocitrate dehydrogenase, lumped"),
    _r("tca_lower", "2-oxoglutarate → OAA",
       {"akg": 1, "nad": 3, "adp": 1, "phosphate": 1, "water": 1},
       {"oxaloacetate": 1, "co2": 1, "nadh": 3, "atp": 1},
       "ogdh", 6.0,
       note="OGDH round to malate dehydrogenase; FADH2 folded into NADH"),
    _r("cataplerosis", "OAA → pyruvate",
       {"oxaloacetate": 1}, {"pyruvate": 1, "co2": 1},
       "fbpase", 1.5,
       note="PEPCK route out of the cycle; without a way out, the cycle jams "
            "solid on its own intermediates"),
    _r("anaplerosis", "pyruvate → OAA",
       {"pyruvate": 1, "co2": 1, "atp": 1, "water": 1},
       {"oxaloacetate": 1, "adp": 1, "phosphate": 1},
       "pc", 2.0,
       note="pyruvate carboxylase; without it the cycle bleeds dry"),

    # --- respiration -----------------------------------------------------
    _r("oxphos", "2 NADH + O2 → 5 ATP",
       {"nadh": 2, "o2": 1, "adp": 5, "phosphate": 5},
       {"nad": 2, "water": 7, "atp": 5},
       "etc", 15.0,
       note="P/O ratio of 2.5 per NADH; the whole chain as one step"),

    # --- lipid ------------------------------------------------------------
    _r("beta_oxidation", "palmitate → 8 acetyl-CoA",
       {"palmitate": 1, "atp": 2, "nad": 14, "water": 16},
       {"acetyl": 8, "nadh": 14, "adp": 2, "phosphate": 2},
       "acad", 0.8,
       note="activation costs two ATP equivalents; seven turns of the spiral"),
    _r("lipogenesis", "8 acetyl-CoA → palmitate",
       {"acetyl": 8, "nadh": 14, "atp": 7},
       {"palmitate": 1, "nad": 14, "adp": 7, "phosphate": 7, "water": 7},
       "fas", 0.4,
       note="reducing power is NADPH in life; folded into NADH here"),

    # --- growth -----------------------------------------------------------
    _r("biosynthesis", "acetyl + glutamate → biomass",
       {"acetyl": 2, "glutamate": 1, "atp": 2},
       {"biomass": 1, "adp": 2, "phosphate": 2},
       "biosyn", 2.0,
       note="one lumped condensation standing for the whole anabolic load; "
            "biomass is what a cell must accumulate before it can divide"),

    # --- nitrogen ---------------------------------------------------------
    _r("gdh", "glutamate ⇌ 2-oxoglutarate + NH3",
       {"glutamate": 1, "nad": 1, "water": 1},
       {"akg": 1, "ammonia": 1, "nadh": 1},
       "gdh", 2.5, reversible=True, reverse_ratio=0.30,
       note="carbon skeleton into the cycle, nitrogen out as ammonia"),

    # --- the cost of being alive ------------------------------------------
    _r("maintenance", "ATP → ADP",
       {"atp": 1, "water": 1}, {"adp": 1, "phosphate": 1},
       "maintenance", 5.0,
       note="unregulated basal burn; the floor every configuration must clear"),
]

EXCHANGE: list[Reaction] = [
    # Exchange is passive and bidirectional: net flux follows the concentration
    # gradient between the cell and the medium, and never runs against it
    # (spec 3.6). ``base_rate`` is the permeability, not a direction. There is
    # no separate "export" row, because a carrier that could pump both ways at
    # once would just spin a futile cycle.
    _r("exchange_glucose", "glucose", {"glucose": 1}, {"glucose": 1}, "glut", 3.0, exchange=True),
    _r("exchange_o2", "oxygen", {"o2": 1}, {"o2": 1}, "resp_o2", 20.0, exchange=True),
    _r("exchange_palmitate", "palmitate", {"palmitate": 1}, {"palmitate": 1}, "cd36", 1.5, exchange=True),
    _r("exchange_glutamate", "glutamate", {"glutamate": 1}, {"glutamate": 1}, "aat", 2.5, exchange=True),
    _r("exchange_lactate", "lactate", {"lactate": 1}, {"lactate": 1}, "mct", 6.0, exchange=True),
    _r("exchange_co2", "carbon dioxide", {"co2": 1}, {"co2": 1}, "co2_vent", 3.0, exchange=True),
    _r("exchange_ammonia", "ammonia", {"ammonia": 1}, {"ammonia": 1}, "amt", 4.0, exchange=True),
]

REACTIONS: list[Reaction] = INTERNAL + EXCHANGE
BY_ID: dict[str, Reaction] = {r.id: r for r in REACTIONS}
