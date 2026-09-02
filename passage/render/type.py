"""Typography. One face, machine-set, and no handwriting font anywhere.

The player's hand is *drawn*, by ``ink.hand_mark``, not typed. The contrast
between the machine-set labels of the plate and the drawn annotation over it is
the entire point of the style, and a handwriting font would collapse it.

Plate labels are small, letter-spaced, sepia, printed. The gene register is
small and tabular. Margin annotations are the same face, smaller, in the pencil
tone. Numbers live in the side panel; the plate carries no numerals.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pygame

from . import palette

FACE = Path(__file__).resolve().parent.parent / "data" / "chart.ttf"


@lru_cache(maxsize=16)
def font(size: int) -> pygame.font.Font:
    return pygame.font.Font(str(FACE), size)


@lru_cache(maxsize=4096)
def _glyph(char: str, size: int, colour: tuple[int, int, int]) -> pygame.Surface:
    return font(size).render(char, True, colour)


def width(text: str, size: int, spacing: float = 0.0) -> float:
    f = font(size)
    return sum(f.size(c)[0] + spacing for c in text) - (spacing if text else 0)


def draw(surface: pygame.Surface, text: str, pos: tuple[float, float],
         size: int = 11, colour: tuple[int, int, int] = palette.INK,
         spacing: float = 0.0, align: str = "left") -> float:
    """Letter-spaced text. Spacing is what makes a label look set rather than typed."""
    x, y = pos
    if align == "centre":
        x -= width(text, size, spacing) / 2
    elif align == "right":
        x -= width(text, size, spacing)
    for char in text:
        glyph = _glyph(char, size, colour)
        surface.blit(glyph, (round(x), round(y)))
        x += glyph.get_width() + spacing
    return x


def caps(surface: pygame.Surface, text: str, pos: tuple[float, float],
         size: int = 10, colour: tuple[int, int, int] = palette.INK,
         spacing: float = 1.4, align: str = "left") -> float:
    """A plate label: small, letter-spaced, and set in capitals."""
    return draw(surface, text.upper(), pos, size, colour, spacing, align)
