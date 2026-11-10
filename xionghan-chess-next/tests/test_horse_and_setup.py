"""马的两条新规则（别马腿 / 直走三格仅移动）+ 开局布局（尉在将后方、士对称两枚）。

**这个文件里有一条“看起来不合理、其实刻意”的断言**：
`test_guard_has_no_opening_moves_by_design` —— 尉开局 0 着不是 bug，是强子的平衡约束。
历史包袱：`756a938`（1.7.4）曾把尉与士对调，让尉首着 4，理由是"玩家不愿动仕 → 整局不动尉"。
用户已明确该限制是设计意图，故此处**钉住 0**，防止下一个人"顺手优化"回去。
"""

from __future__ import annotations

import pytest

from xionghan_chess.core.game import Game, GameState
from xionghan_chess.core.model import Color, Piece, PieceType
from xionghan_chess.core.profiles import (
    OPTION_DEPENDS_ON,
    RuleOptions,
    option_dependencies,
    option_enabled_by,
)


def _horse_targets(extra: tuple[Piece, ...] = (), **overrides: object) -> set[tuple[int, int]]:
    """王放对角，避免两王同列“照面”把着法全挡掉（踩过一次的坑）。"""
    pieces = [
        Piece.create(PieceType.KING, Color.RED, 12, 0),
        Piece.create(PieceType.KING, Color.BLACK, 0, 12),
        Piece.create(PieceType.HORSE, Color.RED, 6, 6),
        *extra,
    ]
    game = Game.from_state(
        GameState("desktop_complete", list(pieces), turn=Color.RED), option_overrides=dict(overrides)
    )
    return {
        (m.target.row, m.target.col)
        for m in game.rules.legal_moves(game.state)
        if (m.source.row, m.source.col) == (6, 6)
    }


# --- 别马腿 ---------------------------------------------------------------


def test_horse_leg_blocking_blocks_when_enabled() -> None:
    """开启别马腿：右腿被己兵堵住时 (5,8)/(7,8) 不可走，其余 6 处仍可走。

    注意"默认值"分档案而定：完整/精简模式关闭它（加强版），经典模式开启（传统）。
    数据类的字段默认值仍是 True，这里先钉住这个默认，再验证开关行为。
    """
    assert RuleOptions().horse_blocked_by_leg is True

    blocker = (Piece.create(PieceType.PAWN, Color.RED, 6, 7),)
    targets = _horse_targets(blocker, horse_straight_three=False, horse_blocked_by_leg=True)

    assert (5, 8) not in targets and (7, 8) not in targets, "马腿没生效"
    assert targets == {(4, 5), (4, 7), (5, 4), (7, 4), (8, 5), (8, 7)}


def test_turning_leg_off_restores_chess_knight_moves() -> None:
    """关闭别马腿后走法同国际象棋：只多出被挡住的两格，其余不变。"""
    blocker = (Piece.create(PieceType.PAWN, Color.RED, 6, 7),)
    blocked = _horse_targets(blocker, horse_straight_three=False, horse_blocked_by_leg=True)
    free = _horse_targets(blocker, horse_straight_three=False, horse_blocked_by_leg=False)

    assert free - blocked == {(5, 8), (7, 8)}, "关掉别马腿只该多出被腿挡住的两格"
    assert blocked - free == set()


# --- 直走三格：可吃 / 仅移动 ------------------------------------------------


def test_straight_three_can_capture_by_default() -> None:
    enemy = (Piece.create(PieceType.PAWN, Color.BLACK, 6, 9),)
    targets = _horse_targets(enemy, horse_straight_three=True)
    assert (6, 9) in targets, "直走三格默认可吃子"


def test_move_only_blocks_capture_but_not_quiet_moves() -> None:
    enemy = (Piece.create(PieceType.PAWN, Color.BLACK, 6, 9),)
    with_enemy = _horse_targets(enemy, horse_straight_three=True, horse_straight_three_move_only=True)
    assert (6, 9) not in with_enemy, "仅可移动时不该吃子"

    quiet = _horse_targets(horse_straight_three=True, horse_straight_three_move_only=True)
    assert (6, 9) in quiet, "仅可移动不能把空格也一起禁掉"


def test_move_only_is_inert_without_straight_three() -> None:
    """上游关掉时，下游开关不改变任何着法 —— 这正是它被置灰的原因。"""
    on = _horse_targets(horse_straight_three=False, horse_straight_three_move_only=True)
    off = _horse_targets(horse_straight_three=False, horse_straight_three_move_only=False)
    assert on == off


# --- 开局布局 -------------------------------------------------------------


def test_layout_guard_sits_behind_king_with_two_advisors() -> None:
    game = Game("desktop_complete")
    red = {p.type: [] for p in game.state.pieces if p.color is Color.RED}
    for piece in game.state.pieces:
        if piece.color is Color.RED:
            red[piece.type].append((piece.position.row, piece.position.col))

    assert red[PieceType.KING] == [(11, 6)]
    assert sorted(red[PieceType.ADVISOR]) == [(11, 5), (11, 7)], "士应在将两侧各一枚"
    assert len(red[PieceType.ADVISOR]) == 2
    assert red[PieceType.GUARD] == [(12, 6)], "尉应在将正后（红方为下方）"
    assert len(red[PieceType.GUARD]) == 1


@pytest.mark.parametrize("profile_id", ["desktop_classic", "web"])
def test_non_complete_profiles_also_field_two_advisors(profile_id: str) -> None:
    game = Game(profile_id)
    advisors = [
        (p.position.row, p.position.col)
        for p in game.state.pieces
        if p.color is Color.RED and p.type is PieceType.ADVISOR
    ]
    assert sorted(advisors) == [(11, 5), (11, 7)]


def test_guard_has_no_opening_moves_by_design() -> None:
    """**刻意为之**：尉是强子，开局两条斜线被己方两只士占住 → 0 着。

    这是限制，不是缺陷。若哪天有人把尉的首着"优化"成 4，这条会红。
    """
    game = Game("desktop_complete")
    guard_moves = [
        (m.source.row, m.source.col)
        for m in game.rules.legal_moves(game.state)
        if (m.source.row, m.source.col) == (12, 6)
    ]
    assert guard_moves == [], "尉开局不该有子可动（强子的平衡约束）"


# --- 依赖关系 -------------------------------------------------------------


def test_dependency_map_points_at_real_options() -> None:
    """依赖表里的每个键（含父键）都必须是 `RuleOptions` 的真实字段。"""
    fields = set(RuleOptions.__dataclass_fields__)
    for child, parents in OPTION_DEPENDS_ON.items():
        assert child in fields, f"{child} 不是规则项"
        for parent in parents:
            assert parent in fields, f"{parent}（{child} 的上游）不是规则项"


def test_move_only_depends_on_straight_three() -> None:
    assert OPTION_DEPENDS_ON["horse_straight_three_move_only"] == ("horse_straight_three",)
    assert option_dependencies()["horse_straight_three_move_only"] == ["horse_straight_three"]

    # 上游关 → 下游“未就绪”；上游开 → 就绪
    assert option_enabled_by(RuleOptions(horse_straight_three=False), "horse_straight_three_move_only") is False
    assert option_enabled_by(RuleOptions(horse_straight_three=True), "horse_straight_three_move_only") is True
    # 无依赖的项恒为就绪
    assert option_enabled_by(RuleOptions(), "pawn_charge") is True
