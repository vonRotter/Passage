"""Genes and the enzymes they encode.

One gene per catalysed step. A gene has a baseline expression it drifts to
when unmarked (spec 3.3); marks push it toward 1 or toward 0. Nothing here
knows about marks -- that arrives at M2.

``maintenance`` is the one gene the player can never touch: it stands for the
cell's unavoidable ATP burn, and it is pinned at full expression.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Gene:
    id: str
    label: str
    baseline: float = 0.15
    markable: bool = True
    note: str = ""


GENES: list[Gene] = [
    Gene("pfk", "PFK-1", note="commits glucose to glycolysis; the classic regulation point"),
    Gene("gapdh", "GAPDH/PGK/PK", note="the payoff half of glycolysis, lumped"),
    Gene("ldh", "LDH", note="fermentation; regenerates NAD+ without oxygen"),
    Gene("pdh", "PDH", note="the gate from glycolysis into the TCA cycle"),
    Gene("cs", "citrate synthase", note="acetyl + oxaloacetate, through to 2-oxoglutarate"),
    Gene("ogdh", "OGDH", note="the rest of the cycle, back to oxaloacetate"),
    Gene("etc", "respiratory chain", baseline=0.30, note="oxidative phosphorylation"),
    Gene("acad", "acyl-CoA dehydrogenase", note="beta-oxidation of palmitate"),
    Gene("fas", "fatty acid synthase", note="stores surplus acetyl as fat"),
    Gene("biosyn", "anabolic condensation", baseline=0.25,
         note="turns carbon and nitrogen into cell material; the demand side of "
              "the whole factory, and the only reason ATP is worth making"),
    Gene("gdh", "glutamate dehydrogenase", note="amino nitrogen in and out; makes ammonia"),
    Gene("pc", "pyruvate carboxylase", note="anaplerosis; refills oxaloacetate"),
    Gene("fbpase", "PEPCK / FBPase", baseline=0.05, note="the gluconeogenic enzymes as one group: carbon back out of the cycle and up the pathway"),
    Gene("glut", "glucose transporter", baseline=0.40, note="glucose uptake"),
    Gene("resp_o2", "oxygen diffusion", baseline=1.00, markable=False, note="passive"),
    Gene("cd36", "fatty acid transporter", note="palmitate uptake"),
    Gene("aat", "amino acid transporter", note="glutamate uptake"),
    Gene("mct", "monocarboxylate transporter", baseline=0.40, note="lactate in and out"),
    Gene("co2_vent", "CO2 venting", baseline=1.00, markable=False, note="passive"),
    Gene("amt", "ammonia export", baseline=0.30, note="nitrogen out; neglect it and ammonia builds"),
    Gene("maintenance", "basal maintenance", baseline=1.00, markable=False,
         note="the ATP the cell burns simply by existing"),
]

BY_ID: dict[str, Gene] = {g.id: g for g in GENES}
