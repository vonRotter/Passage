"""A0 acceptance: a page of primitives alone, and nothing else.

    python -m passage.debug.testpage [out.png]

The acceptance question is whether this looks like a page torn from an atlas
before a single real thing is drawn on it. If the washes read flat or digital,
that is the thing to fix, and fixing it comes before drawing anything real.
"""

from __future__ import annotations

import math
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from ..render import ink, palette

SIZE = (1280, 720)


def build(seed: int = 3) -> pygame.Surface:
    page = ink.paper(SIZE, seed).copy()
    font = pygame.font.Font("passage/data/chart.ttf", 13)
    small = pygame.font.Font("passage/data/chart.ttf", 11)

    def label(text, pos, colour=palette.INK, spacing=1.6, f=None):
        f = f or small
        x, y = pos
        for ch in text:
            glyph = f.render(ch, True, colour)
            page.blit(glyph, (x, y))
            x += glyph.get_width() + spacing

    label("PASSAGE  ·  PLATE I  ·  MATERIALS", (60, 44), palette.INK, 2.4, font)
    ink.ink_line(page, (60, 66), (1220, 66), 0.7, seed=101, alpha=0.55)

    # --- ink lines, at a range of weights ---------------------------------
    label("INK  LINE", (60, 92), palette.INK_FAINT)
    for i, weight in enumerate((0.6, 1.0, 1.6, 2.4, 3.2)):
        y = 118 + i * 17
        ink.ink_line(page, (60, y), (300, y), weight, seed=200 + i)

    # --- ink curves --------------------------------------------------------
    label("INK  CURVE  ·  VESSELS", (60, 218), palette.INK_FAINT)
    for i in range(4):
        pts = [(60 + j * 60, 268 + i * 26 + math.sin(j * 1.3 + i) * 15)
               for j in range(5)]
        ink.ink_curve(page, pts, 1.0 + i * 0.7, seed=300 + i)

    # --- the six class washes ---------------------------------------------
    label("WASH  ·  THE  SIX  CLASSES", (60, 392), palette.INK_FAINT)
    from ..data.metabolites import Class
    order = [Class.SUGARS, Class.LIPIDS, Class.AMINO_ACIDS,
             Class.ENERGY, Class.GASES, Class.WASTE]
    for i, cls in enumerate(order):
        cx, cy = 96 + i * 92, 462
        shape = ink.blob((cx, cy), 34, seed=400 + i, wobble=0.14)
        ink.wash(page, shape, palette.wash_for(cls), seed=400 + i)
        ink.ink_curve(page, shape, 1.1, seed=420 + i, closed=True)
        label(cls.value.upper().replace("_", " "), (cx - 30, cy + 44),
              palette.INK_FAINT, 1.2)

    # --- partial fills, which is how a pool reads --------------------------
    label("WASH  ·  LEVEL", (60, 546), palette.INK_FAINT)
    for i, level in enumerate((0.15, 0.35, 0.6, 0.85, 1.0)):
        cx, cy = 96 + i * 74, 612
        shape = ink.blob((cx, cy), 27, seed=500 + i, wobble=0.10)
        ink.wash(page, shape, palette.wash_for(Class.SUGARS),
                 seed=500 + i, level=level)
        ink.ink_curve(page, shape, 0.9 + level * 0.9, seed=520 + i, closed=True)
        label(f"{level:.0%}", (cx - 8, cy + 36), palette.INK_FAINT, 1.0)

    # --- the alarm colour, used for nothing else --------------------------
    shape = ink.blob((520, 612), 27, seed=560, wobble=0.16)
    ink.wash(page, shape, palette.ALARM, seed=560, strength=1.2)
    ink.ink_curve(page, shape, 1.4, seed=561, closed=True)
    label("SPILL", (498, 648), palette.INK_FAINT, 1.0)

    # --- leader lines out to the margin ------------------------------------
    label("LEADER", (660, 92), palette.INK_FAINT)
    feature = ink.blob((760, 190), 40, seed=600, wobble=0.15)
    ink.wash(page, feature, palette.wash_for(Class.ENERGY), seed=600)
    ink.ink_curve(page, feature, 1.3, seed=601, closed=True)
    for i, (angle, text) in enumerate((
            (-0.9, "energy carriers, arterial red"),
            (0.35, "the wash does not meet the line"),
            (1.4, "and it should not"))):
        px = 760 + math.cos(angle) * 42
        py = 190 + math.sin(angle) * 42
        ty = 150 + i * 46
        ink.leader(page, (px, py), (1024, ty), seed=610 + i)
        label(text, (1032, ty - 7), palette.PENCIL, 1.0)

    # --- the player's hand -------------------------------------------------
    label("HAND  MARK  ·  FRESH  TO  INHERITED", (660, 392), palette.INK_FAINT)
    kinds = ("circle", "tick", "cross", "underline")
    for row, kind in enumerate(kinds):
        label(kind.upper(), (660, 434 + row * 46), palette.INK_FAINT, 1.0)
        for col in range(5):
            ink.hand_mark(page, kind, (790 + col * 52, 438 + row * 46),
                          seed=700 + row * 10 + col, size=11.5,
                          fade=col * 0.18)
    label("this generation", (778, 622), palette.PENCIL, 1.0)
    label("four back", (990, 622), palette.PENCIL, 1.0)

    ink.ink_line(page, (60, 678), (1220, 678), 0.7, seed=999, alpha=0.55)
    label("A0  MATERIALS  ·  NOTHING  HERE  KNOWS  WHAT  THE  GAME  IS",
          (60, 690), palette.INK_FAINT, 1.6)
    return page


def main(argv: list[str]) -> int:
    pygame.init()
    pygame.display.set_mode((1, 1))
    out = argv[1] if len(argv) > 1 else "testpage.png"
    seed = int(argv[2]) if len(argv) > 2 else 3
    pygame.image.save(build(seed), out)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
