"""Every reaction balances on atom count.

Spec 5: fail the build on any violation. A reaction that creates or destroys
matter would silently corrupt every yield and waste number in the game, and
those numbers are the entire score.
"""

from collections import Counter

import pytest

from passage.bio.network import BalanceError, atom_totals, check_balance, network
from passage.data import metabolites as met_data
from passage.data import reactions as rxn_data


@pytest.mark.parametrize("reaction", rxn_data.INTERNAL, ids=lambda r: r.id)
def test_reaction_balances(reaction):
    left, right = atom_totals(reaction.inputs), atom_totals(reaction.outputs)
    assert left == right, f"{reaction.id}: {dict(left)} in, {dict(right)} out"


def test_network_refuses_to_build_unbalanced():
    broken = rxn_data.Reaction(
        id="broken", label="matter from nothing",
        inputs={"glucose": 1}, outputs={"glucose": 2},
        enzyme="pfk", base_rate=1.0,
    )
    with pytest.raises(BalanceError):
        check_balance(broken)


def test_every_metabolite_carries_atoms():
    for m in met_data.METABOLITES:
        assert m.atoms, f"{m.id} has no atom count"
        assert all(n > 0 for n in m.atoms.values()), m.id


def test_every_reaction_names_known_species_and_gene():
    net = network()
    for r in rxn_data.REACTIONS:
        for mid in list(r.inputs) + list(r.outputs):
            assert mid in net.m_index, f"{r.id} names unknown metabolite {mid}"
        assert r.enzyme in net.g_index, f"{r.id} names unknown gene {r.enzyme}"


def test_exchange_rows_move_exactly_one_species():
    for r in rxn_data.EXCHANGE:
        assert list(r.inputs) == list(r.outputs), r.id
        assert len(r.inputs) == 1, r.id


def test_carrier_pairs_differ_only_by_the_moiety_they_carry():
    """ATP is ADP plus a phosphate; NADH is NAD plus two hydrogens.

    The rest of the table leans on this, and a typo in either formula would
    make every energy and redox reaction quietly unbalanced in the same
    direction, which is the hardest kind of error to spot in play.
    """
    atp, adp = met_data.BY_ID["atp"].atoms, met_data.BY_ID["adp"].atoms
    delta = Counter(atp) - Counter(adp)
    assert dict(delta) == {"H": 1, "O": 3, "P": 1}, dict(delta)

    nadh, nad = met_data.BY_ID["nadh"].atoms, met_data.BY_ID["nad"].atoms
    delta = Counter(nadh) - Counter(nad)
    assert dict(delta) == {"H": 2}, dict(delta)
