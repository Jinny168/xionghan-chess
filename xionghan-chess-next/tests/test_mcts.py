from threading import Event

from xionghan_chess.core.game import Game
from xionghan_chess.core.mcts import MCTS
from xionghan_chess.core.profiles import get_profile
from xionghan_chess.core.setup import GameSetup


def make_game():
    profile = get_profile("traditional")
    return Game(profile, setup=GameSetup.build(profile, profile.options))


def test_mcts_returns_legal_move_without_dependencies():
    game = make_game()
    move = MCTS(simulations=8, seed=4).choose_move(game)
    assert move is not None
    assert game.rules.is_legal(game.state, move)


def test_mcts_honors_cancel_and_falls_back_to_legal_move():
    game = make_game()
    cancel = Event()
    cancel.set()
    move = MCTS(simulations=20, seed=2).choose_move(game, cancel)
    assert move is not None
    assert game.rules.is_legal(game.state, move)
