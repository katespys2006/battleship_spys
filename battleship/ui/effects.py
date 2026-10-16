import math
import random
from functools import lru_cache

import pygame

from .theme import AMBER


@lru_cache(maxsize=None)
def glow(radius, color, level):
    size = radius * 2 + 2
    surf = pygame.Surface((size, size))
    surf.fill((0, 0, 0))
    k = level / 7.0
    for i in range(radius, 0, -1):
        f = (1.0 - i / radius) ** 1.6 * k
        col = (int(color[0] * f), int(color[1] * f), int(color[2] * f))
        pygame.draw.circle(surf, col, (radius + 1, radius + 1), i)
    return surf


@lru_cache(maxsize=None)
def soft(radius):
    size = radius * 2 + 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    for i in range(radius, 0, -1):
        a = int(255 * (1.0 - i / radius) ** 1.1)
        pygame.draw.circle(surf, (74, 76, 86, a), (radius + 1, radius + 1), i)
    return surf


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max", "s0", "s1", "color", "kind", "gravity", "drag", "spin")

    def __init__(self, x, y, vx, vy, life, s0, s1, color, kind, gravity=0.0, drag=0.0, spin=0.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max = life
        self.s0, self.s1 = s0, s1
        self.color, self.kind = color, kind
        self.gravity, self.drag, self.spin = gravity, drag, spin


class Effects:
    def __init__(self, fonts):
        self.fonts = fonts
        self.particles = []
        self.rings = []
        self.popups = []
        self.scheduled = []
        self.shake_amp = 0.0
        self.rng = random.Random()

    def clear(self):
        self.particles.clear()
        self.rings.clear()
        self.popups.clear()
        self.scheduled.clear()
        self.shake_amp = 0.0

    def after(self, delay, fn, *args):
        self.scheduled.append([delay, fn, args])

    def shake(self, amount):
        self.shake_amp = max(self.shake_amp, amount)

    def offset(self):
        if self.shake_amp < 0.3:
            return 0, 0
        a = self.shake_amp
        return int(self.rng.uniform(-a, a)), int(self.rng.uniform(-a, a))

    def splash(self, x, y):
        for i in range(3):
            self.rings.append([x, y, -0.12 * i, 0.9, 30 + i * 6, (210, 238, 255)])
        for _ in range(16):
            ang = self.rng.uniform(-math.pi * 0.95, -math.pi * 0.05)
            sp = self.rng.uniform(70, 190)
            self.particles.append(Particle(x, y, math.cos(ang) * sp * 0.55, math.sin(ang) * sp,
                                           self.rng.uniform(0.5, 0.85), 3, 1, (200, 232, 255), "drop",
                                           gravity=520))
        self.particles.append(Particle(x, y, 0, 0, 0.35, 24, 4, (80, 150, 210), "fire"))

    def explosion(self, x, y, scale=1.0):
        self.particles.append(Particle(x, y, 0, 0, 0.3, 46 * scale, 8, (255, 220, 150), "fire"))
        for _ in range(int(26 * scale)):
            ang = self.rng.uniform(0, math.tau)
            sp = self.rng.uniform(40, 230) * scale
            color = self.rng.choice([(255, 120, 40), (255, 180, 60), (255, 90, 30), (255, 230, 140)])
            self.particles.append(Particle(x, y, math.cos(ang) * sp, math.sin(ang) * sp,
                                           self.rng.uniform(0.35, 0.8), 15 * scale, 3, color, "fire", drag=2.4))
        for _ in range(int(14 * scale)):
            ang = self.rng.uniform(0, math.tau)
            sp = self.rng.uniform(120, 320) * scale
            self.particles.append(Particle(x, y, math.cos(ang) * sp, math.sin(ang) * sp - 40,
                                           self.rng.uniform(0.4, 0.9), 4, 1, (255, 235, 170), "spark",
                                           gravity=380, drag=0.8))
        for _ in range(int(10 * scale)):
            self.particles.append(Particle(x + self.rng.uniform(-8, 8), y + self.rng.uniform(-8, 8),
                                           self.rng.uniform(-24, 24), self.rng.uniform(-70, -25),
                                           self.rng.uniform(1.2, 2.2), 10 * scale, 30 * scale, (70, 72, 80), "smoke"))
        self.shake(5.0 * scale)

    def sunk_burst(self, centers):
        for i, (x, y) in enumerate(centers):
            self.after(0.09 * i, self.explosion, x, y, 1.15)
        cx = sum(p[0] for p in centers) / len(centers)
        cy = sum(p[1] for p in centers) / len(centers)
        self.after(0.09 * len(centers), self.ring_burst, cx, cy)
        self.shake(9.0)

    def ring_burst(self, x, y):
        self.rings.append([x, y, 0.0, 0.7, 110, (255, 190, 100)])
        self.rings.append([x, y, -0.1, 0.8, 150, (255, 140, 60)])

    def smoke(self, x, y):
        self.particles.append(Particle(x + self.rng.uniform(-6, 6), y - 4, self.rng.uniform(-10, 10),
                                       self.rng.uniform(-48, -26), self.rng.uniform(1.4, 2.2), 8, 26,
                                       (70, 72, 80), "smoke"))

    def ripple(self, x, y, color=(210, 238, 255)):
        self.rings.append([x, y, 0.0, 0.8, 24, color])

    def firework(self, x, y):
        color = self.rng.choice([(255, 120, 120), (255, 210, 90), (120, 220, 255), (150, 255, 160), (230, 150, 255)])
        for _ in range(46):
            ang = self.rng.uniform(0, math.tau)
            sp = self.rng.uniform(60, 250)
            self.particles.append(Particle(x, y, math.cos(ang) * sp, math.sin(ang) * sp, self.rng.uniform(0.9, 1.5),
                                           9, 1, color, "fire", gravity=140, drag=1.6))
        self.particles.append(Particle(x, y, 0, 0, 0.25, 60, 10, (255, 255, 255), "fire"))
        self.shake(2.0)

    def confetti(self, count=120):
        palette = [(255, 120, 120), (255, 210, 90), (120, 220, 255), (150, 255, 160), (230, 150, 255)]
        for _ in range(count):
            self.particles.append(Particle(self.rng.uniform(0, 1280), self.rng.uniform(-200, -10),
                                           self.rng.uniform(-30, 30), self.rng.uniform(70, 190),
                                           self.rng.uniform(3.5, 6.0), 8, 8, self.rng.choice(palette), "confetti",
                                           gravity=20, spin=self.rng.uniform(-6, 6)))

    def popup(self, text, x, y, color=AMBER):
        self.popups.append([text, x, y, 0.0, 1.1, color])

    def update(self, dt):
        for item in self.scheduled:
            item[0] -= dt
        due = [s for s in self.scheduled if s[0] <= 0]
        self.scheduled = [s for s in self.scheduled if s[0] > 0]
        for _, fn, args in due:
            fn(*args)

        alive = []
        for p in self.particles:
            p.life -= dt
            if p.life <= 0:
                continue
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy += p.gravity * dt
            if p.drag:
                f = max(0.0, 1.0 - p.drag * dt)
                p.vx *= f
                p.vy *= f
            alive.append(p)
        self.particles = alive

        for ring in self.rings:
            ring[2] += dt
        self.rings = [r for r in self.rings if r[2] < r[3]]
        for pop in self.popups:
            pop[3] += dt
        self.popups = [p for p in self.popups if p[3] < p[4]]
        self.shake_amp *= math.exp(-9.0 * dt)

    def draw(self, screen):
        for p in self.particles:
            if p.kind == "smoke":
                k = p.life / p.max
                size = int(p.s0 + (p.s1 - p.s0) * (1 - k))
                if size < 2:
                    continue
                img = soft(size)
                img.set_alpha(int(150 * k))
                screen.blit(img, (p.x - size - 1, p.y - size - 1))

        for r in self.rings:
            age = r[2]
            if age < 0:
                continue
            k = age / r[3]
            radius = int(4 + (r[4] - 4) * (1 - (1 - k) ** 2))
            size = radius * 2 + 8
            tmp = pygame.Surface((size, size), pygame.SRCALPHA)
            alpha = int(220 * (1 - k))
            pygame.draw.circle(tmp, (*r[5], alpha), (size // 2, size // 2), radius, max(1, int(3 * (1 - k)) + 1))
            screen.blit(tmp, (r[0] - size // 2, r[1] - size // 2))

        for p in self.particles:
            k = p.life / p.max
            size = p.s0 + (p.s1 - p.s0) * (1 - k)
            if p.kind in ("fire", "spark"):
                level = int(7 * k ** 0.8)
                radius = int(size)
                if level <= 0 or radius < 1:
                    continue
                screen.blit(glow(radius, p.color, level), (p.x - radius - 1, p.y - radius - 1),
                            special_flags=pygame.BLEND_RGB_ADD)
            elif p.kind == "drop":
                pygame.draw.circle(screen, p.color, (int(p.x), int(p.y)), max(1, int(size)))
            elif p.kind == "confetti":
                ang = p.spin * (p.max - p.life)
                dx, dy = math.cos(ang) * size, math.sin(ang) * size * 0.5
                pts = [(p.x - dx, p.y - dy), (p.x + dy, p.y - dx * 0.4), (p.x + dx, p.y + dy), (p.x - dy, p.y + dx * 0.4)]
                pygame.draw.polygon(screen, p.color, pts)

        for text, x, y, age, dur, color in self.popups:
            k = age / dur
            img = self.fonts.h2.render(text, True, color)
            img.set_alpha(int(255 * (1 - k ** 2)))
            screen.blit(img, img.get_rect(center=(x, y - 34 * k)))
