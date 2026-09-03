"""A0 and A1: the materials, and the plate.

Three contracts are held here, and each one is a thing that went visibly wrong
while the renderer was being built:

* **The plate is inked once.** Paper, vessels, outlines and the register are
  cached and blitted. Re-inking a stroke every frame is the failure the whole
  caching rule exists to prevent (art direction 3, performance rule).
* **Nothing crawls.** Jitter is seeded from a thing's identity, never from time
  or from ``hash()``, which Python randomises per process. A plate that redrew
  itself differently each frame -- or each launch -- would look cheap and would
  defeat the point of a page the player is meant to learn permanently.
* **A stalled vessel is visibly still.** That stillness is the game's primary
  failure signal, so it is asserted rather than eyeballed.
"""

import os
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np
import pygame
import pytest

from passage.__main__ import build
from passage.bio.cell import Cell
from passage.bio.lineage import Lineage
from passage.bio.network import network
from passage.data import layout
from passage.render import flow_vis, ink, palette, panel, roster
from passage.render.flow_vis import FlowVis, mark_count
from passage.render.plate import Plate


@pytest.fixture(scope="module", autouse=True)
def display():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


@pytest.fixture(scope="module")
def settled():
    flow, marks, _ = build("growing", seed=0)
    for _ in range(6_000):
        flow.step()
    return flow


@pytest.fixture(scope="module")
def lineage(settled):
    """A lineage of one. The roster draws the tree, so it needs a real one."""
    return Lineage(settled, build("growing", seed=0)[1], seed=0)


# --- the layout ------------------------------------------------------------

def test_every_pooled_metabolite_is_placed():
    """Everything the player can affect is readable somewhere.

    Pooled metabolites are on the chart; the four conserved carriers are read
    in the margin instead, because a chart with an ATP box is a node graph."""
    net = network()
    for met in net.metabolites:
        if not met.buffered:
            assert met.id in layout.POOLS or met.id in layout.CARRIERS, \
                f"{met.id} has nowhere to be read"
    for mid in list(layout.POOLS) + list(layout.CARRIERS):
        assert mid in net.m_index, f"{mid} is drawn but is not a metabolite"
    assert not set(layout.POOLS) & set(layout.CARRIERS)


def test_every_reaction_has_a_vessel():
    net = network()
    for row in net.rows:
        if row.reverse:
            continue                      # both directions share one vessel
        where = layout.EXCHANGE_STUBS if row.exchange else layout.VESSELS
        assert row.id in where, f"{row.id} has no vessel"


def test_every_pool_sits_inside_the_cell_envelope():
    """Pools are organelles inside a cell. One drawn outside the membrane reads
    as a mistake, and exchange stubs are the only thing that crosses it."""
    for mid, (x, y, r) in layout.POOLS.items():
        edge = max(layout.envelope_depth(x + r * np.cos(t), y + r * np.sin(t))
                   for t in np.linspace(0.0, 2 * np.pi, 64))
        assert edge < 1.0, f"{mid} crosses the membrane ({edge:.2f})"


def test_the_chart_carries_the_conventions_that_make_it_biochemistry():
    """Cofactors on curved arrows, a compartment, and a ring.

    The first version of this page put ATP in a box beside the cell and drew
    every line at one weight, and it read as a node graph in period costume.
    Each of these is a convention a real chart uses to carry information, and
    losing one silently is the failure this test exists to catch.
    """
    # no carrier has a node; they ride the arrows that spend them
    for mid in layout.CARRIERS:
        assert mid not in layout.POOLS
    assert layout.COFACTORS, "no reaction carries a cofactor arc"
    for row_id in layout.COFACTORS:
        assert row_id in layout.VESSELS

    # the trunk outweighs the side reactions, or the page has no hierarchy
    assert layout.WEIGHTS["glycolysis_upper"] > layout.WEIGHTS["gluconeogenesis"]
    assert layout.WEIGHTS["pdh"] > layout.WEIGHTS["anaplerosis"]

    # the cycle's members are inside the compartment and the cytosol's are not
    (mx, my), radius, squash = layout.MITOCHONDRION

    def inside(mid):
        x, y, _ = layout.POOLS[mid]
        return ((x - mx) / radius) ** 2 + ((y - my) / (radius * squash)) ** 2 < 1.0

    for mid in ("acetyl", "akg", "oxaloacetate"):
        assert inside(mid), f"{mid} belongs in the mitochondrion"
    for mid in ("glucose", "g3p", "pyruvate", "lactate", "biomass"):
        assert not inside(mid), f"{mid} belongs in the cytosol"


def test_the_constitution_is_printed_on_the_plate():
    """The chart is the same chart every run; the inking is not.

    A weakened step is drawn thinner and broken. Without this the constitution
    exists only as a line of text in the margin, and the page a player with
    poor sugar handling learns is identical to everyone else's.
    """
    from passage.data import constitutions as con_data
    from passage.render.plate import Plate

    net = network()
    even = Plate(net, seed=3)
    assert even.constricted("glycolysis_upper") == 1.0

    poor = con_data.BY_ID["sugar_averse"]
    marked = Plate(net, seed=3, constitution=poor)
    assert marked.constricted("glycolysis_upper") < 0.92
    assert marked.constricted("pdh") == 1.0, "only the weak step is marked"

    # and the two pages are not the same page
    a = pygame.surfarray.array3d(even.surface).astype(np.int32)
    b = pygame.surfarray.array3d(marked.surface).astype(np.int32)
    assert np.abs(a - b).sum() > 0, "the constitution left no trace on the plate"


def test_pools_do_not_overlap():
    items = list(layout.POOLS.items())
    for i, (a, (ax, ay, ar)) in enumerate(items):
        for b, (bx, by, br) in items[i + 1:]:
            gap = np.hypot(ax - bx, ay - by) - (ar + br)
            assert gap > 0, f"{a} and {b} overlap"


# --- seeding ---------------------------------------------------------------

def test_seeds_are_stable_across_processes():
    """Not ``hash()``: string hashing is randomised per process, so a plate
    seeded that way would be inked differently on every launch."""
    assert ink.seed_of("glucose") == ink.seed_of("glucose")
    assert ink.seed_of("glucose") == 3467339417
    assert ink.seed_of("glucose", 3) != ink.seed_of("glucose", 4)


def test_paper_is_the_same_for_a_seed_and_different_between_seeds():
    a = pygame.surfarray.array3d(ink.paper((320, 200), 1))
    b = pygame.surfarray.array3d(ink.paper((320, 200), 1))
    c = pygame.surfarray.array3d(ink.paper((320, 200), 2))
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_an_ink_line_drawn_twice_is_identical():
    def once():
        surface = pygame.Surface((200, 60))
        surface.fill(palette.PAPER)
        ink.ink_line(surface, (10, 30), (190, 30), 1.4, seed=77)
        return pygame.surfarray.array3d(surface)
    assert np.array_equal(once(), once())


# --- the plate is cached ---------------------------------------------------

def test_the_plate_is_inked_once_and_never_again(settled, lineage):
    plate = Plate(seed=4)
    vis = FlowVis(plate)
    cell = Cell(settled, 0)
    screen = pygame.Surface(layout.WINDOW)
    for _ in range(180):
        screen.blit(plate.surface, (0, 0))
        vis.draw(screen, settled, cell, 1 / 60)
        roster.draw(screen, lineage, 0)
    assert plate.inkings == 1
    assert vis.inkings <= 4, "strokes are being re-inked inside the frame loop"


def test_the_wash_cache_settles(settled):
    plate = Plate(seed=4)
    vis = FlowVis(plate)
    cell = Cell(settled, 0)
    screen = pygame.Surface(layout.WINDOW)
    for _ in range(60):
        vis.draw(screen, settled, cell, 0.0)
    warm = vis.washes_built
    for _ in range(60):
        vis.draw(screen, settled, cell, 0.0)
    assert vis.washes_built == warm, "washes are being rebuilt for an unchanged state"


def test_nothing_crawls_between_frames(settled, lineage):
    """The same state, drawn twice, must give the same pixels."""
    plate = Plate(seed=4)
    cell = Cell(settled, 0)

    def frame():
        vis = FlowVis(plate)
        screen = pygame.Surface(layout.WINDOW)
        screen.blit(plate.surface, (0, 0))
        vis.draw(screen, settled, cell, 0.0)
        roster.draw(screen, lineage, 0)
        return pygame.surfarray.array3d(screen)

    assert np.array_equal(frame(), frame())


# --- the flow reads --------------------------------------------------------

def test_a_stalled_vessel_carries_nothing():
    assert mark_count(0.0, 200.0) == 0
    assert mark_count(flow_vis.STALLED / 2, 200.0) == 0


def test_a_running_vessel_carries_marks_and_a_busier_one_carries_more():
    assert mark_count(0.05, 200.0) >= 1
    assert mark_count(1.0, 200.0) > mark_count(0.1, 200.0)
    assert mark_count(4.8, 200.0) > mark_count(1.0, 200.0)


def test_a_short_vessel_does_not_fill_with_hatching():
    """Marks closer together than the spacing floor read as a ruler, not as flow."""
    for length in (20.0, 45.0, 90.0):
        assert mark_count(9.0, length) <= max(1, int(length / flow_vis.MIN_SPACING))


def test_density_is_compressed_not_linear():
    """Rates on the plate span two orders of magnitude. Linear density would
    show one crowded vessel and twenty empty ones."""
    ratio = mark_count(4.8, 400.0) / mark_count(0.05, 400.0)
    assert ratio < 4.8 / 0.05


# --- the alarm colour ------------------------------------------------------

def test_a_full_pool_is_not_spilling():
    """The alarm colour marks spillover and damage and nothing else. A charged
    adenylate pool or a saturated oxygen pool is a healthy cell."""
    flow, marks, _ = build("growing", seed=0)
    for _ in range(4_000):
        flow.step()
    cell = Cell(flow, 0)
    assert cell.fill("atp") > 0.9
    assert not any(m.id == "atp" for m in cell.spilling())


def test_material_actually_lost_is_spilling():
    flow, marks, _ = build("growing", seed=0)
    net = flow.net
    flow.pools[0, net.mi("lactate")] = net.cap[net.mi("lactate")] * 1.5
    flow.step()
    assert any(m.id == "lactate" for m in Cell(flow, 0).spilling())


# --- the budget ------------------------------------------------------------

def test_a_frame_fits_inside_sixty_hertz(settled, lineage):
    plate = Plate(seed=4)
    vis = FlowVis(plate)
    cell = Cell(settled, 0)
    screen = pygame.Surface(layout.WINDOW)

    def frame():
        settled.step()
        screen.blit(plate.surface, (0, 0))
        vis.draw(screen, settled, cell, 1 / 60)
        roster.draw(screen, lineage, 0)
        panel.draw(screen, settled, cell, False, 100.0)

    for _ in range(120):
        frame()
    start = time.perf_counter()
    for _ in range(180):
        frame()
    per_frame_ms = (time.perf_counter() - start) / 180 * 1000
    assert per_frame_ms < 16.6, f"{per_frame_ms:.2f} ms/frame at 60 Hz"
