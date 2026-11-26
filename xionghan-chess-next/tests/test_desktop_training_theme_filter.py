"""训练主题筛选：真改下拉、真看列表，不靠源码字符串。

主题与难度是互斥视图：选主题时难度让位给「全部难度」，选回难度时主题清空。
这里直接驱动 `QComboBox`，验证的是玩家实际能走到的路径。
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from xionghan_chess.core.training_progress import is_defense_puzzle  # noqa: E402
from xionghan_chess.desktop.ui.dialogs import TRAINING_THEME_ALL, TrainingDialog  # noqa: E402


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _dialog() -> tuple[QWidget, TrainingDialog]:
    parent = QWidget()  # 父对象必须存活，否则对话框被提前回收
    parent.config = {}
    return parent, TrainingDialog(parent)


def _listed_ids(dialog: TrainingDialog) -> set[str]:
    ids = set()
    for index in range(dialog.list.count()):
        data = dialog.list.item(index).data(Qt.ItemDataRole.UserRole)
        if data:
            ids.add(str(data))
    return ids


def test_theme_filter_finds_archer_puzzles(qt_app: QApplication) -> None:
    """「我想练射」必须同时捞到射的走法练习与 feature:archer 真题。"""
    parent, dialog = _dialog()
    dialog.theme.setCurrentIndex(dialog.theme.findData("archer"))

    ids = {p.id for p in dialog.puzzles}
    assert {"advanced-archer-01", "gen-25"} <= ids, ids
    assert "gen-01" not in ids, "围杀题不该混进射星轨筛选"
    assert _listed_ids(dialog) == ids, "下拉筛出的题没同步到列表"
    assert parent is not None


def test_theme_and_difficulty_are_mutually_exclusive(qt_app: QApplication) -> None:
    """两个筛选器但不是两个 AND 条件：后选的维度接管，另一个回到全部。"""
    parent, dialog = _dialog()
    assert dialog.level.currentData() == "beginner"

    dialog.theme.setCurrentIndex(dialog.theme.findData("archer"))
    assert dialog.level.currentData() is None, "选主题后难度应为「全部难度」"
    assert any(p.id == "advanced-archer-01" for p in dialog.puzzles), "主题筛选被旧难度挡住了"

    dialog.level.setCurrentIndex(0)  # 玩家改回 beginner
    assert dialog.theme.currentData() == TRAINING_THEME_ALL, "改回难度应清空主题"
    assert dialog.puzzles and all(p.difficulty == "beginner" for p in dialog.puzzles)
    assert parent is not None


def test_defense_theme_reuses_training_progress_recognizer(qt_app: QApplication) -> None:
    """守和口径由 `is_defense_puzzle` 单独持有，UI 不能另写一套。"""
    parent, dialog = _dialog()
    dialog.theme.setCurrentIndex(dialog.theme.findData("defense"))

    expected = {p.id for p in dialog.daily_puzzles if is_defense_puzzle(p)}
    assert expected, "题库里应当有守和题"
    assert {p.id for p in dialog.puzzles} == expected
    assert parent is not None


def test_theme_without_puzzles_shows_explicit_empty_state(qt_app: QApplication) -> None:
    """后续批次的专题标签还没补进题库时，给空态而不是静默空白列表。"""
    parent, dialog = _dialog()
    dialog.theme.setCurrentIndex(dialog.theme.findData("pawn_resurrection"))

    assert dialog.puzzles == []
    notes = [dialog.list.item(i) for i in range(dialog.list.count())]
    assert any("兵复活" in note.text() for note in notes), [note.text() for note in notes]
    assert all(note.flags() == Qt.ItemFlag.NoItemFlags for note in notes), "空态不应可选"

    dialog.theme.setCurrentIndex(dialog.theme.findData(TRAINING_THEME_ALL))
    assert dialog.puzzles, "切回全部主题应恢复题目"
    assert parent is not None
