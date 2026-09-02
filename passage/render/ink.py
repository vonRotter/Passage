"""The rendering primitives. Six functions, and the whole style lives in them.

The conceit is that the game is an anatomical plate and the player annotates
it: warm paper, confident ink, restrained watercolour, leader lines out to
handwritten notes in the margin. Nothing here draws anything the game knows
about -- these are materials, and ``plate.py`` is what uses them.

Two rules that everything else depends on:

**Jitter is seeded from a thing's identity, never from time.** A line asked for
twice with the same seed comes back identical. Seed from the clock instead and
the whole plate crawls, which is the single most obvious way to make drawn
linework look cheap.

**The plate is cached.** Paper, vessels, printed labels and the fixed network
are rendered once to a surface and blitted whole. Only pool washes and the
flow animation are per-frame work. If the plate is being re-inked every frame,
that is a bug.
"""

from __future__ import annotations

import math
import zlib
from functools import lru_cache

import numpy as np
import pygame

from . import palette

Point = tuple[float, float]
RGB = tuple[int, int, int]


# ---------------------------------------------------------------------------
# numpy helpers: noise and blur, which the paper and the washes are built from
# ---------------------------------------------------------------------------

def box_blur(field: np.ndarray, radius: int, passes: int = 2) -> np.ndarray:
    """Separable box blur by running sums. Two passes read as Gaussian enough.

    Fast enough to run on every wash every frame, which is the constraint that
    ruled out anything more principled.
    """
    if radius < 1:
        return field
    out = field.astype(np.float32)
    for _ in range(passes):
        for axis in (0, 1):
            n = out.shape[axis]
            r = min(radius, max(1, n // 2))
            pad = [(0, 0), (0, 0)]
            pad[axis] = (r, r)
            padded = np.pad(out, pad, mode="edge")
            csum = np.cumsum(padded, axis=axis)
            zero = np.zeros_like(np.take(csum, [0], axis=axis))
            csum = np.concatenate([zero, csum], axis=axis)
            lo = np.take(csum, np.arange(0, n), axis=axis)
            hi = np.take(csum, np.arange(2 * r + 1, n + 2 * r + 1), axis=axis)
            out = (hi - lo) / (2 * r + 1)
    return out


def value_noise(shape: tuple[int, int], scale: float, rng: np.random.Generator,
                octaves: int = 1) -> np.ndarray:
    """Smooth noise in 0..1, by upsampling a coarse random grid.

    Bilinear rather than anything cleverer. At the sizes the paper and the
    washes use, the difference is not visible and the cost difference is.
    """
    h, w = shape
    total = np.zeros((h, w), dtype=np.float32)
    amplitude, weight = 1.0, 0.0
    for octave in range(octaves):
        s = max(2.0, scale / (2 ** octave))
        gh, gw = max(2, int(h / s) + 2), max(2, int(w / s) + 2)
        grid = rng.random((gh, gw)).astype(np.float32)
        ys = np.linspace(0, gh - 1, h, dtype=np.float32)
        xs = np.linspace(0, gw - 1, w, dtype=np.float32)
        y0 = np.clip(ys.astype(np.int32), 0, gh - 2)
        x0 = np.clip(xs.astype(np.int32), 0, gw - 2)
        fy = (ys - y0)[:, None]
        fx = (xs - x0)[None, :]
        fy = fy * fy * (3 - 2 * fy)          # smoothstep, or the grid shows
        fx = fx * fx * (3 - 2 * fx)
        g00 = grid[np.ix_(y0, x0)]
        g01 = grid[np.ix_(y0, x0 + 1)]
        g10 = grid[np.ix_(y0 + 1, x0)]
        g11 = grid[np.ix_(y0 + 1, x0 + 1)]
        top = g00 + (g01 - g00) * fx
        bot = g10 + (g11 - g10) * fx
        total += amplitude * (top + (bot - top) * fy)
        weight += amplitude
        amplitude *= 0.5
    return total / weight


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed & 0xFFFFFFFF)


def seed_of(name: str, salt: int = 0) -> int:
    """A stable seed from a thing's name.

    Not ``hash()``: Python randomises string hashing per process, so a plate
    seeded that way would be re-drawn differently on every launch. The player is
    meant to learn one page and keep it.
    """
    return (zlib.crc32(name.encode("utf-8")) + salt * 2654435761) & 0xFFFFFFFF


# ---------------------------------------------------------------------------
# 3.1 paper
# ---------------------------------------------------------------------------

@lru_cache(maxsize=4)
def paper(size: tuple[int, int], seed: int = 0) -> pygame.Surface:
    """Warm cream base from layered noise. Generated once, cached, blitted.

    Four layers, in the order they matter: coarse fibre, fine grain, darkening
    toward the edges, and a handful of foxing stains. None of them is strong on
    its own; the effect is entirely in the stack.
    """
    w, h = size
    rng = _rng(seed)
    base = np.array(palette.PAPER, dtype=np.float32)
    edge = np.array(palette.PAPER_EDGE, dtype=np.float32)

    fibre = value_noise((h, w), 34.0, rng, octaves=3)
    grain = box_blur(rng.random((h, w)).astype(np.float32), 1, passes=1)
    tone = 1.0 + (fibre - 0.5) * 0.075 + (grain - 0.5) * 0.045

    # edge darkening: a soft frame, stronger in the corners
    ys = np.linspace(-1.0, 1.0, h, dtype=np.float32)[:, None]
    xs = np.linspace(-1.0, 1.0, w, dtype=np.float32)[None, :]
    vignette = np.clip((np.abs(xs) ** 4 + np.abs(ys) ** 4) * 0.62, 0.0, 1.0)
    vignette = vignette * (0.55 + 0.8 * value_noise((h, w), 70.0, rng, octaves=2))

    field = base[None, None, :] * tone[:, :, None]
    field = field + (edge - base)[None, None, :] * np.clip(vignette, 0, 1)[:, :, None]

    # foxing: four or five irregular stains, placed per seed
    for _ in range(int(rng.integers(5, 8))):
        cx, cy = rng.uniform(0.04, 0.96) * w, rng.uniform(0.04, 0.96) * h
        radius = rng.uniform(min(w, h) * 0.012, min(w, h) * 0.045)
        y0, y1 = int(max(0, cy - radius * 2)), int(min(h, cy + radius * 2))
        x0, x1 = int(max(0, cx - radius * 2)), int(min(w, cx + radius * 2))
        if y1 - y0 < 4 or x1 - x0 < 4:
            continue
        sub = (y1 - y0, x1 - x0)
        gy = (np.arange(y0, y1, dtype=np.float32)[:, None] - cy) / radius
        gx = (np.arange(x0, x1, dtype=np.float32)[None, :] - cx) / radius
        dist = np.sqrt(gx * gx + gy * gy)
        wobble = value_noise(sub, radius * 0.5, rng, octaves=2)
        stain = np.clip(1.0 - dist / (0.35 + wobble * 1.0), 0.0, 1.0) ** 1.1
        stain = stain * (0.25 + 0.85 * value_noise(sub, radius * 0.3, rng, octaves=2))
        strength = rng.uniform(0.14, 0.34)
        tint = np.array(palette.FOXING, dtype=np.float32)
        patch = field[y0:y1, x0:x1]
        field[y0:y1, x0:x1] = patch + (tint[None, None, :] - patch) * \
            (stain * strength)[:, :, None]

    surface = pygame.Surface((w, h))
    pygame.surfarray.blit_array(surface, np.clip(field, 0, 255)
                                .astype(np.uint8).transpose(1, 0, 2))
    return surface


# ---------------------------------------------------------------------------
# 3.2 / 3.3 ink lines and curves
# ---------------------------------------------------------------------------

def _jitter(points: list[Point], amount: float, rng: np.random.Generator) -> list[Point]:
    """Push interior vertices sideways, perpendicular to the local direction."""
    if len(points) < 3:
        return list(points)
    out = [points[0]]
    for i in range(1, len(points) - 1):
        px, py = points[i - 1]
        nx, ny = points[i + 1]
        dx, dy = nx - px, ny - py
        length = math.hypot(dx, dy) or 1.0
        ox, oy = -dy / length, dx / length
        push = float(rng.normal(0.0, amount))
        out.append((points[i][0] + ox * push, points[i][1] + oy * push))
    out.append(points[-1])
    return out


def _subdivide(a: Point, b: Point, step: float = 9.0) -> list[Point]:
    length = math.hypot(b[0] - a[0], b[1] - a[1])
    n = max(2, int(length / step))
    return [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
            for i in range(n + 1)]


def spline(points: list[Point], step: float = 9.0) -> list[Point]:
    """Catmull-Rom through the given points. Vessels are curves, never lines."""
    if len(points) < 3:
        return _subdivide(points[0], points[-1], step)
    pts = [points[0]] + list(points) + [points[-1]]
    out: list[Point] = []
    for i in range(len(pts) - 3):
        p0, p1, p2, p3 = pts[i:i + 4]
        seg = max(2, int(math.hypot(p2[0] - p1[0], p2[1] - p1[1]) / step))
        for j in range(seg):
            t = j / seg
            t2, t3 = t * t, t * t * t
            out.append((
                0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
                0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3),
            ))
    out.append(points[-1])
    return out


def _stroke(surface: pygame.Surface, points: list[Point], colour: RGB,
            weight: float, seed: int, alpha: float = 1.0,
            jitter: float = 0.55, closed: bool = False,
            wetness: tuple[float, float] = (0.55, 0.9)) -> None:
    """Lay the same path down two or three times at slightly varied offset.

    That repetition is the whole trick. A single line, however wobbly, still
    reads as a computer drawing it; three near-misses read as a nib.
    """
    rng = _rng(seed)
    passes = max(2, int(round(weight * 1.6)))
    spread = max(0.45, weight * 0.5)

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    pad = int(weight * 2 + jitter * 4 + 4)
    x0, y0 = int(min(xs)) - pad, int(min(ys)) - pad
    x1, y1 = int(max(xs)) + pad, int(max(ys)) + pad
    w, h = max(1, x1 - x0), max(1, y1 - y0)
    if w > 4096 or h > 4096:
        return
    layer = pygame.Surface((w, h), pygame.SRCALPHA)

    for p in range(passes):
        offset = (p / max(1, passes - 1) - 0.5) * 2.0 * spread
        wobbled = _jitter(list(points), jitter, rng)
        shifted = [(x - x0 + offset * 0.7 + float(rng.normal(0, 0.18)),
                    y - y0 + offset * 0.7 + float(rng.normal(0, 0.18)))
                   for x, y in wobbled]
        shade = int(255 * alpha * rng.uniform(*wetness))
        pygame.draw.aalines(layer, (*colour, shade), closed, shifted)
    surface.blit(layer, (x0, y0))


def ink_line(surface: pygame.Surface, a: Point, b: Point, weight: float = 1.0,
             seed: int = 0, colour: RGB = palette.INK, alpha: float = 1.0) -> None:
    """A straight run, drawn by hand. Seeded from the line's identity."""
    _stroke(surface, _subdivide(a, b), colour, weight, seed, alpha)


def ink_curve(surface: pygame.Surface, points: list[Point], weight: float = 1.0,
              seed: int = 0, colour: RGB = palette.INK, alpha: float = 1.0,
              closed: bool = False) -> None:
    """The same treatment on a spline. Vessels and cell outlines are curves."""
    path = spline(list(points) + ([points[0]] if closed else []))
    _stroke(surface, path, colour, weight, seed, alpha, closed=closed)


# ---------------------------------------------------------------------------
# 3.4 wash -- the one that makes the style work
# ---------------------------------------------------------------------------

def make_wash(polygon: list[Point], colour: RGB, seed: int = 0,
              strength: float = 1.0, level: float = 1.0
              ) -> tuple[pygame.Surface, tuple[float, float]] | None:
    """A soft, uneven fill that does not quite meet the ink outline.

    Watercolour never registers exactly with the linework, and reproducing that
    small imprecision is most of what sells this style. Four things do the work,
    and removing any one of them makes it look digital again:

    * the fill is offset a pixel or two from where the outline is,
    * the edge is ragged, because noise is added before the mask is thresholded,
    * pigment pools at the edge and thins in the middle, as real washes do,
    * granulation, from a second noise field at a finer scale.

    ``level`` fills from the bottom, for a pool bar drawn as a wash rather than
    as a rectangle.
    """
    if level <= 0.001 or strength <= 0.001:
        return None
    rng = _rng(seed)
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    pad = 8
    x0, y0 = int(min(xs)) - pad, int(min(ys)) - pad
    x1, y1 = int(max(xs)) + pad, int(max(ys)) + pad
    w, h = max(2, x1 - x0), max(2, y1 - y0)
    if w > 2048 or h > 2048:
        return None

    stencil = pygame.Surface((w, h))
    stencil.fill((0, 0, 0))
    pygame.draw.polygon(stencil, (255, 255, 255),
                        [(x - x0, y - y0) for x, y in polygon])
    mask = (pygame.surfarray.array2d(stencil) & 0xFF).astype(np.float32).T / 255.0

    if level < 0.999:
        # fill from the bottom of the shape, with a slightly uneven meniscus
        top = min(ys) - y0
        bottom = max(ys) - y0
        line = bottom - (bottom - top) * level
        rows = np.arange(h, dtype=np.float32)[:, None]
        meniscus = (value_noise((1, w), 16.0, rng, octaves=2) - 0.5) * 7.0
        surface_of = line + meniscus
        mask = mask * np.clip((rows - surface_of) * 0.45 + 0.5, 0.0, 1.0)
        # pigment gathers along the meniscus, the way a drying wash does
        mask = mask * (1.0 + 0.9 * np.exp(-((rows - surface_of) / 3.5) ** 2))

    soft = box_blur(mask, 2, passes=2)

    # a ragged edge: noise goes in *before* the threshold, so the boundary is
    # broken rather than merely blurred
    rag = value_noise((h, w), 9.0, rng, octaves=2)
    body = np.clip((soft + (rag - 0.5) * 0.55 - 0.45) * 2.6, 0.0, 1.0)

    # pigment pools at the rim and thins in the middle. Subtracting a heavily
    # blurred copy of the shape from itself leaves exactly that band.
    reach = max(3, int(min(w, h) * 0.22))
    inner = box_blur(body, reach, passes=2)
    rim = np.clip((body - inner) * 1.35 + 0.42, 0.0, 1.0)

    # low-frequency blotching is what the eye actually reads as watercolour;
    # fine grain alone just looks like noise over a flat fill
    blotch = value_noise((h, w), max(6.0, min(w, h) * 0.42), rng, octaves=3)
    grain = 0.86 + 0.30 * value_noise((h, w), 3.5, rng)

    density = (0.52 + 0.62 * rim) * (0.55 + 0.90 * blotch) * grain
    alpha = np.clip(body * density * 0.42 * strength, 0.0, 1.0)

    rgba = np.empty((h, w, 4), dtype=np.uint8)
    rgba[:, :, 0] = colour[0]
    rgba[:, :, 1] = colour[1]
    rgba[:, :, 2] = colour[2]
    rgba[:, :, 3] = (alpha * 255).astype(np.uint8)

    layer = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.surfarray.blit_array(layer, rgba[:, :, :3].transpose(1, 0, 2))
    pygame.surfarray.pixels_alpha(layer)[:] = rgba[:, :, 3].T

    # never quite in register with the linework. This is not a tolerance to be
    # tightened -- the small misregistration is the point.
    drift = (float(rng.normal(0, 2.4)), float(rng.normal(0, 2.4)))
    return layer, (x0 + drift[0], y0 + drift[1])


def wash(surface: pygame.Surface, polygon: list[Point], colour: RGB,
         seed: int = 0, strength: float = 1.0, level: float = 1.0) -> None:
    """Lay a wash straight onto a surface. See :func:`make_wash`.

    Pool levels change every frame, so the plate caches the surfaces this
    returns and re-renders one only when its level has actually moved. Building
    a wash is several blurs over a small array -- cheap, but not free enough to
    do seventeen times at sixty hertz for nothing.
    """
    made = make_wash(polygon, colour, seed, strength, level)
    if made is not None:
        layer, at = made
        surface.blit(layer, at)


# ---------------------------------------------------------------------------
# 3.5 leader lines
# ---------------------------------------------------------------------------

def leader(surface: pygame.Surface, from_point: Point, to_margin: Point,
           seed: int = 0, colour: RGB = palette.INK, alpha: float = 0.8) -> None:
    """A thin ruled line from a feature out to the margin, ticked at the feature.

    This is how every annotation attaches, exactly as on the reference plate.
    Nothing in this game gets a floating tooltip.
    """
    rng = _rng(seed)
    fx, fy = from_point
    mx, my = to_margin
    dx, dy = mx - fx, my - fy
    length = math.hypot(dx, dy) or 1.0
    ox, oy = -dy / length, dx / length

    tick = 3.5
    ink_line(surface, (fx + ox * tick, fy + oy * tick),
             (fx - ox * tick, fy - oy * tick), 0.7, seed * 31 + 1, colour, alpha)

    # a shallow elbow, so the leader reads as ruled rather than as a vector
    elbow = (fx + dx * rng.uniform(0.55, 0.75), my)
    _stroke(surface, [from_point, elbow, to_margin], colour, 0.6,
            seed * 31 + 2, alpha, jitter=0.3)


# ---------------------------------------------------------------------------
# 3.6 the player's hand
# ---------------------------------------------------------------------------

def hand_mark(surface: pygame.Surface, kind: str, position: Point, seed: int = 0,
              size: float = 9.0, fade: float = 0.0,
              colour: RGB = palette.INK) -> None:
    """The player's handwriting: wobblier and darker than the plate beneath it.

    ``fade`` is the inheritance ladder. A mark placed this generation is fresh
    and wet; each generation of inheritance fades one step further, to a floor.
    A mark inherited from four generations back should look like something
    somebody else wrote a long time ago.
    """
    rng = _rng(seed)
    x, y = position
    shade = palette.fade(colour, min(fade, 0.72))
    alpha = 1.0 - min(fade, 0.72) * 0.5
    weight = 1.9 - min(fade, 0.72) * 1.0

    wet = (0.80 - fade * 0.25, 1.0 - fade * 0.25)

    if kind == "circle":
        # an overrun loop, because nobody closes a circle exactly
        start = rng.uniform(0, math.tau)
        sweep = math.tau + rng.uniform(0.2, 0.6)
        steps = 30
        pts = []
        for i in range(steps + 1):
            t = start + sweep * i / steps
            r = size * (1.0 + 0.11 * math.sin(t * 2.3 + seed)
                        + 0.06 * math.sin(t * 3.7 - seed))
            pts.append((x + math.cos(t) * r * 1.10, y + math.sin(t) * r))
        _stroke(surface, pts, shade, weight, seed * 17 + 3, alpha,
                jitter=0.9, wetness=wet)

    elif kind == "tick":
        _stroke(surface, [(x - size * 0.5, y),
                          (x - size * 0.12, y + size * 0.42),
                          (x + size * 0.6, y - size * 0.55)],
                shade, weight, seed * 17 + 4, alpha, jitter=0.5, wetness=wet)

    elif kind == "cross":
        s = size * 0.55
        _stroke(surface, [(x - s, y - s), (x + s, y + s)], shade, weight,
                seed * 17 + 5, alpha, jitter=0.5, wetness=wet)
        _stroke(surface, [(x + s, y - s), (x - s, y + s)], shade, weight,
                seed * 17 + 6, alpha, jitter=0.5, wetness=wet)

    elif kind == "underline":
        _stroke(surface, [(x - size, y), (x, y + rng.uniform(-0.8, 0.8)),
                          (x + size, y)], shade, weight, seed * 17 + 7,
                alpha, jitter=0.5, wetness=wet)

    else:
        raise ValueError(f"unknown hand mark: {kind!r}")


# ---------------------------------------------------------------------------
# shapes the plate is built from
# ---------------------------------------------------------------------------

def blob(centre: Point, radius: float, seed: int = 0, squash: float = 1.0,
         wobble: float = 0.12, steps: int = 30) -> list[Point]:
    """A soft rounded form. At this scale nothing has anatomy.

    Everything on the plate is one of these: cells are big ones, pools are small
    organelle-like ones. The style carries the sophistication; the shapes stay
    simple, and attempting detail is how this look gets ruined.
    """
    rng = _rng(seed)
    phase = rng.uniform(0, math.tau, 3)
    out = []
    for i in range(steps):
        t = math.tau * i / steps
        r = radius * (1.0
                      + wobble * math.sin(t * 2 + phase[0]) * 0.6
                      + wobble * math.sin(t * 3 + phase[1]) * 0.3
                      + wobble * math.sin(t * 5 + phase[2]) * 0.15)
        out.append((centre[0] + math.cos(t) * r, centre[1] + math.sin(t) * r * squash))
    return out
