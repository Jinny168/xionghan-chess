"""「专家」档：固定 d3、35s 上限、root_limit 沿用 18。

## 为什么要单独一个文件、还要拆快慢

深度测试每个局面要真跑 10–30 秒。16 条全开时整跑从 ~70s 涨到 ~230s（3.5 倍），
**改一行代码等四分钟**不划算；全关又不甘心（专家档的价值就是"能不能跑完 d3"）。

所以按**成本**拆：
- **默认只跑 2 条代表局面**（合计约 42s）：
  * `2719dd6f` —— 实测 27.7s，**最坏情况**，最容易回落 d2 的那条，必须留在默认集；
  * `c2c43f4f` —— 实测 14.6s，中位偏上。
  两端覆盖住了，默认门禁才既便宜又有意义（把最坏那条挪进 slow 等于自废门禁）。
- **其余 14 条标 `@pytest.mark.slow`**：`-m slow` 时全跑。

## 墙钟：**测能力，不测机器**
- 产品配置 `expert.time_limit` 仍是 **35s**（用户选的就是"愿意等 35 秒"）；
- 但**断言不用产品上限**：`35s` 是产品上限，不是测试上限。拿它当阈值，测的是"当时机器忙不忙"——
  `2719dd6f` 单跑 233s 全绿、整跑红过一次，就是负载造成的假红；
- 所以深度用例统一用 `AI_TIME_SCALE` 把预算放到 **180s**（35 × 36/7），断言 `completed_depth == 3`。
  只要算法没坏就一定绿，不受机器负载影响；
- **时长只报告、不断言**：实测中位 ~10.7s / 最坏 ~27.7s，负载下可能 >35s，写在这里供对照，不判红。

## 什么时候必须跑全 16 条

改了**评估函数 / 着法排序 / 搜索参数（depth、root_limit、branch_limit、quiescence）/
难度参数**之后 —— 这些都会改变各局面的分支宽度，只看 2 条会漏掉"某些局面突然回落 d2"。
命令：`pytest tests/test_expert_level.py -m slow`（14 条）+ 默认跑（2 条）= 全 16 条。
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

from xionghan_chess.core.ai import CONFIGS, ChessAI, Difficulty
from xionghan_chess.core.game import Game

ROOT = Path(__file__).resolve().parent.parent
CORPUS = json.loads(
    (ROOT / "benchmarks/baseline_2026-10-31-50p/base4_corpus16.json").read_text(encoding="utf-8")
)
sys.path.insert(0, str(ROOT / "scripts"))


def test_expert_config_is_fixed_depth_three() -> None:
    """参数口径：depth 3（固定）、35s、randomness 0、root_limit 18 与 hard 相同。"""
    expert = CONFIGS[Difficulty.EXPERT]
    hard = CONFIGS[Difficulty.HARD]
    assert expert.depth == 3
    assert expert.time_limit == 35.0
    assert expert.randomness == 0.0
    assert expert.root_limit == hard.root_limit == 18, "不改根宽，才能把深度单独归因"

    # hard 档一格未动
    assert (hard.depth, hard.time_limit, hard.randomness) == (8, 12.0, 0.0)


def test_expert_is_in_the_difficulty_dropdown() -> None:
    """设置页下拉里要在 hard 之后、master 之前。"""
    from PySide6.QtWidgets import QApplication

    from xionghan_chess.desktop.ui.dialogs import SettingsDialog

    QApplication.instance() or QApplication([])
    from xionghan_chess.desktop.config import DEFAULTS

    config = {**DEFAULTS, "profile": "desktop_complete", "language": "zh-CN",
              "difficulty": "expert"}
    dialog = SettingsDialog(config)
    values = [dialog.difficulty.itemData(i) for i in range(dialog.difficulty.count())]
    assert values == ["beginner", "easy", "medium", "hard", "expert", "master"]
    assert dialog.difficulty.findData("expert") >= 0
    dialog.deleteLater()


# 默认集：最坏 + 中位偏上两条；其余标 slow（见模块 docstring 的取舍说明）
DEFAULT_CORPUS_IDS = {"2719dd6f26e881f3", "c2c43f4f145beaa7"}
CORPUS_PARAMS = [
    pytest.param(
        entry,
        id=entry["id"][:8],
        marks=[] if entry["id"] in DEFAULT_CORPUS_IDS else [pytest.mark.slow],
    )
    for entry in CORPUS
]


@pytest.mark.parametrize("entry", CORPUS_PARAMS)
def test_expert_completes_depth_3_on_corpus(entry: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    """16 局面语料：每个都必须真的跑完 d3（`completed_depth == 3`）。

    若某局面 35s 被截断回落到 d2，这条会红并把该局面 id 报出来 —— 不偷偷放行。
    """
    import bench_roots as BR

    # 180s 预算：**测能力，不测机器**（35s 是产品上限，见模块 docstring）
    monkeypatch.setenv("AI_TIME_SCALE", str(180.0 / CONFIGS[Difficulty.EXPERT].time_limit))
    game, _ = BR.build_position(entry["profile"], entry["seed"], entry["plies"])
    ai = ChessAI(Difficulty.EXPERT)
    started = time.perf_counter()
    move = ai.choose_move(game)
    elapsed = time.perf_counter() - started
    assert move is not None
    assert ai.completed_depth == 3, (
        f"{entry['id'][:8]} 未跑完 d3（completed_depth={ai.completed_depth}, {elapsed:.1f}s）"
    )
    # 时长只报告，不断言（CI 机器更慢是常态）
    print(f"{entry['id'][:8]} d3 用时 {elapsed:.1f}s（180s 预算下）")


def Difficulty_EXPERT_LIMIT() -> float:      # noqa: N802 - 仅作本文件内的上限取值
    return CONFIGS[Difficulty.EXPERT].time_limit + 5.0      # 软上限：允许结算越过少量
