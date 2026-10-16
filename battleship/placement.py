"""Стратегія розстановки флоту (за стратегічним керівництвом гри).

Правила розстановки:
  1. «Берегова лінія»: лінкор і крейсери ставимо ВПРИТУЛ до краю поля
     (уздовж межі), лінкор — бажано в кутку. Після потоплення такий корабель
     «відкриває» супернику мало зайвих клітинок:
         лінкор у центрі  -> 14 клітинок «червоної зони»,
         лінкор у кутку   ->  6 клітинок.
  2. Розпорошення: великі кораблі не купчимо в одному місці — кожен наступний
     ставимо якомога далі від уже розставлених великих кораблів, щоб одне
     влучання не розкрило позиції кількох головних кораблів.
  3. Есмінці (2) — розпорошуємо по вільній території.
  4. Катери (1) — поодинці на вільних місцях; останню пару ставимо
     «кластером» (близько одна до одної, через клітинку).

Усюди додано випадковість, щоб розстановка не була однаковою щоразу.
"""
from __future__ import annotations

import random
from typing import Optional

from .board import FLEET, Board, ship_cells


def chebyshev(a, b) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _distance(cells, others) -> int:
    """Мінімальна відстань (Чебишева) між клітинками двох груп."""
    if not others:
        return 0
    return min(chebyshev(a, b) for a in cells for b in others)


def _all_placements(board: Board, length: int) -> list:
    options = []
    n = board.size
    for r in range(n):
        for c in range(n):
            for horizontal in ((True, False) if length > 1 else (True,)):
                cells = ship_cells(r, c, length, horizontal)
                if board.can_place(cells):
                    options.append(cells)
    return options


def _along_border(cells, n: int) -> bool:
    """Усі клітинки корабля лежать на одній межі поля («берегова лінія»)."""
    return (all(r == 0 for r, _ in cells) or all(r == n - 1 for r, _ in cells)
            or all(c == 0 for _, c in cells) or all(c == n - 1 for _, c in cells))


def _touches_corner(cells, n: int) -> bool:
    corners = {(0, 0), (0, n - 1), (n - 1, 0), (n - 1, n - 1)}
    return any(cell in corners for cell in cells)


def _occupied(board: Board) -> list:
    return [cell for ship in board.ships for cell in ship.cells]


def _try_smart(board: Board, fleet, rng: random.Random) -> bool:
    n = board.size
    big = sorted((L for L in fleet if L >= 3), reverse=True)
    mid = [L for L in fleet if L == 2]
    small = [L for L in fleet if L == 1]
    big_cells: list = []

    # --- великі кораблі: уздовж берега, розпорошені ---
    for i, length in enumerate(big):
        options = [p for p in _all_placements(board, length) if _along_border(p, n)]
        if not options:
            return False
        if i == 0:                                     # лінкор — у кут
            corner = [p for p in options if _touches_corner(p, n)]
            options = corner or options
        best = max(options, key=lambda p: _distance(p, big_cells) + rng.random() * 2)
        board.place(best)
        big_cells.extend(best)

    # --- есмінці: розпорошуємо ---
    for length in mid:
        options = _all_placements(board, length)
        if not options:
            return False
        occ = _occupied(board)
        best = max(options, key=lambda p: min(_distance(p, occ), 4) + rng.random() * 2)
        board.place(best)

    # --- катери: поодинці; остання пара — кластер ---
    last = None
    for i, length in enumerate(small):
        options = _all_placements(board, length)
        if not options:
            return False
        occ = _occupied(board)
        if last is not None and i == len(small) - 1 and len(small) >= 2:
            near = [p for p in options if chebyshev(p[0], last) == 2]
            if near:
                best = rng.choice(near)
                board.place(best)
                last = best[0]
                continue
        best = max(options, key=lambda p: min(_distance(p, occ), 4) + rng.random() * 2)
        board.place(best)
        last = best[0]
    return True


def smart_placement(board: Board, fleet=FLEET, rng: Optional[random.Random] = None) -> None:
    """Розставляє весь флот за стратегією. Якщо раптом не вийшло — випадково."""
    rng = rng or random.Random()
    for _ in range(100):
        board.clear()
        if _try_smart(board, fleet, rng) and len(board.ships) == len(fleet):
            return
    board.place_randomly(fleet, rng)
