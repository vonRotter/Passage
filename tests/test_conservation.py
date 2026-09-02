"""Atoms are neither created nor destroyed over a long headless run.

Spec 5: over 100,000 ticks, total atoms in the system equal atoms supplied
minus atoms in waste, within tolerance. The ledger books four channels --
perfusion in, perfusion out, the buffered species, and spillover -- and the
residual of all of them together must stay at floating-point noise.
"""

import numpy as np
import pytest

from passage import tuning
from passage.__main__ import PROFILES, build
from passage.bio.flow import Flow


@pytest.mark.parametrize("profile", sorted(PROFILES))
def test_atoms_conserved_over_a_long_run(profile):
    flow = build(profile, seed=0)
    for _ in range(20_000):
        flow.step()
    residual = np.abs(flow.atom_residual())
    scale = max(flow.ledger.initial_atoms.sum(), 1.0)
    assert (residual / scale).max() < tuning.CONSERVATION_TOLERANCE, (
        f"{profile}: residual {residual} over {flow.ticks} ticks")


def test_atoms_conserved_over_one_hundred_thousand_ticks():
    flow = build("tuned", seed=0)
    for _ in range(100_000):
        flow.step()
    residual = np.abs(flow.atom_residual())
    scale = max(flow.ledger.initial_atoms.sum(), 1.0)
    assert (residual / scale).max() < tuning.CONSERVATION_TOLERANCE, residual


def test_no_pool_ever_goes_negative():
    flow = build("fermenting", seed=0)
    for _ in range(20_000):
        flow.step()
        assert (flow.pools >= -1e-9).all()
        assert (flow.medium >= -1e-9).all()


def test_no_pool_exceeds_its_cap():
    flow = build("fermenting", seed=0)
    net = flow.net
    for _ in range(20_000):
        flow.step()
        over = flow.pools - net.cap[None, :]
        assert (over[:, ~net.buffered] <= 1e-9).all()


def test_conserved_carrier_pairs_do_not_drift():
    """ATP+ADP and NADH+NAD are closed pools. If either total moves, some
    reaction is quietly minting or eating a carrier."""
    flow = build("tuned", seed=0)
    adenylate = flow.pool_of("atp") + flow.pool_of("adp")
    nicotinamide = flow.pool_of("nad") + flow.pool_of("nadh")
    for _ in range(20_000):
        flow.step()
    assert flow.pool_of("atp") + flow.pool_of("adp") == pytest.approx(adenylate, abs=1e-6)
    assert flow.pool_of("nad") + flow.pool_of("nadh") == pytest.approx(nicotinamide, abs=1e-6)


def test_spillover_is_booked_not_deleted():
    """Over-cap material leaves the cell but stays in the ledger, so waste can
    be charged for and the conservation sum still closes."""
    flow = Flow(n_cells=1, seed=0)
    net = flow.net
    flow.pools[0, net.mi("lactate")] = net.cap[net.mi("lactate")] * 2
    before = flow.atom_residual().copy()
    flow.step()
    assert flow.ledger.spilled[net.mi("lactate")] > 0
    assert np.abs(flow.atom_residual() - before).max() < 1e-6
