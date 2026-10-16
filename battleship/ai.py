"""ШІ-супротивники для «Морського бою» — стратегія обстрілу.

Реалізовано алгоритми зі стратегічного керівництва гри (усе написано самостійно,
без готових солверів). Морський бій — гра з НЕПОВНОЮ інформацією (кораблів
суперника не видно), тому minimax / alpha-beta тут не застосовні: немає повного
дерева станів. ШІ діє за правилами, виведеними з теорії ймовірностей і
послідовного виключення зон.

Стратегія складається з трьох етапів:

  Етап A. ПОЛЮВАННЯ на великі кораблі — діагональна сітка.
          Стріляємо по клітинках, де (рядок + стовпець) % K == s, де K — довжина
          найбільшого ще не потопленого корабля. Корабель довжиною K завжди
          перетне таку сітку, тож пропустити його неможливо.
          На полі 10x10 для лінкора (K=4) вистачає 24 пострілів.
          Після потоплення лінкора крок звужується до 3 (крейсери), потім до 2.

  Етап B. ДОБИВАННЯ — після влучання («поранив»):
          1) обстрілюємо «хрестом» 4 сусідні клітинки;
          2) коли знайшли другу палубу, лінія корабля відома — стріляємо вздовж неї
             в обидва кінці, доки корабель не потоплено;
          3) навколо потопленого корабля клітинки позначаються як промахи
             («червона зона» — там не може бути інших кораблів).

  Етап C. ОДНОПАЛУБНІ катери — шукаємо в останню чергу, у найбільших
          вільних (ще не відкритих) зонах поля.

Три рівні складності:
  EasyAI   — випадковий пошук + добивання;
  MediumAI — шахова парність (крок 2) + добивання;
  HardAI   — повна стратегія: крок 4 → 3 → 2, добивання, зони для катерів.
"""
from __future__ import annotations

import random
from typing import Optional

from .board import Cell, neighbors4, neighbors8
from .knowledge import UNKNOWN, Knowledge


# ----------------------------------------------------------------------
# Допоміжні функції аналізу поля
# ----------------------------------------------------------------------
def _run_length(k: Knowledge, cell: Cell, dr: int, dc: int) -> int:
    """Довжина безперервної смуги НЕвідкритих клітинок через `cell` у напрямку (dr, dc)."""
    r, c = cell
    length = 1
    for sign in (1, -1):
        rr, cc = r + sign * dr, c + sign * dc
        while 0 <= rr < k.size and 0 <= cc < k.size and k.grid[rr][cc] == UNKNOWN:
            length += 1
            rr += sign * dr
            cc += sign * dc
    return length


def max_run(k: Knowledge, cell: Cell) -> int:
    """Найдовша смуга вільних клітинок (по горизонталі або вертикалі) через клітинку.
    Якщо вона коротша за корабель, корабель тут фізично не поміститься."""
    return max(_run_length(k, cell, 0, 1), _run_length(k, cell, 1, 0))


def grid_candidates(k: Knowledge, step: int, memory: dict,
                    rng: random.Random) -> list:
    """Діагональна сітка з кроком `step` (етап A).

    Для кожного зсуву s = 0..step-1 беремо невідкриті клітинки, де
    (r + c) % step == s і в які ще може поміститися корабель довжиною `step`.
    Обираємо зсув, що дає НАЙМЕНШЕ клітинок (тобто найменше пострілів у гіршому
    випадку; для лінкора 10x10 це 24), і далі тримаємося його («запам'ятовуємо»).
    """
    unknown = k.unknown_cells()
    options = {}
    for s in range(step):
        cells = [x for x in unknown
                 if (x[0] + x[1]) % step == s and max_run(k, x) >= step]
        if cells:
            options[s] = cells
    if not options:
        return unknown
    if memory.get(step) in options:
        return options[memory[step]]
    fewest = min(len(v) for v in options.values())
    s = rng.choice([s for s, v in options.items() if len(v) == fewest])
    memory[step] = s
    return options[s]


def unknown_zones(k: Knowledge) -> list:
    """Зв'язні області невідкритих клітинок (сусідство по горизонталі/вертикалі)."""
    unknown = set(k.unknown_cells())
    zones, seen = [], set()
    for start in sorted(unknown):
        if start in seen:
            continue
        stack, zone = [start], []
        seen.add(start)
        while stack:
            cur = stack.pop()
            zone.append(cur)
            for nb in neighbors4(cur, k.size):
                if nb in unknown and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        zones.append(zone)
    return zones


def largest_zone_cells(k: Knowledge) -> list:
    """Етап C: клітинки найбільшої вільної зони; усередині — «найвідкритіші»
    (ті, що мають найбільше невідкритих сусідів)."""
    zones = unknown_zones(k)
    if not zones:
        return k.unknown_cells()
    zone = max(zones, key=len)
    zone_set = set(zone)

    def openness(cell):
        return sum(1 for nb in neighbors8(cell, k.size) if nb in zone_set)

    best = max(openness(c) for c in zone)
    return [c for c in zone if openness(c) == best]


# ----------------------------------------------------------------------
# Базові класи
# ----------------------------------------------------------------------
class BaseAI:
    name = "base"

    def __init__(self, rng: Optional[random.Random] = None):
        self.rng = rng or random.Random()

    def choose(self, k: Knowledge) -> Cell:
        """Повертає клітинку для пострілу. Реалізується в нащадках."""
        raise NotImplementedError

    def planned_cells(self, k: Knowledge) -> list:
        """Клітинки, з яких ШІ зараз обирає постріл (для підсвітки в інтерфейсі)."""
        return k.unknown_cells()


class RandomAI(BaseAI):
    """Чисто випадкові постріли («пальцем в небо»). Лише еталон для порівняння."""
    name = "Випадковий (еталон)"

    def choose(self, k: Knowledge) -> Cell:
        return self.rng.choice(k.unknown_cells())


class TargetingAI(BaseAI):
    """ШІ з добиванням (етап B) + власний спосіб пошуку (hunt_candidates)."""

    def choose(self, k: Knowledge) -> Cell:
        targets = self.target_cells(k)
        if targets:
            return self.rng.choice(targets)
        return self.rng.choice(self.hunt_candidates(k))

    def planned_cells(self, k: Knowledge) -> list:
        return self.target_cells(k) or self.hunt_candidates(k)

    def hunt_candidates(self, k: Knowledge) -> list:
        raise NotImplementedError

    # ---------- Етап B: добивання ----------
    @staticmethod
    def target_cells(k: Knowledge) -> list:
        """Куди стріляти, щоб добити підбитий корабель (порожньо, якщо таких немає)."""
        def free(cell):
            r, c = cell
            return 0 <= r < k.size and 0 <= c < k.size and k.grid[r][c] == UNKNOWN

        for group in k.hit_groups():
            if len(group) == 1:                          # «хрест»: напрямок невідомий
                r, c = group[0]
                cells = [x for x in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
                         if free(x)]
            else:                                        # лінія відома: обидва кінці
                if len({r for r, _ in group}) == 1:      # горизонтально
                    r = group[0][0]
                    lo, hi = min(c for _, c in group), max(c for _, c in group)
                    ends = [(r, lo - 1), (r, hi + 1)]
                else:                                    # вертикально
                    c = group[0][1]
                    lo, hi = min(r for r, _ in group), max(r for r, _ in group)
                    ends = [(lo - 1, c), (hi + 1, c)]
                cells = [x for x in ends if free(x)]
            if cells:
                return cells
        return []


# ----------------------------------------------------------------------
# Рівні складності
# ----------------------------------------------------------------------
class EasyAI(TargetingAI):
    """Легкий: пошук випадковий, але добиває підбитий корабель."""
    name = "Легкий (випадковий пошук + добивання)"

    def hunt_candidates(self, k: Knowledge) -> list:
        return k.unknown_cells()


class MediumAI(TargetingAI):
    """Середній: шахова парність (крок 2) + добивання."""
    name = "Середній (шахова парність + добивання)"

    def __init__(self, rng: Optional[random.Random] = None):
        super().__init__(rng)
        self._memory: dict = {}

    def hunt_candidates(self, k: Knowledge) -> list:
        if max(k.remaining) < 2:                  # лишились самі катери
            return k.unknown_cells()
        return grid_candidates(k, 2, self._memory, self.rng)


class HardAI(TargetingAI):
    """Складний: повна стратегія. Крок сітки = довжина найбільшого живого корабля
    (4 → 3 → 2), далі катери шукаються в найбільших вільних зонах."""
    name = "Складний (діагональна сітка 4→3→2 + добивання)"

    def __init__(self, rng: Optional[random.Random] = None):
        super().__init__(rng)
        self._memory: dict = {}

    def hunt_candidates(self, k: Knowledge) -> list:
        biggest = max(k.remaining)
        if biggest >= 2:
            return grid_candidates(k, biggest, self._memory, self.rng)   # етап A
        return largest_zone_cells(k)                                      # етап C


LEVELS = {
    "easy": EasyAI,
    "medium": MediumAI,
    "hard": HardAI,
}


def make_ai(level: str, rng: Optional[random.Random] = None) -> BaseAI:
    return LEVELS[level](rng)
