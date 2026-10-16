from __future__ import annotations

from collections import Counter

from .ai import BaseAI
from .board import Cell, ship_cells
from .knowledge import HIT, MISS, SUNK, UNKNOWN, Knowledge


class ProbabilityAI(BaseAI):
    name = "Складний (карта ймовірностей)"

    def probability_map(self, k: Knowledge, use_hits: bool = True) -> list:
        n = k.size
        groups = [set(g) for g in k.hit_groups()] if use_hits else []
        heat = [[0] * n for _ in range(n)]

        for length, count in Counter(k.remaining).items():
            orientations = (True, False) if length > 1 else (True,)
            for r in range(n):
                for c in range(n):
                    for horizontal in orientations:
                        cells = ship_cells(r, c, length, horizontal)
                        if not self._fits(k, cells):
                            continue
                        if not self._consistent(set(cells), groups):
                            continue
                        for (cr, cc) in cells:
                            heat[cr][cc] += count
        return heat

    @staticmethod
    def _fits(k: Knowledge, cells: tuple) -> bool:
        for r, c in cells:
            if not (0 <= r < k.size and 0 <= c < k.size):
                return False
            if k.grid[r][c] in (MISS, SUNK):
                return False
        return True

    @staticmethod
    def _consistent(placement: set, groups: list) -> bool:
        if not groups:
            return True
        touched = [g for g in groups if g & placement]
        if not touched:
            return False
        return all(g <= placement for g in touched)

    def best_cells(self, k: Knowledge) -> list:
        unknown = k.unknown_cells()
        heat = self.probability_map(k, use_hits=True)
        best = max(heat[r][c] for r, c in unknown)
        if best == 0:
            heat = self.probability_map(k, use_hits=False)
            best = max(heat[r][c] for r, c in unknown)
            if best == 0:
                return unknown
        return [(r, c) for r, c in unknown if heat[r][c] == best]

    def choose(self, k: Knowledge) -> Cell:
        return self.rng.choice(self.best_cells(k))

    def planned_cells(self, k: Knowledge) -> list:
        return self.best_cells(k)
