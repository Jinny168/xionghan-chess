"""桌面快捷键的功能核查：不只列清单，而是**真的按键**看有没有生效。

为什么值得单独测：快捷键最容易出现三种"看起来有、实际没用"的问题 ——
① QAction 建好了但没加到菜单（不在窗口作用域，按了没反应）；
② 与文本输入框冲突（在聊天框里按 Ctrl+Z 把棋盘悔了，而不是撤销输入）；
③ 单字母快捷键（如 `F` 翻转棋盘）会吃掉正常打字。
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.core.model import Move, Position  # noqa: E402
from xionghan_chess.desktop.app import MainWindow  # noqa: E402


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def window(qt_app):
    # 隔离与 `save_config` 的拦截已由 `tests/conftest.py` 的 autouse fixture
    # （`isolated_user_data`）统一兜住，不再逐文件 patch —— 原先这里的
    # `monkeypatch.setattr(settings, "save_config", ...)` 拦不住 app.py 里
    # `from .config import save_config` 拿到的那个副本，等于没拦。
    win = MainWindow()
    win.show()
    qt_app.processEvents()
    yield win
    win.close()


def _actions(window):
    for menu_action in window.menuBar().actions():
        menu = menu_action.menu()
        if not menu:
            continue
        for action in menu.actions():
            if not action.isSeparator() and not action.shortcut().isEmpty():
                yield menu_action.text(), action


def test_shortcuts_are_unique(window) -> None:
    seen: dict[str, list[str]] = {}
    for _menu, action in _actions(window):
        seen.setdefault(action.shortcut().toString(), []).append(action.text())
    duplicated = {seq: names for seq, names in seen.items() if len(names) > 1}
    assert not duplicated, f"快捷键冲突：{duplicated}"


def test_no_plain_letter_shortcuts(window) -> None:
    """单字母快捷键会吃掉正常打字（侧栏有聊天输入框）。"""
    plain = [action.shortcut().toString() for _menu, action in _actions(window)
             if len(action.shortcut().toString()) == 1]
    assert not plain, f"存在单字母快捷键，会和文字输入冲突：{plain}"


def test_f11_toggles_fullscreen(window) -> None:
    assert not window.isFullScreen()
    QTest.keyClick(window, Qt.Key.Key_F11)
    QApplication.instance().processEvents()
    assert window.isFullScreen(), "按 F11 没有进入全屏 —— 检查 QAction 是否挂进菜单"
    QTest.keyClick(window, Qt.Key.Key_F11)
    QApplication.instance().processEvents()
    assert not window.isFullScreen(), "再按 F11 没有退出全屏"


def _play_one_move(window) -> None:
    """走一手真实合法的棋，给悔棋/暂停等用例制造前提。"""
    game = window.game
    move = game.rules.legal_moves(game.state, game.state.turn)[0]
    window.human_move(move)
    QApplication.instance().processEvents()


def test_ctrl_z_undoes_the_last_move(window) -> None:
    _play_one_move(window)
    assert window.game.state.history, "前提：应当已有一步历史"
    QTest.keyClick(window, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    QApplication.instance().processEvents()
    assert not window.game.state.history, "按 Ctrl+Z 没有悔棋"


def test_ctrl_p_toggles_pause(window) -> None:
    before = window.game.state.paused
    QTest.keyClick(window, Qt.Key.Key_P, Qt.KeyboardModifier.ControlModifier)
    QApplication.instance().processEvents()
    assert window.game.state.paused is not before, "按 Ctrl+P 没有切换暂停"


def test_ctrl_z_in_the_chat_box_does_not_move_the_board(window) -> None:
    """在聊天框里按 Ctrl+Z 应该只影响输入框，不该把棋盘悔了。

    这里是**行为断言**：如果窗口级快捷键抢走了按键，历史会少一步。
    """
    _play_one_move(window)
    history_before = len(window.game.state.history)
    window.chat_input.setText("测试文字")
    window.chat_input.setFocus()
    QApplication.instance().processEvents()
    QTest.keyClick(window.chat_input, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    QApplication.instance().processEvents()
    assert len(window.game.state.history) == history_before, (
        "在聊天框里按 Ctrl+Z 把棋盘悔了 —— 窗口级快捷键抢走了文本框的撤销")


def test_side_buttons_are_icon_only_with_tooltips(window) -> None:
    """侧栏七个操作必须是纯图标：文字退到 tooltip，否则单列会占满整条侧栏。"""
    for name in ("undo", "pause", "resign", "draw", "resurrect", "flip", "again"):
        button = getattr(window, name)
        assert button.text() == "", f"{name} 还在显示文字，图标化没生效"
        assert not button.icon().isNull(), f"{name} 没有图标"
        assert button.toolTip(), f"{name} 缺少悬浮说明"
        assert button.accessibleName(), f"{name} 缺少无障碍名（读屏会读成空按钮）"


def test_side_buttons_are_icon_only_with_tooltips(window) -> None:
    """侧栏七个操作必须是纯图标：文字退到 tooltip，否则单列会占满整条侧栏。"""
    for name in ("undo", "pause", "resign", "draw", "resurrect", "flip", "again"):
        button = getattr(window, name)
        assert button.text() == "", f"{name} 还在显示文字，图标化没生效"
        assert not button.icon().isNull(), f"{name} 没有图标"
        assert button.toolTip(), f"{name} 缺少悬浮说明"
        assert button.accessibleName(), f"{name} 缺少无障碍名（读屏会读成空按钮）"
