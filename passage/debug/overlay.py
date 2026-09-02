"""Raw rates, mass-balance residual, timing. Toggled on the F-keys.

Spec 2: F1 numeric rates on every vessel, F2 the live mass-balance residual,
F3 reseed, F4 timing. F5 -- reveal the optimal mark set -- arrives with the
mark system and is never shipped.
"""

from __future__ import annotations

import numpy as np
import pygame

from ..bio.cell import Cell
from ..bio.flow import Flow
from ..data import layout
from ..render import palette, plate as plate_mod, type as typo


class Overlay:
    def __init__(self) -> None:
        self.rates = False
        self.balance = False
        self.timing = False

    def key(self, key: int) -> None:
        if key == pygame.K_F1:
            self.rates = not self.rates
        elif key == pygame.K_F2:
            self.balance = not self.balance
        elif key == pygame.K_F4:
            self.timing = not self.timing

    def draw(self, surface: pygame.Surface, flow: Flow, cell: Cell,
             plate: "plate_mod.Plate", fps: float) -> None:
        if self.rates:
            for row_id in list(layout.VESSELS) + list(layout.EXCHANGE_STUBS):
                path = plate.vessel_path(row_id)
                x, y = path[len(path) // 2]
                try:
                    rate = flow.rate_of(row_id, cell.index)
                except KeyError:
                    continue
                typo.draw(surface, f"{rate:.2f}", (x + 4, y - 6), 9,
                          palette.ALARM, 0.0)
        if self.balance:
            residual = float(np.abs(flow.atom_residual()).max())
            typo.draw(surface, f"atom residual {residual:.2e}", (210, 700), 10,
                      palette.ALARM if residual > 1e-6 else palette.INK, 0.2)
        if self.timing:
            typo.draw(surface, f"{fps:5.1f} fps   tick {flow.ticks}   "
                              f"platings {plate.inkings}", (470, 700), 10,
                      palette.INK, 0.2)
