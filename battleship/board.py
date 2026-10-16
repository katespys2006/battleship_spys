"""Поле гри «Морський бій»: кораблі, розстановка, обробка пострілів.

Правила (класичні українські):
  * поле 10x10;
  * флот: 1 чотирипалубний, 2 трипалубні, 3 двопалубні, 4 однопалубні;
  * кораблі не можуть торкатися один одного (навіть по діагоналі);
  * після влучання стрілець ходить ще раз;
  * коли корабель потоплено, всі клітинки навколо нього автоматично
    позначаються як «промах».
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Iterator, Optional

SIZE = 10
FLEET = (4, 3, 3, 2, 2, 2, 1, 1, 1, 1)  # довжини кораблів, від більшого до меншого

Cell = tuple  # (рядок, стовпець)


def neighbors8(cell: Cell, size: int = SIZE) -> Iterator[Cell]:
    """Усі сусідні клітинки, включно з діагоналями (в межах поля)."""
    r, c = cell
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < size and 0 <= nc < size:
                yield (nr, nc)


def neighbors4(cell: Cell, size: int = SIZE) -> Iterator[Cell]:
    """Сусіди по горизонталі/вертикалі (в межах поля)."""
    r, c = cell
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < size and 0 <= nc < size:
            yield (nr, nc)


def ship_cells(r: int, c: int, length: int, horizontal: bool) -> tuple:
    """Клітинки корабля, що починається в (r, c). Межі поля НЕ перевіряються."""
    if horizontal:
        return tuple((r, c + i) for i in range(length))
    return tuple((r + i, c) for i in range(length))


@dataclass
class Ship:
    cells: tuple
    hits: set = field(default_factory=set)

    @property
    def length(self) -> int:
        return len(self.cells)

    @property
    def is_sunk(self) -> bool:
        return len(self.hits) == len(self.cells)


@dataclass(frozen=True)
class ShotResult:
    """Результат одного пострілу."""
    cell: Cell
    hit: bool
    sunk: bool = False
    ship_cells: tuple = ()   # клітинки потопленого корабля
    around: tuple = ()       # клітинки навколо потопленого корабля (авто-промахи)


class Board:
    """Поле одного гравця: його кораблі та отримані постріли."""

    def __init__(self, size: int = SIZE):
        self.size = size
        self.ships: list = []
        self._owner: dict = {}      # клітинка -> індекс корабля
        self.shots: set = set()     # клітинки, у які вже стріляли (включно з авто-промахами)

    # ---------- розстановка ----------
    def has_ship(self, cell: Cell) -> bool:
        return cell in self._owner

    def can_place(self, cells) -> bool:
        """Корабель можна поставити, якщо всі клітинки в межах поля,
        вільні, і поруч (включно з діагоналями) немає інших кораблів."""
        for cell in cells:
            r, c = cell
            if not (0 <= r < self.size and 0 <= c < self.size):
                return False
            if cell in self._owner:
                return False
            for nb in neighbors8(cell, self.size):
                if nb in self._owner:
                    return False
        return True

    def place(self, cells) -> bool:
        if not self.can_place(cells):
            return False
        idx = len(self.ships)
        self.ships.append(Ship(tuple(cells)))
        for cell in cells:
            self._owner[cell] = idx
        return True

    def remove_last(self) -> None:
        if not self.ships:
            return
        ship = self.ships.pop()
        for cell in ship.cells:
            del self._owner[cell]

    def clear(self) -> None:
        self.ships.clear()
        self._owner.clear()
        self.shots.clear()

    def place_randomly(self, fleet=FLEET, rng: Optional[random.Random] = None) -> None:
        """Випадкова коректна розстановка всього флоту."""
        rng = rng or random.Random()
        while True:
            self.clear()
            ok = True
            for length in fleet:
                for _ in range(500):
                    horizontal = rng.random() < 0.5
                    r = rng.randrange(self.size)
                    c = rng.randrange(self.size)
                    if self.place(ship_cells(r, c, length, horizontal)):
                        break
                else:
                    ok = False
                    break
            if ok:
                return

    # ---------- постріли ----------
    def receive_shot(self, cell: Cell) -> ShotResult:
        if cell in self.shots:
            raise ValueError(f"У клітинку {cell} вже стріляли")
        self.shots.add(cell)
        idx = self._owner.get(cell)
        if idx is None:
            return ShotResult(cell, hit=False)

        ship = self.ships[idx]
        ship.hits.add(cell)
        if not ship.is_sunk:
            return ShotResult(cell, hit=True)

        # корабель потоплено: позначаємо клітинки навколо як промахи
        around = []
        for sc in ship.cells:
            for nb in neighbors8(sc, self.size):
                if nb not in ship.cells and nb not in self.shots:
                    self.shots.add(nb)
                    around.append(nb)
        return ShotResult(cell, hit=True, sunk=True,
                          ship_cells=ship.cells, around=tuple(around))

    @property
    def all_sunk(self) -> bool:
        return bool(self.ships) and all(s.is_sunk for s in self.ships)
