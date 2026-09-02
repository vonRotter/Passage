"""The pathway graph, compiled from ``data/`` into numpy matrices.

The network is fixed across all runs: never shuffled, never generated
(spec 3.1). This module turns the plain tables into the arrays the solver
needs, and refuses to build at all if any reaction fails to balance.

Reversible reactions are expanded into two solver rows -- a forward row and a
reverse row sharing one gene. That keeps the solver a single unconditional
matrix operation instead of a signed special case, and lets each direction
saturate and inhibit on its own substrates, which is what actually happens.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np

from .. import tuning
from ..data import genes as gene_data
from ..data import metabolites as met_data
from ..data import reactions as rxn_data


class BalanceError(ValueError):
    """A reaction that does not conserve atoms. Never recoverable."""


def atom_totals(side: dict[str, float]) -> Counter:
    total: Counter = Counter()
    for mid, n in side.items():
        for atom, count in met_data.BY_ID[mid].atoms.items():
            total[atom] += count * n
    return total


def check_balance(reaction: rxn_data.Reaction) -> None:
    if reaction.exchange:
        return
    left, right = atom_totals(reaction.inputs), atom_totals(reaction.outputs)
    for atom in set(left) | set(right):
        if abs(left[atom] - right[atom]) > tuning.BALANCE_TOLERANCE:
            raise BalanceError(
                f"{reaction.id}: {atom} {left[atom]} in, {right[atom]} out"
            )


@dataclass(frozen=True)
class Row:
    """One directed solver row: a reaction, or one direction of a reversible."""

    id: str
    reaction: str
    label: str
    gene: str
    base_rate: float
    reverse: bool
    exchange: bool


class Network:
    """Immutable once built. Everything downstream reads it, nothing edits it."""

    def __init__(self) -> None:
        self.metabolites = list(met_data.METABOLITES)
        self.m_index = {m.id: i for i, m in enumerate(self.metabolites)}
        self.genes = list(gene_data.GENES)
        self.g_index = {g.id: i for i, g in enumerate(self.genes)}

        for reaction in rxn_data.REACTIONS:
            check_balance(reaction)

        self.rows: list[Row] = []
        internal, exchange = [], []
        for r in rxn_data.INTERNAL:
            internal.append((r, False))
            if r.reversible:
                internal.append((r, True))
        for r in rxn_data.EXCHANGE:
            exchange.append((r, False))

        n_m = len(self.metabolites)
        n_int = len(internal)
        n_exc = len(exchange)

        self.s_in = np.zeros((n_int, n_m))
        self.s_out = np.zeros((n_int, n_m))
        self.base_rate = np.zeros(n_int)
        self.row_gene = np.zeros(n_int, dtype=np.int64)

        for i, (r, rev) in enumerate(internal):
            inputs, outputs = (r.outputs, r.inputs) if rev else (r.inputs, r.outputs)
            for mid, n in inputs.items():
                self.s_in[i, self.m_index[mid]] += n
            for mid, n in outputs.items():
                self.s_out[i, self.m_index[mid]] += n
            self.base_rate[i] = r.base_rate * (r.reverse_ratio if rev else 1.0)
            self.row_gene[i] = self.g_index[r.enzyme]
            self.rows.append(Row(
                id=f"{r.id}_rev" if rev else r.id, reaction=r.id,
                label=("\u2190 " if rev else "") + r.label, gene=r.enzyme,
                base_rate=self.base_rate[i], reverse=rev, exchange=False,
            ))

        self.s_net = self.s_out - self.s_in

        # exchange rows: one metabolite each, permeability only -- no direction,
        # because the gradient decides which way the material actually goes.
        self.x_metabolite = np.zeros(n_exc, dtype=np.int64)
        self.x_base_rate = np.zeros(n_exc)
        self.x_gene = np.zeros(n_exc, dtype=np.int64)
        for i, (r, _) in enumerate(exchange):
            mid = next(iter(r.inputs))
            self.x_metabolite[i] = self.m_index[mid]
            self.x_base_rate[i] = r.base_rate
            self.x_gene[i] = self.g_index[r.enzyme]
            self.rows.append(Row(
                id=r.id, reaction=r.id, label=r.label, gene=r.enzyme,
                base_rate=r.base_rate, reverse=False, exchange=True,
            ))

        # per-metabolite properties
        self.cap = np.array([m.cap for m in self.metabolites])
        self.km = np.array([m.km for m in self.metabolites])
        self.buffered = np.array([m.buffered for m in self.metabolites])
        self.atoms, self.atom_names = self._atom_matrix()

        # masks the solver leans on every tick
        self.mask_in = (self.s_in > 0) & ~self.buffered[None, :]
        self.mask_out = (self.s_out > 0) & ~self.buffered[None, :]

        self.is_reverse = np.array([r.reverse for r in self.rows[:n_int]])
        self.baseline = np.array([g.baseline for g in self.genes])
        self.markable = np.array([g.markable for g in self.genes])

    # -- shapes -----------------------------------------------------------
    @property
    def n_metabolites(self) -> int:
        return len(self.metabolites)

    @property
    def n_internal(self) -> int:
        return self.s_in.shape[0]

    @property
    def n_exchange(self) -> int:
        return self.x_metabolite.shape[0]

    @property
    def n_genes(self) -> int:
        return len(self.genes)

    def _atom_matrix(self) -> tuple[np.ndarray, list[str]]:
        names = sorted({a for m in self.metabolites for a in m.atoms})
        table = np.zeros((len(self.metabolites), len(names)))
        for i, m in enumerate(self.metabolites):
            for j, a in enumerate(names):
                table[i, j] = m.atoms.get(a, 0)
        return table, names

    # -- lookups ----------------------------------------------------------
    def mi(self, mid: str) -> int:
        return self.m_index[mid]

    def gi(self, gid: str) -> int:
        return self.g_index[gid]

    def ri(self, row_id: str) -> int:
        for i, row in enumerate(self.rows):
            if row.id == row_id:
                return i
        raise KeyError(row_id)


_NETWORK: Network | None = None


def network() -> Network:
    """The one network. Built once, shared, never mutated."""
    global _NETWORK
    if _NETWORK is None:
        _NETWORK = Network()
    return _NETWORK
