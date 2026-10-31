"""三连吃子只结算**移动兵参与的线**（L-05）。

口径（规则作者定稿）：三子紧挨、两我一敌、**任意顺序**、移动兵必须在窗口内、需开关开启。

两类错误各有用例盯着：
1. **收窄过头** → 该吃的线也不吃（正例）；
2. **没收窄** → 走无关的兵却收割远处已成线的敌子（反例）。
"""

from __future__ import annotations

from xionghan_chess.core.game import Game
from xionghan_chess.core.model import (
    Color, GameState, Move, Piece, PieceType, Position,
)

ON = {"pawn_three_line_capture": True}
# 黑王必须在 (0,4)：走到 (0,6) 会与红王 (11,6) 同列照面 → 非法走棋
KINGS = (("king", Color.RED, 11, 6), ("king", Color.BLACK, 0, 4))


def pc(kind: str, color: Color, row: int, col: int) -> Piece:
    return Piece.create(PieceType(kind), color, row, col)


def game(spec: list[tuple[str, Color, int, int]]) -> Game:
    pieces = [pc(*item) for item in list(KINGS) + spec]
    state = GameState("web", pieces, turn=Color.RED,
                      captured={Color.RED: [], Color.BLACK: []})
    return Game.from_state(state, ON, None)


def removals(g: Game, source: tuple[int, int], target: tuple[int, int]) -> set[tuple[int, int]]:
    moves = g.rules.board_removals(g.state, Move(Position(*source), Position(*target)))
    return {(r.position.row, r.position.col) for r in moves}


def test_pawn_landing_on_the_end_of_the_line_captures() -> None:
    """落点在线端：兵 (6,4)→(5,4)，与 (5,5) 兵、(5,6) 黑士紧邻成线 → 吃 (5,6)。"""
    g = game([("pawn", Color.RED, 6, 4), ("pawn", Color.RED, 5, 5),
              ("advisor", Color.BLACK, 5, 6)])
    assert removals(g, (6, 4), (5, 4)) == {(5, 6)}


def test_pawn_landing_in_the_middle_of_the_line_captures() -> None:
    """落点居中：兵 (6,5)→(5,5)，两侧 (5,4) 兵、(5,6) 黑士 → 吃 (5,6)。"""
    g = game([("pawn", Color.RED, 6, 5), ("pawn", Color.RED, 5, 4),
              ("advisor", Color.BLACK, 5, 6)])
    assert removals(g, (6, 5), (5, 5)) == {(5, 6)}


def test_gap_of_one_does_not_capture() -> None:
    """隔一格（不相邻）→ 不吃。"""
    g = game([("pawn", Color.RED, 6, 4), ("pawn", Color.RED, 5, 7),
              ("advisor", Color.BLACK, 5, 8)])
    assert removals(g, (6, 4), (5, 4)) == set()


def test_gap_of_two_does_not_capture() -> None:
    """隔两格 → 不吃。"""
    g = game([("pawn", Color.RED, 6, 4), ("pawn", Color.RED, 5, 8),
              ("advisor", Color.BLACK, 5, 9)])
    assert removals(g, (6, 4), (5, 4)) == set()


def test_unrelated_pawn_move_does_not_harvest_a_far_line() -> None:
    """审计反例：走无关的兵 (8,4)→(7,4)，远处 (2,8)(2,9)(2,10) 已成线 → **不吃**。"""
    g = game([("pawn", Color.RED, 8, 4), ("pawn", Color.RED, 2, 8),
              ("pawn", Color.RED, 2, 9), ("advisor", Color.BLACK, 2, 10)])
    assert removals(g, (8, 4), (7, 4)) == set()


def test_capturable_squares_matches_actual_removals() -> None:
    """不变量：`capturable_squares` 里标为 three_line 的格子 == 真走那步后的实际移除。

    不管内部有几条路径，只要"能吃到"与"实际吃到"分叉，这条就红。
    """
    g = game([("pawn", Color.RED, 6, 4), ("pawn", Color.RED, 5, 5),
              ("advisor", Color.BLACK, 5, 6)])
    specs = g.rules.capturable_squares(g.state, Color.RED)
    reported = {spec.position for spec in specs.values()
                if any("three_line" in str(r.kind) for r in spec.removals)}

    move = Move(Position(6, 4), Position(5, 4))
    before = {(p.type, p.position) for p in g.state.pieces}
    next_state = g.rules.apply_unchecked(g.state, move)
    after = {(p.type, p.position) for p in next_state.pieces}
    # 排除"走子本身离开起点"那一项，只看被移除的子
    actual_positions = {pos for (_t, pos) in before - after if pos != move.source}

    assert reported == actual_positions, f"能吃到 {reported} != 实际吃到 {actual_positions}"
