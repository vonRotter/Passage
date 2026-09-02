"""The solver stays inside its budget.

Spec 5: 20 cells x 22 reactions solved for 600 ticks in under 5 ms per tick.
The budget matters because the simulation runs at 20 Hz while rendering runs at
60, and every millisecond the chemistry takes is a millisecond the plate does
not get.
"""

import time

import pytest

from passage.bio.flow import Flow
from passage.bio.network import network

BUDGET_MS = 5.0
TICKS = 600


def test_twenty_cells_six_hundred_ticks_under_budget():
    flow = Flow(n_cells=20, seed=0)
    flow.feed *= 20.0
    for _ in range(50):                      # warm up, out of the measurement
        flow.step()

    start = time.perf_counter()
    for _ in range(TICKS):
        flow.step()
    per_tick_ms = (time.perf_counter() - start) / TICKS * 1000.0

    assert per_tick_ms < BUDGET_MS, f"{per_tick_ms:.2f} ms/tick, budget {BUDGET_MS}"


def test_the_network_is_the_size_the_spec_asks_for():
    """Spec 3.1 asks for roughly 22 reactions, small enough to hold in the head.

    The bound is deliberately loose; what it catches is the network quietly
    doubling while nobody is looking, which is how the plate becomes
    unreadable.
    """
    net = network()
    assert 16 <= len(net.rows) <= 28, len(net.rows)


def test_solving_scales_roughly_linearly_in_cells():
    """A guard against someone reintroducing a Python loop over reactions:
    that would show up as super-linear growth long before it showed up as a
    failed budget."""
    def timed(n_cells):
        flow = Flow(n_cells=n_cells, seed=0)
        flow.feed *= n_cells
        for _ in range(50):
            flow.step()
        start = time.perf_counter()
        for _ in range(300):
            flow.step()
        return time.perf_counter() - start

    one, twenty = timed(1), timed(20)
    assert twenty < one * 8.0, f"1 cell {one:.3f}s, 20 cells {twenty:.3f}s"
