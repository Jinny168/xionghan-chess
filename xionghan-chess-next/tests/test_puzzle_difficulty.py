"""难度标定的落库守卫。

标定口径见 `scripts/calibrate_puzzles.py`：按 (ply, 首着是否一眼可见) 升序排，
再按 9/7/6 切三档。这里只守**排序不变量**，不跑引擎 —— 引擎项在标定脚本里，
每次改题库重跑一次即可；日常门禁只需保证没有题被"插队"到更低的档。
"""

from __future__ import annotations

from collections import defaultdict

from xionghan_chess.core.puzzles import load_puzzles

LEVELS = ["beginner", "advanced", "master"]


def _generated():
    return [item for item in load_puzzles() if item.id.startswith("gen-")]


def test_tiers_are_ordered_by_ply() -> None:
    """低档的 ply 不得高于高档：beginner ≤ advanced ≤ master。

    这条是标定排序的直接后果。如果有人手工把一道 7 ply 塞进 beginner，
    玩家第一天就会撞上一道四手杀 —— 而"每日一题"的第一印象就毁了。
    """
    by_level = defaultdict(list)
    for puzzle in _generated():
        by_level[puzzle.difficulty].append(len(puzzle.solution))
    for lower, higher in zip(LEVELS, LEVELS[1:]):
        assert by_level[lower], f"{lower} 档是空的"
        assert max(by_level[lower]) <= min(by_level[higher]), (
            f"{lower} 有 {max(by_level[lower])} ply，却比 {higher} 的 {min(by_level[higher])} ply 还长"
        )


def test_beginner_tier_is_all_two_move_mates() -> None:
    """新手档只放 3 ply（2 手杀）：第一天的题必须是"看一步就懂"的。"""
    beginner = [p for p in _generated() if p.difficulty == "beginner"]
    assert beginner, "beginner 档为空"
    assert {len(p.solution) for p in beginner} == {3}


def test_every_generated_puzzle_has_a_tier() -> None:
    for puzzle in _generated():
        assert puzzle.difficulty in LEVELS, f"{puzzle.id} 的难度 {puzzle.difficulty!r} 不认识"
