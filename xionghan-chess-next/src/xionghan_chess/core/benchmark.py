from __future__ import annotations

from dataclasses import asdict, dataclass
import os
import statistics
import time

from .ai import ChessAI, Difficulty
from .game import Game
from .mcts import MCTS
from .model import Color


@dataclass(slots=True)
class MatchResult:
    game: int
    master_color: str
    winner: str | None
    adjudicated: bool
    plies: int
    master_seconds: float
    hard_seconds: float


def benchmark_master_vs_hard(games: int = 50, profile: str = "traditional",
                             max_plies: int = 240, seed: int = 0,
                             hard_time_scale: float = 1.0,
                             master_simulations: int | None = None) -> dict:
    """Run a color-balanced match and return machine-readable acceptance data."""
    results: list[MatchResult] = []
    master_move_times: list[float] = []
    hard_move_times: list[float] = []
    previous_scale = os.environ.get("AI_TIME_SCALE")
    os.environ["AI_TIME_SCALE"] = str(hard_time_scale)
    try:
        for game_index in range(games):
            game = Game(profile)
            master_color = Color.RED if game_index % 2 == 0 else Color.BLACK
            totals = {"master": 0.0, "hard": 0.0}
            for ply in range(max_plies):
                if game.state.finished:
                    break
                is_master = game.state.turn is master_color
                started = time.perf_counter()
                if is_master and master_simulations is not None:
                    scorer = ChessAI(Difficulty.HARD)._see_score
                    move = MCTS(simulations=master_simulations, seed=seed + game_index * max_plies + ply,
                                root_score=scorer).choose_move(game)
                else:
                    level = Difficulty.MASTER if is_master else Difficulty.HARD
                    move = ChessAI(level, seed=seed + game_index * max_plies + ply).choose_move(game)
                elapsed = time.perf_counter() - started
                bucket = master_move_times if is_master else hard_move_times
                bucket.append(elapsed)
                totals["master" if is_master else "hard"] += elapsed
                if move is None:
                    break
                game.move(move)
            adjudicated = not game.state.finished
            winner = game.state.winner
            if adjudicated:
                score = ChessAI(Difficulty.HARD)._evaluate(game, Color.RED)
                winner = Color.RED if score > 100 else Color.BLACK if score < -100 else None
            results.append(MatchResult(
                game_index + 1, master_color.value, winner.value if winner else None,
                adjudicated, len(game.state.history), totals["master"], totals["hard"],
            ))
    finally:
        if previous_scale is None:
            os.environ.pop("AI_TIME_SCALE", None)
        else:
            os.environ["AI_TIME_SCALE"] = previous_scale
    wins = sum(item.winner == item.master_color for item in results)
    losses = sum(item.winner is not None and item.winner != item.master_color for item in results)
    draws = len(results) - wins - losses
    decisive = wins + losses
    completed_games = sum(not item.adjudicated for item in results)
    return {
        "games": games, "masterWins": wins, "hardWins": losses, "draws": draws,
        "masterWinRate": wins / games if games else 0.0,
        "masterDecisiveWinRate": wins / decisive if decisive else 0.0,
        "masterMoveMeanSeconds": statistics.fmean(master_move_times) if master_move_times else 0.0,
        "masterMoveMaxSeconds": max(master_move_times, default=0.0),
        "hardMoveMeanSeconds": statistics.fmean(hard_move_times) if hard_move_times else 0.0,
        "hardMoveMaxSeconds": max(hard_move_times, default=0.0),
        "completedGames": completed_games,
        "adjudicatedGames": sum(item.adjudicated for item in results),
        "acceptance": {
            "enoughGames": games >= 50,
            "enoughCompletedGames": completed_games >= 50,
            "winRateAtLeast55Percent": completed_games >= 50 and wins / games >= 0.55,
            "masterMoveAtMost12Seconds": max(master_move_times, default=0.0) <= 12.0,
        },
        "results": [asdict(item) for item in results],
    }
