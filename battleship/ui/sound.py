import array
import math
import random

import pygame


class SoundBank:
    def __init__(self):
        self.enabled = True
        self.available = False
        self.sounds = {}
        self.rate = 22050
        self.channels = 1
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
            init = pygame.mixer.get_init()
        except pygame.error:
            return
        if not init:
            return
        self.rate, _, self.channels = init
        self._build()
        self.available = True

    def _sine(self, f0, f1, dur, vol=1.0, decay=3.0, attack=0.004):
        n = int(self.rate * dur)
        out, phase = [], 0.0
        for i in range(n):
            k = i / n
            phase += math.tau * (f0 + (f1 - f0) * k) / self.rate
            env = min(1.0, i / (self.rate * attack + 1)) * math.exp(-decay * k)
            out.append(math.sin(phase) * env * vol)
        return out

    def _noise(self, dur, vol=1.0, decay=4.0, cut0=0.5, cut1=0.05, swell=False, seed=7):
        rng = random.Random(seed)
        n = int(self.rate * dur)
        out, y = [], 0.0
        for i in range(n):
            k = i / n
            a = cut0 + (cut1 - cut0) * k
            y += a * (rng.uniform(-1, 1) - y)
            if swell:
                env = math.sin(math.pi * k) ** 1.5
            else:
                env = min(1.0, i / (self.rate * 0.003 + 1)) * math.exp(-decay * k)
            out.append(y * env * vol * 2.4)
        return out

    def _mix(self, parts):
        length = max(int(off * self.rate) + len(s) for off, s in parts)
        buf = [0.0] * length
        for off, samples in parts:
            start = int(off * self.rate)
            for i, v in enumerate(samples):
                buf[start + i] += v
        return buf

    def _make(self, samples, volume=0.6):
        data = array.array("h")
        for v in samples:
            s = max(-1.0, min(1.0, v * volume))
            iv = int(s * 32000)
            for _ in range(self.channels):
                data.append(iv)
        return pygame.mixer.Sound(buffer=data.tobytes())

    def _build(self):
        s = self.sounds
        s["click"] = self._make(self._sine(880, 640, 0.07, 0.8, 5.0))
        s["place"] = self._make(self._mix([(0, self._sine(220, 110, 0.12, 0.9, 5.0)),
                                           (0, self._noise(0.08, 0.4, 6.0, 0.4, 0.2))]))
        s["launch"] = self._make(self._mix([(0, self._noise(0.5, 0.55, cut0=0.03, cut1=0.4, swell=True)),
                                            (0, self._sine(260, 1100, 0.5, 0.12, 1.5))]), 0.5)
        s["splash"] = self._make(self._mix([(0, self._noise(0.6, 0.9, 5.0, 0.6, 0.04)),
                                            (0.02, self._sine(520, 180, 0.16, 0.35, 4.0))]))
        s["hit"] = self._make(self._mix([(0, self._sine(130, 38, 0.6, 1.0, 4.0)),
                                         (0, self._noise(0.45, 0.9, 6.0, 0.5, 0.06, seed=3))]), 0.7)
        s["sunk"] = self._make(self._mix([(0, self._sine(120, 30, 0.9, 1.0, 3.0)),
                                          (0, self._noise(0.7, 0.9, 4.0, 0.5, 0.05, seed=5)),
                                          (0.22, self._sine(95, 28, 0.9, 0.9, 3.0)),
                                          (0.22, self._noise(0.8, 0.8, 4.0, 0.4, 0.04, seed=9)),
                                          (0.5, self._noise(1.0, 0.45, 2.5, 0.12, 0.02, seed=11))]), 0.75)
        win = []
        for i, f in enumerate((523, 659, 784, 1047)):
            win.append((i * 0.14, self._sine(f, f, 0.5, 0.55, 3.2, 0.01)))
        s["win"] = self._make(self._mix(win), 0.5)
        lose = []
        for i, f in enumerate((392, 349, 311, 262)):
            lose.append((i * 0.22, self._sine(f, f * 0.97, 0.6, 0.55, 2.8, 0.01)))
        s["lose"] = self._make(self._mix(lose), 0.5)

    def play(self, name):
        if self.available and self.enabled and name in self.sounds:
            self.sounds[name].play()

    def toggle(self):
        self.enabled = not self.enabled
        return self.enabled
