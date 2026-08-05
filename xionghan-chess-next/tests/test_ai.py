import threading

from xionghan_chess.core.ai import ChessAI, Difficulty
from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Color, GameState, Piece, PieceType


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


def test_hard_ai_prefers_a_clean_material_capture(monkeypatch):
    monkeypatch.setenv("AI_TIME_SCALE", "0.1")
    red_king = Piece.create(PieceType.KING, Color.RED, 11, 6)
    black_king = Piece.create(PieceType.KING, Color.BLACK, 1, 4)
    rook = Piece.create(PieceType.ROOK, Color.RED, 5, 5)
    pawn = Piece.create(PieceType.PAWN, Color.BLACK, 5, 8)
    game = Game.from_state(GameState(
        "desktop_complete", [red_king, black_king, rook, pawn], turn=Color.RED,
    ))

    move = ChessAI(Difficulty.HARD, seed=1).choose_move(game)

    assert move is not None
    assert move.source == rook.position
    assert move.target == pawn.position
