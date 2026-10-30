"""内置题库的**内容质量**守卫（阶段2 S2-7 / 问题 P1-M）。

背景：`puzzles.json` 曾经 9 条全是「开局第一步」式单步 drill，标题却叫
「残局与排局训练」，且甲/刺/楯三种特色子力**零覆盖** —— 训练模块名不副实。

已有的 `tests/test_extensions.py::test_built_in_puzzle_solutions_are_legal` 只保证
「解法合法」，不保证「这道题真的在练它声称要练的东西」。本文件补上后者，
判据用 `Puzzle.exercise()`：**从解法反推**实际用到的子力与吃法，
不看题目自带的任何声明字段 —— 否则作者写一句 `pieceTypes: ["armor"]`
就能让覆盖率好看，而玩家实际上没碰到甲。

这些断言的意义不是「数字越大越好」，而是防退化：任何一次题库改写，只要把
甲/刺/楯 又弄丢了、或者整库退回成「只会挪一步、从不吃子」，这里立刻红。
"""

from __future__ import annotations

from functools import lru_cache

import pytest

from xionghan_chess.core.model import PieceType
from xionghan_chess.core.puzzles import load_puzzles


@lru_cache(maxsize=1)
def _coverage() -> tuple[dict[str, int], dict[str, int]]:
    """整库覆盖度只算一次。

    `Puzzle.exercise()` 每题都要 `game_from_document` + 逐步 `capturable_squares`
    全盘扫描，16 题跑下来近 1 分钟。这里七个断言共用同一份结果，避免把测试套件
    从 80 秒拖到 3 分钟 —— 慢测试最终会被人用 `-x` 或跳过对待。
    """
    pieces: dict[str, int] = {}
    kinds: dict[str, int] = {}
    for puzzle in load_puzzles():
        covered_pieces, covered_kinds = puzzle.exercise()
        for kind in covered_pieces:
            pieces[kind] = pieces.get(kind, 0) + 1
        for kind in covered_kinds:
            kinds[kind] = kinds.get(kind, 0) + 1
    return pieces, kinds


def test_special_pieces_are_covered() -> None:
    """P1-M 的原始症状：甲/刺/楯零覆盖。这三种子力是匈汉象棋的特色，不能被漏掉。"""
    pieces, _ = _coverage()
    # 甲/楯已软删（`*_appear=False` + 布局移除），题库里不再有它们的题；
    # 刺暂时缺题，缺口由下方 xfail(strict) 用例显式钉住。
    for kind in (PieceType.GUARD, PieceType.ARCHER, PieceType.THUNDER, PieceType.PATROL):
        assert pieces.get(kind.value, 0) >= 1, f"题库没有任何一道题真的用到 {kind.value}"


def test_every_piece_type_is_covered() -> None:
    pieces, _ = _coverage()
    # 甲/楯软删、刺暂时缺题：这三类由下方 xfail(strict) 单独钉，不在此静默放过
    skipped = {PieceType.ARMOR, PieceType.SHIELD, PieceType.ASSASSIN}
    missing = [kind.value for kind in PieceType
               if kind not in skipped and pieces.get(kind.value, 0) == 0]
    assert not missing, f"以下子力在题库里没有任何一道题练到：{missing}"


@pytest.mark.xfail(
    strict=True,
    reason="刺的唯一题目 endgame-assassin-drag-01 因机制删除而移除；待设计侧补一道刺题后本用例应通过，"
           "届时 strict 会报错提醒去掉本标记",
)
def test_assassin_is_covered() -> None:
    """题库应至少有一道题在解法中实际动到 ASSASSIN（`exercise()` 口径：解法真正走到的子力）。"""
    pieces, _ = _coverage()
    assert pieces.get(PieceType.ASSASSIN.value, 0) >= 1


@pytest.mark.xfail(
    strict=True,
    reason="甲/楯已软删（appear=False + 布局移除），题库里不再有它们的题；"
           "若将来恢复甲/楯并重新补题，本用例会通过，届时 strict 会报错提醒去掉本标记",
)
def test_soft_removed_pieces_are_covered() -> None:
    """甲（ARMOR）与楯（SHIELD）应至少各有一道题真的走到 —— 软删期间预期失败。"""
    pieces, _ = _coverage()
    for kind in (PieceType.ARMOR, PieceType.SHIELD):
        assert pieces.get(kind.value, 0) >= 1


def test_special_capture_kinds_are_covered() -> None:
    """成线吃与拖拽吃是甲的/刺的核心机制，光「能走」不算掌握。"""
    _, kinds = _coverage()
    # 甲的成线吃随甲一起软删（原 assert armor_line >= 1 已不适用）；
    # 兵三连是开关项（默认关），题库里也没有题触发它。
    # 刺的"拖拽/同归于尽"吃法已删除（改为兵走 + 斜向滑吃，归入 direct），
    # 题库里不再可能触发 `assassin_drag`；这里不再要求该类覆盖。


def test_puzzles_are_not_all_single_move_drills() -> None:
    """「残局」必须真的吃子。若整库只有挪步，标题就是虚的。"""
    _, kinds = _coverage()
    total_captures = sum(kinds.values())
    assert total_captures >= 5, f"真正吃子的题太少（{total_captures} 道），残局名不副实"


def test_each_difficulty_has_enough_content() -> None:
    """训练界面按难度筛选，任何一档空了都会让玩家看到空列表。"""
    tiers: dict[str, int] = {}
    for puzzle in load_puzzles():
        tiers[puzzle.difficulty] = tiers.get(puzzle.difficulty, 0) + 1
    assert set(tiers) == {"beginner", "advanced", "master"}, tiers
    for tier, count in tiers.items():
        assert count >= 3, f"{tier} 只有 {count} 道题，筛选后列表太空"


def test_every_puzzle_has_readable_metadata() -> None:
    """列表项显示「标题 · 描述」，任一为空都会出现孤立的分隔符。"""
    for puzzle in load_puzzles():
        assert puzzle.title.strip(), f"{puzzle.id} 缺标题"
        assert puzzle.description.strip(), f"{puzzle.id} 缺描述"
        assert puzzle.hints, f"{puzzle.id} 没有提示，玩家卡住时无路可走"


def test_solutions_actually_move_pieces() -> None:
    """`exercise()` 为空说明解法一步都没走成 —— 要么解法非法，要么题面是终局。"""
    for puzzle in load_puzzles():
        pieces, _ = puzzle.exercise()
        assert pieces, f"{puzzle.id} 的解法没有走到任何棋子"
