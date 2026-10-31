"""「专家」档：固定 d3、35s 上限、root_limit 沿用 18。

为什么单独一个文件：深度测试要跑满 16 个局面（每个可能十几秒），标 `slow`；
而"配置对不对""下拉里有没有这一档"是毫秒级断言，不能被拖成慢测。
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


@pytest.mark.slow
@pytest.mark.parametrize("entry", CORPUS, ids=[item["id"][:8] for item in CORPUS])
def test_expert_completes_depth_3_on_corpus(entry: dict) -> None:
    """16 局面语料：每个都必须真的跑完 d3（`completed_depth == 3`）。

    若某局面 35s 被截断回落到 d2，这条会红并把该局面 id 报出来 —— 不偷偷放行。
    """
    import bench_roots as BR

    game, _ = BR.build_position(entry["profile"], entry["seed"], entry["plies"])
    ai = ChessAI(Difficulty.EXPERT)
    started = time.perf_counter()
    move = ai.choose_move(game)
    elapsed = time.perf_counter() - started
    assert move is not None
    assert ai.completed_depth == 3, (
        f"{entry['id'][:8]} 未跑完 d3（completed_depth={ai.completed_depth}, {elapsed:.1f}s）"
    )
    assert elapsed <= Difficulty_EXPERT_LIMIT(), f"{entry['id'][:8]} 超过 35s 上限：{elapsed:.1f}s"


def Difficulty_EXPERT_LIMIT() -> float:      # noqa: N802 - 仅作本文件内的上限取值
    return CONFIGS[Difficulty.EXPERT].time_limit + 5.0      # 软上限：允许结算越过少量
