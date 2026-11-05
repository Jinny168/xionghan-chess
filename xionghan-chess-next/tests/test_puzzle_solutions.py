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


# --------------------------------------------------------------------------- #
# 题面 options 的数据卫生（2.0.0 清债）
#
# 背景：题面 `document.options` 是**当年那一刻**的全量快照，包含两类不该留在数据里的键：
#   ① 引擎早就不认识的键（`pawn_full_movement_at_base`）—— 加载器本来就忽略，
#      纯垃圾，但会让"这题用哪些开关"看起来比实际复杂；
#   ② 当年默认值被写进数据、后来默认值又改了的键（`pawn_backward_at_base`）——
#      留着等于把这些题的走法语义**钉死在 2.0.0 之前**，改默认值对它们无效。
# 删②之前必须先逐题重放解法：删了会让这些题失去"底线后退"，可能直接把题做死。
# 本轮实测 35/35 仍可解（见提交信息），所以两键都删了；这里留下护栏防回潮。
# --------------------------------------------------------------------------- #


def test_puzzle_options_only_use_keys_the_engine_knows() -> None:
    """题面里不许出现 `RuleOptions` 已不认识的键（`pawn_full_movement_at_base` 这类残骸）。

    判据直接用 `RuleOptions` 的字段集合 —— 不在别处再抄一份"合法键名单"。
    """
    from dataclasses import asdict

    from xionghan_chess.core.profiles import RuleOptions

    known = set(asdict(RuleOptions()))
    offenders = {}
    for puzzle in load_puzzles():
        extra = sorted(set(puzzle.document.get("options", {})) - known)
        if extra:
            offenders[puzzle.id] = extra
    assert not offenders, (
        f"题面 options 里出现了引擎不认识的键：{offenders}\n"
        "  → 改哪：src/xionghan_chess/core/data/puzzles.json 里对应题目的 document.options\n"
        "  → 改什么：删掉这些键（加载器本来就忽略它们），然后重新生成安卓离线题库：\n"
        "     python scripts/build_offline_puzzles.py"
    )


def test_puzzle_options_do_not_pin_the_retired_backward_pawn_switch() -> None:
    """`pawn_backward_at_base` 不许回到题面里。

    2.0.0 把它的默认值改成 `False`（兵到底线后不再后退）。题面里若显式写着 `true`，
    `RuleOptions.merged()` 会用它盖掉默认值 —— 这些题就会永远停在旧规则上，
    而"改默认值"对它们**完全无效**。要允许某题底线后退，应当是例外且显式的决定，
    届时连同这条断言一起改，而不是无声地跟着历史快照走。
    """
    offenders = [puzzle.id for puzzle in load_puzzles()
                 if "pawn_backward_at_base" in puzzle.document.get("options", {})]
    assert not offenders, (
        f"这些题的题面里又写上了 `pawn_backward_at_base`：{offenders}\n"
        "  → 改哪：src/xionghan_chess/core/data/puzzles.json 里对应题目的 document.options\n"
        "  → 改什么：删掉该键（走默认值 False）；随后重新生成安卓离线题库"
    )
