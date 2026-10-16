from __future__ import annotations

import random
from typing import Optional

from .board import FLEET, Board, Cell, ShotResult
from .knowledge import UNKNOWN, Knowledge
from .levels import make_ai
from .placement import smart_placement

PLACEMENT, PLAYER, AI, OVER = "placement", "player", "ai", "over"


class Game:
    def __init__(self, level: str = "hard", rng: Optional[random.Random] = None,
                 hit_again: bool = True):
        self.rng = rng or random.Random()
        self.hit_again = hit_again
        self.level = level
        self.ai = make_ai(level, self.rng)

        self.player_board = Board()
        self.enemy_board = Board()
        smart_placement(self.enemy_board, FLEET, self.rng)

        self.player_view = Knowledge()
        self.ai_view = Knowledge()

        self.phase = PLACEMENT
        self.winner: Optional[str] = None
        self.player_shots = 0
        self.ai_shots = 0

    def set_level(self, level: str) -> None:
        self.level = level
        self.ai = make_ai(level, self.rng)

    @property
    def placement_done(self) -> bool:
        return len(self.player_board.ships) == len(FLEET)

    def next_ship_length(self) -> Optional[int]:
        i = len(self.player_board.ships)
        return FLEET[i] if i < len(FLEET) else None

    def randomize_player(self) -> None:
        self.player_board.place_randomly(FLEET, self.rng)

    def recommend_player(self) -> None:
        smart_placement(self.player_board, FLEET, self.rng)

    def start(self) -> bool:
        if self.phase != PLACEMENT or not self.placement_done:
            return False
        self.phase = PLAYER
        return True

    def player_shoot(self, cell: Cell) -> Optional[ShotResult]:
        if self.phase != PLAYER or self.player_view.state(cell) != UNKNOWN:
            return None
        result = self.enemy_board.receive_shot(cell)
        self.player_view.update(result)
        self.player_shots += 1
        if self.enemy_board.all_sunk:
            self.phase, self.winner = OVER, "player"
        elif not (result.hit and self.hit_again):
            self.phase = AI
        return result

    def ai_shoot(self) -> Optional[ShotResult]:
        if self.phase != AI:
            return None
        cell = self.ai.choose(self.ai_view)
        result = self.player_board.receive_shot(cell)
        self.ai_view.update(result)
        self.ai_shots += 1
        if self.player_board.all_sunk:
            self.phase, self.winner = OVER, "ai"
        elif not (result.hit and self.hit_again):
            self.phase = PLAYER
        return result
