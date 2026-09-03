"""Window, loop, pause, time control.

    python -m passage                          # the plate
    python -m passage --profile fermenting     # start from a given expression set
    python -m passage --headless --ticks 50000 --trace

Flow runs at a fixed 20 Hz and rendering at 60 (spec 2). Chemistry does not need
sixty hertz and the extra headroom goes to legibility. The simulation steps on
an accumulator, so a slow frame costs frames rather than silently changing the
chemistry.

The player may pause at any time, indefinitely, and the plate stays live under
the pause -- the flow marks stop, because a stalled vessel must look stalled,
but everything remains readable.

``--headless`` keeps the M0 runner: one cell, no rendering, pools printed at the
end. It imports nothing from ``render`` and is the path the chemistry tests use.
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

from . import tuning
from .bio.cell import Cell
from .bio.flow import Flow
from .bio.marks import Kind, Marks
from .data.metabolites import Class, POOLED

#: Opening books: mark sets a player could actually place, within the budget of
#: eight. They are not the game -- the game is choosing them -- but they let a
#: run start from somewhere other than a blank page, and they keep the headless
#: numbers honest, because an illegal configuration would flatter the chemistry
#: with a spread no player could reach.
PROFILES: dict[str, list[tuple[str, str]]] = {
    "baseline": [],
    "respiring": [("glut", "+"), ("pfk", "+"), ("gapdh", "+"), ("pdh", "+"),
                  ("cs", "+"), ("ogdh", "+"), ("etc", "+"), ("biosyn", "+")],
    "growing":   [("glut", "+"), ("gapdh", "+"), ("pdh", "+"), ("cs", "+"),
                  ("ogdh", "+"), ("etc", "+"), ("biosyn", "+"), ("aat", "+")],
    # A working fermenter has to spend three of its eight marks *switching
    # things off*: leave the cycle running and it burns NAD+ that nothing can
    # reoxidise, and the cell suffocates on its own reducing power.
    "fermenting": [("glut", "+"), ("pfk", "+"), ("gapdh", "+"), ("ldh", "+"),
                   ("mct", "+"), ("biosyn", "+"), ("cs", "-"), ("ogdh", "-")],
    "starved":   [("etc", "-")],
}


def build(profile: str, seed: int) -> tuple[Flow, Marks]:
    """A cell, and the marks on it. Everything downstream reads both."""
    flow = Flow(n_cells=1, seed=seed)
    marks = Marks(flow, 0)
    for gene, sign in PROFILES[profile]:
        marks.place(gene, Kind.ACTIVATING if sign == "+" else Kind.SILENCING)
    flow.settle()
    return flow, marks


def print_pools(flow: Flow) -> None:
    cell = Cell(flow, 0)
    print(f"\n  pools after {flow.ticks} ticks ({flow.ticks / tuning.TICK_HZ:.0f} s)")
    for cls in Class:
        if cls is Class.BUFFER:
            continue
        members = [m for m in POOLED if m.cls is cls]
        if not members:
            continue
        print(f"    {cls.value:<12}", end="")
        print("  ".join(f"{m.id}={cell.pool(m.id):6.2f}[{cell.fill(m.id):4.0%}]"
                        for m in members))


def print_rates(flow: Flow) -> None:
    print("\n  rates (per second, cell 0)")
    for row in flow.net.rows:
        rate = flow.rate_of(row.id)
        if abs(rate) < 1e-3:
            continue
        print(f"    {row.id:<22} {rate:8.3f}   {row.label}")


def print_ledger(flow: Flow) -> None:
    net = flow.net
    supplied = flow.ledger.supplied
    print("\n  ledger")
    print(f"    glucose supplied      {supplied[net.mi('glucose')]:9.2f}")
    print(f"    biomass made          {flow.pools[:, net.mi('biomass')].sum():9.2f}")
    print(f"    spilled (waste)       {flow.ledger.spilled.sum():9.2f}")
    residual = np.abs(flow.atom_residual()).max()
    print(f"    atom residual         {residual:9.2e}   "
          f"({'balanced' if residual < 1e-6 else 'BROKEN'})")


KEY_HELP = """
    space   pause and unpause; the player may act while paused
    f1      numeric rates on every vessel
    f2      live mass-balance residual
    f3      reseed the paper and the linework
    f4      frame and tick timing
"""


def run_window(profile: str, seed: int, silent: bool = False) -> int:
    """The game loop. Sim at a fixed 20 Hz, render at 60."""
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    import pygame

    from .render.flow_vis import FlowVis
    from .render.plate import Plate
    from .render import interact, margin, panel, reference, roster
    from .bio.diagnose import Diagnostician
    from .bio.marks import Kind
    from .debug import overlay
    from .sound import Sound

    audio = Sound(enabled=not silent)
    pygame.init()
    screen = pygame.display.set_mode(tuning_window())
    pygame.display.set_caption("Passage")
    clock = pygame.time.Clock()

    flow, marks = build(profile, seed)
    plate = Plate(seed=seed + 4)
    vis = FlowVis(plate)
    debug = overlay.Overlay()
    doctor = Diagnostician(flow.net)
    hand = margin.RegisterHand(flow.net)
    appendix = reference.Reference(flow.net, seed=seed + 9)

    hover: interact.Target | None = None
    pinned: interact.Target | None = None
    reference_open = False
    paused = False
    accumulator = 0.0
    elapsed = 0.0
    running = True
    while running:
        frame = clock.tick(tuning.RENDER_HZ) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEMOTION:
                hover = interact.at(event.pos, flow.net, plate.vessel_path)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                target = interact.at(event.pos, flow.net, plate.vessel_path)
                if target is None:
                    pinned = None
                elif target.kind == "gene" and event.button in (1, 3):
                    kind = Kind.ACTIVATING if event.button == 1 else Kind.SILENCING
                    if marks.toggle(target.id, kind):
                        audio.scratch()
                    pinned = target
                else:
                    pinned = None if pinned == target else target
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_TAB:
                    reference_open = not reference_open
                elif reference_open and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    appendix.turn(1 if event.key == pygame.K_RIGHT else -1)
                elif event.key == pygame.K_g:
                    marks.advance_generation()
                elif event.key == pygame.K_F3:
                    plate = Plate(seed=int(np.random.default_rng().integers(1 << 20)))
                    vis = FlowVis(plate)
                else:
                    debug.key(event.key)

        if not paused:
            accumulator += min(frame, 0.25)
            while accumulator >= tuning.DT:
                flow.step()
                marks.update(tuning.DT)
                accumulator -= tuning.DT
                elapsed += tuning.DT

        cell = Cell(flow, 0)

        if reference_open:
            screen.blit(appendix.surface(), (0, 0))
            audio.update(frame)
            pygame.display.flip()
            continue

        # The hum is the game's most useful instrument: its pitch follows total
        # throughput, so the factory can be heard slowing before it is seen.
        # Under a pause it holds where it is rather than dropping to silence --
        # the lineage has not stopped, the clock has.
        if not paused:
            audio.set_throughput(flow.throughput())
            if cell.spilling():
                audio.sour()
        audio.update(frame)
        screen.blit(plate.surface, (0, 0))
        vis.draw(screen, flow, cell, 0.0 if paused else frame)
        hand.draw_debt(screen, marks)
        hand.draw(screen, marks)
        roster.draw(screen, [cell], 0)
        panel.draw(screen, flow, cell, paused, elapsed)
        margin.budget(screen, marks)

        # What the plate has to say, out on a leader line into the margin.
        # A pinned note stays put; otherwise the worst bottleneck speaks up on
        # its own, because a player should not have to go looking for the thing
        # that is wrong.
        showing = pinned or hover
        if showing is not None:
            row = (showing.id if showing.kind == "vessel"
                   else _row_for(flow.net, showing))
            if row:
                margin.annotate(screen, doctor.of(flow, marks, row, 0),
                                showing.anchor, seed=91)
        else:
            worst = doctor.bottlenecks(flow, marks, 0, 1)
            if worst:
                margin.annotate(screen, worst[0],
                                _anchor_for(plate, worst[0].row), seed=92)

        debug.draw(screen, flow, cell, plate, clock.get_fps())
        pygame.display.flip()

    audio.close()
    pygame.quit()
    return 0


def _row_for(net, target) -> str | None:
    """The reaction a pool or a gene is best explained through."""
    if target.kind == "vessel":
        return target.id
    if target.kind == "gene":
        for row in net.rows:
            if row.gene == target.id and not row.reverse:
                return row.id
        return None
    # a pool: the step that consumes it and is hurting most for it
    for row in net.rows:
        if row.reverse or row.exchange:
            continue
        if net.s_in[net.ri(row.id), net.mi(target.id)] > 0:
            return row.id
    return None


def _anchor_for(plate, row_id: str):
    path = plate.vessel_path(row_id)
    return path[len(path) // 2]


def tuning_window():
    from .data.layout import WINDOW
    return WINDOW


def run_shot(profile: str, seed: int, ticks: int, path: str,
             page: int | None = None) -> int:
    """Render one frame of a settled run to a PNG and exit.

    The plate is the deliverable of this milestone, so being able to look at it
    without a display attached is not a convenience -- it is how the art
    direction gets checked at all on a machine with no screen.
    """
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame

    from .render.flow_vis import FlowVis
    from .render.plate import Plate
    from .render import margin, panel, reference, roster
    from .bio.diagnose import Diagnostician

    pygame.init()
    pygame.display.set_mode((1, 1))
    flow, marks = build(profile, seed)
    for _ in range(ticks):
        flow.step()
        marks.update(tuning.DT)
    cell = Cell(flow, 0)
    plate = Plate(seed=seed + 4)
    vis = FlowVis(plate)
    screen = pygame.Surface(tuning_window())
    if page is not None:
        appendix = reference.Reference(flow.net, seed=seed + 9)
        appendix.page = page
        screen.blit(appendix.surface(), (0, 0))
    else:
        hand = margin.RegisterHand(flow.net)
        doctor = Diagnostician(flow.net)
        screen.blit(plate.surface, (0, 0))
        vis.draw(screen, flow, cell, 1 / 60)
        hand.draw_debt(screen, marks)
        hand.draw(screen, marks)
        roster.draw(screen, [cell], 0)
        panel.draw(screen, flow, cell, False, ticks / tuning.TICK_HZ)
        margin.budget(screen, marks)
        worst = doctor.bottlenecks(flow, marks, 0, 1)
        if worst:
            margin.annotate(screen, worst[0],
                            _anchor_for(plate, worst[0].row), seed=92)
    pygame.image.save(screen, path)
    pygame.quit()
    print(f"wrote {path}")
    return 0


def run_headless(profile: str, seed: int, ticks: int, trace: bool) -> int:
    flow, marks = build(profile, seed)
    cell = Cell(flow, 0)
    watch = ["glucose", "g3p", "pyruvate", "acetyl", "oxaloacetate",
             "atp", "nadh", "lactate", "biomass"]

    if trace:
        print("      t  " + "".join(m[:6].rjust(8) for m in watch))
    every = int(5 * tuning.TICK_HZ)
    for tick in range(ticks):
        if trace and tick % every == 0:
            print(f"  {tick / tuning.TICK_HZ:5.0f}s  "
                  + "".join(f"{cell.pool(m):8.2f}" for m in watch))
        flow.step()
        marks.update(tuning.DT)

    print(f"\nprofile: {profile}   seed: {seed}   "
          f"marks {marks.spent:.0f}/{marks.budget:.0f}")
    print_pools(flow)
    print_rates(flow)
    print_ledger(flow)
    print(f"\n  {cell!r}  dominant={cell.dominant_class().value}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="passage", description=__doc__)
    parser.add_argument("--profile", default="baseline", choices=sorted(PROFILES))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--headless", action="store_true",
                        help="no window: run the chemistry and print pools")
    parser.add_argument("--ticks", type=int, default=10_000,
                        help="headless only")
    parser.add_argument("--trace", action="store_true",
                        help="headless only: a line of pools every 5 seconds")
    parser.add_argument("--shot", metavar="PATH",
                        help="render one frame to a PNG and exit")
    parser.add_argument("--silent", action="store_true",
                        help="no audio, even where a device is available")
    parser.add_argument("--page", type=int, default=None,
                        help="with --shot: render a page of the reference instead")
    args = parser.parse_args(argv)

    if args.shot:
        return run_shot(args.profile, args.seed, args.ticks, args.shot,
                        args.page)
    if args.headless:
        return run_headless(args.profile, args.seed, args.ticks, args.trace)
    return run_window(args.profile, args.seed, args.silent)


if __name__ == "__main__":
    sys.exit(main())
