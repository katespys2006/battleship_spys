import random
import unittest

from battleship.ai import EasyAI, HardAI, MediumAI, RandomAI
from battleship.placement import smart_placement
from battleship.board import FLEET, Board, neighbors8, ship_cells
from battleship.game import AI, OVER, PLAYER, Game
from battleship.knowledge import HIT, MISS, SUNK, UNKNOWN, Knowledge


class BoardTests(unittest.TestCase):
    def test_random_placement_is_valid(self):
        rng = random.Random(1)
        for _ in range(50):
            b = Board()
            b.place_randomly(FLEET, rng)
            self.assertEqual(sorted((s.length for s in b.ships), reverse=True), list(FLEET))
            cells = {c for s in b.ships for c in s.cells}
            self.assertEqual(len(cells), sum(FLEET))
            for s in b.ships:                      # кораблі не торкаються
                for cell in s.cells:
                    for nb in neighbors8(cell):
                        if nb in cells:
                            self.assertIn(nb, s.cells)

    def test_cannot_place_touching_ships(self):
        b = Board()
        self.assertTrue(b.place(ship_cells(0, 0, 3, True)))
        self.assertFalse(b.place(ship_cells(1, 1, 2, True)))   # торкається по діагоналі
        self.assertFalse(b.place(ship_cells(0, 8, 3, True)))   # за межами поля
        self.assertTrue(b.place(ship_cells(2, 0, 2, True)))

    def test_sinking_marks_surroundings(self):
        b = Board()
        b.place(ship_cells(5, 5, 2, True))
        self.assertFalse(b.receive_shot((0, 0)).hit)
        r1 = b.receive_shot((5, 5))
        self.assertTrue(r1.hit and not r1.sunk)
        r2 = b.receive_shot((5, 6))
        self.assertTrue(r2.sunk)
        self.assertEqual(len(r2.around), 10)    # 4x3 прямокутник мінус 2 клітинки корабля
        self.assertTrue(b.all_sunk)
        with self.assertRaises(ValueError):
            b.receive_shot((5, 5))


class KnowledgeTests(unittest.TestCase):
    def test_update_and_groups(self):
        b = Board()
        b.place(ship_cells(2, 2, 3, False))
        k = Knowledge()
        k.update(b.receive_shot((2, 2)))
        k.update(b.receive_shot((3, 2)))
        self.assertEqual(k.hit_groups(), [[(2, 2), (3, 2)]])
        k.update(b.receive_shot((4, 2)))
        self.assertEqual(k.hit_groups(), [])
        self.assertEqual(k.state((3, 2)), SUNK)
        self.assertEqual(k.state((1, 2)), MISS)
        self.assertEqual(k.remaining.count(3), 1)


class AITests(unittest.TestCase):
    def play_alone(self, ai_cls, seed):
        rng = random.Random(seed)
        b = Board()
        b.place_randomly(FLEET, rng)
        k = Knowledge()
        ai = ai_cls(rng)
        shots = set()
        while not b.all_sunk:
            cell = ai.choose(k)
            self.assertNotIn(cell, shots)          # ніколи не стріляє двічі в одну клітинку
            shots.add(cell)
            k.update(b.receive_shot(cell))
        return len(shots)

    def test_all_ais_finish_and_never_repeat(self):
        for cls in (RandomAI, EasyAI, MediumAI, HardAI):
            for seed in range(10):
                self.assertLessEqual(self.play_alone(cls, seed), 100)

    def test_levels_get_stronger(self):
        def avg(cls):
            return sum(self.play_alone(cls, s) for s in range(60)) / 60
        rnd, easy, medium, hard = avg(RandomAI), avg(EasyAI), avg(MediumAI), avg(HardAI)
        self.assertLess(easy, rnd)
        self.assertLess(medium, easy)
        self.assertLess(hard, medium + 1)       # складний не гірший за середній

    def test_first_hunt_grid_for_battleship_is_24_cells(self):
        ai = HardAI(random.Random(0))
        cells = ai.hunt_candidates(Knowledge())
        self.assertEqual(len(cells), 24)
        offsets = {(r + c) % 4 for r, c in cells}
        self.assertEqual(len(offsets), 1)       # усі на одній діагональній сітці кроку 4

    def test_battleship_always_found_within_24_shots(self):
        """Гарантія діагонального методу: лінкор (4) знаходиться максимум за 24 постріли."""
        for horizontal in (True, False):
            for r in range(10):
                for c in range(10):
                    cells = ship_cells(r, c, 4, horizontal)
                    b = Board()
                    if not b.place(cells):
                        continue
                    k = Knowledge(fleet=(4,))
                    ai = HardAI(random.Random(r * 10 + c))
                    shots = 0
                    while True:
                        shots += 1
                        res = b.receive_shot(ai.choose(k))
                        k.update(res)
                        if res.hit:
                            break
                    self.assertLessEqual(shots, 24)

    def test_target_mode_finishes_wounded_ship_along_line(self):
        b = Board()
        b.place(ship_cells(4, 3, 4, True))
        k = Knowledge()
        k.update(b.receive_shot((4, 4)))
        k.update(b.receive_shot((4, 5)))
        self.assertEqual(sorted(EasyAI.target_cells(k)), [(4, 3), (4, 6)])

    def test_single_hit_makes_cross(self):
        b = Board()
        b.place(ship_cells(4, 4, 3, True))
        k = Knowledge()
        k.update(b.receive_shot((4, 4)))
        self.assertEqual(sorted(HardAI.target_cells(k)),
                         [(3, 4), (4, 3), (4, 5), (5, 4)])

    def test_singles_searched_in_largest_zone(self):
        k = Knowledge(fleet=(1,))
        # відкриваємо все, окрім великої зони справа та кількох клітинок зліва
        for r in range(10):
            for c in range(10):
                if c < 6 and not (r == 0 and c in (0, 2)):
                    k.grid[r][c] = MISS
        cells = HardAI(random.Random(1)).hunt_candidates(k)
        self.assertTrue(all(c >= 6 for _, c in cells))


class PlacementTests(unittest.TestCase):
    def test_smart_placement_valid_and_coastal(self):
        rng = random.Random(7)
        for _ in range(100):
            b = Board()
            smart_placement(b, FLEET, rng)
            self.assertEqual(sorted((s.length for s in b.ships), reverse=True), list(FLEET))
            cells = {c for s in b.ships for c in s.cells}
            self.assertEqual(len(cells), 20)
            for s in b.ships:                      # кораблі не торкаються
                for cell in s.cells:
                    for nb in neighbors8(cell):
                        if nb in cells:
                            self.assertIn(nb, s.cells)
            battleship = [s for s in b.ships if s.length == 4][0]
            self.assertTrue(all(r in (0, 9) for r, _ in battleship.cells)
                            or all(c in (0, 9) for _, c in battleship.cells))


class GameTests(unittest.TestCase):
    def test_full_game_flow(self):
        rng = random.Random(3)
        g = Game("hard", rng)
        self.assertFalse(g.start())
        g.randomize_player()
        self.assertTrue(g.start())
        guard = 0
        while g.phase != OVER and guard < 1000:
            guard += 1
            if g.phase == PLAYER:
                cell = rng.choice(g.player_view.unknown_cells())
                self.assertIsNotNone(g.player_shoot(cell))
            elif g.phase == AI:
                self.assertIsNotNone(g.ai_shoot())
        self.assertEqual(g.phase, OVER)
        self.assertIn(g.winner, ("player", "ai"))


if __name__ == "__main__":
    unittest.main()
