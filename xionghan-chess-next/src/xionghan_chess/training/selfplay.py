from __future__ import annotations

import json
from pathlib import Path
import random

from ..core.game import Game
from ..core.mcts import MCTS
from ..core.model import Color
from .encoding import action_index


def collect_game(profile: str = "traditional", simulations: int = 32,
                 max_plies: int = 240, seed: int = 0) -> list[dict]:
    """Run one local self-play episode using only the authoritative core."""
    game = Game(profile)
    randomizer = random.Random(seed)
    pending: list[tuple[dict, int, Color]] = []
    for _ in range(max_plies):
        if game.state.finished:
            break
        engine = MCTS(simulations=simulations, seed=randomizer.randrange(2**32))
        move = engine.choose_move(game)
        if move is None:
            break
        pending.append((game.state.to_dict(), action_index(move), game.state.turn))
        game.move(move)
    samples = []
    for state, action, player in pending:
        value = 0.0
        if game.state.winner is not None:
            value = 1.0 if game.state.winner is player else -1.0
        samples.append({"schema": 1, "state": state, "action": action,
                        "player": player.value, "value": value})
    return samples


def append_jsonl(path: str | Path, samples: list[dict]) -> int:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8", newline="\n") as stream:
        for sample in samples:
            stream.write(json.dumps(sample, ensure_ascii=False, separators=(",", ":")) + "\n")
    return len(samples)
