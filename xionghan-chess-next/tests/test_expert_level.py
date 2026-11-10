"""「专家」档并档后的契约：只是 HARD 的别名。

Expert 曾是固定 d3 / 35s 的独立档；实测选点与 hard 全同，产品已并档。
MCTS/深度语料测试不再属于产品门禁（研究路径由 `test_mcts_integration.py` 显式构造）。
"""

from __future__ import annotations

from xionghan_chess.core.ai import CONFIGS, Difficulty


def test_expert_is_an_alias_of_hard() -> None:
    assert CONFIGS[Difficulty.EXPERT] is CONFIGS[Difficulty.HARD]
    assert CONFIGS[Difficulty.EXPERT].depth == 3
    assert CONFIGS[Difficulty.EXPERT].time_limit == 12.0


def test_expert_is_merged_into_hard_in_the_dropdown() -> None:
    """并档后下拉只有三档；旧值 expert 归一成 hard，并在顶部显示「已并入高级」。"""
    from PySide6.QtWidgets import QApplication

    from xionghan_chess.desktop.config import DEFAULTS
    from xionghan_chess.desktop.ui.dialogs import SettingsDialog

    QApplication.instance() or QApplication([])
    config = {**DEFAULTS, "profile": "desktop_complete", "language": "zh-CN", "difficulty": "expert"}
    dialog = SettingsDialog(config)
    real_values = [dialog.difficulty.itemData(i) for i in range(dialog.difficulty.count())]
    assert real_values[:1] == ["expert"], "旧值应作为不可选提示条目出现"
    assert real_values[1:] == ["beginner", "medium", "hard"]
    assert dialog.difficulty.currentData() == "hard"
    assert dialog.difficulty.model().item(0).isEnabled() is False
    dialog.deleteLater()
