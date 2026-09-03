"""Why a reaction is running below capacity, in plain words, with numbers.

This is the section the project lives or dies on (spec 3.11). Two of the
previous games failed because the player could not see what the system was
doing, and the requirement here is not "show a warning icon" -- it is that a
present-day failure can be followed back to the decision that caused it,
without the player keeping notes.

So every reason produced here carries four things:

``headline``
    what is wrong, in the fewest plain words that are still true.
``detail``
    the numbers, named. Not "low substrate" but *which* substrate, how much of
    it there is, and how much there would need to be.
``remedy``
    what to do about it, in terms of the four verbs. A player cannot pour
    anything into a cell; they can only change which genes are on. So a
    shortage is always reported as *the gene that would fix it*, named, with
    its current state.
``culprit``
    the gene and the generation the mark was placed in, when the trail leads to
    one. This is the clause the design turns on.

A wrong explanation is worse than no explanation, so everything asserted here
is derived from the same arrays the solver uses, and ``tests/test_traceability``
holds each claim against the state it was drawn from.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .. import tuning
from ..data import reactions as rxn_data
from .flow import Flow
from .marks import Kind, Marks
from .network import Network

#: The share of capacity a reaction has to reach before it stops being called a
#: bottleneck. Nothing runs at 100%: saturation is a curve, so a healthy
#: reaction still sits somewhere below its ceiling.
HEALTHY = 0.72

#: What "running freely" means when saying how much of a substrate is wanted.
#: Michaelis-Menten never reaches 1, so a target has to be named, and nine
#: tenths is both reachable and honest.
FREELY = 0.9


@dataclass
class Reason:
    """One diagnosis. Everything the margin needs, already in words."""

    row: str
    kind: str                    # silenced | idling | starved | backed_up | gradient | fine
    headline: str
    detail: str
    remedy: str
    severity: float              # capacity lost, weighted by how big the step is
    share: float                 # 0..1, what fraction of capacity it is running at
    metabolite: str | None = None
    gene: str | None = None
    generation: int | None = None

    @property
    def is_bottleneck(self) -> bool:
        return self.kind != "fine"


def _plain(x: float) -> str:
    """A number a person can read out loud."""
    if x >= 100:
        return f"{x:.0f}"
    if x >= 10:
        return f"{x:.1f}"
    return f"{x:.2f}"


class Diagnostician:
    """Reads the solver's own arrays and says what they mean."""

    def __init__(self, net: Network) -> None:
        self.net = net
        n = net
        # who makes and who consumes each metabolite, by internal row
        self.producers = {m.id: np.flatnonzero(n.s_out[:, i] > 0)
                          for i, m in enumerate(n.metabolites)}
        self.consumers = {m.id: np.flatnonzero(n.s_in[:, i] > 0)
                          for i, m in enumerate(n.metabolites)}
        self.pathway_of = {r: name for name, rows in rxn_data.PATHWAYS.items()
                           for r in rows}

    # -- the public question -------------------------------------------------
    def of(self, flow: Flow, marks: Marks | None, row_id: str,
           cell: int = 0) -> Reason:
        n = self.net
        i = n.ri(row_id)
        if n.rows[i].exchange:
            return self._exchange(flow, row_id, i - n.n_internal, cell)
        return self._internal(flow, marks, row_id, i, cell)

    def bottlenecks(self, flow: Flow, marks: Marks | None, cell: int = 0,
                    limit: int = 3) -> list[Reason]:
        """The reactions costing this cell the most, worst first."""
        found = []
        for row in self.net.rows:
            if row.reverse:
                continue
            reason = self.of(flow, marks, row.id, cell)
            if reason.is_bottleneck:
                found.append(reason)
        found.sort(key=lambda r: -r.severity)
        return found[:limit]

    # -- internal reactions ---------------------------------------------------
    def _internal(self, flow: Flow, marks: Marks | None, row_id: str, i: int,
                  cell: int) -> Reason:
        n = self.net
        row = n.rows[i]
        enzyme = float(flow.enzyme[cell, n.row_gene[i]])
        sat = float(flow.saturation[cell, i])
        relief = 1.0 - float(flow.inhibition[cell, i])
        share = enzyme * sat * relief
        # what a step of this size costs when throttled: a big reaction running
        # at half is a bigger problem than a small one stopped dead
        severity = float(n.base_rate[i]) * (1.0 - share)

        if share >= HEALTHY:
            return Reason(row_id, "fine", f"{row.label} is running freely",
                          f"at {share:.0%} of what its enzyme allows", "",
                          severity, share)

        worst = min((enzyme, "enzyme"), (sat, "substrate"), (relief, "product"),
                    key=lambda pair: pair[0])[1]
        if worst == "enzyme":
            return self._enzyme_reason(flow, marks, row_id, i, cell,
                                       enzyme, share, severity)
        if worst == "substrate":
            return self._starved_reason(flow, marks, row_id, i, cell,
                                        share, severity)
        return self._backed_up_reason(flow, marks, row_id, i, cell,
                                      share, severity)

    def _enzyme_reason(self, flow, marks, row_id, i, cell, enzyme, share,
                       severity) -> Reason:
        n = self.net
        gene = n.genes[n.row_gene[i]]
        mark = marks.of(gene.id) if marks else None
        if mark is not None and mark.kind is Kind.SILENCING:
            return Reason(
                row_id, "silenced",
                f"{n.rows[i].label} is switched off",
                f"enzyme at {enzyme:.0%}. You silenced {gene.label} in "
                f"generation {mark.generation}.",
                f"Lift the mark on {gene.label} — but lifting costs more than "
                f"placing did, and takes longer to bite.",
                severity, share, gene=gene.id, generation=mark.generation)
        if mark is not None:
            return Reason(
                row_id, "idling",
                f"{n.rows[i].label} is still building its enzyme",
                f"enzyme at {enzyme:.0%}, climbing toward "
                f"{mark.target:.0%}. Nothing here responds instantly.",
                "Wait. Expression lags by seconds and the enzyme lags behind that.",
                severity, share, gene=gene.id, generation=mark.generation)
        debt = marks.debt_on(gene.id) if marks else 0.0
        if debt > 0.05:
            return Reason(
                row_id, "idling",
                f"{n.rows[i].label} is coming back slowly",
                f"enzyme at {enzyme:.0%}. {gene.label} was un-marked and is "
                f"still {debt:.1f} of budget in debt for it.",
                f"Nothing to do but wait, or mark {gene.label} again and pay "
                f"for it twice.",
                severity, share, gene=gene.id)
        return Reason(
            row_id, "idling",
            f"{n.rows[i].label} was never switched on",
            f"enzyme at {enzyme:.0%}. {gene.label} is unmarked and idling at "
            f"its baseline of {gene.baseline:.0%}.",
            self._afford(marks, gene.label),
            severity, share, gene=gene.id)

    def _starved_reason(self, flow, marks, row_id, i, cell, share,
                        severity) -> Reason:
        n = self.net
        conc = flow.pools[cell]
        worst_mid, worst_mm = None, 2.0
        for j in np.flatnonzero(n.mask_in[i]):
            mm = conc[j] / (n.km[j] + max(conc[j], 0.0))
            if mm < worst_mm:
                worst_mm, worst_mid = float(mm), n.metabolites[j].id

        j = n.mi(worst_mid)
        have = float(conc[j])
        if not n.inhibits[j]:
            return self._carrier_reason(flow, marks, row_id, i, cell, j,
                                        worst_mm, share, severity)
        # how much would be needed to run freely, from the same curve the
        # solver uses: conc = Km * s / (1 - s)
        wants = float(n.km[j]) * FREELY / (1.0 - FREELY)
        met = n.metabolites[j]
        supplier = self._best_supplier(flow, marks, worst_mid, cell)

        return Reason(
            row_id, "starved",
            f"{n.rows[i].label} is starved of {met.label}",
            f"the cell holds {_plain(have)} of {met.label} and wants about "
            f"{_plain(wants)} to run freely — {worst_mm:.0%} of the way there.",
            supplier,
            severity, share, metabolite=worst_mid)

    #: The two conserved pairs. Being short of one half means the other half is
    #: piled up, and the fix is never "make more" -- it is to spend the partner.
    PARTNER = {"adp": "atp", "atp": "adp", "nad": "nadh", "nadh": "nad"}

    def _carrier_reason(self, flow, marks, row_id, i, cell, j, mm, share,
                        severity) -> Reason:
        """Being short of a carrier is a ratio problem, not a supply problem.

        Telling a player they need more ADP is true and useless: ADP is not
        made, it is what is left when ATP is spent. So the explanation names the
        partner, says which way the pair has tipped, and points at the reaction
        that would tip it back.
        """
        n = self.net
        met = n.metabolites[j]
        partner_id = self.PARTNER[met.id]
        partner = n.metabolites[n.mi(partner_id)]
        have = float(flow.pools[cell, j])
        held = float(flow.pools[cell, n.mi(partner_id)])
        total = have + held
        spender = self._best_drain(flow, marks, partner_id, cell, exclude=-1)
        return Reason(
            row_id, "starved",
            f"{n.rows[i].label} is short of {met.label}",
            f"{met.label} and {partner.label} are one closed pool: "
            f"{_plain(have)} against {_plain(held)}, so "
            f"{held / total:.0%} of it is sitting as {partner.label}. "
            f"{met.label} is not made — it is what is left when "
            f"{partner.label} gets spent, and nothing here is spending it.",
            spender,
            severity, share, metabolite=met.id)

    def _backed_up_reason(self, flow, marks, row_id, i, cell, share,
                          severity) -> Reason:
        n = self.net
        conc = flow.pools[cell]
        fills = np.where(n.mask_out[i], conc / n.cap, -1.0)
        j = int(np.argmax(fills))
        met = n.metabolites[j]
        drain = self._best_drain(flow, marks, met.id, cell, exclude=i)
        return Reason(
            row_id, "backed_up",
            f"{n.rows[i].label} is backed up behind {met.label}",
            f"{met.label} is at {float(fills[j]):.0%} of its capacity "
            f"({_plain(float(conc[j]))} of {_plain(float(n.cap[j]))}). A full "
            f"product pool pushes back on the step that fills it.",
            drain,
            severity, share, metabolite=met.id)

    # -- following the trail one step further --------------------------------
    def _best_supplier(self, flow, marks, mid: str, cell: int) -> str:
        """Name the gene that would make more of what this reaction lacks.

        The player cannot pour anything into a cell. They can only decide which
        genes are on, so a shortage has to be reported as a gene.
        """
        n = self.net
        best, best_room = None, -1.0
        for i in self.producers.get(mid, []):
            if n.rows[i].reverse:
                continue
            enzyme = float(flow.enzyme[cell, n.row_gene[i]])
            room = float(n.base_rate[i]) * (1.0 - enzyme)
            if room > best_room:
                best, best_room = int(i), room
        if best is None:
            return f"Nothing in this cell makes {mid}; it has to come in from outside."
        gene = n.genes[n.row_gene[best]]
        made_by = n.rows[best].label
        mark = marks.of(gene.id) if marks else None
        state = (f"silenced in generation {mark.generation}"
                 if mark and mark.kind is Kind.SILENCING else
                 f"already activated" if mark else
                 f"unmarked, at {float(flow.enzyme[cell, n.row_gene[best]]):.0%}")
        if mark and mark.kind is Kind.SILENCING:
            return (f"{made_by} is what makes it, and you {state}. "
                    f"Lifting that mark on {gene.label} is the fix.")
        if mark:
            return (f"{made_by} is what makes it and {gene.label} is {state}; "
                    f"the shortage is further upstream.")
        return (f"{made_by} is what makes it, and {gene.label} is {state}. "
                + self._afford(marks, gene.label))

    def _best_drain(self, flow, marks, mid: str, cell: int, exclude: int) -> str:
        """Name the gene that would clear what this reaction is backed up behind."""
        n = self.net
        best, best_room = None, -1.0
        for i in self.consumers.get(mid, []):
            if i == exclude or n.rows[i].reverse:
                continue
            enzyme = float(flow.enzyme[cell, n.row_gene[i]])
            room = float(n.base_rate[i]) * (1.0 - enzyme)
            if room > best_room:
                best, best_room = int(i), room
        if best is None:
            return f"Nothing in this cell consumes {mid}; it can only be sent out."
        gene = n.genes[n.row_gene[best]]
        mark = marks.of(gene.id) if marks else None
        if mark and mark.kind is Kind.SILENCING:
            return (f"{n.rows[best].label} is what clears it, and you silenced "
                    f"{gene.label} in generation {mark.generation}. That is the cause.")
        return (f"{n.rows[best].label} is what clears it, and {gene.label} is "
                f"at {float(flow.enzyme[cell, n.row_gene[best]]):.0%}. "
                + self._afford(marks, gene.label))

    @staticmethod
    def _afford(marks: Marks | None, subject: str) -> str:
        """Advice a player cannot act on is worse than none.

        With the budget full, "activate this" is not a remedy -- it is a
        reminder that something has to be given up first. So the note changes
        mood, and names the mark that would be cheapest to lift.
        """
        if marks is None or marks.can_place():
            return f"Activate {subject}. It costs one of your eight."
        cheapest = min(marks.marks.values(),
                       key=lambda m: (m.fixed, m.generation), default=None)
        if cheapest is None:
            return (f"Activating {subject} would clear it, but your whole "
                    f"budget is spoken for by debt. There is nothing to do but "
                    f"wait for it to decay.")
        label = marks.net.genes[marks.net.gi(cheapest.gene)].label
        return (f"Activating {subject} would clear it, but all eight marks are "
                f"placed. Something has to come off first, and lifting costs "
                f"more than placing did — the oldest is {label}, from "
                f"generation {cheapest.generation}.")

    # -- exchange -------------------------------------------------------------
    def _exchange(self, flow: Flow, row_id: str, k: int, cell: int) -> Reason:
        n = self.net
        j = int(n.x_metabolite[k])
        met = n.metabolites[j]
        inside = float(flow.pools[cell, j])
        outside = float(flow.medium[j])
        rate = float(flow.x_rate[cell, k])
        km = float(n.km[j])
        drive = (outside / (km + outside)) - (inside / (km + inside))
        share = min(1.0, abs(drive) / 0.5)
        severity = float(n.x_base_rate[k]) * (1.0 - share) * 0.5

        if abs(rate) > 1e-3 and share >= 0.35:
            return Reason(row_id, "fine", f"{met.label} is crossing freely",
                          f"{_plain(abs(rate))} a second, "
                          f"{'in' if rate > 0 else 'out'}", "", severity, share,
                          metabolite=met.id)
        return Reason(
            row_id, "gradient",
            f"{met.label} has stopped moving",
            f"the cell holds {_plain(inside)} and the medium holds "
            f"{_plain(outside)}. Transport is passive — nothing is pumped, so "
            f"material only moves while there is a difference to move it.",
            f"Nothing crosses a membrane on request. Burn the {met.label} "
            f"inside faster and more will follow it in.",
            severity, share, metabolite=met.id)
