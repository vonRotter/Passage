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
from .data.metabolites import Class, POOLED

#: Hand-written expression sets, for looking at the chemistry under load.
#: These are not the game -- the game is the player choosing them with marks
#: (M2). They exist so that M0 can be inspected without a mark system.
PROFILES: dict[str, dict[str, float]] = {
    "baseline": {},
    "aerobic": {
        "glut": 0.9, "pfk": 0.8, "gapdh": 0.9, "pdh": 0.8,
        "cs": 0.9, "ogdh": 0.9, "etc": 1.0, "pc": 0.5,
        "biosyn": 0.8, "aat": 0.6,
    },
    "tuned": {
        "glut": 1.0, "pfk": 0.9, "gapdh": 1.0, "pdh": 0.9,
        "cs": 0.8, "ogdh": 0.8, "etc": 1.0, "pc": 0.6, "aat": 0.9,
        "biosyn": 1.0, "ldh": 0.0, "fas": 0.0,
    },
    "fermenting": {
        "glut": 1.0, "pfk": 1.0, "gapdh": 1.0, "ldh": 1.0, "mct": 1.0,
        "etc": 0.05, "pdh": 0.05, "fbpase": 0.0,
    },
    "etc_silenced": {
        "glut": 0.9, "pfk": 0.8, "gapdh": 0.9, "pdh": 0.8,
        "cs": 0.9, "ogdh": 0.9, "etc": 0.0, "pc": 0.5, "biosyn": 0.8,
    },
}


def build(profile: str, seed: int) -> Flow:
    flow = Flow(n_cells=1, seed=seed)
    for gene, level in PROFILES[profile].items():
        flow.set_expression(gene, level)
    return flow


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


def run_window(profile: str, seed: int) -> int:
    """The game loop. Sim at a fixed 20 Hz, render at 60."""
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    import pygame

    from .render.flow_vis import FlowVis
    from .render.plate import Plate
    from .render import panel, roster
    from .debug import overlay

    pygame.init()
    screen = pygame.display.set_mode(tuning_window())
    pygame.display.set_caption("Passage")
    clock = pygame.time.Clock()

    flow = build(profile, seed)
    plate = Plate(seed=seed + 4)
    vis = FlowVis(plate)
    debug = overlay.Overlay()

    paused = False
    accumulator = 0.0
    elapsed = 0.0
    running = True
    while running:
        frame = clock.tick(tuning.RENDER_HZ) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_F3:
                    plate = Plate(seed=int(np.random.default_rng().integers(1 << 20)))
                    vis = FlowVis(plate)
                else:
                    debug.key(event.key)

        if not paused:
            accumulator += min(frame, 0.25)
            while accumulator >= tuning.DT:
                flow.step()
                accumulator -= tuning.DT
                elapsed += tuning.DT

        cell = Cell(flow, 0)
        screen.blit(plate.surface, (0, 0))
        vis.draw(screen, flow, cell, 0.0 if paused else frame)
        roster.draw(screen, [cell], 0)
        panel.draw(screen, flow, cell, paused, elapsed)
        debug.draw(screen, flow, cell, plate, clock.get_fps())
        pygame.display.flip()

    pygame.quit()
    return 0


def tuning_window():
    from .data.layout import WINDOW
    return WINDOW


def run_shot(profile: str, seed: int, ticks: int, path: str) -> int:
    """Render one frame of a settled run to a PNG and exit.

    The plate is the deliverable of this milestone, so being able to look at it
    without a display attached is not a convenience -- it is how the art
    direction gets checked at all on a machine with no screen.
    """
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame

    from .render.flow_vis import FlowVis
    from .render.plate import Plate
    from .render import panel, roster

    pygame.init()
    pygame.display.set_mode((1, 1))
    flow = build(profile, seed)
    for _ in range(ticks):
        flow.step()
    cell = Cell(flow, 0)
    plate = Plate(seed=seed + 4)
    vis = FlowVis(plate)
    screen = pygame.Surface(tuning_window())
    screen.blit(plate.surface, (0, 0))
    vis.draw(screen, flow, cell, 1 / 60)
    roster.draw(screen, [cell], 0)
    panel.draw(screen, flow, cell, False, ticks / tuning.TICK_HZ)
    pygame.image.save(screen, path)
    pygame.quit()
    print(f"wrote {path}")
    return 0


def run_headless(profile: str, seed: int, ticks: int, trace: bool) -> int:
    flow = build(profile, seed)
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

    print(f"\nprofile: {profile}   seed: {seed}")
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
    args = parser.parse_args(argv)

    if args.shot:
        return run_shot(args.profile, args.seed, args.ticks, args.shot)
    if args.headless:
        return run_headless(args.profile, args.seed, args.ticks, args.trace)
    return run_window(args.profile, args.seed)


if __name__ == "__main__":
    sys.exit(main())
