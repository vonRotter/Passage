"""Every stated reason is checked against the state it was drawn from.

Spec 5: for every bottleneck the game highlights, the stated reason must be
correct -- the named metabolite genuinely scarce, or the named gene genuinely
silenced. **A wrong explanation is worse than no explanation**, because a player
who follows a false trail loses the one thing this design promises them: that a
present-day failure can be traced back to the decision that caused it.

So these tests do not check that the game says *something*. They take each
claim apart and hold it against the arrays the solver actually used.
"""

import numpy as np
import pytest

from passage import tuning
from passage.__main__ import PROFILES, build
from passage.bio.diagnose import FREELY, HEALTHY, Diagnostician
from passage.bio.marks import Kind


def settle(profile="growing", ticks=4_000, silence=None):
    flow, marks, _ = build(profile, seed=0)
    if silence:
        marks.lift(silence) if marks.of(silence) else None
        marks.place(silence, Kind.SILENCING)
    for _ in range(ticks):
        flow.step()
        marks.update(tuning.DT)
    return flow, marks, Diagnostician(flow.net)


@pytest.mark.parametrize("profile", sorted(PROFILES))
def test_every_reason_holds_against_the_solver(profile):
    """Walk every reaction in every profile and verify the claim it makes."""
    flow, marks, doctor = settle(profile)
    net = flow.net
    for row in net.rows:
        if row.reverse:
            continue
        reason = doctor.of(flow, marks, row.id, 0)
        i = net.ri(row.id)

        if reason.kind == "silenced":
            mark = marks.of(reason.gene)
            assert mark is not None and mark.kind is Kind.SILENCING, (
                f"{row.id}: claims {reason.gene} is silenced, but it is not")
            assert mark.generation == reason.generation
            assert flow.enzyme[0, net.gi(reason.gene)] < 0.5

        elif reason.kind == "starved":
            j = net.mi(reason.metabolite)
            assert net.mask_in[i, j], (
                f"{row.id}: claims to be starved of {reason.metabolite}, "
                f"which is not one of its inputs")
            # and it must be the *worst* of that reaction's inputs
            conc = flow.pools[0]
            mine = conc[j] / (net.km[j] + max(conc[j], 0.0))
            for k in np.flatnonzero(net.mask_in[i]):
                other = conc[k] / (net.km[k] + max(conc[k], 0.0))
                assert mine <= other + 1e-9, (
                    f"{row.id}: blames {reason.metabolite} but "
                    f"{net.metabolites[k].id} is scarcer")

        elif reason.kind == "backed_up":
            j = net.mi(reason.metabolite)
            assert net.mask_out[i, j], (
                f"{row.id}: claims to be backed up behind "
                f"{reason.metabolite}, which is not one of its products")
            fills = np.where(net.mask_out[i], flow.pools[0] / net.cap, -1.0)
            assert fills[j] == pytest.approx(fills.max()), (
                f"{row.id}: blames {reason.metabolite}, which is not the "
                f"fullest of its products")

        elif reason.kind == "fine":
            assert reason.share >= HEALTHY - 1e-9 or row.exchange


def test_a_silenced_gene_is_named_with_the_generation_it_was_placed_in():
    """The clause the whole design turns on (spec 3.11)."""
    flow, marks, _ = build("baseline", seed=0)
    marks.advance_generation()
    marks.advance_generation()
    assert marks.place("etc", Kind.SILENCING)
    for _ in range(3_000):
        flow.step()
        marks.update(tuning.DT)

    reason = Diagnostician(flow.net).of(flow, marks, "oxphos", 0)
    assert reason.kind == "silenced"
    assert reason.gene == "etc"
    assert reason.generation == 3
    assert "generation 3" in reason.detail


def test_the_amount_named_as_wanted_is_the_real_curve():
    """"Wants about nine" has to come from the same saturation curve the solver
    uses, or the number is decoration."""
    flow, marks, doctor = settle("baseline")
    net = flow.net
    for row in net.rows:
        reason = doctor.of(flow, marks, row.id, 0)
        if reason.kind != "starved" or reason.metabolite is None:
            continue
        j = net.mi(reason.metabolite)
        if not net.inhibits[j]:
            continue                      # carriers are explained as a ratio
        wants = float(net.km[j]) * FREELY / (1.0 - FREELY)
        assert f"{wants:.1f}" in reason.detail or f"{wants:.0f}" in reason.detail


def test_a_carrier_shortage_is_explained_as_a_ratio_not_a_supply():
    """Telling a player to make more ADP would be true and useless: ADP is what
    is left when ATP is spent."""
    flow, marks, doctor = settle("growing")
    net = flow.net
    found = False
    for row in net.rows:
        reason = doctor.of(flow, marks, row.id, 0)
        if reason.kind == "starved" and reason.metabolite in ("adp", "nad", "nadh", "atp"):
            found = True
            assert "closed pool" in reason.detail
            assert "not made" in reason.detail
    assert found, "no carrier shortage arose to check"


def test_bottlenecks_are_ordered_by_what_they_cost():
    flow, marks, doctor = settle("growing")
    found = doctor.bottlenecks(flow, marks, 0, limit=5)
    assert found == sorted(found, key=lambda r: -r.severity)
    assert all(r.is_bottleneck for r in found)


def test_a_healthy_reaction_is_not_called_a_bottleneck():
    flow, marks, doctor = settle("growing")
    for row in flow.net.rows:
        reason = doctor.of(flow, marks, row.id, 0)
        if reason.share >= HEALTHY and not row.exchange:
            assert not reason.is_bottleneck, row.id


def test_the_remedy_never_asks_for_a_mark_the_player_cannot_place():
    """Advice a player cannot act on is worse than none."""
    flow, marks, doctor = settle("growing")
    assert not marks.can_place(), "this profile should have spent its budget"
    for reason in doctor.bottlenecks(flow, marks, 0, limit=4):
        if "Activate " in reason.remedy:
            pytest.fail(f"tells a player with no budget to activate: "
                        f"{reason.remedy}")


def test_removing_a_mark_costs_more_than_placing_it_did():
    """Spec 3.3, and it must not be softened for convenience."""
    flow, marks, _ = build("baseline", seed=0)
    assert marks.place("etc", Kind.SILENCING)
    assert marks.free == pytest.approx(tuning.MARK_BUDGET - 1)
    marks.advance_generation()
    marks.advance_generation()
    marks.advance_generation()
    assert marks.lift("etc")
    # the slot came back, but the debt is larger than the mark ever cost
    assert marks.owed > 1.0
    assert marks.free < tuning.MARK_BUDGET - 1.0


def test_un_silencing_takes_longer_to_take_effect_than_silencing_did():
    flow, marks, _ = build("baseline", seed=0)
    net = flow.net
    marks.place("etc", Kind.SILENCING)
    assert flow.relax_scale[0, net.gi("etc")] == pytest.approx(1.0)
    marks.lift("etc")
    assert flow.relax_scale[0, net.gi("etc")] > 2.0
