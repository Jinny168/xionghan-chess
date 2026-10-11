from __future__ import annotations

import threading

from xionghan_chess.core.ai import ChessAI, Difficulty
from xionghan_chess.core.game import Game
from xionghan_chess.core.mcts import MCTS, _Node


def test_master_difficulty_dispatches_to_mcts(monkeypatch):
    game = Game()
    expected = game.rules.legal_moves(game.state)[0]
    observed: dict[str, object] = {}

    def choose(self, candidate, cancel=None):
        observed["time_limit"] = self.time_limit
        observed["cancel"] = cancel
        return expected

    monkeypatch.setattr(MCTS, "choose_move", choose)
    monkeypatch.setenv("AI_TIME_SCALE", "0.5")
    cancel = threading.Event()

    assert ChessAI(Difficulty.MASTER, seed=7).choose_move(game, cancel) == expected
    assert observed == {"time_limit": 6.0, "cancel": cancel}


def test_seeded_mcts_is_reproducible_and_legal():
    game = Game()
    legal = game.rules.legal_moves(game.state)
    first = MCTS(simulations=12, seed=23).choose_move(game)
    second = MCTS(simulations=12, seed=23).choose_move(game)

    assert first in legal
    assert second == first


def test_ucb_reverses_exploitation_for_opponent_nodes():
    engine = MCTS(simulations=1, exploration=0)
    favorable = _Node(visits=4, value=3)
    unfavorable = _Node(visits=4, value=-2)

    assert engine._ucb(favorable, 8, maximizing=True) > engine._ucb(unfavorable, 8, maximizing=True)
    assert engine._ucb(favorable, 8, maximizing=False) < engine._ucb(unfavorable, 8, maximizing=False)


def test_master_is_exposed_as_fifth_ai_tier():
    assert [item.value for item in Difficulty] == [
        "beginner", "easy", "medium", "hard", "master"
    ]
