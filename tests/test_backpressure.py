"""Blocking a reaction slows everything that feeds it, upstream, in order.

Spec 5, and spec 3.2: backpressure is the single most important piece of the
simulation, because it is how a problem three steps downstream becomes visible
at the top of the pathway. Without it a bottleneck is merely fatal instead of
findable, and the Factorio loop this game is built on does not exist.

Two shapes of propagation are tested separately, because they are genuinely
different and conflating them would make the test assert something false:

* **Positional.** Block a step and its own substrate backs up, which inhibits
  the step before it, and so on up the chain. This propagates strictly in
  order, and the test asserts that order.
* **Carrier-coupled.** Block the respiratory chain and NAD+ stops being
  regenerated, so *every* NAD-consuming step slows at once, wherever it sits
  on the plate. This is not positional and must not be asserted as if it were.
"""

import pytest

from passage.__main__ import build

BOUND_TICKS = 6_000          # 300 simulated seconds
#: The last hop -- glucose uptake -- is gradient-driven and so responds far
#: more slowly than the steps inside the cell. Roughly 200 s, measured.


def settled(profile="respiring", ticks=6_000):
    flow, marks = build(profile, seed=0)
    for _ in range(ticks):
        flow.step()
    return flow


def time_to_half(flow, rows, before, limit=BOUND_TICKS):
    """Seconds until each row drops below half the rate it ran at before."""
    hit: dict[str, float] = {}
    for tick in range(1, limit + 1):
        flow.step()
        for row in rows:
            if row not in hit and abs(flow.rate_of(row)) < 0.5 * abs(before[row]):
                hit[row] = tick / 20.0
        if len(hit) == len(rows):
            break
    return hit


def test_blocking_pdh_slows_glycolysis_in_positional_order():
    """PDH is the gate out of glycolysis and shares no carrier shortcut with
    the steps above it, so its blockage must travel strictly upstream."""
    flow = settled()
    chain = ["glycolysis_lower", "glycolysis_upper", "exchange_glucose"]
    before = {r: flow.rate_of(r) for r in chain}
    assert all(v > 1e-3 for v in before.values()), before

    pyruvate_before = flow.pool_of("pyruvate")
    flow.set_expression("pdh", 0.0)
    hit = time_to_half(flow, chain, before)

    assert flow.pool_of("pyruvate") > pyruvate_before, "the blocked substrate must back up"
    for row in chain:
        assert row in hit, f"{row} never slowed within {BOUND_TICKS} ticks"
    assert hit["glycolysis_lower"] <= hit["glycolysis_upper"] <= hit["exchange_glucose"], hit


def test_blocking_the_respiratory_chain_reduces_every_nad_consumer():
    """Silencing the terminal acceptor reduces NAD+, and every step that needs
    it slows -- including steps upstream of nothing in particular."""
    flow = settled()
    consumers = ["glycolysis_lower", "pdh", "tca_upper", "tca_lower"]
    before = {r: flow.rate_of(r) for r in consumers}
    assert all(v > 1e-3 for v in before.values()), before

    nadh_before = flow.pool_of("nadh")
    flow.set_expression("etc", 0.0)
    hit = time_to_half(flow, consumers, before)

    assert flow.pool_of("nadh") > nadh_before, "reducing equivalents must pile up"
    assert flow.pool_of("nad") < 1.0, "NAD+ must be nearly exhausted"
    for row in consumers:
        assert row in hit, f"{row} never slowed within {BOUND_TICKS} ticks"


def test_backpressure_reaches_the_cell_boundary():
    """The point of the whole mechanism: a stall deep in the plate eventually
    shows up as the cell no longer taking food in."""
    flow = settled()
    before = flow.rate_of("exchange_glucose")
    assert before > 1e-3
    flow.set_expression("gapdh", 0.0)
    for _ in range(BOUND_TICKS):
        flow.step()
    assert flow.rate_of("exchange_glucose") < 0.25 * before
    assert flow.pool_of("g3p") > 0.9 * flow.net.cap[flow.net.mi("g3p")], \
        "the metabolite immediately above the block must be the one that fills"


def test_relieving_a_block_restores_flow():
    """Backpressure has to be reversible, or a player who mis-silences a gene
    could never learn anything from putting it back."""
    flow = settled()
    before = flow.rate_of("glycolysis_lower")
    flow.set_expression("pdh", 0.0)
    for _ in range(BOUND_TICKS):
        flow.step()
    blocked = flow.rate_of("glycolysis_lower")
    assert blocked < 0.5 * before

    flow.set_expression("pdh", 0.9)
    for _ in range(BOUND_TICKS):
        flow.step()
    assert flow.rate_of("glycolysis_lower") > 2.0 * blocked


def test_nothing_responds_instantly():
    """Spec 3.3: enzyme level lags expression by seconds. A mark that took
    effect on the next tick would make regulation a switch, not a decision."""
    flow = settled()
    before = flow.rate_of("oxphos")
    flow.set_expression("etc", 0.0)
    flow.step()
    assert flow.rate_of("oxphos") > 0.9 * before, "expression must not bite immediately"
