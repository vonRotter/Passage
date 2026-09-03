"""The same seed and the same input trace produce the same pools.

Spec 2 and spec 5. Without this the invalidation cycle cannot be tuned, a
replay cannot be trusted, and no failure a player reports can be reproduced.
"""

import numpy as np

from passage.__main__ import build
from passage.bio.flow import Flow


def trace_run(seed: int, ticks: int = 50_000):
    """A run with marks applied partway through, as a player would."""
    flow, marks, _ = build("respiring", seed=seed)
    schedule = {5_000: ("etc", 0.0), 12_000: ("ldh", 1.0),
                25_000: ("etc", 1.0), 33_000: ("pfk", 0.2)}
    for tick in range(ticks):
        if tick in schedule:
            flow.set_expression(*schedule[tick])
        flow.step()
    return flow


def test_identical_pools_after_fifty_thousand_ticks():
    a, b = trace_run(7), trace_run(7)
    assert np.array_equal(a.pools, b.pools)
    assert np.array_equal(a.medium, b.medium)
    assert np.array_equal(a.enzyme, b.enzyme)


def test_ledger_is_reproduced_too():
    a, b = trace_run(7, ticks=10_000), trace_run(7, ticks=10_000)
    assert np.array_equal(a.ledger.supplied, b.ledger.supplied)
    assert np.array_equal(a.ledger.spilled, b.ledger.spilled)
    assert np.array_equal(a.ledger.buffer_net, b.ledger.buffer_net)


def test_a_different_input_trace_diverges():
    """Guards against the run being deterministic for the boring reason that
    nothing in it responds to input at all."""
    plain, _, _ = build("respiring", seed=7)
    for _ in range(20_000):
        plain.step()
    marked, _, _ = build("respiring", seed=7)
    for tick in range(20_000):
        if tick == 5_000:
            marked.set_expression("etc", 0.0)
        marked.step()
    assert not np.allclose(plain.pools, marked.pools)


def test_identical_cells_stay_identical():
    """Four cells starting alike must remain alike. The solver is one matrix
    operation over every cell at once, and this is what catches an index that
    couples them through anything but the medium they actually share."""
    quad = Flow(n_cells=4, seed=0)
    quad.feed *= 4.0
    for _ in range(2_000):
        quad.step()
    for i in range(1, 4):
        assert np.array_equal(quad.pools[0], quad.pools[i])
