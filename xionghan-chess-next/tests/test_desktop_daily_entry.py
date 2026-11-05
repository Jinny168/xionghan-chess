"""桌面端「每日一题」入口：按钮存在、文案跟随连续天数、点了直接开当天那题。

只测入口的**接线**（选到哪道题、文案读的哪个字段），不重复测选题算法本身
—— 那部分在 `tests/test_daily_puzzle.py` 里，是纯逻辑、不需要 Qt。

注意对象生命周期：父 `QWidget` 必须在本测试内保持存活。父对象一被回收，
子对话框跟着销毁，后面的 `dialog.xxx` 会抛 `RuntimeError: Internal C++ object already deleted`。
"""

from __future__ import annotations

import os
from datetime import date

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from xionghan_chess.core import daily as daily_quiz  # noqa: E402
from xionghan_chess.core.puzzles import load_puzzles  # noqa: E402
from xionghan_chess.desktop.ui.dialogs import TrainingDialog  # noqa: E402


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _dialog(config: dict | None = None) -> tuple[QWidget, TrainingDialog]:
    """返回 (父窗口, 对话框)。父窗口由调用方持有，保证对话框不会被提前回收。"""
    parent = QWidget()
    parent.config = config if config is not None else {}   # TrainingDialog 只读 parent.config
    return parent, TrainingDialog(parent)


def test_daily_button_exists_and_targets_todays_puzzle(qt_app: QApplication) -> None:
    parent, dialog = _dialog()
    expected = daily_quiz.pick_daily(load_puzzles(), date.today())
    assert dialog.daily_puzzle is not None
    assert dialog.daily_puzzle.id == expected.id, "每日入口选到的不是当天那道题"
    assert "每日" in dialog.daily_button.text() or "Daily" in dialog.daily_button.text()
    assert dialog.daily_button.isEnabled()
    # 主入口不能是一条 20px 的窄带（Qt 默认高度就是 20，实测比下面的下拉框还矮）
    assert dialog.daily_button.minimumHeight() >= 30
    assert parent is not None


def test_clicking_daily_starts_that_puzzle_without_selection(qt_app: QApplication) -> None:
    """不选列表项也能开题 —— 这正是「入口」与「列表」的区别。"""
    parent, dialog = _dialog()
    dialog.start_daily()
    assert dialog.started_daily is True
    assert dialog.selected_puzzle is dialog.daily_puzzle
    assert dialog.selected_game is not None
    assert parent is not None


def test_button_reads_streak_from_parent_config(qt_app: QApplication) -> None:
    """昨天做完了、今天还没做 → 按钮显示「第 N+1 天」而不是清零。"""
    yesterday = date.fromordinal(date.today().toordinal() - 1)
    record = daily_quiz.DailyRecord(day=yesterday.isoformat(), id="x", done=True,
                                    streak=3, best=3)
    parent, dialog = _dialog({"daily": record.to_dict()})
    text = dialog.daily_button.text()
    assert "4" in text, f"连续天数没接上：{text}"
    assert parent is not None


def test_button_shows_solved_state_for_today(qt_app: QApplication) -> None:
    record = daily_quiz.DailyRecord(day=date.today().isoformat(), id="x", done=True,
                                    streak=5, best=5)
    parent, dialog = _dialog({"daily": record.to_dict()})
    text = dialog.daily_button.text().lower()
    assert "明天" in text or "tomorrow" in text
    assert parent is not None
