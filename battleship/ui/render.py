import math

import pygame

from ..knowledge import HIT, MISS, SUNK, UNKNOWN
from .effects import glow
from .ships_art import bob, place_ship, ship_surface
from .theme import AMBER, BOARD_PX, CELL, DIM, LETTERS, SIZE, mix


def _water_surface():
    surf = pygame.Surface((BOARD_PX, BOARD_PX))
    top, bottom = (30, 98, 146), (12, 48, 92)
    for y in range(BOARD_PX):
        pygame.draw.line(surf, mix(top, bottom, y / BOARD_PX), (0, y), (BOARD_PX, y))
    shade = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
    shade.fill((255, 255, 255, 9))
    for r in range(SIZE):
        for c in range(SIZE):
            if (r + c) % 2 == 0:
                surf.blit(shade, (c * CELL, r * CELL))
    return surf


def _grid_surface():
    surf = pygame.Surface((BOARD_PX, BOARD_PX), pygame.SRCALPHA)
    for i in range(SIZE + 1):
        pygame.draw.line(surf, (190, 225, 255, 46), (i * CELL, 0), (i * CELL, BOARD_PX))
        pygame.draw.line(surf, (190, 225, 255, 46), (0, i * CELL), (BOARD_PX, i * CELL))
    return surf


class BoardView:
    def __init__(self, origin, fonts):
        self.origin = origin
        self.fonts = fonts
        self.rect = pygame.Rect(origin, (BOARD_PX, BOARD_PX))
        self.water = _water_surface()
        self.grid = _grid_surface()
        self.fx = pygame.Surface((BOARD_PX, BOARD_PX), pygame.SRCALPHA)

    def cell_at(self, pos):
        x, y = pos[0] - self.origin[0], pos[1] - self.origin[1]
        if 0 <= x < BOARD_PX and 0 <= y < BOARD_PX:
            return (y // CELL, x // CELL)
        return None

    def _waves(self, t):
        fx = self.fx
        for k in range(13):
            base = k * BOARD_PX / 12
            pts = []
            for x in range(0, BOARD_PX + 8, 8):
                y = base + math.sin(x * 0.045 + t * 1.5 + k * 1.7) * 2.6 + math.sin(x * 0.11 - t * 0.9 + k) * 1.2
                pts.append((x, y))
            pygame.draw.lines(fx, (255, 255, 255, 24 if k % 2 else 15), False, pts, 1)

    def _flame(self, t, cx, cy, ph):
        for i in range(3):
            f = math.sin(t * 9 + ph + i * 2.1)
            h = 17 + 7 * f
            w = 7 - i * 1.2
            sway = math.sin(t * 5 + ph + i) * 2.5
            offx = (i - 1) * 6
            color = ((255, 120, 30, 225), (255, 190, 60, 235), (255, 246, 180, 245))[i]
            scale = (1.0, 0.72, 0.42)[i]
            pts = [(cx + offx - w, cy + 8), (cx + offx - w * 0.7, cy - h * 0.35 * scale),
                   (cx + offx + sway, cy + 6 - h * scale), (cx + offx + w * 0.7, cy - h * 0.35 * scale),
                   (cx + offx + w, cy + 8)]
            pygame.draw.polygon(self.fx, color, pts)

    def draw(self, screen, t, *, ships, knowledge, hidden, plan=None, preview=None, hover=None,
             glow_color=None, radar=False, veil=False, hover_color=AMBER):
        ox, oy = self.origin
        screen.blit(self.water, self.origin)

        fx = self.fx
        fx.fill((0, 0, 0, 0))
        self._waves(t)
        fx.blit(self.grid, (0, 0))

        if radar:
            ang = t * 1.1
            cx = cy = BOARD_PX / 2
            for i in range(36):
                a = ang - i * 0.016
                alpha = int(70 * (1 - i / 36) ** 1.5)
                pygame.draw.line(fx, (110, 255, 190, alpha), (cx, cy),
                                 (cx + math.cos(a) * BOARD_PX, cy + math.sin(a) * BOARD_PX), 6)

        def state(cell):
            return UNKNOWN if cell in hidden else knowledge.grid[cell[0]][cell[1]]

        screen.blit(fx, self.origin)
        fx.fill((0, 0, 0, 0))

        clip = screen.get_clip()
        screen.set_clip(self.rect)
        for cells, wreck in ships:
            (r, c), length, horizontal = place_ship(cells)
            surf = ship_surface(length, horizontal, CELL, "wreck" if wreck else "normal")
            screen.blit(surf, (ox + c * CELL, oy + r * CELL + bob(t, cells, 0.6 if wreck else 1.3)))
        if preview:
            cells, valid = preview
            (r, c), length, horizontal = place_ship(cells)
            surf = ship_surface(length, horizontal, CELL, "ok" if valid else "bad")
            screen.blit(surf, (ox + c * CELL, oy + r * CELL))
            tint = (80, 220, 130, 60) if valid else (240, 80, 80, 70)
            for rr, cc in cells:
                if 0 <= rr < SIZE and 0 <= cc < SIZE:
                    pygame.draw.rect(fx, tint, (cc * CELL, rr * CELL, CELL, CELL))
        screen.set_clip(clip)

        pulse = 0.5 + 0.5 * math.sin(t * 3)
        flames = []
        embers = []
        for r in range(SIZE):
            for c in range(SIZE):
                st = state((r, c))
                cx, cy = c * CELL + CELL // 2, r * CELL + CELL // 2
                if st == MISS:
                    ph = (r * 5 + c * 3) % 7
                    rad = 7 + int(2 * math.sin(t * 2 + ph))
                    pygame.draw.circle(fx, (225, 240, 255, 70), (cx, cy), rad, 1)
                    pygame.draw.circle(fx, (235, 245, 255, 190), (cx, cy), 3)
                elif st == HIT:
                    pygame.draw.circle(fx, (0, 0, 0, 110), (cx, cy + 3), 15)
                    flames.append((cx, cy, (r * 13 + c * 7) % 17))
                elif st == SUNK:
                    pygame.draw.circle(fx, (0, 0, 0, 120), (cx, cy), 14)
                    embers.append((cx, cy, (r * 11 + c * 5) % 13))

        if plan:
            for (r, c) in plan:
                if state((r, c)) == UNKNOWN:
                    pygame.draw.rect(fx, (255, 150, 0, int(55 + 55 * pulse)),
                                     (c * CELL + 2, r * CELL + 2, CELL - 4, CELL - 4), border_radius=6)

        for cx, cy, ph in flames:
            self._flame(t, cx, cy, ph)
        for cx, cy, ph in embers:
            if math.sin(t * 6 + ph) > -0.2:
                pygame.draw.circle(fx, (255, 140, 50, 190), (cx - 8 + ph % 5 * 4, cy - 3 + ph % 3 * 4), 2)

        if hover and not preview:
            r, c = hover
            x, y = c * CELL, r * CELL
            pygame.draw.rect(fx, (*hover_color, 38), (x, y, CELL, CELL))
            grow = int(2 + 2 * math.sin(t * 7))
            x, y, s = x - grow, y - grow, CELL + grow * 2
            L = 11
            col = (*hover_color, 240)
            for px, py, dx, dy in ((x, y, 1, 1), (x + s, y, -1, 1), (x, y + s, 1, -1), (x + s, y + s, -1, -1)):
                pygame.draw.line(fx, col, (px, py), (px + dx * L, py), 3)
                pygame.draw.line(fx, col, (px, py), (px, py + dy * L), 3)
            mid = CELL // 2
            pygame.draw.line(fx, (*hover_color, 150), (c * CELL + mid - 4, r * CELL + mid), (c * CELL + mid + 4, r * CELL + mid), 1)
            pygame.draw.line(fx, (*hover_color, 150), (c * CELL + mid, r * CELL + mid - 4), (c * CELL + mid, r * CELL + mid + 4), 1)

        screen.blit(fx, self.origin)

        for cx, cy, ph in flames:
            level = int(4 + 3 * (0.5 + 0.5 * math.sin(t * 8 + ph)))
            screen.blit(glow(26, (255, 130, 40), level), (ox + cx - 27, oy + cy - 27), special_flags=pygame.BLEND_RGB_ADD)

        if veil:
            shade = pygame.Surface((BOARD_PX, BOARD_PX), pygame.SRCALPHA)
            shade.fill((6, 12, 24, 170))
            screen.blit(shade, self.origin)

        self._frame(screen, t, glow_color)
        self._labels(screen)

    def _frame(self, screen, t, glow_color):
        rect = self.rect.inflate(10, 10)
        if glow_color:
            k = 0.55 + 0.45 * math.sin(t * 3)
            for i in range(7, 0, -1):
                col = mix((10, 22, 42), glow_color, (1 - i / 8) * 0.6 * k)
                pygame.draw.rect(screen, col, rect.inflate(i * 3, i * 3), 2, border_radius=14 + i)
        pygame.draw.rect(screen, (120, 150, 184), rect, 3, border_radius=10)
        pygame.draw.rect(screen, (24, 40, 64), rect.inflate(-6, -6), 2, border_radius=8)
        for pos in (rect.topleft, rect.topright, rect.bottomleft, rect.bottomright):
            pygame.draw.circle(screen, (170, 196, 224), pos, 4)
            pygame.draw.circle(screen, (60, 80, 106), pos, 2)

    def _labels(self, screen):
        ox, oy = self.origin
        for i in range(SIZE):
            img = self.fonts.coord.render(LETTERS[i], True, DIM)
            screen.blit(img, img.get_rect(center=(ox + i * CELL + CELL // 2, oy - 18)))
            img = self.fonts.coord.render(str(i + 1), True, DIM)
            screen.blit(img, img.get_rect(center=(ox - 20, oy + i * CELL + CELL // 2)))
