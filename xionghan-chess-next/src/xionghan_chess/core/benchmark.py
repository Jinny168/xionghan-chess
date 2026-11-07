from __future__ import annotations

from dataclasses import asdict, dataclass
import os
import statistics
import time
from typing import Callable, Optional

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
    master_max_move_seconds: float = 0.0


def benchmark_master_vs_hard(games: int = 50, profile: str = "traditional",
                             max_plies: int = 240, seed: int = 0,
                             hard_time_scale: float = 1.0,
                             master_simulations: int | None = None,
                             on_game: Optional[Callable[[MatchResult], None]] = None,
                             start_game: int = 0) -> dict:
    """Run a color-balanced match and return machine-readable acceptance data.

    ``on_game`` is called once per finished game, in order. It lets long matches
    survive a crash: the caller can append each :class:`MatchResult` to disk
    instead of waiting for the whole run to finish.

    ``start_game`` skips the first N games of the sequence. Because colour,
    tie-break seeds and game numbering all derive from the absolute index, a
    match split into chunks with ``start_game=0,5,10,...`` is bit-identical to
    the same match run in one go.
    """
    results: list[MatchResult] = []
    master_move_times: list[float] = []
    hard_move_times: list[float] = []
    previous_scale = os.environ.get("AI_TIME_SCALE")
    os.environ["AI_TIME_SCALE"] = str(hard_time_scale)
    try:
        for game_index in range(start_game, start_game + games):
            game = Game(profile)
            master_color = Color.RED if game_index % 2 == 0 else Color.BLACK
            totals = {"master": 0.0, "hard": 0.0}
            master_moves_before = len(master_move_times)
            for ply in range(max_plies):
                if game.state.finished:
                    break
                is_master = game.state.turn is master_color
                started = time.perf_counter()
                if is_master and master_simulations is not None:
                    # Use the *production* master configuration (model-loaded scorers) so that
                    # bounded-simulation runs still exercise the shipped master path, not a
                    # heuristic SEE scorer that diverges from what users actually play.
                    master_ai = ChessAI(Difficulty.MASTER)
                    master_model = master_ai._load_master_model()
                    move = MCTS(simulations=master_simulations, seed=seed + game_index * max_plies + ply,
                                root_score=lambda g, m: master_ai._master_move_score(g, m, master_model),
                                leaf_score=master_ai._master_leaf_score).choose_move(game)
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
            result = MatchResult(
                game_index + 1, master_color.value, winner.value if winner else None,
                adjudicated, len(game.state.history), totals["master"], totals["hard"],
                round(max(master_move_times[master_moves_before:], default=0.0), 3),
            )
            results.append(result)
            if on_game is not None:
                on_game(result)
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
