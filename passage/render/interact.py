"""What the pointer is over, and what a click on it means.

Hit-testing only. It knows the plate's geometry and nothing about the game, so
that the input handling in ``__main__`` stays a few lines of dispatch rather
than a pile of rectangles.

The gene register is the one place a click *does* something: the player's marks
go directly onto the printed table, exactly as they would on a real plate. Left
button activates, right button silences, and the same button again lifts what
it placed -- which is the expensive direction, and says so.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..bio.network import Network
from ..data import layout

Point = tuple[float, float]

POOL_SLACK = 5.0            # how far outside a pool still counts as over it
VESSEL_SLACK = 7.0


@dataclass(frozen=True)
class Target:
    """Whatever the pointer is over. ``kind`` says which field to read."""

    kind: str               # "pool" | "vessel" | "gene" | None
    id: str
    anchor: Point           # where a leader line should leave from


def _near_polyline(pos: Point, path: list[Point]) -> float:
    x, y = pos
    best = 1e9
    for (ax, ay), (bx, by) in zip(path, path[1:]):
        dx, dy = bx - ax, by - ay
        span = dx * dx + dy * dy
        if span <= 1e-9:
            continue
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / span))
        best = min(best, math.hypot(x - (ax + dx * t), y - (ay + dy * t)))
    return best


def gene_rows(net: Network) -> dict[str, tuple[float, float, float, float]]:
    """The clickable rectangle of every gene's row in the printed register."""
    markable = [g for g in net.genes if g.markable]
    rows = (len(markable) + layout.REGISTER_COLUMNS - 1) // layout.REGISTER_COLUMNS
    width = layout.register_column_width()
    out = {}
    for n, gene in enumerate(markable):
        column, row = divmod(n, rows)
        gx, gy = layout.register_cell(row, column)
        out[gene.id] = (gx - 2, gy - 3, width - 16, layout.REGISTER_ROW_HEIGHT - 2)
    return out


def at(pos: Point, net: Network, paths) -> Target | None:
    """What is under the pointer, most specific first."""
    x, y = pos
    for gene, (rx, ry, rw, rh) in gene_rows(net).items():
        if rx <= x <= rx + rw and ry <= y <= ry + rh:
            return Target("gene", gene, (rx + rw, ry + rh / 2))

    for mid, (px, py, r) in layout.POOLS.items():
        if math.hypot(x - px, y - py) <= r + POOL_SLACK:
            return Target("pool", mid, layout.LEADER_ANCHORS.get(mid, (px + r, py)))

    best, best_d = None, VESSEL_SLACK
    for row_id in list(layout.VESSELS) + list(layout.EXCHANGE_STUBS):
        d = _near_polyline(pos, paths(row_id))
        if d < best_d:
            best, best_d = row_id, d
    if best is not None:
        path = paths(best)
        return Target("vessel", best, path[len(path) // 2])
    return None
