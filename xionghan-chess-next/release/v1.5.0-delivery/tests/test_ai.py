import threading
import pytest

from xionghan_chess.core.ai import ChessAI, Difficulty
from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Color, GameState, Move, MoveRecord, Piece, PieceType, Position


def test_ai_returns_only_legal_move():
    game = Game("web")
    move = ChessAI(Difficulty.BEGINNER, seed=7).choose_move(game)
    assert move is not None
    assert game.rules.is_legal(game.state, move)


def test_ai_can_be_cancelled_without_hanging():
    game = Game("desktop_complete")
    cancel = threading.Event()
    cancel.set()
    move = ChessAI(Difficulty.HARD).choose_move(game, cancel)
    assert move is not None


@pytest.mark.parametrize("difficulty", list(Difficulty))
def test_every_difficulty_prefers_a_clean_material_capture(monkeypatch, difficulty):
    monkeypatch.setenv("AI_TIME_SCALE", "0.1")
    red_king = Piece.create(PieceType.KING, Color.RED, 11, 6)
    black_king = Piece.create(PieceType.KING, Color.BLACK, 1, 4)
    rook = Piece.create(PieceType.ROOK, Color.RED, 5, 5)
    pawn = Piece.create(PieceType.PAWN, Color.BLACK, 5, 8)
    game = Game.from_state(GameState(
        "desktop_complete", [red_king, black_king, rook, pawn], turn=Color.RED,
    ))

    move = ChessAI(difficulty, seed=1).choose_move(game)

    assert move is not None
    assert move.source == rook.position
    assert move.target == pawn.position


def test_hard_ai_prefers_the_more_valuable_capture(monkeypatch):
    monkeypatch.setenv("AI_TIME_SCALE", "0.1")
    red_king = Piece.create(PieceType.KING, Color.RED, 11, 6)
    black_king = Piece.create(PieceType.KING, Color.BLACK, 1, 4)
    rook = Piece.create(PieceType.ROOK, Color.RED, 5, 5)
    black_pawn = Piece.create(PieceType.PAWN, Color.BLACK, 5, 8)
    black_rook = Piece.create(PieceType.ROOK, Color.BLACK, 8, 5)
    game = Game.from_state(GameState(
        "desktop_complete", [red_king, black_king, rook, black_pawn, black_rook],
        turn=Color.RED,
    ))

    move = ChessAI(Difficulty.HARD, seed=2).choose_move(game)

    assert move is not None
    assert move.source == rook.position
    assert move.target == black_rook.position


def test_ai_avoids_an_immediate_reverse_when_useful_moves_exist(monkeypatch):
    monkeypatch.setenv("AI_TIME_SCALE", "0.1")
    red_king = Piece.create(PieceType.KING, Color.RED, 11, 6)
    black_king = Piece.create(PieceType.KING, Color.BLACK, 1, 6)
    blocker = Piece.create(PieceType.ADVISOR, Color.BLACK, 2, 6)
    rook = Piece.create(PieceType.ROOK, Color.BLACK, 2, 2)
    red_pawn = Piece.create(PieceType.PAWN, Color.RED, 8, 2)
    state = GameState(
        "desktop_complete", [red_king, black_king, blocker, rook, red_pawn],
        turn=Color.BLACK,
    )
    previous = Move(Position(1, 2), Position(2, 2))
    state.history.append(MoveRecord(previous, Color.BLACK, PieceType.ROOK, (), "俥 2,3 至 3,3"))
    game = Game.from_state(state)

    move = ChessAI(Difficulty.HARD, seed=3).choose_move(game)

    assert move is not None
    assert move != Move(Position(2, 2), Position(1, 2))
