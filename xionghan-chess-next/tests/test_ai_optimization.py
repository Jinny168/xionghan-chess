import math
import time

import pytest

from xionghan_chess.core.ai import ChessAI, Difficulty
from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Color, GameState, Move, Piece, PieceType, Position


def piece(kind, color, row, col):
    return Piece.create(kind, color, row, col)


def kings():
    return (piece(PieceType.KING, Color.RED, 11, 6),
            piece(PieceType.KING, Color.BLACK, 1, 5))


def cannon_sacrifice_position():
    red_king, black_king = kings()
    cannon = piece(PieceType.CANNON, Color.BLACK, 3, 4)
    screen = piece(PieceType.PAWN, Color.BLACK, 5, 4)
    pawn = piece(PieceType.PAWN, Color.RED, 8, 4)
    horse = piece(PieceType.HORSE, Color.RED, 9, 2)
    game = Game.from_state(GameState(
        "desktop_complete", [red_king, black_king, cannon, screen, pawn, horse],
        turn=Color.BLACK,
    ))
    return game, Move(cannon.position, pawn.position)


def test_see_detects_cannon_sacrifice_from_recorded_game():
    game, move = cannon_sacrifice_position()
    assert game.rules.is_legal(game.state, move)
    assert ChessAI()._see_score(game, move) == -380


def test_see_detects_rook_capture_lost_to_elephant():
    red_king, black_king = kings()
    rook = piece(PieceType.ROOK, Color.BLACK, 9, 1)
    cannon = piece(PieceType.CANNON, Color.RED, 9, 6)
    elephant = piece(PieceType.ELEPHANT, Color.RED, 11, 8)
    game = Game.from_state(GameState(
        "desktop_complete", [red_king, black_king, rook, cannon, elephant],
        turn=Color.BLACK,
    ))
    move = Move(rook.position, cannon.position)
    assert game.rules.is_legal(game.state, move)
    assert ChessAI()._see_score(game, move) == -400


def test_see_detects_quiet_move_that_hangs_rook():
    red_king, black_king = kings()
    black_rook = piece(PieceType.ROOK, Color.BLACK, 1, 10)
    red_rook = piece(PieceType.ROOK, Color.RED, 7, 9)
    game = Game.from_state(GameState(
        "desktop_complete", [red_king, black_king, black_rook, red_rook],
        turn=Color.BLACK,
    ))
    move = Move(black_rook.position, Position(1, 9))
    assert game.rules.is_legal(game.state, move)
    assert ChessAI()._see_score(game, move) == -900


@pytest.mark.parametrize("difficulty", list(Difficulty))
def test_ai_avoids_immediate_cannon_sacrifice(monkeypatch, difficulty):
    monkeypatch.setenv("AI_TIME_SCALE", "0.1")
    game, sacrifice = cannon_sacrifice_position()
    assert ChessAI(difficulty, seed=0).choose_move(game) != sacrifice


def test_evaluation_is_symmetric_when_colors_and_rows_are_mirrored():
    pieces = [
        piece(PieceType.KING, Color.RED, 11, 6),
        piece(PieceType.KING, Color.BLACK, 1, 5),
        piece(PieceType.ROOK, Color.RED, 8, 2),
        piece(PieceType.HORSE, Color.BLACK, 3, 9),
        piece(PieceType.PAWN, Color.RED, 6, 4),
        piece(PieceType.CANNON, Color.BLACK, 4, 7),
    ]
    game = Game.from_state(GameState("desktop_complete", pieces, turn=Color.RED))
    mirrored = [Piece.create(item.type, item.color.opponent,
                             12 - item.position.row, item.position.col)
                for item in pieces]
    mirror_game = Game.from_state(GameState(
        "desktop_complete", mirrored, turn=Color.BLACK,
    ))
    assert ChessAI()._evaluate(game, Color.RED) == pytest.approx(
        ChessAI()._evaluate(mirror_game, Color.BLACK)
    )


def test_null_move_is_disabled_for_resurrection_and_sparse_endgames():
    engine = ChessAI(Difficulty.HARD)
    assert engine._can_null_move(Game("desktop_complete")) is False
    assert engine._can_null_move(Game("traditional")) is True
    red_king, black_king = kings()
    sparse = Game.from_state(GameState(
        "traditional", [red_king, black_king,
                        piece(PieceType.ROOK, Color.RED, 8, 2)],
        turn=Color.RED,
    ))
    assert engine._can_null_move(sparse) is False


def test_null_move_pruning_executes_in_supported_midgame_profile():
    engine = ChessAI(Difficulty.HARD)
    game = Game("traditional")
    deadline = time.monotonic() + 2
    engine._active_deadline = deadline
    score = engine._search(game, 4, -math.inf, -10_000, deadline, None, 0)
    assert score == -10_000
    assert engine.null_prunes == 1
