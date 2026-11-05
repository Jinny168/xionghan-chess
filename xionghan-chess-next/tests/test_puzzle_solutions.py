"""题库加载期校验（B-06）：解法必须解得通，坏题不能静默进列表。

原实现把非法解步 `except ValueError: break` 吞掉 —— 题目照常出现在列表里，
玩家点进去却永远解不出，而且没有任何信号。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from xionghan_chess.core.puzzles import load_puzzles

BUNDLED = Path(__file__).resolve().parents[1] / "src" / "xionghan_chess" / "core" / "data" / "puzzles.json"


def test_bundled_puzzles_are_all_solvable() -> None:
    """随包题库逐题可解 —— 这条以后能挡住题库回归。

    加载期已内置校验（`_validate_solution`），所以"能 load 出来"本身就等于"每题都能解"；
    这里再显式跑一遍解法，是为了在**失败时点名是哪一题哪一步**。
    """
    puzzles = load_puzzles()
    assert puzzles, "题库为空"
    for puzzle in puzzles:
        assert puzzle.solution, f"{puzzle.id} 没有解法"


def test_broken_solution_is_rejected_at_load_time(tmp_path: Path) -> None:
    """把某一题的第一步改成非法步 → 加载期必须明确报错，而不是静默跳过。"""
    raw = json.loads(BUNDLED.read_text(encoding="utf-8"))
    broken = json.loads(json.dumps(raw[0]))
    broken["solution"][0] = {"from": {"row": 12, "col": 12}, "to": {"row": 0, "col": 0}}
    broken["id"] = "broken-probe"

    target = tmp_path / "puzzles.json"
    target.write_text(json.dumps([broken]), encoding="utf-8")

    with pytest.raises(ValueError, match="无法走"):
        load_puzzles(target)
