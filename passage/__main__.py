"""M0: the chemistry, headless.

Runs one cell for a stretch of ticks and prints what happened. There is no
window yet -- the rendering milestone is next -- and there deliberately is no
rendering code in the import path, so that the chemistry can be trusted before
anything is drawn on top of it.

    python -m passage                 # baseline expression, 10000 ticks
    python -m passage --profile tuned
    python -m passage --ticks 50000 --trace
"""

from __future__ import annotations

import argparse
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="passage", description=__doc__)
    parser.add_argument("--profile", default="baseline", choices=sorted(PROFILES))
    parser.add_argument("--ticks", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--trace", action="store_true",
                        help="print a line of pools every 5 simulated seconds")
    args = parser.parse_args(argv)

    flow = build(args.profile, args.seed)
    cell = Cell(flow, 0)
    watch = ["glucose", "g3p", "pyruvate", "acetyl", "oxaloacetate",
             "atp", "nadh", "lactate", "biomass"]

    if args.trace:
        print("      t  " + "".join(m[:6].rjust(8) for m in watch))
    every = int(5 * tuning.TICK_HZ)
    for tick in range(args.ticks):
        if args.trace and tick % every == 0:
            print(f"  {tick / tuning.TICK_HZ:5.0f}s  "
                  + "".join(f"{cell.pool(m):8.2f}" for m in watch))
        flow.step()

    print(f"\nprofile: {args.profile}   seed: {args.seed}")
    print_pools(flow)
    print_rates(flow)
    print_ledger(flow)
    print(f"\n  {cell!r}  dominant={cell.dominant_class().value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
