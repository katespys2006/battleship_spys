import math
import random
from functools import lru_cache

import pygame

SS = 3

ACCENTS = {
    4: (214, 96, 72),
    3: (226, 164, 64),
    2: (84, 168, 204),
    1: (120, 196, 142),
}

PALETTES = {
    "normal": {"edge": (30, 40, 54), "hull": (112, 128, 146), "deck": (158, 172, 188),
               "cabin": (210, 220, 230), "dark": (60, 72, 88), "accent": None},
    "wreck": {"edge": (14, 14, 16), "hull": (52, 48, 46), "deck": (72, 66, 62),
              "cabin": (84, 78, 74), "dark": (30, 28, 28), "accent": (96, 44, 32)},
    "dusk": {"edge": (6, 12, 22), "hull": (20, 34, 54), "deck": (30, 48, 72),
             "cabin": (40, 62, 90), "dark": (12, 22, 38), "accent": (36, 60, 90)},
}


def _poly(x0, y0, x1, y1, bow, cut):
    ym = (y0 + y1) / 2
    return [(x0 + cut, y0), (x1 - bow, y0), (x1, ym), (x1 - bow, y1), (x0 + cut, y1),
            (x0, y1 - cut), (x0, y0 + cut)]


@lru_cache(maxsize=None)
def _horizontal(length, cell, mode):
    base_mode = mode if mode in PALETTES else "normal"
    pal = PALETTES[base_mode]
    accent = pal["accent"] or ACCENTS[length]
    c = cell * SS
    w, h = length * c, c
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    mx, my = int(c * 0.12), int(c * 0.2)
    x0, y0, x1, y1 = mx, my, w - mx, h - my
    span = x1 - x0
    bow = span * 0.45 if length == 1 else min(c * 0.95, span * 0.36)
    cut = c * 0.08

    shadow = _poly(x0 + c * 0.05, y0 + c * 0.09, x1 + c * 0.03, y1 + c * 0.09, bow, cut)
    pygame.draw.polygon(surf, (0, 10, 24, 90), shadow)
    pygame.draw.polygon(surf, pal["edge"], _poly(x0, y0, x1, y1, bow, cut))
    ins = c * 0.06
    pygame.draw.polygon(surf, pal["hull"], _poly(x0 + ins, y0 + ins, x1 - ins, y1 - ins, bow * 0.92, cut * 0.8))
    ins2 = c * 0.15
    pygame.draw.polygon(surf, pal["deck"], _poly(x0 + ins2, y0 + ins2, x1 - ins2 * 1.3, y1 - ins2, bow * 0.8, cut * 0.6))

    ym = (y0 + y1) / 2
    stripe_h = c * 0.07
    pygame.draw.rect(surf, accent, (x0 + span * 0.1, ym - stripe_h / 2, span * (0.72 if length > 1 else 0.3), stripe_h))

    if length >= 2:
        bw = c * (0.62 if length >= 3 else 0.5)
        bh = c * 0.34
        bx = x0 + span * 0.26
        pygame.draw.rect(surf, pal["dark"], (bx - 3, ym - bh / 2 - 3, bw + 6, bh + 6), border_radius=int(c * 0.06))
        pygame.draw.rect(surf, pal["cabin"], (bx, ym - bh / 2, bw, bh), border_radius=int(c * 0.05))
        pygame.draw.rect(surf, pal["dark"], (bx + bw * 0.12, ym - bh * 0.18, bw * 0.76, bh * 0.22))
    else:
        bw, bh = c * 0.3, c * 0.24
        bx = x0 + span * 0.22
        pygame.draw.rect(surf, pal["dark"], (bx - 2, ym - bh / 2 - 2, bw + 4, bh + 4), border_radius=int(c * 0.05))
        pygame.draw.rect(surf, pal["cabin"], (bx, ym - bh / 2, bw, bh), border_radius=int(c * 0.05))

    if length >= 3:
        fx = x0 + span * 0.5
        r = c * 0.13
        pygame.draw.circle(surf, pal["dark"], (fx, ym), r + 3)
        pygame.draw.circle(surf, accent, (fx, ym), r)
        pygame.draw.circle(surf, (14, 16, 20), (fx, ym), r * 0.55)

    turrets = {4: (0.74, 0.12), 3: (0.74,), 2: (0.7,)}.get(length, ())
    for t in turrets:
        tx = x0 + span * t
        r = c * (0.13 if length >= 3 else 0.09)
        pygame.draw.line(surf, pal["edge"], (tx, ym), (tx + c * 0.34, ym), max(3, int(c * 0.06)))
        pygame.draw.circle(surf, pal["edge"], (tx, ym), r + 3)
        pygame.draw.circle(surf, pal["hull"], (tx, ym), r)
        pygame.draw.circle(surf, pal["cabin"], (tx - r * 0.25, ym - r * 0.25), r * 0.4)

    if base_mode == "wreck":
        rng = random.Random(length * 31 + cell)
        for _ in range(length * 3):
            px = rng.uniform(x0 + c * 0.2, x1 - c * 0.3)
            py = rng.uniform(y0 + c * 0.1, y1 - c * 0.1)
            pygame.draw.circle(surf, (10, 10, 10, 190), (px, py), rng.uniform(c * 0.07, c * 0.2))
        pygame.draw.line(surf, (12, 12, 12), (x0 + span * 0.45, y0), (x0 + span * 0.55, y1), max(2, int(c * 0.05)))

    out = pygame.transform.smoothscale(surf, (length * cell, cell))
    return out


@lru_cache(maxsize=None)
def ship_surface(length, horizontal, cell, mode="normal"):
    base_mode = mode if mode in PALETTES else "normal"
    surf = _horizontal(length, cell, base_mode).copy()
    if mode == "ok":
        surf.fill((140, 255, 170, 255), special_flags=pygame.BLEND_RGBA_MULT)
        surf.set_alpha(200)
    elif mode == "bad":
        surf.fill((255, 120, 120, 255), special_flags=pygame.BLEND_RGBA_MULT)
        surf.set_alpha(200)
    if not horizontal:
        surf = pygame.transform.rotate(surf, -90)
    return surf


def place_ship(cells):
    rows = [r for r, _ in cells]
    cols = [c for _, c in cells]
    horizontal = len(set(rows)) == 1
    return (min(rows), min(cols)), len(cells), horizontal


def bob(t, cells, amp=1.3):
    ph = (cells[0][0] * 7 + cells[0][1] * 3) % 11
    return math.sin(t * 1.6 + ph) * amp
