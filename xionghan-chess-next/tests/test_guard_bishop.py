"""尉（GUARD）的「照面钉住」：与敌方尉同一横/竖线、中间无子 → 该子任何着法都不合法。

## 为什么单独一层测试

钉住不是"某一步不能走"，而是"这枚子整轮不能动"——它会被 `legal_moves` 直接过滤掉。
这类规则最容易写成"只挡了吃子/只挡了前进"，或者在两尉互相照面时漏掉一边；
下面的用例逐条钉住：单向钉、互相钉、被己方子挡住则不钉、只影响被照面的那一枚。
"""

from __future__ import annotations

from xionghan_chess.core.model import Color, GameState, Piece, PieceType, Position
from xionghan_chess.core.profiles import get_profile
from xionghan_chess.core.rules import RulesEngine

PROFILE = "desktop_complete"


def piece(kind: PieceType, color: Color, row: int, col: int) -> Piece:
    return Piece.create(kind, color, row, col)


def kings() -> list[Piece]:
    return [piece(PieceType.KING, Color.RED, 11, 6), piece(PieceType.KING, Color.BLACK, 1, 5)]


def rules() -> RulesEngine:
    return RulesEngine(get_profile(PROFILE))


def moves_from(state: GameState, source: Position, color: Color):
    return [move for move in rules().legal_moves(state, color) if move.source == source]


def test_guard_pins_the_enemy_piece_it_faces() -> None:
    guard = piece(PieceType.GUARD, Color.RED, 6, 0)
    pinned = piece(PieceType.ROOK, Color.BLACK, 6, 4)
    movable = piece(PieceType.ROOK, Color.BLACK, 9, 9)
    state = GameState(PROFILE, kings() + [guard, pinned, movable], turn=Color.BLACK)

    assert moves_from(state, pinned.position, Color.BLACK) == [], "被照面的子不能动"
    assert moves_from(state, movable.position, Color.BLACK), "没被照面的子必须正常"


def test_both_guards_are_pinned_when_they_face_each_other() -> None:
    red_guard = piece(PieceType.GUARD, Color.RED, 6, 3)
    black_guard = piece(PieceType.GUARD, Color.BLACK, 6, 7)
    state = GameState(PROFILE, kings() + [red_guard, black_guard], turn=Color.RED)

    assert moves_from(state, red_guard.position, Color.RED) == [], "互相照面时红尉也被钉"
    state.turn = Color.BLACK
    assert moves_from(state, black_guard.position, Color.BLACK) == [], "黑尉同样被钉"


def test_guard_does_not_pin_through_a_friendly_piece() -> None:
    guard = piece(PieceType.GUARD, Color.RED, 6, 0)
    blocker = piece(PieceType.PAWN, Color.RED, 6, 2)      # 己方子挡在中间
    behind = piece(PieceType.ROOK, Color.BLACK, 6, 4)
    state = GameState(PROFILE, kings() + [guard, blocker, behind], turn=Color.BLACK)

    assert moves_from(state, behind.position, Color.BLACK), "照面不跨越任何棋子，隔了子就不钉"


def test_guard_pinning_is_orthogonal_only() -> None:
    """对角线不算照面。"""
    guard = piece(PieceType.GUARD, Color.RED, 6, 0)
    diagonal = piece(PieceType.ROOK, Color.BLACK, 8, 2)
    state = GameState(PROFILE, kings() + [guard, diagonal], turn=Color.BLACK)

    assert moves_from(state, diagonal.position, Color.BLACK), "斜向相邻/同斜线不构成照面"
