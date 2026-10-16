import random
import unittest

from battleship.ai_probability import ProbabilityAI
from battleship.board import FLEET, Board
from battleship.game import Game
from battleship.knowledge import Knowledge
from battleship.levels import LEVELS, make_ai


class LevelsTests(unittest.TestCase):
    def test_hard_level_uses_probability_map(self):
        self.assertIs(LEVELS["hard"], ProbabilityAI)
        self.assertIsInstance(make_ai("hard"), ProbabilityAI)
        self.assertIsInstance(Game("hard").ai, ProbabilityAI)

    def test_hard_ai_finishes_and_never_repeats(self):
        for seed in range(15):
            rng = random.Random(seed)
            board = Board()
            board.place_randomly(FLEET, rng)
            view = Knowledge()
            ai = make_ai("hard", rng)
            shots = set()
            while not board.all_sunk:
                cell = ai.choose(view)
                self.assertNotIn(cell, shots)
                shots.add(cell)
                view.update(board.receive_shot(cell))
            self.assertLessEqual(len(shots), 100)

    def test_plan_cells_are_unknown_cells(self):
        rng = random.Random(3)
        board = Board()
        board.place_randomly(FLEET, rng)
        view = Knowledge()
        ai = make_ai("hard", rng)
        for _ in range(25):
            view.update(board.receive_shot(ai.choose(view)))
            if board.all_sunk:
                break
        plan = ai.planned_cells(view)
        self.assertTrue(plan)
        self.assertTrue(set(plan) <= set(view.unknown_cells()))

    def test_after_a_hit_it_finishes_the_ship_first(self):
        k = Knowledge()
        board = Board()
        board.place([(4, 4), (4, 5), (4, 6)])
        k.update(board.receive_shot((4, 5)))
        ai = make_ai("hard", random.Random(1))
        self.assertIn(ai.choose(k), {(3, 5), (5, 5), (4, 4), (4, 6)})


if __name__ == "__main__":
    unittest.main()
