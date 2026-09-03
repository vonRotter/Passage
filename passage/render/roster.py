"""The left margin: the lineage tree, and the state of the selected cell.

The tree is hand-ruled in **pencil** rather than ink, because it is a record the
player is keeping rather than part of the printed plate. Each cell is a small
circle carrying its dominant class colour, so the shape of the lineage and the
health of it are one glance rather than two.

It is drawn as a record and not as a user interface. There are no buttons, no
panels and no rows -- just a ruled tree with the cells on it, the way somebody
would keep track on the margin of a page they were working from.

The tree is also the roster the spec asks for (3.11): every cell, what it is
mostly doing, its worst-off substance, and whether it is starving or spilling.
Those live under the tree for whichever cell is selected, because printing them
for ten cells at once would be a table, and a table is not a record.
"""

from __future__ import annotations

import pygame

from ..bio.cell import Cell
from ..bio.lineage import Lineage
from ..data import layout
from . import ink, palette, type as typo

TOP = 84
ROW = 30
ROW_MIN = 15
TREE_HEIGHT = 400          # the tree compresses rather than running off the page
INDENT = 30
LEFT = 26
NODE = 8

_STAMPS: dict[tuple, pygame.Surface] = {}
SIDE = 30


def _node(colour, strength: float, selected: bool, slot: int) -> pygame.Surface:
    """One cell on the tree, inked once per (colour, state) and kept."""
    key = (colour, round(strength, 2), selected, slot)
    stamp = _STAMPS.get(key)
    if stamp is None:
        stamp = pygame.Surface((SIDE, SIDE), pygame.SRCALPHA)
        shape = ink.blob((SIDE / 2, SIDE / 2), NODE, seed=900 + slot * 5,
                         wobble=0.16)
        ink.wash(stamp, shape, colour, seed=910 + slot * 5,
                 strength=0.4 + strength * 0.8)
        ink.ink_curve(stamp, shape, 1.4 if selected else 0.7, seed=920 + slot * 5,
                      closed=True, colour=palette.INK if selected else palette.PENCIL,
                      alpha=1.0 if selected else 0.6)
        _STAMPS[key] = stamp
    return stamp


def positions(lineage: Lineage) -> dict[int, tuple[float, float]]:
    """Where each cell sits on the tree: depth across, birth order down.

    The spacing shrinks as the lineage grows so the record stays on the page.
    A tree that ran off the bottom would be a worse record than a cramped one.
    """
    count = max(1, len(lineage.members))
    row_height = max(ROW_MIN, min(ROW, TREE_HEIGHT / count))
    depth_step = INDENT if row_height > 22 else INDENT * 0.7
    order: dict[int, tuple[float, float]] = {}
    for row, member in enumerate(lineage.members):
        depth = min(lineage.depth_of(member.index), 4)
        order[member.index] = (LEFT + depth * depth_step, TOP + row * row_height)
    return order


def node_at(pos: tuple[float, float], lineage: Lineage) -> int | None:
    x, y = pos
    for index, (nx, ny) in positions(lineage).items():
        if abs(x - nx) <= NODE + 5 and abs(y - ny) <= NODE + 5:
            return index
    return None


def draw(surface: pygame.Surface, lineage: Lineage, selected: int,
         warning: str = "") -> None:
    where = positions(lineage)

    # the branches first, in pencil, so the cells sit on top of them
    for member in lineage.members:
        if member.parent is None:
            continue
        px, py = where[member.parent]
        cx, cy = where[member.index]
        ink.ink_curve(surface, [(px, py + NODE), (px, (py + cy) / 2),
                                (px + 6, cy), (cx - NODE, cy)],
                      0.6, seed=940 + member.index, colour=palette.PENCIL,
                      alpha=0.75)

    for member in lineage.members:
        cell = Cell(lineage.flow, member.index)
        weights, strength = cell.cast()
        x, y = where[member.index]
        surface.blit(_node(palette.blend(weights), strength,
                           member.index == selected, member.index % 8),
                     (int(x - SIDE / 2), int(y - SIDE / 2)))
        if len(lineage.members) <= 16:
            typo.draw(surface, f"{member.index}", (x + NODE + 6, y - 7), 9,
                      palette.INK if member.index == selected else palette.PENCIL,
                      0.2)

    _selected_state(surface, lineage, selected, warning)


def _selected_state(surface: pygame.Surface, lineage: Lineage,
                    selected: int, warning: str = "") -> None:
    """What the spec's roster asks for, for the cell being looked at."""
    x = 16
    y = layout.ROSTER[3] - 176
    ink.ink_line(surface, (x, y - 12), (layout.ROSTER[2] - 16, y - 12), 0.5,
                 61, palette.INK, 0.35)
    cell = Cell(lineage.flow, selected)
    member = lineage.members[selected]

    typo.caps(surface, f"cell {selected}", (x, y), 9, palette.INK_FAINT, 1.6)
    typo.draw(surface, cell.dominant_pathway(), (x, y + 16), 11, palette.INK, 0.2)

    state = ("starving" if cell.starving()
             else "spilling" if cell.spilling() else "running")
    typo.draw(surface, state, (x, y + 34), 11,
              palette.ALARM if state != "running" else palette.PENCIL, 0.2)
    typo.draw(surface, f"low: {cell.worst_metabolite().label}", (x, y + 50), 9,
              palette.PENCIL, 0.2)

    placed = lineage.placed_marks(selected)
    inherited = lineage.inherited_marks(selected)
    typo.draw(surface, f"{placed} placed, {inherited} inherited", (x, y + 70), 9,
              palette.PENCIL, 0.2)
    if member.parent is not None:
        typo.draw(surface, f"from cell {member.parent}, generation {member.born}",
                  (x, y + 84), 9, palette.PENCIL, 0.2)

    reason = lineage.why_not_divide(selected)
    typo.draw(surface, reason or "ready to divide  ·  d", (x, y + 106), 10,
              palette.PENCIL if reason else palette.INK, 0.2)

    # What dividing would actually do. The milestone turns on a player being
    # reluctant to copy a cell that is not working, and they can only be
    # reluctant about something they were told.
    if not reason and warning:
        for i, line in enumerate(_wrap(warning, 9, layout.ROSTER[2] - 30)):
            typo.draw(surface, line, (x, y + 122 + i * 12), 9, palette.ALARM, 0.2)


def _wrap(text: str, size: int, width: float) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if typo.width(trial, size, 0.2) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines
