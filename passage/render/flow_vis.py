"""The per-frame layer: pool washes, cell tint, and the flow animation.

This is the legibility gate the project lives or dies on (spec 3.11). Two of
the previous games failed because the player could not see what the system was
doing, and the requirement here is blunt: **the player must be able to see that
things are moving**, and a stalled vessel must be visibly still.

Two cues carry the rate, not one:

* **Density.** Marks along a vessel are spaced by throughput. A busy vessel is
  crowded; a slow one carries a mark or two; a stopped one is bare.
* **Speed.** Marks also travel more slowly on a slow vessel, so a bottleneck
  reads as a crawl and not merely as a gap.

Density alone matches the reference plate; speed alone matches the intuition a
Factorio player already has. Both together is what makes the bottleneck findable
by watching, which is the A1 acceptance test.
"""

from __future__ import annotations

import math

import numpy as np
import pygame

from ..bio.cell import Cell
from ..bio.flow import Flow
from ..data import layout
from ..data.metabolites import Class
from . import ink, palette
from .plate import Plate, arclength

#: How many marks a vessel carries per unit of rate, and how fast they travel.
#: Rates across the plate span two orders of magnitude -- basal upkeep runs at
#: 4.8 while anaplerosis trickles at 0.03 -- so density is taken on a
#: compressed scale. Linear density would show one crowded vessel and twenty
#: empty ones, which is a worse lie than no marks at all.
MARKS_PER_UNIT = 7.0
DENSITY_POWER = 0.55
MAX_MARKS = 14
MIN_SPACING = 15.0         # pixels; closer than this and marks read as hatching
BASE_SPEED = 30.0          # pixels per second at full pace
CRAWL = 0.28               # a slow vessel still crawls, at this share of pace
REFERENCE_RATE = 1.2       # the rate that counts as "full pace"
MARK_HALF = 3.4            # half-length of one mark, across the vessel
STALLED = 0.012            # below this a vessel carries nothing and is still

#: Pool levels are quantised before a wash is rebuilt. Finer than the eye can
#: see between frames, coarse enough that most frames rebuild nothing.
LEVEL_STEPS = 28


def mark_count(rate: float, path_length: float) -> int:
    """How many marks one vessel carries. Zero means stalled, and still.

    Split out from the drawing so a test can hold the visual contract directly:
    a stopped reaction shows nothing, a running one shows something, and a
    short vessel never fills up with hatching.
    """
    if abs(rate) < STALLED:
        return 0
    wanted = MARKS_PER_UNIT * abs(rate) ** DENSITY_POWER
    return min(MAX_MARKS, max(1, int(wanted + 0.5)),
               max(1, int(path_length / MIN_SPACING)))


class FlowVis:
    """Draws the living part of the plate. Owns the wash cache and the phases."""

    def __init__(self, plate: Plate) -> None:
        self.plate = plate
        self.net = plate.net
        self._wash_cache: dict[tuple, tuple[pygame.Surface, tuple[float, float]]] = {}
        self._phase: dict[str, float] = {}
        self._tint_cache: dict[tuple, tuple[pygame.Surface, tuple[float, float]]] = {}
        self._outline_cache: dict[str, tuple[pygame.Surface, tuple[int, int]]] = {}
        self._spill_cache: dict[str, tuple[pygame.Surface, tuple[float, float]]] = {}
        self.washes_built = 0
        self.inkings = 0

    # -- washes -------------------------------------------------------------
    def _pool_wash(self, mid: str, level: float, cls: Class, fade: float):
        bucket = int(round(min(1.0, max(0.0, level)) * LEVEL_STEPS))
        key = (mid, bucket, fade > 0.0)
        hit = self._wash_cache.get(key)
        if hit is None:
            x, y, r = layout.POOLS[mid]
            shape = ink.blob((x, y), r * 0.94, seed=ink.seed_of(mid, 3),
                             wobble=0.10)
            colour = palette.fade(palette.wash_for(cls), fade * 0.55)
            made = ink.make_wash(shape, colour, seed=ink.seed_of(mid, 5),
                                 strength=1.0, level=bucket / LEVEL_STEPS)
            if made is None:
                self._wash_cache[key] = None
                return None
            self._wash_cache[key] = hit = made
            self.washes_built += 1
        return hit

    def _cell_tint(self, colour: tuple[int, int, int], strength: float):
        bucket = int(round(strength * 6))
        key = (colour, bucket)
        hit = self._tint_cache.get(key)
        if hit is None and bucket > 0:
            centre, radius, squash = layout.CELL_ENVELOPE
            shape = ink.blob(centre, radius * 0.99, seed=21, squash=squash,
                             wobble=0.09, steps=52)
            # a whisper, not a fill. At this size the wash covers most of the
            # plate, and anything stronger drowns the paper and the linework.
            made = ink.make_wash(shape, colour, seed=61,
                                 strength=0.025 + bucket * 0.011)
            self._tint_cache[key] = hit = made
        return hit

    # -- the frame ----------------------------------------------------------
    def draw(self, target: pygame.Surface, flow: Flow, cell: Cell,
             dt: float) -> None:
        self._advance(flow, cell, dt)
        self._draw_tint(target, cell)
        self._draw_pools(target, cell)
        self._draw_marks(target, flow, cell)
        self._draw_spill(target, cell)

    def _advance(self, flow: Flow, cell: Cell, dt: float) -> None:
        """Move every vessel's marks along. Phase is the only mutable state."""
        for row_id in list(layout.VESSELS) + list(layout.EXCHANGE_STUBS):
            rate = abs(_rate(flow, cell, row_id))
            pace = CRAWL + (1.0 - CRAWL) * min(1.0, rate / REFERENCE_RATE)
            self._phase[row_id] = (self._phase.get(row_id, 0.0)
                                   + BASE_SPEED * pace * dt)

    def _draw_tint(self, target: pygame.Surface, cell: Cell) -> None:
        """The cell's overall cast: its story, before any number is read."""
        weights, strength = cell.cast()
        made = self._cell_tint(palette.blend(weights), strength)
        if made:
            layer, at = made
            target.blit(layer, at)

    def _draw_pools(self, target: pygame.Surface, cell: Cell) -> None:
        for mid in layout.POOLS:
            met = self.net.metabolites[self.net.mi(mid)]
            made = self._pool_wash(mid, cell.fill(mid), met.cls,
                                   self.plate.faded(mid))
            if made:
                layer, at = made
                target.blit(layer, at)
            # a pool near capacity thickens its outline; an empty one is bare paper
            if cell.fill(mid) > 0.86:
                layer, at = self._full_outline(mid)
                target.blit(layer, at)

    def _full_outline(self, mid: str):
        """The thickened outline of a saturated pool, inked once and kept.

        Re-inking a stroke every frame is the mistake the whole caching rule
        exists to prevent, and a pool sitting at its cap would do it sixty
        times a second.
        """
        hit = self._outline_cache.get(mid)
        if hit is None:
            x, y, r = layout.POOLS[mid]
            pad = 10
            side = int((r + pad) * 2)
            layer = pygame.Surface((side, side), pygame.SRCALPHA)
            shape = ink.blob((r + pad, r + pad), r, seed=ink.seed_of(mid, 3),
                             wobble=0.11)
            ink.ink_curve(layer, shape, 1.6, seed=ink.seed_of(mid, 31),
                          closed=True, alpha=0.8)
            self._outline_cache[mid] = hit = (layer, (int(x - r - pad),
                                                      int(y - r - pad)))
            self.inkings += 1
        return hit

    def _draw_marks(self, target: pygame.Surface, flow: Flow, cell: Cell) -> None:
        for row_id in list(layout.VESSELS) + list(layout.EXCHANGE_STUBS):
            rate = _rate(flow, cell, row_id)
            path = self.plate.vessel_path(row_id)
            lengths = arclength(path)
            total = float(lengths[-1]) or 1.0
            count = mark_count(rate, total)
            if count <= 0:
                continue                       # a stalled vessel is bare, and still
            phase = self._phase.get(row_id, 0.0)
            fade = self.plate.faded(row_id)
            colour = palette.fade(palette.INK, fade * 0.5)
            backwards = rate < 0
            for k in range(count):
                travel = (phase + k * total / count) % total
                if backwards:
                    travel = total - travel
                _tick(target, path, lengths, travel, colour, 0.85 - fade * 0.35)

    def _draw_spill(self, target: pygame.Surface, cell: Cell) -> None:
        """The alarm colour, and nothing else in the game ever uses it."""
        for met in cell.spilling():
            if met.id not in layout.POOLS:
                continue
            hit = self._spill_cache.get(met.id)
            if hit is None:
                x, y, r = layout.POOLS[met.id]
                shape = ink.blob((x, y), r * 1.22, seed=ink.seed_of(met.id, 7),
                                 wobble=0.2)
                hit = ink.make_wash(shape, palette.ALARM,
                                    seed=ink.seed_of(met.id, 71), strength=0.85)
                self._spill_cache[met.id] = hit
                self.inkings += 1
            if hit:
                layer, at = hit
                target.blit(layer, at)


def _rate(flow: Flow, cell: Cell, row_id: str) -> float:
    try:
        return flow.rate_of(row_id, cell.index)
    except KeyError:
        return 0.0


def _tick(surface: pygame.Surface, path: list[ink.Point], lengths: np.ndarray,
          travel: float, colour: tuple[int, int, int], alpha: float) -> None:
    """One flow mark: a short stroke across the vessel, at the given distance."""
    i = int(np.searchsorted(lengths, travel)) - 1
    i = max(0, min(len(path) - 2, i))
    span = lengths[i + 1] - lengths[i]
    t = 0.0 if span <= 0 else (travel - lengths[i]) / span
    ax, ay = path[i]
    bx, by = path[i + 1]
    x, y = ax + (bx - ax) * t, ay + (by - ay) * t
    dx, dy = bx - ax, by - ay
    length = math.hypot(dx, dy) or 1.0
    ox, oy = -dy / length * MARK_HALF, dx / length * MARK_HALF
    shade = (*colour, int(255 * alpha))
    # two offset strokes: one hairline is invisible against the linework, and
    # the player must be able to *see* that things are moving (spec 3.11)
    pygame.draw.line(surface, shade, (x - ox, y - oy), (x + ox, y + oy), 2)
    pygame.draw.aaline(surface, shade, (x - ox, y - oy), (x + ox, y + oy))
