import os

import pygame

W, H = 1280, 780
SIZE = 10
CELL = 42
BOARD_PX = CELL * SIZE

LEFT = (64, 206)
RIGHT = (548, 206)

STATUS_RECT = pygame.Rect(64, 108, 904, 44)
STATS_RECT = pygame.Rect(1010, 108, 230, 170)
LOG_RECT = pygame.Rect(1010, 290, 230, 336)

AI_DELAY_MS = 700
SHELL_MS = 520

TEXT = (232, 240, 248)
DIM = (128, 148, 172)
ACCENT = (80, 200, 240)
AMBER = (255, 176, 64)
OK_C = (96, 220, 140)
BAD_C = (240, 92, 92)
FIRE = (255, 120, 50)
PANEL_FILL = (10, 20, 38, 205)
PANEL_BORDER = (80, 120, 170, 130)

LETTERS = "АБВГДЕЖЗИК"

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS = os.path.join(ROOT, "assets")


def coord(cell):
    return f"{LETTERS[cell[1]]}{cell[0] + 1}"


def cell_rect(origin, cell):
    return pygame.Rect(origin[0] + cell[1] * CELL, origin[1] + cell[0] * CELL, CELL, CELL)


def cell_center(origin, cell):
    return cell_rect(origin, cell).center


def lerp(a, b, k):
    return a + (b - a) * k


def mix(c1, c2, k):
    return tuple(int(lerp(c1[i], c2[i], k)) for i in range(3))


def _load(file, size, bold=False):
    path = os.path.join(ASSETS, "fonts", file)
    if os.path.exists(path):
        return pygame.font.Font(path, size)
    return pygame.font.SysFont("arial,helveticaneue,helvetica,dejavusans,liberationsans", size, bold=bold)


class Fonts:
    def __init__(self):
        display = "RussoOne-Regular.ttf"
        regular = "PT_Sans-Web-Regular.ttf"
        bold = "PT_Sans-Web-Bold.ttf"
        self.huge = _load(display, 84, True)
        self.title = _load(display, 52, True)
        self.h1 = _load(display, 30, True)
        self.h2 = _load(display, 20, True)
        self.coord = _load(display, 14, True)
        self.body = _load(regular, 19)
        self.bodyb = _load(bold, 19, True)
        self.small = _load(regular, 15)
        self.smallb = _load(bold, 15, True)
        self.btn = _load(bold, 18, True)
