import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

try:
    import pygame
    from battleship.game import AI, OVER, PLAYER
    from battleship.ui import App
    from battleship.ui.effects import Effects
    from battleship.ui.ships_art import ship_surface
    from battleship.ui.theme import CELL, Fonts
    HAVE_PYGAME = True
except ImportError:
    HAVE_PYGAME = False


@unittest.skipUnless(HAVE_PYGAME, "pygame не встановлено")
class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = App()

    def setUp(self):
        self.app.scene = "game"
        self.app.new_game()
        self.app.recommend()
        self.app.start()

    def run_frames(self, count, dt=40):
        for _ in range(count):
            self.app.frame(dt)

    def test_ship_sprites_have_cell_size(self):
        for length in (1, 2, 3, 4):
            horizontal = ship_surface(length, True, CELL)
            vertical = ship_surface(length, False, CELL)
            self.assertEqual(horizontal.get_size(), (length * CELL, CELL))
            self.assertEqual(vertical.get_size(), (CELL, length * CELL))

    def test_shot_result_is_hidden_until_shell_lands(self):
        app = self.app
        cell = app.game.player_view.unknown_cells()[0]
        app.player_shoot(cell)
        self.assertTrue(app.busy)
        self.assertIn(cell, app.hidden)
        self.assertEqual(app.stats["player"][0], 0)
        self.run_frames(30)
        self.assertFalse(app.busy and app.shells and app.shells[0].who == "player")
        self.assertNotIn(cell, app.hidden)
        self.assertEqual(app.stats["player"][0], 1)
        self.assertTrue(app.log)

    def test_input_is_blocked_while_shell_flies(self):
        app = self.app
        cells = app.game.player_view.unknown_cells()
        app.player_shoot(cells[0])
        app.player_shoot(cells[1])
        self.assertEqual(app.game.player_shots, 1)

    def test_player_can_win_and_overlay_appears(self):
        app = self.app
        targets = [cell for ship in app.game.enemy_board.ships for cell in ship.cells]
        guard = 0
        while app.game.phase != OVER and guard < 4000:
            guard += 1
            if app.game.phase == PLAYER and not app.busy and targets:
                app.player_shoot(targets.pop())
            app.frame(40)
        self.assertEqual(app.game.phase, OVER)
        self.assertEqual(app.game.winner, "player")
        self.run_frames(80)
        self.assertTrue(app.over_ready)
        self.assertEqual(app.stats["player"][1], 20)

    def test_every_scene_renders(self):
        app = self.app
        app.scene = "menu"
        self.run_frames(3)
        app.scene = "game"
        self.run_frames(3)
        self.assertEqual(app.canvas.get_size(), (1280, 780))

    def test_effects_expire(self):
        fx = Effects(Fonts())
        fx.explosion(100, 100)
        fx.splash(200, 200)
        fx.popup("тест", 50, 50)
        for _ in range(400):
            fx.update(0.02)
        self.assertFalse(fx.particles or fx.rings or fx.popups)


if __name__ == "__main__":
    unittest.main()
