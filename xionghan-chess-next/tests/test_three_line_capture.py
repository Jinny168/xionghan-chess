"""三连吃子只结算**移动兵参与的线**（L-05）。

口径（规则作者定稿）：三子紧挨、两我一敌、**任意顺序**、移动兵必须在窗口内、需开关开启。

这里先钉住风险最大的那条：**全盘扫描会把"移动前就存在的线"一并收割** ——
走一步无关的兵，远处已成线的敌子也会被吃。
"""

from __future__ import annotations

from xionghan_chess.core.game import Game
from xionghan_chess.core.model import (
    Color, GameState, Move, Piece, PieceType, Position,
)

ON = {"pawn_three_line_capture": True}


def pc(kind: PieceType, color: Color, row: int, col: int) -> Piece:
    return Piece.create(kind, color, row, col)


def game(*pieces: Piece) -> Game:
    state = GameState("web", list(pieces), turn=Color.RED,
                      captured={Color.RED: [], Color.BLACK: []})
    return Game.from_state(state, ON, None)


KINGS = (pc(PieceType.KING, Color.RED, 12, 12), pc(PieceType.KING, Color.BLACK, 0, 10))


def removals(g: Game, source: tuple[int, int], target: tuple[int, int]) -> set[tuple[int, int]]:
    return {(r.target.row, r.target.col)
            for r in g.rules.board_removals(g.state, Move(Position(*source), Position(*target)))}


def test_unrelated_pawn_move_does_not_harvest_a_far_line() -> None:
    """审计反例：走无关的兵 (8,4)→(7,4)，远处 (2,8)(2,9)(2,10) 已成线 → **不吃**。"""
    g = game(*KINGS,
             pc(PieceType.PAWN, Color.RED, 8, 4),
             pc(PieceType.ADVISOR, Color.BLACK, 2, 10),
             pc(PieceType.PAWN, Color.RED, 2, 8),
             pc(PieceType.PAWN, Color.RED, 2, 9))
    assert removals(g, (8, 4), (7, 4)) == set()
