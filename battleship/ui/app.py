import math
import os
import sys
from collections import Counter

import pygame

from ..board import FLEET, ship_cells
from ..game import AI, OVER, PLACEMENT, PLAYER, Game
from ..knowledge import HIT, SUNK
from .background import Background
from .effects import Effects, glow
from .render import BoardView
from .ships_art import ship_surface
from .theme import (ACCENT, AI_DELAY_MS, AMBER, ASSETS, BAD_C, BOARD_PX, CELL, DIM, FIRE, H, LEFT, LOG_RECT,
                    OK_C, RIGHT, SHELL_MS, STATS_RECT, STATUS_RECT, TEXT, W, Fonts, cell_center, coord, lerp)
from .sound import SoundBank
from .widgets import Button, draw_panel, draw_text

LEVELS = [
    ("easy", "Легкий", 1),
    ("medium", "Середній", 2),
    ("hard", "Складний", 3),
]
CARD_W, CARD_H, CARD_GAP = 280, 96, 30
CARD_Y = 320


class Shot:
    def __init__(self, who, result, start, remaining):
        self.who = who
        self.result = result
        self.start = start
        self.land = start + SHELL_MS
        self.remaining = remaining
        self.hidden = {result.cell, *result.around, *result.ship_cells}


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Морський бій — ШІ-супротивник")
        flags = pygame.SCALED | pygame.RESIZABLE
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            self.screen = pygame.display.set_mode((W, H))
        icon = os.path.join(ASSETS, "icon.png")
        if os.path.exists(icon):
            pygame.display.set_icon(pygame.image.load(icon))
        self.canvas = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.fonts = Fonts()
        self.sound = SoundBank()
        self.bg = Background()
        self.fx = Effects(self.fonts)
        self.left = BoardView(LEFT, self.fonts)
        self.right = BoardView(RIGHT, self.fonts)

        self.time = 0.0
        self.scene = "menu"
        self.level = "hard"
        self.horizontal = True
        self.show_plan = False
        self.running = True
        self.mouse = (0, 0)
        self.card_hover = {key: 0.0 for key, *_ in LEVELS}
        self.new_game()
        self.buttons = self._build_buttons()

    def new_game(self):
        self.game = Game(self.level)
        self.horizontal = True
        self.shells = []
        self.hidden = set()
        self.stats = {"player": [0, 0], "ai": [0, 0]}
        self.log = []
        self.shown_own = list(FLEET)
        self.shown_enemy = list(FLEET)
        self.next_ai_time = 0.0
        self.banner = None
        self.over_at = None
        self.smoke_timer = 0.0
        self.message = "Розстав свої кораблі на лівому полі."
        self.fx.clear()

    def _build_buttons(self):
        in_menu = lambda: self.scene == "menu"
        in_game = lambda: self.scene == "game" and not self.over_ready
        placing = lambda: self.scene == "game" and self.game.phase == PLACEMENT
        playing = lambda: self.scene == "game" and self.game.phase in (PLAYER, AI) and not self.over_ready
        b = []
        b.append(Button((W // 2 - 150, 520, 300, 66), "ГРАТИ", self.start_from_menu, visible=in_menu, kind="primary"))
        b.append(Button((1070, 30, 80, 38), "Меню", self.to_menu, visible=in_game))
        b.append(Button((1160, 30, 80, 38), "Звук", self.toggle_sound, visible=in_game,
                        active=lambda: self.sound.enabled and self.sound.available))
        b.append(Button((W - 110, 24, 90, 38), "Звук", self.toggle_sound, visible=in_menu,
                        active=lambda: self.sound.enabled and self.sound.available))
        for i, (key, label, _) in enumerate(LEVELS):
            b.append(Button((LEFT[0] + i * 142, 648, 130, 38), label, lambda k=key: self.set_level(k),
                            visible=placing, active=lambda k=key: self.level == k))
        y = 706
        b.append(Button((LEFT[0], y, 124, 44), "Випадково", self.randomize, visible=placing))
        b.append(Button((LEFT[0] + 134, y, 162, 44), "Рекомендована", self.recommend, visible=placing))
        b.append(Button((LEFT[0] + 306, y, 114, 44), "Скасувати", self.undo, visible=placing,
                        enabled=lambda: len(self.game.player_board.ships) > 0))
        b.append(Button((RIGHT[0], y, 180, 44), "Повернути (R)", self.rotate, visible=placing))
        b.append(Button((RIGHT[0] + 190, y, 230, 44), "СТАРТ", self.start, visible=placing,
                        enabled=lambda: self.game.placement_done, kind="primary"))
        b.append(Button((LEFT[0], y, 230, 44), "План ШІ (H)", self.toggle_plan,
                        visible=lambda: playing() and self.game.level in ("medium", "hard"),
                        active=lambda: self.show_plan))
        b.append(Button((W // 2 - 270, 520, 250, 56), "Грати ще", self.again, visible=lambda: self.over_ready,
                        kind="primary"))
        b.append(Button((W // 2 + 20, 520, 250, 56), "Меню", self.to_menu, visible=lambda: self.over_ready))
        return b

    @property
    def over_ready(self):
        return self.over_at is not None and self.time - self.over_at > 1300

    @property
    def busy(self):
        return bool(self.shells)

    def play_sound(self, name):
        self.sound.play(name)

    def start_from_menu(self):
        self.play_sound("click")
        self.new_game()
        self.scene = "game"

    def to_menu(self):
        self.play_sound("click")
        self.scene = "menu"

    def again(self):
        self.play_sound("click")
        self.new_game()

    def toggle_sound(self):
        self.sound.toggle()
        self.play_sound("click")

    def set_level(self, key):
        self.play_sound("click")
        self.level = key
        self.game.set_level(key)

    def randomize(self):
        self.play_sound("place")
        self.game.randomize_player()
        self.message = "Кораблі розставлено. Натисни «СТАРТ» або перемішай ще раз."

    def recommend(self):
        self.play_sound("place")
        self.game.recommend_player()
        self.message = "Рекомендована розстановка: великі кораблі вздовж берега, розпорошені."

    def undo(self):
        self.play_sound("click")
        self.game.player_board.remove_last()

    def rotate(self):
        self.play_sound("click")
        self.horizontal = not self.horizontal

    def start(self):
        if self.game.start():
            self.play_sound("click")
            self.message = "Бій розпочато! Обирай ціль на полі ворога."
            self.set_banner("БІЙ РОЗПОЧАТО", AMBER)

    def toggle_plan(self):
        self.play_sound("click")
        self.show_plan = not self.show_plan

    def set_banner(self, text, color):
        self.banner = (text, color, self.time)

    def try_place(self, cell):
        length = self.game.next_ship_length()
        if length is None:
            return
        cells = ship_cells(cell[0], cell[1], length, self.horizontal)
        if self.game.player_board.place(cells):
            self.play_sound("place")
            x, y = cell_center(LEFT, cells[len(cells) // 2])
            self.fx.ripple(x, y)
            nxt = self.game.next_ship_length()
            self.message = f"Став корабель довжиною {nxt}." if nxt else "Усі кораблі розставлено. Натисни «СТАРТ»."

    def player_shoot(self, cell):
        if self.busy:
            return
        result = self.game.player_shoot(cell)
        if result is None:
            return
        self._launch("player", result, self.game.player_view)

    def _launch(self, who, result, view):
        shot = Shot(who, result, self.time, list(view.remaining))
        self.shells.append(shot)
        self.hidden |= shot.hidden
        self.play_sound("launch")
        if who == "ai" or self.game.phase == AI:
            self.next_ai_time = shot.land + AI_DELAY_MS

    def _land(self, shot):
        r = shot.result
        self.hidden -= shot.hidden
        origin = RIGHT if shot.who == "player" else LEFT
        x, y = cell_center(origin, r.cell)
        stats = self.stats[shot.who]
        stats[0] += 1
        stats[1] += 1 if r.hit else 0
        if shot.who == "player":
            self.shown_enemy = shot.remaining
        else:
            self.shown_own = shot.remaining
        tag = "Ви" if shot.who == "player" else "ШІ"
        if r.sunk:
            centers = [cell_center(origin, c) for c in r.ship_cells]
            self.fx.sunk_burst(centers)
            self.play_sound("sunk")
            text = f"{coord(r.cell)} · потоплено ({len(r.ship_cells)})"
            self.log_add(tag, text, BAD_C, shot.who)
            self.set_banner("ПОТОПЛЕНО!" if shot.who == "player" else "ВАШ КОРАБЕЛЬ ПОТОПЛЕНО", BAD_C)
            self.message = f"{tag}: {coord(r.cell)} — корабель потоплено (довжина {len(r.ship_cells)})!"
        elif r.hit:
            self.fx.explosion(x, y, 1.0)
            self.play_sound("hit")
            self.log_add(tag, f"{coord(r.cell)} · влучання", FIRE, shot.who)
            self.fx.popup("ВЛУЧАННЯ", x, y - 10, FIRE)
            self.message = f"{tag}: {coord(r.cell)} — влучання!"
        else:
            self.fx.splash(x, y)
            self.play_sound("splash")
            self.log_add(tag, f"{coord(r.cell)} · промах", DIM, shot.who)
            self.message = f"{tag}: {coord(r.cell)} — промах."

    def log_add(self, tag, text, color, who):
        self.log.insert(0, (tag, text, color, who))
        del self.log[40:]

    def _finish(self):
        self.over_at = self.time
        won = self.game.winner == "player"
        self.play_sound("win" if won else "lose")
        if won:
            self.fx.confetti(140)
            for i in range(7):
                self.fx.after(0.25 * i, self.fx.firework, 200 + (i * 173) % 880, 110 + (i * 59) % 190)
        else:
            for i in range(8):
                x, y = cell_center(LEFT, ((i * 3) % 10, (i * 7) % 10))
                self.fx.after(0.2 * i, self.fx.explosion, x, y, 1.1)

    def on_click(self, pos, button):
        for b in self.buttons:
            if button == 1 and b.hit(pos):
                b.action()
                return
        if self.scene == "menu":
            if button == 1:
                for i, (key, *_) in enumerate(LEVELS):
                    if self._card_rect(i).collidepoint(pos):
                        self.play_sound("click")
                        self.level = key
                        self.game.set_level(key)
            return
        g = self.game
        if self.over_ready:
            return
        if g.phase == PLACEMENT:
            if button == 3:
                self.rotate()
            elif button == 1:
                cell = self.left.cell_at(pos)
                if cell:
                    self.try_place(cell)
        elif g.phase == PLAYER and button == 1:
            cell = self.right.cell_at(pos)
            if cell:
                self.player_shoot(cell)

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.on_click(event.pos, event.button)
        elif event.type == pygame.KEYDOWN:
            self.on_key(event.key)

    def on_key(self, key):
        if key == pygame.K_ESCAPE:
            if self.scene == "menu":
                self.running = False
            else:
                self.to_menu()
        elif key == pygame.K_m:
            self.toggle_sound()
        elif key == pygame.K_F11 or key == pygame.K_f:
            pygame.display.toggle_fullscreen()
        elif self.scene == "menu":
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.start_from_menu()
        else:
            if key == pygame.K_r and self.game.phase == PLACEMENT:
                self.rotate()
            elif key == pygame.K_h and self.game.level in ("medium", "hard"):
                self.toggle_plan()
            elif key == pygame.K_n:
                self.again()
            elif key in (pygame.K_RETURN, pygame.K_SPACE) and self.game.phase == PLACEMENT:
                self.start()

    def frame(self, dt):
        self.mouse = pygame.mouse.get_pos()
        self.update(dt)
        self.draw()

    def update(self, dt):
        self.time += dt
        for shot in list(self.shells):
            if self.time >= shot.land:
                self.shells.remove(shot)
                self._land(shot)

        g = self.game
        if self.scene == "game":
            if g.phase == AI and not self.shells and self.time >= self.next_ai_time:
                result = g.ai_shoot()
                if result is not None:
                    self._launch("ai", result, g.ai_view)
            if g.phase == OVER and not self.shells and self.over_at is None:
                self._finish()
            self.smoke_timer -= dt
            if self.smoke_timer <= 0:
                self.smoke_timer = 170
                self._ambient_smoke()

        for key in self.card_hover:
            target = 1.0 if (self.scene == "menu" and self._card_rect_for(key).collidepoint(self.mouse)) else 0.0
            self.card_hover[key] += (target - self.card_hover[key]) * min(1.0, dt / 100.0)
        for b in self.buttons:
            b.update(self.mouse, dt)
        self.fx.update(dt / 1000.0)

    def _ambient_smoke(self):
        pairs = ((self.game.ai_view, LEFT), (self.game.player_view, RIGHT))
        for view, origin in pairs:
            cells = [(r, c) for r in range(10) for c in range(10) if view.grid[r][c] in (HIT, SUNK)
                     and (r, c) not in self.hidden]
            for cell in self.fx.rng.sample(cells, min(2, len(cells))):
                x, y = cell_center(origin, cell)
                self.fx.smoke(x, y)

    def _card_rect(self, i):
        x0 = (W - (3 * CARD_W + 2 * CARD_GAP)) // 2
        return pygame.Rect(x0 + i * (CARD_W + CARD_GAP), CARD_Y, CARD_W, CARD_H)

    def _card_rect_for(self, key):
        for i, (k, *_) in enumerate(LEVELS):
            if k == key:
                return self._card_rect(i)

    def _own_ships(self):
        out = []
        for ship in self.game.player_board.ships:
            wreck = ship.is_sunk and not (self.hidden & set(ship.cells))
            out.append((ship.cells, wreck))
        return out

    def _enemy_ships(self):
        out = []
        revealed = self.game.phase == OVER and not self.shells
        for ship in self.game.enemy_board.ships:
            if ship.is_sunk and not (self.hidden & set(ship.cells)):
                out.append((ship.cells, True))
            elif revealed:
                out.append((ship.cells, False))
        return out

    def draw(self):
        c = self.canvas
        t = self.time / 1000.0
        if self.scene == "menu":
            self.draw_menu(c, t)
        else:
            self.draw_game(c, t)
        self.fx.draw(c)
        for b in self.buttons:
            if b.visible():
                b.draw(c, self.fonts)
        self.screen.fill((4, 8, 16))
        self.screen.blit(c, self.fx.offset())
        pygame.display.flip()

    def draw_menu(self, c, t):
        self.bg.draw(c, t, menu=True)
        draw_text(c, self.fonts.huge, "МОРСЬКИЙ БІЙ", (110, 200, 255), (W // 2, 118), "center", shadow=(4, 14, 30))
        draw_text(c, self.fonts.h2, "Лабораторна робота 1 · Основи штучного інтелекту", TEXT, (W // 2, 188), "center")
        draw_text(c, self.fonts.body, "Обери рівень ШІ-супротивника, розстав флот і розпочни бій", DIM,
                  (W // 2, 226), "center")
        for i, (key, label, stars) in enumerate(LEVELS):
            rect = self._card_rect(i)
            k = self.card_hover[key]
            selected = self.level == key
            rect = rect.inflate(int(10 * k), int(10 * k)).move(0, -int(4 * k))
            border = (*ACCENT, 255) if selected else (80, 120, 170, 150)
            draw_panel(c, rect, (10, 22, 42, 215 if selected else 180), border, 16, 3 if selected else 1)
            draw_text(c, self.fonts.h1, label.upper(), ACCENT if selected else TEXT, (rect.x + 20, rect.y + 16))
            for s in range(3):
                col = AMBER if s < stars else (50, 66, 88)
                pygame.draw.circle(c, col, (rect.x + 28 + s * 26, rect.y + 70), 8)
            if selected:
                draw_text(c, self.fonts.smallb, "ОБРАНО", OK_C, (rect.right - 18, rect.y + 24), "topright")
        draw_text(c, self.fonts.small, "Enter — грати · M — звук · F — повний екран · Esc — вихід", DIM,
                  (W // 2, 752), "center")

    def draw_game(self, c, t):
        g = self.game
        self.bg.draw(c, t)
        draw_text(c, self.fonts.title, "МОРСЬКИЙ БІЙ", (110, 200, 255), (64, 16), shadow=(4, 14, 30))

        self.draw_status(c, t)

        draw_text(c, self.fonts.h2, "ВАШ ФЛОТ", TEXT, (LEFT[0], 156))
        draw_text(c, self.fonts.h2, "ФЛОТ ВОРОГА", TEXT, (RIGHT[0], 156))

        preview = None
        if g.phase == PLACEMENT and not self.over_ready:
            cell = self.left.cell_at(self.mouse)
            length = g.next_ship_length()
            if cell and length:
                cells = ship_cells(cell[0], cell[1], length, self.horizontal)
                preview = (cells, g.player_board.can_place(cells))

        plan = None
        if self.show_plan and g.phase in (PLAYER, AI) and g.level in ("medium", "hard"):
            plan = set(g.ai.planned_cells(g.ai_view))

        my_turn = g.phase == PLAYER and not self.busy
        hover = self.right.cell_at(self.mouse) if my_turn else None
        if hover and g.player_view.state(hover) != 0:
            hover = None
        self.left.draw(c, t, ships=self._own_ships(), knowledge=g.ai_view, hidden=self.hidden, plan=plan,
                       preview=preview, glow_color=BAD_C if g.phase == AI else None)
        self.right.draw(c, t, ships=self._enemy_ships(), knowledge=g.player_view, hidden=self.hidden,
                        hover=hover, glow_color=OK_C if g.phase == PLAYER else None,
                        radar=g.phase == PLAYER, veil=g.phase == PLACEMENT)

        if g.phase == PLACEMENT:
            self.draw_checklist(c, t)
        else:
            draw_text(c, self.fonts.smallb, "Ваші кораблі", DIM, (LEFT[0], 642))
            self.draw_fleet(c, LEFT[0], 666, self.shown_own)
            draw_text(c, self.fonts.smallb, "Кораблі ворога", DIM, (RIGHT[0], 642))
            self.draw_fleet(c, RIGHT[0], 666, self.shown_enemy)

        self.draw_stats(c)
        self.draw_log(c)
        self.draw_shells(c, t)
        self.draw_banner(c)
        if self.over_at is not None and not self.shells:
            self.draw_over(c)

    def draw_status(self, c, t):
        g = self.game
        draw_panel(c, STATUS_RECT)
        if g.phase == PLACEMENT:
            nxt = g.next_ship_length()
            text = (f"Розстановка: корабель довжиною {nxt} · {'горизонтально' if self.horizontal else 'вертикально'}"
                    if nxt else "Усі кораблі розставлено — натисни «СТАРТ»")
            color = AMBER
        elif g.phase == PLAYER:
            text, color = ("Ваш хід: клікни по полю ворога" if not self.busy else "Снаряд у польоті…"), OK_C
        elif g.phase == AI:
            dots = "." * (1 + int(t * 3) % 3)
            text, color = f"Хід комп'ютера{dots}", BAD_C
        else:
            won = g.winner == "player"
            text, color = ("ПЕРЕМОГА!" if won else "ПОРАЗКА"), (OK_C if won else BAD_C)
        pulse = 0.5 + 0.5 * math.sin(t * 4)
        pygame.draw.circle(c, color, (STATUS_RECT.x + 24, STATUS_RECT.centery), 6 + int(2 * pulse))
        draw_text(c, self.fonts.bodyb, text, color, (STATUS_RECT.x + 44, STATUS_RECT.y + 4))
        draw_text(c, self.fonts.small, self.message, DIM, (STATUS_RECT.x + 44, STATUS_RECT.y + 25))

    def draw_fleet(self, c, x, y, remaining):
        rem = list(remaining)
        cx = x
        for length in FLEET:
            alive = length in rem
            if alive:
                rem.remove(length)
            surf = ship_surface(length, True, 18, "normal" if alive else "wreck")
            c.blit(surf, (cx, y))
            cx += surf.get_width() + 8

    def draw_checklist(self, c, t):
        need = Counter(FLEET)
        have = Counter(len(s.cells) for s in self.game.player_board.ships)
        nxt = self.game.next_ship_length()
        panel = pygame.Rect(RIGHT[0] + 50, RIGHT[1] + 60, BOARD_PX - 100, 300)
        draw_panel(c, panel, (10, 22, 42, 225))
        draw_text(c, self.fonts.h2, "ФЛОТ ДЛЯ РОЗСТАНОВКИ", ACCENT, (panel.centerx, panel.y + 26), "center")
        for i, length in enumerate((4, 3, 2, 1)):
            y = panel.y + 66 + i * 54
            done = have[length] >= need[length]
            surf = ship_surface(length, True, 30, "dusk" if done else "normal")
            c.blit(surf, (panel.x + 26, y))
            label = f"× {need[length]}"
            draw_text(c, self.fonts.bodyb, label, TEXT, (panel.x + 26 + 4 * 30 + 16, y + 4))
            progress = f"{min(have[length], need[length])}/{need[length]}"
            draw_text(c, self.fonts.bodyb, progress, OK_C if done else AMBER, (panel.right - 26, y + 4), "topright")
            if nxt == length:
                pygame.draw.polygon(c, AMBER, [(panel.x + 8, y + 6), (panel.x + 8, y + 24), (panel.x + 20, y + 15)])
        draw_text(c, self.fonts.small, "ЛКМ — поставити · ПКМ або R — повернути", DIM,
                  (panel.centerx, panel.bottom - 22), "center")

    def draw_stats(self, c):
        draw_panel(c, STATS_RECT)
        r = STATS_RECT
        draw_text(c, self.fonts.h2, "СТАТИСТИКА", ACCENT, (r.x + 16, r.y + 12))
        draw_text(c, self.fonts.smallb, "Ви", OK_C, (r.x + 150, r.y + 44), "midtop")
        draw_text(c, self.fonts.smallb, "ШІ", BAD_C, (r.x + 200, r.y + 44), "midtop")
        p, a = self.stats["player"], self.stats["ai"]
        rows = [("Постріли", str(p[0]), str(a[0])), ("Влучання", str(p[1]), str(a[1])),
                ("Точність", self.pct(p), self.pct(a))]
        for i, (name, pv, av) in enumerate(rows):
            y = r.y + 72 + i * 30
            draw_text(c, self.fonts.body, name, DIM, (r.x + 16, y))
            draw_text(c, self.fonts.bodyb, pv, TEXT, (r.x + 150, y), "midtop")
            draw_text(c, self.fonts.bodyb, av, TEXT, (r.x + 200, y), "midtop")

    @staticmethod
    def pct(s):
        return f"{round(100 * s[1] / s[0])}%" if s[0] else "—"

    def draw_log(self, c):
        draw_panel(c, LOG_RECT)
        r = LOG_RECT
        draw_text(c, self.fonts.h2, "ЖУРНАЛ БОЮ", ACCENT, (r.x + 16, r.y + 12))
        for i, (tag, text, color, who) in enumerate(self.log[:10]):
            y = r.y + 48 + i * 28
            alpha = max(70, 255 - i * 22)
            tag_color = OK_C if who == "player" else BAD_C
            draw_text(c, self.fonts.smallb, tag, tag_color, (r.x + 16, y), alpha=alpha)
            draw_text(c, self.fonts.small, text, color if color != DIM else (170, 188, 210), (r.x + 52, y), alpha=alpha)
        if not self.log:
            draw_text(c, self.fonts.small, "Тут з'являтимуться ходи", DIM, (r.x + 16, r.y + 50))

    def _shell_pos(self, shot, k):
        origin = RIGHT if shot.who == "player" else LEFT
        tx, ty = cell_center(origin, shot.result.cell)
        if shot.who == "player":
            sx, sy = LEFT[0] + BOARD_PX // 2, LEFT[1] + BOARD_PX + 40
        else:
            sx, sy = RIGHT[0] + BOARD_PX // 2, RIGHT[1] - 120
        e = k * k * (3 - 2 * k)
        x = lerp(sx, tx, e)
        y = lerp(sy, ty, e) - math.sin(math.pi * k) * 190
        return x, y

    def draw_shells(self, c, t):
        for shot in self.shells:
            k = min(1.0, (self.time - shot.start) / SHELL_MS)
            color = (150, 230, 255) if shot.who == "player" else (255, 170, 90)
            origin = RIGHT if shot.who == "player" else LEFT
            tx, ty = cell_center(origin, shot.result.cell)
            ring = 10 + int(16 * (1 - k))
            pygame.draw.circle(c, color, (tx, ty), ring, 2)
            pygame.draw.line(c, color, (tx - 18, ty), (tx + 18, ty), 1)
            pygame.draw.line(c, color, (tx, ty - 18), (tx, ty + 18), 1)
            for j in range(10, -1, -1):
                kk = max(0.0, k - j * 0.018)
                x, y = self._shell_pos(shot, kk)
                level = max(1, 7 - j)
                radius = max(3, 12 - j)
                c.blit(glow(radius, color, level), (x - radius - 1, y - radius - 1), special_flags=pygame.BLEND_RGB_ADD)
            x, y = self._shell_pos(shot, k)
            pygame.draw.circle(c, (255, 255, 255), (int(x), int(y)), 4)

    def draw_banner(self, c):
        if not self.banner:
            return
        text, color, start = self.banner
        age = (self.time - start) / 1000.0
        if age > 1.6:
            self.banner = None
            return
        grow = min(1.0, age / 0.18)
        fade = 1.0 if age < 1.1 else max(0.0, 1 - (age - 1.1) / 0.5)
        img = self.fonts.h1.render(text, True, color)
        w, h = img.get_size()
        scale = 0.6 + 0.4 * grow
        img = pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))
        img.set_alpha(int(255 * fade))
        sh = pygame.Surface((img.get_width() + 80, img.get_height() + 30), pygame.SRCALPHA)
        pygame.draw.rect(sh, (4, 10, 22, int(170 * fade)), sh.get_rect(), border_radius=16)
        c.blit(sh, sh.get_rect(center=(775, 52)))
        c.blit(img, img.get_rect(center=(775, 52)))

    def draw_over(self, c):
        g = self.game
        age = min(1.0, (self.time - self.over_at) / 1300.0)
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((2, 6, 14, int(170 * age)))
        c.blit(shade, (0, 0))
        if not self.over_ready:
            return
        won = g.winner == "player"
        panel = pygame.Rect(W // 2 - 300, 190, 600, 400)
        draw_panel(c, panel, (8, 18, 34, 240), (*(OK_C if won else BAD_C), 255), 20, 3)
        draw_text(c, self.fonts.title, "ПЕРЕМОГА!" if won else "ПОРАЗКА", OK_C if won else BAD_C,
                  (panel.centerx, panel.y + 56), "center", shadow=(0, 0, 0))
        sub = ("Ти потопив увесь флот ворога" if won else "Комп'ютер потопив твій флот")
        draw_text(c, self.fonts.body, sub, TEXT, (panel.centerx, panel.y + 104), "center")
        p, a = self.stats["player"], self.stats["ai"]
        draw_text(c, self.fonts.smallb, "Ви", OK_C, (panel.centerx + 60, panel.y + 150), "midtop")
        draw_text(c, self.fonts.smallb, "ШІ", BAD_C, (panel.centerx + 170, panel.y + 150), "midtop")
        rows = [("Постріли", str(p[0]), str(a[0])), ("Влучання", str(p[1]), str(a[1])),
                ("Точність", self.pct(p), self.pct(a))]
        for i, (name, pv, av) in enumerate(rows):
            y = panel.y + 182 + i * 34
            draw_text(c, self.fonts.body, name, DIM, (panel.x + 120, y))
            draw_text(c, self.fonts.bodyb, pv, TEXT, (panel.centerx + 60, y), "midtop")
            draw_text(c, self.fonts.bodyb, av, TEXT, (panel.centerx + 170, y), "midtop")

    def run(self):
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)
            self.frame(self.clock.tick(60))
        pygame.quit()


def run():
    App().run()
    sys.exit(0)
