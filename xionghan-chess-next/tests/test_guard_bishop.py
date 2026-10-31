"""尉（GUARD）＝ 标准主教：斜向任意距离，路径必须无子，落点有敌子即吃。

## 为什么整份重写

尉原来是「四正/斜向隔一子跳 + 照面钉住」；`1571ca8` 把它改成标准主教并**删除照面钉住**。
旧用例（`test_guard_pin.py`）测的全是已不存在的机制，留着会误导后来人以为还能回滚，
所以整份换掉，只留**现口径**的行为断言。照面钉住不保留任何 skip/xfail —— 机制真的没了。
"""

from __future__ import annotations

import pytest

from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Color, GameState, Move, Piece, PieceType, Position

PROFILE = "desktop_complete"


def piece(kind: PieceType, color: Color, row: int, col: int) -> Piece:
    return Piece.create(kind, color, row, col)


def kings() -> list[Piece]:
    return [piece(PieceType.KING, Color.RED, 12, 12), piece(PieceType.KING, Color.BLACK, 0, 10)]


def board(*extra: Piece, turn: Color = Color.RED) -> GameState:
    return GameState(PROFILE, [*kings(), *extra], turn=turn)


@pytest.fixture(scope="module")
def rules():
    return Game(PROFILE).rules


def test_guard_moves_one_diagonal_step(rules) -> None:
    guard = piece(PieceType.GUARD, Color.RED, 6, 6)
    state = board(guard)
    assert rules.is_legal(state, Move(guard.position, Position(7, 7)))
    assert rules.is_legal(state, Move(guard.position, Position(5, 5)))


def test_guard_slides_any_distance_on_a_clear_diagonal(rules) -> None:
    guard = piece(PieceType.GUARD, Color.RED, 6, 6)
    state = board(guard)
    for target in ((3, 3), (0, 0), (9, 9), (2, 2)):
        assert rules.is_legal(state, Move(guard.position, Position(*target))), target


def test_guard_never_moves_orthogonally(rules) -> None:
    guard = piece(PieceType.GUARD, Color.RED, 6, 6)
    state = board(guard)
    for target in ((6, 7), (6, 4), (5, 6), (8, 6)):
        assert not rules.is_legal(state, Move(guard.position, Position(*target))), target


def test_guard_stops_at_the_first_piece_on_the_diagonal(rules) -> None:
    """斜线上有子即停：既不能穿过，也吃不到更远的敌子。"""
    guard = piece(PieceType.GUARD, Color.RED, 6, 6)
    blocker = piece(PieceType.PAWN, Color.RED, 7, 7)
    far = piece(PieceType.HORSE, Color.BLACK, 9, 9)
    state = board(guard, blocker, far)
    assert not rules.is_legal(state, Move(guard.position, Position(8, 8)))
    assert not rules.is_legal(state, Move(guard.position, Position(9, 9)))


def test_guard_captures_the_first_enemy_on_the_diagonal(rules) -> None:
    guard = piece(PieceType.GUARD, Color.RED, 6, 6)
    victim = piece(PieceType.HORSE, Color.BLACK, 9, 9)
    state = board(guard, victim)
    move = Move(guard.position, victim.position)
    assert rules.is_legal(state, move)
    after = rules.apply_unchecked(state, move)
    assert after.piece_at(Position(9, 9)).type is PieceType.GUARD


def test_guards_no_longer_pin_anything(rules) -> None:
    """照面钉住已删除：原来被"照面"的敌子现在可以正常走。"""
    red_guard = piece(PieceType.GUARD, Color.RED, 6, 0)
    enemy_rook = piece(PieceType.ROOK, Color.BLACK, 6, 4)
    state = board(red_guard, enemy_rook, turn=Color.BLACK)
    moves = [m for m in rules.legal_moves(state, Color.BLACK) if m.source == enemy_rook.position]
    assert moves, "照面机制已删，被'照面'的敌子必须能走"
