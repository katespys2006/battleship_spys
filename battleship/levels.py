from __future__ import annotations

import random
from typing import Optional

from .ai import BaseAI, EasyAI, MediumAI
from .ai_probability import ProbabilityAI

LEVELS = {
    "easy": EasyAI,
    "medium": MediumAI,
    "hard": ProbabilityAI,
}


def make_ai(level: str, rng: Optional[random.Random] = None) -> BaseAI:
    return LEVELS[level](rng)
