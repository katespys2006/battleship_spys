import math
import random

import pygame

from .effects import soft
from .ships_art import ship_surface
from .theme import H, W, mix


class Background:
    def __init__(self):
        rng = random.Random(4)
        self.base = pygame.Surface((W, H))
        top, mid, bottom = (6, 10, 22), (12, 30, 58), (14, 52, 88)
        for y in range(H):
            k = y / H
            col = mix(top, mid, k / 0.55) if k < 0.55 else mix(mid, bottom, (k - 0.55) / 0.45)
            pygame.draw.line(self.base, col, (0, y), (W, y))
        self.stars = [(rng.randrange(W), rng.randrange(0, 150), rng.choice((1, 1, 2)), rng.uniform(0, 6.28))
                      for _ in range(70)]
        self.fog = [(rng.uniform(0, W), rng.uniform(110, H - 60), rng.randrange(90, 180), rng.uniform(4, 14))
                    for _ in range(7)]
        self.wave_surface = pygame.Surface((W, 340), pygame.SRCALPHA)
        self.ships = [(4, 0.0, 22), (3, 0.38, 17), (2, 0.7, 28), (3, 0.9, 14)]

    def draw(self, screen, t, menu=False):
        screen.blit(self.base, (0, 0))
        for x, y, r, ph in self.stars:
            v = int(110 + 100 * math.sin(t * 1.2 + ph))
            pygame.draw.circle(screen, (v, v, min(255, v + 25)), (x, y), r)

        if menu:
            moon = soft(110)
            moon.set_alpha(90)
            screen.blit(moon, (1010 - 111, 130 - 111))
            pygame.draw.circle(screen, (226, 234, 246), (1010, 130), 34)
            pygame.draw.circle(screen, (206, 216, 232), (999, 120), 7)
            pygame.draw.circle(screen, (206, 216, 232), (1020, 140), 5)

        for x0, y, r, speed in self.fog:
            x = (x0 + t * speed) % (W + 2 * r) - r
            img = soft(r)
            img.set_alpha(26)
            screen.blit(img, (x - r, y - r))

        if menu:
            for length, phase, speed in self.ships:
                surf = ship_surface(length, True, 78, "dusk")
                span = W + surf.get_width() + 80
                x = (phase * span + t * speed) % span - surf.get_width() - 40
                y = H - 128 + (length % 3) * 8 + math.sin(t * 1.1 + phase * 9) * 3
                screen.blit(surf, (x, y))

        base_y = H - (300 if menu else 100)
        self.wave_surface.fill((0, 0, 0, 0))
        offset = 340 - (H - base_y)
        layers = [((20, 70, 120, 90), 0.0, 9, 0.9, 0), ((24, 84, 140, 90), 1.3, 7, 1.3, 22),
                  ((30, 100, 160, 100), 2.1, 6, 1.7, 46), ((18, 60, 108, 150), 3.4, 5, 2.1, 70)]
        for color, phase, amp, speed, drop in layers:
            pts = [(0, 340)]
            for x in range(0, W + 16, 16):
                y = offset + drop + math.sin(x * 0.012 + t * speed + phase) * amp + math.sin(x * 0.031 - t * speed * 0.7) * amp * 0.4
                pts.append((x, y))
            pts.append((W, 340))
            pygame.draw.polygon(self.wave_surface, color, pts)
        screen.blit(self.wave_surface, (0, H - 340))
