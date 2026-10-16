"""Знання стрільця про поле суперника (те, що видно «зверху»).

Саме цей об'єкт отримує ШІ: він НЕ бачить кораблів суперника,
а лише результати власних пострілів. Це гра з неповною інформацією.
"""
from __future__ import annotations

from .board import FLEET, SIZE, Cell, ShotResult, neighbors4

UNKNOWN, MISS, HIT, SUNK = 0, 1, 2, 3


class Knowledge:
    def __init__(self, size: int = SIZE, fleet=FLEET):
        self.size = size
        self.grid = [[UNKNOWN] * size for _ in range(size)]
        self.remaining = list(fleet)   # довжини ще не потоплених кораблів суперника

    # ---------- оновлення після пострілу ----------
    def update(self, result: ShotResult) -> None:
        r, c = result.cell
        self.grid[r][c] = HIT if result.hit else MISS
        if result.sunk:
            for sr, sc in result.ship_cells:
                self.grid[sr][sc] = SUNK
            self.remaining.remove(len(result.ship_cells))
            for ar, ac in result.around:
                if self.grid[ar][ac] == UNKNOWN:
                    self.grid[ar][ac] = MISS

    # ---------- запити ----------
    def state(self, cell: Cell) -> int:
        return self.grid[cell[0]][cell[1]]

    def unknown_cells(self) -> list:
        return [(r, c) for r in range(self.size) for c in range(self.size)
                if self.grid[r][c] == UNKNOWN]

    def hit_cells(self) -> list:
        """Влучання, які ще не належать потопленому кораблю."""
        return [(r, c) for r in range(self.size) for c in range(self.size)
                if self.grid[r][c] == HIT]

    def hit_groups(self) -> list:
        """Групи зв'язних (по горизонталі/вертикалі) пошкоджених клітинок.

        Оскільки кораблі не торкаються один одного, сусідні влучання
        завжди належать ОДНОМУ кораблю, тож кожна група = один підбитий корабель.
        """
        hits = set(self.hit_cells())
        groups, seen = [], set()
        for start in sorted(hits):
            if start in seen:
                continue
            stack, group = [start], []
            seen.add(start)
            while stack:
                cur = stack.pop()
                group.append(cur)
                for nb in neighbors4(cur, self.size):
                    if nb in hits and nb not in seen:
                        seen.add(nb)
                        stack.append(nb)
            groups.append(sorted(group))
        return groups

    def known_count(self) -> int:
        return sum(1 for row in self.grid for v in row if v != UNKNOWN)
