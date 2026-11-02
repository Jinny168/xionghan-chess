"""A2 战役章节：数据完整性 + 列表分组的接线。

两条断言防止以后有人加题时忘了分章，或者把分章做成"看起来有、实际没接上"。
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from xionghan_chess.core.puzzles import CHAPTERS, chapter_order, load_puzzles  # noqa: E402
from xionghan_chess.desktop.ui.dialogs import TrainingDialog  # noqa: E402


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_every_generated_puzzle_has_a_known_chapter() -> None:
    missing = [p.id for p in load_puzzles()
               if p.id.startswith("gen-") and p.chapter not in CHAPTERS]
    assert not missing, f"这些题没有分到已知章节：{missing}"


def test_drills_stay_unchaptered() -> None:
    """走法练习不属于任何战役 —— 它们排在章节之后单独归档。"""
    wrong = [p.id for p in load_puzzles() if "drill" in p.tags and p.chapter]
    assert not wrong, f"这些练习被错误地分进了章节：{wrong}"


def test_chapter_order_puts_unknown_last() -> None:
    assert sorted(CHAPTERS, key=chapter_order) == list(CHAPTERS), "已知章节要保持定义顺序"
    assert chapter_order("") == len(CHAPTERS)
    assert chapter_order("不存在的章节") == len(CHAPTERS)


def test_list_is_grouped_by_chapter(qt_app: QApplication) -> None:
    parent = QWidget()          # 父对象必须存活，否则对话框被回收
    parent.config = {}
    dialog = TrainingDialog(parent)

    headers, puzzles = [], []
    for index in range(dialog.list.count()):
        item = dialog.list.item(index)
        if item.flags() == Qt.ItemFlag.NoItemFlags:
            headers.append(item)
        else:
            puzzles.append(item)

    assert headers, "列表里没有分组标题 —— 章节没接上"
    assert puzzles, "列表里没有可选题目"
    for item in puzzles:
        assert item.data(Qt.ItemDataRole.UserRole), (
            f"题目项没写 id：{item.text()!r} —— 分组后行号不再等于下标，current() 会取错")

    # 选中第一条题目，`current()` 必须按 id 取回它
    first = puzzles[0]
    dialog.list.setCurrentItem(first)
    picked = dialog.current()
    assert picked is not None, "选中题目后 current() 返回 None"
    assert picked.id == first.data(Qt.ItemDataRole.UserRole)
