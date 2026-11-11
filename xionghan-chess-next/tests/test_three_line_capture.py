"""三连吃子只结算**移动兵参与的线**（L-05）。

口径（规则作者定稿）：三子紧挨、**恰好三子**、两我一敌、**任意顺序**、移动兵必须在窗口内、
需开关开启、且**这一着位移不超过一格**。

四类错误各有用例盯着：
1. **收窄过头** → 该吃的线也不吃（正例）；
2. **没收窄** → 走无关的兵却收割远处已成线的敌子（反例）；
3. **多格行军旁吃** → 一着位移 2..7 格（快速行军 / 敌阵冲锋）顺便吃子（R1，回归）；
4. **超长线** → 线上连成 4 子 / 5 子，仍按 3 格窗口各算一次（R2，回归）。
"""

from __future__ import annotations

import pytest

from xionghan_chess.core.game import Game
from xionghan_chess.core.model import (
    Color,
    GameState,
    Move,
    Piece,
    PieceType,
    Position,
)

ON = {"pawn_three_line_capture": True}
# 黑王必须在 (0,4)：走到 (0,6) 会与红王 (11,6) 同列照面 → 非法走棋
KINGS = (("king", Color.RED, 11, 6), ("king", Color.BLACK, 0, 4))


def pc(kind: str, color: Color, row: int, col: int) -> Piece:
    return Piece.create(PieceType(kind), color, row, col)


def game(spec: list[tuple[str, Color, int, int]], extra_options: dict | None = None) -> Game:
    pieces = [pc(*item) for item in list(KINGS) + spec]
    state = GameState("web", pieces, turn=Color.RED, captured={Color.RED: [], Color.BLACK: []})
    return Game.from_state(state, {**ON, **(extra_options or {})}, None)


def removals(g: Game, source: tuple[int, int], target: tuple[int, int]) -> set[tuple[int, int]]:
    moves = g.rules.board_removals(g.state, Move(Position(*source), Position(*target)))
    return {(r.position.row, r.position.col) for r in moves}


def test_pawn_landing_on_the_end_of_the_line_captures() -> None:
    """落点在线端：兵 (6,4)→(5,4)，与 (5,5) 兵、(5,6) 黑士紧邻成线 → 吃 (5,6)。"""
    g = game([("pawn", Color.RED, 6, 4), ("pawn", Color.RED, 5, 5), ("advisor", Color.BLACK, 5, 6)])
    assert removals(g, (6, 4), (5, 4)) == {(5, 6)}


def test_pawn_landing_in_the_middle_of_the_line_captures() -> None:
    """落点居中：兵 (6,5)→(5,5)，两侧 (5,4) 兵、(5,6) 黑士 → 吃 (5,6)。"""
    g = game([("pawn", Color.RED, 6, 5), ("pawn", Color.RED, 5, 4), ("advisor", Color.BLACK, 5, 6)])
    assert removals(g, (6, 5), (5, 5)) == {(5, 6)}


def test_gap_of_one_does_not_capture() -> None:
    """隔一格（不相邻）→ 不吃。"""
    g = game([("pawn", Color.RED, 6, 4), ("pawn", Color.RED, 5, 7), ("advisor", Color.BLACK, 5, 8)])
    assert removals(g, (6, 4), (5, 4)) == set()


def test_gap_of_two_does_not_capture() -> None:
    """隔两格 → 不吃。"""
    g = game([("pawn", Color.RED, 6, 4), ("pawn", Color.RED, 5, 8), ("advisor", Color.BLACK, 5, 9)])
    assert removals(g, (6, 4), (5, 4)) == set()


def test_unrelated_pawn_move_does_not_harvest_a_far_line() -> None:
    """审计反例：走无关的兵 (8,4)→(7,4)，远处 (2,8)(2,9)(2,10) 已成线 → **不吃**。"""
    g = game(
        [
            ("pawn", Color.RED, 8, 4),
            ("pawn", Color.RED, 2, 8),
            ("pawn", Color.RED, 2, 9),
            ("advisor", Color.BLACK, 2, 10),
        ]
    )
    assert removals(g, (8, 4), (7, 4)) == set()


def test_capturable_squares_matches_actual_removals() -> None:
    """不变量：`capturable_squares` 里标为 three_line 的格子 == 真走那步后的实际移除。

    不管内部有几条路径，只要"能吃到"与"实际吃到"分叉，这条就红。
    """
    g = game([("pawn", Color.RED, 6, 4), ("pawn", Color.RED, 5, 5), ("advisor", Color.BLACK, 5, 6)])
    specs = g.rules.capturable_squares(g.state, Color.RED)
    reported = {spec.position for spec in specs.values() if any("three_line" in str(r.kind) for r in spec.removals)}

    move = Move(Position(6, 4), Position(5, 4))
    before = {(p.type, p.position) for p in g.state.pieces}
    next_state = g.rules.apply_unchecked(g.state, move)
    after = {(p.type, p.position) for p in next_state.pieces}
    # 排除"走子本身离开起点"那一项，只看被移除的子
    actual_positions = {pos for (_t, pos) in before - after if pos != move.source}

    assert reported == actual_positions, f"能吃到 {reported} != 实际吃到 {actual_positions}"

# ---------------------------------------------------------------------------
# R1：位移 > 1 格不结算三连
# ---------------------------------------------------------------------------
# 几何：红兵沿 3 列从 (5+steps, 3) 快速行军到 (5,3)。
# `distance_to_enemy_territory = row - rows//2 + 1 = steps`，所以落点 (5,3)
# 恰好是快速行军的**最远**合法落点 —— 这一步是真能走的，不是纸上谈兵。
# 落点处的三连线：(5,3) 落点兵 + (5,4) 我兵 + (5,5) 敌士（外侧 (5,2)(5,6) 均空，恰好三子）。
def _march_line(steps: int) -> Game:
    return game(
        [
            ("pawn", Color.RED, 5 + steps, 3),
            ("pawn", Color.RED, 5, 4),
            ("advisor", Color.BLACK, 5, 5),
        ]
    )


@pytest.mark.parametrize("steps", [2, 3, 4, 5, 6, 7])
def test_fast_march_longer_than_one_square_does_not_settle_three_line(steps: int) -> None:
    """一着位移 2..7 格 → 落点照样成三连，但**不结算**（R1）。"""
    g = _march_line(steps)
    source = (5 + steps, 3)
    move = Move(Position(*source), Position(5, 3))
    assert g.rules.pseudo_legal(g.state, move), f"{steps} 格快速行军应当合法"
    assert removals(g, source, (5, 3)) == set(), f"位移 {steps} 格不该触发三连吃子"


def test_single_step_into_the_same_line_still_captures() -> None:
    """R1 的对照：同样一条线，兵只走一格 → **照吃**（防收窄过头）。"""
    g = _march_line(1)  # 兵在 (6,3)，前进一格落到 (5,3)
    assert g.rules.pseudo_legal(g.state, Move(Position(6, 3), Position(5, 3)))
    assert removals(g, (6, 3), (5, 3)) == {(5, 5)}


def test_pawn_charge_long_move_does_not_settle_three_line() -> None:
    """敌阵冲锋 3 格（过阴山后的另一条多格分支）同样不结算（R1 覆盖 `pawn_charge`）。"""
    # 兵 (5,3) 已过阴山（row 5 < 6），冲锋到 (2,3)，路径 (4,3)(3,3) 全空；
    # 落点处：(2,3) 我兵 + (2,4) 我兵 + (2,5) 敌士，外侧 (2,2)(2,6) 均空。
    g = game(
        [
            ("pawn", Color.RED, 5, 3),
            ("pawn", Color.RED, 2, 4),
            ("advisor", Color.BLACK, 2, 5),
        ]
    )
    assert g.rules.options.pawn_charge, "本用例依赖 web 档案的敌阵冲锋开关"
    move = Move(Position(5, 3), Position(2, 3))
    assert g.rules.pseudo_legal(g.state, move), "冲锋 3 格应当合法"
    assert removals(g, (5, 3), (2, 3)) == set()


# ---------------------------------------------------------------------------
# R2：线上必须恰好三子
# ---------------------------------------------------------------------------
# 几何统一：红兵 (7,3) 前进一格落到 (6,3)，三连窗口 = (6,3)(6,4)(6,5)。
_EXTRA = [("pawn", Color.RED, 6, 4), ("advisor", Color.BLACK, 6, 5)]


@pytest.mark.parametrize(
    ("label", "extra", "expected"),
    [
        ("恰好三子", [], {(6, 5)}),
        ("四子（远端多一子）", [("pawn", Color.RED, 6, 6)], set()),
        ("四子（近端多一子）", [("pawn", Color.RED, 6, 2)], set()),
        ("五子", [("pawn", Color.RED, 6, 6), ("pawn", Color.RED, 6, 7)], set()),
    ],
)
def test_three_line_requires_exactly_three_pieces(
    label: str, extra: list[tuple[str, Color, int, int]], expected: set[tuple[int, int]]
) -> None:
    """线上连成 4 子 / 5 子时不算"三子相连"（R2）。"""
    g = game([("pawn", Color.RED, 7, 3), *_EXTRA, *extra])
    assert g.rules.pseudo_legal(g.state, Move(Position(7, 3), Position(6, 3)))
    assert removals(g, (7, 3), (6, 3)) == expected, label


def test_exactly_three_on_one_line_captures_even_when_another_line_is_longer() -> None:
    """多线独立：横线恰好三子照吃，竖线连成四子不结算。"""
    g = game(
        [
            ("pawn", Color.RED, 7, 3),
            # 横线：落点 + (6,4) + (6,5) —— 恰好三子
            ("pawn", Color.RED, 6, 4),
            ("advisor", Color.BLACK, 6, 5),
            # 竖线：(6,3) 落点 + (5,3) + (4,3) + (3,3) —— 四子，且中间隔着一敌
            ("pawn", Color.RED, 5, 3),
            ("advisor", Color.BLACK, 4, 3),
            ("pawn", Color.RED, 3, 3),
        ]
    )
    assert removals(g, (7, 3), (6, 3)) == {(6, 5)}


def test_capturable_squares_agrees_after_r1_and_r2() -> None:
    """不变量（R1/R2 之后仍成立）：`capturable_squares` 标的三连格 == 实走后的实际移除。

    这条是"能吃到 / 实际吃到"分叉的通用护栏：`_capture_removals` 的落点枚举
    必须与 `_apply_move` 的结算判据用同一套规则，否则 `in_check` 又会漏判。
    """
    for spec, move in (
        (_EXTRA, ((7, 3), (6, 3))),  # 恰好三子：能吃到 == 实际吃到 == {(6,5)}
        ([*_EXTRA, ("pawn", Color.RED, 6, 6)], ((7, 3), (6, 3))),  # 四子：两边都必须为空
        (
            [("pawn", Color.RED, 5, 4), ("advisor", Color.BLACK, 5, 5)],
            ((7, 3), (5, 3)),
        ),  # 两格行军：两边都必须为空
    ):
        g = game([("pawn", Color.RED, 7, 3), *spec])
        specs = g.rules.capturable_squares(g.state, Color.RED)
        reported = {s.position for s in specs.values() if any("three_line" in str(r.kind) for r in s.removals)}

        before = {(p.type, p.position) for p in g.state.pieces}
        after_state = g.rules.apply_unchecked(g.state, Move(Position(*move[0]), Position(*move[1])))
        after = {(p.type, p.position) for p in after_state.pieces}
        actual = {pos for (_t, pos) in before - after if pos != Position(*move[0])}

        assert reported == actual, f"{spec} → 能吃到 {reported} != 实际吃到 {actual}"
