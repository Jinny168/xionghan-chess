from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from .ai import ChessAI, Difficulty
from .game import Game
from .model import GameState, Move


@dataclass(frozen=True, slots=True)
class MoveAnalysis:
    ply: int
    notation: str
    quality: str
    score_loss: int
    score: int
    win_rate: float
    best_move: Move | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ply": self.ply,
            "notation": self.notation,
            "quality": self.quality,
            "scoreLoss": self.score_loss,
            "score": self.score,
            "winRate": self.win_rate,
            "bestMove": move_dict(self.best_move),
        }


def move_dict(move: Move | None) -> dict[str, Any] | None:
    if move is None:
        return None
    return {
        "from": {"row": move.source.row, "col": move.source.col},
        "to": {"row": move.target.row, "col": move.target.col},
        "promotion": move.promotion.value if move.promotion else None,
    }


def analyze_game(game: Game, difficulty: Difficulty | str = Difficulty.BEGINNER,
                 max_plies: int = 200) -> dict[str, Any]:
    analyses: list[MoveAnalysis] = []
    snapshots = list(game._snapshots)
    for index, record in enumerate(game.state.history[:max_plies]):
        if index >= len(snapshots):
            break
        state = GameState.from_dict(snapshots[index])
        position = Game.from_state(state, game.options, game.setup)
        engine = ChessAI(difficulty, seed=0)
        best = engine.choose_move(position)
        scores = {move.key(): int(round(score)) for score, move in engine.root_scores}
        best_score = max(scores.values(), default=0)
        actual_score = scores.get(record.move.key(), best_score if best == record.move else best_score - 400)
        loss = max(0, best_score - actual_score)
        quality = quality_for_loss(loss, best == record.move)
        perspective_score = actual_score if record.color.value == "red" else -actual_score
        analyses.append(MoveAnalysis(
            index + 1, record.notation, quality, loss, perspective_score,
            round(100 / (1 + math.exp(-perspective_score / 500)), 1), best,
        ))
    return {
        "engine": "xionghan-builtin",
        "difficulty": Difficulty(difficulty).value,
        "analyzedPlies": len(analyses),
        "moves": [item.to_dict() for item in analyses],
        "winRateCurve": [item.win_rate for item in analyses],
        "summary": {
            key: sum(item.quality == key for item in analyses)
            for key in ("best", "good", "inaccuracy", "mistake", "blunder")
        },
    }


def quality_for_loss(loss: int, is_best: bool = False) -> str:
    if is_best or loss <= 20:
        return "best"
    if loss <= 90:
        return "good"
    if loss <= 220:
        return "inaccuracy"
    if loss <= 450:
        return "mistake"
    return "blunder"
