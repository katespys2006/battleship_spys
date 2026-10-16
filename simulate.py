import argparse
import random
import statistics

from battleship.ai import EasyAI, HardAI, MediumAI, RandomAI
from battleship.ai_probability import ProbabilityAI
from battleship.board import FLEET, Board
from battleship.knowledge import Knowledge
from battleship.placement import smart_placement

STRATEGIES = [
    ("Випадковий (еталон)", RandomAI),
    ("Легкий (випадковий пошук + добивання)", EasyAI),
    ("Середній (шахова парність + добивання)", MediumAI),
    ("Сітка 4-3-2 + добивання (перша версія складного)", HardAI),
    ("Складний (карта ймовірностей)", ProbabilityAI),
]


def play(ai_cls, placement: str, rng: random.Random):
    board = Board()
    if placement == "smart":
        smart_placement(board, FLEET, rng)
    else:
        board.place_randomly(FLEET, rng)
    view = Knowledge()
    ai = ai_cls(rng)
    shots, battleship_at = 0, None
    while not board.all_sunk:
        result = board.receive_shot(ai.choose(view))
        view.update(result)
        shots += 1
        if result.sunk and len(result.ship_cells) == 4:
            battleship_at = shots
    return shots, battleship_at


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=500)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()

    print(f"Ігор на кожну клітинку таблиці: {args.games}, seed={args.seed}\n")
    print("Менше = краще.\n")
    print(f"{'':52s} {'Усього пострілів до перемоги':>30s}   {'До потоплення лінкора':>24s}")
    print(f"{'Стратегія':52s} {'випадк. розст.':>14s} {'страт. розст.':>14s}   {'середнє':>10s} {'макс':>6s}")
    for name, cls in STRATEGIES:
        total = {}
        for placement in ("random", "smart"):
            rng = random.Random(args.seed)
            games = [play(cls, placement, rng) for _ in range(args.games)]
            total[placement] = statistics.mean(g[0] for g in games)
            if placement == "random":
                bs = [g[1] for g in games]
        print(f"{name:52s} {total['random']:14.1f} {total['smart']:14.1f}   "
              f"{statistics.mean(bs):10.1f} {max(bs):6d}")


if __name__ == "__main__":
    main()
